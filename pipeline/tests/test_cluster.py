import json

import numpy as np
import pandas as pd

from atlas.cluster import assign_outliers, cluster, coarse_groups, merge_similar, relabel_by_size
from atlas.io_utils import read_table, write_table


def blobs(n_per=60, k=5, dim=32, noise=0.05, seed=0):
    rng = np.random.default_rng(seed)
    centers = np.eye(dim)[:k]                                   # orthogonal centres
    X = np.vstack([c + rng.normal(0, noise, (n_per, dim)) for c in centers])
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    return X.astype(np.float32), np.repeat(np.arange(k), n_per)


def test_merge_similar_rejoins_a_split_cluster():
    X, y = blobs()
    labels = y.copy()
    labels[(y == 0) & (np.arange(len(y)) % 2 == 0)] = 9          # split blob 0 in two
    merged = merge_similar(labels, X, threshold=0.8)
    assert len(set(merged[y == 0])) == 1
    assert len(set(merged)) == 5


def test_assign_outliers_respects_threshold():
    X, y = blobs()
    near = X[y == 1][0] * 0.98
    far = np.eye(32)[20].astype(np.float32)                       # orthogonal to every centre
    X2 = np.vstack([X, near / np.linalg.norm(near), far])
    labels = np.concatenate([y, [-1, -1]])
    out = assign_outliers(labels, X2, min_sim=0.35)
    assert out[-2] == 1 and out[-1] == -1


def test_coarse_groups_do_not_collapse():
    e = np.eye(8, dtype=np.float32)
    C = np.vstack([e[0], e[0] * 0.9 + e[7] * 0.1, e[1], e[1] * 0.9 + e[7] * 0.1, e[2], e[2] * 0.9 + e[7] * 0.1])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    g3 = coarse_groups(C, 3)
    assert len(set(g3)) == 3 and g3[0] == g3[1] and g3[2] == g3[3]
    assert len(set(coarse_groups(C, 20))) == 6                    # regression: v1 collapsed to one group


def test_relabel_by_size_largest_is_zero():
    assert relabel_by_size(np.array([5, 5, 2, -1, 5, 2, 7])).tolist() == [0, 0, 1, -1, 0, 1, 2]


def test_cluster_step_on_blobs(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["clustering"].update(reducer="pca", n_groups=3)
    cfg["clustering"]["fine"].update(hdbscan_min_cluster_size=20, hdbscan_min_samples=5)
    X, y = blobs(n_per=80)
    words = ["ข้าว เกษตรกร", "เบาหวาน อินซูลิน", "ท่องเที่ยว โฮมสเตย์", "พลังงาน แสงอาทิตย์", "วรรณกรรม กวีนิพนธ์"]
    work = tmp_path / "work"
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(len(y))],
                              "doc_text": [f"การศึกษา{words[t]}" for t in y],
                              "keywords_th": [words[t].split()[0] for t in y],
                              "keywords_en": [""] * len(y)}), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", X)
    labels = cluster(cfg)
    info = read_table(work / "04_topic_info.parquet")
    assert len(info) == 5 and (labels >= 0).mean() > 0.95
    assert info["coherence"].min() > 0.9
    assert info["coarse_topic"].nunique() == 3
    assert all(info["top_keywords"].str.len() > 0)
    ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    assert ids == sorted(info["topic_id"].tolist()) and np.load(work / "04_centroids.npy").shape == (5, 32)


# ---- F6(b): an all-noise HDBSCAN result is collapsed into one topic only for genuinely tiny corpora
def _all_noise_cfg(make_cfg, tmp_path, monkeypatch, mcs):
    import atlas.cluster as C

    monkeypatch.setattr(C, "hdbscan_labels", lambda red, fine: np.full(len(red), -1))
    cfg = make_cfg(tmp_path)
    cfg["clustering"].update(reducer="pca", n_groups=2)
    cfg["clustering"]["fine"]["hdbscan_min_cluster_size"] = mcs
    X, y = blobs(n_per=4)                                         # 20 documents
    work = tmp_path / "work"
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(len(y))],
                              "doc_text": [f"doc {t} text {i}" for i, t in enumerate(y)],
                              "keywords_th": [""] * len(y), "keywords_en": [f"k{t}" for t in y]}),
                work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", X)
    return cfg


def test_all_noise_tiny_corpus_becomes_one_topic(make_cfg, tmp_path, monkeypatch):
    labels = cluster(_all_noise_cfg(make_cfg, tmp_path, monkeypatch, mcs=20))     # 20 < 2 × 20
    assert set(labels.tolist()) == {0}


def test_all_noise_real_corpus_is_an_error(make_cfg, tmp_path, monkeypatch):
    import pytest

    cfg = _all_noise_cfg(make_cfg, tmp_path, monkeypatch, mcs=5)                  # 20 >= 2 × 5
    with pytest.raises(ValueError, match="hdbscan_min_cluster_size"):
        cluster(cfg)
    assert not (tmp_path / "work" / "04_fine_topics.parquet").exists()
