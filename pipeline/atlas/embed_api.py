"""Embeddings over any OpenAI-compatible API (BGE-M3 on TEI/vLLM/Infinity/Ollama, DeepInfra, OpenAI, ...).

Only the embedding-specific parts live here — request body, response validation, batch split and
single-text truncation on "too large", `ApiEmbedder` and `check()`. HTTP, classification, backoff and
the retry loop come from atlas.api_http (shared with the P1 LLM client).

Failure policy (embed_batch):
  transient (408/409/425/429/5xx, network, malformed response)  -> retry (forever unless max_retries)
  the same malformed answer MALFORMED_REPEAT times in a row     -> split the batch; a single text -> config error
  too large (413, or 400/422 saying so)                         -> split the batch in half; a single text
                                                                   is cut in half down to min_text_chars
  permanent (3xx redirect, 401/402/403/404, other 4xx, 429 out of quota) -> EmbeddingConfigError at once
A split batch that is stopped part-way raises PartialBatch carrying the parts already paid for.
"""
from __future__ import annotations

import base64
import binascii
import ipaddress
import os
import random
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import numpy as np

from atlas.api_http import (
    ApiConfigError,
    EventHandler,
    HttpPermanentError,
    MalformedResponse,
    RateLimiter,
    RetryPolicy,
    TooLargeError,
    Transport,
    call_with_retry,
    explain_permanent,
    post_json,
    urllib_transport,
    validate_base_url,
)

CHECK_TEXT = "TCI Research Atlas embedding check — \N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER CHO CHANG}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}"
MALFORMED_REPEAT = 3                    # the same malformed answer this often for one batch = not transient
_WARNED_PLAIN_HTTP: set[str] = set()


class EmbeddingConfigError(ApiConfigError):
    """Permanent embedding failure: fix the config (key, base_url, model, store_id) and rerun."""


class PartialBatch(Exception):
    """A split batch stopped part-way. `parts` = [(start, vectors)] already paid for (start = offset in the
    batch passed to embed_batch); `cause` = the exception that stopped the rest (often api_http.Cancelled)."""

    def __init__(self, parts: list[tuple[int, np.ndarray]], cause: BaseException):
        super().__init__(f"{sum(len(a) for _, a in parts)} of the batch's texts done before "
                         f"{type(cause).__name__}: {cause}")
        self.parts, self.cause = parts, cause


class _PersistentMalformed(Exception):
    """The server gave the same malformed answer MALFORMED_REPEAT times for one batch."""


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
    """(n, dim) float32 aligned to the input order; anything malformed raises MalformedResponse (re-requested)."""
    data = obj.get("data") if isinstance(obj, dict) else None
    if not isinstance(data, list):
        raise MalformedResponse("malformed response: no `data` list", kind="no-data")
    if len(data) != n:
        raise MalformedResponse(f"malformed response: {len(data)} vectors for a batch of {n}", kind="count")
    try:
        items = sorted(data, key=lambda d: d["index"])
    except (KeyError, TypeError):
        raise MalformedResponse("malformed response: an item has no usable `index`", kind="index") from None
    if [d["index"] for d in items] != list(range(n)):
        raise MalformedResponse(f"malformed response: indices {[d['index'] for d in items][:10]} for a batch "
                                f"of {n}", kind="index")
    vecs = []
    for d in items:
        emb = d.get("embedding")
        try:
            v = (np.frombuffer(base64.b64decode(emb), dtype="<f4") if isinstance(emb, str)
                 else np.asarray(emb, dtype=np.float32))
        except (TypeError, ValueError, binascii.Error):
            raise MalformedResponse("malformed response: an embedding is not a list of numbers",
                                    kind="type") from None
        vecs.append(v)
    if any(v.ndim != 1 or v.size == 0 or v.size != vecs[0].size for v in vecs):
        raise MalformedResponse("malformed response: vectors of different lengths", kind="ragged")
    arr = np.vstack(vecs).astype(np.float32)
    if not np.isfinite(arr).all():
        raise MalformedResponse("malformed response: non-finite values (NaN/Inf) in a vector", kind="nonfinite")
    return arr


def dim_mismatch(store_dim: int, got: int, store_id: str) -> EmbeddingConfigError:
    return EmbeddingConfigError(
        f"store \N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER SARA I} {store_dim} \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK} server \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER BO BAIMAI} {got} — \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NGO NGU} store_id \N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK} / the existing store "
        f"({store_id}) holds {store_dim}-dim vectors but the server returned {got}: a different model or "
        f"settings — set embedding.api.store_id to a new name (or fix model/dimensions)")


def _loopback(host: str | None) -> bool:
    if not host or host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


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
        try:
            validate_base_url(self.url)
        except ApiConfigError as e:
            raise EmbeddingConfigError(str(e)) from None
        self.model, self.dimensions = acfg["model"], acfg.get("dimensions")
        self.key_env = acfg["api_key_env"]
        self.__key = os.environ.get(self.key_env, "").strip()
        host = urlparse(self.url).hostname
        if self.__key and urlparse(self.url).scheme == "http" and not _loopback(host) \
                and host not in _WARNED_PLAIN_HTTP:
            _WARNED_PLAIN_HTTP.add(host)
            print(f"[embed] WARNING: the API key (${self.key_env}) is sent unencrypted over http:// to {host} — "
                  f"use https:// unless this is a trusted private network")
        self.model_id = api_store_id(acfg)
        self.transport = transport or urllib_transport
        self.timeout = float(acfg["request_timeout"])
        self.min_text_chars = int(acfg["min_text_chars"])
        self._sleep, self._rand = sleep, rand
        self.policy = RetryPolicy(acfg["backoff_initial"], acfg["backoff_max"], acfg.get("max_retries"),
                                  sleep=sleep, rand=rand)
        rpm = acfg.get("requests_per_minute")
        self.limiter = RateLimiter(rpm, cancel=self.policy.cancel_event) if rpm else None
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
        """Stop retrying: a worker in (or entering) a backoff or rate-limit wait raises api_http.Cancelled."""
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
        seen = {"kind": None, "n": 0}

        def attempt() -> np.ndarray:
            try:
                return self._request(texts)
            except MalformedResponse as e:
                seen["n"] = seen["n"] + 1 if e.kind == seen["kind"] else 1
                seen["kind"] = e.kind
                if seen["n"] >= MALFORMED_REPEAT:
                    raise _PersistentMalformed(str(e)) from None
                raise

        try:
            arr = call_with_retry(attempt, policy or self.policy, self._emit)
        except HttpPermanentError as e:
            raise EmbeddingConfigError(explain_permanent(e.status, e.body, key_env=self.key_env,
                                                         base_url=self.base_url, model=self.model,
                                                         location=e.location)) from None
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

    def _malformed_error(self, err: Exception) -> EmbeddingConfigError:
        return EmbeddingConfigError(
            f"server \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER PHO PHUNG}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER SO SO}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AM} {MALFORMED_REPEAT} \N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER WO WAEN} / the server returned the same "
            f"malformed answer {MALFORMED_REPEAT} times for a single text ({err}) — check the server and model "
            f"(base_url {self.base_url}, model {self.model})")

    # ---- public
    def embed_batch(self, texts: list[str]) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return np.empty((0, self.dim or 0), dtype=np.float32)
        try:
            return self._send(texts)
        except (TooLargeError, _PersistentMalformed) as e:
            if len(texts) == 1:
                if isinstance(e, _PersistentMalformed):
                    raise self._malformed_error(e) from None
                return self._embed_shortened(texts[0], e)
            mid = len(texts) // 2
            self._emit("split", {"size": len(texts), "error": str(e)})
            parts: list[tuple[int, np.ndarray]] = []
            for start, chunk in ((0, texts[:mid]), (mid, texts[mid:])):
                try:
                    parts.append((start, self.embed_batch(chunk)))
                except PartialBatch as pb:
                    raise PartialBatch(parts + [(start + s, a) for s, a in pb.parts], pb.cause) from None
                except Exception as exc:  # noqa: BLE001 — hand back what is already paid for
                    if parts:
                        raise PartialBatch(parts, exc) from None
                    raise
            return np.vstack([a for _, a in parts])

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
            try:
                arr = self._send([cur])
            except TooLargeError as e:
                err = e
                continue
            except _PersistentMalformed as e:
                raise self._malformed_error(e) from None
            self._emit("truncated", {"text": text, "chars": len(cur), "original_chars": len(text)})
            return arr

    def check(self) -> dict:
        """One small request with at most 2 quick retries: model, dim, latency — verify key/URL first."""
        policy = RetryPolicy(self.policy.initial, max(self.policy.initial, min(self.policy.cap, 10.0)), 2,
                             sleep=self._sleep, rand=self._rand)
        t0 = time.perf_counter()
        try:
            arr = self._send([CHECK_TEXT], policy)
        except _PersistentMalformed as e:
            raise self._malformed_error(e) from None
        return {"model": self.model, "store_id": self.model_id, "base_url": self.base_url,
                "dim": int(arr.shape[1]), "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "api_key_env": self.key_env, "api_key_set": self.has_key}
