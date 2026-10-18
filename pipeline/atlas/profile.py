"""Corpus quality profile — run on the full .md corpus BEFORE any modelling.

Answers: how many files/articles, which years (and how they were recovered), which
journals and whether any journal uploaded a backlog in one year, coverage of English
metadata/DOI/references, author affiliation coverage, and text-quality flags.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from atlas.ingest import read_thaijo_corpus, records_to_tables


def _pct(mask: pd.Series) -> float:
    return round(100 * float(mask.mean()), 1) if len(mask) else 0.0


def profile_corpus(root: str | Path, pattern: str = "**/*.md", workers: int = 1) -> dict:
    arts, auths, _ = records_to_tables(read_thaijo_corpus(root, pattern, workers))
    n = len(arts)
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
    return {
        "files": n,
        "unique_articles": int(arts["article_id"].nunique()),
        "duplicate_files": int(n - arts["article_id"].nunique()),
        "missing_article_url": int(arts["article_id"].str.startswith("file:").sum()),
        "years": {
            "min": int(years.min()) if years.notna().any() else None,
            "max": int(years.max()) if years.notna().any() else None,
            "missing": int(years.isna().sum()),
            "by_source": {str(k): int(v) for k, v in arts["year_source"].replace("", "none").value_counts().items()},
        },
        "by_year": {int(y): int(c) for y, c in years.dropna().astype(int).value_counts().sort_index().items()},
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
    ]
    return "\n".join(lines)
