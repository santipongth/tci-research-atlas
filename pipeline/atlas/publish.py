"""`atlas publish` — put a validated release on the static site (and, optionally, package it).

Validates first (refuses on errors, and on warnings unless allow_warnings). Then, with a site folder
(the web build output — any static host, opened from a sub-path):
  <site>/data/<release>/…        the contract v2 files, copied (a re-publish replaces that folder)
  <site>/data/latest.json        {release, path: "<release>/manifest.json", …} — the web reads it at run
                                 time relative to its BASE_URL; publishing a quarter = copying data, no rebuild.
                                 Moved only when the published release is the newest on the site (re-publishing
                                 an older quarter keeps it, with a warning; set_latest / --set-latest forces)
  <site>/atlas-offline.html      the single-file edition: the web build's offline-template.html with the
                                 release injected into <script type="application/json" id="atlas-data">
                                 by plain string replacement (Python only — no Node on the operator's machine);
                                 files in export.offline_exclude (default match.json, the largest) stay out of it —
                                 the offline /match page says it needs the web edition
  <site>/data/feeds/…            Atom feeds (atlas.feeds) when publish.site_url is set — releases.xml + one per
                                 topic of the newest release; latest.json then carries feeds: true (the offline
                                 edition does not: its feeds would be links to the site)
Older releases already in <site>/data/ stay (the web can compare quarters), and the earlier releases this one
builds on (manifest.previous_release, then its previous_release, …) that the site lacks are restored from
output/data/ — e.g. after `npm run build` emptied dist/data. A release folder already on the site is never
replaced by that restore; a previous release found nowhere is reported (the web then shows no change vs it).
With tarball=True also output/releases/atlas-data-<release>.tar.gz (deterministic: sorted members,
mtime 0, uid/gid 0, no gzip timestamp) + .sha256 + .notes.md, and the `gh release create` command is
printed for a human — never run.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import shutil
import tarfile
from pathlib import Path

from atlas.feeds import write_feeds
from atlas.schema.contract import Latest
from atlas.state import _checked, default_release, is_newest, known_releases
from atlas.validate import render_report, validate_release

OFFLINE_TEMPLATE, OFFLINE_HTML = "offline-template.html", "atlas-offline.html"
ALWAYS_OFFLINE_EXCLUDE = ("search", "galaxy.json")   # P4: tens–hundreds of MB at full scale — never inlined, whatever
                                                    # an older config.yaml lists in export.offline_exclude
_DATA_TAG = re.compile(r'(<script type="application/json" id="atlas-data">)(.*?)(</script>)', re.S)


class PublishRefused(RuntimeError):
    pass


def package_release(release_dir: str | Path, out_dir: str | Path) -> tuple[Path, Path]:
    root = Path(release_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tar_path = out / f"atlas-data-{root.name}.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for p in sorted(x for x in root.rglob("*") if x.is_file()):
            data = p.read_bytes()
            info = tarfile.TarInfo(f"{root.name}/{p.relative_to(root).as_posix()}")
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    with open(tar_path, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
        gz.write(buf.getvalue())
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    sha_path = tar_path.with_name(tar_path.name + ".sha256")
    sha_path.write_text(f"{digest}  {tar_path.name}\n", encoding="utf-8")
    return tar_path, sha_path


def release_notes(release_dir: str | Path) -> str:
    root = Path(release_dir)
    ov = json.loads((root / "overview.json").read_text(encoding="utf-8"))
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    k = ov["kpis"]
    lines = [f"# TCI Research Atlas — data {ov['release']}", "",
             f"- {k['articles']:,} articles · {k['topics']:,} topics · {k['groups']} groups · "
             f"{k['journals']:,} journals · {k['institutions']:,} institutions",
             f"- data through {ov['last_complete_year']} · schema {man['schema_version']} · "
             f"definition v{ov['definition_version']} · intervals {round(man.get('ci_level', 0.9) * 100)}% · "
             f"embedding `{man['embedding_model']}`",
             f"- previous release: {ov.get('previous_release') or '—'}", "", "## Status", ""]
    lines += [f"- {s}: {n}" for s, n in sorted(ov["status_counts"].items())]
    if ov.get("lineage_events"):
        lines += ["", "## Topic lineage", ""] + [f"- {e}: {n}" for e, n in sorted(ov["lineage_events"].items())]
    lines += ["", f"Files: {len(man['files']) + 1} (sha256 per file in manifest.json). Licence: CC BY 4.0.", ""]
    return "\n".join(lines)


DETAIL_FOLDERS = ("topics", "journals", "institutions")   # inlined in this order, as far as the byte budget goes
SLIM_KEEP = ("manifest.json", "overview.json", "topics.json", "taxonomy.json", "diff.json")


def offline_bundle(release_dir: str | Path, latest: dict, exclude=(), max_bytes: int | None = None) -> dict:
    """{latest, files: {relative path: parsed JSON}} — what atlas-offline.html carries; paths equal to (or inside
    a folder named by) an entry of `exclude` are left out. The top-level files always go in; the per-topic,
    per-journal and per-institution files follow until `max_bytes` of JSON is reached (None = no limit)."""
    root = Path(release_dir)
    skip = tuple(str(e).strip("/") for e in exclude)
    paths = [p for p in sorted(root.rglob("*.json"))
             if not any((rel := p.relative_to(root).as_posix()) == e or rel.startswith(f"{e}/") for e in skip)]

    def folder(p: Path) -> str:
        return p.relative_to(root).parts[0] if len(p.relative_to(root).parts) > 1 else ""
    top = [p for p in paths if folder(p) not in DETAIL_FOLDERS]
    files = {p.relative_to(root).as_posix(): json.loads(p.read_text(encoding="utf-8")) for p in top}
    used = sum(p.stat().st_size for p in top)
    left_out: dict[str, int] = {}
    for name in DETAIL_FOLDERS:
        for p in (p for p in paths if folder(p) == name):
            size = p.stat().st_size
            if max_bytes is not None and used + size > max_bytes:
                left_out[name] = left_out.get(name, 0) + 1
                continue
            files[p.relative_to(root).as_posix()] = json.loads(p.read_text(encoding="utf-8"))
            used += size
    if left_out:
        print("[publish] atlas-offline.html size budget reached — left out: "
              + ", ".join(f"{n} {k}/ files" for k, n in left_out.items()) + " (raise export.offline_max_mb)")
    return {"latest": latest, "files": files}


def slim_old_releases(site: Path, keep_full: int) -> list[str]:
    """Older releases on the site keep only what the web and the feeds read (SLIM_KEEP): the site must not grow by
    hundreds of MB every quarter. The newest `keep_full` releases are untouched. Returns the slimmed names."""
    data = site / "data"
    names = sorted((p.name for p in data.glob("*") if (p / "manifest.json").exists()), reverse=True)
    slimmed = []
    for name in names[keep_full:]:
        folder = data / name
        removed = False
        for p in sorted(folder.rglob("*"), reverse=True):
            rel = p.relative_to(folder).as_posix()
            if p.is_file() and rel not in SLIM_KEEP:
                p.unlink()
                removed = True
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
        if removed:
            slimmed.append(name)
    if slimmed:
        print(f"[publish] older release(s) {', '.join(slimmed)} slimmed to {', '.join(SLIM_KEEP)} (publish.keep_full_releases)")
    return slimmed


def inject_offline(template_html: str, bundle: dict) -> str:
    """Put the bundle into the data <script> of the template; '</' is escaped so the JSON cannot end it, and
    '<!--' so it cannot switch the HTML parser into the escaped script state (both stay valid JSON)."""
    payload = (json.dumps(bundle, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
               .replace("</", "<\\/").replace("<!--", "<\\u0021--"))
    out, n = _DATA_TAG.subn(lambda m: m.group(1) + payload + m.group(3), template_html, count=1)
    if n != 1:
        raise ValueError(f'{OFFLINE_TEMPLATE} has no <script type="application/json" id="atlas-data"> element')
    return out


def _site_latest(site: Path) -> str | None:
    try:
        return str(json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))["release"])
    except (FileNotFoundError, ValueError, KeyError, TypeError):
        return None


def _previous_of(folder: Path) -> str | None:
    try:
        return json.loads((folder / "manifest.json").read_text(encoding="utf-8")).get("previous_release")
    except (FileNotFoundError, ValueError, AttributeError):
        return None


def restore_previous(release_dir: Path, site: Path) -> list[str]:
    """Copy the chain of earlier releases (previous_release of previous_release …) that <site>/data lacks from the
    local output/data. Never replaces a folder already on the site; warns when a previous release is nowhere."""
    local, data, restored = release_dir.parent, site / "data", []
    seen, prev = {release_dir.name}, _previous_of(release_dir)
    while prev and prev not in seen:
        seen.add(prev)
        try:
            _checked(prev)                         # a manifest is data: never follow "../x"
        except ValueError:
            print(f"[publish] WARNING: previous_release {prev!r} is not a release name — not restored")
            break
        on_site, src = data / prev, local / prev
        if on_site.exists():                       # whatever is there stays (published earlier, maybe edited)
            folder = on_site
        elif (src / "manifest.json").exists():
            shutil.copytree(src, on_site)
            restored.append(prev)
            folder = on_site
        else:
            print(f"[publish] WARNING: previous release {prev} is not in {local} nor on the site — the web cannot "
                  f"show changes against it")
            break
        prev = _previous_of(folder)
    if restored:
        print(f"[publish] restored earlier release(s) {', '.join(restored)} from {local} (the web compares quarters)")
    return restored


def _mark_feeds(path: Path) -> None:
    """latest.json kept on another release (an older quarter was re-published): only say the feeds are there."""
    try:
        latest = Latest.model_validate_json(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return
    if not latest.feeds:
        latest.feeds = True
        path.write_text(json.dumps(latest.model_dump(mode="json", exclude_none=True), ensure_ascii=False),
                        encoding="utf-8")


def publish_site(release_dir: Path, site: Path, cfg: dict | None = None, set_latest: bool = False) -> dict:
    release = release_dir.name
    dst = site / "data" / release
    current = _site_latest(site)
    others = [p.name for p in (site / "data").glob("*") if (p / "manifest.json").exists() and p.name != release]
    others += [current] if current and current != release else []
    move = set_latest or current is None or is_newest(release, others, known_releases(cfg) if cfg else ())
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(release_dir, dst)
    restored = restore_previous(release_dir, site)
    pcfg = (cfg or {}).get("publish") or {}
    slimmed = slim_old_releases(site, int(pcfg.get("keep_full_releases", 1))) if move else []
    feeds = None
    if pcfg.get("site_url"):
        feeds = write_feeds(site, pcfg["site_url"], int(pcfg.get("feed_max_entries", 12)),
                            int(((cfg or {}).get("emerging") or {}).get("recent_window") or 0) or None)
    else:
        print("[publish] publish.site_url is not set — no Atom feeds written (set it to the public address of the "
              "site to get data/feeds/)")
    man = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    latest = Latest(release=release, path=f"{release}/manifest.json", generated_at=man["generated_at"],
                    feeds=True if feeds else None)
    latest_json = latest.model_dump(mode="json", exclude_none=True)
    offline_latest = {k: v for k, v in latest_json.items() if k != "feeds"}   # feeds live on the site, not in the file
    offline = None
    template = site / OFFLINE_TEMPLATE
    if not move:                                   # latest.json and the offline edition stay on the newest release
        print(f"[publish] WARNING: {release} is not the newest release on the site — latest.json still points at "
              f"{current} (atlas-offline.html unchanged); pass --set-latest to make {release} the latest")
        if feeds:
            _mark_feeds(site / "data" / "latest.json")
    elif template.exists():
        (site / "data" / "latest.json").write_text(json.dumps(latest_json, ensure_ascii=False), encoding="utf-8")
        exclude = tuple(dict.fromkeys([*(cfg["export"]["offline_exclude"] if cfg else ()), *ALWAYS_OFFLINE_EXCLUDE]))
        html = inject_offline(template.read_text(encoding="utf-8"),
                              offline_bundle(release_dir, offline_latest, exclude,
                                             int(cfg["export"]["offline_max_mb"]) * 1_000_000 if cfg else None))
        offline = site / OFFLINE_HTML
        offline.write_text(html, encoding="utf-8", newline="")     # same bytes on Windows and Linux
    else:
        (site / "data" / "latest.json").write_text(json.dumps(latest_json, ensure_ascii=False), encoding="utf-8")
        print(f"[publish] WARNING: {template} not found — build the web first (npm run build); "
              "the single-file offline edition was skipped")
    return {"site_data": str(dst), "latest": str(site / "data" / "latest.json"), "latest_moved": move,
            "restored": restored, "slimmed": slimmed, "feeds": feeds,
            "offline_html": str(offline) if offline else None}


def publish(cfg: dict, release: str | None = None, allow_warnings: bool = False, site: str | Path | None = None,
            tarball: bool = False, set_latest: bool = False) -> dict:
    """release None → pipeline.release, else the release work_dir was clustered for, else today's quarter."""
    try:
        release = _checked(release) if release else default_release(cfg)
    except ValueError as e:
        raise PublishRefused(str(e)) from e
    rel_dir = Path(cfg["pipeline"]["output_dir"]) / "data" / release
    rep = validate_release(rel_dir, None, cfg["validation"], cfg["pipeline"]["work_dir"])
    print(render_report(rep))
    if rep.exit_code == 2 or (rep.exit_code == 1 and not allow_warnings):
        raise PublishRefused(f"validation exit code {rep.exit_code} — fix the release (or pass --allow-warnings)")
    result: dict = {"release": release, "validation": rep.exit_code}
    if site is not None:
        result.update(publish_site(rel_dir, Path(site), cfg, set_latest))
    if tarball:
        out = Path(cfg["pipeline"]["output_dir"]) / "releases"
        tar_path, sha_path = package_release(rel_dir, out)
        notes = out / f"atlas-data-{release}.notes.md"
        notes.write_text(release_notes(rel_dir), encoding="utf-8")
        result.update(tarball=str(tar_path), sha256=str(sha_path), notes=str(notes),
                      gh_command=(f'gh release create data-{release} "{tar_path}" "{sha_path}" '
                                  f'--title "Atlas data {release}" --notes-file "{notes}"'))
    return result
