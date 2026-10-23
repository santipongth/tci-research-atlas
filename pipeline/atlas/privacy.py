"""PDPA safety net for a release: nothing that identifies a person may be in a published file.

`atlas validate` / `atlas publish` call `scan_release` on the real release (the unit tests only ever saw synthetic
data). Three checks:
  1. e-mail addresses and ORCID iDs anywhere in the release files (JSON, search shards, feeds);
  2. organisation-name strings (institutions, topic institution lists, journal owners/publishers) that contain the
     full name of an author of the corpus — "Somchai Jaidee Mahidol University" is the typical leak;
  3. (the names come from work/01_authors, read for this check only and never written anywhere).
Messages quote the file and the offending organisation string, never an author's name.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from atlas.io_utils import read_table
from atlas.thai import clean_text, norm_key

EMAIL = re.compile(rb"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
ORCID = re.compile(rb"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
MIN_NAME_KEY = 6                 # folded characters: shorter "names" are common words
MAX_WORDS = 4                    # longest author name matched, in words
ORG_FILES = ("institutions.json",)
ORG_GLOBS = ("institutions/*.json", "journals.json", "journals/*.json")
OWNER_KEYS = ("owner", "publisher")
_SPLIT = re.compile(r"[\s,;()\[\]/|]+")


def author_name_keys(work_dir: str | Path) -> set[str]:
    """Folded full names (two words or more) of every author — the only place a name is read for this check."""
    path = Path(work_dir) / "01_authors.parquet"
    if not path.exists():
        return set()
    try:
        df = read_table(path)
    except Exception:  # noqa: BLE001 — an unreadable checkpoint must not hide the other checks
        return set()
    keys: set[str] = set()
    for col in ("name", "name_en"):
        if col not in df.columns:
            continue
        for raw in df[col].dropna().astype(str).unique():
            name = clean_text(raw)
            if len(name.split()) >= 2 and len(norm_key(name)) >= MIN_NAME_KEY:
                keys.add(norm_key(name))
    return keys


def _strings(obj, only: tuple[str, ...] | None = None, under: bool = False) -> Iterator[str]:
    """Every string in a JSON value; with `only`, just the strings below keys that contain one of those words."""
    if isinstance(obj, str):
        if only is None or under:
            yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            hit = under or (only is not None and any(w in str(k).lower() for w in only))
            yield from _strings(v, only, hit)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v, only, under)


def _org_strings(root: Path) -> Iterator[tuple[str, str]]:
    """(file, string) of every place a release names an organisation."""
    for rel in ORG_FILES:
        f = root / rel
        if f.is_file():
            for s in _strings(json.loads(f.read_text(encoding="utf-8"))):
                yield rel, s
    for pat in ORG_GLOBS:
        owner_only = pat.startswith("journals")
        for f in sorted(root.glob(pat)):
            doc = json.loads(f.read_text(encoding="utf-8"))
            for s in _strings(doc, OWNER_KEYS if owner_only else None):
                yield f.relative_to(root).as_posix(), s
    for f in sorted(root.glob("topics/*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        for s in _strings(doc.get("institutions") or []):
            yield f.relative_to(root).as_posix(), s


def contains_name(text: str, names: set[str]) -> bool:
    """True when 2–MAX_WORDS consecutive words of `text` are an author's full name."""
    words = [w for w in _SPLIT.split(clean_text(text)) if w]
    for n in range(2, MAX_WORDS + 1):
        for i in range(len(words) - n + 1):
            if norm_key("".join(words[i:i + n])) in names:
                return True
    return False


def scan_release(release_dir: str | Path, work_dir: str | Path | None = None, max_report: int = 10) -> list[str]:
    """Errors (empty = clean) for a release folder; the name check runs when the work_dir holds 01_authors."""
    root = Path(release_dir)
    errors: list[str] = []
    for f in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix in (".json", ".xml", ".html")):
        data = f.read_bytes()
        if EMAIL.search(data):
            errors.append(f"privacy: an e-mail address is in {f.relative_to(root).as_posix()}")
        if ORCID.search(data):
            errors.append(f"privacy: an ORCID iD is in {f.relative_to(root).as_posix()}")
    names = author_name_keys(work_dir) if work_dir else set()
    if names:
        seen = 0
        for rel, s in _org_strings(root):
            if contains_name(s, names):
                seen += 1
                if seen <= max_report:
                    errors.append(f"privacy: an organisation string in {rel} contains an author's full name: {s[:60]!r}")
        if seen > max_report:
            errors.append(f"privacy: {seen - max_report} more organisation strings contain an author's full name")
    return errors
