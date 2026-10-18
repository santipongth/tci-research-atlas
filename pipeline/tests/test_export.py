import json
import math

import pandas as pd

from atlas.config import load_config
from atlas.export import build_atlas, clean_json

META = {"last_complete_year": 2024, "as_of_year": 2026, "trimmed_years": [2025, 2026]}


def _frames():
    info = pd.DataFrame({"topic_id": [0, 1], "size": [30, 10], "top_terms": ["a", "b"], "top_keywords": ["a", "b"],
                         "coarse_topic": [0, 0], "coherence": [0.91, math.nan]})
    labels = pd.DataFrame({"level": "fine", "topic_id": [0, 1], "name_th": ["one_th", "two_th"],
                           "name_en": ["One", "Two"], "description": "", "keywords": "", "cache_key": "fallback"})
    layout = pd.DataFrame([
        {"kind": "group", "id": 0, "x": 10.0, "y": 10.0, "r": 40.0, "parent": -1},
        {"kind": "topic", "id": 0, "x": 5.0, "y": 5.0, "r": 20.0, "parent": 0},
        {"kind": "topic", "id": 1, "x": 15.0, "y": 15.0, "r": 10.0, "parent": 0}])
    edges = pd.DataFrame({"s": [0], "t": [1], "w": [0.7]})
    em = pd.DataFrame({"topic_id": [0, 1], "status": ["EMERGING", "LOW_DATA"], "emerging_score": [80.0, 20.0],
                       "cagr_recent": [0.5, math.nan], "burst_years": ["2023", ""], "share_growth": [0.4, math.nan],
                       "share_growth_lo": [0.2, math.nan], "share_growth_hi": [0.6, math.nan],
                       "n_journals_R": [4, 1], "n_orgs_R": [5, 1], "journal_driven": [False, False],
                       "orgs_unverified": [False, True]})
    hist = json.dumps([2019, 2020, 2021, 2022, 2023, 2024])
    fc = pd.DataFrame({"topic_id": [0, 1], "model": ["linear", "naive"], "backtest_mae": [1.0, 2.0],
                       "backtest_mape": [5.0, 9.0], "mase": [0.5, None], "skill_vs_naive": [0.6, 0.0],
                       "show": [True, False], "hist_years": [hist, hist], "hist_counts": ["[1,2,3,4,5,6]"] * 2,
                       "fc_years": ["[2025,2026]"] * 2, "fc_mean": ["[7,8]"] * 2, "fc_lo": ["[6,7]"] * 2,
                       "fc_hi": ["[8,9]"] * 2})
    return info, labels, layout, edges, em, fc


def test_build_atlas_v11_is_strict_json_and_gated():
    atlas = build_atlas(*_frames(), meta=META, n_articles=50, include_forecast=True, definition_version=3)
    json.dumps(atlas, allow_nan=False)                                   # raises if NaN slipped through
    m = atlas["meta"]
    assert (m["schema_version"], m["definition_version"]) == ("1.1", 3)
    assert (m["as_of_year"], m["trimmed_years"], m["n_orgs_unverified"]) == (2026, [2025, 2026], 1)
    assert (m["total_articles"], m["assigned_articles"], m["unassigned_articles"]) == (50, 40, 10)
    topics = {n["nodeId"]: n for n in atlas["nodes"] if n["kind"] == "topic"}
    assert topics["t0"]["status"] == "EMERGING" and topics["t0"]["forecast"]["fc_mean"] == [7, 8]
    assert topics["t1"]["forecast"] is None and topics["t1"]["forecast_uncertain"] is True
    assert topics["t1"]["coherence"] is None and topics["t1"]["share_growth"] is None
    assert topics["t0"]["orgs_unverified"] is False and topics["t1"]["orgs_unverified"] is True
    assert atlas["links"] == [{"s": "t0", "t": "t1", "w": 0.7}]


def test_clean_json_handles_numpy_and_nan():
    import numpy as np

    assert clean_json({"a": np.float64("nan"), "b": [np.int64(3), np.bool_(True)], "c": float("inf")}) == \
        {"a": None, "b": [3, True], "c": None}


def test_forecast_uncertain_uses_skill_gate_only_and_missing_show_is_not_shown():
    frames = list(_frames())
    atlas = build_atlas(*frames, meta=META, n_articles=50, include_forecast=False, definition_version=3)
    t = {n["nodeId"]: n for n in atlas["nodes"] if n["kind"] == "topic"}
    assert t["t0"]["forecast"] is None and t["t0"]["forecast_uncertain"] is False
    assert t["t1"]["forecast"] is None and t["t1"]["forecast_uncertain"] is True

    fc = frames[5].copy()
    fc["show"] = pd.Series([True, None], dtype=object)
    fc.loc[0, "show"] = math.nan
    frames[5] = fc
    atlas = build_atlas(*frames, meta=META, n_articles=50, include_forecast=True, definition_version=3)
    t = {n["nodeId"]: n for n in atlas["nodes"] if n["kind"] == "topic"}
    assert t["t0"]["forecast"] is None and t["t1"]["forecast"] is None


def _write_work(tmp_path, with_centroids=True):
    import numpy as np

    from atlas.io_utils import write_table

    info, labels, layout, edges, em, fc = _frames()
    work, out, state = tmp_path / "work", tmp_path / "out", tmp_path / "state"
    work.mkdir()
    extra = pd.DataFrame({"level": ["fine", "coarse"], "topic_id": [0, 0], "name_th": ["old_th", "coarse_th"],
                          "name_en": ["Old", "Coarse"], "description": "", "keywords": "", "cache_key": "old"})
    labels = pd.concat([extra.iloc[:1], labels, extra.iloc[1:]], ignore_index=True)   # old dup first, coarse last
    for name, df in [("04_topic_info", info), ("05_labels", labels), ("07_emerging", em), ("08_forecasts", fc),
                     ("09_layout", layout), ("09_edges", edges), ("02_docs", pd.DataFrame({"article_id": range(50)}))]:
        write_table(df, work / f"{name}.parquet")
    (work / "06_meta.json").write_text(json.dumps(META), encoding="utf-8")
    (work / "03_meta.json").write_text(json.dumps({"model_id": "lite|char2-4|svd8", "n": 50, "dim": 8}),
                                       encoding="utf-8")
    write_table(pd.DataFrame({"path": ["x/bad.md"], "error": ["PermissionError: denied"]}),
                work / "01_ingest_errors.parquet")
    if with_centroids:
        np.save(work / "04_centroids.npy", np.zeros((2, 3)))
        (work / "04_centroid_ids.json").write_text("[0, 1]", encoding="utf-8")
    cfg = {"pipeline": {"work_dir": str(work), "output_dir": str(out), "state_dir": str(state)},
           "export": {"formats": ["json", "csv"], "include_forecast_in_json": True},
           "emerging": load_config(None)["emerging"], "embedding": {"provider": "lite"}}
    return cfg, out, state


def test_export_topics_csv_one_row_per_topic_with_latest_fine_label(tmp_path):
    from atlas.export import export

    cfg, out, state = _write_work(tmp_path)
    export(cfg)
    csv = pd.read_csv(out / "topics.csv")
    assert len(csv) == 2 and csv["topic_id"].tolist() == [0, 1]
    assert csv.loc[0, "name_en"] == "One"
    assert (state / "prev" / "centroids.npy").exists() and (state / "prev" / "centroid_ids.json").exists()


def test_export_checks_centroids_before_writing_anything(tmp_path):
    import pytest

    from atlas.export import export

    cfg, out, _ = _write_work(tmp_path, with_centroids=False)
    with pytest.raises(FileNotFoundError, match="04_centroids.npy"):
        export(cfg)
    assert not out.exists() or not any(out.iterdir())


def test_low_data_topic_never_gets_a_forecast():
    frames = list(_frames())
    fc = frames[5].copy()
    fc["show"] = [True, True]                         # t1 passes the skill gate but is LOW_DATA
    frames[5] = fc
    atlas = build_atlas(*frames, meta=META, n_articles=50, include_forecast=True, definition_version=3)
    t = {n["nodeId"]: n for n in atlas["nodes"] if n["kind"] == "topic"}
    assert t["t1"]["status"] == "LOW_DATA"
    assert t["t1"]["forecast"] is None and t["t1"]["forecast_uncertain"] is True
    assert t["t0"]["forecast"] is not None and t["t0"]["forecast_uncertain"] is False


def test_manifest_records_run_provenance(tmp_path):
    from atlas.export import export

    cfg, out, _ = _write_work(tmp_path)
    export(cfg)
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["embedding_provider"] == "lite" and man["embedding_model_id"] == "lite|char2-4|svd8"
    assert man["n_labels_fallback"] == 2                        # latest fine label of each topic is "fallback"
    assert (man["definition_version"], man["ci_level"]) == (3, 0.9)
    assert (man["trimmed_years"], man["as_of_year"]) == ([2025, 2026], 2026)
    assert (man["n_orgs_unverified"], man["ingest_errors"]) == (1, 1)
