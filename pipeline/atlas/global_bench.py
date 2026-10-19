"""Step `benchmark` (after sdg): Thailand vs the world in OpenAlex (E9) → work/17_* (export publishes global.json).

Counts per OpenAlex subfield for the emerging recent window R and its baseline B, for the whole world and for works
with an author in taxonomy.openalex.country_code — 16 requests (4 domains × R/B × world/country):
  GET /works?filter=publication_year:<a>-<b>,primary_topic.domain.id:<1-4>[,authorships.institutions.country_code:TH]
      &group_by=primary_topic.subfield.id&per_page=200
through P1's HttpFetcher (request cache in state_dir/openalex, keyless or with the API key, ATLAS_OFFLINE honoured;
every domain has fewer than 200 subfields, so one page each). Per subfield:
  world_ratio     (world_R / ΣR) ÷ (world_B / ΣB) — growth of its share of world output (window lengths cancel)
  activity_index  (country_R / Σcountry_R) ÷ (world_R / ΣR) — 1 = the country publishes it as much as the world does
  country_share   country_R / world_R
  opportunity     world_R ≥ benchmark.min_world_works, world_ratio ≥ min_world_ratio, activity_index ≤ max_activity_index
  tci_R           TCI corpus articles in R on topics anchored to the subfield (10_taxonomy + 07_emerging)
Never fails a run: disabled, a map not anchored to OpenAlex, offline or an API error → no table and
17_benchmark_meta.json {"skipped": reason} (the export names it in manifest.skipped_modules.global).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.openalex import Fetch, HttpFetcher, OpenAlexUnavailable, short_id

DOMAINS = (1, 2, 3, 4)
BENCH_COLUMNS = ["subfield_id", "subfield_en", "field_id", "world_R", "world_B", "country_R", "country_B", "tci_R",
                 "world_ratio", "activity_index", "country_share", "opportunity"]


def group_counts(fetch: Fetch, years: tuple[int, int], country: str | None) -> dict[str, tuple[str, int]]:
    out: dict[str, tuple[str, int]] = {}
    for d in DOMAINS:
        flt = f"publication_year:{years[0]}-{years[1]},primary_topic.domain.id:{d}"
        if country:
            flt += f",authorships.institutions.country_code:{country}"
        res = fetch("/works", {"filter": flt, "group_by": "primary_topic.subfield.id", "per_page": 200})
        for g in res.get("group_by") or []:
            sid = short_id(g.get("key"))
            if sid.isdigit():
                out[sid] = (str(g.get("key_display_name") or ""), int(g.get("count") or 0))
    return out


def _total(counts: dict[str, tuple[str, int]]) -> int:
    return sum(c for _, c in counts.values())


def benchmark_table(world_r: dict, world_b: dict, country_r: dict, country_b: dict, tci_r: dict[str, int],
                    bcfg: dict) -> pd.DataFrame:
    wr_all, wb_all, cr_all = _total(world_r), _total(world_b), _total(country_r)
    rows = []
    for sid in sorted(set(world_r) | set(world_b)):
        name = (world_r.get(sid) or world_b.get(sid))[0]
        wr, wb = world_r.get(sid, ("", 0))[1], world_b.get(sid, ("", 0))[1]
        cr, cb = country_r.get(sid, ("", 0))[1], country_b.get(sid, ("", 0))[1]
        ratio = (wr / wr_all) / (wb / wb_all) if wr and wb and wr_all and wb_all else None
        ai = (cr / cr_all) / (wr / wr_all) if wr and cr_all and wr_all else None
        opportunity = bool(ratio is not None and ai is not None and wr >= int(bcfg["min_world_works"])
                           and ratio >= float(bcfg["min_world_ratio"]) and ai <= float(bcfg["max_activity_index"]))
        rows.append({"subfield_id": sid, "subfield_en": name, "field_id": sid[:2], "world_R": wr, "world_B": wb,
                     "country_R": cr, "country_B": cb, "tci_R": int(tci_r.get(sid, 0)), "world_ratio": ratio,
                     "activity_index": ai, "country_share": cr / wr if wr else None, "opportunity": opportunity})
    return pd.DataFrame(rows, columns=BENCH_COLUMNS)


def _skip(work: Path, reason: str) -> pd.DataFrame:
    print(f"[benchmark] skipped: {reason}")
    (work / "17_benchmark_meta.json").write_text(json.dumps({"skipped": reason}, ensure_ascii=False), encoding="utf-8")
    return pd.DataFrame(columns=BENCH_COLUMNS)


def benchmark(cfg: dict, fetch: Fetch | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    bcfg = cfg["benchmark"]
    for stale in work.glob("17_*"):
        stale.unlink()
    if not bcfg["enabled"]:
        return _skip(work, "benchmark.enabled is false")
    try:
        tax = read_table(work / "10_taxonomy.parquet")
    except FileNotFoundError:
        return _skip(work, "no 10_taxonomy — run the taxonomy step first")
    if tax.empty or not (tax["source"] == "openalex").all():
        return _skip(work, "the topic map is not anchored to OpenAlex subfields (taxonomy fell back to agglomerative "
                           "groups)")
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    e = cfg["emerging"]
    r0 = last - int(e["recent_window"]) + 1
    R, B = (r0, last), (r0 - int(e["baseline_window"]), r0 - 1)
    ocfg = cfg["taxonomy"]["openalex"]
    cc = str(ocfg["country_code"])
    fetcher = fetch or HttpFetcher(ocfg, Path(cfg["pipeline"]["state_dir"]) / "openalex")
    try:
        wr, wb = group_counts(fetcher, R, None), group_counts(fetcher, B, None)
        cr, cb = group_counts(fetcher, R, cc), group_counts(fetcher, B, cc)
    except OpenAlexUnavailable as err:
        return _skip(work, f"OpenAlex unavailable: {err}")
    if not wr or not wb:
        return _skip(work, "OpenAlex returned no subfield counts")
    em = read_table(work / "07_emerging.parquet")[["topic_id", "count_recent"]]
    tci = (tax[["topic_id", "subfield_id"]].astype({"subfield_id": str}).merge(em, on="topic_id")
           .groupby("subfield_id")["count_recent"].sum())
    table = benchmark_table(wr, wb, cr, cb, {str(k): int(v) for k, v in tci.items()}, bcfg)
    write_table(table, work / "17_benchmark.parquet")
    meta = {"skipped": None, "source": f"openalex@{datetime.now(UTC).strftime('%Y-%m-%d')}", "country": cc,
            "recent": list(R), "baseline": list(B), "world_recent": _total(wr), "country_recent": _total(cr),
            "subfields": int(len(table)), "opportunities": int(table["opportunity"].sum())}
    (work / "17_benchmark_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[benchmark] {len(table)} subfields, {meta['opportunities']} opportunities ({cc} vs the world, "
          f"{R[0]}–{R[1]} vs {B[0]}–{B[1]})")
    return table
