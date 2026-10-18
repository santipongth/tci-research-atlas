"""Topic clustering (no BERTopic dependency):

  embeddings → [PCA] → UMAP (fit on a sample, transform the rest) → HDBSCAN
  → merge over-split clusters (centroid cosine ≥ merge_similarity)
  → outliers join the nearest topic only if cosine ≥ outlier_min_similarity (else −1 = unassigned)
  → coarse groups = agglomerative clustering of topic centroids (P1: OpenAlex fields)
  → per topic: c-TF-IDF words, author keywords, coherence (mean cosine to centroid)

Stable ids (atlas/lineage.py): topics.mode auto|fit|assign — assign keeps last release's
topics, fit re-clusters and matches clusters to last release's ids; state per release in
state_dir/releases/<release>/topics/. Extra outputs: 04_lineage, 04_topics_meta.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import load_aligned
from atlas.ctfidf import topic_keywords, topic_terms
from atlas.io_utils import write_table
from atlas.lineage import (
    EVENT_COLUMNS,
    EVENTS,
    assign_to_previous,
    kept_fraction,
    load_topic_state,
    match_topics,
    member_centroids,
    save_topic_state,
    update_registry,
)
from atlas.state import current_release, previous_release


def _sample(n: int, k: int, seed: int) -> np.ndarray:
    return np.sort(np.random.default_rng(seed).choice(n, k, replace=False)) if n > k else np.arange(n)


def reduce_embeddings(emb: np.ndarray, ccfg: dict, seed: int) -> np.ndarray:
    n, d = emb.shape
    fine = ccfg["fine"]
    n_comp = int(fine["umap_n_components"])
    if ccfg["reducer"] == "pca" or n < 10:
        from sklearn.decomposition import PCA

        return PCA(max(1, min(n_comp, d, n - 1)), random_state=seed).fit_transform(emb)
    X = emb
    pca_dims = int(ccfg["pca_dims"])
    if d > pca_dims and n > pca_dims:
        from sklearn.decomposition import PCA

        X = PCA(pca_dims, random_state=seed).fit(emb[_sample(n, int(ccfg["pca_fit_sample"]), seed)]).transform(emb)
    import umap

    reducer = umap.UMAP(n_components=min(n_comp, n - 2), n_neighbors=min(int(fine["umap_n_neighbors"]), n - 1),
                        min_dist=float(fine["umap_min_dist"]), metric="cosine", random_state=seed)
    fit_n = int(ccfg["umap_fit_sample"])
    if n > fit_n:
        reducer.fit(X[_sample(n, fit_n, seed)])
        return reducer.transform(X)
    return reducer.fit_transform(X)


def hdbscan_labels(red: np.ndarray, fine: dict, backend: str = "sklearn") -> np.ndarray:
    if backend == "fast":
        import fast_hdbscan  # optional extra: uv sync --extra fast

        n = len(red)
        mcs = max(2, min(int(fine["hdbscan_min_cluster_size"]), max(2, n // 2)))
        ms = max(1, min(int(fine["hdbscan_min_samples"]), mcs))
        return np.asarray(fast_hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=ms).fit_predict(red), dtype=int)
    from sklearn.cluster import HDBSCAN

    n = len(red)
    mcs = max(2, min(int(fine["hdbscan_min_cluster_size"]), max(2, n // 2)))
    ms = max(1, min(int(fine["hdbscan_min_samples"]), mcs))
    return HDBSCAN(min_cluster_size=mcs, min_samples=ms, copy=True).fit_predict(red)


def centroids(labels: np.ndarray, emb: np.ndarray) -> tuple[list[int], np.ndarray]:
    ids = sorted(set(int(x) for x in labels) - {-1})
    if not ids:
        return [], np.zeros((0, emb.shape[1]), dtype=np.float32)
    C = np.stack([emb[labels == i].mean(axis=0) for i in ids])
    C /= np.maximum(np.linalg.norm(C, axis=1, keepdims=True), 1e-9)
    return ids, C.astype(np.float32)


def merge_similar(labels: np.ndarray, emb: np.ndarray, threshold: float) -> np.ndarray:
    ids, C = centroids(labels, emb)
    if len(ids) < 2:
        return labels.copy()
    from sklearn.cluster import AgglomerativeClustering

    grp = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                  distance_threshold=1.0 - threshold).fit_predict(C)
    mapping = dict(zip(ids, (int(g) for g in grp)))
    return np.array([mapping.get(int(x), -1) for x in labels])


def assign_outliers(labels: np.ndarray, emb: np.ndarray, min_sim: float) -> np.ndarray:
    labels = labels.copy()
    mask = labels == -1
    ids, C = centroids(labels, emb)
    if not mask.any() or not ids:
        return labels
    sim = emb[mask] @ C.T
    labels[mask] = np.where(sim.max(axis=1) >= min_sim, np.array(ids)[sim.argmax(axis=1)], -1)
    return labels


def relabel_by_size(labels: np.ndarray) -> np.ndarray:
    order = pd.Series(labels[labels >= 0]).value_counts(sort=True).index.tolist()
    mapping = {int(old): new for new, old in enumerate(order)}
    return np.array([mapping.get(int(x), -1) for x in labels])


def coarse_groups(C: np.ndarray, n_groups: int) -> np.ndarray:
    if len(C) <= 1:
        return np.zeros(len(C), dtype=int)
    from sklearn.cluster import AgglomerativeClustering

    return AgglomerativeClustering(n_clusters=min(n_groups, len(C)), metric="cosine",
                                   linkage="average").fit_predict(C)


def fit_labels(emb: np.ndarray, ccfg: dict, seed: int) -> tuple[np.ndarray, int]:
    """Cluster from scratch → (labels 0..k−1 by size, −1 = unassigned; raw cluster count)."""
    if ccfg["algorithm"] == "leiden":
        from atlas.graph_cluster import leiden_labels  # optional extra: uv sync --extra leiden

        raw = leiden_labels(emb, ccfg["leiden"], seed)
    else:
        raw = hdbscan_labels(reduce_embeddings(emb, ccfg, seed), ccfg["fine"], ccfg["hdbscan_backend"])
    n_raw = len(set(raw.tolist()) - {-1})
    labels = merge_similar(raw, emb, float(ccfg["merge_similarity"]))
    labels = assign_outliers(labels, emb, float(ccfg["outlier_min_similarity"]))
    if (labels < 0).all():
        mcs = int(ccfg["fine"]["hdbscan_min_cluster_size"])
        if len(labels) >= 2 * mcs:
            raise ValueError(
                f"HDBSCAN found no clusters in {len(labels):,} documents (everything is noise). Lower "
                f"clustering.fine.hdbscan_min_cluster_size (now {mcs}) / hdbscan_min_samples, or check the "
                f"embeddings (embedding.provider, 03_meta.json) before publishing anything")
        labels = np.zeros(len(labels), dtype=int)      # tiny corpus (< 2 × min_cluster_size): one topic
    return relabel_by_size(labels), n_raw


def _embedding_model_id(work: Path) -> str:
    meta = work / "03_meta.json"
    return json.loads(meta.read_text(encoding="utf-8"))["model_id"] if meta.exists() else ""


def _active_ids(registry: pd.DataFrame) -> set[int]:
    return set(registry.loc[registry["status"] == "active", "topic_id"].astype(int))


def stable_labels(cfg: dict, article_ids: pd.Series, emb: np.ndarray, prev: dict | None,
                  model_id: str) -> tuple[np.ndarray, pd.DataFrame, dict, str]:
    """→ (labels with stable ids, lineage events, model.json for this release, log message)."""
    ccfg, tcfg, seed = cfg["clustering"], cfg["topics"], int(cfg["pipeline"]["seed"])
    min_sim = float(ccfg["outlier_min_similarity"])
    mode, reason = tcfg["mode"], "configured"
    if prev is None:
        mode, reason = "fit", "no previous release"
    elif mode == "auto":
        pm = prev["model"]
        if pm.get("embedding_model") != model_id:
            mode, reason = "fit", "embedding model changed"
        elif int(pm.get("releases_since_fit", 0)) + 1 >= int(tcfg["refit_every_releases"]):
            mode, reason = "fit", "scheduled refit"
        else:
            mode, reason = "assign", "auto"
    if mode == "assign":
        labels, n_new, n_lost = assign_to_previous(article_ids, emb, prev["assignments"], min_sim)
        if tcfg["mode"] == "auto" and n_new and n_lost / n_new > float(tcfg["refit_max_unassigned"]):
            mode, reason = "fit", f"{n_lost / n_new:.0%} of new articles fit no topic"
        else:
            cur = sorted(set(labels.tolist()) - {-1})
            events = pd.DataFrame([{"event": "continue", "topic_id": t, "parents": ""} for t in cur]
                                  + [{"event": "retired", "topic_id": t, "parents": ""}
                                     for t in sorted(_active_ids(prev["registry"]) - set(cur))],
                                  columns=EVENT_COLUMNS)
            model = {**prev["model"], "releases_since_fit": int(prev["model"].get("releases_since_fit", 0)) + 1,
                     "mode": "assign"}
            return labels, events, model, f"assign ({reason}): {n_new:,} new articles, {n_lost:,} without a topic"
    tmp, n_raw = fit_labels(emb, ccfg, seed)
    cur_df = pd.DataFrame({"article_id": article_ids.to_numpy(), "topic_id": tmp})
    if prev is None:
        mapping = {t: t + 1 for t in sorted(set(tmp.tolist()) - {-1})}
        events = pd.DataFrame([{"event": "new", "topic_id": s, "parents": ""} for s in mapping.values()],
                              columns=EVENT_COLUMNS)
        next_id = max(mapping.values(), default=0) + 1
    else:
        pa = prev["assignments"]
        old_vec = member_centroids(article_ids, emb, pa)
        new_vec = member_centroids(article_ids, emb, cur_df)
        mapping, events, next_id = match_topics(pa, cur_df, old_vec, new_vec, int(prev["model"]["next_id"]),
                                                float(tcfg["match_containment"]), int(tcfg["match_min_shared"]))
    labels = np.array([mapping.get(int(t), -1) for t in tmp], dtype=int)
    model = {"embedding_model": model_id, "fitted_release": current_release(cfg), "releases_since_fit": 0,
             "next_id": int(next_id), "mode": "fit"}
    return labels, events, model, f"fit ({reason}): {n_raw} raw clusters → {len(mapping)} topics"


def cluster(cfg: dict) -> np.ndarray:
    work = Path(cfg["pipeline"]["work_dir"])
    df, emb = load_aligned(work)
    ccfg, seed = cfg["clustering"], int(cfg["pipeline"]["seed"])
    release, prev_release = current_release(cfg), previous_release(cfg)
    prev = load_topic_state(cfg, prev_release)

    labels, events, model, msg = stable_labels(cfg, df["article_id"], emb, prev, _embedding_model_id(work))
    ids, C = centroids(labels, emb)
    groups = coarse_groups(C, int(ccfg["n_groups"]))
    group_of = dict(zip(ids, (int(g) for g in groups)))

    texts = {t: df["doc_text"][labels == t].tolist() for t in ids}
    kw_col = (df.get("keywords_th", pd.Series([""] * len(df))).fillna("").astype(str) + "; "
              + df.get("keywords_en", pd.Series([""] * len(df))).fillna("").astype(str))
    kws = {t: kw_col[labels == t].tolist() for t in ids}
    top_n = int(ccfg["ctfidf_top_n"])
    terms = topic_terms(texts, top_n, int(ccfg["ctfidf_max_docs_per_topic"]), seed)
    keys = topic_keywords(kws, top_n)

    info = pd.DataFrame([{
        "level": "fine", "topic_id": t, "size": int((labels == t).sum()),
        "top_terms": "; ".join(terms[t]), "top_keywords": "; ".join(keys[t]),
        "coarse_topic": group_of[t], "coherence": float((emb[labels == t] @ C[i]).mean()),
    } for i, t in enumerate(ids)])
    fine = pd.DataFrame({"article_id": df["article_id"], "fine_topic": labels})
    write_table(fine, work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"article_id": df["article_id"],
                              "coarse_topic": [group_of.get(int(x), -1) for x in labels]}),
                work / "04_coarse_topics.parquet")
    write_table(info, work / "04_topic_info.parquet")
    write_table(events, work / "04_lineage.parquet")
    np.save(work / "04_centroids.npy", C)
    (work / "04_centroid_ids.json").write_text(json.dumps(ids), encoding="utf-8")

    kept = kept_fraction(set() if prev is None else _active_ids(prev["registry"]), set(ids))
    (work / "04_topics_meta.json").write_text(json.dumps({
        "release": release, "previous_release": prev_release, "mode": model["mode"],
        "kept_fraction": round(kept, 4), "n_topics": len(ids),
        "events": {e: int((events["event"] == e).sum()) for e in EVENTS},
    }), encoding="utf-8")
    registry = update_registry(None if prev is None else prev["registry"], ids, events, release)
    save_topic_state(cfg, release, fine.rename(columns={"fine_topic": "topic_id"}), registry, events, model)
    print(f"[cluster] {msg}; {len(ids)} topics, {len(set(groups.tolist()))} groups, "
          f"unassigned {(labels < 0).mean():.1%}, ids kept {kept:.0%}")
    return labels
