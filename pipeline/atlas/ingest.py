"""Ingest: corpus format 1.0 (articles/*.jsonl[.gz], docs/corpus/README.md), a folder of ThaiJO Markdown files
(the config default when input.format is not set) or one table file → canonical tables.

Outputs (work_dir): 01_articles, 01_authors, 01_references  (via io_utils)
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from atlas.io_utils import read_table, write_table
from atlas.orgs import org_key
from atlas.registry import journal_keys
from atlas.sources import corpus_jsonl
from atlas.sources.thaijo_md import fill_years_from_issue, parse_markdown
from atlas.thai import clean_text, norm_key

ARTICLE_COLUMNS = [
    "article_id", "source_path", "url", "issue_url", "journal_name", "published", "year", "year_source",
    "pages", "doi", "title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en",
    "authors", "affiliations", "n_authors", "n_student_authors", "n_references", "has_references",
    "self_citation_only", "text_quality",
    # corpus format 1.0 only (empty for the Markdown and table inputs)
    "journal_key", "article_type", "language", "issn", "eissn", "volume", "issue",
]
CORPUS_ARTICLE_COLUMNS = ["journal_key", "article_type", "language", "issn", "eissn", "volume", "issue"]
# one row per author and affiliation: position = author order, affiliation_index = the author's n-th affiliation
AUTHOR_COLUMNS = ["article_id", "position", "affiliation_index", "name", "name_en", "affiliation_th", "affiliation_en",
                  "role", "is_student", "org_key", "orcid", "ror", "country", "province"]
CORPUS_AUTHOR_COLUMNS = ["orcid", "ror", "country", "province"]
REFERENCE_COLUMNS = ["article_id", "position", "text", "year", "lang", "translated", "self_citation"]
_TEXT = ["source_path", "url", "issue_url", "journal_name", "published", "year_source", "pages", "doi",
         "title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en",
         "authors", "affiliations", "text_quality", *CORPUS_ARTICLE_COLUMNS]


# ------------------------------------------------------------------ markdown corpus
POOL_MIN_FILES = 2000          # below this, parsing in-process is faster than starting worker processes
ERROR_COLUMNS = ["path", "error"]
_NONE_PARSED_TH = "\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER FO FAN}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER THANTHAKHAT}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER DO DEK} parse \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO}"   # "no file could be parsed"
REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"


def _parse_file(path_str: str) -> dict:
    p = Path(path_str)
    text = p.read_text(encoding="utf-8-sig", errors="replace")   # one bad byte must not drop the article
    rec = parse_markdown(text, source_path=str(p))
    if REPLACEMENT_CHAR in text:
        rec["text_quality"].append("decode_replaced")
    if not rec["article_id"]:                     # broken scrape: stable id from the folder and file name
        rec["article_id"] = "file:" + hashlib.sha1(f"{p.parent.name}/{p.name}".encode()).hexdigest()[:16]
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
    """Records of thaijo_md.parse_markdown or sources.corpus_jsonl → (articles, authors, references).
    A corpus record lists one author row per affiliation (author_index, affiliation_index)."""
    arts, auths, refs = [], [], []
    for r in records:
        rows = r["authors"]
        first = [x for x in rows if x.get("affiliation_index", 0) == 0]     # one row per author
        arts.append({
            **{k: r[k] for k in ("article_id", "source_path", "url", "issue_url", "journal_name", "published",
                                 "year", "year_source", "pages", "doi", "title_th", "title_en",
                                 "abstract_th", "abstract_en", "n_references", "has_references",
                                 "self_citation_only")},
            **{k: r.get(k, "") for k in CORPUS_ARTICLE_COLUMNS},
            "keywords_th": "; ".join(r["keywords_th"]),
            "keywords_en": "; ".join(r["keywords_en"]),
            "authors": "; ".join(x["name"] for x in first),
            "affiliations": "; ".join(x["affiliation_th"] or x["affiliation_en"] for x in rows),
            "n_authors": len(first),
            "n_student_authors": sum(bool(x["is_student"]) for x in first),
            "text_quality": "; ".join(r["text_quality"]),
        })
        for i, x in enumerate(rows):
            auths.append({"article_id": r["article_id"], "position": x.get("author_index", i),
                          "affiliation_index": x.get("affiliation_index", 0),
                          **{k: x[k] for k in ("name", "name_en", "affiliation_th", "affiliation_en", "role",
                                               "is_student")},
                          **{k: x.get(k, "") for k in CORPUS_AUTHOR_COLUMNS},
                          "org_key": org_key(x["affiliation_th"], x["affiliation_en"])})
        for i, x in enumerate(r["references"]):
            refs.append({"article_id": r["article_id"], "position": i, **{k: x[k] for k in REFERENCE_COLUMNS[2:]}})
    return (pd.DataFrame(arts, columns=ARTICLE_COLUMNS),
            pd.DataFrame(auths, columns=AUTHOR_COLUMNS),
            pd.DataFrame(refs, columns=REFERENCE_COLUMNS))


def fill_years_from_issue_df(articles: pd.DataFrame) -> pd.DataFrame:
    """Corpus-level pass on the article table: a missing year takes the median year of its issue
    (same rule as sources.thaijo_md.fill_years_from_issue, independent of how the corpus was batched)."""
    y = pd.to_numeric(articles["year"], errors="coerce")
    issue = articles["issue_url"].fillna("").astype(str)
    has = y.notna() & (issue != "")
    med = y[has].groupby(issue[has]).median()
    fill = y.isna() & issue.isin(med.index)
    out = articles.copy()
    out["year"] = y.astype("Int64")
    out.loc[fill, "year"] = issue[fill].map(med).astype(int).to_numpy()
    out.loc[fill, "year_source"] = "issue_median"
    return out


def _parse_batch(files: list[str], workers: int) -> tuple[list[dict], list[dict]]:
    """One batch through the fix wave's per-file wrapper (records, {path, error} rows)."""
    if workers > 1 and len(files) > POOL_MIN_FILES:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            out = list(ex.map(_parse_file_safe, files, chunksize=max(1, min(256, len(files) // workers))))
    else:
        out = [_parse_file_safe(f) for f in files]
    return [r for r, _ in out if r is not None], [e for _, e in out if e is not None]


def read_thaijo_tables(root: str | Path, pattern: str = "**/*.md", workers: int = 1,
                       batch_files: int = 20_000) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict]]:
    """Parse the corpus batch by batch straight into tables → (articles, authors, references, errors).
    Same files, records and errors as read_thaijo_corpus, without holding every record in memory."""
    files = sorted(str(p) for p in Path(root).glob(pattern) if not p.name.startswith("_"))
    parts, errors = [], []
    for i in tqdm(range(0, len(files), batch_files), desc="parse batches", disable=len(files) <= batch_files):
        recs, errs = _parse_batch(files[i:i + batch_files], workers)
        parts.append(records_to_tables(recs))
        errors += errs
        del recs
    if not parts:
        parts = [records_to_tables([])]
    arts, auths, refs = (pd.concat([p[k] for p in parts], ignore_index=True) for k in range(3))
    return fill_years_from_issue_df(arts), auths, refs, errors


# ------------------------------------------------------------------ corpus format 1.0 (JSON Lines)
def _corpus_file_tables(args: tuple[str, tuple[str, ...]]) -> tuple:
    """One data file → (articles, authors, references, errors, excluded types, id sources) — top-level so worker
    processes can pickle it; tables are built in the worker so records never cross the process boundary."""
    path, exclude = args
    try:
        recs, errors, excluded = corpus_jsonl.read_corpus_file(path, exclude)
    except OSError as e:                          # unreadable / corrupt .gz: the whole file is one error row
        return (*records_to_tables([]), [{"path": path, "error": f"{type(e).__name__}: {e}"}], Counter(), Counter())
    sources = Counter(r["id_source"] for r in recs)
    return (*records_to_tables(recs), errors, excluded, sources)


def read_corpus_tables(root: str | Path, pattern: str = corpus_jsonl.DEFAULT_GLOB, workers: int = 1,
                       exclude: tuple[str, ...] = ()) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict], dict]:
    """Corpus folder → (articles, authors, references, errors, stats{excluded, id_source, lines}).
    Errors are per line ("file:line"); a corpus without data files is an error, not an empty run."""
    files = corpus_jsonl.corpus_files(root, pattern)
    if not files:
        raise FileNotFoundError(f"no corpus data files matching {pattern!r} under {root} "
                                f"(expected articles/*.jsonl or *.jsonl.gz — docs/corpus/README.md)")
    jobs = [(f, tuple(exclude)) for f in files]
    if workers > 1 and len(files) > 1:
        with ProcessPoolExecutor(max_workers=min(workers, len(files))) as ex:
            parts = list(tqdm(ex.map(_corpus_file_tables, jobs), total=len(jobs), desc="corpus files"))
    else:
        parts = [_corpus_file_tables(j) for j in tqdm(jobs, desc="corpus files", disable=len(jobs) < 2)]
    arts, auths, refs = (pd.concat([p[k] for p in parts], ignore_index=True) for k in range(3))
    errors = [e for p in parts for e in p[3]]
    excluded = sum((p[4] for p in parts), Counter())
    sources = sum((p[5] for p in parts), Counter())
    stats = {"excluded": dict(excluded), "id_source": dict(sources),
             "lines": len(arts) + len(errors) + sum(excluded.values())}
    return fill_years_from_issue_df(arts), auths, refs, errors, stats


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
            auth_rows.append({"article_id": aid, "position": i, "affiliation_index": 0, "name": name, "name_en": "",
                              "affiliation_th": aff, "affiliation_en": "", "role": "", "is_student": False,
                              "org_key": org_key(aff, ""), **dict.fromkeys(CORPUS_AUTHOR_COLUMNS, "")})
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
    """First 80 folded characters — the DOI-collision check only (a prefix is enough to tell two titles apart there)."""
    return titles.fillna("").astype(str).map(norm_key).str[:80]


def full_title_key(titles: pd.Series) -> pd.Series:
    """The whole folded title: formulaic Thai titles that differ only at the end ("… ชั้นมัธยมศึกษาปีที่ 1" / "… 4")
    must stay different articles."""
    return titles.fillna("").astype(str).map(norm_key)


SHORT_TITLE = 40          # folded characters: a title this short ("บทบรรณาธิการ") is generic and needs the journal to match


def drop_duplicate_ids(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Always applied (even with dedup off): duplicate article_ids would inflate series counts."""
    out = _most_complete_first(df).drop_duplicates("article_id", keep="first")
    return out.sort_values("article_id").reset_index(drop=True), len(df) - len(out)


def _drop_doi_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Same DOI = duplicate when the Thai title keys match OR the English title keys match (empty keys
    never match). `df` is most-complete-first, so the first record seen of a duplicate set is kept.
    Returns (df, number of DOIs that still hold several records = different titles)."""
    df = df.reset_index(drop=True)
    doi = doi_key(df)
    cand = (doi != "") & doi.duplicated(keep=False)          # only DOIs that occur twice or more
    if not cand.any():
        return df, 0
    th, en = title_key(df["title_th"]), title_key(df["title_en"])
    drop: list[int] = []
    conflicts = 0
    for rows in doi[cand].groupby(doi[cand]).indices.values():   # groups are tiny; positions keep df order
        pos = doi[cand].index[rows]
        kept: list[int] = []
        for i in sorted(pos):
            if any((th[i] != "" and th[i] == th[k]) or (en[i] != "" and en[i] == en[k]) for k in kept):
                drop.append(i)
            else:
                kept.append(i)
        conflicts += len(kept) > 1
    return df.drop(index=drop), int(conflicts)


def _drop_title_year_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Same whole title and year = the same article, unless both carry a DOI and the DOIs differ, or the title is a
    short generic one and the journals differ. `df` is most-complete-first: the first of a duplicate set is kept."""
    df = df.reset_index(drop=True)
    tkey = full_title_key(df["title"])
    key = tkey.where(tkey == "", tkey + "|" + df["year"].astype(str))
    cand = (key != "") & key.duplicated(keep=False)
    if not cand.any():
        return df
    # a short generic title ("บทบรรณาธิการ", "Editorial") is only a duplicate inside one journal
    short = tkey.str.len() < SHORT_TITLE
    key = key.where(~(cand & short), key + "|" + journal_keys(df))
    cand = (key != "") & key.duplicated(keep=False)
    if not cand.any():
        return df
    doi = doi_key(df).tolist()
    drop: list[int] = []
    for rows in key[cand].groupby(key[cand]).indices.values():
        # same title + year: a duplicate unless both DOIs are known and differ. Linear: a kept row without a DOI
        # matches everything after it; otherwise a row matches when its DOI is empty or already kept.
        kept_dois: set[str] = set()
        kept_blank = kept_any = False
        for i in sorted(key[cand].index[rows]):
            d = doi[i]
            if kept_any and (kept_blank or d == "" or d in kept_dois):
                drop.append(i)
                continue
            kept_any = True
            if d:
                kept_dois.add(d)
            else:
                kept_blank = True
    return df.drop(index=drop)


def dedup(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """article_id → DOI (+ same Thai or same English title) → normalised title + year; keep the most complete.

    A DOI shared by articles whose Thai titles differ AND whose English titles differ is a metadata
    error (journals reuse or mistype DOIs), not a duplicate: those articles are all kept and counted in
    `doi_title_conflicts`. A missing title on one copy never makes it distinct.
    """
    n0 = len(df)
    df = _most_complete_first(df).drop_duplicates("article_id", keep="first")
    df, conflicts = _drop_doi_duplicates(df)
    df = _drop_title_year_duplicates(df)
    out = df.sort_values("article_id").reset_index(drop=True)
    return out, {"dropped": n0 - len(out), "doi_title_conflicts": conflicts}


def check_error_ceiling(n_files: int, errors: list[dict], max_ratio: float, errors_path: Path) -> None:
    """Stop the run when too many files failed — a parser bug must not publish a silently thinned corpus."""
    if n_files == 0 or not errors:
        return
    if len(errors) == n_files:
        raise RuntimeError(f"{_NONE_PARSED_TH} (none of {n_files:,} files could be parsed) - see {errors_path}")
    ratio = len(errors) / n_files
    if ratio > max_ratio:
        kinds = ", ".join(e["error"].split(":")[0] for e in errors[:3])
        raise RuntimeError(
            f"{len(errors):,} of {n_files:,} files failed to read/parse (ratio {ratio:.4f} > input.max_error_ratio "
            f"{max_ratio:g}); first error types: {kinds}. Inspect {errors_path}, fix the files or the parser, "
            f"or raise input.max_error_ratio deliberately.")


# ------------------------------------------------------------------ step
def ingest(cfg: dict) -> pd.DataFrame:
    icfg = cfg["input"]
    errors: list[dict] = []
    n_files = 0
    if icfg["format"] == "thaijo_md":
        articles, authors, refs, errors = read_thaijo_tables(icfg["path"], icfg["glob"], int(icfg["workers"]),
                                                             int(icfg["batch_files"]))
        n_files = len(articles) + len(errors)            # one article or one error per file
    elif icfg["format"] == "corpus_jsonl":
        articles, authors, refs, errors, cstats = read_corpus_tables(
            icfg["path"], icfg["corpus_glob"], int(icfg["workers"]), tuple(icfg["exclude_article_types"]))
        n_files = cstats["lines"]                        # one article, one error or one excluded article per line
        if cstats["excluded"]:
            print("[ingest] left out by input.exclude_article_types: "
                  + ", ".join(f"{k} {v:,}" for k, v in sorted(cstats["excluded"].items())))
    else:
        articles, authors, refs = read_table_input(cfg)
    n_raw = len(articles)
    articles = normalize_years(articles, int(icfg["min_year"]), icfg["max_year"])
    n_bad_year = n_raw - len(articles)
    articles = add_convenience_columns(articles)
    n_before_title = len(articles)
    articles = articles[articles["title"] != ""]
    n_no_title = n_before_title - len(articles)
    if icfg["dedup"]["enabled"]:
        articles, stats = dedup(articles)
        n_dup = stats["dropped"]
        if stats["doi_title_conflicts"]:
            print(f"[ingest] {stats['doi_title_conflicts']:,} DOIs are shared by articles with different titles "
                  f"— kept as separate articles (see `atlas profile` → DOI collisions)")
    else:
        articles, n_dup = drop_duplicate_ids(articles)
    keep = set(articles["article_id"])
    authors = authors[authors["article_id"].isin(keep)].drop_duplicates(["article_id", "position", "affiliation_index"])
    refs = refs[refs["article_id"].isin(keep)].drop_duplicates(["article_id", "position"])

    work = Path(cfg["pipeline"]["work_dir"])
    # the error ceiling is checked BEFORE the checkpoints are written: a refused run must not leave a thinned
    # 01_articles behind that a later `atlas run -s preprocess …` would carry on with
    write_table(pd.DataFrame(errors, columns=ERROR_COLUMNS), work / "01_ingest_errors.parquet")
    check_error_ceiling(n_files, errors, float(icfg["max_error_ratio"]), work / "01_ingest_errors.parquet")
    write_table(articles.reset_index(drop=True), work / "01_articles.parquet")
    write_table(authors.reset_index(drop=True), work / "01_authors.parquet")
    write_table(refs.reset_index(drop=True), work / "01_references.parquet")
    drops = {"records": n_raw, "articles": len(articles), "outside_year_range": n_bad_year, "no_title": n_no_title,
             "duplicates": n_dup, "year_missing": int(articles["year"].isna().sum()), "files_with_errors": len(errors)}
    (work / "01_ingest_meta.json").write_text(json.dumps(drops), encoding="utf-8")
    if errors:
        print(f"[ingest] WARNING: {len(errors):,} files could not be read or parsed and were skipped "
              f"(first: {errors[0]['path']} — {errors[0]['error']}) → 01_ingest_errors")
    print(f"[ingest] {n_raw:,} records → {len(articles):,} articles (left out: duplicates {n_dup:,}, "
          f"year outside {icfg['min_year']}–{icfg['max_year'] or 'next year'} {n_bad_year:,}, no title {n_no_title:,}; "
          f"year missing: {drops['year_missing']:,}; files with errors: {len(errors):,}) → {work}")
    return articles
