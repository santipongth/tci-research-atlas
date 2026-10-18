"""Per-release persistent state under state_dir/releases/.

work_dir is regenerable; state_dir keeps what the NEXT quarter needs:

  releases/index.json            ordered list of releases written so far
  releases/<release>/topics/     stable topic ids, article assignments, lineage (cluster step)
  releases/<release>/layout.parquet   topic positions (layout step)

A step re-run for the same release overwrites only that release's folder and always
reads the *previous* release, so re-running any step is idempotent.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

RELEASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def release_from_date(d: date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def current_release(cfg: dict) -> str:
    rel = cfg["pipeline"].get("release") or release_from_date(date.today())
    if not RELEASE_RE.match(rel):
        raise ValueError(f"invalid release name {rel!r}")
    return rel


def _index_path(cfg: dict) -> Path:
    return Path(cfg["pipeline"]["state_dir"]) / "releases" / "index.json"


def known_releases(cfg: dict) -> list[str]:
    p = _index_path(cfg)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def previous_release(cfg: dict) -> str | None:
    """The release written before the current one (None on the first run)."""
    cur, rels = current_release(cfg), known_releases(cfg)
    if cur in rels:
        i = rels.index(cur)
        return rels[i - 1] if i > 0 else None
    return rels[-1] if rels else None


def release_dir(cfg: dict, release: str | None = None, create: bool = False) -> Path:
    """state_dir/releases/<release>; create=True also registers the release in index.json."""
    rel = release or current_release(cfg)
    d = Path(cfg["pipeline"]["state_dir"]) / "releases" / rel
    if create:
        d.mkdir(parents=True, exist_ok=True)
        rels = known_releases(cfg)
        if rel not in rels:
            rels.append(rel)
            _index_path(cfg).write_text(json.dumps(rels), encoding="utf-8")
    return d
