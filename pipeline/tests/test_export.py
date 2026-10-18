import json
import math

import pandas as pd

from atlas.export import build_atlas, clean_json


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
                       "n_journals_R": [4, 1], "n_orgs_R": [5, 1], "journal_driven": [False, False]})
    hist = json.dumps([2019, 2020, 2021, 2022, 2023, 2024])
    fc = pd.DataFrame({"topic_id": [0, 1], "model": ["linear", "naive"], "backtest_mae": [1.0, 2.0],
                       "backtest_mape": [5.0, 9.0], "mase": [0.5, None], "skill_vs_naive": [0.6, 0.0],
                       "show": [True, False], "hist_years": [hist, hist], "hist_counts": ["[1,2,3,4,5,6]"] * 2,
                       "fc_years": ["[2025,2026]"] * 2, "fc_mean": ["[7,8]"] * 2, "fc_lo": ["[6,7]"] * 2,
                       "fc_hi": ["[8,9]"] * 2})
    return info, labels, layout, edges, em, fc


def test_build_atlas_v11_is_strict_json_and_gated():
    atlas = build_atlas(*_frames(), meta={"last_complete_year": 2024}, n_articles=50, include_forecast=True)
    json.dumps(atlas, allow_nan=False)                                   # raises if NaN slipped through
    m = atlas["meta"]
    assert (m["schema_version"], m["definition_version"]) == ("1.1", 2)
    assert (m["total_articles"], m["assigned_articles"], m["unassigned_articles"]) == (50, 40, 10)
    topics = {n["nodeId"]: n for n in atlas["nodes"] if n["kind"] == "topic"}
    assert topics["t0"]["status"] == "EMERGING" and topics["t0"]["forecast"]["fc_mean"] == [7, 8]
    assert topics["t1"]["forecast"] is None and topics["t1"]["forecast_uncertain"] is True
    assert topics["t1"]["coherence"] is None and topics["t1"]["share_growth"] is None
    assert atlas["links"] == [{"s": "t0", "t": "t1", "w": 0.7}]


def test_clean_json_handles_numpy_and_nan():
    import numpy as np

    assert clean_json({"a": np.float64("nan"), "b": [np.int64(3), np.bool_(True)], "c": float("inf")}) == \
        {"a": None, "b": [3, True], "c": None}
