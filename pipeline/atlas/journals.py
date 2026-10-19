"""Step `journals` (after methods): the editors' journal module → work/13_* (published by export).

Journals come from the corpus (atlas.registry.journal_key), optionally named by registry/journals.csv.
Windows (from 06_meta.json last_complete_year): W = the last journals.window_years complete years (metrics),
R / B = the emerging recent / baseline windows (topic shifts, special issues).

  13_journals              one row per journal: identity (+ registry), counts, D2 completeness score, D3 owner,
                           in-house share, institutions, effective number of institutions, foreign share,
                           affiliation coverage, methods coverage, low_data (< journals.min_articles in W → every
                           rate is null)
  13_journal_years         journal_key, year, articles (dated years ≤ last_complete_year)
  13_journal_topics        journal_key, topic_id, count, share (W, every topic — export keeps the top ones)
  13_journal_drift         journal_key, year, articles, distance (D1)
  13_journal_shifts        journal_key, topic_id, kind, share_before, share_after (B → R)
  13_journal_peers         journal_key, peer_key, similarity (D4)
  13_journal_completeness  journal_key, component, rate, n (D2)
  13_journal_methods       journal_key, method, count, share (D7, share of the articles naming a method)
  13_special_issue         topic_id, hosts, top_host_share, articles_R (D5)
  13_journal_opportunities journal_key, topic_id, reason, journal_articles, hosts (D5)
  13_journals_meta.json    windows, registry use, counts
Author rows are read here and only aggregates leave this step (PDPA).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.journal_metrics import article_completeness, author_metrics, completeness_table, owners
from atlas.journal_topics import (
    in_years,
    journal_opportunities,
    peer_journals,
    scope_drift,
    special_issue,
    topic_mix,
    topic_shifts,
)
from atlas.methods import shares_of
from atlas.orgs import org_display_names
from atlas.registry import journal_code, journal_keys, journal_path, load_registry, match_registry

SUMMARY_COLUMNS = [
    "journal_key", "code", "path", "name_th", "name_en", "issn", "eissn", "tci_tier", "tci_field", "publisher",
    "url", "in_registry", "articles", "articles_window", "articles_recent", "first_year", "last_year", "active",
    "low_data", "completeness", "owner_name", "owner_source", "owner_share", "owner_matched", "inhouse_share",
    "with_org", "n_orgs", "effective_orgs", "foreign_share", "affiliation_coverage", "methods_coverage",
]
RATE_COLUMNS = ["completeness", "inhouse_share", "effective_orgs", "foreign_share", "methods_coverage", "owner_share"]
AUTHOR_COLUMNS = ["article_id", "affiliation_th", "affiliation_en", "org_key"]
REF_COLUMNS = ["article_id", "lang", "translated"]


def _optional(path: Path, columns: list[str] | None = None) -> pd.DataFrame | None:
    try:
        return read_table(path)
    except FileNotFoundError:
        return pd.DataFrame(columns=columns) if columns is not None else None


def windows(cfg: dict, last: int) -> dict[str, tuple[int, int]]:
    e, j = cfg["emerging"], cfg["journals"]
    r0 = last - int(e["recent_window"]) + 1
    return {"W": (last - int(j["window_years"]) + 1, last), "R": (r0, last),
            "B": (r0 - int(e["baseline_window"]), r0 - 1)}


def journal_methods(ma: pd.DataFrame | None, arts_w: pd.DataFrame, eligible: set[str]) -> tuple[pd.DataFrame, dict]:
    """(journal_key, method, count, share) + {journal_key: coverage} for eligible journals (window articles)."""
    cols = ["journal_key", "method", "count", "share"]
    if ma is None or ma.empty:
        return pd.DataFrame(columns=cols), {}
    m = ma[["article_id", "methods"]].merge(arts_w[["article_id", "journal_key"]], on="article_id")
    rows, coverage = [], {}
    for jk, g in m[m["journal_key"].isin(eligible)].groupby("journal_key"):
        counts, n_with = shares_of(g["methods"])
        coverage[jk] = n_with / len(g) if len(g) else np.nan
        rows += [{"journal_key": jk, "method": k, "count": n, "share": n / n_with} for k, n in counts.items()]
    return pd.DataFrame(rows, columns=cols), coverage


def journals(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    jcfg = cfg["journals"]
    meta6 = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    win = windows(cfg, int(meta6["last_complete_year"]))
    W, R, B = win["W"], win["R"], win["B"]

    arts = read_table(work / "01_articles.parquet")
    arts = arts.assign(journal_key=journal_keys(arts), year=pd.to_numeric(arts["year"], errors="coerce"))
    arts = arts[arts["journal_key"] != ""].reset_index(drop=True)
    authors = _optional(work / "01_authors.parquet", AUTHOR_COLUMNS)
    refs = _optional(work / "01_references.parquet", REF_COLUMNS)

    registry, warnings = load_registry(jcfg["registry_path"])
    matched, more = match_registry(arts["journal_key"].unique(), registry)
    for w in warnings + more:
        print(f"[journals] WARNING: {w}")

    in_w = arts["year"].between(*W).fillna(False).astype(bool)
    arts_w = arts[in_w]
    counts_w = arts_w.groupby("journal_key").size()
    eligible = set(counts_w[counts_w >= int(jcfg["min_articles"])].index)

    ids_w = set(arts_w["article_id"])
    comp = article_completeness(arts_w, refs[refs["article_id"].isin(ids_w)], authors[authors["article_id"].isin(ids_w)])
    comp_long, score = completeness_table(comp, arts_w.set_index("article_id")["journal_key"],
                                          jcfg["completeness_weights"])
    reg_owner = {k: str(r.get("publisher_org") or "") for k, r in matched.items()}
    own = owners(arts_w, authors, reg_owner, float(jcfg["owner_min_share"]), org_display_names(authors))
    amet = author_metrics(arts_w, authors, own)

    docs = read_table(work / "02_docs.parquet")[["article_id"]]
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    jt = (docs.merge(fine, on="article_id").merge(arts[["article_id", "journal_key", "year"]], on="article_id")
          .rename(columns={"fine_topic": "topic_id"}))
    jt = jt[(jt["topic_id"] >= 0) & jt["year"].notna()].astype({"topic_id": int, "year": int})
    mix = topic_mix(jt, *W)
    peers = peer_journals(mix, eligible, int(jcfg["peers_k"]), float(jcfg["peers_min_similarity"]))
    drift = scope_drift(jt, list(range(W[0], W[1] + 1)), int(jcfg["drift_reference_years"]),
                        int(jcfg["drift_min_articles"]))
    shifts = topic_shifts(jt, B, R, int(jcfg["shift_topics"]), int(jcfg["min_articles"]))
    status = read_table(work / "07_emerging.parquet").set_index("topic_id")["status"]
    edges = _optional(work / "09_edges.parquet", ["s", "t", "w"])
    opps = special_issue(in_years(jt, *R), status, list(jcfg["special_issue_statuses"]),
                         int(jcfg["special_issue_min_host_articles"]), int(jcfg["special_issue_max_hosts"]))
    jopps = journal_opportunities(opps, mix, edges, int(jcfg["scope_topics"]), int(jcfg["special_issue_per_journal"]))
    jmeth, mcov = journal_methods(_optional(work / "12_methods_articles.parquet"), arts_w, eligible)

    dated = arts[arts["year"].notna() & (arts["year"] <= W[1])].astype({"year": int})
    years = dated.groupby(["journal_key", "year"]).size().rename("articles").reset_index()
    span = arts.dropna(subset=["year"]).groupby("journal_key")["year"].agg(["min", "max"])
    recent = arts[arts["year"].between(*R).fillna(False).astype(bool)].groupby("journal_key").size()
    total = arts.groupby("journal_key").size()
    own_i, am_i = own.set_index("journal_key"), amet.set_index("journal_key")
    rows = []
    for jk in sorted(total.index):
        reg = matched.get(jk, {})
        o = own_i.loc[jk] if jk in own_i.index else None
        a = am_i.loc[jk] if jk in am_i.index else None
        tier = reg.get("tci_tier")
        rows.append({
            "journal_key": jk, "code": journal_code(jk), "path": journal_path(jk),
            "name_th": reg.get("name_th", ""), "name_en": reg.get("name_en", ""), "issn": reg.get("issn", ""),
            "eissn": reg.get("eissn", ""), "tci_tier": int(tier) if tier is not None and pd.notna(tier) else pd.NA,
            "tci_field": reg.get("tci_field", ""), "publisher": reg.get("publisher_org", ""),
            "url": reg.get("url", ""), "in_registry": bool(reg),
            "articles": int(total[jk]), "articles_window": int(counts_w.get(jk, 0)),
            "articles_recent": int(recent.get(jk, 0)),
            "first_year": int(span.loc[jk, "min"]) if jk in span.index else pd.NA,
            "last_year": int(span.loc[jk, "max"]) if jk in span.index else pd.NA,
            "active": bool(recent.get(jk, 0) > 0), "low_data": jk not in eligible,
            "completeness": float(score.get(jk, np.nan)),
            "owner_name": str(o["owner_name"]) if o is not None else "",
            "owner_source": o["owner_source"] if o is not None and pd.notna(o["owner_source"]) else None,
            "owner_share": float(o["owner_share"]) if o is not None else np.nan,
            "owner_matched": bool(o["owner_matched"]) if o is not None else False,
            "inhouse_share": float(a["inhouse_share"]) if a is not None else np.nan,
            "with_org": int(a["with_org"]) if a is not None else 0,
            "n_orgs": int(a["n_orgs"]) if a is not None else 0,
            "effective_orgs": float(a["effective_orgs"]) if a is not None else np.nan,
            "foreign_share": float(a["foreign_share"]) if a is not None else np.nan,
            "affiliation_coverage": float(a["affiliation_coverage"]) if a is not None else np.nan,
            "methods_coverage": float(mcov.get(jk, np.nan)),
        })
    summary = pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
    summary.loc[summary["low_data"], RATE_COLUMNS] = np.nan        # too few articles: no rate is published
    summary["tci_tier"] = summary["tci_tier"].astype("Int64")
    summary["first_year"] = summary["first_year"].astype("Int64")
    summary["last_year"] = summary["last_year"].astype("Int64")
    peer_rows = [{"journal_key": jk, "peer_key": p, "similarity": s} for jk, ps in peers.items() for p, s in ps]

    write_table(summary, work / "13_journals.parquet")
    write_table(years, work / "13_journal_years.parquet")
    write_table(mix, work / "13_journal_topics.parquet")
    write_table(drift, work / "13_journal_drift.parquet")
    write_table(shifts, work / "13_journal_shifts.parquet")
    write_table(pd.DataFrame(peer_rows, columns=["journal_key", "peer_key", "similarity"]),
                work / "13_journal_peers.parquet")
    write_table(comp_long[comp_long["journal_key"].isin(eligible)], work / "13_journal_completeness.parquet")
    write_table(jmeth, work / "13_journal_methods.parquet")
    write_table(opps, work / "13_special_issue.parquet")
    write_table(jopps, work / "13_journal_opportunities.parquet")
    meta = {"windows": {k: list(v) for k, v in win.items()}, "journals": int(len(summary)),
            "eligible": len(eligible), "registry": {"rows": int(len(registry)), "matched": len(matched),
                                                     "warnings": warnings + more}}
    (work / "13_journals_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[journals] {len(summary):,} journals ({len(eligible):,} with ≥ {jcfg['min_articles']} articles in "
          f"{W[0]}–{W[1]}; {len(matched):,} named by the registry); {len(opps)} special-issue topics")
    return summary
