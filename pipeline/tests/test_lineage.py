import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.cluster import cluster
from atlas.io_utils import read_table, write_table
from atlas.lineage import assign_to_previous, kept_fraction, match_topics, topic_code, update_registry


def _assign(spec: dict[int, int], start: int = 0) -> pd.DataFrame:
    """{topic: n_articles} → article_id/topic_id rows with consecutive ids a{start}…"""
    rows, i = [], start
    for t, n in spec.items():
        for _ in range(n):
            rows.append({"article_id": f"a{i}", "topic_id": t})
            i += 1
    return pd.DataFrame(rows)


def _events(ev: pd.DataFrame) -> dict[int, tuple[str, str]]:
    return {int(r.topic_id): (r.event, r.parents) for r in ev.itertuples()}


def test_continue_new_and_retired():
    prev = _assign({1: 20, 2: 20, 3: 20})
    cur = prev.copy()
    cur["topic_id"] = cur["topic_id"].map({1: 0, 2: 1, 3: -1})          # topic 3's articles now unassigned
    cur = pd.concat([cur, _assign({2: 15}, start=100)])                  # a brand-new cluster of new articles
    mapping, ev, nxt = match_topics(prev, cur, {}, {}, next_id=4, containment=0.5, min_shared=5)
    assert mapping == {0: 1, 1: 2, 2: 4} and nxt == 5
    assert _events(ev) == {1: ("continue", ""), 2: ("continue", ""), 4: ("new", ""), 3: ("retired", "")}


def test_split_keeps_id_for_the_larger_child():
    prev = _assign({7: 40})
    cur = prev.copy()
    cur["topic_id"] = [0] * 25 + [1] * 15
    mapping, ev, _ = match_topics(prev, cur, {}, {}, next_id=8, containment=0.5, min_shared=5)
    assert mapping == {0: 7, 1: 8}
    assert _events(ev) == {7: ("split", "7"), 8: ("split", "7")}


def test_merge_takes_the_id_of_the_main_source():
    prev = _assign({1: 30, 2: 20})
    cur = prev.assign(topic_id=0)
    mapping, ev, _ = match_topics(prev, cur, {}, {}, next_id=3, containment=0.5, min_shared=5)
    assert mapping == {0: 1}
    assert _events(ev) == {1: ("merge", "1;2")}
    reg = update_registry(pd.DataFrame({"topic_id": [1, 2], "born": "2026Q1", "status": "active",
                                        "last_seen": "2026Q1"}), [1], ev, "2026Q2")
    assert reg.set_index("topic_id")["status"].to_dict() == {1: "active", 2: "merged"}
    assert reg.set_index("topic_id").loc[1, "born"] == "2026Q1"


def test_cosine_breaks_ties_between_equal_overlaps():
    prev = _assign({1: 10, 2: 10})
    cur = prev.assign(topic_id=0)                                         # equal overlap 10 vs 10
    e = np.eye(3)
    mapping, _, _ = match_topics(prev, cur, {1: e[0], 2: e[1]}, {0: e[1]}, 3, 0.5, 5)
    assert mapping == {0: 2}                                              # topic 2 points the same way


def test_tiny_overlap_is_not_an_edge():
    prev = _assign({1: 50})
    cur = pd.concat([prev.iloc[:3].assign(topic_id=0), _assign({0: 30}, start=100)])
    mapping, ev, _ = match_topics(prev, cur, {}, {}, 2, 0.5, 5)           # 3 shared < min_shared 5
    assert mapping == {0: 2} and set(ev["event"]) == {"new", "retired"}


def test_assign_mode_keeps_old_and_places_new_articles():
    emb = np.array([[1, 0], [1, 0.1], [0, 1], [0.1, 1], [0.95, 0.05], [-1, 0]], dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    ids = pd.Series([f"a{i}" for i in range(6)])
    prev = pd.DataFrame({"article_id": ["a0", "a1", "a2", "a3"], "topic_id": [5, 5, 9, 9]})
    labels, n_new, n_lost = assign_to_previous(ids, emb, prev, min_sim=0.35)
    assert labels.tolist() == [5, 5, 9, 9, 5, -1] and (n_new, n_lost) == (2, 1)


def test_codes_and_kept_fraction():
    assert topic_code(123) == "T000123"
    assert kept_fraction({1, 2, 3, 4}, {1, 2, 3, 9}) == 0.75 and kept_fraction(set(), {1}) == 1.0


def _blob_work(cfg, n_per=60, k=4, extra=0, seed=0):
    rng = np.random.default_rng(seed)
    X = np.vstack([np.eye(16)[c] + rng.normal(0, 0.05, (n_per, 16)) for c in range(k)]
                  + ([np.eye(16)[0] + rng.normal(0, 0.05, (extra, 16))] if extra else []))
    X = (X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32)
    n = len(X)
    work = Path(cfg["pipeline"]["work_dir"])
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(n)], "doc_text": ["ข้าว เกษตรกร"] * n,
                              "keywords_th": ["ข้าว"] * n, "keywords_en": [""] * n}), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", X)
    (work / "03_meta.json").write_text(json.dumps({"model_id": "fake|1", "n": n, "dim": 16}), encoding="utf-8")


def _cfg(make_cfg, tmp_path, release, mode="auto"):
    cfg = make_cfg(tmp_path)
    cfg["clustering"].update(reducer="pca", n_groups=2)
    cfg["clustering"]["fine"].update(hdbscan_min_cluster_size=20, hdbscan_min_samples=5)
    cfg["pipeline"]["release"] = release
    cfg["topics"]["mode"] = mode
    return cfg


def test_cluster_step_keeps_ids_across_releases(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path, "2026Q1")
    _blob_work(cfg)
    first = cluster(cfg)
    work = tmp_path / "work"
    ids1 = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    assert ids1 == [1, 2, 3, 4] and set(read_table(work / "04_lineage.parquet")["event"]) == {"new"}

    cfg = _cfg(make_cfg, tmp_path, "2026Q2")                                     # auto → assign
    _blob_work(cfg, extra=10)
    second = cluster(cfg)
    meta = json.loads((work / "04_topics_meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "assign" and meta["kept_fraction"] == 1.0 and meta["previous_release"] == "2026Q1"
    assert (second[:len(first)] == first).all() and set(second[len(first):]) == {first[0]}

    cfg = _cfg(make_cfg, tmp_path, "2026Q3", mode="fit")                         # forced refit → matched
    _blob_work(cfg, extra=10, seed=1)
    cluster(cfg)
    meta = json.loads((work / "04_topics_meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "fit" and meta["kept_fraction"] == 1.0 and meta["events"]["continue"] == 4

    again = cluster(cfg)                                                          # same release re-run: idempotent
    assert json.loads((work / "04_topics_meta.json").read_text(encoding="utf-8")) == meta
    assert (tmp_path / "state" / "releases" / "2026Q3" / "topics" / "assignments.parquet").exists()
    assert len(set(again.tolist())) == 4


def test_embedding_model_change_forces_refit(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path, "2026Q1")
    _blob_work(cfg)
    cluster(cfg)
    cfg = _cfg(make_cfg, tmp_path, "2026Q2")
    _blob_work(cfg)
    (tmp_path / "work" / "03_meta.json").write_text(json.dumps({"model_id": "other|2", "n": 240, "dim": 16}),
                                                   encoding="utf-8")
    cluster(cfg)
    meta = json.loads((tmp_path / "work" / "04_topics_meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "fit" and meta["kept_fraction"] == 1.0
