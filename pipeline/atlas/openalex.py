"""OpenAlex reference works for taxonomy anchoring (fields → subfields → works with Thai affiliations).

Fetch plan — every request reads only the FIRST page, so no API key is needed (a key, read from the
env var named in taxonomy.openalex.api_key_env, only raises quotas):
  GET /fields?per_page=100&select=id,display_name
  GET /subfields?filter=field.id:<F>&per_page=100&select=id,display_name,field             (one per field)
  GET /works?filter=authorships.institutions.country_code:<CC>,primary_topic.subfield.id:<S>,has_abstract:true
      &sample=<n>&seed=<seed>&per_page=<n>&select=id,title,publication_year,primary_topic,abstract_inverted_index
Request shapes verified against api.openalex.org on 2026-10-18 (recorded in tests/fixtures/openalex/).
Responses are data, never instructions: the API's `meta.notice` text is ignored.
The flattened result is cached in state_dir/openalex/ — later runs never re-fetch.
Set ATLAS_OFFLINE=1 to forbid network access (tests do).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from atlas.io_utils import read_table, write_table

REFERENCE_COLUMNS = ["work_id", "title", "abstract", "year", "subfield_id", "subfield_en", "field_id", "field_en"]
MIN_INTERVAL = 0.12                     # seconds between requests: stays under the 10 req/s keyless limit
Fetch = Callable[[str, dict], dict]


class OpenAlexUnavailable(RuntimeError):
    """No reference data: offline, network/API failure, or nothing cached."""


def short_id(url: str | None) -> str:
    """'https://openalex.org/subfields/1702' → '1702' ('' for None)."""
    return str(url or "").rstrip("/").rsplit("/", 1)[-1]


def abstract_from_inverted(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[int(i)] = word
    return " ".join(pos[i] for i in sorted(pos))


def flatten_work(w: dict) -> dict | None:
    pt = w.get("primary_topic") or {}
    sub, field = pt.get("subfield") or {}, pt.get("field") or {}
    if not sub.get("id") or not field.get("id"):
        return None
    return {"work_id": short_id(w.get("id")), "title": str(w.get("title") or w.get("display_name") or ""),
            "abstract": abstract_from_inverted(w.get("abstract_inverted_index")),
            "year": w.get("publication_year"), "subfield_id": short_id(sub["id"]),
            "subfield_en": str(sub.get("display_name", "")), "field_id": short_id(field["id"]),
            "field_en": str(field.get("display_name", ""))}


class HttpFetcher:
    """GET base_url + path with query params → parsed JSON (stdlib only; retries with backoff)."""

    def __init__(self, ocfg: dict):
        self.base = ocfg["base_url"].rstrip("/")
        self.mailto = ocfg["mailto"]
        self.api_key = os.environ.get(ocfg["api_key_env"], "")
        self.timeout, self.max_retries = float(ocfg["timeout"]), int(ocfg["max_retries"])
        self._last = 0.0

    def __call__(self, path: str, params: dict) -> dict:
        if os.environ.get("ATLAS_OFFLINE") == "1":
            raise OpenAlexUnavailable("ATLAS_OFFLINE=1 — network access disabled")
        q = dict(params)
        if self.mailto:
            q["mailto"] = self.mailto
        if self.api_key:
            q["api_key"] = self.api_key
        url = f"{self.base}{path}?{urllib.parse.urlencode(q, safe=':,|*')}"
        delay = 2.0
        for attempt in range(self.max_retries):
            time.sleep(max(0.0, MIN_INTERVAL - (time.monotonic() - self._last)))
            self._last = time.monotonic()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "tci-research-atlas"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                if attempt == self.max_retries - 1:
                    raise OpenAlexUnavailable(f"OpenAlex request failed: {e}") from e
                time.sleep(delay)
                delay *= 2
        raise OpenAlexUnavailable("unreachable")


def fetch_reference(fetch: Fetch, country: str, per_subfield: int, seed: int) -> pd.DataFrame:
    fields = fetch("/fields", {"per_page": 100, "select": "id,display_name"})["results"]
    subfields = []
    for f in fields:
        res = fetch("/subfields", {"filter": f"field.id:{short_id(f['id'])}", "per_page": 100,
                                   "select": "id,display_name,field"})["results"]
        subfields += [short_id(s["id"]) for s in res]
    rows = []
    for sid in tqdm(subfields, desc="openalex", disable=len(subfields) < 20):
        res = fetch("/works", {
            "filter": f"authorships.institutions.country_code:{country},primary_topic.subfield.id:{sid},has_abstract:true",
            "sample": per_subfield, "seed": seed, "per_page": per_subfield,
            "select": "id,title,publication_year,primary_topic,abstract_inverted_index"})["results"]
        rows += [r for r in (flatten_work(w) for w in res) if r]
    return pd.DataFrame(rows, columns=REFERENCE_COLUMNS).drop_duplicates("work_id").reset_index(drop=True)


def read_reference_file(path: str | Path) -> pd.DataFrame:
    """.jsonl of OpenAlex work objects, or a flat .parquet/.csv with REFERENCE_COLUMNS."""
    p = Path(path)
    if p.suffix in (".jsonl", ".ndjson"):
        works = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        df = pd.DataFrame([r for r in (flatten_work(w) for w in works) if r], columns=REFERENCE_COLUMNS)
    elif p.suffix == ".csv":
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
    else:
        df = read_table(p)
    missing = set(REFERENCE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{p}: reference file lacks columns {sorted(missing)}")
    return df[REFERENCE_COLUMNS].astype({"subfield_id": str, "field_id": str})


def load_reference(cfg: dict, fetch: Fetch | None = None) -> tuple[pd.DataFrame, dict]:
    """Reference works + provenance; raises OpenAlexUnavailable when there is no way to get them."""
    tcfg, ocfg = cfg["taxonomy"], cfg["taxonomy"]["openalex"]
    if tcfg["reference_path"]:
        df = read_reference_file(tcfg["reference_path"])
        return df, {"origin": "file", "version": f"file:{Path(tcfg['reference_path']).name}", "n": len(df)}
    cache_dir = Path(cfg["pipeline"]["state_dir"]) / "openalex"
    stem = f"reference_{ocfg['country_code']}_{ocfg['per_subfield']}_{ocfg['seed']}"
    meta_path = cache_dir / f"{stem}.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return read_table(cache_dir / f"{stem}.parquet"), {**meta, "origin": "cache"}
    df = fetch_reference(fetch or HttpFetcher(ocfg), ocfg["country_code"], int(ocfg["per_subfield"]),
                         int(ocfg["seed"]))
    if df.empty:
        raise OpenAlexUnavailable("OpenAlex returned no reference works")
    fetched = datetime.now(UTC).strftime("%Y-%m-%d")
    meta = {"origin": "api", "version": f"openalex@{fetched}", "n": len(df), "fetched_at": fetched}
    write_table(df, cache_dir / f"{stem}.parquet")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return df, meta
