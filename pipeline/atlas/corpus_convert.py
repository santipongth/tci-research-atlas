"""`atlas corpus convert`: a folder of ThaiJO Markdown files → corpus format 1.0 (articles/part-NNNN.jsonl.gz).

The converted corpus ingests to the same article, author and reference tables as the Markdown corpus (tested), so a
team can start from it and enrich it (article_type, ISSN, ORCID, ROR, provinces, ...). Ids are kept as they are, so
topic history and the embedding store carry over. Also writes journals.csv with one row per journal_key (names, ISSN
and TCI tier left empty for the team to fill) unless the file exists already.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
from datetime import date
from pathlib import Path

from tqdm import tqdm

from atlas.registry import REGISTRY_COLUMNS, journal_key
from atlas.schema.corpus import CORPUS_SCHEMA, KEY, Article
from atlas.sources.thaijo_md import _URL_ID, STUDENT_ROLES
from atlas.thai import thai_ratio

_DOCTORAL = {STUDENT_ROLES[i] for i in (0, 2, 7, 8, 9)}
_MASTER = {STUDENT_ROLES[i] for i in (1, 3, 10)}
_KEY = re.compile(KEY)
_HTTP = re.compile(r"^https?://\S+$")


def _role(role: str, is_student: bool) -> str | None:
    if is_student:
        return "student-doctoral" if role in _DOCTORAL else "student-master" if role in _MASTER else "student"
    return "lecturer" if role else None                  # every academic title the parser knows is teaching staff


def _lang(th: str, en: str) -> dict:
    return {"th": th or None, "en": en or None}


def _journal_key(r: dict) -> str:
    key = journal_key(r["article_id"], r["journal_name"])
    return key if _KEY.match(key) else "journal:" + hashlib.sha1(key.encode()).hexdigest()[:12]


def _dates(r: dict) -> tuple[str | None, int | None]:
    if r["year_source"] == "published":
        try:
            d = date.fromisoformat(r["published"][:10])
            return (d.replace(year=d.year - 543) if d.year > 2400 else d).isoformat(), None
        except ValueError:
            pass
    return None, r["year"]


def md_to_corpus(r: dict) -> dict:
    """A thaijo_md.parse_markdown record → a corpus format 1.0 article (validated by the caller)."""
    published, year = _dates(r)
    authors = []
    for i, a in enumerate(r["authors"], start=1):
        name = a["name"]
        nm = {"th": name or None, "en": a["name_en"] or None} if thai_ratio(name) > 0.5 else {"th": None, "en": name or None}
        aff = [{"name": _lang(a["affiliation_th"], a["affiliation_en"])}] if (a["affiliation_th"] or a["affiliation_en"]) else []
        authors.append({"position": i, "name": nm, "role": _role(a["role"], a["is_student"]), "affiliations": aff})
    pages = r["pages"].split("-") if r["pages"] else []
    return {
        "schema": CORPUS_SCHEMA, "id": r["article_id"], "source": "thaijo" if _URL_ID.search(r["url"]) else None,
        "doi": r["doi"] or None, "url": r["url"] if _HTTP.match(r["url"]) else None,
        "issue_url": r["issue_url"] if _HTTP.match(r["issue_url"]) else None,
        "journal_key": _journal_key(r), "journal_title": None,
        "pages": {"first": pages[0].strip() or None, "last": pages[1].strip() if len(pages) > 1 else None} if pages else None,
        "published": published, "year": year,
        "title": _lang(r["title_th"], r["title_en"]), "abstract": _lang(r["abstract_th"], r["abstract_en"]),
        "keywords": {"th": r["keywords_th"], "en": r["keywords_en"]},
        "authors": authors,
        "references": [{"text": x["text"], "year": x["year"], "translated": bool(x["translated"])} for x in r["references"]],
        "provenance": {"extracted_from": "html"},
    }


def _journal_row(key: str) -> dict:
    row = dict.fromkeys(REGISTRY_COLUMNS, "")
    row["journal_key"] = key
    m = re.match(r"^([A-Za-z0-9_-]+):([^:\s]+)$", key)
    if m:
        row["url"] = f"https://{m.group(1)}.tci-thaijo.org/index.php/{m.group(2)}"
    return row


def convert_markdown(src: str | Path, out: str | Path, pattern: str = "**/*.md", per_file: int = 50_000,
                     workers: int = 1, batch_files: int = 20_000) -> dict:
    """Convert → {articles, files, skipped (no title / invalid), journals_csv}. Refuses a non-empty articles/."""
    from atlas.ingest import _parse_batch

    out = Path(out)
    adir = out / "articles"
    if adir.exists() and any(adir.iterdir()):
        raise FileExistsError(f"{adir} is not empty — convert into a new folder")
    adir.mkdir(parents=True, exist_ok=True)
    files = sorted(str(p) for p in Path(src).glob(pattern) if not p.name.startswith("_"))
    written, skipped, part, in_part, fh, journals = 0, [], 0, 0, None, set()
    try:
        for i in tqdm(range(0, len(files), batch_files), desc="convert", disable=len(files) <= batch_files):
            recs, errs = _parse_batch(files[i:i + batch_files], workers)
            skipped += [f"{e['path']}: {e['error']}" for e in errs]
            for r in recs:
                if not (r["title_th"] or r["title_en"]):
                    skipped.append(f"{r['source_path']}: no title")
                    continue
                doc = md_to_corpus(r)
                try:
                    Article.model_validate(doc)
                except ValueError as e:
                    skipped.append(f"{r['source_path']}: {str(e).splitlines()[0]}")
                    continue
                if fh is None or in_part >= per_file:
                    if fh is not None:
                        fh.close()
                    part += 1
                    in_part = 0
                    fh = gzip.open(adir / f"part-{part:04d}.jsonl.gz", "wt", encoding="utf-8")
                fh.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
                in_part += 1
                written += 1
                journals.add(doc["journal_key"])
    finally:
        if fh is not None:
            fh.close()
    jpath = out / "journals.csv"
    if not jpath.exists():
        with jpath.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
            w.writeheader()
            w.writerows(_journal_row(k) for k in sorted(journals))
    return {"articles": written, "files": part, "skipped": skipped, "journals_csv": str(jpath)}
