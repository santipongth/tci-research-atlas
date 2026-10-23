"""Emerging Topic Analysis — definition v3 (source of truth: docs/EMERGING_SPEC.md).

Windows: R = recent_window last complete years, B = baseline_window years before R,
W = trend_window last years. Per topic:
  share_growth (+90% CI)  Poisson GLM log E[c_t] = log N_t + a + b·t, quasi-Poisson SE,
                          Student-t quantile when overdispersed; NaN when not estimable
  share_ratio             share_R / share_B
  acceleration            log growth in R − log growth in B
  burst_frac              Kleinberg burst years ∩ R / |R|
  novelty                 recency + topic age
  breadth                 journals / institutions in R, share from journals new in R
                          (orgs_unverified = institution rule skipped: affiliation coverage too low)
Statuses (in order): LOW_DATA, EMERGING, WATCH, HOT, DECLINING, STABLE.
Score 0–100 = weighted percentile ranks within the run (ranking only; not comparable across runs).
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table

EPS = 1e-12
STATUSES = ("EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA")
EMERGING_COLUMNS = [
    "topic_id", "count_recent", "share_recent", "share_baseline", "share_ratio", "share_growth", "share_growth_lo",
    "share_growth_hi", "cagr_recent", "acceleration", "burst_frac", "burst_years", "novelty", "coherence",
    "n_journals_R", "journal_hhi", "new_journal_share", "n_orgs_R", "org_coverage_R", "orgs_unverified", "status",
    "journal_driven", "large_share_threshold", "emerging_score", "last_complete_year", "definition_version",
]


def _cagr(first: float, last: float, periods: int) -> float:
    return 0.0 if periods <= 0 else float(((last + 0.5) / (first + 0.5)) ** (1 / periods) - 1)


def share_growth(counts, totals, years, ci_level: float,
                 max_abs_log_growth: float) -> tuple[float, float, float]:
    """Annual growth of the topic's SHARE of the corpus with a `ci_level` confidence interval.

    Poisson GLM  log E[c_t] = log N_t + a + b·(t − t̄)  (offset = corpus size).
    Quasi-Poisson standard errors: se = se_Poisson · sqrt(φ), φ = max(1, Pearson χ²/df) —
    overdispersion widens the interval, underdispersion never narrows it below Poisson.
    Quantile q: Student-t with the GLM's residual df when φ > 1 (φ is itself estimated from the
    window), standard normal when φ == 1 (Poisson variance known).
    Returns (e^b − 1, e^(b − q·se) − 1, e^(b + q·se) − 1), or NaNs when not estimable:
    < 3 years with corpus data, no articles, positive counts in < 2 distinct years (the MLE is
    infinite when all positives sit in one edge year; one middle year is finite but meaningless),
    a numerical failure of the fit, or any of b, b ± q·se non-finite or beyond ±max_abs_log_growth.
    """
    c, n, t = (np.asarray(a, dtype=float) for a in (counts, totals, years))
    ok = n > 0
    c, n, t = c[ok], n[ok], t[ok]
    nan = (math.nan, math.nan, math.nan)
    if len(c) < 3 or c.sum() == 0 or len(np.unique(t[c > 0])) < 2:
        return nan
    import statsmodels.api as sm
    from scipy.stats import norm
    from scipy.stats import t as student_t
    from statsmodels.tools.sm_exceptions import PerfectSeparationError

    X = sm.add_constant(t - t.mean(), has_constant="add")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = sm.GLM(c, X, family=sm.families.Poisson(), offset=np.log(n)).fit()
        df = float(fit.df_resid)
        phi = max(1.0, float(fit.pearson_chi2) / max(df, 1.0))
        b, se = float(fit.params[1]), float(fit.bse[1]) * math.sqrt(phi)
    except (PerfectSeparationError, np.linalg.LinAlgError, ValueError, FloatingPointError):
        return nan                                   # numerically degenerate series → not estimable
    p = 0.5 + float(ci_level) / 2
    q = float(student_t.ppf(p, df)) if phi > 1.0 else float(norm.ppf(p))
    log_g = (b, b - q * se, b + q * se)              # checked on the log scale, before exp
    if not all(math.isfinite(v) and abs(v) <= max_abs_log_growth for v in log_g):
        return nan
    return math.exp(log_g[0]) - 1, math.exp(log_g[1]) - 1, math.exp(log_g[2]) - 1


def _poisson_nll(c: np.ndarray, lam: np.ndarray) -> np.ndarray:
    lam = np.maximum(lam, EPS)
    return -(c * np.log(lam) - lam - np.array([math.lgamma(x + 1) for x in c]))


def kleinberg_burst(counts, totals, s: float = 2.0, gamma: float = 1.0) -> list[int]:
    """Kleinberg (2003) two-state burst automaton on yearly batches.

    The burst state expects s × the topic's base rate (scaled by each year's corpus size);
    moving UP into it costs γ·ln(T) (T = number of years), moving down is free.
    Returns the indices of burst years.
    """
    counts = np.asarray(counts, dtype=float)
    totals = np.asarray(totals, dtype=float)
    T = len(counts)
    if T == 0 or counts.sum() == 0:
        return []
    p0 = counts.sum() / max(totals.sum(), 1.0)
    p1 = min(p0 * s, 0.9999)
    if p1 <= p0:
        return []
    cost = np.vstack([_poisson_nll(counts, totals * p0), _poisson_nll(counts, totals * p1)])
    up = gamma * math.log(T) if T > 1 else gamma
    dp = np.zeros((T, 2))
    back = np.zeros((T, 2), dtype=int)
    dp[0] = [cost[0, 0], cost[1, 0] + up]
    for t in range(1, T):
        stay0, from1 = dp[t - 1, 0], dp[t - 1, 1]            # into state 0: free from either
        dp[t, 0], back[t, 0] = (stay0, 0) if stay0 <= from1 else (from1, 1)
        stay1, from0 = dp[t - 1, 1], dp[t - 1, 0] + up       # into state 1: pay to move up
        dp[t, 1], back[t, 1] = (stay1, 1) if stay1 <= from0 else (from0, 0)
        dp[t] += cost[:, t]
    state = int(np.argmin(dp[-1]))
    states = [0] * T
    for t in range(T - 1, -1, -1):
        states[t] = state
        state = back[t, state]
    return [i for i, st in enumerate(states) if st == 1]


def topic_novelty(cnt: np.ndarray, yrs: np.ndarray, r_years: list[int], last_year: int) -> float:
    """0.5 × share of the topic's articles that fall in R + 0.5 × (1 − age/15).

    age = years since the topic first reached max(3, 10% of its peak) articles.
    """
    total = cnt.sum()
    if total <= 0:
        return 0.0
    recent = cnt[np.isin(yrs, r_years)].sum() / total
    hit = cnt >= max(3.0, 0.1 * cnt.max())
    first = int(yrs[np.argmax(hit)]) if hit.any() else last_year
    age = max(0, last_year - first)
    return float(0.5 * recent + 0.5 * (1 - min(age, 15) / 15))


def definition_windows(ecfg: dict, last_year: int) -> tuple[list[int], list[int], list[int]]:
    """(R, B, W) of the definition (docs/EMERGING_SPEC.md): the recent years, the baseline years just before them and
    the trend window, all ending at `last_year` (the last complete year)."""
    wR, wB, wW = int(ecfg["recent_window"]), int(ecfg["baseline_window"]), int(ecfg["trend_window"])
    return (list(range(last_year - wR + 1, last_year + 1)), list(range(last_year - wR - wB + 1, last_year - wR + 1)),
            list(range(last_year - wW + 1, last_year + 1)))


def compute_emerging(series: pd.DataFrame, last_year: int, ecfg: dict, jseries: pd.DataFrame,
                     oseries: pd.DataFrame, jfirst: pd.DataFrame,
                     coherence: dict | None = None) -> pd.DataFrame:
    R, B, W = definition_windows(ecfg, last_year)
    ci, max_log = float(ecfg["ci_level"]), float(ecfg["max_abs_log_growth"])
    bcfg, br = ecfg["burst"], ecfg["breadth"]
    new_j = set(jfirst.loc[jfirst["first_year"] >= R[0], "journal"])
    jR = jseries[jseries["year"].isin(R) & (jseries["count"] > 0)]
    oR = oseries[oseries["year"].isin(R) & (oseries["count"] > 0)]
    coherence = coherence or {}

    rows = []
    for tid, g in series.groupby("topic_id"):
        g = g.sort_values("year")
        yrs = g["year"].to_numpy()
        cnt = g["count"].to_numpy(dtype=float)
        tot = g["corpus_total"].to_numpy(dtype=float)
        with_org = g["count_with_org"].to_numpy(dtype=float) if "count_with_org" in g else cnt
        inR, inB, inW = np.isin(yrs, R), np.isin(yrs, B), np.isin(yrs, W)
        count_R = float(cnt[inR].sum())
        share_R = count_R / max(tot[inR].sum(), 1.0)
        share_B = cnt[inB].sum() / max(tot[inB].sum(), 1.0)
        growth, lo, hi = share_growth(cnt[inW], tot[inW], yrs[inW], ci, max_log)
        g_R = share_growth(cnt[inR], tot[inR], yrs[inR], ci, max_log)[0]
        g_B = share_growth(cnt[inB], tot[inB], yrs[inB], ci, max_log)[0]
        accel = (math.log1p(g_R) if math.isfinite(g_R) else 0.0) - (math.log1p(g_B) if math.isfinite(g_B) else 0.0)
        bursts = [int(yrs[i]) for i in kleinberg_burst(cnt, tot, float(bcfg["s"]), float(bcfg["gamma"]))]
        tj = jR[jR["topic_id"] == tid].groupby("journal")["count"].sum()
        tj_total = float(tj.sum())
        rows.append({
            "topic_id": tid,
            "count_recent": int(count_R),
            "share_recent": share_R,
            "share_baseline": share_B,
            "share_ratio": (share_R + EPS) / (share_B + EPS),
            "share_growth": growth,
            "share_growth_lo": lo,
            "share_growth_hi": hi,
            "cagr_recent": _cagr(cnt[inR][0], cnt[inR][-1], int(inR.sum()) - 1) if inR.any() else 0.0,
            "acceleration": accel,
            "burst_frac": len(set(bursts) & set(R)) / len(R),
            "burst_years": ",".join(map(str, bursts)),
            "novelty": topic_novelty(cnt, yrs, R, last_year),
            "coherence": float(coherence.get(tid, math.nan)),
            "n_journals_R": int(len(tj)),
            "journal_hhi": float(((tj / tj_total) ** 2).sum()) if tj_total else 0.0,
            "new_journal_share": float(tj[tj.index.isin(new_j)].sum() / tj_total) if tj_total else 0.0,
            "n_orgs_R": int(oR.loc[oR["topic_id"] == tid, "org_key"].nunique()),
            "org_coverage_R": float(with_org[inR].sum() / count_R) if count_R else 0.0,
        })
    m = pd.DataFrame(rows)
    if m.empty:
        return pd.DataFrame(columns=EMERGING_COLUMNS)

    low = (m["count_recent"] < int(ecfg["min_articles_recent"])) | m["share_growth"].isna()
    size = ecfg["size"]
    if size["rule"] == "quantile":
        thr = float(m.loc[~low, "share_recent"].quantile(float(size["large_quantile"]))) if (~low).any() else math.inf
    else:
        thr = float(size["large_share"])
    large = m["share_recent"] >= thr
    em, hot, dec = ecfg["emerging"], ecfg["hot"], ecfg["declining"]
    growth_ok = ~large & (m["share_growth_lo"] >= em["min_growth_lo"]) & (m["share_ratio"] >= em["min_share_ratio"])
    # the institution rule only applies when we actually know the institutions (>= min_org_coverage);
    # orgs_unverified exposes every topic for which it was skipped (any status)
    m["orgs_unverified"] = m["org_coverage_R"] < br["min_org_coverage"]
    orgs_ok = (m["n_orgs_R"] >= br["min_orgs"]) | m["orgs_unverified"]
    breadth_ok = ((m["n_journals_R"] >= br["min_journals"]) & orgs_ok
                  & (m["new_journal_share"] < br["max_new_journal_share"]))
    m["status"] = np.select(
        [low, growth_ok & breadth_ok, growth_ok,
         large & (m["share_growth_lo"] > hot["min_growth_lo"]),
         (m["share_growth_hi"] < dec["max_growth_hi"]) & (m["share_ratio"] <= dec["max_share_ratio"])],
        ["LOW_DATA", "EMERGING", "WATCH", "HOT", "DECLINING"], default="STABLE")
    m["journal_driven"] = growth_ok & ~breadth_ok
    m["large_share_threshold"] = thr

    w = ecfg["score_weights"]
    coh = m["coherence"]
    parts = {
        "growth": m["share_growth_lo"].fillna(-1.0),
        "acceleration": m["acceleration"].fillna(0.0),
        "burst": m["burst_frac"],
        "novelty": m["novelty"],
        "coherence": coh.fillna(coh.median() if coh.notna().any() else 0.0),
        "breadth": np.log1p(m["n_journals_R"]) + np.log1p(m["n_orgs_R"]),
    }
    m["emerging_score"] = 100 * sum(float(w[k]) * v.rank(pct=True) for k, v in parts.items())
    m["last_complete_year"] = last_year
    m["definition_version"] = int(ecfg["definition_version"])
    return m.sort_values("emerging_score", ascending=False).reset_index(drop=True)[EMERGING_COLUMNS]


def emerging(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    info = read_table(work / "04_topic_info.parquet")
    m = compute_emerging(
        read_table(work / "06_series.parquet"), int(meta["last_complete_year"]), cfg["emerging"],
        read_table(work / "06_topic_journal_year.parquet"), read_table(work / "06_topic_org_year.parquet"),
        read_table(work / "06_journal_first_year.parquet"),
        coherence=dict(zip(info["topic_id"], info["coherence"])),
    )
    write_table(m, work / "07_emerging.parquet")
    counts = ", ".join(f"{k}={v}" for k, v in m["status"].value_counts().items()) or "no topics"
    print(f"[emerging] v{cfg['emerging']['definition_version']} {len(m)} topics | {counts} | "
          f"orgs unverified: {int(m['orgs_unverified'].sum())}")
    return m
