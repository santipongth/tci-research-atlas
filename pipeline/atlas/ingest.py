"""Ingest: a folder of ThaiJO Markdown files (default) or one table file → canonical tables.

Outputs (work_dir): 01_articles, 01_authors, 01_references  (via io_utils)
"""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from atlas.io_utils import read_table, write_table
from atlas.orgs import org_key
from atlas.sources.thaijo_md import fill_years_from_issue, parse_markdown
from atlas.thai import clean_text, norm_key

ARTICLE_COLUMNS = [
    "article_id", "source_path", "url", "issue_url", "journal_name", "published", "year", "year_source",
    "pages", "doi", "title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en",
    "authors", "affiliations", "n_authors", "n_student_authors", "n_references", "has_references",
    "self_citation_only", "text_quality",
]
AUTHOR_COLUMNS = ["article_id", "position", "name", "name_en", "affiliation_th", "affiliation_en",
                  "role", "is_student", "org_key"]
REFERENCE_COLUMNS = ["article_id", "position", "text", "year", "lang", "translated", "self_citation"]
_TEXT = ["source_path", "url", "issue_url", "journal_name", "published", "year_source", "pages", "doi",
         "title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en",
         "authors", "affiliations", "text_quality"]


# ------------------------------------------------------------------ markdown corpus
POOL_MIN_FILES = 2000          # below this, parsing in-process is faster than starting worker processes
ERROR_COLUMNS = ["path", "error"]
REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"


def _parse_file(path_str: str) -> dict:
    p = Path(path_str)
    text = p.read_text(encoding="utf-8-sig", errors="replace")   # one bad byte must not drop the article
    rec = parse_markdown(text, source_path=str(p))
    if REPLACEMENT_CHAR in text:
        rec["text_quality"].append("decode_replaced")
    if not rec["article_id"]:                     # broken scrape: stable id from the file name
        rec["article_id"] = "file:" + hashlib.sha1(p.name.encode("utf-8")).hexdigest()[:16]
    return rec


def _parse_file_safe(path_str: str) -> tuple[dict | None, dict | None]:
    """(record, None) or (None, {path, error}) — top-level so worker processes can pickle it."""
    try:
        return _parse_file(path_str), None
    except Exception as e:  # noqa: BLE001 — one unreadable/unparsable file must not abort a 250K run;
        return None, {"path": path_str, "error": f"{type(e).__name__}: {e}"}   # it is recorded, never silent


def read_thaijo_corpus(root: str | Path, pattern: str = "**/*.md",
                       workers: int = 1) -> tuple[list[dict], list[dict]]:
    """Parse every matching file → (records, errors); a file that cannot be read or parsed is
    recorded in `errors` ({path, error: "Type: message"}) and skipped."""
    files = sorted(str(p) for p in Path(root).glob(pattern) if not p.name.startswith("_"))
    if workers > 1 and len(files) > POOL_MIN_FILES:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = list(tqdm(ex.map(_parse_file_safe, files, chunksize=max(1, min(256, len(files) // workers))),
                                total=len(files), desc="parse"))
    else:
        results = [_parse_file_safe(f) for f in tqdm(files, desc="parse", disable=len(files) < POOL_MIN_FILES)]
    recs = [r for r, _ in results if r is not None]
    errors = [e for _, e in results if e is not None]
    fill_years_from_issue(recs)
    return recs, errors


def records_to_tables(records: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    arts, auths, refs = [], [], []
    for r in records:
        a = r["authors"]
        arts.append({
            **{k: r[k] for k in ("article_id", "source_path", "url", "issue_url", "journal_name", "published",
                                 "year", "year_source", "pages", "doi", "title_th", "title_en",
                                 "abstract_th", "abstract_en", "n_references", "has_references",
                                 "self_citation_only")},
            "keywords_th": "; ".join(r["keywords_th"]),
            "keywords_en": "; ".join(r["keywords_en"]),
            "authors": "; ".join(x["name"] for x in a),
            "affiliations": "; ".join(x["affiliation_th"] or x["affiliation_en"] for x in a),
            "n_authors": len(a),
            "n_student_authors": sum(bool(x["is_student"]) for x in a),
            "text_quality": "; ".join(r["text_quality"]),
        })
        for i, x in enumerate(a):
            auths.append({"article_id": r["article_id"], "position": i, **x,
                          "org_key": org_key(x["affiliation_th"], x["affiliation_en"])})
        for i, x in enumerate(r["references"]):
            refs.append({"article_id": r["article_id"], "position": i, **{k: x[k] for k in REFERENCE_COLUMNS[2:]}})
    return (pd.DataFrame(arts, columns=ARTICLE_COLUMNS),
            pd.DataFrame(auths, columns=AUTHOR_COLUMNS),
            pd.DataFrame(refs, columns=REFERENCE_COLUMNS))


# ------------------------------------------------------------------ table input
def _read_any(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"input not found: {p}")
    if p.suffix == ".csv":
        return pd.read_csv(p, dtype=str, keep_default_na=False)
    if p.suffix == ".parquet":
        return read_table(p)
    if p.suffix in (".jsonl", ".ndjson"):
        return pd.read_json(p, lines=True, dtype=False)
    if p.suffix == ".json":
        obj = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            obj = next(v for v in obj.values() if isinstance(v, list))
        return pd.DataFrame(obj)
    raise ValueError(f"unsupported input type: {p.suffix}")


def read_table_input(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = _read_any(cfg["input"]["path"])
    colmap = {k: v for k, v in cfg["input"]["columns"].items() if v in raw.columns}
    if "article_id" not in colmap:
        raise ValueError("table input needs an id column mapped to article_id")
    df = raw.rename(columns={v: k for k, v in colmap.items()})
    for c in ARTICLE_COLUMNS:
        if c not in df.columns:
            df[c] = None
    df = df[ARTICLE_COLUMNS].copy()
    for c in _TEXT:
        df[c] = df[c].fillna("").astype(str).map(clean_text)
    df["article_id"] = df["article_id"].astype(str)
    df["year_source"] = "table"
    df["n_authors"] = df["authors"].map(lambda s: len([x for x in s.split(";") if x.strip()]))
    for c in ("n_student_authors", "n_references"):
        df[c] = 0
    for c in ("has_references", "self_citation_only"):
        df[c] = False
    auth_rows = []
    for aid, names, affs in zip(df["article_id"], df["authors"], df["affiliations"]):
        aff_list = [x.strip() for x in affs.split(";")]
        for i, name in enumerate(x.strip() for x in names.split(";") if x.strip()):
            aff = aff_list[i] if i < len(aff_list) else ""
            auth_rows.append({"article_id": aid, "position": i, "name": name, "name_en": "",
                              "affiliation_th": aff, "affiliation_en": "", "role": "", "is_student": False,
                              "org_key": org_key(aff, "")})
    return df, pd.DataFrame(auth_rows, columns=AUTHOR_COLUMNS), pd.DataFrame(columns=REFERENCE_COLUMNS)


# ------------------------------------------------------------------ normalisation
def normalize_years(df: pd.DataFrame, min_year: int, max_year: int | None) -> pd.DataFrame:
    y = pd.to_numeric(df["year"], errors="coerce")
    y = y.where(y <= 2400, y - 543)                       # Buddhist Era → Common Era
    max_year = max_year or date.today().year + 1
    df = df.assign(year=y.astype("Int64"))
    bad = df["year"].notna() & ((df["year"] < min_year) | (df["year"] > max_year))
    return df[~bad]


def add_convenience_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["title"] = df["title_th"].where(df["title_th"] != "", df["title_en"])
    df["abstract"] = (df["abstract_th"] + " " + df["abstract_en"]).str.strip()
    df["keywords"] = [("; ".join(x for x in (a, b) if x)) for a, b in zip(df["keywords_th"], df["keywords_en"])]
    return df


def _completeness(df: pd.DataFrame) -> pd.Series:
    cols = ("title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en", "doi", "authors")
    return sum((df[c].astype(str).str.len() > 0).astype(int) for c in cols)


def _drop_dup_keys(df: pd.DataFrame, key: pd.Series) -> pd.DataFrame:
    has = key != ""
    return pd.concat([df[has].loc[~key[has].duplicated()], df[~has]])


def _most_complete_first(df: pd.DataFrame) -> pd.DataFrame:
    return (df.assign(_c=_completeness(df)).sort_values(["_c", "article_id"], ascending=[False, True], kind="stable")
            .drop(columns="_c"))


def doi_key(df: pd.DataFrame) -> pd.Series:
    return df["doi"].fillna("").astype(str).str.lower().str.strip()


def title_key(titles: pd.Series) -> pd.Series:
    return titles.fillna("").astype(str).map(norm_key).str[:80]


def drop_duplicate_ids(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Always applied (even with dedup off): duplicate article_ids would inflate series counts."""
    out = _most_complete_first(df).drop_duplicates("article_id", keep="first")
    return out.sort_values("article_id").reset_index(drop=True), len(df) - len(out)


def dedup(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """article_id → DOI (+ same normalised title) → normalised title + year; keep the most complete record.

    A DOI shared by articles with DIFFERENT titles is a metadata error (journals reuse or mistype
    DOIs), not a duplicate: those articles are all kept and counted in `doi_title_conflicts`.
    """
    n0 = len(df)
    df = _most_complete_first(df).drop_duplicates("article_id", keep="first")
    doi, tkey = doi_key(df), title_key(df["title"])
    df = _drop_dup_keys(df, doi.where(doi == "", doi + "|" + tkey))
    doi, tkey = doi_key(df), title_key(df["title"])
    conflicts = int((tkey[doi != ""].groupby(doi[doi != ""]).nunique() > 1).sum())
    df = _drop_dup_keys(df, tkey.where(tkey == "", tkey + "|" + df["year"].astype(str)))
    out = df.sort_values("article_id").reset_index(drop=True)
    return out, {"dropped": n0 - len(out), "doi_title_conflicts": conflicts}


# ------------------------------------------------------------------ step
def ingest(cfg: dict) -> pd.DataFrame:
    icfg = cfg["input"]
    errors: list[dict] = []
    if icfg["format"] == "thaijo_md":
        recs, errors = read_thaijo_corpus(icfg["path"], icfg["glob"], int(icfg["workers"]))
        articles, authors, refs = records_to_tables(recs)
    else:
        articles, authors, refs = read_table_input(cfg)
    n_raw = len(articles)
    articles = normalize_years(articles, int(icfg["min_year"]), icfg["max_year"])
    articles = add_convenience_columns(articles)
    articles = articles[articles["title"] != ""]
    if icfg["dedup"]["enabled"]:
        articles, stats = dedup(articles)
        n_dup = stats["dropped"]
        if stats["doi_title_conflicts"]:
            print(f"[ingest] {stats['doi_title_conflicts']:,} DOIs are shared by articles with different titles "
                  f"— kept as separate articles (see `atlas profile` → DOI collisions)")
    else:
        articles, n_dup = drop_duplicate_ids(articles)
    keep = set(articles["article_id"])
    authors = authors[authors["article_id"].isin(keep)].drop_duplicates(["article_id", "position"])
    refs = refs[refs["article_id"].isin(keep)].drop_duplicates(["article_id", "position"])

    work = Path(cfg["pipeline"]["work_dir"])
    write_table(articles.reset_index(drop=True), work / "01_articles.parquet")
    write_table(authors.reset_index(drop=True), work / "01_authors.parquet")
    write_table(refs.reset_index(drop=True), work / "01_references.parquet")
    write_table(pd.DataFrame(errors, columns=ERROR_COLUMNS), work / "01_ingest_errors.parquet")
    if errors:
        print(f"[ingest] WARNING: {len(errors):,} files could not be read or parsed and were skipped "
              f"(first: {errors[0]['path']} — {errors[0]['error']}) → 01_ingest_errors")
    print(f"[ingest] {n_raw:,} records → {len(articles):,} articles (duplicates dropped: {n_dup:,}; "
          f"year missing: {int(articles['year'].isna().sum()):,}; files with errors: {len(errors):,}) → {work}")
    return articles
