"""Append-only embedding store keyed by a hash of (model_id, text) — lives in state_dir.

Layout: <root>/<model-slug>/index.parquet (key, shard, row) + shard_00000.npy, ...
Every add() writes a NEW shard and then the index. A run interrupted mid-way keeps all
fully written shards, so re-running embeds only what is missing; texts that did not
change between quarters are never paid for twice.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import (
    fsync_dir,
    read_table,
    replace_blocked,
    replace_with_retry,
    unlink_with_retry,
    write_table,
)


def text_key(model_id: str, text: str) -> str:
    return hashlib.sha1(f"{model_id}\n{text}".encode()).hexdigest()


def _fsync(f) -> None:
    f.flush()
    os.fsync(f.fileno())


def store_dir(root: str | Path, model_id: str) -> Path:
    """The folder of the store for `model_id` (not created)."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", model_id)[:80]
    return Path(root) / f"{slug}-{hashlib.sha1(model_id.encode()).hexdigest()[:8]}"


class EmbeddingStore:
    def __init__(self, root: str | Path, model_id: str):
        self.dir = store_dir(root, model_id)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.dir / "index.parquet"
        self.reload()

    def reload(self) -> None:
        """Re-read index.parquet (call after taking the run lock: another run may have written since)."""
        try:
            self.index = read_table(self._index_path)
        except FileNotFoundError:
            self.index = pd.DataFrame({"key": pd.Series(dtype=str), "shard": pd.Series(dtype="int64"),
                                       "row": pd.Series(dtype="int64")})
        self._lookup = dict(zip(self.index["key"], zip(self.index["shard"], self.index["row"])))

    def index_replace_blocked(self) -> bool:
        """Windows: another program holds index.parquet so that a checkpoint would fail right now."""
        return replace_blocked(self._index_path)

    def __len__(self) -> int:
        return len(self._lookup)

    def has(self, key: str) -> bool:
        return key in self._lookup

    def add(self, keys: list[str], vectors: np.ndarray, *, replace_timeout: float = 20.0) -> None:
        """Write the new keys' vectors as a NEW shard, then atomically replace the index.

        The shard is created exclusively ("xb"): an existing file — an orphan of a killed run, or another
        writer's — is never overwritten; the next free number is used. On Windows the index replace waits up
        to `replace_timeout` s for readers (`atlas status`, antivirus); if it still fails, the new shard is
        removed, memory is unchanged and the PermissionError propagates (the caller keeps the vectors).
        """
        vectors = np.asarray(vectors, dtype=np.float32)
        if len(keys) != len(vectors):
            raise ValueError("keys and vectors differ in length")
        new, seen = [], set()
        for i, k in enumerate(keys):
            if k not in self._lookup and k not in seen:
                new.append((k, i))
                seen.add(k)
        if not new:
            return
        shard = int(self.index["shard"].max()) + 1 if len(self.index) else 0
        while True:
            shard_path = self.dir / f"shard_{shard:05d}.npy"
            try:
                f = open(shard_path, "xb")
            except FileExistsError:
                shard += 1
                continue
            with f:
                np.save(f, vectors[[i for _, i in new]])
                _fsync(f)
            break
        add = pd.DataFrame({"key": [k for k, _ in new], "shard": shard, "row": np.arange(len(new))})
        index = pd.concat([self.index, add], ignore_index=True)
        tmp = self.dir / "index.tmp.parquet"
        written = tmp
        try:                                                                # until the new index is in place,
            written = write_table(index, tmp)                               # any failure removes the shard
            with open(written, "rb+") as f:                                 # durable before it replaces the
                _fsync(f)                                                   # old index (power loss safe)
            replace_with_retry(written, self.dir / written.name.replace(".tmp", ""), timeout=replace_timeout)
        except BaseException:
            unlink_with_retry(shard_path, timeout=1.0)                      # not referenced by any index
            unlink_with_retry(written, timeout=1.0)
            raise
        fsync_dir(self.dir)
        self.index = index
        self._lookup.update({k: (shard, int(r)) for k, r in zip(add["key"], add["row"])})

    @property
    def dim(self) -> int | None:
        """Vector length of the stored vectors (None while empty)."""
        if not len(self.index):
            return None
        shard = int(self.index["shard"].iloc[0])
        return int(np.load(self.dir / f"shard_{shard:05d}.npy", mmap_mode="r").shape[1])

    def get(self, keys: list[str]) -> np.ndarray:
        missing = [k for k in keys if k not in self._lookup]
        if missing:
            raise KeyError(f"{len(missing)} keys not in store")
        by_shard: dict[int, list[tuple[int, int]]] = {}
        for pos, k in enumerate(keys):
            s, r = self._lookup[k]
            by_shard.setdefault(int(s), []).append((pos, int(r)))
        out: np.ndarray | None = None
        for s, items in by_shard.items():
            arr = np.load(self.dir / f"shard_{s:05d}.npy", mmap_mode="r")
            if out is None:
                out = np.empty((len(keys), arr.shape[1]), dtype=np.float32)
            pos, rows = zip(*items)
            out[list(pos)] = arr[list(rows)]
        return out if out is not None else np.empty((0, 0), dtype=np.float32)
