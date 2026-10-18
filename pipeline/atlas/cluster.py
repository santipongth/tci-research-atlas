"""Topic clustering (no BERTopic dependency):

  embeddings → [PCA] → UMAP (fit on a sample, transform the rest) → HDBSCAN
  → merge over-split clusters (centroid cosine ≥ merge_similarity)
  → outliers join the nearest topic only if cosine ≥ outlier_min_similarity (else −1 = unassigned)
  → coarse groups = agglomerative clustering of topic centroids (P1: OpenAlex fields)
  → per topic: c-TF-IDF words, author keywords, coherence (mean cosine to centroid)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.ctfidf import topic_keywords, topic_terms
from atlas.io_utils import read_table, write_table


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

        X = PCA(pca_dims, random_state=seed).fit(emb[_sample(n, 100_000, seed)]).transform(emb)
    import umap

    reducer = umap.UMAP(n_components=min(n_comp, n - 2), n_neighbors=min(int(fine["umap_n_neighbors"]), n - 1),
                        min_dist=float(fine["umap_min_dist"]), metric="cosine", random_state=seed)
    fit_n = int(ccfg["umap_fit_sample"])
    if n > fit_n:
        reducer.fit(X[_sample(n, fit_n, seed)])
        return reducer.transform(X)
    return reducer.fit_transform(X)


def hdbscan_labels(red: np.ndarray, fine: dict) -> np.ndarray:
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


def cluster(cfg: dict) -> np.ndarray:
    work = Path(cfg["pipeline"]["work_dir"])
    df = read_table(work / "02_docs.parquet")
    emb = np.load(work / "03_embeddings.npy")
    ccfg, seed = cfg["clustering"], int(cfg["pipeline"]["seed"])

    raw = hdbscan_labels(reduce_embeddings(emb, ccfg, seed), ccfg["fine"])
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
    labels = relabel_by_size(labels)
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
    write_table(pd.DataFrame({"article_id": df["article_id"], "fine_topic": labels}), work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"article_id": df["article_id"],
                              "coarse_topic": [group_of.get(int(x), -1) for x in labels]}),
                work / "04_coarse_topics.parquet")
    write_table(info, work / "04_topic_info.parquet")
    np.save(work / "04_centroids.npy", C)
    (work / "04_centroid_ids.json").write_text(json.dumps(ids), encoding="utf-8")
    print(f"[cluster] HDBSCAN {n_raw} → merged {len(ids)} topics, {len(set(groups.tolist()))} groups, "
          f"unassigned {(labels < 0).mean():.1%}")
    return labels
