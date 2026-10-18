"""Corpus quality profile — run on the full .md corpus BEFORE any modelling.

Answers: how many files/articles, which years (and how they were recovered), which
journals and whether any journal uploaded a backlog in one year, coverage of English
metadata/DOI/references, author affiliation coverage, and text-quality flags.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from atlas.ingest import doi_key, read_thaijo_corpus, records_to_tables, title_key


def _pct(mask: pd.Series) -> float:
    return round(100 * float(mask.mean()), 1) if len(mask) else 0.0


def doi_title_collisions(arts: pd.DataFrame, max_examples: int = 10) -> dict:
    """DOIs shared by different articles whose normalised titles differ (kept apart by ingest)."""
    a = arts.drop_duplicates("article_id")
    title = a["title_th"].fillna("").astype(str).where(a["title_th"].fillna("") != "", a["title_en"])
    d = pd.DataFrame({"doi": doi_key(a), "tkey": title_key(title), "title": title, "article_id": a["article_id"]})
    d = d[d["doi"] != ""]
    n_keys = d.groupby("doi")["tkey"].nunique()                  # vectorised: no Python loop over 250K DOIs
    colliding = n_keys.index[n_keys > 1]
    examples = [{"doi": doi, "titles": g["title"].tolist(), "article_ids": g["article_id"].tolist()}
                for doi, g in d[d["doi"].isin(colliding[:max_examples])].groupby("doi")]
    return {"count": int(len(colliding)), "examples": examples}


def profile_corpus(root: str | Path, pattern: str = "**/*.md", workers: int = 1,
                   max_error_ratio: float = 0.01) -> dict:
    recs, errors = read_thaijo_corpus(root, pattern, workers)
    arts, auths, _ = records_to_tables(recs)
    n = len(arts)
    n_files = n + len(errors)
    years = pd.to_numeric(arts["year"], errors="coerce")
    nonempty = {c: arts[c].fillna("").astype(str).str.len() > 0
                for c in ("title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en", "doi")}

    journals, spikes = [], []
    for name, g in arts.assign(y=years).groupby("journal_name"):
        yc = g["y"].dropna().astype(int).value_counts()
        entry = {"journal": name, "articles": int(len(g)),
                 "first_year": int(yc.index.min()) if len(yc) else None,
                 "last_year": int(yc.index.max()) if len(yc) else None,
                 "peak_year_share": round(float(yc.max() / yc.sum()), 3) if len(yc) else 0.0}
        journals.append(entry)
        if entry["articles"] >= 20 and entry["peak_year_share"] >= 0.5:
            spikes.append(entry)                     # likely a backlog upload → interpret trends with care
    journals.sort(key=lambda j: -j["articles"])

    flags = Counter(f for s in arts["text_quality"].fillna("").astype(str) for f in s.split("; ") if f)
    affiliation = auths["affiliation_th"].fillna("").astype(str) + auths["affiliation_en"].fillna("").astype(str)
    by_year = years.dropna().astype(int).value_counts().sort_index()
    year_totals = [{"year": int(y), "articles": int(c),
                    "vs_prev": round(int(c) / int(by_year[y - 1]), 3) if (y - 1) in by_year.index else None}
                   for y, c in by_year.items()]
    return {
        "files": n,                                  # files parsed into a record
        "files_with_errors": {"count": len(errors), "examples": errors[:20],     # unreadable/unparsable: skipped
                              "ratio": round(len(errors) / n_files, 6) if n_files else 0.0,
                              "threshold": max_error_ratio},     # profile never raises; ingest does above it
        "unique_articles": int(arts["article_id"].nunique()),
        "duplicate_files": int(n - arts["article_id"].nunique()),
        "missing_article_url": int(arts["article_id"].str.startswith("file:").sum()),
        "doi_title_collisions": doi_title_collisions(arts),
        "years": {
            "min": int(years.min()) if years.notna().any() else None,
            "max": int(years.max()) if years.notna().any() else None,
            "missing": int(years.isna().sum()),
            "by_source": {str(k): int(v) for k, v in arts["year_source"].replace("", "none").value_counts().items()},
            "forward_dated": int((years > date.today().year).sum()),     # issues dated after today's year
        },
        "by_year": {int(y): int(c) for y, c in by_year.items()},
        "year_totals": year_totals,                  # per year vs the previous year: spot incomplete years
        "journals": {"count": int(arts["journal_name"].nunique()), "top": journals[:50], "year_spikes": spikes},
        "coverage_pct": {**{c: _pct(m) for c, m in nonempty.items()},
                         "references": _pct(arts["has_references"].astype(bool)),
                         "self_citation_only": _pct(arts["self_citation_only"].astype(bool))},
        "references": {"articles_with_references": int(arts["has_references"].astype(bool).sum()),
                       "median_counted_per_article": float(arts["n_references"].median()) if n else 0.0},
        "authors": {"median_per_article": float(arts["n_authors"].median()) if n else 0.0,
                    "pct_with_affiliation": _pct(affiliation.str.len() > 0),
                    "pct_student_authors": _pct(auths["is_student"].astype(bool))},
        "text_quality": dict(flags),
    }


def render_markdown(r: dict) -> str:
    cov = r["coverage_pct"]
    lines = [
        "# รายงานคุณภาพคลังบทความ (Corpus profile)",
        "",
        f"- ไฟล์ทั้งหมด **{r['files']:,}** · บทความไม่ซ้ำ **{r['unique_articles']:,}** · "
        f"ไฟล์ซ้ำ {r['duplicate_files']:,} · ไม่มี Article URL {r['missing_article_url']:,}",
        f"- ปี {r['years']['min']}–{r['years']['max']} · ไม่มีปี {r['years']['missing']:,} · "
        f"ที่มาของปี: " + ", ".join(f"{k} {v:,}" for k, v in r["years"]["by_source"].items()),
        f"- วารสาร {r['journals']['count']:,} ฉบับ",
        "",
        "## ความครบถ้วนของ metadata (%)",
        "",
        "| ฟิลด์ | % |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in cov.items()],
        "",
        "## วารสารใหญ่สุด",
        "",
        "| วารสาร | บทความ | ปีแรก | ปีล่าสุด | สัดส่วนปีสูงสุด |",
        "|---|---|---|---|---|",
        *[f"| {j['journal']} | {j['articles']:,} | {j['first_year']} | {j['last_year']} | {j['peak_year_share']} |"
          for j in r["journals"]["top"][:20]],
        "",
        "## วารสารที่อัปโหลดย้อนหลังในปีเดียว (ระวังแนวโน้มเทียม)",
        "",
        *([f"- {j['journal']}: {j['peak_year_share'] * 100:.0f}% ของบทความอยู่ในปีเดียว"
           for j in r["journals"]["year_spikes"]] or ["- ไม่พบ"]),
        "",
        "## Text-quality flags",
        "",
        *([f"- {k}: {v:,}" for k, v in r["text_quality"].items()] or ["- ไม่พบ"]),
        "",
        "## Files with errors (could not be read or parsed — skipped by ingest)",
        "",
        f"- files: {r['files_with_errors']['count']:,} (ratio {r['files_with_errors']['ratio']:.4f}, "
        f"ingest ceiling input.max_error_ratio {r['files_with_errors']['threshold']:g})",
        *(["- \N{WARNING SIGN} above the ceiling: `atlas run` will stop at ingest until these are fixed "
           "or input.max_error_ratio is raised deliberately"]
          if r["files_with_errors"]["ratio"] > r["files_with_errors"]["threshold"] else []),
        *[f"- {e['path']}: {e['error']}" for e in r["files_with_errors"]["examples"]],
        "",
        "## DOI collisions (same DOI, different titles — kept as separate articles)",
        "",
        f"- groups: {r['doi_title_collisions']['count']:,}",
        *[f"- {ex['doi']}: " + " | ".join(ex["titles"]) for ex in r["doi_title_collisions"]["examples"]],
        "",
        "## Articles per year (vs previous year)",
        "",
        f"- Forward-dated articles (year > {date.today().year}): {r['years']['forward_dated']:,}",
        "",
        "| year | articles | vs previous year |",
        "|---|---|---|",
        *[f"| {e['year']} | {e['articles']:,} | "
          f"{'—' if e['vs_prev'] is None else format(e['vs_prev'], '.2f') + '×'} |" for e in r["year_totals"]],
        "",
    ]
    return "\n".join(lines)
