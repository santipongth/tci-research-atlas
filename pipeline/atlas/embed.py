"""Embedding step. Providers:

  api   : any OpenAI-compatible /embeddings endpoint (BGE-M3 on TEI/vLLM/Infinity/Ollama, DeepInfra,
          OpenAI, ...) — see atlas.embed_api
  local : sentence-transformers (default BAAI/bge-m3, max_seq_length 1024)
  lite  : TF-IDF char n-grams + TruncatedSVD on CPU — for tests/CI/demos (lower quality)

api/local vectors go through atlas.embed_runner into state_dir/embeddings (EmbeddingStore + journal):
resumable after Ctrl-C, a closed window, a crash or power loss, and incremental across quarters.
For the big one-off run use `atlas embed -c config.yaml` (status: `atlas status`, stop: `atlas embed-stop`).
Output: work/03_embeddings.npy (+ 03_meta.json).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from atlas.checkpoints import docs_fingerprint
from atlas.embed_api import ApiEmbedder, api_store_id
from atlas.embed_runner import run_embedding
from atlas.embed_store import EmbeddingStore, text_key
from atlas.io_utils import read_table
from atlas.jobs import RunStopped


def local_store_id(lcfg: dict) -> str:
    return f"local|{lcfg['model']}|{lcfg['max_seq_length']}"


class LocalEmbedder:
    def __init__(self, cfg: dict):
        from sentence_transformers import SentenceTransformer  # optional: uv sync --extra local

        lcfg = cfg["embedding"]["local"]
        self.model = SentenceTransformer(lcfg["model"], device=lcfg["device"])
        self.model.max_seq_length = int(lcfg["max_seq_length"])
        self.batch_size = int(lcfg["batch_size"])
        if lcfg.get("fp16") and lcfg["device"] == "cuda":
            self.model.half()
        self.model_id = local_store_id(lcfg)

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


def store_id_for(cfg: dict) -> str | None:
    """The store id the configured provider writes to (None for lite, which has no store)."""
    provider = cfg["embedding"]["provider"]
    if provider == "api":
        return api_store_id(cfg["embedding"]["api"])
    if provider == "local":
        return local_store_id(cfg["embedding"]["local"])
    return None


def store_root(cfg: dict) -> Path:
    return Path(cfg["pipeline"]["state_dir"]) / "embeddings"


def runner_cfg(cfg: dict) -> dict:
    """The runner settings of the configured provider (local: one batch at a time on the GPU/CPU)."""
    provider = cfg["embedding"]["provider"]
    if provider == "api":
        return dict(cfg["embedding"]["api"])
    if provider == "local":
        return {**cfg["embedding"]["local"], "concurrency": 1}
    return {}


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


def embed_texts(cfg: dict, texts: list[str], embedder=None) -> np.ndarray:
    """L2-normalised vectors for texts outside the corpus (OpenAlex reference works, bake-off samples).

    Same machinery as the embed step: get_embedder → run_embedding → state_dir/embeddings/<store id>, so
    texts already stored are free, an API run survives a crash and `atlas status` shows it. A stopped run
    raises RunStopped (as embed() does). lite → ValueError (lite vectors exist only per fit — use
    lite_embed() on all texts together).
    """
    if embedder is None and cfg["embedding"]["provider"] == "lite":
        raise ValueError("lite vectors exist only per fit — use lite_embed() on all texts together")
    embedder = embedder or get_embedder(cfg)
    store = EmbeddingStore(store_root(cfg), embedder.model_id)
    stats = run_embedding(list(texts), embedder, store, runner_cfg(cfg), progress=False)
    if stats["status"] != "done":
        left = stats["total"] - stats["cached"] - stats["embedded"]
        raise RunStopped(f"embedding stopped with {left:,} texts left — run the same command again to resume",
                         abandoned=int(stats.get("abandoned") or 0))
    return _normalize(store.get([text_key(embedder.model_id, t) for t in texts]))




def embed(cfg: dict, embedder=None) -> np.ndarray:
    work = Path(cfg["pipeline"]["work_dir"])
    docs = read_table(work / "02_docs.parquet")
    texts = docs["doc_text"].tolist()
    provider = cfg["embedding"]["provider"]
    meta: dict = {}
    if embedder is None and provider == "lite":
        lcfg = cfg["embedding"]["lite"]
        if len(texts) > int(cfg["embedding"]["lite_max_docs"]):
            print(f"[embed] WARNING: embedding.provider is 'lite' (TF-IDF+SVD, CI/tests only) on {len(texts):,} "
                  f"documents (> embedding.lite_max_docs = {int(cfg['embedding']['lite_max_docs']):,}) — topics "
                  f"will be low quality; use embedding.provider: local or api for a real run")
        arr = lite_embed(texts, lcfg, int(cfg["pipeline"]["seed"]))
        model_id = f"lite|char{lcfg['ngram_min']}-{lcfg['ngram_max']}|svd{arr.shape[1]}"
    else:
        embedder = embedder or get_embedder(cfg)
        if isinstance(embedder, ApiEmbedder) and not embedder.has_key:
            print(f"[embed] ${embedder.key_env} is not set — requests go without an Authorization header "
                  f"(fine for a self-hosted server; a server that needs a key answers 401)")
        store = EmbeddingStore(store_root(cfg), embedder.model_id)
        stats = run_embedding(texts, embedder, store, runner_cfg(cfg))
        if stats["status"] != "done":
            raise RunStopped(f"embedding stopped with {stats['total'] - stats['cached'] - stats['embedded']:,} "
                             f"documents left — run the same command again to resume",
                             abandoned=int(stats.get("abandoned") or 0))
        arr, model_id = store.get([text_key(embedder.model_id, t) for t in texts]), embedder.model_id
        meta = {"store_id": embedder.model_id, "n_retries": stats["retries"], "n_truncated": stats["truncated"]}
    arr = _normalize(arr)
    work.mkdir(parents=True, exist_ok=True)
    np.save(work / "03_embeddings.npy", arr)
    (work / "03_meta.json").write_text(json.dumps({"model_id": model_id, "n": int(arr.shape[0]),
                                                   "dim": int(arr.shape[1]), **meta,
                                                   "docs_fingerprint": docs_fingerprint(docs["article_id"])}),
                                       encoding="utf-8")
    print(f"[embed] {arr.shape} → 03_embeddings.npy")
    return arr
