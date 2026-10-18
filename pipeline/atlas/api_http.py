"""Shared HTTP + retry core for OpenAI-compatible APIs (embeddings now, LLM chat in P1).

Knows nothing about embeddings:
  urllib_transport  POST with stdlib urllib; HTTP errors come back as (status, headers, body)
  classify_http     transient | too_large | permanent
  post_json         one request -> parsed JSON, or a typed exception (TransientError / TooLargeError /
                    HttpPermanentError)
  RetryPolicy       capped exponential backoff with full jitter, honours Retry-After, cancellable
  call_with_retry   retries transient failures (unlimited unless max_retries is set) and nothing else
  RateLimiter       thread-safe token bucket for requests_per_minute

The API key only ever travels in request headers; no message built here includes headers.
"""
from __future__ import annotations

import http.client
import json
import math
import random
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal, TypeVar
from urllib.parse import urlparse

Transport = Callable[[str, dict, bytes, float], tuple[int, dict, bytes]]
EventHandler = Callable[[str, dict], None]
T = TypeVar("T")

TRANSIENT_STATUSES = frozenset({408, 409, 425, 429})
# 400/422 bodies that mean "the request is too big" (OpenAI, vLLM, TEI, Infinity, gateways)
TOO_LARGE_RE = re.compile(r"too long|too large|maximum context|max.*token|token limit|batch size|payload"
                          r"|less than \d+ tokens", re.IGNORECASE)
# 429 bodies that mean "out of money/credits" (waiting does not help) — unless they talk about a rate window
OUT_OF_QUOTA_RE = re.compile(r"insufficient_quota|billing|payment|credits?\b|quota exceeded|exceeded your (current )?quota"
                             r"|quota (has been )?exhausted|out of quota", re.IGNORECASE)
RATE_WINDOW_RE = re.compile(r"per (second|minute|hour|day)|rate.?limit|requests per|tokens per|\brpm\b|\btpm\b",
                            re.IGNORECASE)


class ApiConfigError(RuntimeError):
    """Permanent failure (key, URL, model, request shape, quota): retrying cannot help — fix it and rerun."""


class HttpPermanentError(ApiConfigError):
    """A non-retryable HTTP status; callers turn it into an explained error (see explain_permanent)."""

    def __init__(self, status: int, body: str, headers: dict | None = None):
        self.status, self.body = status, body
        self.location = header(headers or {}, "Location")
        super().__init__(f"HTTP {status}: {short(body)}")


class TransientError(Exception):
    """Worth retrying: 408/409/425/429/5xx, or a malformed response."""

    def __init__(self, message: str, *, status: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.status, self.retry_after = status, retry_after


class MalformedResponse(TransientError):
    """A 2xx answer that is not a usable result (bad JSON, wrong count, NaN, ...). Retried, but the same
    problem (`kind`) again and again is not transient — callers split the batch or give up (see embed_api)."""

    def __init__(self, message: str, *, kind: str = "malformed", status: int | None = None):
        super().__init__(message, status=status)
        self.kind = kind


class TooLargeError(Exception):
    """The request is too big (413, or 400/422 saying so): split the batch or shorten the text."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


class TransientGaveUp(RuntimeError):
    """max_retries was set and exhausted on transient failures."""


class Cancelled(Exception):
    """A retry or rate-limit wait was interrupted because the run is stopping."""


def short(text: str | bytes, n: int = 300) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + "…"


def out_of_quota(body: str) -> bool:
    body = body or ""
    if "insufficient_quota" in body.lower():
        return True
    return bool(OUT_OF_QUOTA_RE.search(body)) and not RATE_WINDOW_RE.search(body)


def classify_http(status: int, body: str) -> Literal["transient", "too_large", "permanent"]:
    if status == 429 and out_of_quota(body):
        return "permanent"                                   # billing/credits: waiting forever will not help
    if status in TRANSIENT_STATUSES or status >= 500:
        return "transient"
    if status == 413 or (status in (400, 422) and TOO_LARGE_RE.search(body or "")):
        return "too_large"
    return "permanent"


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """Retry-After as seconds (delta-seconds or an HTTP date); None when absent or unreadable."""
    if value is None:
        return None
    v = str(value).strip()
    try:
        secs = float(v)
    except ValueError:
        try:
            when = parsedate_to_datetime(v)
        except (TypeError, ValueError, IndexError):
            return None
        if when is None:
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        secs = (when - (now or datetime.now(UTC))).total_seconds()
    return max(0.0, secs) if math.isfinite(secs) else None


def header(headers: dict, name: str) -> str | None:
    name = name.lower()
    return next((v for k, v in (headers or {}).items() if k.lower() == name), None)


def explain_permanent(status: int, body: str, *, key_env: str, base_url: str, model: str,
                      location: str | None = None) -> str:
    """Bilingual message with the fix for a non-retryable HTTP status."""
    said = short(body) or "(empty body)"
    if 300 <= status < 400:
        return (f"HTTP {status}: base_url \N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER KO KAI} redirect \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK} {location or '?'} — \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NGO NGU} base_url \N{THAI CHARACTER SARA E}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER CHO CHAN}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER NGO NGU} / "
                f"base_url redirects to {location or '(no Location header)'} — set base_url to the final URL "
                f"(redirects are not followed, so the API key is never sent elsewhere)")
    if status in (401, 403):
        return (f"HTTP {status}: server \N{THAI CHARACTER PO PLA}\N{THAI CHARACTER TO PATAK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THONG} API key — \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER CHO CHAN} env var {key_env} "
                f"(PowerShell: $env:{key_env}=\"...\" | bash: export {key_env}=...) / "
                f"the server rejected the API key: check the environment variable {key_env}. Server said: {said}")
    if status == 404:
        return (f"HTTP 404: \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER PHO PHAN}\N{THAI CHARACTER BO BAIMAI} endpoint \N{THAI CHARACTER HO HIP}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER SARA O}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER LO LING} — \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER CHO CHAN} base_url ({base_url}) \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA A} model ({model}) \N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER NO NU} config / "
                f"endpoint or model not found: check base_url ({base_url}) and model ({model}). Server said: {said}")
    if status == 402 or (status == 429 and out_of_quota(body)):
        return (f"HTTP {status}: \N{THAI CHARACTER SARA E}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER TO TAO}/\N{THAI CHARACTER SARA O}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER YO YING}\N{THAI CHARACTER CHO CHANG}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER DO DEK} — \N{THAI CHARACTER SARA E}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA O}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER PHO PHUNG}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA} / "
                f"the account is out of quota/credits (billing): top up or raise the limit with your provider, "
                f"then run the same command again (nothing paid for is lost). Server said: {said}")
    return (f"HTTP {status}: server \N{THAI CHARACTER PO PLA}\N{THAI CHARACTER TO PATAK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THONG}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER O ANG} (\N{THAI CHARACTER LO LING}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER CHO CHANG}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER YO YAK}) — \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI THO} config \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK} / "
            f"the server rejected the request permanently; fix the config and rerun. Server said: {said}")


def validate_base_url(url: str) -> None:
    """ApiConfigError unless `url` is http(s)://host[:port]/... with a valid port."""
    try:
        parts = urlparse(url)
        port = parts.port                                    # raises ValueError for a bad/out-of-range port
    except ValueError as e:
        raise ApiConfigError(f"base_url \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU} / invalid base_url {url!r}: {e}") from None
    if parts.scheme not in ("http", "https"):
        raise ApiConfigError(f"base_url \N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER SARA UE}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER YO YAK} http:// \N{THAI CHARACTER HO HIP}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER O ANG} https:// / base_url must start with "
                             f"http:// or https:// (got {url!r})")
    if not parts.hostname:
        raise ApiConfigError(f"base_url \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER CHO CHANG}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG} host / base_url has no host: {url!r}")
    if port == 0:
        raise ApiConfigError(f"base_url has port 0: {url!r}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """POSTs are never redirected (the 3xx comes back as a status): a key must not follow a redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def urllib_transport(url: str, headers: dict, body: bytes, timeout: float) -> tuple[int, dict, bytes]:
    """POST `body`; an HTTP error status (and a 3xx) is returned like a success, network failures raise."""
    validate_base_url(url)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as e:
        try:
            data = e.read()
        except (OSError, http.client.HTTPException):
            data = b""
        return e.code, dict(e.headers.items()) if e.headers else {}, data
    except (http.client.InvalidURL, ValueError, OverflowError) as e:
        raise ApiConfigError(f"base_url \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU} / invalid base_url {url!r}: {e}") from None


def post_json(transport: Transport, url: str, payload: Any, *, headers: dict, timeout: float) -> Any:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    status, resp_headers, raw = transport(url, {"Content-Type": "application/json", **headers}, body, timeout)
    if 200 <= status < 300:
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise MalformedResponse(f"HTTP {status}: response is not JSON ({short(raw, 120)})", kind="json",
                                    status=status) from None
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    kind = classify_http(status, text)
    if kind == "transient":
        raise TransientError(f"HTTP {status}: {short(text, 160)}", status=status,
                             retry_after=parse_retry_after(header(resp_headers, "Retry-After")))
    if kind == "too_large":
        raise TooLargeError(f"HTTP {status}: {short(text, 160)}", status=status)
    raise HttpPermanentError(status, text, resp_headers)


class RetryPolicy:
    """Full-jitter exponential backoff: delay = rand() * min(cap, initial * 2**attempt).

    A server-sent Retry-After wins (capped at `cap`). `max_retries=None` never gives up.
    The default sleep is an Event wait, so cancel() interrupts a long backoff immediately.
    """

    def __init__(self, initial: float, cap: float, max_retries: int | None = None,
                 sleep: Callable[[float], Any] | None = None, rand: Callable[[], float] = random.random):
        if not 0 < float(initial) <= float(cap):
            raise ValueError("need 0 < backoff_initial <= backoff_max")
        self.initial, self.cap, self.max_retries = float(initial), float(cap), max_retries
        self._cancel = threading.Event()
        self._sleep = sleep or self._cancel.wait
        self.rand = rand

    def delay(self, attempt: int, retry_after: float | None = None) -> float:
        jitter = self.rand() * min(self.cap, self.initial * 2 ** min(attempt, 60))
        if retry_after is not None:                          # honour Retry-After, but 0 / a past date must
            return min(self.cap, max(float(retry_after), jitter))   # not turn into a zero-delay hot loop
        return jitter

    def sleep_for(self, seconds: float) -> None:
        if self._cancel.is_set():
            raise Cancelled()
        self._sleep(seconds)
        if self._cancel.is_set():
            raise Cancelled()

    def wait(self, attempt: int, retry_after: float | None = None) -> float:
        seconds = self.delay(attempt, retry_after)
        self.sleep_for(seconds)
        return seconds

    def exhausted(self, attempt: int) -> bool:
        return self.max_retries is not None and attempt >= self.max_retries

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancel_event(self) -> threading.Event:
        """Set when the run is stopping — share it with a RateLimiter so its wait stops too."""
        return self._cancel

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()


def _cert_error(exc: BaseException) -> bool:
    return isinstance(exc, ssl.SSLCertVerificationError) or isinstance(getattr(exc, "reason", None),
                                                                      ssl.SSLCertVerificationError)


def call_with_retry(send: Callable[[], T], policy: RetryPolicy, on_event: EventHandler | None = None) -> T:
    """Call `send()` until it returns. Transient failures (TransientError, network errors) are retried
    with `policy`; everything else (ApiConfigError, TooLargeError, bugs) propagates on the first try."""
    attempt = 0
    while True:
        try:
            return send()
        except TransientError as e:
            error, status, retry_after = str(e), e.status, e.retry_after
        except (OSError, http.client.HTTPException) as e:   # URLError, timeouts, resets, incomplete reads
            if _cert_error(e):
                raise ApiConfigError(f"TLS certificate verification failed — check base_url / the server "
                                     f"certificate ({e})") from e
            error, status, retry_after = f"{type(e).__name__}: {short(str(e), 160)}", None, None
        if policy.exhausted(attempt):
            raise TransientGaveUp(f"gave up after {attempt} retries (max_retries): {error}")
        delay = policy.delay(attempt, retry_after)
        attempt += 1
        if on_event:
            on_event("retry", {"attempt": attempt, "delay": delay, "status": status, "error": error})
        policy.sleep_for(delay)


class RateLimiter:
    """Thread-safe token bucket: at most `per_minute` acquisitions per minute (burst `burst`).
    The wait is an Event wait: setting `cancel` (the run is stopping) makes a waiting acquire() raise Cancelled."""

    def __init__(self, per_minute: float, *, burst: int = 1, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], Any] | None = None, cancel: threading.Event | None = None):
        if per_minute <= 0:
            raise ValueError("requests_per_minute must be > 0")
        self.interval = 60.0 / float(per_minute)
        self.capacity = float(max(1, burst))
        self.tokens = self.capacity
        self.cancel = cancel or threading.Event()
        self.clock, self.sleep = clock, sleep or self.cancel.wait
        self.last = clock()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            if self.cancel.is_set():
                raise Cancelled()
            with self._lock:
                now = self.clock()
                self.tokens = min(self.capacity, self.tokens + (now - self.last) / self.interval)
                self.last = now
                if self.tokens >= 1.0 - 1e-9:
                    self.tokens = max(0.0, self.tokens - 1.0)
                    return
                wait = (1.0 - self.tokens) * self.interval
            self.sleep(wait)
