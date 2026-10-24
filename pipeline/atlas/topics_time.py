"""Yearly series per topic + journal/institution tables for Emerging v3, with backfill guard.

corpus_total counts ALL dated articles (assigned or not) — it is the share denominator.
Years after last_complete_year (v3 rule, unchanged) are kept for the Forecast v2 nowcast only:
06_partial_year (topic counts) and 06_months (articles per publication month, dates that agree with the
article year). They are computed after the cutoff and never feed back into it.
Outputs: 06_series, 06_topic_journal_year, 06_topic_org_year, 06_journal_first_year, 06_months,
06_partial_year, 06_meta.json (as_of_year and snapshot_at come from the snapshot cluster recorded in work_dir)
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.registry import journal_keys
from atlas.state import snapshot_at


def as_of_year(ecfg: dict, snapshot: date | None = None) -> int:
    """The year the run describes (config `as_of_year`; default the snapshot's calendar year — the snapshot the
    cluster step recorded, so a run continued days later describes the same year — else today's)."""
    v = ecfg.get("as_of_year")
    return int(v) if v is not None else (snapshot or date.today()).year


def last_complete_year(totals: pd.Series, ecfg: dict, snapshot: date | None = None) -> int:
    """Last year whose corpus total can be trusted as complete (EMERGING_SPEC §2, v3).

    1. `min_year_complete` set → it wins.
    2. candidate = min(last year with data, as_of_year − 1) — the running year is never complete
       and forward-dated issues are never the last complete year.
    3. while candidate's total < backfill_min_ratio × median(totals of the years in the calendar window
       candidate − backfill_ref_years … candidate − 1) and fewer than backfill_max_trim years were
       trimmed: candidate −= 1. A year in that window with no articles has no row in `totals`, so it is
       absent from the median (not counted as 0); if no year of the window has data, nothing is trimmed.
    """
    if ecfg.get("min_year_complete") is not None:
        return int(ecfg["min_year_complete"])
    totals = totals.sort_index()
    as_of = as_of_year(ecfg, snapshot)
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


def publication_months(docs: pd.DataFrame) -> pd.DataFrame:
    """year, month, count from `published` dates that agree with the article year (1970/lost dates drop out)."""
    if "published" not in docs.columns:
        return pd.DataFrame(columns=["year", "month", "count"])
    m = docs["published"].fillna("").astype(str).str.extract(r"^(\d{4})-(\d{2})")
    y = pd.to_numeric(m[0], errors="coerce")
    y = y.where(y <= 2400, y - 543)                               # Buddhist Era dates
    mon = pd.to_numeric(m[1], errors="coerce")
    ok = (y == docs["year"]) & mon.between(1, 12)
    out = pd.DataFrame({"year": docs.loc[ok, "year"].astype(int), "month": mon[ok].astype(int)})
    return out.groupby(["year", "month"]).size().rename("count").reset_index()


def article_orgs(cfg: dict) -> pd.DataFrame:
    """(article_id, org_key) for the institution rule: canonical institutions (emerging.breadth.org_unit
    "institution", definition v4, when institutions.enabled) or written affiliations ("affiliation", v3)."""
    work = Path(cfg["pipeline"]["work_dir"])
    try:
        authors = read_table(work / "01_authors.parquet")
    except FileNotFoundError:
        return pd.DataFrame(columns=["article_id", "org_key"])
    if cfg["emerging"]["breadth"]["org_unit"] == "institution" and cfg["institutions"]["enabled"]:
        from atlas.institutions import article_institutions    # lazy: the institutions module is the heavier import
        return article_institutions(cfg, authors).rename(columns={"inst_key": "org_key"})
    a = authors[["article_id", "org_key"]].copy()
    a["org_key"] = a["org_key"].fillna("").astype(str)
    return a[a["org_key"] != ""].drop_duplicates().reset_index(drop=True)


def build_series(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    docs = read_table(work / "02_docs.parquet", ["article_id", "year", "journal_name", "journal_key", "published"])
    n_articles = len(docs)
    docs = docs.assign(journal_name=journal_keys(docs))       # a journal is its key, never a (possibly varying) title
    fine = read_table(work / "04_fine_topics.parquet")
    authors = article_orgs(cfg)
    write_table(authors, work / "06_article_orgs.parquet")

    d = docs.merge(fine, on="article_id", how="left")
    d = d[d["year"].notna()].copy()
    d["year"] = d["year"].astype(int)
    d["fine_topic"] = d["fine_topic"].fillna(-1).astype(int)
    jfirst = (d.groupby("journal_name")["year"].min().rename("first_year").reset_index()
              .rename(columns={"journal_name": "journal"}))

    all_totals = d.groupby("year").size()
    snap = snapshot_at(cfg)                                      # recorded by cluster (now() without a record)
    cutoff = last_complete_year(all_totals, cfg["emerging"], snap.date())    # definition v3, unchanged
    how = {"method": "configured" if cfg["emerging"].get("min_year_complete") is not None else "median"}
    trimmed = [int(y) for y in all_totals.index if y > cutoff]  # forward-dated / incomplete years: kept in the
    later = d[(d["year"] > cutoff) & (d["fine_topic"] >= 0)]     # corpus, excluded from trends, used for nowcast
    partial = (later.groupby(["fine_topic", "year"]).size().rename("count").reset_index()
               .rename(columns={"fine_topic": "topic_id"}))
    d, totals = d[d["year"] <= cutoff], all_totals[all_totals.index <= cutoff]
    a = d[d["fine_topic"] >= 0]

    orgs = authors[authors["org_key"].astype(str) != ""].drop_duplicates(["article_id", "org_key"])
    a = a.assign(has_org=a["article_id"].isin(set(orgs["article_id"])))
    counts = (a.groupby(["fine_topic", "year"]).agg(count=("article_id", "size"), count_with_org=("has_org", "sum"))
              .reset_index().rename(columns={"fine_topic": "topic_id"}))
    try:                                                     # a topic with no article in the analysed years still exists
        known = set(read_table(work / "04_topic_info.parquet")["topic_id"].astype(int))
    except FileNotFoundError:
        known = set()
    grid = pd.MultiIndex.from_product([sorted(set(a["fine_topic"].unique()) | known), sorted(totals.index)],
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
    dated = docs[docs["year"].notna()].assign(year=lambda x: x["year"].astype(int))
    write_table(publication_months(dated), work / "06_months.parquet")
    write_table(partial, work / "06_partial_year.parquet")
    (work / "06_meta.json").write_text(json.dumps({
        "last_complete_year": int(cutoff),
        "n_articles": int(n_articles),                              # whole corpus = overview kpis.articles
        "as_of_year": as_of_year(cfg["emerging"], snap.date()),
        "snapshot_at": snap.isoformat(),
        "trimmed_years": trimmed,
        "years": [int(y) for y in totals.index],
        "totals": {str(int(y)): int(c) for y, c in totals.items()},
        "partial_totals": {str(int(y)): int(c) for y, c in all_totals.items() if y > cutoff},
        "completeness": how,
    }), encoding="utf-8")
    print(f"[series] {s['topic_id'].nunique()} topics × {len(totals)} years (≤ {cutoff}; "
          f"excluded years {trimmed or 'none'}) → 06_series")
    return s
