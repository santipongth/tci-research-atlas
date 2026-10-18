"""Per-topic forecast (P0): naive / linear / Poisson, chosen by backtest MAE, skill-gated.

skill = 1 − MAE(best) / MAE(naive) over the last `backtest_years`. A forecast is SHOWN only
when the best model is not naive and skill > forecast.min_skill; otherwise the web says
"แนวโน้มไม่แน่นอน". History is exported raw (v1 winsorised it, which distorted charts).
Forecast v2 (share × total, NB/ETS, rolling-origin CV, conformal intervals) arrives in P1.
Output: work/08_forecasts
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table

FORECAST_COLUMNS = ["topic_id", "model", "backtest_mae", "backtest_mape", "mase", "skill_vs_naive", "show",
                    "hist_years", "hist_counts", "fc_years", "fc_mean", "fc_lo", "fc_hi"]


def _fit_predict_naive(yrs, cnt, future):
    d = np.diff(cnt)
    sigma = float(d.std(ddof=1)) if len(d) > 1 else 1.0
    return np.repeat(float(cnt[-1]), len(future)), sigma


def _fit_predict_linear(yrs, cnt, future):
    coef = np.polyfit(yrs, cnt, 1)
    resid = cnt - np.polyval(coef, yrs)
    sigma = float(resid.std(ddof=2)) if len(cnt) > 2 else 1.0
    return np.polyval(coef, future), sigma


def _fit_predict_poisson(yrs, cnt, future):
    import statsmodels.api as sm

    X = sm.add_constant(yrs - yrs.mean(), has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.GLM(cnt, X, family=sm.families.Poisson()).fit()
    resid = cnt - np.asarray(model.predict(X))
    sigma = float(resid.std(ddof=2)) if len(cnt) > 2 else 1.0
    Xf = sm.add_constant(future - yrs.mean(), has_constant="add")
    return np.asarray(model.predict(Xf)), sigma


MODELS = {"naive": _fit_predict_naive, "linear": _fit_predict_linear, "poisson": _fit_predict_poisson}


def _mae(a, p) -> float:
    return float(np.mean(np.abs(a - p)))


def _mape(a, p) -> float:
    return float(np.mean(np.abs(a - p) / np.maximum(np.abs(a), 1.0)) * 100)


def forecast_topic(yrs, cnt, last_year: int, horizon: int, backtest_years: int,
                   models: list[str], min_skill: float) -> dict | None:
    yrs, cnt = np.asarray(yrs, dtype=float), np.asarray(cnt, dtype=float)
    tr = yrs <= last_year - backtest_years
    te = ~tr
    if tr.sum() < 3 or te.sum() == 0:
        return None
    maes: dict[str, float] = {}
    mapes: dict[str, float] = {}
    for name in dict.fromkeys(["naive", *models]):             # naive first → wins ties
        try:
            p, _ = MODELS[name](yrs[tr], cnt[tr], yrs[te])
        except Exception:  # noqa: BLE001 — a failing model is skipped, never fatal
            continue
        p = np.maximum(p, 0)
        mae = _mae(cnt[te], p)
        if math.isfinite(mae):                                   # NaN/inf would poison min() and the skill
            maes[name], mapes[name] = mae, _mape(cnt[te], p)
    if "naive" not in maes:                                       # no baseline → skill undefined → no forecast
        return None
    best = min(maes, key=maes.get)
    skill = 1 - maes[best] / maes["naive"] if maes["naive"] > 0 else 0.0
    scale = float(np.mean(np.abs(np.diff(cnt[tr]))))
    mase = maes[best] / scale if scale > 0 else math.nan
    future = np.arange(last_year + 1, last_year + 1 + horizon, dtype=float)
    pred, sigma = MODELS[best](yrs, cnt, future)
    pred = np.maximum(pred, 0)
    return {
        "model": best,
        "backtest_mae": round(maes[best], 2),
        "backtest_mape": round(mapes[best], 2),
        "mase": round(mase, 3) if math.isfinite(mase) else None,
        "skill_vs_naive": round(skill, 3),
        "show": bool(best != "naive" and skill > min_skill),
        "hist_years": json.dumps([int(y) for y in yrs]),
        "hist_counts": json.dumps([int(c) for c in cnt]),
        "fc_years": json.dumps([int(y) for y in future]),
        "fc_mean": json.dumps([round(float(v), 1) for v in pred]),
        "fc_lo": json.dumps([round(max(float(v) - 1.96 * sigma, 0.0), 1) for v in pred]),
        "fc_hi": json.dumps([round(float(v) + 1.96 * sigma, 1) for v in pred]),
    }


def forecast(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    series = read_table(work / "06_series.parquet")
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    f = cfg["forecast"]
    rows = []
    for tid, g in series.groupby("topic_id"):
        g = g.sort_values("year")
        if len(g) < int(f["min_history_years"]) or g["count"].sum() == 0:
            continue
        r = forecast_topic(g["year"], g["count"], last, int(f["horizon"]), int(f["backtest_years"]),
                           list(f["models"]), float(f["min_skill"]))
        if r:
            rows.append({"topic_id": int(tid), **r})
    out = pd.DataFrame(rows, columns=FORECAST_COLUMNS)
    write_table(out, work / "08_forecasts.parquet")
    shown = int(out["show"].sum()) if len(out) else 0
    print(f"[forecast] {len(out)} topics forecast, {shown} skilful enough to show")
    return out
