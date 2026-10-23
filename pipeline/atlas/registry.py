"""Journal identity from the corpus + the optional journal registry (registry/journals.csv).

The official TCI journal list is not available yet, so journals come from the corpus:
  journal_key   "<server>:<OJS path>" from the article id ("so02:BECJournal:74136" → "so02:BECJournal");
                records without such an id (table input) → "name:<normalised journal name>"
  journal_code  the published id (URL path and file name): "so02.BECJournal", or "J" + 12 hex digits of
                sha1(key) when the key is not ASCII-safe — a fixed function of the key, so stable across releases
registry/journals.csv (git-ignored; registry/journals.example.csv shows the columns) adds names, ISSN, TCI
tier/field, publisher and URL. Every column except journal_key is optional and may be empty. A row matches a
corpus journal by its full key, or by the bare OJS path when exactly one corpus journal has that path.
"""
from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Callable, Iterable
from pathlib import Path

import pandas as pd

from atlas.thai import clean_text, norm_key

REGISTRY_COLUMNS = ["journal_key", "name_th", "name_en", "issn", "eissn", "tci_tier", "tci_field",
                    "publisher_org", "url"]
_ARTICLE_ID = re.compile(r"^(?P<host>[A-Za-z0-9_-]+):(?P<path>[^:\s]+):\d+$")
_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_ISSN = re.compile(r"^\d{4}-?\d{3}[\dX]$")
_TIER_WORDS = re.compile(r"(?i)กลุ่ม|tier|group")


class RegistryError(ValueError):
    """registry/journals.csv cannot be used as written (the message names the row)."""


def journal_key(article_id: str, journal_name: str) -> str:
    m = _ARTICLE_ID.match(str(article_id or ""))
    if m:
        return f"{m['host']}:{m['path']}"
    name = norm_key(str(journal_name or ""))[:60]
    return f"name:{name}" if name else ""


def journal_keys(articles: pd.DataFrame) -> pd.Series:
    """journal_key of every row of a table with article_id and journal_name; a journal_key column (corpus format
    1.0 gives it) wins where it is not empty."""
    ids = articles["article_id"].fillna("").astype(str)
    names = articles["journal_name"].fillna("").astype(str) if "journal_name" in articles else pd.Series(
        "", index=articles.index)
    given = articles["journal_key"].fillna("").astype(str) if "journal_key" in articles else pd.Series(
        "", index=articles.index)
    return pd.Series([g or journal_key(a, j) for g, a, j in zip(given, ids, names)], index=articles.index, dtype=str)


def journal_code(key: str) -> str:
    cand = key.replace(":", ".", 1)
    if ":" not in cand and _SAFE.fullmatch(cand):
        return cand
    return "J" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def journal_path(key: str) -> str:
    """The OJS path of a key ("so02:BECJournal" → "BECJournal"); the normalised name for "name:" keys."""
    return key.split(":", 1)[1] if ":" in key else key


def _issn(value: str, where: Callable[[], str], warnings: list[str]) -> str:
    v = value.strip().upper().replace(" ", "")
    if not v:
        return ""
    if not _ISSN.fullmatch(v):
        warnings.append(f"{where()}: ISSN {value!r} is not NNNN-NNNC — kept as written")
        return value.strip()
    return v if "-" in v else f"{v[:4]}-{v[4:]}"


def _check_field_counts(path: str | Path, hint: str) -> None:
    """Every row must have as many fields as the header (pandas would pad a short row and drop a long one)."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = csv.reader(f)
            header = next(rows, None)
            if header is None:
                return                                      # empty file: read_csv names it below
            for n, row in enumerate(rows, start=2):         # row 1 is the header, as in a spreadsheet
                if row and len(row) != len(header):
                    trailing = (" — the header ends with a comma: remove the trailing comma in the header"
                                if not header[-1].strip() else "")
                    raise RegistryError(f"{path} row {n}: {len(row)} fields but the header has {len(header)} — check "
                                        f"for a missing or extra comma or an unclosed quote{trailing}")
    except UnicodeDecodeError as e:
        raise RegistryError(f"{path}: not readable as UTF-8 ({e.reason} at byte {e.start}) — {hint}") from e
    except csv.Error as e:
        raise RegistryError(f"{path}: not a well-formed CSV ({e}) — {hint}") from e


def load_registry(path: str | Path | None) -> tuple[pd.DataFrame, list[str]]:
    """(rows with REGISTRY_COLUMNS — tci_tier as nullable Int64, text cleaned —, warnings).
    No path or no file → an empty table (the registry is optional). Raises RegistryError for a file that
    cannot be trusted: unreadable (not UTF-8, empty, malformed), no journal_key column, unknown columns, a row
    with the wrong number of fields, a duplicated key. A tier other than 1–3 is a warning (the tier is left empty)."""
    if not path or not Path(path).exists():
        return pd.DataFrame({c: pd.Series(dtype="Int64" if c == "tci_tier" else str) for c in REGISTRY_COLUMNS}), []
    hint = "save it as a UTF-8 CSV (Excel: Save As > CSV UTF-8) with the header row from journals.example.csv"
    _check_field_counts(path, hint)
    try:    # index_col=False: a trailing delimiter must not turn the first column into the index
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", index_col=False)  # BOM-safe
    except UnicodeDecodeError as e:
        raise RegistryError(f"{path}: not readable as UTF-8 ({e.reason} at byte {e.start}) — {hint}") from e
    except pd.errors.EmptyDataError as e:
        raise RegistryError(f"{path}: the file is empty (UTF-8 CSV expected) — {hint}") from e
    except pd.errors.ParserError as e:
        raise RegistryError(f"{path}: not a well-formed CSV ({e}) — {hint}") from e
    raw.columns = [str(c).strip() for c in raw.columns]
    if "journal_key" not in raw.columns:
        raise RegistryError(f"{path}: the header needs a journal_key column (columns: {REGISTRY_COLUMNS})")
    unknown = sorted(set(raw.columns) - set(REGISTRY_COLUMNS))
    if unknown:
        blank = any(c == "" or c.startswith("Unnamed:") for c in unknown)
        raise RegistryError(f"{path}: unknown columns {unknown} (allowed: {REGISTRY_COLUMNS})"
                            + (" — remove the trailing comma in the header" if blank else ""))
    df = raw.reindex(columns=REGISTRY_COLUMNS, fill_value="")
    for c in REGISTRY_COLUMNS:
        df[c] = df[c].map(clean_text)
    df = df[df["journal_key"] != ""]
    dup = df["journal_key"][df["journal_key"].duplicated()]
    if len(dup):
        raise RegistryError(f"{path} row {int(dup.index[0]) + 2}: journal_key {dup.iloc[0]!r} appears more than once")
    warnings: list[str] = []
    tiers = []
    for i, v in zip(df.index, df["tci_tier"]):
        t = _TIER_WORDS.sub("", v).strip()
        if t == "":
            tiers.append(pd.NA)
        elif t in ("1", "2", "3"):
            tiers.append(int(t))
        else:
            warnings.append(f"{path} row {i + 2}: tci_tier {v!r} must be 1, 2 or 3 — left empty")
            tiers.append(pd.NA)
    df["tci_tier"] = pd.array(tiers, dtype="Int64")
    for col in ("issn", "eissn"):
        df[col] = [_issn(v, lambda i=i: f"{path} row {i + 2}", warnings) for i, v in zip(df.index, df[col])]
    return df.reset_index(drop=True), warnings


def match_registry(keys: Iterable[str], registry: pd.DataFrame) -> tuple[dict[str, dict], list[str]]:
    """{corpus journal key: registry row as a dict} + warnings for rows that match no (or no single) journal."""
    known = sorted(set(keys))
    by_path: dict[str, list[str]] = {}
    for k in known:
        if not k.startswith("name:"):
            by_path.setdefault(journal_path(k), []).append(k)
    out: dict[str, dict] = {}
    unmatched, ambiguous = [], []
    known_set = set(known)
    for row in registry.to_dict("records"):
        rk = row["journal_key"]
        if rk in known_set:
            target = rk
        elif len(by_path.get(rk, [])) == 1:
            target = by_path[rk][0]
        else:
            (ambiguous if len(by_path.get(rk, [])) > 1 else unmatched).append(rk)
            continue
        if target in out:
            raise RegistryError(f"registry rows {out[target]['journal_key']!r} and {rk!r} name the same journal "
                                f"{target!r}")
        out[target] = row
    warnings = []
    if unmatched:
        warnings.append(f"{len(unmatched)} registry rows match no journal in the corpus (e.g. {unmatched[0]!r})")
    if ambiguous:
        warnings.append(f"{len(ambiguous)} registry rows name an OJS path used on several servers — write the full "
                        f"key <server>:<path> (e.g. {ambiguous[0]!r})")
    return out, warnings
