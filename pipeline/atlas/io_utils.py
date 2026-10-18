"""Parquet-first IO with pickle fallback (for environments without pyarrow), plus file operations that
survive Windows sharing violations (another process — `atlas status`, an antivirus, a backup tool — reading
the file at that moment makes os.replace / os.unlink fail with PermissionError on Windows)."""
from __future__ import annotations

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


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.exists():
        return pd.read_parquet(path)
    alt = path.with_suffix(".pkl")
    if alt.exists():
        return pd.read_pickle(alt)
    raise FileNotFoundError(f"neither {path} nor {alt} exists — run the previous step first")
