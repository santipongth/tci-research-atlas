"""`atlas validate` — check one release folder before it is published.

1. integrity  manifest.json parses; every listed file exists with the listed size and sha256;
              JSON files on disk that the manifest does not list → warning
2. schema     every file validates against its pydantic model (atlas/schema/contract.py)
3. coherence  unique topic ids; one topics/<id>.json per topic; series and edges only name known
              topics; every topic's group exists in taxonomy.json; KPI topic count matches;
              editors' modules (2.1): unique journal ids with one journals/<id>.json each, peers / topic
              journal links / match journals name known journals, every topic id in journals, methods,
              diff (incl. restructured / merged_into) and match is a topic of this release (retired ones
              are not); executives' modules (2.2): unique institution ids with one institutions/<id>.json each,
              edges / partners / suggestions / province tops / topic institution links / concentration tops
              name published institutions, every topic id in sdg, global and gaps is a topic of this release,
              gaps' fields are taxonomy groups; files above
              validation.max_file_bytes → warning (static hosts cap single files)
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

from atlas.privacy import scan_release
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


def _check_files(root: Path, rep: Report, max_bytes: int = 50_000_000) -> dict[str, object]:
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
        if len(data) > max_bytes:
            rep.warnings.append(f"{entry.path}: {len(data):,} bytes > validation.max_file_bytes ({max_bytes:,})")
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


VOCAB_WARN_BYTES = 8_000_000      # search/vocab.json is downloaded whole before the first search


def _check_research(models: dict, root: Path, rep: Report) -> None:
    """P4 cross-checks the per-file schemas cannot see: the search index, its article rows and the galaxy must agree
    with each other and with topics.json — a broken search or galaxy must not pass as a valid release."""
    meta = models.get("search/meta.json")
    galaxy = models.get("galaxy.json")
    topics = models.get("topics.json")
    topic_ids = {t.id for t in topics.topics} if topics is not None else None
    if meta is not None:
        want = -(-meta.n_docs // meta.docs_per_shard) if meta.docs_per_shard else 0
        if meta.doc_shards != want:
            rep.errors.append(f"search/meta.json: {meta.doc_shards} doc shards for {meta.n_docs:,} articles at "
                              f"{meta.docs_per_shard} per shard (expected {want})")
        rows = 0
        bad_topic = 0
        for i in range(meta.doc_shards):
            shard = models.get(f"search/docs-{i:03d}.json")
            if shard is None:
                rep.errors.append(f"search/docs-{i:03d}.json: missing or invalid (search/meta.json lists {meta.doc_shards} shards)")
                continue
            if shard.start != i * meta.docs_per_shard:
                rep.errors.append(f"search/docs-{i:03d}.json: starts at ordinal {shard.start}, expected {i * meta.docs_per_shard}")
            rows += len(shard.docs)
            if topic_ids is not None:
                bad_topic += sum(1 for d in shard.docs if d[5] is not None and d[5] not in topic_ids)
        if rows != meta.n_docs:
            rep.errors.append(f"search: the doc shards hold {rows:,} rows, search/meta.json says {meta.n_docs:,} articles")
        if bad_topic:
            rep.errors.append(f"search: {bad_topic:,} article rows name a topic that is not in topics.json")
        for i in range(meta.index_shards):
            if f"search/idx-{i:03d}.json" not in models:
                rep.errors.append(f"search/idx-{i:03d}.json: missing or invalid (search/meta.json lists {meta.index_shards} index shards)")
        vocab = models.get("search/vocab.json")
        if vocab is not None and len(vocab.tokens) != meta.n_tokens:
            rep.errors.append(f"search/vocab.json: {len(vocab.tokens):,} tokens, search/meta.json says {meta.n_tokens:,}")
        vfile = root / "search" / "vocab.json"
        if vfile.exists() and vfile.stat().st_size > VOCAB_WARN_BYTES:
            rep.warnings.append(f"search/vocab.json is {vfile.stat().st_size / 1e6:.1f} MB and is downloaded whole before the first "
                                f"search — consider search.min_df: 2")
        rep.stats["search"] = f"{meta.n_docs:,} articles · {meta.n_tokens:,} tokens · {meta.doc_shards} doc shards"
    if galaxy is not None:
        if meta is not None and galaxy.n != meta.n_docs:
            rep.errors.append(f"galaxy.json has {galaxy.n:,} points but search/meta.json has {meta.n_docs:,} articles")
        if topic_ids is not None and not set(galaxy.topics) <= topic_ids:
            rep.errors.append("galaxy.json names topics that are not in topics.json")


def _unknown(ids, known: set[str]) -> list[str]:
    return sorted({i for i in ids if i not in known})


def _check_editors(models: dict, rep: Report) -> None:
    """Cross-file references of the P2 modules (journals, methods, diff, match)."""
    topics = models.get("topics.json")
    if topics is None:
        return
    known = {t.id for t in topics.topics}
    jf = models.get("journals.json")
    jids: set[str] | None = None
    if jf is not None:
        ids = [j.id for j in jf.journals]
        jids = set(ids)
        if len(jids) != len(ids):
            rep.errors.append("journals.json: duplicate journal ids")
        missing = [i for i in ids if f"journals/{i}.json" not in models]
        if missing:
            rep.errors.append(f"{len(missing)} journals have no valid journals/<id>.json (e.g. {missing[0]})")
        if bad := _unknown((s.topic for s in jf.special_issue), known):
            rep.errors.append(f"journals.json: special-issue topics not in topics.json: {bad[:5]}")
    for path, m in models.items():
        if path.startswith("journals/"):
            refs = [t.topic for t in m.topics] + [s.topic for s in m.gained + m.lost] + [o.topic for o in m.opportunities]
            if bad := _unknown(refs, known):
                rep.errors.append(f"{path}: topics not in topics.json: {bad[:5]}")
            if jids is not None and (bad := _unknown((p.id for p in m.peers), jids)):
                rep.errors.append(f"{path}: peers not in journals.json: {bad[:5]}")
        elif path.startswith("topics/") and jids is not None:
            if bad := _unknown((j.id for j in m.journals if j.id), jids):
                rep.errors.append(f"{path}: journal links not in journals.json: {bad[:5]}")
    if (mf := models.get("methods.json")) is not None and (bad := _unknown((t.topic for t in mf.topics), known)):
        rep.errors.append(f"methods.json: topics not in topics.json: {bad[:5]}")
    if (df := models.get("diff.json")) is not None:
        refs = ([t.topic for t in df.new_topics] + [c.topic for c in df.status_changes] + [m.topic for m in df.movers]
                + [r.topic for r in df.restructured] + [r.merged_into for r in df.retired if r.merged_into])
        if bad := _unknown(refs, known):
            rep.errors.append(f"diff.json: topics not in topics.json: {bad[:5]}")
        if still := sorted({r.topic for r in df.retired} & known):
            rep.errors.append(f"diff.json: retired topics still in topics.json: {still[:5]}")
    if (mx := models.get("match.json")) is not None:
        if bad := _unknown((t.id for t in mx.topics), known):
            rep.errors.append(f"match.json: topics not in topics.json: {bad[:5]}")
        refs = [t for j in mx.journals for t in j.topics]
        if bad := _unknown(refs, known):
            rep.errors.append(f"match.json: journal topics not in topics.json: {bad[:5]}")
        if jids is not None and (bad := _unknown((j.id for j in mx.journals), jids)):
            rep.errors.append(f"match.json: journals not in journals.json: {bad[:5]}")


def _check_executives(models: dict, rep: Report) -> None:
    """Cross-file references of the P3 modules (institutions, regions, sdg, global, gaps)."""
    topics = models.get("topics.json")
    if topics is None:
        return
    known = {t.id for t in topics.topics}
    groups = {g.id for g in models["taxonomy.json"].groups} if "taxonomy.json" in models else None
    inf = models.get("institutions.json")
    iids: set[str] | None = None
    if inf is not None:
        ids = [i.id for i in inf.institutions]
        iids = set(ids)
        if len(iids) != len(ids):
            rep.errors.append("institutions.json: duplicate institution ids")
        missing = [i for i in ids if f"institutions/{i}.json" not in models]
        if missing:
            rep.errors.append(f"{len(missing)} institutions have no valid institutions/<id>.json (e.g. {missing[0]})")
        if bad := _unknown((x for e in inf.edges for x in (e.a, e.b)), iids):
            rep.errors.append(f"institutions.json: edges name unknown institutions: {bad[:5]}")
    for path, m in models.items():
        if path.startswith("institutions/"):
            if bad := _unknown([t.topic for t in m.topics] + [t for s in m.suggested for t in s.topics], known):
                rep.errors.append(f"{path}: topics not in topics.json: {bad[:5]}")
            if iids is not None and (bad := _unknown([p.id for p in m.partners] + [s.id for s in m.suggested], iids)):
                rep.errors.append(f"{path}: institutions not in institutions.json: {bad[:5]}")
        elif path.startswith("topics/") and iids is not None:
            if bad := _unknown((i.id for i in m.institutions if i.id), iids):
                rep.errors.append(f"{path}: institution links not in institutions.json: {bad[:5]}")
    if (rf := models.get("regions.json")) is not None and iids is not None:
        if bad := _unknown((i for p in rf.provinces for i in p.top), iids):
            rep.errors.append(f"regions.json: institutions not in institutions.json: {bad[:5]}")
    if (sf := models.get("sdg.json")) is not None and (bad := _unknown((t for g in sf.goals for t in g.topics), known)):
        rep.errors.append(f"sdg.json: topics not in topics.json: {bad[:5]}")
    if (gf := models.get("global.json")) is not None and (
            bad := _unknown((t for s in gf.subfields for t in s.topics), known)):
        rep.errors.append(f"global.json: topics not in topics.json: {bad[:5]}")
    if (gp := models.get("gaps.json")) is not None:
        refs = ([f.topic for f in gp.few_institutions] + [x for b in gp.bridges for x in (b.a, b.b)]
                + [t for w in gp.world for t in w.topics] + [c.id for c in gp.concentration if c.scope == "topic"])
        if bad := _unknown(refs, known):
            rep.errors.append(f"gaps.json: topics not in topics.json: {bad[:5]}")
        if groups is not None and (bad := _unknown((c.id for c in gp.concentration if c.scope == "group"), groups)):
            rep.errors.append(f"gaps.json: fields not in taxonomy.json: {bad[:5]}")
        if iids is not None and (bad := _unknown((c.top for c in gp.concentration
                                                  if c.kind == "institution" and c.top), iids)):
            rep.errors.append(f"gaps.json: institutions not in institutions.json: {bad[:5]}")


def _diff(models: dict, prev_root: Path, vcfg: dict, rep: Report) -> None:
    try:
        raw_topics = _load(prev_root / "topics.json")["topics"]
        prev_overview = _load(prev_root / "overview.json")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        rep.warnings.append(f"previous release at {prev_root} is unreadable ({e}) — diff skipped")
        return
    prev_topics = {t["id"]: t for t in raw_topics if isinstance(t, dict) and "id" in t
                   and isinstance(t.get("size"), int | float) and "status" in t}
    if len(prev_topics) < len(raw_topics):
        rep.warnings.append(f"{len(raw_topics) - len(prev_topics)} entries of the previous topics.json lack "
                            "id/size/status — skipped in the diff")
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


def validate_release(release_dir: str | Path, previous_dir: str | Path | None, vcfg: dict,
                     work_dir: str | Path | None = None) -> Report:
    """Checks of one release folder. With `work_dir` (the pipeline work folder) the PDPA scan also looks for author
    names inside organisation strings (atlas.privacy)."""
    root = Path(release_dir)
    rep = Report(release_dir=str(root))
    models = _check_files(root, rep, int(vcfg.get("max_file_bytes", 50_000_000)))
    _check_coherence(models, rep)
    _check_editors(models, rep)
    _check_executives(models, rep)
    _check_research(models, root, rep)
    rep.errors += scan_release(root, work_dir)
    manifest = models.get("manifest.json")
    _check_llm(manifest, rep)
    if manifest is not None and manifest.release != root.name:
        rep.errors.append(f"manifest.release {manifest.release!r} does not match the folder name {root.name!r}")
    if previous_dir is None and manifest is not None and manifest.previous_release:
        cand = root.parent / manifest.previous_release
        if cand.exists():
            previous_dir = cand
        else:
            rep.warnings.append(f"previous release {manifest.previous_release} not found — diff skipped")
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
