"""Shared HTTP + retry core (atlas.api_http) — no network except a local throwaway server."""
from __future__ import annotations

import http.client
import http.server
import threading
import time
import urllib.error
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest

from atlas.api_http import (
    ApiConfigError,
    Cancelled,
    HttpPermanentError,
    RateLimiter,
    RetryPolicy,
    TooLargeError,
    TransientError,
    TransientGaveUp,
    call_with_retry,
    classify_http,
    explain_permanent,
    parse_retry_after,
    post_json,
    urllib_transport,
    validate_base_url,
)


# ---------- classify_http
@pytest.mark.parametrize("status", [408, 409, 425, 429, 500, 502, 503, 504, 599])
def test_transient_statuses(status):
    assert classify_http(status, "") == "transient"


@pytest.mark.parametrize("status,body", [
    (413, ""),
    (400, "This model's maximum context length is 8192 tokens"),
    (422, "Input is TOO LONG for this model"),
    (400, "request too large"),
    (400, "max_tokens per input exceeded"),
    (422, "token limit reached"),
    (422, "batch size 64 > maximum allowed batch size 32"),
    (400, "payload exceeds limit"),
    (422, "Input validation error: `inputs` must have less than 512 tokens. Given: 600"),
])
def test_too_large_statuses(status, body):
    assert classify_http(status, body) == "too_large"


@pytest.mark.parametrize("status,body", [(400, "invalid input type"), (401, ""), (403, "forbidden"),
                                         (404, "model not found"), (405, ""), (422, "unknown field"),
                                         (418, "teapot"), (301, "moved")])
def test_permanent_statuses(status, body):
    assert classify_http(status, body) == "permanent"


# ---------- Retry-After
def test_parse_retry_after_seconds_and_dates():
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)
    assert parse_retry_after("7", now=now) == 7.0
    assert parse_retry_after(" 1.5 ", now=now) == 1.5
    assert parse_retry_after(format_datetime(now + timedelta(seconds=30), usegmt=True), now=now) == 30.0
    assert parse_retry_after(format_datetime(now - timedelta(seconds=30), usegmt=True), now=now) == 0.0
    assert parse_retry_after("-3", now=now) == 0.0
    assert parse_retry_after("soon", now=now) is None
    assert parse_retry_after(None, now=now) is None


# ---------- RetryPolicy
def test_retry_policy_full_jitter_and_cap():
    slept = []
    p = RetryPolicy(initial=2.0, cap=300.0, max_retries=None, sleep=slept.append, rand=lambda: 0.5)
    assert p.wait(0, None) == 1.0                      # 0.5 * 2
    assert p.wait(3, None) == 8.0                      # 0.5 * 2 * 2**3
    assert p.wait(20, None) == 150.0                   # 0.5 * cap
    assert slept == [1.0, 8.0, 150.0]
    top = RetryPolicy(initial=2.0, cap=300.0, max_retries=None, sleep=lambda s: None, rand=lambda: 1.0)
    assert max(top.wait(a, None) for a in range(40)) == 300.0
    low = RetryPolicy(initial=2.0, cap=300.0, max_retries=None, sleep=lambda s: None, rand=lambda: 0.0)
    assert low.wait(5, None) == 0.0                    # full jitter: anywhere in [0, ceiling]


def test_retry_policy_respects_retry_after_capped():
    slept = []
    p = RetryPolicy(initial=2.0, cap=60.0, max_retries=None, sleep=slept.append, rand=lambda: 0.5)
    assert p.wait(0, 7.0) == 7.0
    assert p.wait(0, 1000.0) == 60.0
    assert slept == [7.0, 60.0]


def test_retry_policy_exhausted():
    assert not RetryPolicy(1, 2, None).exhausted(10_000)
    p = RetryPolicy(1, 2, 2)
    assert not p.exhausted(0) and not p.exhausted(1) and p.exhausted(2)


def test_retry_policy_cancel_interrupts_the_wait():
    p = RetryPolicy(initial=100.0, cap=100.0, max_retries=None, rand=lambda: 1.0)   # real (interruptible) sleep
    threading.Timer(0.05, p.cancel).start()
    with pytest.raises(Cancelled):
        p.wait(0, None)                                  # would sleep 100 s without the cancel


# ---------- call_with_retry
def _flaky(failures: list[BaseException], result="ok"):
    calls = {"n": 0}

    def send():
        calls["n"] += 1
        if failures:
            raise failures.pop(0)
        return result
    return send, calls


def test_call_with_retry_retries_transient_then_succeeds():
    slept, events = [], []
    send, calls = _flaky([TransientError("HTTP 503", status=503)] * 3)
    pol = RetryPolicy(2.0, 300.0, None, sleep=slept.append, rand=lambda: 0.5)
    assert call_with_retry(send, pol, lambda k, i: events.append((k, i))) == "ok"
    assert calls["n"] == 4 and len(slept) == 3
    assert [i["attempt"] for _, i in events] == [1, 2, 3]
    assert all(k == "retry" and i["status"] == 503 and "503" in i["error"] for k, i in events)
    assert [i["delay"] for _, i in events] == slept


def test_call_with_retry_uses_retry_after():
    slept = []
    send, _ = _flaky([TransientError("HTTP 429", status=429, retry_after=7.0)])
    call_with_retry(send, RetryPolicy(2.0, 300.0, None, sleep=slept.append, rand=lambda: 0.5))
    assert slept == [7.0]


@pytest.mark.parametrize("exc", [
    urllib.error.URLError(ConnectionRefusedError(10061, "refused")),
    ConnectionResetError("reset"),
    TimeoutError("timed out"),
    http.client.RemoteDisconnected("closed"),
    http.client.IncompleteRead(b"partial"),
])
def test_network_errors_are_transient(exc):
    send, calls = _flaky([exc])
    assert call_with_retry(send, RetryPolicy(1, 1, None, sleep=lambda s: None)) == "ok"
    assert calls["n"] == 2


def test_unlimited_retries_survive_twenty_failures():
    send, calls = _flaky([TransientError("HTTP 502", status=502) for _ in range(20)])
    assert call_with_retry(send, RetryPolicy(2.0, 300.0, None, sleep=lambda s: None)) == "ok"
    assert calls["n"] == 21


def test_limited_retries_give_up():
    send, calls = _flaky([TransientError("HTTP 502", status=502) for _ in range(20)])
    with pytest.raises(TransientGaveUp, match="502"):
        call_with_retry(send, RetryPolicy(2.0, 300.0, 2, sleep=lambda s: None))
    assert calls["n"] == 3                              # first try + 2 retries


@pytest.mark.parametrize("exc", [ApiConfigError("bad key"), TooLargeError("413", status=413), ValueError("bug")])
def test_non_transient_errors_are_not_retried(exc):
    slept = []
    send, calls = _flaky([exc])
    with pytest.raises(type(exc)):
        call_with_retry(send, RetryPolicy(1, 1, None, sleep=slept.append))
    assert calls["n"] == 1 and slept == []


# ---------- post_json (fake transport)
def _transport(status, body=b"", headers=None, seen=None):
    def t(url, hdrs, data, timeout):
        if seen is not None:
            seen.append((url, hdrs, data, timeout))
        return status, headers or {}, body
    return t


def test_post_json_success_and_request_shape():
    seen = []
    out = post_json(_transport(200, b'{"a": 1}', seen=seen), "http://x/v1/embeddings", {"q": 1},
                    headers={"Authorization": "Bearer k"}, timeout=12.0)
    assert out == {"a": 1}
    url, hdrs, data, timeout = seen[0]
    assert url == "http://x/v1/embeddings" and timeout == 12.0 and data == b'{"q": 1}'
    assert hdrs["Content-Type"] == "application/json" and hdrs["Authorization"] == "Bearer k"


def test_post_json_classifies_failures():
    with pytest.raises(TransientError) as e:
        post_json(_transport(503, b"busy", {"retry-after": "7"}), "u", {}, headers={}, timeout=1)
    assert e.value.status == 503 and e.value.retry_after == 7.0
    with pytest.raises(TransientError, match="JSON"):
        post_json(_transport(200, b"<html>"), "u", {}, headers={}, timeout=1)
    with pytest.raises(TooLargeError):
        post_json(_transport(413, b"too big"), "u", {}, headers={}, timeout=1)
    with pytest.raises(HttpPermanentError) as p:
        post_json(_transport(401, b'{"error": "invalid api key"}'), "u", {}, headers={}, timeout=1)
    assert p.value.status == 401 and "invalid api key" in p.value.body
    assert isinstance(p.value, ApiConfigError)


def test_explain_permanent_names_the_fix():
    m401 = explain_permanent(401, "nope", key_env="ATLAS_EMBED_API_KEY", base_url="http://h/v1", model="bge-m3")
    assert "ATLAS_EMBED_API_KEY" in m401 and "401" in m401
    m404 = explain_permanent(404, "", key_env="K", base_url="http://h/v1", model="bge-m3")
    assert "http://h/v1" in m404 and "bge-m3" in m404 and "base_url" in m404
    m400 = explain_permanent(400, "field `foo` is not allowed", key_env="K", base_url="u", model="m")
    assert "field `foo` is not allowed" in m400


def test_secret_never_appears_in_errors():
    with pytest.raises(HttpPermanentError) as p:
        post_json(_transport(403, b"denied"), "u", {}, headers={"Authorization": "Bearer sk-SECRET"}, timeout=1)
    assert "sk-SECRET" not in str(p.value)


# ---------- RateLimiter (fake clock)
class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_rate_limiter_spaces_requests():
    c = _Clock()
    rl = RateLimiter(60, clock=c, sleep=c.sleep)        # 1 request / second, burst 1
    for _ in range(4):
        rl.acquire()
    assert c.t == pytest.approx(3.0)


def test_rate_limiter_is_thread_safe():
    rl = RateLimiter(60_000)                           # 1,000/s: 50 acquires take ~50 ms
    done = []

    def worker():
        for _ in range(10):
            rl.acquire()
        done.append(1)
    ts = [threading.Thread(target=worker) for _ in range(5)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(5)
    assert len(done) == 5


# ---------- default transport: HTTP errors come back as statuses, not exceptions
class _Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(503)
        self.send_header("Retry-After", "5")
        self.send_header("Content-Length", "4")
        self.end_headers()
        self.wfile.write(b"busy")

    def log_message(self, *a):
        pass


def test_urllib_transport_returns_http_errors():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        status, headers, body = urllib_transport(f"http://127.0.0.1:{srv.server_address[1]}/x", {}, b"{}", 5.0)
    finally:
        srv.shutdown()
    assert status == 503 and body == b"busy"
    assert {k.lower(): v for k, v in headers.items()}["retry-after"] == "5"


# ---------- fix round 1
@pytest.mark.parametrize("body", ['{"error": {"code": "insufficient_quota", "message": "You exceeded your current quota"}}',
                                  "billing hard limit has been reached", "Payment required: add credits",
                                  "monthly quota exceeded for this key"])
def test_429_out_of_money_is_permanent(body):
    assert classify_http(429, body) == "permanent"
    msg = explain_permanent(429, body, key_env="K", base_url="u", model="m")
    assert "quota" in msg.lower() or "billing" in msg.lower()


@pytest.mark.parametrize("body", ["Rate limit reached for requests", "Quota exceeded for metric: requests per minute",
                                  "too many requests", ""])
def test_429_rate_limits_stay_transient(body):
    assert classify_http(429, body) == "transient"


def test_402_payment_required_is_permanent_and_explained():
    assert classify_http(402, "") == "permanent"
    assert "billing" in explain_permanent(402, "", key_env="K", base_url="u", model="m").lower()


def test_retry_after_zero_or_past_is_floored_at_the_backoff():
    p = RetryPolicy(2.0, 300.0, None, sleep=lambda s: None, rand=lambda: 0.5)
    assert p.delay(3, 0.0) == 8.0                       # not a zero-delay hot loop
    assert p.delay(3, 20.0) == 20.0                     # a longer Retry-After still wins
    slept = []
    send, _ = _flaky([TransientError("HTTP 429", status=429, retry_after=0.0)] * 2)
    call_with_retry(send, RetryPolicy(2.0, 300.0, None, sleep=slept.append, rand=lambda: 0.5))
    assert slept == [1.0, 2.0]


def test_rate_limiter_wait_is_cancellable():
    cancel = threading.Event()
    rl = RateLimiter(1, cancel=cancel)                  # 1 request per minute
    rl.acquire()
    threading.Timer(0.1, cancel.set).start()
    t = time.monotonic()
    with pytest.raises(Cancelled):
        rl.acquire()                                    # would wait ~60 s
    assert time.monotonic() - t < 5


@pytest.mark.parametrize("url", ["http://127.0.0.1:notaport/v1", "http://127.0.0.1:99999/v1", "http:///v1",
                                 "localhost:8080/v1", "ftp://host/v1"])
def test_bad_base_urls_are_config_errors(url):
    with pytest.raises(ApiConfigError):
        validate_base_url(url)
    with pytest.raises(ApiConfigError):
        urllib_transport(url + "/embeddings", {}, b"{}", 2.0)


class _Redirect(http.server.BaseHTTPRequestHandler):
    hits: list = []

    def do_POST(self):  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        _Redirect.hits.append((self.path, self.headers.get("Authorization")))
        if self.path.startswith("/old"):
            self.send_response(307)
            self.send_header("Location", f"http://127.0.0.1:{self.server.server_address[1]}/new/embeddings")
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

    def log_message(self, *a):
        pass


def test_redirects_are_not_followed_and_explained():
    _Redirect.hits = []
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Redirect)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        with pytest.raises(HttpPermanentError) as e:
            post_json(urllib_transport, f"{base}/old/embeddings", {}, headers={"Authorization": "Bearer k"},
                      timeout=5)
    finally:
        srv.shutdown()
    assert e.value.status == 307 and [p for p, _ in _Redirect.hits] == ["/old/embeddings"]   # never followed
    msg = explain_permanent(e.value.status, e.value.body, key_env="K", base_url=f"{base}/old", model="m",
                            location=e.value.location)
    assert f"{base}/new/embeddings" in msg and "base_url" in msg
