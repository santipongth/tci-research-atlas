"""Quarter diff: snapshots in state_dir, fallback to the previous release folder, what changed."""
import json

import pytest

from atlas.config import load_config
from atlas.diff import load_snapshot, make_snapshot, quarter_diff, write_snapshot


def _topic(tid, status, size, share, th="ก"):
    return {"id": tid, "status": status, "size": size, "score": 50.0, "th": th, "en": tid,
            "metrics": {"share_recent": share}}


PREV = make_snapshot("2026Q3", [_topic("T000001", "STABLE", 100, 0.010), _topic("T000002", "HOT", 300, 0.030),
                                _topic("T000003", "DECLINING", 50, 0.004, th="เก่า")],
                     {"articles": 1000, "topics": 3, "journals": 2}, ["so02.A", "so02.B"])
CUR = make_snapshot("2026Q4", [_topic("T000001", "EMERGING", 140, 0.016), _topic("T000002", "HOT", 310, 0.0302),
                               _topic("T000004", "LOW_DATA", 20, 0.001), _topic("T000005", "STABLE", 60, 0.005)],
                    {"articles": 1100, "topics": 4, "journals": 3}, ["so02.A", "so02.B", "so02.C"])


def test_quarter_diff_lists_new_retired_changed_and_movers():
    lineage = {"T000004": {"event": "split", "parents": ["T000003"]}, "T000005": {"event": "new", "parents": []}}
    d = quarter_diff(CUR, PREV, lineage, movers=10, min_share_delta=0.0005)
    assert d["release"] == "2026Q4" and d["previous_release"] == "2026Q3"
    assert d["new_topics"] == [{"topic": "T000004", "event": "split", "parents": ["T000003"]},
                               {"topic": "T000005", "event": "new", "parents": []}]
    assert d["retired"] == [{"topic": "T000003", "th": "เก่า", "en": "T000003", "merged_into": None}]  # split parent
    assert d["restructured"] == []
    assert d["status_changes"] == [{"topic": "T000001", "previous": "STABLE", "current": "EMERGING"}]
    assert [m["topic"] for m in d["movers"]] == ["T000001"]          # T000002 moved 0.0002 < 0.0005
    assert {k["key"]: (k["previous"], k["current"]) for k in d["kpis"]}["articles"] == (1000, 1100)
    assert d["journals_compared"] and d["new_journals"] == ["so02.C"]
    no_j = quarter_diff(CUR, {**PREV, "journals": None}, {}, 10, 0.0)
    assert not no_j["journals_compared"] and no_j["new_journals"] == []
    assert len(quarter_diff(CUR, PREV, {}, movers=1, min_share_delta=0.0)["movers"]) == 1


def test_a_merge_is_visible_not_a_plain_disappearance():
    """T1 + T2 merge into the topic that keeps id T1: T2 is retired *into* T1 and T1 is listed as restructured."""
    prev = make_snapshot("2026Q3", [_topic("T000001", "STABLE", 100, 0.01), _topic("T000002", "STABLE", 80, 0.008)],
                         {"articles": 1000}, None)
    cur = make_snapshot("2026Q4", [_topic("T000001", "STABLE", 180, 0.018)], {"articles": 1000}, None)
    lineage = {"T000001": {"event": "merge", "parents": ["T000001", "T000002"]}}
    d = quarter_diff(cur, prev, lineage, 10, 0.0)
    assert d["new_topics"] == []
    assert d["retired"] == [{"topic": "T000002", "th": "ก", "en": "T000002", "merged_into": "T000001"}]
    assert d["restructured"] == [{"topic": "T000001", "event": "merge", "parents": ["T000001", "T000002"]}]
    gone = quarter_diff(cur, prev, {}, 10, 0.0)                       # no lineage: a plain disappearance
    assert gone["retired"][0]["merged_into"] is None and gone["restructured"] == []


def test_a_split_lists_the_continuing_parent_and_the_new_child():
    prev = make_snapshot("2026Q3", [_topic("T000001", "STABLE", 200, 0.02)], {"articles": 1000}, None)
    cur = make_snapshot("2026Q4", [_topic("T000001", "STABLE", 120, 0.012), _topic("T000003", "STABLE", 80, 0.008)],
                        {"articles": 1000}, None)
    lineage = {"T000001": {"event": "split", "parents": ["T000001"]},
               "T000003": {"event": "split", "parents": ["T000001"]}}
    d = quarter_diff(cur, prev, lineage, 10, 0.0)
    assert d["new_topics"] == [{"topic": "T000003", "event": "split", "parents": ["T000001"]}]
    assert d["restructured"] == [{"topic": "T000001", "event": "split", "parents": ["T000001"]}]
    assert d["retired"] == []


@pytest.fixture
def cfg(tmp_path):
    c = load_config(None)
    c["pipeline"].update(state_dir=str(tmp_path / "state"), output_dir=str(tmp_path / "out"))
    return c


def test_snapshot_round_trip_through_state(cfg):
    write_snapshot(cfg, "2026Q3", PREV)
    snap, source = load_snapshot(cfg, "2026Q3")
    assert source == "state" and snap == json.loads(json.dumps(PREV))


def test_fallback_reads_the_previous_release_folder(cfg, tmp_path):
    folder = tmp_path / "out" / "data" / "2026Q2"
    folder.mkdir(parents=True)
    (folder / "topics.json").write_text(json.dumps({"topics": [_topic("T000001", "HOT", 10, 0.01), {"id": "bad"}]}),
                                        encoding="utf-8")
    (folder / "overview.json").write_text(json.dumps({"kpis": {"articles": 10, "topics": 1}}), encoding="utf-8")
    snap, source = load_snapshot(cfg, "2026Q2")
    assert source == "output" and list(snap["topics"]) == ["T000001"] and snap["journals"] is None
    assert load_snapshot(cfg, "2025Q1") == (None, "")


def _release_folder(tmp_path, release, topics, kpis=None, journals=None):
    folder = tmp_path / "out" / "data" / release
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "topics.json").write_text(json.dumps(topics), encoding="utf-8")
    (folder / "overview.json").write_text(json.dumps({"kpis": kpis or {"articles": 10}}), encoding="utf-8")
    if journals is not None:
        (folder / "journals.json").write_text(json.dumps(journals), encoding="utf-8")
    return folder


def test_the_state_snapshot_wins_over_the_release_folder_and_is_versioned(cfg, tmp_path):
    _release_folder(tmp_path, "2026Q3", {"topics": [_topic("T000009", "HOT", 10, 0.01)]})
    p = write_snapshot(cfg, "2026Q3", PREV)
    assert json.loads(p.read_text(encoding="utf-8"))["schema_version"] == 1
    assert not list(p.parent.glob("*.tmp"))                          # written atomically
    snap, source = load_snapshot(cfg, "2026Q3")
    assert source == "state" and set(snap["topics"]) == {"T000001", "T000002", "T000003"}


@pytest.mark.parametrize("bad", ["{not json", "[]", json.dumps({"release": "2026Q3", "topics": []}),
                                 json.dumps({"release": "2026Q3", "kpis": {}, "topics": {"T000001": {"size": 1}}})])
def test_a_corrupt_snapshot_falls_back_to_the_release_folder(cfg, tmp_path, capsys, bad):
    write_snapshot(cfg, "2026Q3", PREV)
    (tmp_path / "state" / "releases" / "2026Q3" / "snapshot.json").write_text(bad, encoding="utf-8")
    assert load_snapshot(cfg, "2026Q3") == (None, "")                # no folder either → no diff, no crash
    assert "WARNING" in capsys.readouterr().out
    _release_folder(tmp_path, "2026Q3", {"topics": [_topic("T000009", "HOT", 10, 0.01)]})
    snap, source = load_snapshot(cfg, "2026Q3")
    assert source == "output" and list(snap["topics"]) == ["T000009"]


@pytest.mark.parametrize("topics, journals", [
    ({"topics": [{"id": "T000001", "status": "HOT", "size": 3, "metrics": {"count_recent": 3}}]}, None),  # pre-P2
    (["not", "a", "dict"], None),
    ({"topics": [_topic("T000001", "HOT", 10, 0.01)]}, {"journals": [{"key": "so02:A"}]}),             # no id
    ({"topics": [_topic("T000001", "HOT", 10, 0.01)]}, ["x"]),
])
def test_an_unreadable_previous_folder_means_no_diff_never_a_crash(cfg, tmp_path, capsys, topics, journals):
    _release_folder(tmp_path, "2026Q2", topics, journals=journals)
    snap, source = load_snapshot(cfg, "2026Q2")
    if isinstance(journals, list):                                    # a non-dict journals.json: compared without it
        assert source == "output" and snap["journals"] is None
    else:
        assert (snap, source) == (None, "") and "WARNING" in capsys.readouterr().out
