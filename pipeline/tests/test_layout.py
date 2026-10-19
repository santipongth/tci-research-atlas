import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.layout import galaxy_coords, layout, procrustes_fit


def test_procrustes_recovers_rotation_scale_and_shift():
    rng = np.random.default_rng(0)
    A = rng.normal(size=(12, 2))
    th = 0.7
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    B = 3.0 * A @ R + np.array([100.0, 50.0])
    s, R2, t = procrustes_fit(A, B)
    assert np.allclose(s * A @ R2 + t, B, atol=1e-6)


def test_galaxy_is_deterministic_and_inside_the_topic_circle():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(50, 8))
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    c = X.mean(axis=0) / np.linalg.norm(X.mean(axis=0))
    gx, gy = galaxy_coords(X, c, 500.0, 300.0, 40.0)
    gx2, gy2 = galaxy_coords(X.copy(), c, 500.0, 300.0, 40.0)
    assert np.array_equal(gx, gx2) and np.array_equal(gy, gy2)
    assert (np.hypot(gx - 500, gy - 300) <= 40.0).all()
    closest = int(np.argmax(X @ c))                       # the most central article sits nearest the centre
    assert np.hypot(gx[closest] - 500, gy[closest] - 300) == np.hypot(gx - 500, gy - 300).min()
    assert galaxy_coords(X[:1], c, 1.0, 2.0, 5.0) == (np.array([1.0]), np.array([2.0]))


def _work(cfg, k: int, seed: int = 0):
    """k topics (ids 1..k) of 30 articles around distinct directions in 32-D."""
    rng = np.random.default_rng(seed)
    dirs = np.random.default_rng(42).normal(size=(k, 32))
    X = np.vstack([d + rng.normal(0, 0.3, (30, 32)) for d in dirs])
    X = (X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32)
    labels = np.repeat(np.arange(1, k + 1), 30)
    C = np.stack([X[labels == t].mean(axis=0) for t in range(1, k + 1)])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    work = Path(cfg["pipeline"]["work_dir"])
    ids = [f"a{i}" for i in range(len(X))]
    write_table(pd.DataFrame({"article_id": ids}), work / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": ids, "fine_topic": labels}), work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"topic_id": range(1, k + 1), "size": 30, "coarse_topic": [t % 3 for t in range(k)]}),
                work / "04_topic_info.parquet")
    np.save(work / "03_embeddings.npy", X)
    np.save(work / "04_centroids.npy", C.astype(np.float32))
    (work / "04_centroid_ids.json").write_text(json.dumps(list(range(1, k + 1))), encoding="utf-8")


def _positions(tmp_path) -> dict[int, tuple[float, float]]:
    lay = read_table(tmp_path / "work" / "09_layout.parquet")
    return {int(r.id): (r.x, r.y) for r in lay[lay["kind"] == "topic"].itertuples()}


def test_layout_is_stable_across_releases_and_writes_galaxy(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q1"
    _work(cfg, k=12)
    layout(cfg)
    p1 = _positions(tmp_path)
    galaxy = read_table(tmp_path / "work" / "09_galaxy.parquet")
    assert len(galaxy) == 360 and set(galaxy["topic_id"]) == set(range(1, 13))
    assert (tmp_path / "state" / "releases" / "2026Q1" / "layout.parquet").exists()

    cfg["pipeline"]["release"] = "2026Q2"
    _work(cfg, k=13, seed=1)                                   # one new topic, every article re-sampled
    layout(cfg)
    p2 = _positions(tmp_path)
    moved = np.array([np.hypot(p2[t][0] - p1[t][0], p2[t][1] - p1[t][1]) for t in p1])
    assert np.median(moved) < 0.05 * cfg["layout"]["view_w"]
    W, H = cfg["layout"]["view_w"], cfg["layout"]["view_h"]
    assert all(90 <= x <= W - 90 and 90 <= y <= H - 90 for x, y in p2.values())


def test_layout_without_previous_release_fills_the_view(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q1"
    cfg["layout"]["galaxy"] = False
    _work(cfg, k=6)
    layout(cfg)
    xs = [x for x, _ in _positions(tmp_path).values()]
    assert min(xs) == 90.0 and max(xs) == cfg["layout"]["view_w"] - 90.0
    assert not (tmp_path / "work" / "09_galaxy.parquet").exists()
