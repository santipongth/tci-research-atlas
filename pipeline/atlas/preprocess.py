"""Phase 1.5 — build doc_text for embedding from title + keywords + abstract."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .io_utils import read_table, write_table


def build_doc_text(row: pd.Series, fields: list[str], max_chars: int) -> str:
    parts: list[str] = []
    for f in fields:
        v = row.get(f) or ""
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    text = " . ".join(parts)
    return text[:max_chars]


def preprocess(cfg: dict, df: pd.DataFrame | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    if df is None:
        df = read_table(work / "01_articles.parquet")

    ecfg = cfg["embedding"]
    df = df.copy()
    df["doc_text"] = df.apply(
        build_doc_text, axis=1,
        fields=ecfg["doc_fields"], max_chars=ecfg["max_chars_per_doc"],
    )
    # เรื่องที่ไม่มี abstract ใช้ title+keywords (ทำมาแล้วใน doc_text โดยอัตโนมัติ)
    df = df[df["doc_text"].str.len() >= 10].reset_index(drop=True)

    out = work / "02_docs.parquet"
    write_table(df, out)
    print(f"[preprocess] {len(df):,} docs -> {out} (avg {df['doc_text'].str.len().mean():.0f} chars)")
    return df
