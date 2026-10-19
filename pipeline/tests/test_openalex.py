import json
import re
import urllib.parse

import pytest

from atlas.openalex import (
    HttpFetcher,
    OpenAlexUnavailable,
    abstract_from_inverted,
    fetch_reference,
    flatten_work,
    load_reference,
    read_reference_file,
    short_id,
)
from tests.conftest import FIXTURES

OA = FIXTURES / "openalex"


class RecordedFetch:
    """Serves tests/fixtures/openalex/*.json by endpoint + filter; records every call."""

    def __init__(self):
        self.calls = []

    def __call__(self, path: str, params: dict) -> dict:
        self.calls.append((path, dict(params)))
        if path == "/fields":
            name = "fields"
        elif path == "/subfields":
            name = "subfields_" + re.search(r"field\.id:(\d+)", params["filter"]).group(1)
        else:
            name = "works_" + re.search(r"primary_topic\.subfield\.id:(\d+)", params["filter"]).group(1)
        return json.loads((OA / f"{name}.json").read_text(encoding="utf-8"))


def test_helpers():
    assert short_id("https://openalex.org/subfields/1702") == "1702" and short_id(None) == ""
    assert abstract_from_inverted({"b": [1], "a": [0, 2]}) == "a b a" and abstract_from_inverted(None) == ""
    assert flatten_work({"id": "W1", "primary_topic": None}) is None


def test_fetch_reference_walks_fields_subfields_and_samples_works():
    fetch = RecordedFetch()
    df = fetch_reference(fetch, "TH", per_subfield=100, seed=42)
    assert sorted(df["subfield_id"].unique()) == ["1702", "3304", "3315"]
    assert len(df) == 5                                    # the work without a primary topic is dropped
    row = df.set_index("work_id").loc["W1000000002"]
    assert (row["field_id"], row["field_en"]) == ("17", "Computer Science")
    assert row["abstract"] == "We fine-tune a language model a Thai corpus"
    works = [p for path, p in fetch.calls if path == "/works"]
    assert len(works) == 3 and all(p["sample"] == 100 and p["seed"] == 42 and p["per_page"] == 100 for p in works)
    assert all("authorships.institutions.country_code:TH" in p["filter"] and "has_abstract:true" in p["filter"]
               for p in works)


def test_load_reference_caches_in_state_dir(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    df, meta = load_reference(cfg, RecordedFetch())
    assert meta["origin"] == "api" and meta["version"].startswith("openalex@") and len(df) == 5

    def boom(path, params):
        raise AssertionError("must not fetch again")

    df2, meta2 = load_reference(cfg, boom)
    assert meta2["origin"] == "cache" and df2["work_id"].tolist() == df["work_id"].tolist()


def test_reference_file_overrides_the_api(make_cfg, tmp_path):
    works = json.loads((OA / "works_3304.json").read_text(encoding="utf-8"))["results"]
    p = tmp_path / "ref.jsonl"
    p.write_text("\n".join(json.dumps(w) for w in works), encoding="utf-8")
    cfg = make_cfg(tmp_path)
    cfg["taxonomy"]["reference_path"] = str(p)
    df, meta = load_reference(cfg, None)
    assert meta == {"origin": "file", "version": "file:ref.jsonl", "n": 2}
    csv = tmp_path / "ref.csv"
    df.to_csv(csv, index=False)
    assert read_reference_file(csv)["subfield_id"].tolist() == ["3304", "3304"]


def test_offline_flag_blocks_the_network(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    with pytest.raises(OpenAlexUnavailable, match="ATLAS_OFFLINE"):
        load_reference(cfg)                                 # conftest sets ATLAS_OFFLINE=1


class FakeTransport:
    """Serves the recorded fixtures over the HttpFetcher transport interface; scripted statuses first."""

    def __init__(self, script=()):
        self.script = list(script)
        self.calls = []                                  # (url, headers)

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers)))
        if self.script:
            status, hdr = self.script.pop(0)
            if status != 200:
                return status, hdr, b"{}"
        path, _, query = url.partition("openalex.org")[2].partition("?")
        params = {k: urllib.parse.unquote(v) for k, v in (p.split("=", 1) for p in query.split("&"))}
        body = json.dumps(RecordedFetch()(path, params)).encode("utf-8")
        return 200, {}, body


def _fetcher(make_cfg, tmp_path, monkeypatch, transport, key=None, **over):
    cfg = make_cfg(tmp_path)
    ocfg = {**cfg["taxonomy"]["openalex"], **over}
    monkeypatch.delenv("ATLAS_OFFLINE", raising=False)
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    if key:
        monkeypatch.setenv("OPENALEX_API_KEY", key)
    cache = tmp_path / "state" / "openalex"
    return HttpFetcher(ocfg, cache, transport=transport, sleep=lambda s: None), cache


def test_key_is_optional_and_only_sent_as_a_bearer_header(make_cfg, tmp_path, monkeypatch, capsys):
    t = FakeTransport()
    f, cache = _fetcher(make_cfg, tmp_path, monkeypatch, t, key="SECRETKEY", mailto="atlas@example.org")
    assert f("/fields", {"per_page": 100}) == json.loads((OA / "fields.json").read_text(encoding="utf-8"))
    url, headers = t.calls[0]
    assert headers["Authorization"] == "Bearer SECRETKEY" and "SECRETKEY" not in url and "api_key" not in url
    assert url.endswith("&mailto=atlas%40example.org")
    assert "with key" in capsys.readouterr().out
    cached = [p for p in cache.rglob("*") if p.is_file()]
    assert cached and all("SECRETKEY" not in p.name and "SECRETKEY" not in p.read_text(encoding="utf-8")
                          and "mailto" not in p.read_text(encoding="utf-8") for p in cached)

    t2 = FakeTransport()
    f2, _ = _fetcher(make_cfg, tmp_path, monkeypatch, t2)         # keyless, same cache dir: served from cache
    f2("/fields", {"per_page": 100})
    assert t2.calls == [] and f2.n_cached == 1
    f3, _ = _fetcher(make_cfg, tmp_path / "other", monkeypatch, t2)
    f3("/fields", {"per_page": 100})
    assert "Authorization" not in t2.calls[0][1] and "mailto" not in t2.calls[0][0]
    assert "keyless" in capsys.readouterr().out


def test_daily_budget_429_stops_cleanly_and_rerun_resumes_from_cache(make_cfg, tmp_path, monkeypatch):
    t = FakeTransport([(200, {}), (200, {}), (429, {"X-RateLimit-Remaining": "0"})])
    f, cache = _fetcher(make_cfg, tmp_path, monkeypatch, t, key="SECRETKEY")
    with pytest.raises(OpenAlexUnavailable, match="tomorrow") as exc:
        fetch_reference(f, "TH", 100, 42)
    assert "SECRETKEY" not in str(exc.value) and "OPENALEX_API_KEY" in str(exc.value)
    n_first = len(t.calls)
    t2 = FakeTransport()
    f2, _ = _fetcher(make_cfg, tmp_path, monkeypatch, t2)
    df = fetch_reference(f2, "TH", 100, 42)
    assert len(df) == 5 and f2.n_cached == n_first - 1 and len(t2.calls) == 6 - (n_first - 1)


def test_per_second_429_is_retried_and_cost_is_tracked(make_cfg, tmp_path, monkeypatch):
    t = FakeTransport([(429, {}), (429, {"X-RateLimit-Remaining": "7"})])
    f, _ = _fetcher(make_cfg, tmp_path, monkeypatch, t)
    f("/fields", {"per_page": 100})
    assert len(t.calls) == 3 and f.n_network == 1
    t = FakeTransport([(429, {})] * 3)
    f, _ = _fetcher(make_cfg, tmp_path / "b", monkeypatch, t)
    with pytest.raises(OpenAlexUnavailable, match="429"):
        f("/fields", {"per_page": 100})


def test_pages_only_with_a_key(make_cfg, tmp_path, monkeypatch):
    for key, expected in (("k", 2), (None, 1)):
        t = FakeTransport()
        f, _ = _fetcher(make_cfg, tmp_path / str(key), monkeypatch, t, key=key, max_pages_keyed=2)
        assert f.max_pages == expected
        fetch_reference(f, "TH", 100, 42, pages=f.max_pages)
        works = [u for u, _ in t.calls if "/works" in u]
        assert len(works) == 3 * expected and (expected == 2) == any("page=2" in u for u in works)


def test_offline_flag_blocks_the_network_for_uncached_requests(make_cfg, tmp_path, monkeypatch):
    f, _ = _fetcher(make_cfg, tmp_path, monkeypatch, FakeTransport())
    monkeypatch.setenv("ATLAS_OFFLINE", "1")
    with pytest.raises(OpenAlexUnavailable, match="ATLAS_OFFLINE"):
        f("/fields", {"per_page": 100})


def test_429_on_every_attempt_without_a_remaining_header_reads_as_the_daily_budget(make_cfg, tmp_path,
                                                                                   monkeypatch):
    from atlas.openalex import OpenAlexBudgetExhausted

    f, _ = _fetcher(make_cfg, tmp_path, monkeypatch, FakeTransport([(429, {})] * 3))
    with pytest.raises(OpenAlexBudgetExhausted, match="probably the daily budget") as exc:
        f("/fields", {"per_page": 100})
    assert "tomorrow" in str(exc.value) and "OPENALEX_API_KEY" in str(exc.value)
    f, _ = _fetcher(make_cfg, tmp_path / "b", monkeypatch,
                    FakeTransport([(429, {"X-RateLimit-Remaining": "7"})] * 3))   # per-second limit: stays generic
    with pytest.raises(OpenAlexUnavailable, match="429") as exc:
        f("/fields", {"per_page": 100})
    assert not isinstance(exc.value, OpenAlexBudgetExhausted)


def test_corrupt_cache_files_are_cache_misses_and_get_rewritten(make_cfg, tmp_path, monkeypatch):
    t = FakeTransport()
    f, cache = _fetcher(make_cfg, tmp_path, monkeypatch, t)
    good = f("/fields", {"per_page": 100})
    (cp,) = list((cache / "requests").iterdir())
    cp.write_text('{"results": [', encoding="utf-8")                        # half-written
    f2, _ = _fetcher(make_cfg, tmp_path, monkeypatch, t)
    assert f2("/fields", {"per_page": 100}) == good and len(t.calls) == 2 and f2.n_network == 1
    assert json.loads(cp.read_text(encoding="utf-8")) == good                # rewritten

    cfg = make_cfg(tmp_path)
    load_reference(cfg, RecordedFetch())
    (meta,) = (tmp_path / "state" / "openalex").glob("reference_*.json")
    meta.write_text("{", encoding="utf-8")                                   # half-written reference meta
    df, m = load_reference(cfg, RecordedFetch())
    assert m["origin"] == "api" and len(df) == 5
    assert json.loads(meta.read_text(encoding="utf-8"))["n"] == 5
    for bad in (b"", b"\x80\x04not a pickle"):              # the .pkl fallback, truncated or corrupt
        for p in meta.parent.glob(meta.stem + ".*"):
            if p.suffix != ".json":
                p.unlink()
        meta.with_suffix(".pkl").write_bytes(bad)
        df, m = load_reference(cfg, RecordedFetch())
        assert m["origin"] == "api" and len(df) == 5
