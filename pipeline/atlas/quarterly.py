"""`atlas quarterly`: the whole quarterly round in one command — corpus in, a site folder ready to upload out.

  1. config     runs/<release>/config.yaml = config.yaml + this round's corpus, release and journals.csv (archived)
  2. corpus     runs/<release>/corpus_manifest.json (files, sizes, sha256 of JSONL files) — what this round read
  3. profile    runs/<release>/profile.md — stops when more lines/files fail than input.max_error_ratio
  4. embed      embedding.provider api only: dry-run numbers, then `atlas embed` (retries forever, resumable)
  5. llm        LLM tasks on only: `atlas llm --dry-run` is shown and must be confirmed (or --yes) before paying
  6. run        `atlas run` (all steps) → runs/<release>/pipeline.log
  7. validate   exit 2 stops the round; exit 1 (warnings) continues unless --strict
  8. web        builds web/dist when it is missing (or --build-web): npm ci + npm run build (ATLAS_SITE_URL = publish.site_url)
  9. publish    `atlas publish --site web/dist`
 10. deploy     deploy/<release>/site/ (the whole site) + deploy/atlas-site-<release>.zip + deploy/atlas-data-<release>.zip
 11. summary    runs/<release>/summary.md — counts, timings, what to upload where
Every step is a separate `atlas` process with its own exit code; a failed round is resumed by running the same
command again (embeddings, LLM answers and the corpus profile are never paid for twice).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import yaml

from atlas.profile import detect_format
from atlas.sources.corpus_jsonl import corpus_files
from atlas.state import _checked, release_from_date, today

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "pipeline"
SAMPLE_PROVIDERS = ("fixture", "lite")


class RoundError(RuntimeError):
    """The round stopped; the message says why and what to do next."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def _say(msg: str) -> None:
    print(f"[quarterly] {msg}", flush=True)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def round_config(config: Path | None, release: str, corpus: Path | None) -> dict:
    """The user's config with this round's corpus (format detected from the folder), journals.csv and release."""
    from atlas.config import load_config

    cfg = load_config(config)
    if corpus is not None:
        cfg["input"]["path"] = str(Path(corpus).resolve())
    path = Path(cfg["input"]["path"])
    if not path.exists():
        raise RoundError(f"corpus not found: {path} — pass --corpus <folder> or set input.path in config.yaml", 2)
    if path.is_dir():
        cfg["input"]["format"] = detect_format(path)
        if (path / "journals.csv").is_file():
            cfg["journals"]["registry_path"] = str((path / "journals.csv").resolve())
    cfg["pipeline"]["release"] = release
    return cfg


def corpus_manifest(cfg: dict) -> dict:
    root = Path(cfg["input"]["path"])
    if cfg["input"]["format"] == "corpus_jsonl":
        files = [Path(f) for f in corpus_files(root, cfg["input"]["corpus_glob"])]
        extra = [root / "journals.csv"] if (root / "journals.csv").is_file() else []
        entries = [{"path": str(p.relative_to(root)).replace(os.sep, "/"), "bytes": p.stat().st_size,
                    "sha256": _sha256(p)} for p in files + extra]
        return {"format": "corpus_jsonl", "root": str(root), "files": entries,
                "bytes": sum(e["bytes"] for e in entries)}
    if root.is_dir():                                  # Markdown: hashing 500K small files is not worth the wait
        files = [p for p in root.glob(cfg["input"]["glob"]) if p.is_file()]
        return {"format": cfg["input"]["format"], "root": str(root), "count": len(files),
                "bytes": sum(p.stat().st_size for p in files)}
    return {"format": cfg["input"]["format"], "root": str(root), "bytes": root.stat().st_size, "sha256": _sha256(root)}


def _atlas(args: list[str], log: Path | None = None) -> int:
    """Run `python -m atlas <args>` in pipeline/, echoing its output (and appending it to `log`)."""
    cmd = [sys.executable, "-m", "atlas", *args]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    with subprocess.Popen(cmd, cwd=PIPELINE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                          text=True, encoding="utf-8", errors="replace", bufsize=1) as p:
        fh = log.open("a", encoding="utf-8") if log else None
        try:
            for line in p.stdout:                      # type: ignore[union-attr]
                sys.stdout.write(line)
                if fh:
                    fh.write(line)
        finally:
            if fh:
                fh.close()
    return p.returncode


def _npm() -> str:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise RoundError("Node.js (npm) is needed to build the web site once — install Node.js 24 or build web/dist "
                         "on another machine and copy it here", 2)
    return npm


def build_web(site_url: str | None, log: Path) -> None:
    web = ROOT / "web"
    npm = _npm()
    env = {**os.environ, **({"ATLAS_SITE_URL": site_url} if site_url else {})}
    with log.open("a", encoding="utf-8") as fh:
        for args in ([["ci"]] if not (web / "node_modules").is_dir() else []) + [["run", "build"]]:
            _say(f"web: npm {' '.join(args)}")
            r = subprocess.run([npm, *args], cwd=web, env=env, stdout=fh, stderr=subprocess.STDOUT)
            if r.returncode:
                raise RoundError(f"npm {' '.join(args)} failed (exit {r.returncode}) — see {log}")


def llm_enabled(cfg: dict) -> bool:
    return (cfg["labeling"]["provider"] == "llm" or cfg["narrative"]["provider"] == "llm"
            or cfg["methods"]["provider"] == "llm")


def preflight(cfg: dict) -> list[str]:
    """Warnings for keys that are not set (a key-less in-house server is fine, so these never stop the round)."""
    out = []
    if cfg["embedding"]["provider"] == "api":
        env = cfg["embedding"]["api"]["api_key_env"]
        if not os.environ.get(env):
            out.append(f"embedding.provider is api but {env} is not set (fine only for a server without keys)")
    if llm_enabled(cfg):
        for name, ep in cfg["llm"]["endpoints"].items():
            if ep["base_url"] and not os.environ.get(ep["api_key_env"]):
                out.append(f"llm endpoint {name}: {ep['api_key_env']} is not set")
    return out


def package(site: Path, release: str, deploy_dir: Path) -> dict:
    """deploy/<release>/site (copy of the whole site) + two zips; refuses a site whose latest release is sample data."""
    latest = json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))
    manifest = json.loads((site / "data" / latest["path"]).read_text(encoding="utf-8"))
    if manifest.get("embedding_provider") in SAMPLE_PROVIDERS:
        raise RoundError(f"the release on {site} was made with embedding provider "
                         f"{manifest['embedding_provider']!r} (tests only) — not packaged for the public site")
    target = deploy_dir / release / "site"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(site, target)
    full = shutil.make_archive(str(deploy_dir / f"atlas-site-{release}"), "zip", target)
    data_only = deploy_dir / release / "_data_only"
    if data_only.exists():
        shutil.rmtree(data_only)
    shutil.copytree(target / "data", data_only / "data")
    if (target / "atlas-offline.html").is_file():
        shutil.copy2(target / "atlas-offline.html", data_only / "atlas-offline.html")
    data_zip = shutil.make_archive(str(deploy_dir / f"atlas-data-{release}"), "zip", data_only)
    shutil.rmtree(data_only)
    return {"site": str(target), "site_zip": full, "data_zip": data_zip, "articles": manifest.get("counts", {})}


def _summary(release: str, cfg: dict, timings: list[tuple[str, float]], validate_code: int, pkg: dict | None,
             warnings: list[str]) -> str:
    counts = (pkg or {}).get("articles") or {}
    lines = [f"# รอบ {release}", "",
             f"- คลัง: `{cfg['input']['path']}` ({cfg['input']['format']})",
             f"- embedding: {cfg['embedding']['provider']} · LLM: {'on' if llm_enabled(cfg) else 'off'}",
             f"- atlas validate: exit {validate_code} (0 = ผ่าน, 1 = มีคำเตือน — อ่าน validate.txt)",
             *(f"- {k}: {v:,}" if isinstance(v, int) else f"- {k}: {v}" for k, v in counts.items()),
             "", "## เวลาแต่ละขั้น", "", "| ขั้น | นาที |", "|---|---|",
             *(f"| {name} | {sec / 60:.1f} |" for name, sec in timings), ""]
    if warnings:
        lines += ["## คำเตือน", "", *(f"- {w}" for w in warnings), ""]
    if pkg:
        lines += ["## เผยแพร่", "",
                  f"- ทั้งเว็บ (ครั้งแรก หรือเมื่อโค้ดเว็บเปลี่ยน): อัปโหลดทุกไฟล์ใน `{pkg['site']}` "
                  f"หรือแตก `{Path(pkg['site_zip']).name}` ที่โฟลเดอร์รากของ host",
                  f"- เฉพาะข้อมูล (รอบถัดไป): แตก `{Path(pkg['data_zip']).name}` ทับโฟลเดอร์ของเว็บบน host "
                  "(ได้ data/ ใหม่ + atlas-offline.html; รอบเก่ายังอยู่ใน data/)",
                  "- GitHub Pages: `bash scripts/package_release.sh --upload` แล้ว Actions → Pages → data_release", ""]
    return "\n".join(lines)


def run_round(config: Path | None, corpus: Path | None, release: str | None, yes: bool, strict: bool,
              build: bool, prepare: bool, runs_dir: Path, deploy_dir: Path, site: Path,
              confirm: Callable[[str], bool]) -> int:
    release = _checked(release or release_from_date(today()))
    cfg = round_config(config, release, corpus)
    rdir = runs_dir / release
    rdir.mkdir(parents=True, exist_ok=True)
    rcfg = rdir / "config.yaml"
    rcfg.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    c = ["-c", str(rcfg)]
    timings: list[tuple[str, float]] = []
    warnings = preflight(cfg)
    for w in warnings:
        _say(f"WARNING: {w}")

    def step(name: str, fn: Callable[[], int | None]) -> int:
        t0 = time.monotonic()
        _say(f"== {name} ==")
        code = fn() or 0
        timings.append((name, time.monotonic() - t0))
        return code

    _say(f"round {release} · corpus {cfg['input']['path']} ({cfg['input']['format']}) · config {rcfg}")
    def write_manifest() -> None:
        (rdir / "corpus_manifest.json").write_text(json.dumps(corpus_manifest(cfg), ensure_ascii=False, indent=2),
                                                   encoding="utf-8")

    step("corpus", write_manifest)
    if cfg["input"]["format"] == "table":           # one table file: atlas profile reads folders only
        code = 0
    else:
            code = step("profile", lambda: _atlas(["profile", cfg["input"]["path"], "--format", cfg["input"]["format"],
                                               "--md", str(rdir / "profile.md"), "--out", str(rdir / "profile.json"),
                                               "--workers", str(cfg["input"]["workers"]),
                                               "--max-error-ratio", str(cfg["input"]["max_error_ratio"])],
                                              rdir / "profile.log"))
    if code:
        raise RoundError(f"the corpus has more unreadable lines/files than input.max_error_ratio — fix them "
                         f"(list in {rdir / 'profile.md'}) and run again")
    if prepare:
        _say(f"prepared: {rcfg} — first big embedding: uv run atlas embed -c {rcfg} --check / --dry-run / --background")
        return 0

    if cfg["embedding"]["provider"] == "api":
        if step("embed (dry run)", lambda: _atlas(["embed", *c, "--dry-run"], rdir / "embed_dryrun.txt")):
            raise RoundError("atlas embed --dry-run failed — see the message above", 2)
        code = step("embed", lambda: _atlas(["embed", *c], rdir / "embed.log"))
        if code:
            raise RoundError(f"atlas embed stopped (exit {code}) — fix the cause shown above, then run the same "
                             f"command again: it resumes where it stopped", code)

    if llm_enabled(cfg):
        if step("llm (dry run)", lambda: _atlas(["llm", *c, "--dry-run"], rdir / "llm_dryrun.txt")):
            raise RoundError("atlas llm --dry-run failed — see the message above", 2)
        if not yes and not confirm(f"pay for the LLM calls estimated above (details in {rdir / 'llm_dryrun.txt'})?"):
            raise RoundError("LLM cost not confirmed — run again with --yes, or turn the LLM tasks off", 2)

    code = step("run", lambda: _atlas(["run", *c], rdir / "pipeline.log"))
    if code:
        raise RoundError(f"atlas run stopped (exit {code}) — see {rdir / 'pipeline.log'}; running the same command "
                         f"again resumes (paid work is cached)", code)
    validate_code = step("validate", lambda: _atlas(["validate", *c], rdir / "validate.txt"))
    if validate_code >= 2 or (strict and validate_code):
        raise RoundError(f"atlas validate exit {validate_code}: this release must not be published — "
                         f"read {rdir / 'validate.txt'}", 2)

    if build or not (site / "index.html").is_file() or not (site / "offline-template.html").is_file():
        step("web build", lambda: build_web(cfg["publish"]["site_url"], rdir / "web_build.log"))
    if step("publish", lambda: _atlas(["publish", *c, "--site", str(site)], rdir / "publish.log")):
        raise RoundError(f"atlas publish failed — see {rdir / 'publish.log'}")
    pkg: dict = {}
    step("deploy package", lambda: pkg.update(package(site, release, deploy_dir)))

    out = Path(cfg["pipeline"]["output_dir"])
    for f in out.glob("*"):
        if f.is_file():
            shutil.copy2(f, rdir / f.name)
    text = _summary(release, cfg, timings, validate_code, pkg, warnings)
    (rdir / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    _say(f"done — upload {pkg['site']} (or a zip in {deploy_dir}); the round is archived in {rdir}")
    return 0
