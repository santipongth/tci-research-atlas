"""Quarter diff (E5 "what changed since the previous release") → diff.json and page /changes.

Every export writes a compact snapshot of its release to state_dir/releases/<release>/snapshot.json
(topics: id → status, size, share_recent, score, names; KPIs; journal ids) — state_dir is the persistent
store, so the next quarter can compare even when output/ was cleaned. A previous release exported before P2 has
no snapshot: the diff then reads output/data/<previous>/topics.json + overview.json (+ journals.json when
present). Neither available → no diff.json (the web explains that /changes needs a previous release).
"""
from __future__ import annotations

import json
from pathlib import Path

from atlas.state import release_dir

SNAPSHOT = "snapshot.json"
KPI_KEYS = ("articles", "assigned_articles", "topics", "journals", "institutions")
STATUS_ORDER = ("EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA")


def make_snapshot(release: str, topics: list[dict], kpis: dict, journal_ids: list[str] | None) -> dict:
    """topics: contract Topic dicts (id, status, size, score, th, en, metrics.share_recent)."""
    return {"release": release,
            "topics": {t["id"]: {"status": t["status"], "size": int(t["size"]), "score": float(t.get("score") or 0.0),
                                 "share_recent": float(t["metrics"]["share_recent"]), "th": t.get("th", ""),
                                 "en": t.get("en", "")} for t in topics},
            "kpis": {k: kpis[k] for k in KPI_KEYS if k in kpis},
            "journals": sorted(journal_ids) if journal_ids is not None else None}


def write_snapshot(cfg: dict, release: str, snap: dict) -> Path:
    d = release_dir(cfg, release)
    d.mkdir(parents=True, exist_ok=True)
    p = d / SNAPSHOT
    p.write_text(json.dumps(snap, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return p


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def load_snapshot(cfg: dict, release: str) -> tuple[dict | None, str]:
    """(snapshot, source "state" | "output") of a release, or (None, "")."""
    snap = _load(release_dir(cfg, release) / SNAPSHOT)
    if snap is not None:
        return snap, "state"
    folder = Path(cfg["pipeline"]["output_dir"]) / "data" / release
    topics, overview = _load(folder / "topics.json"), _load(folder / "overview.json")
    try:
        rows = [t for t in topics["topics"] if isinstance(t, dict) and {"id", "status", "size", "metrics"} <= set(t)]
        kpis = overview["kpis"]
    except (TypeError, KeyError):
        return None, ""
    journals = _load(folder / "journals.json")
    ids = [j["id"] for j in journals.get("journals", [])] if isinstance(journals, dict) else None
    return make_snapshot(release, rows, kpis, ids), "output"


def quarter_diff(cur: dict, prev: dict, lineage: dict[str, dict], movers: int, min_share_delta: float) -> dict:
    """What changed from `prev` to `cur` (snapshots). lineage: current topic id → {event, parents}."""
    ct, pt = cur["topics"], prev["topics"]
    common = sorted(set(ct) & set(pt))
    new = []
    for tid in sorted(set(ct) - set(pt)):
        lin = lineage.get(tid, {})
        event = lin.get("event") if lin.get("event") in ("split", "merge") else "new"
        new.append({"topic": tid, "event": event, "parents": list(lin.get("parents", []))})
    retired = [{"topic": tid, "th": pt[tid].get("th", ""), "en": pt[tid].get("en", "")}
               for tid in sorted(set(pt) - set(ct))]
    order = {s: i for i, s in enumerate(STATUS_ORDER)}
    changes = sorted(({"topic": t, "previous": pt[t]["status"], "current": ct[t]["status"]}
                      for t in common if pt[t]["status"] != ct[t]["status"]),
                     key=lambda r: (order.get(r["current"], 99), r["topic"]))
    moved = [{"topic": t, "share_previous": round(pt[t]["share_recent"], 6), "share_current": round(ct[t]["share_recent"], 6)}
             for t in common if abs(ct[t]["share_recent"] - pt[t]["share_recent"]) >= min_share_delta]
    moved.sort(key=lambda r: (-abs(r["share_current"] - r["share_previous"]), r["topic"]))
    kpis = [{"key": k, "previous": float(prev["kpis"][k]), "current": float(cur["kpis"][k])}
            for k in KPI_KEYS if k in cur["kpis"] and k in prev.get("kpis", {})]
    compared = cur.get("journals") is not None and prev.get("journals") is not None
    return {"release": cur["release"], "previous_release": prev["release"], "kpis": kpis, "new_topics": new,
            "retired": retired, "status_changes": changes, "movers": moved[:movers],
            "journals_compared": compared,
            "new_journals": sorted(set(cur["journals"]) - set(prev["journals"])) if compared else []}
