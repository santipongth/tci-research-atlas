"""Leiden community detection on a kNN graph of the embeddings (the CWTS/OpenAlex style alternative
to UMAP→HDBSCAN). Optional dependency: `uv sync --extra leiden` (python-igraph; wheels for Windows,
macOS and Linux). igraph's built-in Leiden is used (no separate leidenalg package).

Graph: each article links to its k most similar articles (cosine), weight = cosine; the graph is
made undirected (an edge kept once, maximum weight). Modularity Leiden with `resolution`;
communities smaller than min_cluster_size become −1 (unassigned), like HDBSCAN noise. Python's
`random` module drives igraph's RNG, so seeding it makes runs reproducible.

Memory: the kNN search multiplies a block of rows by all n vectors; the block has knn_chunk(n) rows so one
block holds at most KNN_CHUNK_ELEMENTS similarities (~256 MB of float32) whatever the corpus size. It is a
memory bound only — every row's neighbours are the same for any block size.
"""
from __future__ import annotations

import random

import numpy as np

KNN_CHUNK_ELEMENTS = 2 ** 26       # similarities per block (chunk rows × n); memory only, never changes results
KNN_MIN_CHUNK = 64


def has_igraph() -> bool:
    try:
        import igraph  # noqa: F401
    except ImportError:
        return False
    return True


def knn_chunk(n: int) -> int:
    """Rows per block of the n × n similarity search: max(64, 2**26 // n) — 64 rows at 1M articles."""
    return max(KNN_MIN_CHUNK, KNN_CHUNK_ELEMENTS // max(int(n), 1))


def knn_edges(emb: np.ndarray, k: int, chunk: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """→ (edges [m, 2] with i < j, weights [m]) of the symmetrised kNN graph (chunk: rows per block,
    default knn_chunk(n))."""
    n = len(emb)
    chunk = int(chunk or knn_chunk(n))
    k = max(1, min(k, n - 1))
    src, dst, w = [], [], []
    for s in range(0, n, chunk):
        sim = emb[s:s + chunk] @ emb.T
        rows = np.arange(s, min(s + chunk, n))
        sim[np.arange(len(rows)), rows] = -np.inf                     # no self loops
        idx = np.argpartition(-sim, k - 1, axis=1)[:, :k]
        src.append(np.repeat(rows, k))
        dst.append(idx.ravel())
        w.append(np.take_along_axis(sim, idx, axis=1).ravel())
    a, b, wt = np.concatenate(src), np.concatenate(dst), np.concatenate(w)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    key = lo.astype(np.int64) * n + hi
    order = np.lexsort((-wt, key))                                    # per pair, keep the largest weight
    key, lo, hi, wt = key[order], lo[order], hi[order], wt[order]
    first = np.r_[True, key[1:] != key[:-1]]
    return np.stack([lo[first], hi[first]], axis=1), np.maximum(wt[first], 0.0)


def leiden_labels(emb: np.ndarray, lcfg: dict, seed: int) -> np.ndarray:
    import igraph as ig  # optional dependency

    if len(emb) < 3:
        return np.zeros(len(emb), dtype=int)
    edges, weights = knn_edges(emb, int(lcfg["k"]))
    g = ig.Graph(n=len(emb), edges=edges.tolist(), directed=False)
    state = random.getstate()                  # igraph draws from the global RNG: seed it, then give it back
    random.seed(seed)
    try:
        part = g.community_leiden(objective_function="modularity", weights=weights.tolist(),
                                  resolution=float(lcfg["resolution"]), n_iterations=int(lcfg["n_iterations"]))
    finally:
        random.setstate(state)
    labels = np.asarray(part.membership, dtype=int)
    sizes = np.bincount(labels)
    labels[sizes[labels] < int(lcfg["min_cluster_size"])] = -1
    return labels
