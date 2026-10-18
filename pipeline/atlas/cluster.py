"""Phase 3 — Two-level topic clustering (BERTopic: UMAP + HDBSCAN + c-TF-IDF).

  - coarse : big groups shown as hubs on the atlas
  - fine   : topics for drill-down, time series, emerging detection

Outputs:
  work/04_fine_topics.parquet    article_id, fine_topic, prob
  work/04_coarse_topics.parquet  article_id, coarse_topic
  work/04_topic_info.parquet     per-topic: level, topic_id, size, top_terms, centroid_index
  work/04_centroids.npy          fine-topic centroids (row order = sorted fine topic ids)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import read_table, write_table


def _cluster_level(cfg_level: dict, texts: list[str], embeddings: np.ndarray, seed: int):
    import umap
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer

    umap_model = umap.UMAP(
        n_components=cfg_level["umap_n_components"],
        n_neighbors=cfg_level["umap_n_neighbors"],
        min_dist=cfg_level["umap_min_dist"],
        metric="cosine",
        random_state=seed,
    )
    hdb = HDBSCAN(
        min_cluster_size=cfg_level["hdbscan_min_cluster_size"],
        min_samples=cfg_level["hdbscan_min_samples"],
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    # Thai has no whitespace — c-TF-IDF on char n-grams works surprisingly well for
    # topic keywords across TH/EN mixed corpora; switch to pythainlp tokenizer if preferred.
    vectorizer = CountVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=5, max_features=50_000)
    model = BERTopic(
        umap_model=umap_model,
        hdbscan_model=hdb,
        vectorizer_model=vectorizer,
        top_n_words=20,
        verbose=False,
    )
    topics, probs = model.fit_transform(texts, embeddings)
    return model, np.array(topics), probs


def _reassign_outliers(labels: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
    """Assign HDBSCAN outliers (-1) to the nearest cluster centroid."""
    labels = labels.copy()
    mask = labels == -1
    if not mask.any():
        return labels
    ids = sorted(set(labels) - {-1})
    if not ids:
        labels[mask] = 0
        return labels
    centroids = np.stack([embeddings[labels == t].mean(axis=0) for t in ids])
    centroids /= np.maximum(np.linalg.norm(centroids, axis=1, keepdims=True), 1e-9)
    out = embeddings[mask]
    sim = out @ centroids.T
    labels[mask] = np.array(ids)[sim.argmax(axis=1)]
    return labels


def _centroids(labels: np.ndarray, embeddings: np.ndarray) -> tuple[list[int], np.ndarray]:
    ids = sorted(set(labels))
    c = np.stack([embeddings[labels == t].mean(axis=0) for t in ids])
    c /= np.maximum(np.linalg.norm(c, axis=1, keepdims=True), 1e-9)
    return ids, c.astype(np.float32)


def _top_terms(model, topic_id: int, n: int) -> list[str]:
    words = model.get_topic(topic_id) or []
    return [w for w, _ in words[:n]]


def cluster(cfg: dict, df: pd.DataFrame | None = None, embeddings: np.ndarray | None = None):
    work = Path(cfg["pipeline"]["work_dir"])
    if df is None:
        df = read_table(work / "02_docs.parquet")
    if embeddings is None:
        embeddings = np.load(work / "03_embeddings.npy")
    seed = int(cfg["pipeline"]["seed"])
    texts = df["doc_text"].tolist()

    # ---- fine level ----
    print("[cluster] fine level ...")
    fine_model, fine_labels, _ = _cluster_level(cfg["clustering"]["fine"], texts, embeddings, seed)
    n_raw = len(set(fine_labels) - {-1})
    fine_labels = _reassign_outliers(fine_labels, embeddings)
    fine_ids, fine_cents = _centroids(fine_labels, embeddings)
    print(f"[cluster] fine: {len(fine_ids)} topics (raw {n_raw}, outliers reassigned)")

    # ---- coarse level (on fine centroids — fast & stable) ----
    print("[cluster] coarse level ...")
    coarse_labels_fine = _cluster_level(
        cfg["clustering"]["coarse"],
        texts=[" ".join(_top_terms(fine_model, t, 10)) or f"topic {t}" for t in fine_ids],
        embeddings=fine_cents,
        seed=seed,
    )[1]
    coarse_labels_fine = _reassign_outliers(coarse_labels_fine, fine_cents)
    fine_to_coarse = dict(zip(fine_ids, coarse_labels_fine))
    coarse_labels = np.array([fine_to_coarse[t] for t in fine_labels])
    n_coarse = len(set(coarse_labels))
    print(f"[cluster] coarse: {n_coarse} groups")

    # ---- persist ----
    pd.DataFrame({"article_id": df["article_id"], "fine_topic": fine_labels}).to_parquet(
        work / "04_fine_topics.parquet", index=False)
    pd.DataFrame({"article_id": df["article_id"], "coarse_topic": coarse_labels}).to_parquet(
        work / "04_coarse_topics.parquet", index=False)

    rows = []
    for t in fine_ids:
        rows.append({
            "level": "fine", "topic_id": t,
            "size": int((fine_labels == t).sum()),
            "top_terms": "; ".join(_top_terms(fine_model, t, cfg["clustering"]["ctfidf_top_n"])),
            "coarse_topic": int(fine_to_coarse[t]),
        })
    info = pd.DataFrame(rows)
    write_table(info, work / "04_topic_info.parquet")
    np.save(work / "04_centroids.npy", fine_cents)
    pd.Series(fine_ids).to_json(work / "04_centroid_ids.json")
    print(f"[cluster] saved topic info ({len(info)} fine topics)")
    return fine_labels, coarse_labels
