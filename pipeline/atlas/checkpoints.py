"""Checkpoint integrity — a step that reads 03_embeddings.npy must get the vectors of THIS 02_docs.

embed writes docs_fingerprint (hash of the article_id order) into 03_meta.json; load_aligned()
re-checks the row count and the fingerprint and fails with a clear message instead of silently
pairing vectors with the wrong articles (e.g. after re-running preprocess without embed).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table


class CheckpointMismatch(RuntimeError):
    """work_dir checkpoints were written by different runs — re-run the named step."""


def docs_fingerprint(article_ids) -> str:
    h = hashlib.sha256()
    for a in article_ids:
        h.update(str(a).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:16]


def load_aligned(work: str | Path) -> tuple[pd.DataFrame, np.ndarray]:
    """(02_docs, 03_embeddings) after checking that they belong together."""
    work = Path(work)
    df = read_table(work / "02_docs.parquet")
    emb = np.load(work / "03_embeddings.npy")
    if len(emb) != len(df):
        raise CheckpointMismatch(f"03_embeddings.npy has {len(emb):,} rows but 02_docs has {len(df):,} "
                                 "— re-run the embed step")
    meta = work / "03_meta.json"
    if meta.exists():
        fp = json.loads(meta.read_text(encoding="utf-8")).get("docs_fingerprint")
        if fp and fp != docs_fingerprint(df["article_id"]):
            raise CheckpointMismatch("03_embeddings.npy was built for a different 02_docs — re-run the embed step")
    return df, emb


def analysed_window(work: str | Path) -> tuple[int, int] | None:
    """(first, last) year of the analysed corpus (06_meta.json: series years plus the trimmed recent years, so the
    newest issues stay findable) — None when the series step has not run."""
    p = Path(work) / "06_meta.json"
    if not p.exists():
        return None
    meta = json.loads(p.read_text(encoding="utf-8"))
    years = [int(y) for y in meta.get("years", [])] + [int(y) for y in meta.get("trimmed_years", [])]
    return (min(years), max(years)) if years else None


def article_topics(work: str | Path) -> pd.Series:
    """article_id → fine topic id (−1 = unassigned) for the articles of 02_docs."""
    work = Path(work)
    docs = read_table(work / "02_docs.parquet")[["article_id"]]
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    t = docs.merge(fine, on="article_id", how="left")
    return pd.Series(t["fine_topic"].fillna(-1).astype(int).to_numpy(), index=t["article_id"].astype(str).to_numpy())
