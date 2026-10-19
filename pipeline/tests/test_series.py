import json

import pandas as pd
import pytest

from atlas.config import load_config
from atlas.io_utils import read_table, write_table
from atlas.topics_time import build_series, last_complete_year

ECFG = load_config(None)["emerging"]


def test_series_backfill_guard_and_tables(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["emerging"]["as_of_year"] = 2026                  # explicit: no wall-clock dependence
    work = tmp_path / "work"
    rows, topics = [], []
    for y in range(2019, 2025):
        n = 2 if y == 2024 else 10                         # 2024 incomplete (< 60% of median)
        for i in range(n):
            aid = f"{y}-{i}"
            rows.append({"article_id": aid, "year": y, "journal_name": "jA" if i % 2 else "jB"})
            topics.append({"article_id": aid, "fine_topic": 0 if i < n / 2 else -1})
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    write_table(pd.DataFrame(topics), work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows[::2]], "org_key": "orgX"}),
                work / "01_authors.parquet")
    s = build_series(cfg)
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    assert meta["last_complete_year"] == 2023 and s["year"].max() == 2023
    assert meta["trimmed_years"] == [2024] and meta["as_of_year"] == 2026
    assert meta["n_articles"] == len(rows)                    # whole corpus (the KPI) next to the analysed totals
    assert set(s["topic_id"]) == {0}                          # unassigned (-1) never becomes a topic
    assert (s["corpus_total"] == 10).all()                    # ... but counts in the denominator
    assert (s["count"] == 5).all() and (s["count_with_org"] <= s["count"]).all()
    jf = read_table(work / "06_journal_first_year.parquet").set_index("journal")["first_year"]
    assert jf.to_dict() == {"jA": 2019, "jB": 2019}
    assert len(read_table(work / "06_topic_org_year.parquet")) > 0


# ---- v3 / F4: last-complete-year guard (as_of_year + rolling reference window, up to backfill_max_trim)
def _lcy(totals: dict, **over) -> int:
    return last_complete_year(pd.Series(totals).sort_index(), {**ECFG, **over})


def _growing(first=2005, last=2025, base=3000, rate=0.12):
    return {y: int(base * (1 + rate) ** (y - first)) for y in range(first, last + 1)}


def test_growing_corpus_with_quarter_complete_last_year_is_trimmed():
    tot = _growing()
    tot[2025] = int(tot[2025] * 0.25)
    assert _lcy(tot, as_of_year=2026) == 2024


def test_forward_dated_next_year_and_partial_current_year_are_both_excluded():
    tot = _growing()
    tot[2026] = int(tot[2025] * 1.05 * 0.75)           # running year (as_of) — never complete
    tot[2027] = 400                                     # forward-dated issues
    assert _lcy(tot, as_of_year=2026) == 2025


def test_stable_complete_history_keeps_last_year():
    assert _lcy({y: 1000 for y in range(2015, 2025)}, as_of_year=2025) == 2024


def test_running_year_is_never_complete_even_when_large():
    assert _lcy({y: 1000 for y in range(2015, 2026)}, as_of_year=2025) == 2024


def test_backfill_trims_at_most_max_trim_years():
    # back-filling ramp: the most recent years are progressively less complete
    tot = {**{y: 1000 for y in range(2010, 2022)}, 2022: 500, 2023: 300, 2024: 100}
    assert _lcy(tot, as_of_year=2025) == 2022                  # 2024, 2023 trimmed, then the cap (2) stops
    assert _lcy(tot, as_of_year=2025, backfill_max_trim=4) == 2021
    assert _lcy(tot, as_of_year=2025, backfill_max_trim=0) == 2024


def test_min_year_complete_override_wins():
    tot = _growing()
    tot[2025] = 10
    assert _lcy(tot, as_of_year=2026, min_year_complete=2019) == 2019


def test_as_of_before_any_data_is_an_error():
    with pytest.raises(ValueError, match="as_of_year"):
        _lcy({y: 1000 for y in range(2015, 2025)}, as_of_year=2010)


# ---- P1: partial-year tables for the nowcast (definition v3 unchanged)
def test_publication_months_and_partial_year(make_cfg, tmp_path):
    from atlas.topics_time import publication_months

    docs = pd.DataFrame({"year": [2024, 2024, 2025, 2016, 2014],
                         "published": ["2024-03-02", "2024-11-30", "2025-02-01", "2559-07-01", "1970-01-01"]})
    m = publication_months(docs.astype({"year": "Int64"}))
    assert sorted(map(tuple, m[["year", "month"]].to_numpy().tolist())) == [(2016, 7), (2024, 3), (2024, 11), (2025, 2)]
    cfg = make_cfg(tmp_path)
    cfg["emerging"]["as_of_year"] = 2026
    work = tmp_path / "work"
    rows, topics = [], []
    for y in range(2019, 2025):
        n = 2 if y == 2024 else 10
        for i in range(n):
            rows.append({"article_id": f"{y}-{i}", "year": y, "journal_name": "jA", "published": f"{y}-0{i % 9 + 1}-01"})
            topics.append({"article_id": f"{y}-{i}", "fine_topic": 0})
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    write_table(pd.DataFrame(topics), work / "04_fine_topics.parquet")
    build_series(cfg)
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    assert meta["last_complete_year"] == 2023 and meta["trimmed_years"] == [2024]       # the v3 rule, unchanged
    assert meta["partial_totals"] == {"2024": 2} and meta["completeness"] == {"method": "median"}
    assert read_table(work / "06_partial_year.parquet").to_dict("records") == [{"topic_id": 0, "year": 2024, "count": 2}]
    assert read_table(work / "06_months.parquet")["count"].sum() == 52


def test_as_of_year_comes_from_the_snapshot_recorded_at_cluster_time(make_cfg, tmp_path):
    """A run continued days later (here: in the next year) keeps the snapshot the cluster step recorded."""
    cfg = make_cfg(tmp_path)                                  # emerging.as_of_year: null → the snapshot's year
    work = tmp_path / "work"
    rows = [{"article_id": f"{y}-{i}", "year": y, "journal_name": "jA"} for y in range(2018, 2026) for i in range(10)]
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows], "fine_topic": 0}),
                work / "04_fine_topics.parquet")
    (work / "04_topics_meta.json").write_text(json.dumps({"release": "2025Q2",
                                                          "snapshot_at": "2025-05-02T09:00:00+07:00"}), encoding="utf-8")
    build_series(cfg)
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    assert meta["as_of_year"] == 2025 and meta["last_complete_year"] == 2024 and meta["trimmed_years"] == [2025]
    assert meta["snapshot_at"] == "2025-05-02T09:00:00+07:00"
