import math

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from scipy.stats import t as student_t

from atlas.config import load_config
from atlas.emerging import STATUSES, compute_emerging, kleinberg_burst, share_growth

ECFG = load_config(None)["emerging"]          # tests lock the shipped defaults
YEARS = list(range(2015, 2025))               # last complete 2024 → R 2022–24, W 2020–24, B 2017–21
OLD4 = [("j_old_a", .25), ("j_old_b", .25), ("j_old_c", .25), ("j_old_d", .25)]


def make_inputs(specs, years=YEARS, corpus=100_000):
    rows, jrows, orows = [], [], []
    for tid, sp in specs.items():
        orgs = sp.get("orgs", 5)
        for y in years:
            c = int(sp["counts"].get(y, 0))
            rows.append(dict(topic_id=tid, year=y, count=c, corpus_total=corpus, share=c / corpus,
                             count_with_org=c if orgs else 0))
            for j, frac in sp.get("journals", OLD4):
                if round(c * frac):
                    jrows.append(dict(topic_id=tid, journal=j, year=y, count=round(c * frac)))
            for o in range(orgs):
                if c:
                    orows.append(dict(topic_id=tid, org_key=f"org{o}", year=y, count=max(1, c // orgs)))
    js = pd.DataFrame(jrows, columns=["topic_id", "journal", "year", "count"])
    os_ = pd.DataFrame(orows, columns=["topic_id", "org_key", "year", "count"])
    jf = js.groupby("journal")["year"].min().rename("first_year").reset_index()
    return pd.DataFrame(rows), js, os_, jf


EM = {**{y: 10 for y in range(2015, 2020)}, 2020: 15, 2021: 25, 2022: 60, 2023: 120, 2024: 240}
SPECS = {
    1: {"counts": EM},                                                            # EMERGING
    2: {"counts": {2022: 60, 2023: 120, 2024: 240}, "journals": [("j_new", 1.0)], "orgs": 1},  # new journal → WATCH
    3: {"counts": {y: round(3000 * 1.03 ** (y - 2015)) for y in YEARS}},          # large & growing → HOT
    4: {"counts": {y: round(2000 * 0.85 ** (y - 2015)) for y in YEARS}},          # → DECLINING
    5: {"counts": {y: 2500 for y in YEARS}},                                      # perfectly flat → STABLE
    6: {"counts": {2022: 3, 2023: 5, 2024: 8}},                                   # tiny → LOW_DATA
    7: {"counts": {2015: 40, 2016: 40}},                                          # nothing in W → LOW_DATA, no crash
    8: {"counts": EM, "journals": [("j_old_a", 1.0)]},                            # one journal → WATCH
    9: {"counts": EM, "orgs": 0},                                                 # affiliations unknown → rule skipped
}
EXPECTED = {1: "EMERGING", 2: "WATCH", 3: "HOT", 4: "DECLINING", 5: "STABLE", 6: "LOW_DATA",
            7: "LOW_DATA", 8: "WATCH", 9: "EMERGING"}


@pytest.fixture(scope="module")
def result():
    s, js, os_, jf = make_inputs(SPECS)
    return compute_emerging(s, 2024, ECFG, js, os_, jf, coherence={1: 0.9, 5: 0.8}).set_index("topic_id")


@pytest.mark.parametrize("tid", sorted(EXPECTED))
def test_status_rules(result, tid):
    assert result.loc[tid, "status"] == EXPECTED[tid]


def test_journal_driven_flag(result):
    assert bool(result.loc[2, "journal_driven"]) and bool(result.loc[8, "journal_driven"])
    assert not bool(result.loc[1, "journal_driven"])
    assert result.loc[2, "new_journal_share"] == 1.0


def test_scores_bounded_and_ranked(result):
    assert result["emerging_score"].between(0, 100.0001).all()
    assert result.loc[1, "emerging_score"] > result.loc[5, "emerging_score"]
    assert set(result["status"]) <= set(STATUSES)
    assert (result["definition_version"] == 3).all()


def test_two_year_corpus_does_not_crash():
    s, js, os_, jf = make_inputs({1: {"counts": {2023: 50, 2024: 80}}, 2: {"counts": {2023: 5, 2024: 9}}},
                                 years=[2023, 2024])
    m = compute_emerging(s, 2024, ECFG, js, os_, jf)
    assert set(m["status"]) == {"LOW_DATA"}


CI, MAXLOG = ECFG["ci_level"], ECFG["max_abs_log_growth"]
W5 = list(range(2020, 2025))


def test_share_growth_recovers_known_rate():
    years = np.arange(2020, 2025)
    counts = 100 * 1.2 ** (years - 2020)
    g, lo, hi = share_growth(counts, np.full(5, 10_000.0), years, CI, MAXLOG)
    assert abs(g - 0.2) < 0.01 and lo < g < hi
    assert all(np.isnan(share_growth([0, 0, 0], [10, 10, 10], [1, 2, 3], CI, MAXLOG)))


# ---- v3 / F1: separation (all positives in one year) is "not estimable", never a huge number
@pytest.mark.parametrize("counts", [[0, 0, 0, 0, 40], [40, 0, 0, 0, 0], [0, 3, 0, 0, 0]])
def test_share_growth_single_positive_year_is_not_estimable(counts):
    out = share_growth(counts, [1000] * 5, W5, CI, MAXLOG)
    assert all(math.isnan(v) for v in out)


def test_share_growth_regular_series_is_finite():
    g, lo, hi = share_growth([10, 12, 15, 18, 22], [1000] * 5, W5, CI, MAXLOG)
    assert all(math.isfinite(v) for v in (g, lo, hi)) and lo < g < hi


def test_share_growth_insane_bounds_are_not_estimable():
    # the same regular series, but with a sanity bound so tight that b ± q·se exceeds it
    assert all(math.isnan(v) for v in share_growth([10, 12, 15, 18, 22], [1000] * 5, W5, CI, 0.05))


def test_share_growth_numerical_failure_is_nan_but_unexpected_errors_propagate(monkeypatch):
    import statsmodels.api as sm

    def linalg_fail(*a, **k):
        raise np.linalg.LinAlgError("singular")
    monkeypatch.setattr(sm, "GLM", linalg_fail)
    assert all(math.isnan(v) for v in share_growth([10, 12, 15, 18, 22], [1000] * 5, W5, CI, MAXLOG))

    def bug(*a, **k):
        raise RuntimeError("a real bug")
    monkeypatch.setattr(sm, "GLM", bug)
    with pytest.raises(RuntimeError, match="a real bug"):
        share_growth([10, 12, 15, 18, 22], [1000] * 5, W5, CI, MAXLOG)


# ---- v3 / F2: honest interval — Student-t quantile when phi > 1, normal when phi == 1
def _quasi_poisson_se(counts, totals, years):
    import warnings

    import statsmodels.api as sm

    t = np.asarray(years, dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")              # an exact curve triggers a "perfect prediction" warning
        fit = sm.GLM(np.asarray(counts, dtype=float), sm.add_constant(t - t.mean(), has_constant="add"),
                     family=sm.families.Poisson(), offset=np.log(np.asarray(totals, dtype=float))).fit()
    phi = max(1.0, float(fit.pearson_chi2) / float(fit.df_resid))
    return float(fit.params[1]), float(fit.bse[1]) * math.sqrt(phi), phi, float(fit.df_resid)


def test_share_growth_uses_t_quantile_when_overdispersed():
    counts, totals = [100, 60, 140, 80, 160], [10_000] * 5
    b, se, phi, df = _quasi_poisson_se(counts, totals, W5)
    assert phi > 1
    g, lo, hi = share_growth(counts, totals, W5, 0.90, MAXLOG)
    q_t, q_z = student_t.ppf(0.95, df), norm.ppf(0.95)
    assert math.log1p(g) == pytest.approx(b)
    assert math.log1p(hi) - math.log1p(g) == pytest.approx(q_t * se, rel=1e-9)
    assert math.log1p(g) - math.log1p(lo) == pytest.approx(q_t * se, rel=1e-9)
    assert q_t * se > q_z * se * 1.3                       # t(3) widens the interval by ~43%


def test_share_growth_uses_normal_quantile_when_poisson():
    years = np.arange(2020, 2025)
    counts, totals = 100 * 1.2 ** (years - 2020), [10_000] * 5   # exact curve → chi2 ≈ 0 → phi = 1
    b, se, phi, _ = _quasi_poisson_se(counts, totals, years)
    assert phi == 1.0
    g, lo, hi = share_growth(counts, totals, years, 0.90, MAXLOG)
    assert math.log1p(hi) - math.log1p(g) == pytest.approx(norm.ppf(0.95) * se, rel=1e-9)


# ---- v3 / F1 through compute_emerging: new topics never produce huge numbers or crash
STABLE_BIG = {"counts": {y: 2500 for y in YEARS}}
GROWTH_COLS = ["share_growth", "share_growth_lo", "share_growth_hi", "acceleration", "cagr_recent",
               "emerging_score", "novelty", "burst_frac"]


def _run(specs):
    s, js, os_, jf = make_inputs(specs)
    return compute_emerging(s, 2024, ECFG, js, os_, jf).set_index("topic_id")


def test_topic_born_in_last_complete_year_is_low_data_without_huge_numbers():
    # share_ratio is (share_R + eps) / eps here by definition (no baseline) and is deliberately not checked
    m = _run({1: {"counts": {2024: 40}}, 2: STABLE_BIG})
    row = m.loc[1]
    assert row["status"] == "LOW_DATA"
    assert all(math.isnan(row[c]) for c in ("share_growth", "share_growth_lo", "share_growth_hi"))
    assert math.isfinite(row["acceleration"]) and abs(row["acceleration"]) < 5
    vals = row[GROWTH_COLS].astype(float)
    assert (vals[vals.notna()].abs() < 1e3).all(), vals.to_dict()


def test_topic_born_in_last_baseline_year_has_moderate_acceleration():
    m = _run({1: {"counts": {2021: 1, 2022: 60, 2023: 120, 2024: 240}}, 2: STABLE_BIG})
    acc = float(m.loc[1, "acceleration"])
    assert math.isfinite(acc) and abs(acc) < 5


def test_all_recent_articles_in_last_year_does_not_crash():
    m = _run({1: {"counts": {**{y: 10 for y in range(2015, 2022)}, 2024: 300}}, 2: {"counts": {2024: 300}},
              3: STABLE_BIG})
    assert set(m["status"]) <= set(STATUSES)
    assert m[GROWTH_COLS].abs().max().max() < 1e3


def test_zero_topics_writes_empty_table_with_contract_columns(tmp_path):
    import json

    from atlas.emerging import EMERGING_COLUMNS, emerging
    from atlas.io_utils import read_table, write_table

    work = tmp_path / "work"
    s = pd.DataFrame(columns=["topic_id", "year", "count", "corpus_total", "share", "count_with_org"])
    js = pd.DataFrame(columns=["topic_id", "journal", "year", "count"])
    os_ = pd.DataFrame(columns=["topic_id", "org_key", "year", "count"])
    jf = pd.DataFrame(columns=["journal", "first_year"])
    work.mkdir()
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024}), encoding="utf-8")
    write_table(pd.DataFrame(columns=["topic_id", "coherence"]), work / "04_topic_info.parquet")
    for name, df in [("06_series", s), ("06_topic_journal_year", js), ("06_topic_org_year", os_),
                     ("06_journal_first_year", jf)]:
        write_table(df, work / f"{name}.parquet")
    emerging({"pipeline": {"work_dir": str(work)}, "emerging": ECFG})
    out = read_table(work / "07_emerging.parquet")
    assert len(out) == 0 and list(out.columns) == EMERGING_COLUMNS


# ---- v3 / F3: orgs_unverified exposes the skipped institution criterion
def test_orgs_unverified_flag(result):
    assert bool(result.loc[9, "orgs_unverified"]) and result.loc[9, "status"] == "EMERGING"
    assert not bool(result.loc[1, "orgs_unverified"])


def test_kleinberg_detects_planted_burst_and_ignores_flat():
    corp = np.full(8, 10_000.0)
    assert kleinberg_burst(np.array([5, 5, 5, 5, 5, 50, 50, 5.0]), corp) == [5, 6]
    assert kleinberg_burst(np.full(8, 20.0), corp) == []
