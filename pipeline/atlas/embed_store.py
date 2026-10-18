"""Append-only embedding store keyed by a hash of (model_id, text) — lives in state_dir.

Layout: <root>/<model-slug>/index.parquet (key, shard, row) + shard_00000.npy, ...
Every add() writes a NEW shard and then the index. A run interrupted mid-way keeps all
fully written shards, so re-running embeds only what is missing; texts that did not
change between quarters are never paid for twice.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table


def text_key(model_id: str, text: str) -> str:
    return hashlib.sha1(f"{model_id}\n{text}".encode()).hexdigest()


class EmbeddingStore:
    def __init__(self, root: str | Path, model_id: str):
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", model_id)[:80]
        self.dir = Path(root) / f"{slug}-{hashlib.sha1(model_id.encode()).hexdigest()[:8]}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.dir / "index.parquet"
        try:
            self.index = read_table(self._index_path)
        except FileNotFoundError:
            self.index = pd.DataFrame({"key": pd.Series(dtype=str), "shard": pd.Series(dtype="int64"),
                                       "row": pd.Series(dtype="int64")})
        self._lookup = dict(zip(self.index["key"], zip(self.index["shard"], self.index["row"])))

    def __len__(self) -> int:
        return len(self._lookup)

    def has(self, key: str) -> bool:
        return key in self._lookup

    def add(self, keys: list[str], vectors: np.ndarray) -> None:
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
        np.save(self.dir / f"shard_{shard:05d}.npy", vectors[[i for _, i in new]])
        add = pd.DataFrame({"key": [k for k, _ in new], "shard": shard, "row": np.arange(len(new))})
        self.index = pd.concat([self.index, add], ignore_index=True)
        write_table(self.index, self._index_path)
        self._lookup.update({k: (shard, int(r)) for k, r in zip(add["key"], add["row"])})

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
