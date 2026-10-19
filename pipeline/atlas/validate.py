"""`atlas validate` — check one release folder before it is published.

1. integrity  manifest.json parses; every listed file exists with the listed size and sha256;
              JSON files on disk that the manifest does not list → warning
2. schema     every file validates against its pydantic model (atlas/schema/contract.py)
3. coherence  unique topic ids; one topics/<id>.json per topic; series and edges only name known
              topics; every topic's group exists in taxonomy.json; KPI topic count matches
4. diff       against the previous release folder (manifest.previous_release next to this one, or
              --previous): topic count change, share of last release's ids kept, status changes of
              continuing topics, large size swings, a shrinking corpus (thresholds: validation.*)
5. LLM        topic names that fell back to keywords and narrative/brief items that fell back to a
              template (invalid replies, or transient errors past max_retries) → warning: re-run `atlas llm` before publishing
Exit code: 0 = clean, 1 = warnings only, 2 = errors.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from atlas.schema.contract import SCHEMA_VERSION, Manifest, model_for


@dataclass
class Report:
    release_dir: str
    previous_dir: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return 2 if self.errors else 1 if self.warnings else 0


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _check_files(root: Path, rep: Report) -> dict[str, object]:
    """Integrity + schema. Returns {relative path: validated model} for files that passed."""
    try:
        manifest = Manifest.model_validate(_load(root / "manifest.json"))
    except FileNotFoundError:
        rep.errors.append("manifest.json is missing")
        return {}
    except (ValidationError, json.JSONDecodeError) as e:
        rep.errors.append(f"manifest.json is invalid: {e}")
        return {}
    if manifest.schema_version.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        rep.errors.append(f"schema major version {manifest.schema_version} ≠ pipeline {SCHEMA_VERSION}")
    models: dict[str, object] = {"manifest.json": manifest}
    listed = {f.path for f in manifest.files}
    for entry in manifest.files:
        p = root / entry.path
        if not p.exists():
            rep.errors.append(f"{entry.path}: listed in the manifest but missing")
            continue
        data = p.read_bytes()
        if len(data) != entry.bytes or hashlib.sha256(data).hexdigest() != entry.sha256:
            rep.errors.append(f"{entry.path}: size/sha256 differs from the manifest (file changed after export?)")
            continue
        model = model_for(entry.path)
        if model is None:
            rep.warnings.append(f"{entry.path}: no contract model — not schema-checked")
            continue
        try:
            models[entry.path] = model.model_validate(json.loads(data.decode("utf-8")))
        except (ValidationError, json.JSONDecodeError, UnicodeDecodeError) as e:
            rep.errors.append(f"{entry.path}: does not match the contract: {str(e).splitlines()[0]}")
    for p in sorted(root.rglob("*.json")):
        rel = p.relative_to(root).as_posix()
        if rel != "manifest.json" and rel not in listed:
            rep.warnings.append(f"{rel}: on disk but not in the manifest")
    for required in ("overview.json", "taxonomy.json", "topics.json", "series.json", "edges.json"):
        if required not in listed:
            rep.errors.append(f"{required}: required file not in the manifest")
    return models


def _check_coherence(models: dict, rep: Report) -> None:
    topics = models.get("topics.json")
    if topics is None:
        return
    ids = [t.id for t in topics.topics]
    known = set(ids)
    if len(known) != len(ids):
        rep.errors.append("topics.json: duplicate topic ids")
    missing = [i for i in ids if f"topics/{i}.json" not in models]
    if missing:
        rep.errors.append(f"{len(missing)} topics have no valid topics/<id>.json (e.g. {missing[0]})")
    if (s := models.get("series.json")) is not None and set(s.topics) != known:
        rep.errors.append("series.json: topic ids differ from topics.json")
    if (e := models.get("edges.json")) is not None and any(x.s not in known or x.t not in known for x in e.edges):
        rep.errors.append("edges.json: an edge names an unknown topic")
    if (tx := models.get("taxonomy.json")) is not None:
        groups = {g.id for g in tx.groups}
        bad = sorted({t.group for t in topics.topics} - groups)
        if bad:
            rep.errors.append(f"taxonomy.json: missing groups {bad[:5]}")
    if (ov := models.get("overview.json")) is not None and ov.kpis.topics != len(ids):
        rep.errors.append(f"overview.json: kpis.topics={ov.kpis.topics} but topics.json has {len(ids)}")
    rep.stats.update(topics=len(ids), articles=ov.kpis.articles if ov is not None else None,
                     statuses=ov.status_counts if ov is not None else {})


def _diff(models: dict, prev_root: Path, vcfg: dict, rep: Report) -> None:
    try:
        prev_topics = {t["id"]: t for t in _load(prev_root / "topics.json")["topics"]}
        prev_overview = _load(prev_root / "overview.json")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        rep.warnings.append(f"previous release at {prev_root} is unreadable ({e}) — diff skipped")
        return
    cur = {t.id: t for t in models["topics.json"].topics}
    n0, n1 = len(prev_topics), len(cur)
    change = abs(n1 - n0) / n0 if n0 else 0.0
    kept = len(set(prev_topics) & set(cur)) / n0 if n0 else 1.0
    common = sorted(set(prev_topics) & set(cur))
    flips = [i for i in common if prev_topics[i]["status"] != cur[i].status]
    flip_frac = len(flips) / len(common) if common else 0.0
    rep.stats.update(previous_topics=n0, topic_count_change=round(change, 4), kept_ids=round(kept, 4),
                     status_changes=len(flips))
    if change > float(vcfg["max_topic_count_change"]):
        rep.warnings.append(f"topic count {n0} → {n1} ({change:.0%} change)")
    if kept < float(vcfg["min_kept_ids"]):
        rep.warnings.append(f"only {kept:.0%} of the previous release's topic ids remain")
    if flip_frac > float(vcfg["max_status_change_frac"]):
        rep.warnings.append(f"{len(flips)} of {len(common)} continuing topics changed status ({flip_frac:.0%})")
    swing, floor = float(vcfg["size_swing_ratio"]), int(vcfg["size_swing_min_articles"])
    swings = [f"{i} {prev_topics[i]['size']}→{cur[i].size}" for i in common
              if max(prev_topics[i]["size"], cur[i].size) >= floor
              and max(prev_topics[i]["size"], cur[i].size) >= swing * max(min(prev_topics[i]["size"], cur[i].size), 1)]
    if swings:
        rep.warnings.append(f"{len(swings)} topics changed size ≥ {swing:g}×: " + ", ".join(swings[:10]))
    a0, a1 = int(prev_overview["kpis"]["articles"]), models["overview.json"].kpis.articles
    if a0 and (a0 - a1) / a0 > float(vcfg["max_article_drop"]):
        rep.errors.append(f"corpus shrank from {a0:,} to {a1:,} articles")


def _check_llm(manifest: Manifest | None, rep: Report) -> None:
    if manifest is None:
        return
    lab = manifest.labels
    if lab is not None and lab.provider == "llm" and lab.keywords:
        rep.warnings.append(f"{lab.keywords} topic names fell back to keywords (invalid replies, or transient errors past max_retries) "
                            "— run `atlas llm` again, then export")
    for s in manifest.llm:
        if s.task != "label" and s.fallback:
            rep.warnings.append(f"LLM {s.task}: {s.fallback} of {s.items} items use their fallback")


def validate_release(release_dir: str | Path, previous_dir: str | Path | None, vcfg: dict) -> Report:
    root = Path(release_dir)
    rep = Report(release_dir=str(root))
    models = _check_files(root, rep)
    _check_coherence(models, rep)
    manifest = models.get("manifest.json")
    _check_llm(manifest, rep)
    if previous_dir is None and manifest is not None and manifest.previous_release:
        cand = root.parent / manifest.previous_release
        previous_dir = cand if cand.exists() else None
    if previous_dir is not None and "topics.json" in models and "overview.json" in models:
        rep.previous_dir = str(previous_dir)
        _diff(models, Path(previous_dir), vcfg, rep)
    return rep


def render_report(rep: Report) -> str:
    status = {0: "OK", 1: "WARNINGS", 2: "ERRORS"}[rep.exit_code]
    lines = [f"atlas validate: {status} — {rep.release_dir}"]
    if rep.previous_dir:
        lines.append(f"  compared with {rep.previous_dir}")
    lines += [f"  stat  {k}: {v}" for k, v in rep.stats.items()]
    lines += [f"  ERROR {e}" for e in rep.errors] + [f"  WARN  {w}" for w in rep.warnings]
    return "\n".join(lines)
