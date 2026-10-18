"""Phase 1 — Ingest TCI metadata (CSV/JSON/JSONL/Parquet), normalize, dedup.

Output: work/01_articles.parquet  (canonical schema, one row per article)
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import read_table, write_table

CANONICAL_COLUMNS = [
    "article_id", "title_th", "title_en", "abstract_th", "abstract_en",
    "keywords_th", "keywords_en", "authors", "affiliations",
    "journal_name", "year", "volume", "issue", "tci_tier", "doi", "url",
    "title", "abstract", "keywords",  # merged convenience fields
    "doc_text",                       # text used for embedding (built in preprocess)
]

_SPLIT_RE = re.compile(r"[;|]")


def _read_any(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"input not found: {p}")
    if p.suffix == ".csv":
        return pd.read_csv(p, dtype=str, keep_default_na=False)
    if p.suffix == ".parquet":
        return read_table(p)
    if p.suffix in (".jsonl", ".ndjson"):
        return pd.read_json(p, lines=True)
    if p.suffix == ".json":
        obj = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(obj, dict):  # e.g. {"articles": [...]}
            key = next(k for k, v in obj.items() if isinstance(v, list))
            obj = obj[key]
        return pd.DataFrame(obj)
    raise ValueError(f"unsupported input type: {p.suffix}")


def _clean_text(s) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = str(s)
    s = re.sub(r"<[^>]+>", " ", s)          # strip HTML tags (บทคัดย่อ TCI มักมี)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _norm_list(s) -> list[str]:
    s = _clean_text(s)
    if not s:
        return []
    return [x.strip() for x in _SPLIT_RE.split(s) if x.strip()]


def _merge_bi(th: str, en: str) -> str:
    th, en = _clean_text(th), _clean_text(en)
    return " ".join(x for x in (th, en) if x)


def _title_key(title: str) -> str:
    t = re.sub(r"[^0-9a-zA-Zก-๙]+", "", title.lower())
    return hashlib.md5(t.encode()).hexdigest()[:16]


def _completeness(row: pd.Series) -> int:
    return sum(bool(_clean_text(row.get(c))) for c in
               ("title", "abstract", "keywords", "authors", "doi"))


def dedup(df: pd.DataFrame, enabled: bool) -> pd.DataFrame:
    """Drop duplicates: same DOI first, then same normalized title — keep the most complete record."""
    if not enabled or df.empty:
        return df
    df = df.copy()
    df["_completeness"] = df.apply(_completeness, axis=1)
    df["_tkey"] = df["title"].map(_title_key)
    df["_doi"] = df["doi"].str.lower().str.strip()
    df = df.sort_values("_completeness", ascending=False)
    seen_doi, keep = set(), []
    for _, row in df.iterrows():
        if row["_doi"] and row["_doi"] in seen_doi:
            continue
        if row["_doi"]:
            seen_doi.add(row["_doi"])
        keep.append(row.name)
    df = df.loc[keep]
    df = df.drop_duplicates(subset=["_tkey"], keep="first")
    return df.drop(columns=["_completeness", "_tkey", "_doi"])


def ingest(cfg: dict) -> pd.DataFrame:
    raw = _read_any(cfg["input"]["path"])
    colmap = {k: v for k, v in cfg["input"]["columns"].items() if v in raw.columns}
    missing = [k for k in ("article_id", "year") if k not in colmap]
    if missing:
        raise ValueError(f"input missing required columns mapped to: {missing}")

    df = raw.rename(columns={v: k for k, v in colmap.items()})
    for c in CANONICAL_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[CANONICAL_COLUMNS]

    # normalize
    df["title"] = [_merge_bi(a, b) for a, b in zip(df["title_th"], df["title_en"])]
    df["abstract"] = [_merge_bi(a, b) for a, b in zip(df["abstract_th"], df["abstract_en"])]
    df["keywords"] = ["; ".join(_norm_list(a) + _norm_list(b))
                      for a, b in zip(df["keywords_th"], df["keywords_en"])]
    for c in df.columns:
        if c not in ("year",):
            df[c] = df[c].map(_clean_text) if df[c].dtype == object else df[c]

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    min_year = cfg["input"].get("min_year")
    if min_year:
        df = df[(df["year"].isna()) | (df["year"] >= min_year)]

    # drop rows with nothing to embed
    df = df[df["title"].str.len() > 0]
    df = dedup(df, cfg["input"].get("dedup", {}).get("enabled", True))
    df = df.reset_index(drop=True)

    out = Path(cfg["pipeline"]["work_dir"]) / "01_articles.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_table(df, out)
    print(f"[ingest] {len(df):,} articles -> {out}")
    return df
