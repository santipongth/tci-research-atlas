"""Phase 6 — Per-topic trend forecasting with model selection by backtest.

Models: linear (OLS), poisson (GLM via statsmodels), prophet (optional).
Each topic gets the model with the best backtest MAPE on the last N years.
Forecast comes with an interval from residual std (approximate, honest).

Output: work/08_forecasts.parquet
  topic_id, model, backtest_mape, hist_years, hist_counts, fc_years, fc_mean, fc_lo, fc_hi
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import read_table, write_table


def _fit_predict_linear(yrs: np.ndarray, cnt: np.ndarray, future: np.ndarray):
    coef = np.polyfit(yrs, cnt, 1)
    fit = np.polyval(coef, yrs)
    pred = np.polyval(coef, future)
    resid = cnt - fit
    sigma = resid.std(ddof=2) if len(cnt) > 2 else (resid.std() or 1.0)
    return pred, sigma


def _fit_predict_poisson(yrs: np.ndarray, cnt: np.ndarray, future: np.ndarray):
    import statsmodels.api as sm
    X = sm.add_constant(yrs - yrs.mean())
    model = sm.GLM(cnt, X, family=sm.families.Poisson()).fit(disp=0)
    fit = model.predict(X)
    Xf = sm.add_constant(future - yrs.mean())
    pred = np.asarray(model.predict(Xf))
    resid = cnt - np.asarray(fit)
    sigma = resid.std(ddof=2) if len(cnt) > 2 else (resid.std() or 1.0)
    return pred, sigma


def _fit_predict_prophet(yrs: np.ndarray, cnt: np.ndarray, future: np.ndarray):
    from prophet import Prophet
    df = pd.DataFrame({"ds": pd.to_datetime(yrs, format="%Y"), "y": cnt})
    m = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False,
                interval_width=0.95)
    m.fit(df)
    fut = pd.DataFrame({"ds": pd.to_datetime(np.concatenate([yrs, future]), format="%Y")})
    fc = m.predict(fut)
    pred = fc["yhat"].to_numpy()[-len(future):]
    resid = cnt - fc["yhat"].to_numpy()[:len(yrs)]
    sigma = resid.std(ddof=2) if len(cnt) > 2 else (resid.std() or 1.0)
    return np.maximum(pred, 0), sigma


MODELS = {"linear": _fit_predict_linear, "poisson": _fit_predict_poisson, "prophet": _fit_predict_prophet}


def _mape(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - pred) / np.maximum(np.abs(actual), 1.0)) * 100)


def _winsorize(cnt: np.ndarray, q: float) -> np.ndarray:
    hi = np.quantile(cnt, q)
    return np.minimum(cnt, hi)


def forecast(cfg: dict, series: pd.DataFrame | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    if series is None:
        series = read_table(work / "06_series.parquet")
    meta = pd.read_json(work / "06_meta.json", typ="series")
    last_year = int(meta["last_complete_year"])

    fcfg = cfg["forecast"]
    horizon = int(fcfg["horizon"])
    bt = int(fcfg["backtest_years"])
    min_hist = int(fcfg["min_history_years"])
    q = float(fcfg["winsorize_quantile"])

    avail = []
    for name in fcfg["models"]:
        if name in MODELS:
            if name == "prophet":
                try:
                    import prophet  # noqa: F401
                except ImportError:
                    print("[forecast] prophet not installed — skipped")
                    continue
            avail.append(MODELS[name])
    avail_names = [m.__name__.replace("_fit_predict_", "") for m in avail]
    print(f"[forecast] models: {avail_names}, horizon={horizon}y, backtest={bt}y")

    rows = []
    for tid, g in series.groupby("topic_id"):
        g = g.sort_values("year")
        yrs = g["year"].to_numpy(dtype=float)
        cnt = _winsorize(g["count"].to_numpy(dtype=float), q)
        if len(yrs) < min_hist or cnt.sum() == 0:
            continue

        future = np.arange(last_year + 1, last_year + 1 + horizon, dtype=float)

        best = None
        for name, fn in zip(avail_names, avail):
            try:
                # backtest: train ≤ last_year - bt
                tr = yrs <= last_year - bt
                te = ~tr
                if tr.sum() < 3 or te.sum() == 0:
                    pred_te = np.repeat(cnt[tr].mean(), te.sum())
                else:
                    pred_te, _ = fn(yrs[tr], cnt[tr], yrs[te])
                    pred_te = np.maximum(pred_te, 0)
                score = _mape(cnt[te], pred_te)
                # final fit on full history
                pred, sigma = fn(yrs, cnt, future)
                pred = np.maximum(pred, 0)
                if best is None or score < best[1]:
                    best = (name, score, pred, sigma)
            except Exception as e:  # noqa: BLE001 — โมเดลใดพังให้ข้าม ไม่ให้พังทั้ง pipeline
                print(f"[forecast] topic {tid} model {name} failed: {e}")

        if best is None:
            continue
        name, score, pred, sigma = best
        rows.append({
            "topic_id": tid,
            "model": name,
            "backtest_mape": round(score, 2),
            "hist_years": json.dumps([int(y) for y in yrs]),
            "hist_counts": json.dumps([int(c) for c in cnt]),
            "fc_years": json.dumps([int(y) for y in future]),
            "fc_mean": json.dumps([round(float(v), 1) for v in pred]),
            "fc_lo": json.dumps([round(max(float(v) - 1.96 * sigma, 0), 1) for v in pred]),
            "fc_hi": json.dumps([round(float(v) + 1.96 * sigma, 1) for v in pred]),
        })

    out_df = pd.DataFrame(rows)
    out = work / "08_forecasts.parquet"
    write_table(out_df, out)
    if len(out_df):
        print(f"[forecast] {len(out_df)} topics | model mix: "
              f"{out_df['model'].value_counts().to_dict()} | median MAPE={out_df['backtest_mape'].median():.1f}%")
    return out_df
