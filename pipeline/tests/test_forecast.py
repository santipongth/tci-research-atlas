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
    nowcast_month,
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
        "last_complete_year": 2024, "as_of_year": 2025, "years": YEARS,
        "totals": {str(y): int(n) for y, n in tot.items()}, "partial_totals": {"2025": 400}}), encoding="utf-8")
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



# ---------------------------------------------------------------- fix round (Opus review of Forecast v2)
def _poisson_panel(seed: int, n_topics: int):
    rng = np.random.default_rng(seed)
    N = np.round(5000 * 1.05 ** np.arange(13))
    topics = {t: list(rng.poisson(N * rng.uniform(0.002, 0.03) * np.exp(rng.uniform(-0.12, 0.15) * np.arange(13))))
              for t in range(n_topics)}
    return _panel(topics, list(N))


def test_intervals_are_calibrated_on_the_honest_errors():
    # one 13-year topic: origins 8..11; honest points = origins 9..11 (the first only seeds the choice)
    N = [1000 * 1.05 ** i for i in range(13)]
    _, meta = forecast_all(*_panel({1: [round(N[i] * 0.02 * 1.08 ** i) for i in range(13)]}, N), 2024, FCFG)
    assert meta["n_calibration"] == {"1": 3, "2": 2}            # the chosen model's own CV errors gave 4 / 3
    # calibrated on the errors of the model picked for scoring best on them, 80% intervals covered 0.696 here
    cov = rolling_coverage(*_poisson_panel(seed=2, n_topics=40), 2024, FCFG, n_cuts=3)
    assert 0.70 <= cov["coverage80"] <= 0.90 and cov["coverage95"] >= 0.90


def test_a_forecast_needs_enough_honest_points_to_be_shown():
    N = [1000 * 1.05 ** i for i in range(13)]
    trend = [round(N[i] * 0.02 * 1.08 ** i) for i in range(13)]
    six, seven = [0] * 7 + trend[7:], [0] * 6 + trend[6:]      # 6 years → 1 honest point, 7 years → 3
    rows = forecast_all(*_panel({6: six, 7: seven}, N), 2024, FCFG)[0].set_index("topic_id")
    assert not rows.loc[6, "show"] and rows.loc[7, "show"]
    loose = forecast_all(*_panel({6: six}, N), 2024, {**FCFG, "min_honest_points": 1})[0]
    assert loose.iloc[0]["show"]                               # only the honest-point gate holds it back


def test_total_model_choice_has_no_look_ahead_on_a_boom_then_drop_corpus():
    def shown(N, seed=7, n=100):
        rng = np.random.default_rng(seed)
        topics = {t: list(rng.poisson(rng.uniform(0.003, 0.02) * np.exp(np.cumsum(rng.normal(0, 0.15, 13))) * N))
                  for t in range(n)}                           # random-walk shares: no real skill to find
        return int(forecast_all(*_panel(topics, list(N)), 2024, FCFG)[0]["show"].sum())

    steady = np.round(5000 * 1.05 ** np.arange(13))
    boom_drop = np.round(np.r_[3000 * 1.10 ** np.arange(9), 3000 * 1.10 ** 8 * 0.85 ** np.arange(1, 5)])
    # a total model picked with hindsight on every year inflated share-model skill here (25 shown vs 20 steady)
    assert shown(boom_drop) <= shown(steady)


def test_a_failing_full_history_fit_falls_back_to_naive_and_is_not_shown(monkeypatch, capsys):
    import atlas.forecast as F

    real = F.predict_counts
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(N[i] * 0.02 * 1.08 ** i) for i in range(13)]}, N)

    def final_fit_fails(m, c, n, n_future, *a):
        if m != "naive" and len(c) == 13:                      # backtests train on ≤ 12 years; only the final fit
            raise ValueError("did not converge")
        return real(m, c, n, n_future, *a)

    monkeypatch.setattr(F, "predict_counts", final_fit_fails)
    r = F.forecast_all(s, tot, 2024, FCFG)[0].iloc[0]
    assert r["model"] == "naive" and not r["show"] and json.loads(r["fc_mean"]) == [float(s["count"].iloc[-1])] * 2
    assert "published as naive" in capsys.readouterr().out


def test_nowcast_month_skips_tiny_months_and_stops_at_the_snapshot():
    m = pd.DataFrame({"year": 2024, "month": [1, 2, 3, 4, 12], "count": [75, 75, 75, 75, 1]})
    assert nowcast_month(m, 0.02, 12) == 4                     # one forward-dated December article is ignored
    assert nowcast_month(m, 0.0, 12) == 12 and nowcast_month(m, 0.02, 3) == 3
    assert nowcast_month(m.iloc[0:0], 0.02, 12) == 0


def _nowcast_run(make_cfg, tmp_path, as_of_year, last, months_extra, partial, partial_totals, **nc):
    cfg = make_cfg(tmp_path)
    cfg["forecast"]["nowcast"].update(nc)
    work = tmp_path / "work"
    years = list(range(2012, last + 1))
    write_table(pd.DataFrame([{"topic_id": 1, "year": y, "count": 50} for y in years]), work / "06_series.parquet")
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": last, "as_of_year": as_of_year, "years": years,
                                                   "totals": {str(y): 1000 for y in years},
                                                   "partial_totals": partial_totals}), encoding="utf-8")
    months = [{"year": y, "month": m, "count": 83} for y in range(last - 3, last + 1) for m in range(1, 13)]
    write_table(pd.DataFrame(months + months_extra), work / "06_months.parquet")
    write_table(pd.DataFrame(partial), work / "06_partial_year.parquet")
    out = forecast(cfg)
    return json.loads((work / "08_forecast_meta.json").read_text(encoding="utf-8"))["nowcast"], out


def test_no_nowcast_for_a_year_the_backfill_guard_trimmed(make_cfg, tmp_path, capsys):
    # run in 2025: 2024 is calendar-complete but lagging, so the v3 guard trimmed it (last complete = 2023)
    nc, out = _nowcast_run(make_cfg, tmp_path, 2025, 2023,
                           [{"year": 2024, "month": m, "count": 37} for m in range(1, 13)]
                           + [{"year": 2025, "month": m, "count": 22} for m in range(1, 10)],
                           [{"topic_id": 1, "year": 2024, "count": 22}, {"topic_id": 1, "year": 2025, "count": 10}],
                           {"2024": 450, "2025": 200})
    assert nc is None and out["nowcast_mean"].isna().all()     # was: 2024 "as of December", 450 articles
    assert "not the running year 2025" in capsys.readouterr().out


def test_nowcast_ignores_a_forward_dated_month_and_a_wrong_year_as_of(make_cfg, tmp_path, capsys):
    extra = [{"year": 2024, "month": m, "count": 75} for m in range(1, 5)] + [{"year": 2024, "month": 12, "count": 1}]
    args = (2024, 2023, extra, [{"topic_id": 1, "year": 2024, "count": 15}], {"2024": 301})
    nc, out = _nowcast_run(make_cfg, tmp_path, *args)
    assert nc == {"year": 2024, "as_of_month": 4, "fraction": 0.3333, "ytd": 301, "mean": 903.0}   # was: 12 → 301
    assert out.iloc[0]["nowcast_mean"] == 45.0
    nc, _ = _nowcast_run(make_cfg, tmp_path, *args, as_of="2023-06")
    assert nc["as_of_month"] == 4 and "as_of=2023-06 is not in the partial year 2024" in capsys.readouterr().out
    nc, _ = _nowcast_run(make_cfg, tmp_path, *args, as_of="2024-06")
    assert nc["as_of_month"] == 6                              # an as_of in the partial year is used as given


def test_nowcast_month_is_capped_at_the_recorded_snapshot_not_today(make_cfg, tmp_path):
    # snapshot April 2024 (recorded at cluster/series time); the data already holds months up to September
    extra = [{"year": 2024, "month": m, "count": 75} for m in range(1, 10)]
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    work.mkdir(parents=True, exist_ok=True)
    years = list(range(2012, 2024))
    write_table(pd.DataFrame([{"topic_id": 1, "year": y, "count": 50} for y in years]), work / "06_series.parquet")
    (work / "06_meta.json").write_text(json.dumps({
        "last_complete_year": 2023, "as_of_year": 2024, "snapshot_at": "2024-04-15T10:00:00+07:00", "years": years,
        "totals": {str(y): 1000 for y in years}, "partial_totals": {"2024": 675}}), encoding="utf-8")
    months = [{"year": y, "month": m, "count": 83} for y in range(2020, 2024) for m in range(1, 13)]
    write_table(pd.DataFrame(months + extra), work / "06_months.parquet")
    write_table(pd.DataFrame([{"topic_id": 1, "year": 2024, "count": 30}]), work / "06_partial_year.parquet")
    forecast(cfg)
    nc = json.loads((work / "08_forecast_meta.json").read_text(encoding="utf-8"))["nowcast"]
    assert nc["as_of_month"] == 4                             # was 9: the cap came from today's date
