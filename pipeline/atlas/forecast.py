"""Forecast v2 — share × corpus total, rolling-origin CV, MASE, conformal intervals, skill gate, nowcast.

count_t = share_t × N_t. The corpus total N is forecast once (best of forecast.total_models by
rolling-origin MAE); each topic's share is forecast by every model and the count forecast is
share forecast × N forecast — so topic numbers stay consistent with the corpus total.

Models (forecast.models):
  naive       ĉ = c_T                                   — the baseline ("same as last year")
  drift       share_T + h·(share_T − share_1)/(T − 1)   × N̂
  nb_glm      NB2 GLM  log E[c_t] = log N_t + a + b·t    × N̂   (α by moments, offset = corpus size)
  ets_damped  damped-trend Holt (statsmodels) on share  × N̂

Rolling-origin CV: origins o = T−cv_origins … T−1, horizons h ≤ horizon with o + h ≤ T; an origin
trains on years ≤ o only (≥ min_train_years) — including the N̂ it uses, whose total model is also chosen
on years ≤ o only. The published model is the one with the lowest MAE pooled over every (o, h). Skill is
scored honestly, without reusing the data that picked the model: at each origin after the first, the
model chosen from EARLIER origins is evaluated (honest_records). MASE = that MAE / mean|c_t − c_{t−1}|
over the history; skill = 1 − MAE / MAE(naive). Shown only when best ≠ naive, skill > min_skill,
MASE < max_mase and the topic has ≥ min_honest_points honest points ("แนวโน้มไม่แน่นอน" otherwise).

Intervals 80/95%: NB2 scale σ(μ) = sqrt(μ + α·μ²) with the topic's α; split-conformal factor
q_h = the ⌈(n+1)·level⌉-th smallest |c − ĉ| / σ over ALL topics' honest CV errors at horizon h (the
same honest records as skill: errors of the model picked because it scored best on those very points
are too small and give too narrow intervals); interval ĉ ± q_h·σ floored at 0. Fewer than
min_calibration scores → normal quantiles (1.2816 / 1.9600).

Nowcast: only for the running calendar year Y = last_complete_year + 1 = emerging.as_of_year (a year the
backfill guard trimmed gets none). full-year estimate = ytd / f(m), f(m) = share of a year's articles
published by month m in the last profile_years complete years; m = nowcast.as_of, else the latest month
of Y (≤ the snapshot month) holding ≥ nowcast.min_month_share of Y's dated articles.
Outputs: work/08_forecasts, work/08_forecast_meta.json
"""
from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from atlas.config import ForecastCfg
from atlas.io_utils import read_table, write_table
from atlas.topics_time import as_of_year

FORECAST_COLUMNS = ["topic_id", "model", "backtest_mae", "backtest_mape", "mase", "skill_vs_naive", "show",
                    "hist_years", "hist_counts", "fc_years", "fc_mean", "fc_lo", "fc_hi",
                    "fc_lo80", "fc_hi80", "fc_lo95", "fc_hi95",
                    "nowcast_year", "nowcast_month", "nowcast_ytd", "nowcast_mean"]
LEVELS = (0.8, 0.95)
SHARE_MODELS = ("drift", "nb_glm", "ets_damped")


# ------------------------------------------------------------------ models
def holt_damped(y: np.ndarray, h: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    scale = float(np.abs(y).max()) or 1.0
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(y / scale, trend="add", damped_trend=True,
                                   initialization_method="estimated").fit()
        out = np.asarray(fit.forecast(h), dtype=float) * scale
    if not np.isfinite(out).all():
        raise ValueError("ETS produced non-finite values")
    return out


def total_forecast(model: str, N: np.ndarray, h: int) -> np.ndarray:
    N = np.asarray(N, dtype=float)
    if model == "naive":
        out = np.repeat(N[-1], h)
    elif model == "drift":
        out = N[-1] + np.arange(1, h + 1) * (N[-1] - N[0]) / max(len(N) - 1, 1)
    elif model == "ets_damped":
        out = holt_damped(N, h)
    else:
        raise ValueError(model)
    return np.maximum(out, 1.0)


@dataclass(frozen=True)
class NbParams:
    """Result-changing constants of the NB interval (forecast.alpha_min/alpha_max/dispersion_fallback/sigma_floor)."""
    alpha_min: float
    alpha_max: float
    dispersion_fallback: float
    sigma_floor: float

    @classmethod
    def from_cfg(cls, fcfg: dict) -> NbParams:
        return cls(float(fcfg["alpha_min"]), float(fcfg["alpha_max"]), float(fcfg["dispersion_fallback"]),
                   float(fcfg["sigma_floor"]))


NB_DEFAULT = NbParams.from_cfg(ForecastCfg().model_dump())      # the shipped defaults, for callers without a config


def nb_trend(c: np.ndarray, N: np.ndarray, nb_params: NbParams = NB_DEFAULT) -> tuple[float, float, float, float]:
    """log E[c_t] = log N_t + a + b·(t − t̄) → (a, b, alpha, t̄) with NB2 alpha by moments."""
    import statsmodels.api as sm

    t = np.arange(len(c), dtype=float)
    tm = float(t.mean())
    X = sm.add_constant(t - tm, has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pois = sm.GLM(c, X, family=sm.families.Poisson(), offset=np.log(N)).fit()
        mu = np.asarray(pois.fittedvalues, dtype=float)
        dof = max(len(c) - 2, 1)
        alpha = float(np.clip(np.sum(((c - mu) ** 2 - mu) / np.maximum(mu, 1e-9) ** 2) / dof, nb_params.alpha_min, nb_params.alpha_max))
        nb = sm.GLM(c, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=np.log(N)).fit()
    a, b = (float(v) for v in nb.params)
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError("NB GLM did not converge")
    return a, b, alpha, tm


def share_forecast(model: str, c: np.ndarray, N: np.ndarray, h: int,
                   nb_params: NbParams = NB_DEFAULT) -> np.ndarray:
    s = c / N
    steps = np.arange(1, h + 1)
    if model == "drift":
        out = s[-1] + steps * (s[-1] - s[0]) / max(len(s) - 1, 1)
    elif model == "nb_glm":
        a, b, _, tm = nb_trend(c, N, nb_params)
        out = np.exp(a + b * (len(c) - 1 + steps - tm))
    elif model == "ets_damped":
        out = holt_damped(s, h)
    else:
        raise ValueError(model)
    return np.clip(out, 0.0, 1.0)


def predict_counts(model: str, c: np.ndarray, N: np.ndarray, N_future: np.ndarray,
                   nb_params: NbParams = NB_DEFAULT) -> np.ndarray:
    if model == "naive":
        return np.repeat(float(c[-1]), len(N_future))
    return share_forecast(model, c, N, len(N_future), nb_params) * N_future


def dispersion(c: np.ndarray, N: np.ndarray, nb_params: NbParams = NB_DEFAULT) -> float:
    """NB2 alpha of a topic (0 = Poisson); forecast.dispersion_fallback when the trend model cannot be fitted."""
    try:
        return nb_trend(c, N, nb_params)[2]
    except Exception:  # noqa: BLE001
        return nb_params.dispersion_fallback


def nb_sigma(mu: np.ndarray, alpha: float, nb_params: NbParams = NB_DEFAULT) -> np.ndarray:
    mu = np.maximum(np.asarray(mu, dtype=float), 0.0)
    return np.sqrt(mu + alpha * mu ** 2) + nb_params.sigma_floor     # forecast.sigma_floor: never narrower than ±floor


# ------------------------------------------------------------------ backtest
def origins(n_years: int, cv_origins: int, min_train: int) -> list[int]:
    """Index of the last training year for each rolling origin (needs ≥ min_train training years)."""
    return [o for o in range(n_years - 1 - cv_origins, n_years - 1) if o + 1 >= min_train]


def choose_total_model(N: np.ndarray, models: list[str], horizon: int, cv_origins: int, min_train: int) -> str:
    errs: dict[str, list[float]] = {m: [] for m in models}
    for o in origins(len(N), cv_origins, min_train):
        h = min(horizon, len(N) - 1 - o)
        for m in models:
            try:
                errs[m] += list(np.abs(N[o + 1:o + 1 + h] - total_forecast(m, N[:o + 1], h)))
            except Exception:  # noqa: BLE001
                errs[m].append(math.inf)
    mae = {m: float(np.mean(e)) if e else math.inf for m, e in errs.items()}
    return min(models, key=lambda m: (mae[m], models.index(m)))


def backtest_topic(c: np.ndarray, N: np.ndarray, models: list[str], n_hat: dict[int, np.ndarray], offset: int,
                   horizon: int, cv_origins: int, min_train: int,
                   nb_params: NbParams = NB_DEFAULT) -> dict[str, list[tuple[int, int, float, float, float]]]:
    """model → [(origin, h, actual, predicted, sigma)] over all rolling origins; models that fail anywhere are dropped.

    c, N start at the topic's first year = index `offset` of the corpus years; n_hat[i] is the corpus-total
    forecast made with corpus years [0..i] only (no look-ahead).
    """
    out: dict[str, list] = {m: [] for m in models}
    failed: set[str] = set()
    for o in origins(len(c), cv_origins, min_train):
        h = min(horizon, len(c) - 1 - o)
        N_hat = n_hat[offset + o][:h]
        alpha = dispersion(c[:o + 1], N[:o + 1], nb_params)
        for m in models:
            if m in failed:
                continue
            try:
                p = np.maximum(predict_counts(m, c[:o + 1], N[:o + 1], N_hat, nb_params), 0.0)
            except Exception:  # noqa: BLE001 — a model that cannot fit this origin is out for the topic
                failed.add(m)
                continue
            if not np.isfinite(p).all():                 # NaN/inf predictions never enter the MAE
                failed.add(m)
                continue
            sig = nb_sigma(p, alpha, nb_params)
            out[m] += [(o, k + 1, float(c[o + 1 + k]), float(p[k]), float(sig[k])) for k in range(h)]
    return {m: v for m, v in out.items() if m not in failed and v}


def _mae(recs) -> float:
    return float(np.mean([abs(a - p) for _, _, a, p, _ in recs])) if recs else math.inf


def honest_records(bt: dict[str, list], models: list[str]) -> tuple[list, list]:
    """Errors of the model that would have been CHOSEN at each origin using only earlier origins.

    Model choice and skill scoring must not share data: at origin k the model with the lowest MAE over
    origins < k is "selected", and its error at k is what skill and MASE use.
    The first origin only seeds the choice. → (selected-model records, naive records) on the same points.
    Interval calibration (conformal_factors) uses these same selected-model records: the published model's
    own CV errors are optimistic (it was picked for scoring best on them) and give too narrow intervals.
    """
    oks = sorted({r[0] for v in bt.values() for r in v})
    chosen, naive = [], []
    for o in oks[1:]:
        prior = {m: _mae([r for r in v if r[0] < o]) for m, v in bt.items()}
        sel = min(prior, key=lambda m: (prior[m], models.index(m)))
        chosen += [r for r in bt[sel] if r[0] == o]
        naive += [r for r in bt["naive"] if r[0] == o]
    return chosen, naive


def conformal_factors(scores: dict[int, list[float]], min_calibration: int) -> dict[int, dict[float, float]]:
    """horizon → {level: factor} from pooled normalised CV errors (split conformal)."""
    out: dict[int, dict[float, float]] = {}
    for h, s in scores.items():
        s = np.sort(np.asarray(s, dtype=float))
        out[h] = {}
        for lv in LEVELS:
            if len(s) < min_calibration:
                out[h][lv] = NormalDist().inv_cdf(0.5 + lv / 2)
            else:
                k = min(math.ceil((len(s) + 1) * lv), len(s)) - 1
                out[h][lv] = float(s[k])
    return out


# ------------------------------------------------------------------ nowcast
def month_fraction(months: pd.DataFrame, years: list[int], as_of: int) -> float:
    """Share of the articles of `years` published in months ≤ as_of (months: year, month, count)."""
    sub = months[months["year"].isin(years)]
    total = float(sub["count"].sum())
    return float(sub.loc[sub["month"] <= as_of, "count"].sum()) / total if total else 0.0


def nowcast_month(in_year: pd.DataFrame, min_share: float, cap: int) -> int:
    """Latest month ≤ cap holding ≥ min_share of the year's dated articles (0 = none) — the "as of" month.

    A few forward-dated articles (an issue dated December, indexed in April) must not make the year look
    published through December; cap = the snapshot month, since later months cannot be complete yet.
    """
    total = float(in_year["count"].sum())
    ok = in_year[(in_year["month"] <= cap) & (in_year["count"] > 0) & (in_year["count"] >= min_share * total)]
    return int(ok["month"].max()) if len(ok) else 0


# ------------------------------------------------------------------ all topics
def forecast_all(series: pd.DataFrame, totals: pd.Series, last_year: int, fcfg: dict,
                 horizon: int | None = None) -> tuple[pd.DataFrame, dict]:
    """series: topic_id, year, count (years ≤ last_year) · totals: corpus articles by year (index = year)."""
    H = int(horizon or fcfg["horizon"])
    nbp = NbParams.from_cfg(fcfg)
    cvo, mtr = int(fcfg["cv_origins"]), int(fcfg["min_train_years"])
    years = [y for y in sorted(int(y) for y in totals.index) if y <= last_year]
    N = totals.reindex(years).to_numpy(dtype=float)
    models = list(dict.fromkeys(["naive", *fcfg["models"]]))
    tms = list(fcfg["total_models"])
    total_model = choose_total_model(N, tms, H, cvo, mtr)          # for the published future only
    # each origin's N̂ uses a total model chosen on years ≤ that origin (no look-ahead into later totals)
    n_hat = {i: total_forecast(choose_total_model(N[:i + 1], tms, H, cvo, mtr), N[:i + 1], H)
             for i in range(max(0, len(N) - 1 - cvo), len(N) - 1)}
    N_future = total_forecast(total_model, N, H)
    fut_years = list(range(last_year + 1, last_year + 1 + H))

    fits, scores = [], {h: [] for h in range(1, H + 1)}
    for tid, g in series[series["year"] <= last_year].groupby("topic_id"):
        cnt = g.set_index("year")["count"].reindex(years, fill_value=0).to_numpy(dtype=float)
        first = int(np.argmax(cnt > 0)) if cnt.any() else len(cnt)
        c, Nt = cnt[first:], N[first:]                      # history starts at the topic's first article
        if len(c) < int(fcfg["min_history_years"]) or c.sum() == 0:
            continue
        bt = backtest_topic(c, Nt, models, n_hat, first, H, cvo, mtr, nbp)
        if "naive" not in bt:
            continue
        mae = {m: _mae(v) for m, v in bt.items()}
        best = min(mae, key=lambda m: (mae[m], models.index(m)))       # final model: all origins; naive wins ties
        chosen, naive = honest_records(bt, models)
        if not chosen:                                   # a single origin cannot score a selection honestly
            continue
        mae_sel, mae_naive = _mae(chosen), _mae(naive)
        mape = float(np.mean([abs(a - p) / max(a, 1.0) for _, _, a, p, _ in chosen]) * 100)
        scale = float(np.mean(np.abs(np.diff(c)))) if len(c) > 1 else 0.0
        mase = round(mae_sel / scale, 3) if scale > 0 else math.nan       # gate on the value we publish
        skill = 1 - mae_sel / mae_naive if mae_naive > 0 else 0.0
        for _, h, a, p, s in chosen:                    # interval calibration: the honest CV errors
            scores[h].append(abs(a - p) / s)
        fits.append({"topic_id": int(tid), "best": best, "c": c, "N": Nt, "years": years[first:],
                     "mae": mae_sel, "mape": mape, "mase": mase, "skill": skill, "n_honest": len(chosen)})

    q = conformal_factors(scores, int(fcfg["min_calibration"]))
    rows = []
    n_failed = 0
    for f in fits:
        model = f["best"]
        try:
            mean = np.maximum(predict_counts(model, f["c"], f["N"], N_future, nbp), 0.0)
            if not np.isfinite(mean).all():
                raise ValueError("non-finite forecast")
        except Exception:  # noqa: BLE001 — the full-history fit failed: publish the naive line, never a trend
            model, n_failed = "naive", n_failed + 1
            mean = np.maximum(predict_counts(model, f["c"], f["N"], N_future, nbp), 0.0)
        sig = nb_sigma(mean, dispersion(f["c"], f["N"], nbp), nbp)
        show = bool(model != "naive" and f["skill"] > float(fcfg["min_skill"])
                    and math.isfinite(f["mase"]) and f["mase"] < float(fcfg["max_mase"])
                    and f["n_honest"] >= int(fcfg["min_honest_points"]))
        lo = {lv: [round(max(float(mean[i] - q[i + 1][lv] * sig[i]), 0.0), 1) for i in range(H)] for lv in LEVELS}
        hi = {lv: [round(float(mean[i] + q[i + 1][lv] * sig[i]), 1) for i in range(H)] for lv in LEVELS}
        rows.append({
            "topic_id": f["topic_id"], "model": model,
            "backtest_mae": round(f["mae"], 2), "backtest_mape": round(f["mape"], 2),
            "mase": f["mase"] if math.isfinite(f["mase"]) else None,
            "skill_vs_naive": round(f["skill"], 3), "show": show,
            "hist_years": json.dumps([int(y) for y in f["years"]]),
            "hist_counts": json.dumps([int(v) for v in f["c"]]),
            "fc_years": json.dumps(fut_years), "fc_mean": json.dumps([round(float(v), 1) for v in mean]),
            "fc_lo": json.dumps(lo[0.95]), "fc_hi": json.dumps(hi[0.95]),
            "fc_lo80": json.dumps(lo[0.8]), "fc_hi80": json.dumps(hi[0.8]),
            "fc_lo95": json.dumps(lo[0.95]), "fc_hi95": json.dumps(hi[0.95]),
        })
    if n_failed:
        print(f"[forecast] WARNING: {n_failed} topics: the chosen model could not be fitted on the full history "
              "- published as naive, not shown")
    meta = {"total_model": total_model, "total_years": fut_years,
            "total_mean": [round(float(v), 1) for v in N_future],
            "conformal": {str(h): {str(lv): round(v, 4) for lv, v in d.items()} for h, d in q.items()},
            "n_calibration": {str(h): len(s) for h, s in scores.items()}}
    return pd.DataFrame(rows, columns=[c for c in FORECAST_COLUMNS if not c.startswith("nowcast")]), meta


def holdout_coverage(series: pd.DataFrame, totals: pd.Series, last_year: int, fcfg: dict, holdout: int = 2) -> dict:
    """Honest check: forecast from last_year − holdout with everything (incl. calibration) fitted on the
    truncated data, then compare the 80/95% intervals and MASE with the held-out actual counts."""
    cut = last_year - holdout
    rows, _ = forecast_all(series[series["year"] <= cut], totals[totals.index <= cut], cut, fcfg, horizon=holdout)
    actual = series.set_index(["topic_id", "year"])["count"]
    hit80 = hit95 = n = 0
    for r in rows.itertuples():
        for i, y in enumerate(json.loads(r.fc_years)):
            a = float(actual.get((r.topic_id, y), 0))
            hit80 += json.loads(r.fc_lo80)[i] <= a <= json.loads(r.fc_hi80)[i]
            hit95 += json.loads(r.fc_lo95)[i] <= a <= json.loads(r.fc_hi95)[i]
            n += 1
    shown = rows[rows["show"]]
    return {"n": n, "coverage80": hit80 / n if n else math.nan, "coverage95": hit95 / n if n else math.nan,
            "n_shown": int(len(shown)), "max_mase_shown": float(shown["mase"].max()) if len(shown) else math.nan}


def rolling_coverage(series: pd.DataFrame, totals: pd.Series, last_year: int, fcfg: dict, n_cuts: int = 3) -> dict:
    """holdout_coverage at the published horizon from n_cuts successive cut-off years, pooled.

    One cut-off gives few points (topics × horizon); pooling several makes the coverage estimate steady.
    """
    H = int(fcfg["horizon"])
    res = [holdout_coverage(series[series["year"] <= end], totals[totals.index <= end], end, fcfg, holdout=H)
           for end in range(last_year, last_year - n_cuts, -1)]
    n = sum(r["n"] for r in res)
    shown = [r["max_mase_shown"] for r in res if r["n_shown"]]
    return {"n": n, "cuts": n_cuts,
            "coverage80": sum(r["coverage80"] * r["n"] for r in res if r["n"]) / n if n else math.nan,
            "coverage95": sum(r["coverage95"] * r["n"] for r in res if r["n"]) / n if n else math.nan,
            "n_shown": sum(r["n_shown"] for r in res), "max_mase_shown": max(shown) if shown else math.nan}


def forecast(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    f = cfg["forecast"]
    series = read_table(work / "06_series.parquet")
    em_path = work / "07_emerging.parquet"
    if em_path.exists():                       # LOW_DATA topics get no forecast (they get no trend claim either)
        em = read_table(em_path)
        series = series[~series["topic_id"].isin(set(em.loc[em["status"] == "LOW_DATA", "topic_id"]))]
    meta6 = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    last = int(meta6["last_complete_year"])
    totals = pd.Series({int(y): int(n) for y, n in meta6["totals"].items()}).sort_index()
    if len(series) and len(totals) >= int(f["min_history_years"]):
        out, meta = forecast_all(series, totals, last, f)
    else:
        out, meta = pd.DataFrame(columns=FORECAST_COLUMNS[:17]), {"total_model": None}
    out = out.reindex(columns=FORECAST_COLUMNS)
    meta["nowcast"] = None
    nc = f["nowcast"]
    months_path, partial_path = work / "06_months.parquet", work / "06_partial_year.parquet"
    year = last + 1
    running = int(meta6.get("as_of_year") or as_of_year(cfg["emerging"]))
    if nc["enabled"] and year != running:
        print(f"[forecast] no nowcast: the partial year {year} is not the running year {running} "
              "(the backfill guard held it back as incomplete)")
    elif nc["enabled"] and months_path.exists() and partial_path.exists():
        months, partial = read_table(months_path), read_table(partial_path)
        in_year = months[months["year"] == year]
        today = date.today()
        as_of = 0
        if nc["as_of"] and int(nc["as_of"][:4]) == year:
            as_of = int(nc["as_of"][5:7])
        elif nc["as_of"]:
            print(f"[forecast] WARNING: forecast.nowcast.as_of={nc['as_of']} is not in the partial year {year} "
                  "- ignored, the month is taken from the data")
        if not as_of:
            as_of = nowcast_month(in_year, float(nc["min_month_share"]), today.month if running == today.year else 12)
        prof_years = list(range(last - int(nc["profile_years"]) + 1, last + 1))
        frac = month_fraction(months, prof_years, as_of) if as_of else 0.0
        if as_of >= int(nc["min_months"]) and frac > 0:
            ytd = partial[partial["year"] == year].set_index("topic_id")["count"]
            total_ytd = int(meta6.get("partial_totals", {}).get(str(year), int(ytd.sum())))
            meta["nowcast"] = {"year": year, "as_of_month": as_of, "fraction": round(frac, 4),
                               "ytd": total_ytd, "mean": round(total_ytd / frac, 1)}
            out["nowcast_year"], out["nowcast_month"] = year, as_of
            out["nowcast_ytd"] = out["topic_id"].map(ytd).fillna(0).astype(int)
            out["nowcast_mean"] = (out["nowcast_ytd"] / frac).round(1)
    write_table(out, work / "08_forecasts.parquet")
    (work / "08_forecast_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    shown = int(out["show"].astype(bool).sum()) if len(out) else 0
    print(f"[forecast] {len(out)} topics forecast, {shown} skilful enough to show; total model {meta['total_model']}")
    return out
