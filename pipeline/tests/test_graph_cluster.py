import numpy as np
import pytest

from atlas.cluster import fit_labels
from atlas.config import load_config
from atlas.graph_cluster import has_igraph, knn_edges

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
