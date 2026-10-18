"""Phase 2 — Embedding. Supports two providers:

  - api   : any OpenAI-compatible embeddings endpoint (OpenAI, Gemini, OpenRouter,
            vLLM, Ollama ...). Batched, retried, checkpointed — safe to Ctrl-C and rerun.
  - local : sentence-transformers (default BAAI/bge-m3) on your own GPU/CPU.

Output: work/03_embeddings.npy  (float32, row-aligned with 02_docs.parquet)
Checkpoint: work/emb_ckpt/chunk_*.npy
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import read_table, write_table
from tqdm import tqdm


# ---------------------------------------------------------------- API provider
class ApiEmbedder:
    def __init__(self, cfg: dict):
        from openai import OpenAI  # lazy import
        acfg = cfg["embedding"]["api"]
        api_key = os.environ.get(acfg["api_key_env"], "")
        if not api_key:
            raise EnvironmentError(f"set ${acfg['api_key_env']} before running with provider=api")
        self.client = OpenAI(base_url=acfg["base_url"], api_key=api_key, timeout=120)
        self.model = acfg["model"]
        self.dimensions = acfg.get("dimensions")
        self.max_retries = int(acfg.get("max_retries", 6))

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        kwargs = {"model": self.model, "input": texts}
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions
        delay = 2.0
        for attempt in range(self.max_retries):
            try:
                resp = self.client.embeddings.create(**kwargs)
                return np.array([d.embedding for d in resp.data], dtype=np.float32)
            except Exception as e:  # noqa: BLE001
                if attempt == self.max_retries - 1:
                    raise
                print(f"[embed] retry {attempt + 1}/{self.max_retries}: {e}")
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")


# ---------------------------------------------------------------- local provider
class LocalEmbedder:
    def __init__(self, cfg: dict):
        from sentence_transformers import SentenceTransformer  # lazy import
        lcfg = cfg["embedding"]["local"]
        self.model = SentenceTransformer(lcfg["model"], device=lcfg["device"])
        if lcfg.get("max_seq_length"):
            self.model.max_seq_length = lcfg["max_seq_length"]
        self.batch_size = int(lcfg["batch_size"])
        self.fp16 = bool(lcfg.get("fp16", False))
        self.max_retries = 1

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        import torch
        with torch.autocast("cuda", enabled=self.fp16) if self.fp16 else _nullctx():
            vec = self.model.encode(
                texts, batch_size=self.batch_size,
                convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False,
            )
        return vec.astype(np.float32)


class _nullctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False


def get_embedder(cfg: dict):
    provider = cfg["embedding"]["provider"]
    if provider == "api":
        return ApiEmbedder(cfg)
    if provider == "local":
        return LocalEmbedder(cfg)
    raise ValueError(f"unknown embedding.provider: {provider}")


# ---------------------------------------------------------------- runner
def embed(cfg: dict, df: pd.DataFrame | None = None) -> np.ndarray:
    work = Path(cfg["pipeline"]["work_dir"])
    if df is None:
        df = read_table(work / "02_docs.parquet")

    final = work / "03_embeddings.npy"
    if final.exists():
        arr = np.load(final)
        if len(arr) == len(df):
            print(f"[embed] reuse checkpoint {final} ({arr.shape})")
            return arr
        print("[embed] checkpoint shape mismatch — re-embedding")

    ckpt_dir = work / "emb_ckpt"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    provider = cfg["embedding"]["provider"]
    batch_size = int(cfg["embedding"][provider].get("batch_size", 128))
    every = int(cfg["embedding"][provider].get("checkpoint_every", 5000))
    embedder = get_embedder(cfg)

    texts = df["doc_text"].tolist()
    n = len(texts)
    chunks: dict[int, np.ndarray] = {}

    # load existing chunk checkpoints (resume)
    done = 0
    for f in sorted(ckpt_dir.glob("chunk_*.npy")):
        start = int(f.stem.split("_")[1])
        chunks[start] = np.load(f)
        done += len(chunks[start])
    if done:
        print(f"[embed] resume: {done:,}/{n:,} already embedded")

    pending = [i for i in range(0, n, batch_size)
               if not any(s <= i < s + len(c) for s, c in chunks.items())]

    buffer: dict[int, np.ndarray] = {}
    buffered = 0
    for i in tqdm(pending, desc=f"embedding ({provider})", unit="batch"):
        batch = texts[i:i + batch_size]
        vec = embedder.embed_batch(batch)
        buffer[i] = vec
        buffered += len(vec)
        if buffered >= every:
            _flush(ckpt_dir, chunks, buffer)
            buffer, buffered = {}, 0
    if buffer:
        _flush(ckpt_dir, chunks, buffer)

    # stitch in order
    rows = []
    for f in sorted(ckpt_dir.glob("chunk_*.npy")):
        rows.append(np.load(f))
    arr = np.vstack(rows).astype(np.float32)
    assert len(arr) == n, f"stitched {len(arr)} != {n} docs — delete work/emb_ckpt and rerun"

    # L2 normalize (cosine-ready) — local provider already normalizes; harmless to redo
    norm = np.linalg.norm(arr, axis=1, keepdims=True)
    arr = arr / np.maximum(norm, 1e-9)
    np.save(final, arr)
    print(f"[embed] {arr.shape} -> {final}")
    return arr


def _flush(ckpt_dir: Path, chunks: dict, buffer: dict) -> None:
    for start, vec in buffer.items():
        np.save(ckpt_dir / f"chunk_{start:08d}.npy", vec)
        chunks[start] = vec
    print(f"[embed] checkpoint: {sum(len(c) for c in chunks.values()):,} vectors")
