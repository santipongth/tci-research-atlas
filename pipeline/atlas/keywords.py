"""Emerging keywords — term-level emergence, independent of clustering (Carley, Newman, Porter & Garner 2018).

Terms = author keywords (TH + EN), grouped by norm_key (case, spacing and lost tone marks fold together);
counts are documents per year. Windows R / B / W are the Emerging windows (emerging.*). A term is
emerging when it is
  novel       share_R / share_B ≥ novelty_min_ratio (B smoothed by half an article) and it is not a
              generic term (in ≤ max_doc_share of all documents)
  persistent  present in ≥ min_active_years of the W years
  communal    ≥ min_orgs institutions in R, and not journal-driven (≥ min_journals journals in R and
              < max_new_journal_share of its R documents from journals that entered in R)
  growing     lower CI bound of its share growth (emerging.share_growth, same as topics) > min_growth_lo
  big enough  ≥ min_docs_recent documents in R
no_baseline marks terms absent from B: their share_ratio only reflects the smoothing (published as null).
Output: work/07_keywords (candidates, emerging first).
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.emerging import share_growth
from atlas.io_utils import read_table, write_table
from atlas.thai import norm_key

KEYWORD_COLUMNS = ["term", "key", "count_recent", "count_baseline", "share_ratio", "no_baseline", "growth", "growth_lo",
                   "growth_hi", "n_active_years", "n_orgs_R", "n_journals_R", "new_journal_share",
                   "journal_driven", "topic_id", "emerging"]


def keyword_rows(docs: pd.DataFrame) -> pd.DataFrame:
    """One row per (article, keyword key): article_id, year, journal, key, term."""
    rows = []
    for aid, year, journal, th, en in zip(docs["article_id"], docs["year"], docs["journal_name"],
                                          docs["keywords_th"].fillna("").astype(str),
                                          docs["keywords_en"].fillna("").astype(str)):
        if pd.isna(year):
            continue
        seen = set()
        for term in (t.strip() for t in f"{th};{en}".split(";")):
            key = norm_key(term)
            if len(key) >= 2 and key not in seen:
                seen.add(key)
                rows.append((aid, int(year), journal, key, term))
    return pd.DataFrame(rows, columns=["article_id", "year", "journal", "key", "term"])


def emerging_keywords(kw: pd.DataFrame, totals: pd.Series, last_year: int, ecfg: dict, kcfg: dict,
                      orgs: pd.DataFrame, jfirst: pd.DataFrame, topics: pd.DataFrame | None = None) -> pd.DataFrame:
    """kw: keyword_rows() · totals: dated articles per year · orgs: article_id, org_key · jfirst: journal, first_year."""
    wR, wB, wW = int(ecfg["recent_window"]), int(ecfg["baseline_window"]), int(ecfg["trend_window"])
    R = list(range(last_year - wR + 1, last_year + 1))
    B = list(range(last_year - wR - wB + 1, last_year - wR + 1))
    W = list(range(last_year - wW + 1, last_year + 1))
    ci, max_log = float(ecfg["ci_level"]), float(ecfg["max_abs_log_growth"])
    kw = kw[kw["year"] <= last_year]
    n_docs = float(totals[totals.index <= last_year].sum())
    N_R, N_B = float(totals.reindex(R, fill_value=0).sum()), float(totals.reindex(B, fill_value=0).sum())
    if kw.empty or N_R == 0:
        return pd.DataFrame(columns=KEYWORD_COLUMNS)

    by_year = kw.groupby(["key", "year"]).size().unstack(fill_value=0)
    cnt_R = by_year.reindex(columns=R, fill_value=0).sum(axis=1)
    cnt_B = by_year.reindex(columns=B, fill_value=0).sum(axis=1)
    doc_share = by_year.sum(axis=1) / max(n_docs, 1.0)
    eps_B = 0.5 / max(N_B, 1.0)
    ratio = (cnt_R / N_R + eps_B) / (cnt_B / max(N_B, 1.0) + eps_B)
    active = (by_year.reindex(columns=W, fill_value=0) > 0).sum(axis=1)
    cand = ((cnt_R >= int(kcfg["min_docs_recent"])) & (doc_share <= float(kcfg["max_doc_share"]))
            & (ratio >= float(kcfg["novelty_min_ratio"])) & (active >= int(kcfg["min_active_years"])))
    keys = cand[cand].index
    if not len(keys):
        return pd.DataFrame(columns=KEYWORD_COLUMNS)

    kR = kw[kw["key"].isin(keys) & kw["year"].isin(R)]
    new_j = set(jfirst.loc[jfirst["first_year"] >= R[0], "journal"])
    org_R = kR[["key", "article_id"]].merge(orgs[orgs["org_key"].astype(str) != ""], on="article_id")
    n_orgs = org_R.groupby("key")["org_key"].nunique()
    n_j = kR.groupby("key")["journal"].nunique()
    new_share = kR.assign(new=kR["journal"].isin(new_j)).groupby("key")["new"].mean()
    display = kw[kw["key"].isin(keys)].groupby("key")["term"].agg(lambda s: Counter(s).most_common(1)[0][0])
    topic_of: dict[str, int] = {}
    if topics is not None and len(topics):
        tk = kR.merge(topics, on="article_id")
        tk = tk[tk["fine_topic"] >= 0]
        topic_of = tk.groupby("key")["fine_topic"].agg(lambda s: int(s.value_counts().index[0])).to_dict()
    tot_W = totals.reindex(W, fill_value=0).to_numpy(dtype=float)

    rows = []
    for key in keys:
        counts_W = by_year.loc[key].reindex(W, fill_value=0).to_numpy(dtype=float)
        g, lo, hi = share_growth(counts_W, tot_W, np.array(W), ci, max_log)
        nj, no, ns = int(n_j.get(key, 0)), int(n_orgs.get(key, 0)), float(new_share.get(key, 0.0))
        driven = nj < int(kcfg["min_journals"]) or ns >= float(kcfg["max_new_journal_share"])
        emerging = (bool(math.isfinite(lo) and lo > float(kcfg["min_growth_lo"]))
                    and no >= int(kcfg["min_orgs"]) and not driven)
        rows.append({"term": display[key], "key": key, "count_recent": int(cnt_R[key]),
                     "count_baseline": int(cnt_B[key]), "share_ratio": float(ratio[key]),
                     "no_baseline": bool(cnt_B[key] == 0),
                     "growth": g, "growth_lo": lo, "growth_hi": hi, "n_active_years": int(active[key]),
                     "n_orgs_R": no, "n_journals_R": nj, "new_journal_share": ns, "journal_driven": driven,
                     "topic_id": topic_of.get(key, -1), "emerging": emerging})
    out = pd.DataFrame(rows, columns=KEYWORD_COLUMNS)
    out["_lo"] = out["growth_lo"].fillna(-math.inf)
    out = out.sort_values(["emerging", "_lo", "count_recent", "key"], ascending=[False, False, False, True])
    return out.drop(columns="_lo").reset_index(drop=True)


def keywords(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    if not cfg["keywords"]["enabled"]:
        out = pd.DataFrame(columns=KEYWORD_COLUMNS)
        write_table(out, work / "07_keywords.parquet")
        return out
    docs = read_table(work / "02_docs.parquet")
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    totals = pd.Series({int(y): int(n) for y, n in meta["totals"].items()}).sort_index()
    try:
        orgs = read_table(work / "01_authors.parquet")[["article_id", "org_key"]]
    except FileNotFoundError:
        orgs = pd.DataFrame(columns=["article_id", "org_key"])
    out = emerging_keywords(keyword_rows(docs), totals, int(meta["last_complete_year"]), cfg["emerging"],
                            cfg["keywords"], orgs.drop_duplicates(), read_table(work / "06_journal_first_year.parquet"),
                            read_table(work / "04_fine_topics.parquet"))
    write_table(out, work / "07_keywords.parquet")
    print(f"[keywords] {len(out)} candidate terms, {int(out['emerging'].sum()) if len(out) else 0} emerging")
    return out
