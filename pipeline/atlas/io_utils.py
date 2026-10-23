"""Parquet-first IO with pickle fallback (for environments without pyarrow), plus file operations that
survive Windows sharing violations (another process — `atlas status`, an antivirus, a backup tool — reading
the file at that moment makes os.replace / os.unlink fail with PermissionError on Windows)."""
from __future__ import annotations

import json
import math
import os
import random
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd


def _retry_permission(op: Callable[[], object], timeout: float) -> None:
    # short, jittered retries: a reader polling in a loop leaves only brief gaps between its reads, and a
    # growing backoff would keep missing them
    deadline = time.monotonic() + timeout
    while True:
        try:
            op()
            return
        except PermissionError:
            left = deadline - time.monotonic()
            if left <= 0:
                raise
            time.sleep(min(random.uniform(0.005, 0.05), left))


def replace_with_retry(src: str | Path, dst: str | Path, *, timeout: float = 20.0) -> None:
    """os.replace that waits out a reader holding `dst` (short retries for up to `timeout` seconds,
    then the PermissionError propagates)."""
    _retry_permission(lambda: os.replace(src, dst), timeout)


def unlink_with_retry(path: str | Path, *, timeout: float = 5.0) -> bool:
    """Delete `path`, waiting out a reader. True when it is gone (or never existed), False when it stayed
    locked past `timeout` — callers treat that as non-fatal."""
    def op() -> None:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    try:
        _retry_permission(op, timeout)
    except PermissionError:
        return False
    return True


def replace_blocked(path: str | Path) -> bool:
    """Windows: True when os.replace onto `path` would fail right now because another process has it open
    or mapped — whatever sharing that process allows (even read|write|delete, as antivirus/backup agents
    do, replacing an open file fails). The check opens the file for DELETE access with share mode 0 for an
    instant (no data read or written). Always False on POSIX and when the file does not exist."""
    if os.name != "nt" or not Path(path).exists():
        return False
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    # DELETE access, share mode 0 (any other open handle or mapping makes this fail), OPEN_EXISTING
    handle = k32.CreateFileW(str(path), 0x00010000, 0x0, None, 3, 0x80, None)
    if handle in (None, wintypes.HANDLE(-1).value):
        return ctypes.get_last_error() in (5, 32)              # access denied / sharing violation
    k32.CloseHandle(handle)
    return False


def fsync_dir(path: str | Path) -> None:
    """Make a rename inside `path` durable (POSIX); a no-op on Windows, where NTFS journals the rename."""
    if os.name == "nt":
        return
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)

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


def read_table(path: str | Path, columns: list[str] | None = None) -> pd.DataFrame:
    """A checkpoint table. `columns` reads only those that exist (the big 01_articles / 02_docs tables carry
    abstracts and doc_text — most steps need three or four columns); a missing one is left out, not an error."""
    path = Path(path)
    if path.exists():
        if columns is None:
            return pd.read_parquet(path)
        import pyarrow.parquet as pq
        have = set(pq.read_schema(path).names)
        return pd.read_parquet(path, columns=[c for c in columns if c in have])
    alt = path.with_suffix(".pkl")
    if alt.exists():
        df = pd.read_pickle(alt)
        return df if columns is None else df[[c for c in columns if c in df.columns]]
    raise FileNotFoundError(f"neither {path} nor {alt} exists — run the previous step first")


def read_optional(path: str | Path, columns: list[str] | None = None) -> pd.DataFrame | None:
    """A checkpoint table, or None when the step that writes it did not run (optional modules)."""
    try:
        return read_table(path, columns)
    except FileNotFoundError:
        return None


def read_json(path: str | Path) -> dict:
    """A JSON checkpoint (meta files), {} when it is not there."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def text_column(df: pd.DataFrame, col: str) -> pd.Series:
    """A text column with missing values as "" — an all-"" column when the table lacks it."""
    return df[col].fillna("").astype(str) if col in df.columns else pd.Series("", index=df.index, dtype=str)


def json_float(v, nd: int = 4) -> float | None:
    """A number for a published JSON file: rounded, None for missing / non-numeric / NaN / infinity (strict JSON)."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def read_or_empty(path: str | Path, columns: list[str]) -> pd.DataFrame:
    """A checkpoint table, or an empty one with `columns` when the step that writes it did not run."""
    try:
        return read_table(path)
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)
