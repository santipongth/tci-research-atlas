"""Embedding step. Providers:

  api   : any OpenAI-compatible endpoint (OpenAI, Gemini, OpenRouter, vLLM, Ollama)
  local : sentence-transformers (default BAAI/bge-m3, max_seq_length 1024)
  lite  : TF-IDF char n-grams + TruncatedSVD on CPU — for tests/CI/demos (lower quality)

api/local vectors are cached in state_dir/embeddings (EmbeddingStore): resumable and
incremental across quarters. Output: work/03_embeddings.npy (+ 03_meta.json).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
from tqdm import tqdm

from atlas.embed_store import EmbeddingStore, text_key
from atlas.io_utils import read_table


class ApiEmbedder:
    def __init__(self, cfg: dict):
        from openai import OpenAI  # optional dependency: uv sync --extra api

        acfg = cfg["embedding"]["api"]
        api_key = os.environ.get(acfg["api_key_env"], "")
        if not api_key:
            raise OSError(f"set ${acfg['api_key_env']} before running with embedding.provider=api")
        self.client = OpenAI(base_url=acfg["base_url"], api_key=api_key, timeout=120)
        self.model, self.dimensions = acfg["model"], acfg.get("dimensions")
        self.max_retries = int(acfg.get("max_retries", 6))
        self.model_id = f"api|{acfg['base_url']}|{self.model}|{self.dimensions}"

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        kwargs = {"model": self.model, "input": texts}
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions
        delay = 2.0
        for attempt in range(self.max_retries):
            try:
                resp = self.client.embeddings.create(**kwargs)
                return np.array([d.embedding for d in resp.data], dtype=np.float32)
            except Exception as e:  # noqa: BLE001 — retry any transport/API error
                if attempt == self.max_retries - 1:
                    raise
                print(f"[embed] retry {attempt + 1}/{self.max_retries}: {e}")
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")


class LocalEmbedder:
    def __init__(self, cfg: dict):
        from sentence_transformers import SentenceTransformer  # optional: uv sync --extra local

        lcfg = cfg["embedding"]["local"]
        self.model = SentenceTransformer(lcfg["model"], device=lcfg["device"])
        self.model.max_seq_length = int(lcfg["max_seq_length"])
        self.batch_size = int(lcfg["batch_size"])
        if lcfg.get("fp16") and lcfg["device"] == "cuda":
            self.model.half()
        self.model_id = f"local|{lcfg['model']}|{lcfg['max_seq_length']}"

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        vec = self.model.encode(texts, batch_size=self.batch_size, convert_to_numpy=True,
                                normalize_embeddings=True, show_progress_bar=False)
        return vec.astype(np.float32)


def get_embedder(cfg: dict):
    provider = cfg["embedding"]["provider"]
    if provider == "api":
        return ApiEmbedder(cfg)
    if provider == "local":
        return LocalEmbedder(cfg)
    raise ValueError(f"no embedder object for provider {provider!r}")


def lite_embed(texts: list[str], lite_cfg: dict, seed: int) -> np.ndarray:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(int(lite_cfg["ngram_min"]), int(lite_cfg["ngram_max"])),
                          max_features=int(lite_cfg["max_features"]), sublinear_tf=True,
                          min_df=min(int(lite_cfg["min_df"]), max(1, len(texts))))
    X = vec.fit_transform(texts)
    k = max(1, min(int(lite_cfg["dim"]), X.shape[1] - 1, len(texts) - 1))
    return TruncatedSVD(k, random_state=seed).fit_transform(X).astype(np.float32)


def _normalize(arr: np.ndarray) -> np.ndarray:
    return (arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-9)).astype(np.float32)


def embed(cfg: dict, embedder=None) -> np.ndarray:
    work = Path(cfg["pipeline"]["work_dir"])
    texts = read_table(work / "02_docs.parquet")["doc_text"].tolist()
    provider = cfg["embedding"]["provider"]
    if embedder is None and provider == "lite":
        lcfg = cfg["embedding"]["lite"]
        arr = lite_embed(texts, lcfg, int(cfg["pipeline"]["seed"]))
        model_id = f"lite|char{lcfg['ngram_min']}-{lcfg['ngram_max']}|svd{arr.shape[1]}"
    else:
        embedder = embedder or get_embedder(cfg)
        pcfg = cfg["embedding"].get(provider, {}) if provider in ("api", "local") else {}
        batch, every = int(pcfg.get("batch_size", 64)), int(pcfg.get("checkpoint_every", 5000))
        store = EmbeddingStore(Path(cfg["pipeline"]["state_dir"]) / "embeddings", embedder.model_id)
        keys = [text_key(embedder.model_id, t) for t in texts]
        text_of = dict(zip(keys, texts))
        todo = list(dict.fromkeys(k for k in keys if not store.has(k)))
        print(f"[embed] {len(keys) - len(todo):,} cached, {len(todo):,} to embed ({embedder.model_id})")
        buf_k: list[str] = []
        buf_v: list[np.ndarray] = []
        try:
            for i in tqdm(range(0, len(todo), batch), desc="embed", disable=not todo):
                chunk = todo[i:i + batch]
                vec = embedder.embed_batch([text_of[k] for k in chunk])   # paid for only once it returns
                buf_k += chunk
                buf_v.append(vec)
                if len(buf_k) >= every:
                    store.add(buf_k, np.vstack(buf_v))
                    buf_k, buf_v = [], []
        finally:
            # keep vectors already paid for, even when a later batch raises or Ctrl-C arrives
            if buf_k:
                store.add(buf_k, np.vstack(buf_v))
        arr, model_id = store.get(keys), embedder.model_id
    arr = _normalize(arr)
    work.mkdir(parents=True, exist_ok=True)
    np.save(work / "03_embeddings.npy", arr)
    (work / "03_meta.json").write_text(json.dumps({"model_id": model_id, "n": int(arr.shape[0]),
                                                   "dim": int(arr.shape[1])}), encoding="utf-8")
    print(f"[embed] {arr.shape} → 03_embeddings.npy")
    return arr
