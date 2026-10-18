"""Unit tests for the emerging-metrics engine — run with plain python or pytest.

Covers: CAGR, OLS slope, Kleinberg burst, and the TCI EMERGING/HOT/DECLINING rules.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlas.emerging import _cagr, _ols_slope, kleinberg_burst, emerging  # noqa: E402

MINI_CFG = {
    "pipeline": {"work_dir": "/tmp/atlas_test_work", "seed": 42},
    "emerging": {
        "min_year_complete": 2024,
        "recent_window": 3, "baseline_window": 5, "min_articles_recent": 30,
        "emerging": {"max_recent_share": 0.015, "min_cagr_recent": 0.25, "min_share_ratio": 1.8},
        "hot": {"min_recent_share": 0.015, "min_slope_share": 0.0},
        "declining": {"consecutive_negative_years": 3},
        "score_weights": {"growth": 0.35, "acceleration": 0.25, "burst": 0.20, "novelty": 0.20},
        "burst": {"kleinberg_states": 2, "gamma": 1.0},
    },
}


def make_series(topic_counts: dict[int, dict[int, int]], corpus_per_year: int = 100_000) -> pd.DataFrame:
    """topic_counts: {topic_id: {year: count}}"""
    rows = []
    years = sorted({y for c in topic_counts.values() for y in c})
    for tid, per_year in topic_counts.items():
        for y in years:
            c = per_year.get(y, 0)
            rows.append({"topic_id": tid, "year": y, "count": c,
                         "corpus_total": corpus_per_year, "share": c / corpus_per_year})
    return pd.DataFrame(rows)


def run_tests() -> None:
    work = Path(MINI_CFG["pipeline"]["work_dir"])
    work.mkdir(parents=True, exist_ok=True)
    pd.Series({"last_complete_year": 2024}).to_json(work / "06_meta.json")

    # --- primitives ---
    assert abs(_cagr(100, 400, 3) - ((4.5 / 1.5) ** (1 / 3) - 1)) < 1e-6 or _cagr(100, 400, 3) > 0.5
    assert _cagr(100, 100, 3) < 0.01
    assert _ols_slope(np.arange(5.0), np.arange(5.0) * 2) > 0
    assert _ols_slope(np.arange(5.0), np.arange(5.0)[::-1]) < 0

    # burst: flat 5/y then jump to 50/y for 2 years must burst
    cnt = np.array([5, 5, 5, 5, 5, 50, 50, 5], dtype=float)
    corp = np.full(8, 10_000.0)
    intensity, idx = kleinberg_burst(cnt, corp, gamma=1.0)
    assert 5 in idx and 6 in idx, f"burst years wrong: {idx}"
    assert intensity > 0
    # flat series must not burst
    intensity2, idx2 = kleinberg_burst(np.full(8, 20.0), corp, gamma=1.0)
    assert idx2 == [] or intensity2 == 0.0

    # --- classification ---
    years = list(range(2017, 2025))  # B=2017–2021, R=2022–2024
    topics = {
        # EMERGING: tiny share, explosive growth in R
        1: {y: (10 if y < 2022 else c) for y, c in zip(years, [10, 12, 11, 10, 12, 60, 120, 240])},
        # HOT: big share, steadily rising
        2: {y: c for y, c in zip(years, [3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700])},
        # DECLINING: shrinking share every year
        3: {y: c for y, c in zip(years, [2000, 1800, 1600, 1400, 1200, 1000, 800, 600])},
        # STABLE
        4: {y: 500 for y in years},
        # too few recent articles → never EMERGING even if explosive
        5: {y: c for y, c in zip(years, [0, 0, 0, 0, 1, 2, 4, 8])},
    }
    s = make_series(topics)
    result = emerging(MINI_CFG, series=s)
    st = result.set_index("topic_id")["status"].to_dict()

    assert st[1] == "EMERGING", f"topic1 should be EMERGING, got {st[1]}"
    assert st[2] == "HOT", f"topic2 should be HOT, got {st[2]}"
    assert st[3] == "DECLINING", f"topic3 should be DECLINING, got {st[3]}"
    assert st[4] == "STABLE", f"topic4 should be STABLE, got {st[4]}"
    assert st[5] != "EMERGING", f"topic5 (noise) must not be EMERGING, got {st[5]}"

    # score sanity: emerging topic should outscore the stable one
    sc = result.set_index("topic_id")["emerging_score"].to_dict()
    assert sc[1] > sc[4], "emerging topic should score above stable"
    assert 0 <= min(sc.values()) and max(sc.values()) <= 100.001

    print("all emerging-engine tests passed ✓")


if __name__ == "__main__":
    run_tests()
