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

import hashlib
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


class OpenAlexBudgetExhausted(OpenAlexUnavailable):
    """Daily budget used up (HTTP 429 with X-RateLimit-Remaining <= 0): resume tomorrow or set the API key."""


class _RateLimited(TimeoutError):
    """HTTP 429 that is not (known to be) the daily budget: retried with backoff."""

    def __init__(self, message: str, header_missing: bool):
        super().__init__(message)
        self.header_missing = header_missing


def _urlopen_transport(url: str, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200)), dict(getattr(resp, "headers", {}) or {}), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


class HttpFetcher:
    """GET base_url + path with query params → parsed JSON (stdlib only).

    The API key is optional. Present in the env var → sent ONLY as `Authorization: Bearer` (never in the URL, so
    it cannot reach the cache, logs or error messages); absent → keyless. Requests are throttled to the mode's
    req/s. Every answer is cached by its URL WITHOUT credentials (cache_dir/requests/) when cache_dir is given, so
    a re-run - after a daily-budget stop, or in the other mode - continues from the cache.
    transport(url, headers, timeout) -> (status, headers, body) is injectable (tests).
    """

    def __init__(self, ocfg: dict, cache_dir: str | Path | None = None, transport=None, sleep=time.sleep,
                 clock=time.monotonic):
        self.base = ocfg["base_url"].rstrip("/")
        self.mailto = ocfg.get("mailto") or ""
        self.key_env = str(ocfg["api_key_env"])
        self._key = os.environ.get(self.key_env, "").strip()
        self.keyed = bool(self._key)
        rps = ocfg["requests_per_second_keyed" if self.keyed else "requests_per_second_keyless"]
        self.interval = 1.0 / float(rps)
        self.max_pages = int(ocfg["max_pages_keyed"]) if self.keyed else 1
        self.timeout, self.max_retries = float(ocfg["timeout"]), int(ocfg["max_retries"])
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.transport, self._sleep, self._clock = transport or _urlopen_transport, sleep, clock
        self._last = -1e9
        self.cost_usd = 0.0
        self.n_network = self.n_cached = 0
        print("[openalex] mode: " + ("with key" if self.keyed else "keyless")
              + "  (keyless: $0.10/day, 10 req/s | with key: $1/day, 30 req/s)")

    def _cache_path(self, url: str) -> Path | None:
        if not self.cache_dir:
            return None
        return self.cache_dir / "requests" / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")

    def __call__(self, path: str, params: dict) -> dict:
        url = f"{self.base}{path}?{urllib.parse.urlencode(params, safe=':,|*')}"     # no credentials: the cache key
        cp = self._cache_path(url)
        if cp is not None and cp.exists():
            try:
                cached = json.loads(cp.read_text(encoding="utf-8"))
            except (ValueError, OSError):              # half-written / corrupt: a cache miss, rewritten below
                print(f"[openalex] cache file {cp.name} is unreadable - fetching it again")
            else:
                self.n_cached += 1
                return cached
        if os.environ.get("ATLAS_OFFLINE") == "1":
            raise OpenAlexUnavailable("ATLAS_OFFLINE=1 — network access disabled")
        send_url = url + (f"&mailto={urllib.parse.quote(self.mailto, safe='')}" if self.mailto else "")
        headers = {"User-Agent": "tci-research-atlas"}
        if self.keyed:
            headers["Authorization"] = f"Bearer {self._key}"
        delay = 2.0
        for attempt in range(self.max_retries):
            self._sleep(max(0.0, self.interval - (self._clock() - self._last)))
            self._last = self._clock()
            try:
                status, hdr, body = self.transport(send_url, headers, self.timeout)
                hdr = {str(k).lower(): v for k, v in hdr.items()}
                if status == 429:
                    remaining = hdr.get("x-ratelimit-remaining")
                    if remaining is not None and float(remaining) <= 0:
                        raise OpenAlexBudgetExhausted(
                            "OpenAlex daily budget used up (HTTP 429). Cached responses are kept: run the same "
                            "command again tomorrow (the budget resets at midnight UTC), or set the "
                            "OPENALEX_API_KEY environment variable (free key: $1/day) and re-run to continue.")
                    raise _RateLimited("HTTP 429 (rate limit per second)", header_missing=remaining is None)
                if status >= 400:
                    raise urllib.error.URLError(f"HTTP {status}")
                data = json.loads(body.decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
                if attempt == self.max_retries - 1:
                    if isinstance(e, _RateLimited) and e.header_missing:
                        hint = ("" if self.keyed else f", or set the {self.key_env} environment variable "
                                "(free key: $1/day) and re-run to continue")
                        raise OpenAlexBudgetExhausted(
                            f"OpenAlex answered HTTP 429 on all {self.max_retries} attempts without an "
                            "X-RateLimit-Remaining header - probably the daily budget is used up. Cached responses "
                            "are kept: run the same command again tomorrow (the budget resets at midnight UTC)"
                            f"{hint}.") from None
                    raise OpenAlexUnavailable(f"OpenAlex request failed: {e}") from None
                self._sleep(delay)
                delay *= 2
                continue
            self.n_network += 1
            self.cost_usd += float((data.get("meta") or {}).get("cost_usd") or 0.0)
            if cp is not None:
                cp.parent.mkdir(parents=True, exist_ok=True)
                tmp = cp.with_suffix(".tmp")
                tmp.write_text(json.dumps(data), encoding="utf-8")
                tmp.replace(cp)
            return data
        raise OpenAlexUnavailable("unreachable")


def fetch_reference(fetch: Fetch, country: str, per_subfield: int, seed: int, pages: int = 1) -> pd.DataFrame:
    fields = fetch("/fields", {"per_page": 100, "select": "id,display_name"})["results"]
    subfields = []
    for f in fields:
        res = fetch("/subfields", {"filter": f"field.id:{short_id(f['id'])}", "per_page": 100,
                                   "select": "id,display_name,field"})["results"]
        subfields += [short_id(s["id"]) for s in res]
    rows = []
    for sid in tqdm(subfields, desc="openalex", disable=len(subfields) < 20):
        for page in range(1, pages + 1):
            params = {
                "filter": f"authorships.institutions.country_code:{country},primary_topic.subfield.id:{sid},has_abstract:true",
                "sample": per_subfield * pages, "seed": seed, "per_page": per_subfield,
                "select": "id,title,publication_year,primary_topic,abstract_inverted_index"}
            if pages > 1:
                params["page"] = page                     # more than one page needs an API key (see HttpFetcher)
            res = fetch("/works", params)["results"]
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
    fetcher = fetch or HttpFetcher(ocfg, cache_dir)       # request-level cache: valid in both modes
    pages = int(getattr(fetcher, "max_pages", 1))         # keyless is always 1 page
    stem = f"reference_{ocfg['country_code']}_{ocfg['per_subfield']}_{ocfg['seed']}" + (
        f"_p{pages}" if pages > 1 else "")
    meta_path = cache_dir / f"{stem}.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return read_table(cache_dir / f"{stem}.parquet"), {**meta, "origin": "cache"}
        except (ValueError, OSError):                  # half-written / corrupt: rebuilt (from the request cache)
            print(f"[openalex] cached reference {meta_path.name} is unreadable - building it again")
    try:
        df = fetch_reference(fetcher, ocfg["country_code"], int(ocfg["per_subfield"]), int(ocfg["seed"]), pages)
    finally:
        if isinstance(fetcher, HttpFetcher):
            print(f"[openalex] {fetcher.n_network} requests ({fetcher.n_cached} from cache), "
                  f"cost ${fetcher.cost_usd:.4f}")
    if df.empty:
        raise OpenAlexUnavailable("OpenAlex returned no reference works")
    fetched = datetime.now(UTC).strftime("%Y-%m-%d")
    meta = {"origin": "api", "version": f"openalex@{fetched}", "n": len(df), "fetched_at": fetched}
    write_table(df, cache_dir / f"{stem}.parquet")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return df, meta
