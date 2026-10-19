import json
import re

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


def test_http_fetcher_builds_polite_urls(monkeypatch, make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    ocfg = {**cfg["taxonomy"]["openalex"], "mailto": "atlas@example.org"}
    monkeypatch.delenv("ATLAS_OFFLINE")
    monkeypatch.setenv("OPENALEX_API_KEY", "k123")
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"results": []}'

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        return Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert HttpFetcher(ocfg)("/works", {"filter": "a:1,b:2", "per_page": 5}) == {"results": []}
    assert seen["url"] == ("https://api.openalex.org/works?filter=a:1,b:2&per_page=5"
                           "&mailto=atlas%40example.org&api_key=k123")
