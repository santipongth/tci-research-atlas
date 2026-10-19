import json

import numpy as np
import pandas as pd
import pytest

from atlas.config import load_config
from atlas.forecast import (
    FORECAST_COLUMNS,
    conformal_factors,
    forecast,
    forecast_all,
    month_fraction,
    origins,
    rolling_coverage,
    total_forecast,
)
from atlas.io_utils import read_table, write_table

FCFG = load_config(None)["forecast"]          # tests lock the shipped defaults
YEARS = list(range(2012, 2025))


def _panel(topics: dict[int, list[float]], totals: list[float]):
    rows = [{"topic_id": t, "year": y, "count": int(c)} for t, cs in topics.items() for y, c in zip(YEARS, cs)]
    return pd.DataFrame(rows), pd.Series(dict(zip(YEARS, totals)))


def test_steady_share_trend_is_skilful_and_shown():
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(N[i] * 0.02 * 1.08 ** i) for i in range(13)]}, N)
    rows, meta = forecast_all(s, tot, 2024, FCFG)
    r = rows.iloc[0]
    assert r["model"] != "naive" and r["show"] and r["mase"] < 1 and r["skill_vs_naive"] > 0
    mean, lo80, hi80 = (json.loads(r[k]) for k in ("fc_mean", "fc_lo80", "fc_hi80"))
    lo95, hi95 = json.loads(r["fc_lo95"]), json.loads(r["fc_hi95"])
    assert json.loads(r["fc_years"]) == [2025, 2026] and mean[1] > mean[0] > s["count"].iloc[-1]
    assert all(a <= b <= c <= d for a, b, c, d in zip(lo95, lo80, hi80, hi95))
    assert meta["total_model"] in FCFG["total_models"]


def test_unpredictable_series_is_not_shown():
    rng = np.random.default_rng(3)
    s, tot = _panel({1: list(rng.choice([20, 200], 13))}, [10_000] * 13)
    r = forecast_all(s, tot, 2024, FCFG)[0].iloc[0]
    assert not r["show"]


def test_history_is_raw_and_starts_at_the_first_article():
    cnt = [0, 0, 10, 12, 500, 14, 15, 16, 18, 19, 20, 22, 23]
    r = forecast_all(*_panel({1: cnt}, [5000] * 13), 2024, FCFG)[0].iloc[0]
    assert json.loads(r["hist_years"])[0] == 2014 and 500 in json.loads(r["hist_counts"])


def test_too_short_history_is_skipped():
    s, tot = _panel({1: [0] * 9 + [1, 2, 3, 4]}, [100] * 13)
    assert forecast_all(s, tot, 2024, FCFG)[0].empty


def test_origins_and_total_models():
    assert origins(13, 4, 4) == [8, 9, 10, 11]
    assert origins(6, 4, 4) == [3, 4]
    assert list(total_forecast("drift", np.array([100.0, 110, 120]), 2)) == [130.0, 140.0]
    assert list(total_forecast("naive", np.array([5.0, 7]), 2)) == [7.0, 7.0]


def test_conformal_factor_is_the_finite_sample_quantile():
    q = conformal_factors({1: list(np.arange(1, 21) / 10)}, min_calibration=20)    # scores 0.1 … 2.0
    assert q[1][0.8] == pytest.approx(1.7)                                         # ⌈21·0.8⌉ = 17th smallest
    assert q[1][0.95] == pytest.approx(2.0)
    assert conformal_factors({1: [0.5] * 5}, min_calibration=20)[1][0.95] == pytest.approx(1.959964, rel=1e-5)


def _simulated_panel(seed: int, n_topics: int = 80):
    rng = np.random.default_rng(seed)
    N = np.round(5000 * 1.05 ** np.arange(13))
    topics = {}
    for t in range(n_topics):
        base, b, alpha = rng.uniform(0.002, 0.03), rng.uniform(-0.12, 0.15), rng.uniform(0.0, 0.05)
        mu = N * base * np.exp(b * np.arange(13))
        lam = rng.gamma(1 / alpha, mu * alpha) if alpha > 0 else mu
        topics[t] = list(rng.poisson(lam))
    return _panel(topics, list(N))


def test_80pct_intervals_cover_70_to_90pct_of_held_out_counts():
    s, tot = _simulated_panel(seed=0)
    cov = rolling_coverage(s, tot, 2024, FCFG, n_cuts=3)
    assert cov["n"] == 480                                  # 80 topics × 2 horizons × 3 cut-offs
    assert 0.70 <= cov["coverage80"] <= 0.90 and cov["coverage95"] >= 0.85
    assert cov["n_shown"] > 0 and cov["max_mase_shown"] < 1.0


def test_month_fraction():
    months = pd.DataFrame({"year": [2023] * 12, "month": range(1, 13), "count": [10] * 12})
    assert month_fraction(months, [2023], 3) == pytest.approx(0.25)
    assert month_fraction(months, [2020], 3) == 0.0


def test_forecast_step_writes_v2_columns_and_nowcast(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(n * 0.05) for n in N], 2: [round(n * 0.02 * 1.1 ** i) for i, n in enumerate(N)]}, N)
    s["corpus_total"] = s["year"].map(tot)
    write_table(s, work / "06_series.parquet")
    (work / "06_meta.json").write_text(json.dumps({
        "last_complete_year": 2024, "years": YEARS, "totals": {str(y): int(n) for y, n in tot.items()},
        "partial_totals": {"2025": 400}}), encoding="utf-8")
    months = pd.DataFrame([{"year": y, "month": m, "count": 10} for y in range(2022, 2026) for m in range(1, 13)
                           if y < 2025 or m <= 4])
    write_table(months, work / "06_months.parquet")
    write_table(pd.DataFrame({"topic_id": [1, 2], "year": 2025, "count": [30, 20]}), work / "06_partial_year.parquet")
    out = forecast(cfg)
    assert list(out.columns) == FORECAST_COLUMNS and len(out) == 2
    assert (out["nowcast_year"] == 2025).all() and (out["nowcast_month"] == 4).all()
    assert out.set_index("topic_id")["nowcast_mean"].to_dict() == {1: 90.0, 2: 60.0}       # ytd ÷ (4/12)
    meta = json.loads((work / "08_forecast_meta.json").read_text(encoding="utf-8"))
    assert meta["nowcast"] == {"year": 2025, "as_of_month": 4, "fraction": 0.3333, "ytd": 400, "mean": 1200.0}
    assert read_table(work / "08_forecasts.parquet")["show"].dtype == bool


def test_low_data_topics_get_no_forecast(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(n * 0.05) for n in N], 2: [round(n * 0.03) for n in N]}, N)
    write_table(s, work / "06_series.parquet")
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024, "years": YEARS,
                                                   "totals": {str(y): int(n) for y, n in tot.items()}}),
                                       encoding="utf-8")
    write_table(pd.DataFrame({"topic_id": [1, 2], "status": ["STABLE", "LOW_DATA"]}), work / "07_emerging.parquet")
    assert forecast(cfg)["topic_id"].tolist() == [1]           # no trend claim → no forecast either


def test_non_finite_predictions_never_win_and_no_finite_baseline_means_no_forecast(monkeypatch):
    import atlas.forecast as F  # the fix wave guard (0d37cf7), kept by Forecast v2

    real = F.predict_counts
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(N[i] * 0.02 * 1.08 ** i) for i in range(13)]}, N)

    def nan_for(bad):
        return lambda m, c, n, n_future, *a: np.full(len(n_future), np.nan) if m in bad else real(m, c, n, n_future, *a)

    monkeypatch.setattr(F, "predict_counts", nan_for({"drift", "nb_glm"}))
    r = forecast_all(s, tot, 2024, FCFG)[0].iloc[0]
    assert r["model"] not in ("drift", "nb_glm") and np.isfinite(r["backtest_mae"])
    monkeypatch.setattr(F, "predict_counts", nan_for({"naive"}))
    assert forecast_all(s, tot, 2024, FCFG)[0].empty            # no finite baseline → no skill → no forecast


def test_nb_constants_are_config_keys(monkeypatch):
    import atlas.forecast as F

    nb = F.NbParams.from_cfg({**FCFG, "sigma_floor": 2.0, "dispersion_fallback": 0.7})
    assert F.NbParams.from_cfg(FCFG) == F.NB_DEFAULT
    assert F.nb_sigma(np.array([0.0]), 0.0, nb)[0] == 2.0 and F.nb_sigma(np.array([0.0]), 0.0)[0] == 0.5
    monkeypatch.setattr(F, "nb_trend", lambda *a, **k: (_ for _ in ()).throw(ValueError("x")))
    assert F.dispersion(np.ones(5), np.ones(5), nb) == 0.7 and F.dispersion(np.ones(5), np.ones(5)) == 0.1
    N = [1000.0 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(N[i] * 0.02 * 1.08 ** i) for i in range(13)]}, N)
    narrow = F.forecast_all(s, tot, 2024, FCFG)[0].iloc[0]
    wide = F.forecast_all(s, tot, 2024, {**FCFG, "sigma_floor": 50.0})[0].iloc[0]
    assert json.loads(wide["fc_hi80"])[0] - json.loads(wide["fc_lo80"])[0] > \
        json.loads(narrow["fc_hi80"])[0] - json.loads(narrow["fc_lo80"])[0]
