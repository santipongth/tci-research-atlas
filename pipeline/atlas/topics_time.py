"""Yearly series per topic + journal/institution tables for Emerging v2, with backfill guard.

corpus_total counts ALL dated articles (assigned or not) — it is the share denominator.
Outputs: 06_series, 06_topic_journal_year, 06_topic_org_year, 06_journal_first_year, 06_meta.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table


def last_complete_year(totals: pd.Series, ecfg: dict) -> int:
    if ecfg.get("min_year_complete") is not None:
        return int(ecfg["min_year_complete"])
    ymax = int(totals.index.max())
    if len(totals) > 1 and totals.loc[ymax] < float(ecfg["backfill_min_ratio"]) * totals.median():
        print(f"[series] {ymax} looks incomplete (backfill guard) — analysis stops at {ymax - 1}")
        return ymax - 1
    return ymax


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
    d, totals = d[d["year"] <= cutoff], totals[totals.index <= cutoff]
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
        "years": [int(y) for y in totals.index],
        "totals": {str(int(y)): int(c) for y, c in totals.items()},
    }), encoding="utf-8")
    print(f"[series] {s['topic_id'].nunique()} topics × {len(totals)} years (≤ {cutoff}) → 06_series")
    return s
