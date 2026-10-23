"""Reader for corpus format 1.0 (atlas.schema.corpus): JSON Lines files, one article per line.

Every line is validated against the corpus model and mapped to the same record shape as
sources.thaijo_md.parse_markdown, so ingest.records_to_tables builds the tables for both formats.
A line that is not JSON or does not match the model becomes an error row ({path: "file:line", error}) — never
a crash, never silent. Articles whose article_type is in `exclude` are counted and left out.

Article id (kept when given; it must not change between quarters):
  1. a ThaiJO article URL → "<server>:<journal path>:<number>" (the Markdown corpus's id: topic history carries over)
  2. a DOI                → "doi:<doi, lower case>"
  3. otherwise            → "tci:" + 16 hex of sha1(journal_key | folded title | year)
"""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from atlas.schema.corpus import STUDENT_ROLES, Article
from atlas.sources.thaijo_md import (
    _URL_ID,
    mark_self_citations,
    quality_flags,
    reference_lang,
    reference_year,
)
from atlas.thai import clean_text, norm_key

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"
DEFAULT_GLOB = "articles/**/*.jsonl*"


def corpus_files(root: str | Path, pattern: str = DEFAULT_GLOB) -> list[str]:
    """Data files under the corpus folder (.jsonl, .jsonl.gz, .ndjson); names starting with "_" are skipped."""
    ok = (".jsonl", ".jsonl.gz", ".ndjson", ".ndjson.gz")
    return sorted(str(p) for p in Path(root).glob(pattern)
                  if p.is_file() and not p.name.startswith("_") and p.name.endswith(ok))


def iter_lines(path: str | Path) -> Iterator[tuple[int, str]]:
    """(line number, text) of every non-blank line; undecodable bytes become U+FFFD (flagged, never dropped)."""
    p = Path(path)
    opener = gzip.open if p.name.endswith(".gz") else open
    with opener(p, "rt", encoding="utf-8-sig", errors="replace") as fh:
        for i, line in enumerate(fh, start=1):
            if line.strip():
                yield i, line


def _t(v: str | None) -> str:
    return clean_text(v) if v else ""


def derive_id(a: Article) -> tuple[str, str]:
    """(article_id, how it was found: given | url | doi | derived)."""
    if a.id:
        return a.id, "given"
    m = _URL_ID.search(a.url or "")
    if m:
        return f"{m.group('host')}:{m.group('journal')}:{m.group('id')}", "url"
    if a.doi:
        return f"doi:{a.doi.lower()}", "doi"
    title = norm_key(_t(a.title.th) or _t(a.title.en))
    year = a.year or (a.published.year if a.published else "")
    digest = hashlib.sha1(f"{a.journal_key}|{title}|{year}".encode()).hexdigest()[:16]
    return f"tci:{digest}", "derived"


def _authors(a: Article) -> list[dict]:
    """One row per author and affiliation (an author without affiliation keeps one empty row)."""
    order = sorted(range(len(a.authors)), key=lambda i: (a.authors[i].position or i + 1, i))
    rows = []
    for rank, i in enumerate(order):
        au = a.authors[i]
        role = au.role or ""
        base = {"name": _t(au.name.th) or _t(au.name.en), "name_en": _t(au.name.en) if au.name.th else "",
                "role": role, "is_student": role in STUDENT_ROLES, "orcid": au.orcid or "", "author_index": rank}
        for k, af in enumerate(au.affiliations or [None]):
            rows.append({**base, "affiliation_index": k,
                         "affiliation_th": _t(af.name.th) if af else "", "affiliation_en": _t(af.name.en) if af else "",
                         "ror": (af.ror or "") if af else "", "country": (af.country or "") if af else "",
                         "province": (af.province or "") if af else ""})
    return rows


def to_record(a: Article, raw: str, where: str) -> dict:
    """The validated article → the record shape of thaijo_md.parse_markdown (+ the corpus-only fields)."""
    article_id, id_source = derive_id(a)
    title_th, title_en = _t(a.title.th), _t(a.title.en)
    ab_th = _t(a.abstract.th) if a.abstract else ""
    ab_en = _t(a.abstract.en) if a.abstract else ""
    if a.published:
        year, year_source = a.published.year, "published"
    else:
        year, year_source = a.year, ("given" if a.year else "")
    refs = [{"text": _t(r.text), "year": r.year if r.year is not None else reference_year(_t(r.text)),
             "translated": r.translated, "lang": reference_lang(_t(r.text))} for r in a.references]
    counted = mark_self_citations(refs, title_th, title_en)
    flags = quality_flags(raw, ab_th, ab_en)
    if REPLACEMENT_CHAR in raw:
        flags.append("decode_replaced")
    jt = a.journal_title
    journal_name = (_t(jt.th) or _t(jt.en)) if jt else ""
    issue_url = a.issue_url or (f"issue:{a.journal_key}:{a.volume or ''}:{a.issue or ''}"
                                if (a.volume or a.issue) else "")
    pages = "-".join(x for x in ((a.pages.first, a.pages.last) if a.pages else ()) if x)
    kw = a.keywords
    return {
        "article_id": article_id, "id_source": id_source, "source_path": where,
        "url": a.url or "", "issue_url": issue_url,
        "journal_key": a.journal_key, "journal_name": journal_name or a.journal_key.rsplit(":", 1)[-1],
        "published": a.published.isoformat() if a.published else "", "year": year, "year_source": year_source,
        "pages": pages, "doi": a.doi or "", "title_th": title_th, "title_en": title_en,
        "abstract_th": ab_th, "abstract_en": ab_en,
        "keywords_th": [x for x in (_t(k) for k in (kw.th if kw else [])) if x],
        "keywords_en": [x for x in (_t(k) for k in (kw.en if kw else [])) if x],
        "authors": _authors(a), "references": refs,
        "n_references": len(counted), "has_references": bool(refs),
        "self_citation_only": bool(refs) and not counted and any(r["self_citation"] for r in refs),
        "text_quality": flags,
        "article_type": a.article_type or "", "language": a.language or "", "issn": a.issn or "",
        "eissn": a.eissn or "", "volume": a.volume or "", "issue": a.issue or "",
    }


def _error_text(e: Exception) -> str:
    if isinstance(e, ValidationError):
        parts = [f"{'.'.join(str(x) for x in err['loc']) or '(line)'}: {err['msg']}" for err in e.errors()[:3]]
        more = f" (+{e.error_count() - 3} more)" if e.error_count() > 3 else ""
        return "ValidationError: " + "; ".join(parts) + more
    return f"{type(e).__name__}: {e}"


def parse_line(line: str, where: str) -> tuple[dict | None, dict | None]:
    """(record, None) or (None, {path, error})."""
    try:
        return to_record(Article.model_validate(json.loads(line)), line, where), None
    except Exception as e:  # noqa: BLE001 — one bad line must not abort 500K articles; it is recorded, never silent
        return None, {"path": where, "error": _error_text(e)}


def read_corpus_file(path: str | Path, exclude: tuple[str, ...] = ()) -> tuple[list[dict], list[dict], Counter]:
    """(records, errors, excluded article types) of one data file."""
    recs, errors, excluded = [], [], Counter()
    for i, line in iter_lines(path):
        rec, err = parse_line(line, f"{path}:{i}")
        if err is not None:
            errors.append(err)
        elif rec["article_type"] in exclude:
            excluded[rec["article_type"]] += 1
        else:
            recs.append(rec)
    return recs, errors, excluded
