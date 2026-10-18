"""Parquet-first IO with pickle fallback (for environments without pyarrow)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import pyarrow  # noqa: F401
    _HAS_PARQUET = True
except ImportError:
    _HAS_PARQUET = False


def write_table(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if _HAS_PARQUET:
        df.to_parquet(path, index=False)
        return path
    alt = path.with_suffix(".pkl")
    df.to_pickle(alt)
    return alt


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.exists():
        return pd.read_parquet(path)
    alt = path.with_suffix(".pkl")
    if alt.exists():
        return pd.read_pickle(alt)
    raise FileNotFoundError(f"neither {path} nor {alt} exists — run the previous step first")
