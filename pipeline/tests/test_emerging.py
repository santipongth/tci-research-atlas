import numpy as np
import pandas as pd
import pytest

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
    assert (result["definition_version"] == 2).all()


def test_two_year_corpus_does_not_crash():
    s, js, os_, jf = make_inputs({1: {"counts": {2023: 50, 2024: 80}}, 2: {"counts": {2023: 5, 2024: 9}}},
                                 years=[2023, 2024])
    m = compute_emerging(s, 2024, ECFG, js, os_, jf)
    assert set(m["status"]) == {"LOW_DATA"}


def test_share_growth_recovers_known_rate():
    years = np.arange(2020, 2025)
    counts = 100 * 1.2 ** (years - 2020)
    g, lo, hi = share_growth(counts, np.full(5, 10_000.0), years, z=1.645)
    assert abs(g - 0.2) < 0.01 and lo < g < hi
    assert all(np.isnan(share_growth([0, 0, 0], [10, 10, 10], [1, 2, 3], 1.645)))


def test_kleinberg_detects_planted_burst_and_ignores_flat():
    corp = np.full(8, 10_000.0)
    assert kleinberg_burst(np.array([5, 5, 5, 5, 5, 50, 50, 5.0]), corp) == [5, 6]
    assert kleinberg_burst(np.full(8, 20.0), corp) == []
