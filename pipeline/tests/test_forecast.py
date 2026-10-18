import json

import numpy as np

from atlas.forecast import forecast_topic

YRS = np.arange(2015, 2025)
MODELS = ["naive", "linear", "poisson"]


def test_linear_trend_is_skilful_and_shown():
    r = forecast_topic(YRS, np.arange(10, 110, 10), 2024, 2, 3, MODELS, 0.0)
    assert r["model"] == "linear" and r["show"] is True and r["skill_vs_naive"] == 1.0
    assert json.loads(r["fc_mean"]) == [110.0, 120.0]


def test_unpredictable_jump_is_not_shown():
    r = forecast_topic(YRS, np.array([100] * 7 + [100, 300, 100]), 2024, 2, 3, MODELS, 0.0)
    assert r["model"] == "naive" and r["show"] is False          # nothing beats "same as last year"


def test_history_is_raw_not_winsorized():
    cnt = np.array([10, 12, 500, 14, 15, 16, 18, 19, 20, 22])
    assert 500 in json.loads(forecast_topic(YRS, cnt, 2024, 2, 3, MODELS, 0.0)["hist_counts"])


def test_too_short_history_returns_none():
    assert forecast_topic(np.arange(2021, 2025), np.array([1, 2, 3, 4]), 2024, 2, 3, MODELS, 0.0) is None
