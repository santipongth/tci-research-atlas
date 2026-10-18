"""Phase 5a — yearly time series per fine topic, with backfill guard.

Output: work/06_series.parquet  (topic_id, year, count, corpus_total, share)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .io_utils import read_table, write_table


def build_series(cfg: dict, df: pd.DataFrame | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    if df is None:
        df = read_table(work / "02_docs.parquet")
    fine = read_table(work / "04_fine_topics.parquet")

    d = df[["article_id", "year"]].merge(fine, on="article_id")
    d = d.dropna(subset=["year"])
    d["year"] = d["year"].astype(int)

    counts = d.groupby(["fine_topic", "year"]).size().rename("count").reset_index()
    totals = d.groupby("year").size().rename("corpus_total").reset_index()

    # complete grid: every topic × every year (fill 0) so slopes/CAGR are well-defined
    years = sorted(totals["year"].unique())
    topics = sorted(counts["fine_topic"].unique())
    grid = pd.MultiIndex.from_product([topics, years], names=["fine_topic", "year"]).to_frame(index=False)
    s = grid.merge(counts, on=["fine_topic", "year"], how="left").fillna({"count": 0})
    s = s.merge(totals, on="year")
    s["share"] = s["count"] / s["corpus_total"]

    # backfill guard: drop last year if it looks incomplete (e.g. journals not yet ingested)
    cutoff = cfg["emerging"].get("min_year_complete")
    if cutoff is None:
        med = totals["corpus_total"].median()
        ymax = int(totals["year"].max())
        if totals.loc[totals["year"] == ymax, "corpus_total"].iloc[0] < 0.6 * med:
            print(f"[series] year {ymax} looks incomplete (backfill guard) — excluded from analysis windows")
            cutoff = ymax - 1
        else:
            cutoff = ymax
    s.attrs["last_complete_year"] = int(cutoff)
    s = s[s["year"] <= cutoff]

    s = s.rename(columns={"fine_topic": "topic_id"})
    write_table(s, work / "06_series.parquet")
    pd.Series({"last_complete_year": int(cutoff)}).to_json(work / "06_meta.json")
    print(f"[series] {s['topic_id'].nunique()} topics × {s['year'].nunique()} years -> 06_series.parquet")
    return s
