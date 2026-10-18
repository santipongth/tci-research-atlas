"""Embedding requests over an OpenAI-compatible API (atlas.embed_api) — fake transport, injected sleep."""
from __future__ import annotations

import hashlib
import json
import os
import threading

import numpy as np
import pytest

from atlas.api_http import Cancelled, TransientGaveUp
from atlas.config import load_config
from atlas.embed_api import ApiEmbedder, EmbeddingConfigError, api_store_id, parse_embeddings, request_body

DIM = 4


def vec(text: str, dim: int = DIM) -> list[float]:
    d = hashlib.sha256(text.encode("utf-8")).digest()
    return [b / 255.0 + 0.1 for b in d[:dim]]


class FakeAPI:
    """Scripted OpenAI-compatible POST /embeddings. Each call pops the next step from `script`
    (an HTTP tuple, or a keyword: "short", "nan", "noindex", "ragged"); default is a correct answer."""

    def __init__(self, script=(), *, shuffle=False, max_inputs=None, max_chars=None, dim=DIM):
        self.script, self.shuffle, self.dim = list(script), shuffle, dim
        self.max_inputs, self.max_chars = max_inputs, max_chars
        self.calls: list[dict] = []
        self.headers: list[dict] = []
        self.urls: list[str] = []
        self._lock = threading.Lock()

    def __call__(self, url, headers, body, timeout):
        req = json.loads(body)
        with self._lock:
            self.calls.append(req)
            self.headers.append(headers)
            self.urls.append(url)
            step = self.script.pop(0) if self.script else "ok"
        if isinstance(step, tuple):
            return step
        texts = req["input"]
        if self.max_inputs and len(texts) > self.max_inputs:
            return 413, {}, b"Payload Too Large"
        if self.max_chars and any(len(t) > self.max_chars for t in texts):
            return 400, {}, b'{"error": {"message": "This model\'s maximum context length is 8192 tokens"}}'
        data = [{"object": "embedding", "index": i, "embedding": vec(t, self.dim)} for i, t in enumerate(texts)]
        if step == "short":
            data = data[:-1]
        elif step == "nan":
            data[0]["embedding"][0] = float("nan")
        elif step == "noindex":
            del data[0]["index"]
        elif step == "ragged":
            data[0]["embedding"] = data[0]["embedding"][:-1]
        if self.shuffle:
            data = data[::-1]
        return 200, {"Content-Type": "application/json"}, json.dumps({"data": data, "model": req["model"]}).encode()


def make_cfg(**api) -> dict:
    cfg = load_config(None)
    cfg["embedding"]["provider"] = "api"
    cfg["embedding"]["api"].update({"base_url": "http://emb.test/v1", "model": "BAAI/bge-m3", "dimensions": None,
                                    "api_key_env": "ATLAS_TEST_EMBED_KEY", **api})
    return cfg


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("ATLAS_TEST_EMBED_KEY", "sk-test-SECRET")


def emb_for(api: FakeAPI, slept: list | None = None, events: list | None = None, **cfg_api) -> ApiEmbedder:
    return ApiEmbedder(make_cfg(**cfg_api), transport=api,
                       sleep=(slept.append if slept is not None else (lambda s: None)),
                       on_event=(lambda k, i: events.append((k, i))) if events is not None else None)


TEXTS = [f"document {i} text" for i in range(8)]


def expected(texts):
    return np.array([vec(t) for t in texts], dtype=np.float32)


def test_request_shape_and_auth(key):
    api = FakeAPI()
    out = emb_for(api).embed_batch(["a", "b"])
    assert np.allclose(out, expected(["a", "b"]))
    assert api.urls == ["http://emb.test/v1/embeddings"]
    assert api.calls[0] == {"model": "BAAI/bge-m3", "input": ["a", "b"], "encoding_format": "float"}
    assert api.headers[0]["Authorization"] == "Bearer sk-test-SECRET"


def test_request_body_omits_dimensions_when_null():
    assert "dimensions" not in request_body(["x"], "BAAI/bge-m3", None)
    assert request_body(["x"], "text-embedding-3-large", 1024)["dimensions"] == 1024


def test_store_id_excludes_base_url():
    a = make_cfg()["embedding"]["api"]
    b = {**a, "base_url": "https://elsewhere.example/v1"}
    assert api_store_id(a) == api_store_id(b) == "api|BAAI/bge-m3|None"
    assert "emb.test" not in api_store_id(a)
    assert api_store_id({**a, "model": "bge-m3"}) != api_store_id(a)
    assert api_store_id({**a, "dimensions": 512}) != api_store_id(a)
    assert api_store_id({**a, "store_id": "bge-m3-tei"}) == "bge-m3-tei"
    assert ApiEmbedder(make_cfg(), transport=FakeAPI()).model_id == "api|BAAI/bge-m3|None"


def test_503_three_times_then_ok(key):
    slept, events = [], []
    api = FakeAPI([(503, {}, b"busy")] * 3)
    e = emb_for(api, slept, events)
    assert np.allclose(e.embed_batch(TEXTS), expected(TEXTS))
    assert e.n_retries == 3 and len(slept) == 3 and len(api.calls) == 4
    assert [k for k, _ in events] == ["retry"] * 3 and events[-1][1]["status"] == 503


def test_429_retry_after_is_respected(key):
    slept = []
    e = emb_for(FakeAPI([(429, {"Retry-After": "7"}, b"slow down")]), slept)
    e.embed_batch(["a"])
    assert slept == [7.0]


def test_retry_after_is_capped_by_backoff_max(key):
    slept = []
    emb_for(FakeAPI([(503, {"Retry-After": "1000"}, b"")]), slept, backoff_max=60.0).embed_batch(["a"])
    assert slept == [60.0]


def test_401_is_a_config_error_without_retry(key):
    slept = []
    api = FakeAPI([(401, {}, b'{"error": "invalid api key"}')])
    with pytest.raises(EmbeddingConfigError) as e:
        emb_for(api, slept).embed_batch(["a"])
    assert "ATLAS_TEST_EMBED_KEY" in str(e.value) and "sk-test-SECRET" not in str(e.value)
    assert slept == [] and len(api.calls) == 1


def test_404_names_base_url_and_model(key):
    with pytest.raises(EmbeddingConfigError) as e:
        emb_for(FakeAPI([(404, {}, b"not found")])).embed_batch(["a"])
    assert "http://emb.test/v1" in str(e.value) and "BAAI/bge-m3" in str(e.value)


def test_413_splits_the_batch_and_keeps_order(key):
    api = FakeAPI(max_inputs=2)
    e = emb_for(api)
    out = e.embed_batch(TEXTS)
    assert np.allclose(out, expected(TEXTS))
    assert max(len(c["input"]) for c in api.calls if c) == 8          # first try was the full batch
    assert e.n_truncated == 0


def test_single_text_too_large_is_truncated_once(key):
    api = FakeAPI(max_chars=1000)
    e = emb_for(api, min_text_chars=100)
    long = "x" * 1500
    out = e.embed_batch(["short", long])
    assert out.shape == (2, DIM)
    assert np.allclose(out[0], vec("short")) and np.allclose(out[1], vec("x" * 750))
    assert e.n_truncated == 1


def test_too_large_at_min_text_chars_is_a_config_error(key):
    e = emb_for(FakeAPI(max_chars=50), min_text_chars=100)
    with pytest.raises(EmbeddingConfigError, match="min_text_chars"):
        e.embed_batch(["y" * 1000])
    assert e.n_truncated == 1


def test_shuffled_index_is_realigned(key):
    assert np.allclose(emb_for(FakeAPI(shuffle=True)).embed_batch(TEXTS), expected(TEXTS))


@pytest.mark.parametrize("bad", ["short", "nan", "noindex", "ragged", (200, {}, b"<html>oops</html>")])
def test_malformed_responses_are_retried(key, bad):
    slept = []
    api = FakeAPI([bad])
    e = emb_for(api, slept)
    assert np.allclose(e.embed_batch(TEXTS[:3]), expected(TEXTS[:3]))
    assert len(api.calls) == 2 and e.n_retries == 1


def test_twenty_502s_then_ok_with_unlimited_retries(key):
    e = emb_for(FakeAPI([(502, {}, b"bad gateway")] * 20))
    assert e.embed_batch(["a"]).shape == (1, DIM) and e.n_retries == 20


def test_max_retries_gives_up(key):
    api = FakeAPI([(502, {}, b"bad gateway")] * 20)
    with pytest.raises(TransientGaveUp):
        emb_for(api, max_retries=2).embed_batch(["a"])
    assert len(api.calls) == 3


def test_missing_key_sends_no_authorization(monkeypatch):
    monkeypatch.delenv("ATLAS_TEST_EMBED_KEY", raising=False)
    api = FakeAPI()
    emb_for(api).embed_batch(["a"])                         # self-hosted servers often need no key
    assert "Authorization" not in api.headers[0]


def test_key_is_not_in_repr(key):
    assert "sk-test-SECRET" not in repr(emb_for(FakeAPI())) + str(vars(emb_for(FakeAPI())).get("cfg", ""))


def test_rate_limiter_only_when_configured(key):
    assert emb_for(FakeAPI()).limiter is None
    assert emb_for(FakeAPI(), requests_per_minute=600).limiter is not None


def test_cancel_interrupts_a_backoff(key):
    api = FakeAPI([(503, {}, b"down")] * 1000)
    e = ApiEmbedder(make_cfg(backoff_initial=60.0, backoff_max=60.0), transport=api)   # real, interruptible sleep
    threading.Timer(0.1, e.cancel).start()
    with pytest.raises(Cancelled):
        e.embed_batch(["a"])


def test_check_reports_model_dim_latency(key):
    info = emb_for(FakeAPI(dim=6)).check()
    assert info["model"] == "BAAI/bge-m3" and info["dim"] == 6 and info["latency_ms"] >= 0


def test_check_gives_up_quickly_on_a_dead_server(key):
    api = FakeAPI([(503, {}, b"down")] * 50)
    with pytest.raises(TransientGaveUp):
        emb_for(api).check()
    assert len(api.calls) <= 3


def test_parse_embeddings_accepts_base64():
    import base64

    v = np.array([0.5, -1.0, 2.0], dtype="<f4")
    out = parse_embeddings({"data": [{"index": 0, "embedding": base64.b64encode(v.tobytes()).decode()}]}, 1)
    assert np.allclose(out, [v])


@pytest.mark.live
@pytest.mark.skipif(not (os.environ.get("ATLAS_EMBED_LIVE_BASE_URL") and os.environ.get("ATLAS_EMBED_API_KEY")),
                    reason="live smoke test: set ATLAS_EMBED_LIVE_BASE_URL and ATLAS_EMBED_API_KEY "
                           "(optionally ATLAS_EMBED_LIVE_MODEL)")
def test_live_check():
    cfg = load_config(None)
    cfg["embedding"]["api"].update(base_url=os.environ["ATLAS_EMBED_LIVE_BASE_URL"],
                                   model=os.environ.get("ATLAS_EMBED_LIVE_MODEL", "BAAI/bge-m3"),
                                   dimensions=None)
    assert ApiEmbedder(cfg).check()["dim"] > 0


# ---------- fix round 1
def test_three_identical_malformed_answers_split_the_batch(key):
    api = FakeAPI(["short", "short", "short"])
    e = emb_for(api)
    assert np.allclose(e.embed_batch(TEXTS[:4]), expected(TEXTS[:4]))
    assert [len(c["input"]) for c in api.calls] == [4, 4, 4, 2, 2]


def test_different_malformed_answers_keep_retrying_the_whole_batch(key):
    api = FakeAPI(["short", "nan", "short", "nan"])
    e = emb_for(api)
    assert np.allclose(e.embed_batch(TEXTS[:4]), expected(TEXTS[:4]))
    assert [len(c["input"]) for c in api.calls] == [4] * 5


def test_single_text_with_a_persistently_malformed_answer_is_a_config_error(key):
    with pytest.raises(EmbeddingConfigError, match="non-finite"):
        emb_for(FakeAPI(["nan"] * 3)).embed_batch(["one text"])


def test_out_of_quota_is_a_config_error_without_retry(key):
    slept = []
    api = FakeAPI([(429, {}, b'{"error": {"code": "insufficient_quota"}}')])
    with pytest.raises(EmbeddingConfigError, match="(?i)quota"):
        emb_for(api, slept).embed_batch(["a"])
    assert slept == [] and len(api.calls) == 1


def test_redirect_is_a_config_error_naming_the_target(key):
    api = FakeAPI([(308, {"Location": "https://emb.test/v1/embeddings"}, b"")])
    with pytest.raises(EmbeddingConfigError, match="https://emb.test/v1/embeddings"):
        emb_for(api).embed_batch(["a"])


@pytest.mark.parametrize("url", ["http://emb.test:notaport/v1", "http://emb.test:70000/v1", "emb.test/v1"])
def test_bad_base_url_fails_at_construction(key, url):
    with pytest.raises(EmbeddingConfigError):
        ApiEmbedder(make_cfg(base_url=url), transport=FakeAPI())


def test_key_over_plain_http_to_a_remote_host_warns_once(key, capsys):
    ApiEmbedder(make_cfg(base_url="http://emb.example.org/v1"), transport=FakeAPI())
    assert "WARNING" in capsys.readouterr().out
    for url in ("http://127.0.0.1:8080/v1", "http://localhost/v1", "https://emb.example.org/v1"):
        ApiEmbedder(make_cfg(base_url=url), transport=FakeAPI())
    assert "WARNING" not in capsys.readouterr().out


def test_no_warning_without_a_key(monkeypatch, capsys):
    monkeypatch.delenv("ATLAS_TEST_EMBED_KEY", raising=False)
    ApiEmbedder(make_cfg(base_url="http://emb.example.org/v1"), transport=FakeAPI())
    assert "WARNING" not in capsys.readouterr().out


def test_cancel_during_a_split_keeps_the_paid_half(key):
    from atlas.embed_api import PartialBatch

    api = FakeAPI(["ok", "ok"] + [(503, {}, b"down")] * 1000, max_inputs=2)   # 413, left half ok, right half down
    e = ApiEmbedder(make_cfg(backoff_initial=60.0, backoff_max=60.0), transport=api)
    threading.Timer(0.3, e.cancel).start()
    with pytest.raises(PartialBatch) as err:
        e.embed_batch(TEXTS[:4])
    (start, arr), = err.value.parts
    assert start == 0 and np.allclose(arr, expected(TEXTS[:2]))
    assert isinstance(err.value.cause, Cancelled)


def test_truncated_event_names_the_text_once(key):
    events = []
    e = emb_for(FakeAPI(max_chars=1000), events=events, min_text_chars=100)
    long = "z" * 3000
    e.embed_batch([long])
    trunc = [i for k, i in events if k == "truncated"]
    assert len(trunc) == 1 and trunc[0]["text"] == long and trunc[0]["chars"] == 750
