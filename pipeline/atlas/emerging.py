"""Phase 5b — Emerging Topic Analysis (TCI definition).

นิยาม (อ่านร่วมกับ README.md หัวข้อ "นิยาม Emerging ของ TCI"):

  window:  R = recent_window ปีล่าสุด (ที่ข้อมูลสมบูรณ์),  B = baseline_window ปีก่อนหน้า R

  per-topic metrics:
    share_R, share_B   : สัดส่วนบทความของ topic ต่อ corpus ในช่วง R / B
    cagr_recent        : CAGR ของจำนวนบทความในช่วง R (smoothing +0.5)
    slope_share        : OLS slope ของ share เทียบปี ทั้งช่วง B∪R (normalize ด้วย mean share)
    acceleration       : slope(count|R) − slope(count|B)  normalize ด้วย mean count
    burst_intensity    : Kleinberg 2-state burst (Poisson, corpus-adjusted)
    novelty            : 1 − max cosine sim ของ centroid เทียบกับรอบ pipeline ก่อน (ถ้าไม่มี → 0.5)

  classification:
    EMERGING  : share_R < max_recent_share  และ  cagr_recent ≥ min_cagr_recent
                และ  share_R/share_B ≥ min_share_ratio  และ  count_R ≥ min_articles_recent
    HOT       : share_R ≥ max_recent_share  และ  slope_share > min_slope_share
    DECLINING : slope ของ share ติดลบต่อเนื่อง ≥ consecutive_negative_years ปีท้าย
    STABLE    : อื่น ๆ

  emerging_score (0–100) = percentile-rank weighted sum:
    0.35·growth + 0.25·acceleration + 0.20·burst + 0.20·novelty   (weights จาก config)

Output: work/07_emerging.parquet
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import read_table, write_table

EPS = 1e-12


# ---------------------------------------------------------------- statistics
def _ols_slope(years: np.ndarray, values: np.ndarray) -> float:
    if len(years) < 2 or np.all(values == values[0]):
        return 0.0
    x = years - years.mean()
    denom = (x ** 2).sum()
    if denom == 0:
        return 0.0
    return float((x * (values - values.mean())).sum() / denom)


def _cagr(first: float, last: float, periods: int) -> float:
    if periods <= 0:
        return 0.0
    return float(((last + 0.5) / (first + 0.5)) ** (1 / periods) - 1)


def _poisson_logpmf(c: np.ndarray, lam: np.ndarray) -> np.ndarray:
    lam = np.maximum(lam, EPS)
    lgamma = np.array([math.lgamma(x + 1) for x in c])
    return c * np.log(lam) - lam - lgamma


def kleinberg_burst(counts: np.ndarray, corpus: np.ndarray, gamma: float = 1.0,
                    burst_scale: float = 3.0) -> tuple[float, list[int]]:
    """2-state Kleinberg burst detection via Viterbi.

    Returns (burst_intensity, burst_years_index_list).
    Intensity = total log-likelihood gain during burst years (≥ 0).
    """
    T = len(counts)
    if T == 0 or counts.sum() == 0:
        return 0.0, []
    p0 = counts.sum() / max(corpus.sum(), 1)
    p1 = min(p0 * burst_scale, 1.0)
    if p1 <= p0:
        return 0.0, []

    cost0 = -_poisson_logpmf(counts, corpus * p0)
    cost1 = -_poisson_logpmf(counts, corpus * p1)

    # Viterbi, states: 0 = baseline, 1 = burst; entering burst costs gamma
    dp = np.full((T, 2), np.inf)
    back = np.zeros((T, 2), dtype=int)
    dp[0, 0] = cost0[0]
    dp[0, 1] = cost1[0] + gamma
    for t in range(1, T):
        for s in (0, 1):
            cost = cost0[t] if s == 0 else cost1[t]
            stay = dp[t - 1, s] + cost
            switch = dp[t - 1, 1 - s] + gamma + cost
            if stay <= switch:
                dp[t, s], back[t, s] = stay, s
            else:
                dp[t, s], back[t, s] = switch, 1 - s

    state = int(np.argmin(dp[T - 1]))
    states = [0] * T
    for t in range(T - 1, -1, -1):
        states[t] = state
        state = back[t, state]

    burst_idx = [i for i, s in enumerate(states) if s == 1]
    intensity = float(sum(cost0[i] - cost1[i] for i in burst_idx))
    return max(intensity, 0.0), burst_idx


# ---------------------------------------------------------------- novelty
def _novelty(cfg: dict) -> np.ndarray | None:
    """cosine novelty of current centroids vs previous pipeline run (if any)."""
    work = Path(cfg["pipeline"]["work_dir"])
    prev = work / "prev" / "centroids.npy"
    cur_path = work / "04_centroids.npy"
    if not prev.exists() or not cur_path.exists():
        return None
    prev_c = np.load(prev)
    cur_c = np.load(cur_path)
    if prev_c.ndim != 2 or cur_c.ndim != 2 or prev_c.shape[1] != cur_c.shape[1]:
        return None
    sim = cur_c @ prev_c.T
    return (1.0 - sim.max(axis=1)).clip(0, 1)


# ---------------------------------------------------------------- main
def emerging(cfg: dict, series: pd.DataFrame | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    if series is None:
        series = read_table(work / "06_series.parquet")
    meta = pd.read_json(work / "06_meta.json", typ="series")
    last_year = int(meta["last_complete_year"])

    ecfg = cfg["emerging"]
    wR = int(ecfg["recent_window"])
    wB = int(ecfg["baseline_window"])
    R_years = list(range(last_year - wR + 1, last_year + 1))
    B_years = list(range(last_year - wR - wB + 1, last_year - wR + 1))

    novelty = _novelty(cfg)
    centroid_ids = None
    ids_path = work / "04_centroid_ids.json"
    if novelty is not None and ids_path.exists():
        centroid_ids = pd.read_json(ids_path, typ="series").tolist()
        novelty_map = dict(zip(centroid_ids, novelty))
    else:
        novelty_map = {}

    rows = []
    for tid, g in series.groupby("topic_id"):
        g = g.sort_values("year")
        yrs = g["year"].to_numpy()
        cnt = g["count"].to_numpy(dtype=float)
        tot = g["corpus_total"].to_numpy(dtype=float)
        share = g["share"].to_numpy(dtype=float)

        inR = np.isin(yrs, R_years)
        inB = np.isin(yrs, B_years)
        cntR, totR = cnt[inR], tot[inR]
        cntB, totB = cnt[inB], tot[inB]

        count_R = cntR.sum()
        share_R = cntR.sum() / max(totR.sum(), 1)
        share_B = cntB.sum() / max(totB.sum(), 1)
        share_ratio = (share_R + EPS) / (share_B + EPS)

        cagr = _cagr(cntR[0] if len(cntR) else 0, cntR[-1] if len(cntR) else 0, len(cntR) - 1) if len(cntR) else 0.0

        win = inB | inR
        mean_share = share[win].mean() or EPS
        slope_share = _ols_slope(yrs[win], share[win]) / mean_share

        slope_R = _ols_slope(yrs[inR], cntR) / (cntR.mean() + EPS) if len(cntR) > 1 else 0.0
        slope_B = _ols_slope(yrs[inB], cntB) / (cntB.mean() + EPS) if len(cntB) > 1 else 0.0
        acceleration = slope_R - slope_B

        burst_int, burst_idx = kleinberg_burst(
            cnt, tot,
            gamma=float(ecfg["burst"]["gamma"]),
        )
        burst_years = [int(yrs[i]) for i in burst_idx]

        # consecutive negative share-slope years at the tail
        tail_slopes = []
        for i in range(len(yrs) - 1, 0, -1):
            ds = share[i] - share[i - 1]
            if ds < 0:
                tail_slopes.append(ds)
            else:
                break
        neg_streak = len(tail_slopes)

        nov = float(novelty_map.get(tid, 0.5))

        rows.append({
            "topic_id": tid,
            "count_recent": int(count_R),
            "share_recent": share_R,
            "share_baseline": share_B,
            "share_ratio": share_ratio,
            "cagr_recent": cagr,
            "slope_share": slope_share,
            "acceleration": acceleration,
            "burst_intensity": burst_int,
            "burst_years": ",".join(map(str, burst_years)),
            "novelty": nov,
            "neg_share_streak": neg_streak,
        })

    m = pd.DataFrame(rows)
    em, hot, dec = ecfg["emerging"], ecfg["hot"], ecfg["declining"]

    def classify(r):
        if (r.share_recent < em["max_recent_share"]
                and r.cagr_recent >= em["min_cagr_recent"]
                and r.share_ratio >= em["min_share_ratio"]
                and r.count_recent >= ecfg["min_articles_recent"]):
            return "EMERGING"
        if r.share_recent >= hot["min_recent_share"] and r.slope_share > hot["min_slope_share"]:
            return "HOT"
        if r.neg_share_streak >= dec["consecutive_negative_years"]:
            return "DECLINING"
        return "STABLE"

    m["status"] = m.apply(classify, axis=1)

    # score: percentile-rank each dimension within this run, then weighted sum
    w = ecfg["score_weights"]
    for col in ("cagr_recent", "acceleration", "burst_intensity", "novelty"):
        m[f"_p_{col}"] = m[col].rank(pct=True)
    m["emerging_score"] = 100 * (
        w["growth"] * m["_p_cagr_recent"]
        + w["acceleration"] * m["_p_acceleration"]
        + w["burst"] * m["_p_burst_intensity"]
        + w["novelty"] * m["_p_novelty"]
    )
    m = m.drop(columns=[c for c in m.columns if c.startswith("_p_")])
    m["last_complete_year"] = last_year
    m = m.sort_values("emerging_score", ascending=False).reset_index(drop=True)

    out = work / "07_emerging.parquet"
    write_table(m, out)
    n_em = (m["status"] == "EMERGING").sum()
    print(f"[emerging] {len(m)} topics | EMERGING={n_em} HOT={(m['status'] == 'HOT').sum()} "
          f"DECLINING={(m['status'] == 'DECLINING').sum()} (window R={R_years[0]}–{R_years[-1]})")
    return m
