"""Yearly series per topic + journal/institution tables for Emerging v3, with backfill guard.

corpus_total counts ALL dated articles (assigned or not) — it is the share denominator.
Outputs: 06_series, 06_topic_journal_year, 06_topic_org_year, 06_journal_first_year, 06_meta.json
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table


def as_of_year(ecfg: dict) -> int:
    """The year the run describes (config `as_of_year`, default today's calendar year)."""
    v = ecfg.get("as_of_year")
    return int(v) if v is not None else date.today().year


def last_complete_year(totals: pd.Series, ecfg: dict) -> int:
    """Last year whose corpus total can be trusted as complete (EMERGING_SPEC §2, v3).

    1. `min_year_complete` set → it wins.
    2. candidate = min(last year with data, as_of_year − 1) — the running year is never complete
       and forward-dated issues are never the last complete year.
    3. while candidate's total < backfill_min_ratio × median(totals of the backfill_ref_years data
       years before it) and fewer than backfill_max_trim years were trimmed: candidate −= 1.
    """
    if ecfg.get("min_year_complete") is not None:
        return int(ecfg["min_year_complete"])
    totals = totals.sort_index()
    as_of = as_of_year(ecfg)
    first = int(totals.index.min())
    cand = min(int(totals.index.max()), as_of - 1)
    if cand < first:
        raise ValueError(f"emerging.as_of_year={as_of} leaves no complete year: the data starts in {first}")
    ratio, ref_n, max_trim = (float(ecfg["backfill_min_ratio"]), int(ecfg["backfill_ref_years"]),
                              int(ecfg["backfill_max_trim"]))
    trims = 0
    while trims < max_trim:
        ref = totals[(totals.index < cand) & (totals.index >= cand - ref_n)]
        if ref.empty or float(totals.get(cand, 0)) >= ratio * float(ref.median()):
            break
        print(f"[series] {cand} looks incomplete ({int(totals.get(cand, 0)):,} < {ratio:g} × median "
              f"{float(ref.median()):,.0f} of the {len(ref)} years before) — backfill guard trims it")
        cand -= 1
        trims += 1
    return cand


def build_series(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    docs = read_table(work / "02_docs.parquet")[["article_id", "year", "journal_name"]]
    fine = read_table(work / "04_fine_topics.parquet")
    try:
        authors = read_table(work / "01_authors.parquet")[["article_id", "org_key"]]
    except FileNotFoundError:
        authors = pd.DataFrame(columns=["article_id", "org_key"])

    d = docs.merge(fine, on="article_id", how="left")
    d = d[d["year"].notna()].copy()
    d["year"] = d["year"].astype(int)
    d["fine_topic"] = d["fine_topic"].fillna(-1).astype(int)
    jfirst = (d.groupby("journal_name")["year"].min().rename("first_year").reset_index()
              .rename(columns={"journal_name": "journal"}))

    totals = d.groupby("year").size()
    cutoff = last_complete_year(totals, cfg["emerging"])
    trimmed = [int(y) for y in totals.index if y > cutoff]     # forward-dated / incomplete years: kept in the
    d, totals = d[d["year"] <= cutoff], totals[totals.index <= cutoff]   # corpus, excluded from trends
    a = d[d["fine_topic"] >= 0]

    orgs = authors[authors["org_key"].astype(str) != ""].drop_duplicates(["article_id", "org_key"])
    a = a.assign(has_org=a["article_id"].isin(set(orgs["article_id"])))
    counts = (a.groupby(["fine_topic", "year"]).agg(count=("article_id", "size"), count_with_org=("has_org", "sum"))
              .reset_index().rename(columns={"fine_topic": "topic_id"}))
    grid = pd.MultiIndex.from_product([sorted(a["fine_topic"].unique()), sorted(totals.index)],
                                      names=["topic_id", "year"]).to_frame(index=False)
    s = grid.merge(counts, on=["topic_id", "year"], how="left").fillna({"count": 0, "count_with_org": 0})
    s[["count", "count_with_org"]] = s[["count", "count_with_org"]].astype(int)
    s = s.merge(totals.rename("corpus_total").reset_index(), on="year")
    s["share"] = s["count"] / s["corpus_total"]

    js = (a.groupby(["fine_topic", "journal_name", "year"]).size().rename("count").reset_index()
          .rename(columns={"fine_topic": "topic_id", "journal_name": "journal"}))
    oa = a[["article_id", "fine_topic", "year"]].merge(orgs, on="article_id")
    os_ = (oa.groupby(["fine_topic", "org_key", "year"]).size().rename("count").reset_index()
           .rename(columns={"fine_topic": "topic_id"}))

    write_table(s, work / "06_series.parquet")
    write_table(js, work / "06_topic_journal_year.parquet")
    write_table(os_, work / "06_topic_org_year.parquet")
    write_table(jfirst, work / "06_journal_first_year.parquet")
    (work / "06_meta.json").write_text(json.dumps({
        "last_complete_year": int(cutoff),
        "as_of_year": as_of_year(cfg["emerging"]),
        "trimmed_years": trimmed,
        "years": [int(y) for y in totals.index],
        "totals": {str(int(y)): int(c) for y, c in totals.items()},
    }), encoding="utf-8")
    print(f"[series] {s['topic_id'].nunique()} topics × {len(totals)} years (≤ {cutoff}; "
          f"excluded years {trimmed or 'none'}) → 06_series")
    return s
