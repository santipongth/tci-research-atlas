"""Build doc_text (the text that gets embedded) from title + keywords + abstract."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table


def build_doc_texts(df: pd.DataFrame, fields: list[str], max_chars: int) -> list[str]:
    cols = [df[f].fillna("").astype(str).str.strip().tolist() for f in fields if f in df.columns]
    if not cols:
        return [""] * len(df)
    return [" . ".join(v for v in vals if v)[:max_chars] for vals in zip(*cols)]


def preprocess(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    df = read_table(work / "01_articles.parquet")
    ecfg = cfg["embedding"]
    df = df.assign(doc_text=build_doc_texts(df, ecfg["doc_fields"], int(ecfg["max_chars_per_doc"])))
    df = df[df["doc_text"].str.len() >= 10].reset_index(drop=True)
    write_table(df, work / "02_docs.parquet")
    print(f"[preprocess] {len(df):,} docs (avg {df['doc_text'].str.len().mean():.0f} chars) → 02_docs")
    return df
