"""Embeddings over any OpenAI-compatible API (BGE-M3 on TEI/vLLM/Infinity/Ollama, DeepInfra, OpenAI, ...).

Only the embedding-specific parts live here — request body, response validation, batch split and
single-text truncation on "too large", `ApiEmbedder` and `check()`. HTTP, classification, backoff and
the retry loop come from atlas.api_http (shared with the P1 LLM client).

Failure policy (embed_batch):
  transient (408/409/425/429/5xx, network, malformed response)  -> retry (forever unless max_retries)
  too large (413, or 400/422 saying so)                         -> split the batch in half; a single text
                                                                   is cut in half down to min_text_chars
  permanent (401/403/404/other 4xx)                             -> EmbeddingConfigError at once
"""
from __future__ import annotations

import base64
import binascii
import os
import random
import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from atlas.api_http import (
    ApiConfigError,
    EventHandler,
    HttpPermanentError,
    RateLimiter,
    RetryPolicy,
    TooLargeError,
    TransientError,
    Transport,
    call_with_retry,
    explain_permanent,
    post_json,
    urllib_transport,
)

CHECK_TEXT = "TCI Research Atlas embedding check — \N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER CHO CHANG}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}"


class EmbeddingConfigError(ApiConfigError):
    """Permanent embedding failure: fix the config (key, base_url, model, store_id) and rerun."""


def api_store_id(acfg: dict) -> str:
    """Store id for API vectors: model + dimensions only, never base_url (moving servers must not
    re-embed the corpus). `store_id` in config overrides it."""
    return acfg.get("store_id") or f"api|{acfg['model']}|{acfg.get('dimensions')}"


def request_body(texts: list[str], model: str, dimensions: int | None) -> dict:
    body: dict[str, Any] = {"model": model, "input": list(texts), "encoding_format": "float"}
    if dimensions:
        body["dimensions"] = int(dimensions)
    return body


def parse_embeddings(obj: Any, n: int) -> np.ndarray:
    """(n, dim) float32 aligned to the input order; anything malformed raises TransientError (re-requested)."""
    data = obj.get("data") if isinstance(obj, dict) else None
    if not isinstance(data, list):
        raise TransientError("malformed response: no `data` list")
    if len(data) != n:
        raise TransientError(f"malformed response: {len(data)} vectors for a batch of {n}")
    try:
        items = sorted(data, key=lambda d: d["index"])
    except (KeyError, TypeError):
        raise TransientError("malformed response: an item has no usable `index`") from None
    if [d["index"] for d in items] != list(range(n)):
        raise TransientError(f"malformed response: indices {[d['index'] for d in items][:10]} for a batch of {n}")
    vecs = []
    for d in items:
        emb = d.get("embedding")
        try:
            v = (np.frombuffer(base64.b64decode(emb), dtype="<f4") if isinstance(emb, str)
                 else np.asarray(emb, dtype=np.float32))
        except (TypeError, ValueError, binascii.Error):
            raise TransientError("malformed response: an embedding is not a list of numbers") from None
        vecs.append(v)
    if any(v.ndim != 1 or v.size == 0 or v.size != vecs[0].size for v in vecs):
        raise TransientError("malformed response: vectors of different lengths")
    arr = np.vstack(vecs).astype(np.float32)
    if not np.isfinite(arr).all():
        raise TransientError("malformed response: non-finite values (NaN/Inf) in a vector")
    return arr


def dim_mismatch(store_dim: int, got: int, store_id: str) -> EmbeddingConfigError:
    return EmbeddingConfigError(
        f"store \N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER SARA I} {store_dim} \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK} server \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER BO BAIMAI} {got} — \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NGO NGU} store_id \N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK} / the existing store "
        f"({store_id}) holds {store_dim}-dim vectors but the server returned {got}: a different model or "
        f"settings — set embedding.api.store_id to a new name (or fix model/dimensions)")


class ApiEmbedder:
    """`embed_batch(texts)` -> vectors aligned to `texts`; retries, splits and truncation happen inside.

    `on_event(kind, info)` (kinds: retry, split, truncated) may be set later — the runner subscribes to it.
    Counters `n_retries` / `n_truncated` are thread-safe. The API key is read from the env var named by
    `api_key_env`; when it is empty no Authorization header is sent (self-hosted servers often need none —
    a server that does answers 401, which names the variable to set).
    """

    def __init__(self, cfg: dict, transport: Transport | None = None, sleep: Callable[[float], Any] | None = None,
                 on_event: EventHandler | None = None, rand: Callable[[], float] = random.random):
        acfg = cfg["embedding"]["api"]
        self.base_url = str(acfg["base_url"]).rstrip("/")
        self.url = f"{self.base_url}/embeddings"
        self.model, self.dimensions = acfg["model"], acfg.get("dimensions")
        self.key_env = acfg["api_key_env"]
        self.__key = os.environ.get(self.key_env, "").strip()
        self.model_id = api_store_id(acfg)
        self.transport = transport or urllib_transport
        self.timeout = float(acfg["request_timeout"])
        self.min_text_chars = int(acfg["min_text_chars"])
        self._sleep, self._rand = sleep, rand
        self.policy = RetryPolicy(acfg["backoff_initial"], acfg["backoff_max"], acfg.get("max_retries"),
                                  sleep=sleep, rand=rand)
        rpm = acfg.get("requests_per_minute")
        self.limiter = RateLimiter(rpm) if rpm else None
        self.on_event = on_event
        self.n_retries = 0
        self.n_truncated = 0
        self.dim: int | None = None
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"ApiEmbedder(url={self.url!r}, model={self.model!r}, store_id={self.model_id!r})"

    @property
    def has_key(self) -> bool:
        return bool(self.__key)

    # ---- events and counters
    def _emit(self, kind: str, info: dict) -> None:
        if kind == "retry":
            with self._lock:
                self.n_retries += 1
        if self.on_event:
            self.on_event(kind, info)

    def cancel(self) -> None:
        """Stop retrying: a worker in (or entering) a backoff wait raises api_http.Cancelled."""
        self.policy.cancel()

    # ---- one request
    def _request(self, texts: list[str]) -> np.ndarray:
        if self.limiter:
            self.limiter.acquire()
        headers = {"Authorization": f"Bearer {self.__key}"} if self.__key else {}
        obj = post_json(self.transport, self.url, request_body(texts, self.model, self.dimensions),
                        headers=headers, timeout=self.timeout)
        return parse_embeddings(obj, len(texts))

    def _send(self, texts: list[str], policy: RetryPolicy | None = None) -> np.ndarray:
        try:
            arr = call_with_retry(lambda: self._request(texts), policy or self.policy, self._emit)
        except HttpPermanentError as e:
            raise EmbeddingConfigError(explain_permanent(e.status, e.body, key_env=self.key_env,
                                                         base_url=self.base_url, model=self.model)) from None
        except EmbeddingConfigError:
            raise
        except ApiConfigError as e:
            raise EmbeddingConfigError(str(e)) from None
        with self._lock:
            if self.dim is None:
                self.dim = int(arr.shape[1])
        if arr.shape[1] != self.dim:
            raise dim_mismatch(self.dim, int(arr.shape[1]), self.model_id)
        return arr

    # ---- public
    def embed_batch(self, texts: list[str]) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return np.empty((0, self.dim or 0), dtype=np.float32)
        try:
            return self._send(texts)
        except TooLargeError as e:
            if len(texts) > 1:
                mid = len(texts) // 2
                self._emit("split", {"size": len(texts), "error": str(e)})
                return np.vstack([self.embed_batch(texts[:mid]), self.embed_batch(texts[mid:])])
            return self._embed_shortened(texts[0], e)

    def _embed_shortened(self, text: str, err: Exception) -> np.ndarray:
        """Cut one too-large text in half until the server accepts it (not below min_text_chars)."""
        cur, counted = text, False
        while True:
            if len(cur) <= self.min_text_chars:
                raise EmbeddingConfigError(
                    f"\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK} server \N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER BO BAIMAI} \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER O ANG} {len(cur)} \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SO RUSI}\N{THAI CHARACTER RO RUA} (min_text_chars="
                    f"{self.min_text_chars}) / a text is still too large at {len(cur)} characters "
                    f"(min_text_chars={self.min_text_chars}): lower embedding.api.min_text_chars or "
                    f"embedding.max_chars_per_doc, or raise the server's input limit. Server said: {err}")
            cur = cur[:max(self.min_text_chars, len(cur) // 2)]
            if not counted:
                with self._lock:
                    self.n_truncated += 1
                counted = True
            self._emit("truncated", {"chars": len(cur), "original_chars": len(text)})
            try:
                return self._send([cur])
            except TooLargeError as e:
                err = e

    def check(self) -> dict:
        """One small request with at most 2 quick retries: model, dim, latency — verify key/URL first."""
        policy = RetryPolicy(self.policy.initial, max(self.policy.initial, min(self.policy.cap, 10.0)), 2,
                             sleep=self._sleep, rand=self._rand)
        t0 = time.perf_counter()
        arr = self._send([CHECK_TEXT], policy)
        return {"model": self.model, "store_id": self.model_id, "base_url": self.base_url,
                "dim": int(arr.shape[1]), "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "api_key_env": self.key_env, "api_key_set": self.has_key}
