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
                                 by plain string replacement (Python only — no Node on the operator's machine)
Older releases already in <site>/data/ stay (the web can compare quarters).
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

from atlas.schema.contract import Latest
from atlas.state import _checked, default_release, is_newest, known_releases
from atlas.validate import render_report, validate_release

OFFLINE_TEMPLATE, OFFLINE_HTML = "offline-template.html", "atlas-offline.html"
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


def offline_bundle(release_dir: str | Path, latest: dict) -> dict:
    """{latest, files: {relative path: parsed JSON}} — what atlas-offline.html carries."""
    root = Path(release_dir)
    files = {p.relative_to(root).as_posix(): json.loads(p.read_text(encoding="utf-8"))
             for p in sorted(root.rglob("*.json"))}
    return {"latest": latest, "files": files}


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
    man = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    latest = Latest(release=release, path=f"{release}/manifest.json", generated_at=man["generated_at"])
    latest_json = latest.model_dump(mode="json")
    offline = None
    template = site / OFFLINE_TEMPLATE
    if not move:                                   # latest.json and the offline edition stay on the newest release
        print(f"[publish] WARNING: {release} is not the newest release on the site — latest.json still points at "
              f"{current} (atlas-offline.html unchanged); pass --set-latest to make {release} the latest")
    elif template.exists():
        (site / "data" / "latest.json").write_text(json.dumps(latest_json, ensure_ascii=False), encoding="utf-8")
        html = inject_offline(template.read_text(encoding="utf-8"), offline_bundle(release_dir, latest_json))
        offline = site / OFFLINE_HTML
        offline.write_text(html, encoding="utf-8", newline="")     # same bytes on Windows and Linux
    else:
        (site / "data" / "latest.json").write_text(json.dumps(latest_json, ensure_ascii=False), encoding="utf-8")
        print(f"[publish] WARNING: {template} not found — build the web first (npm run build); "
              "the single-file offline edition was skipped")
    return {"site_data": str(dst), "latest": str(site / "data" / "latest.json"), "latest_moved": move,
            "offline_html": str(offline) if offline else None}


def publish(cfg: dict, release: str | None = None, allow_warnings: bool = False, site: str | Path | None = None,
            tarball: bool = False, set_latest: bool = False) -> dict:
    """release None → pipeline.release, else the release work_dir was clustered for, else today's quarter."""
    try:
        release = _checked(release) if release else default_release(cfg)
    except ValueError as e:
        raise PublishRefused(str(e)) from e
    rel_dir = Path(cfg["pipeline"]["output_dir"]) / "data" / release
    rep = validate_release(rel_dir, None, cfg["validation"])
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
