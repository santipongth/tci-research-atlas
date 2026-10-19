"""Per-release persistent state under state_dir/releases/.

work_dir is regenerable; state_dir keeps what the NEXT quarter needs:

  releases/index.json            ordered list of releases written so far
  releases/<release>/topics/     stable topic ids, article assignments, lineage (cluster step)
  releases/<release>/layout.parquet   topic positions (layout step)

A step re-run for the same release overwrites only that release's folder and always
reads the *previous* release, so re-running any step is idempotent.

Which release a step writes:
  cluster            current_release — pipeline.release, or the quarter of today when it is null; it records
                     that release and the snapshot time in work_dir/04_topics_meta.json
  every later step   work_release — the release recorded in work_dir. A configured pipeline.release that names
  (label, narrate,   another release is refused (ReleaseMismatch), so a work_dir is never published as a phantom
  layout, export …)  release or over an older one; null continues the recorded release even in a later quarter
  validate, publish  default_release — pipeline.release, else the recorded release, else today's quarter
snapshot_at (cluster time) drives as_of_year, the nowcast month cap and generated_at, so a run continued days
later describes the same snapshot.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path

from atlas.io_utils import replace_with_retry

RELEASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def release_from_date(d: date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def _checked(rel: str) -> str:
    """A release name is a single path component (never "../x", never a trailing newline)."""
    if not RELEASE_RE.fullmatch(rel):
        raise ValueError(f"invalid release name {rel!r}")
    return rel


def today() -> date:
    """The calendar date (one place, so a test can move the clock)."""
    return date.today()


def now() -> datetime:
    """Local time with its UTC offset, to the second — what cluster records as the snapshot."""
    return datetime.now().astimezone().replace(microsecond=0)


class ReleaseMismatch(ValueError):
    """pipeline.release names another release than the one work_dir was clustered for."""


def current_release(cfg: dict) -> str:
    """The release a NEW cluster run writes: pipeline.release, or the quarter of today."""
    return _checked(cfg["pipeline"].get("release") or release_from_date(today()))


def _topics_meta(cfg: dict) -> dict:
    p = Path(cfg["pipeline"]["work_dir"]) / "04_topics_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def recorded_release(cfg: dict) -> str | None:
    """The release work_dir was clustered for (04_topics_meta.json), None before any cluster run."""
    rel = _topics_meta(cfg).get("release")
    return _checked(rel) if rel else None


def work_release(cfg: dict) -> str:
    """The release every step after `cluster` writes: the one recorded in work_dir.

    pipeline.release null → the recorded release (also when the run is continued in a later quarter);
    set → it must be that release, else ReleaseMismatch. Nothing recorded yet → current_release.
    """
    recorded, configured = recorded_release(cfg), cfg["pipeline"].get("release")
    if recorded is None:
        return current_release(cfg)
    if configured and configured != recorded:
        raise ReleaseMismatch(f"work_dir was clustered for {recorded} but pipeline.release is {configured} — "
                              f"re-run from cluster, or set pipeline.release: {recorded}")
    return recorded


def default_release(cfg: dict) -> str:
    """atlas validate / publish without --release: pipeline.release, else work_dir's release, else today's quarter."""
    return _checked(cfg["pipeline"].get("release") or recorded_release(cfg) or release_from_date(today()))


def snapshot_at(cfg: dict) -> datetime:
    """When the data in work_dir was snapshotted (recorded by cluster); now() for a work_dir without a record."""
    s = _topics_meta(cfg).get("snapshot_at")
    return datetime.fromisoformat(s) if s else now()


def release_order(names, index=()) -> list[str]:
    """names oldest → newest: by position in `index` (the state index, known_releases) when every name is in it,
    else by name (YYYYQn sorts by time)."""
    pos = {r: i for i, r in enumerate(index)}
    names = sorted(set(names))
    return sorted(names, key=pos.__getitem__) if all(n in pos for n in names) else names


def is_newest(release: str, others, index=()) -> bool:
    """True when no release in `others` is newer than `release` (see release_order)."""
    return release_order([release, *others], index)[-1] == release


def _index_path(cfg: dict) -> Path:
    return Path(cfg["pipeline"]["state_dir"]) / "releases" / "index.json"


def known_releases(cfg: dict) -> list[str]:
    p = _index_path(cfg)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def previous_release(cfg: dict, release: str | None = None) -> str | None:
    """The release written before `release` (default: current_release) — None on the first run."""
    cur, rels = release or current_release(cfg), known_releases(cfg)
    if cur in rels:
        i = rels.index(cur)
        return rels[i - 1] if i > 0 else None
    return rels[-1] if rels else None


def release_dir(cfg: dict, release: str | None = None, create: bool = False) -> Path:
    """state_dir/releases/<release>; create=True also registers the release in index.json."""
    rel = _checked(release) if release else current_release(cfg)
    d = Path(cfg["pipeline"]["state_dir"]) / "releases" / rel
    if create:
        d.mkdir(parents=True, exist_ok=True)
        rels = known_releases(cfg)
        if rel not in rels:
            rels.append(rel)
            index = _index_path(cfg)
            tmp = index.with_name(f"{index.name}.{os.getpid()}.tmp")   # tmp + replace: never a half-written index
            tmp.write_text(json.dumps(rels), encoding="utf-8")
            replace_with_retry(tmp, index)
    return d
