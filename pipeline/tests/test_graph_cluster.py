import numpy as np
import pytest

from atlas.cluster import fit_labels
from atlas.config import load_config
from atlas.graph_cluster import KNN_CHUNK_ELEMENTS, has_igraph, knn_chunk, knn_edges

CCFG = load_config(None)["clustering"]


def _blobs(k=5, n_per=60, seed=0):
    rng = np.random.default_rng(seed)
    X = np.vstack([np.eye(32)[c] + rng.normal(0, 0.05, (n_per, 32)) for c in range(k)])
    return (X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32), np.repeat(np.arange(k), n_per)


def test_knn_edges_are_undirected_unique_and_without_self_loops():
    X, _ = _blobs(k=2, n_per=10)
    edges, w = knn_edges(X, k=3)
    assert (edges[:, 0] < edges[:, 1]).all()
    assert len({tuple(e) for e in edges.tolist()}) == len(edges)
    assert len(w) == len(edges) and (w >= 0).all()


def test_knn_chunk_shrinks_with_n_so_one_block_stays_bounded():
    # a block of the similarity matrix is chunk × n floats: it must not grow with the corpus (500K+ articles)
    assert knn_chunk(1_000) >= 1_000                                  # small corpus: one block
    big = [knn_chunk(n) for n in (100_000, 500_000, 1_000_000, 4_000_000)]
    assert big == sorted(big, reverse=True) and big[-1] == 64         # floor of 64 rows
    for n in (100_000, 500_000, 1_000_000):
        assert knn_chunk(n) * n <= KNN_CHUNK_ELEMENTS
    assert knn_chunk(500_000) * 500_000 * 4 <= 2 ** 28                 # ≤ 256 MB of float32 per block (was 4 GB)


def test_knn_edges_do_not_depend_on_the_chunk_size():
    X, _ = _blobs(k=3, n_per=20)
    e1, w1 = knn_edges(X, k=4)
    e2, w2 = knn_edges(X, k=4, chunk=7)
    assert np.array_equal(e1, e2) and np.allclose(w1, w2)


@pytest.mark.skipif(not has_igraph(), reason="optional extra: uv sync --extra leiden")
def test_leiden_recovers_blobs_and_is_reproducible():
    from sklearn.metrics import adjusted_rand_score

    X, y = _blobs()
    ccfg = {**CCFG, "algorithm": "leiden", "leiden": {**CCFG["leiden"], "k": 10, "min_cluster_size": 20}}
    a, n_raw = fit_labels(X, ccfg, seed=1)
    b, _ = fit_labels(X, ccfg, seed=1)
    assert n_raw >= 5 and adjusted_rand_score(y, a) > 0.95 and (a == b).all()


@pytest.mark.skipif(not has_igraph(), reason="optional extra: uv sync --extra leiden")
def test_leiden_small_communities_become_unassigned():
    from atlas.graph_cluster import leiden_labels

    X, _ = _blobs(k=3, n_per=30)
    labels = leiden_labels(X, {**CCFG["leiden"], "k": 8, "min_cluster_size": 1000}, seed=0)
    assert (labels == -1).all()


@pytest.mark.skipif(not has_igraph(), reason="optional extra: uv sync --extra leiden")
def test_leiden_leaves_the_callers_random_state_alone():
    import random

    from atlas.graph_cluster import leiden_labels

    X, _ = _blobs(k=3, n_per=30)
    random.seed(123)
    expected = [random.random() for _ in range(3)]
    random.seed(123)
    leiden_labels(X, {**CCFG["leiden"], "k": 8, "min_cluster_size": 5}, seed=7)
    assert [random.random() for _ in range(3)] == expected
