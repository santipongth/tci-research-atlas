"""`atlas` command-line interface. UTF-8 safe on Windows consoles.

Commands are added by later modules: run, synth, profile, schema.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from atlas.console import use_utf8_stdio

use_utf8_stdio()

app = typer.Typer(help="TCI Research Atlas pipeline", no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """TCI Research Atlas pipeline."""


@app.command()
def version() -> None:
    """Print the pipeline version."""
    from atlas import __version__

    typer.echo(__version__)


@app.command()
def synth(
    out: Path = typer.Option(..., help="output folder for the synthetic .md corpus"),
    n: int = typer.Option(20_000, help="approximate number of articles"),
    seed: int = typer.Option(7),
) -> None:
    """Generate a synthetic ThaiJO-style corpus with planted trends (+ _truth.csv)."""
    from atlas.synth import generate

    truth = generate(out, n=n, seed=seed)
    typer.echo(f"wrote {len(truth):,} articles → {out}")


@app.command()
def profile(
    path: Path = typer.Argument(..., help="corpus folder: articles/*.jsonl[.gz] (corpus format 1.0) or ThaiJO .md files"),
    out: Path = typer.Option(None, help="write the JSON report here"),
    md: Path = typer.Option(None, help="write a Markdown report here"),
    fmt: str = typer.Option("auto", "--format", help="auto | corpus_jsonl | thaijo_md"),
    pattern: str = typer.Option(None, help="file pattern (default articles/**/*.jsonl* or **/*.md)"),
    workers: int = typer.Option(1),
    max_error_ratio: float = typer.Option(0.01, help="exit 1 when more files/lines than this share fail to parse "
                                                     "(same as input.max_error_ratio)"),
    aliases_todo: Path = typer.Option(None, help="write the most frequent affiliations no institutions_aliases.csv "
                                                 "row covers yet (a CSV to fill in)"),
) -> None:
    """Corpus quality report — run before the pipeline on every new corpus. Exit 1 when too many lines/files are
    unreadable or a companion file (journals.csv, institutions_aliases.csv, province_population.csv) needs fixing."""
    import json

    from atlas.profile import problems, profile_corpus, render_markdown

    if fmt not in ("auto", "corpus_jsonl", "thaijo_md"):
        raise typer.BadParameter("--format must be auto, corpus_jsonl or thaijo_md")
    report = profile_corpus(path, pattern, workers, max_error_ratio, fmt, aliases_todo=aliases_todo)
    if out:
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    text = render_markdown(report)
    if md:
        md.write_text(text, encoding="utf-8")
    typer.echo(text)
    found = problems(report, max_error_ratio)
    if found:
        typer.echo("[profile] fix before the hand-over:\n" + "\n".join(f"  - {x}" for x in found), err=True)
        raise typer.Exit(1)
    typer.echo("[profile] OK — nothing to fix")


@app.command()
def schema(
    out: Path = typer.Option(Path("../web/src/data/contract.schema.json"), help="where to write the JSON Schema"),
) -> None:
    """Write the data-contract v2 JSON Schema (then run `npm run gen:types` in web/)."""
    from atlas.schema.contract import write_json_schema

    typer.echo(f"wrote {write_json_schema(out)}")


@app.command("run")
def run_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    step: list[str] = typer.Option(None, "--step", "-s", help="run only these steps, repeatable, in order"),
) -> None:
    """Run the batch pipeline (all steps, or the given --step list)."""
    from atlas.config import load_config

    raise typer.Exit(_run_guarded(load_config(config), step or None, config, tag="run", resume="run"))


# ---------- long embedding run: atlas embed / status / embed-status / embed-stop
EXIT_FAILED, EXIT_CONFIG, EXIT_LOCKED, EXIT_STOPPED = 1, 2, 3, 130


def _cfg_arg(config: Path | None) -> str:
    return str(config) if config else "config.yaml"


def _lock_stale(cfg: dict) -> float:
    """lock_stale_seconds of the provider in use (api/local; 300 otherwise) — when `status` calls a run hung."""
    provider = cfg["embedding"]["provider"]
    return float((cfg["embedding"].get(provider) or {}).get("lock_stale_seconds") or 300)


def _ensure_docs(cfg: dict) -> None:
    work = Path(cfg["pipeline"]["work_dir"])
    if not ((work / "02_docs.parquet").exists() or (work / "02_docs.pkl").exists()):
        typer.echo("[embed] work/02_docs not found — running ingest + preprocess first")
        from atlas.pipeline import run

        run(cfg, ["ingest", "preprocess"])


def _run_guarded(cfg: dict, steps: list[str] | None, config: Path | None, ensure_docs: bool = False,
                 tag: str = "embed", resume: str = "embed") -> int:
    """Run pipeline steps; map the long-run outcomes to exit codes (0 ok, 1 failed, 2 config, 3 locked, 130 stopped).
    `tag` prefixes the messages ([embed] / [llm] / [run]); `resume` names the command that continues a stopped run.

    After a second Ctrl-C abandoned in-flight requests (the exception carries `abandoned`), EVERY outcome
    exits the process at once (os._exit, after flushing) instead of waiting up to request_timeout for the
    abandoned worker threads — keeping that outcome's exit code."""
    from atlas.api_http import ApiConfigError, TransientGaveUp
    from atlas.embed_runner import StoreSaveFailed
    from atlas.jobs import LockHeld, LockUnsupported, RunStopped
    from atlas.llm_runner import RESUME_COMMAND
    from atlas.pipeline import run
    from atlas.state import ReleaseMismatch

    def done(code: int, e: BaseException) -> int:
        if getattr(e, "abandoned", 0):
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(code)
        return code

    token = RESUME_COMMAND.set(f"uv run atlas {resume} -c {_cfg_arg(config)}")   # named by `atlas status`
    try:
        if ensure_docs:
            _ensure_docs(cfg)
        run(cfg, steps)
    except StoreSaveFailed as e:
        typer.echo(f"[{tag}] \N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA UE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER NGO NGU} store \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO} — \N{THAI CHARACTER PHO PHUNG}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER NO NU} journal.bin \N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER BO BAIMAI}; \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER SARA U} (\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER THANTHAKHAT}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER MO MA} / \N{THAI CHARACTER SARA O}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER DO DEK} "
                   f"index.parquet \N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU}) \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NGO NGU} / could not save into the store: {e}\n"
                   f"  run the same command again: uv run atlas {resume} -c {_cfg_arg(config)}", err=True)
        return done(EXIT_FAILED, e)
    except LockUnsupported as e:
        typer.echo(f"[{tag}] ERROR: {e}", err=True)
        return done(EXIT_CONFIG, e)
    except ReleaseMismatch as e:                     # nothing was written for the wrong release
        typer.echo(f"[{tag}] ERROR: {e}", err=True)
        return done(EXIT_CONFIG, e)
    except ApiConfigError as e:
        typer.echo(f"[{tag}] ERROR — \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI THO} config \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK} / fix the config and rerun:\n  {e}", err=True)
        return done(EXIT_CONFIG, e)
    except LockHeld as e:
        typer.echo(f"[{tag}] {e}\n  \N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA A} / status: uv run atlas status -c {_cfg_arg(config)}", err=True)
        return done(EXIT_LOCKED, e)
    except (RunStopped, KeyboardInterrupt) as e:
        typer.echo(f"[{tag}] \N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER CHO CHAN} / stopped before completion{': ' + str(e) if str(e) else ''}\n"
                   f"  \N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG} / resume: uv run atlas {resume} -c {_cfg_arg(config)}", err=True)
        return done(EXIT_STOPPED, e)
    except TransientGaveUp as e:
        where = ("embedding.api.max_retries is set" if tag == "embed"      # `atlas embed`: P0 text, unchanged
                 else "max_retries is set in embedding.api / llm.endpoints")
        typer.echo(f"[{tag}] ERROR: {e}\n  ({where}; null = retry forever)", err=True)
        return done(EXIT_FAILED, e)
    except BaseException as e:                       # unexpected: the usual traceback, but never wait for
        if getattr(e, "abandoned", 0):               # abandoned worker threads
            import traceback

            traceback.print_exc()
            return done(EXIT_FAILED, e)
        raise
    finally:
        RESUME_COMMAND.reset(token)
    return 0


@app.command("embed")
def embed_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    check: bool = typer.Option(False, "--check", help="send one test request: model, vector size, latency "
                                                      "(checks the key and base_url before a long run)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="count cached / to embed / characters / ~tokens — "
                                                          "no API call"),
    background: bool = typer.Option(False, "--background", help="run detached from this window (you may close it); "
                                                                "log in <store>/run.log"),
    concurrency: int = typer.Option(None, "--concurrency", min=1, help="override embedding.api.concurrency"),
) -> None:
    """Embed the whole corpus into state_dir once (API or local model). Retries server errors forever,
    stops at once on config errors, resumes with no re-paid work: just run the same command again.

    Exit codes: 0 done, 2 config/permanent error, 3 another run holds the store, 130 stopped (resume later).
    """
    from atlas.config import load_config

    cfg = load_config(config)
    if concurrency:
        if cfg["embedding"]["provider"] == "api":
            cfg["embedding"]["api"]["concurrency"] = concurrency
        else:
            typer.echo("[embed] --concurrency applies to embedding.provider: api only — ignored")
    if check:
        raise typer.Exit(_embed_check(cfg))
    if dry_run:
        raise typer.Exit(_embed_dry_run(cfg))
    if background:
        raise typer.Exit(_embed_background(cfg, config, concurrency))
    raise typer.Exit(_run_guarded(cfg, ["embed"], config, ensure_docs=True))


def _embed_check(cfg: dict) -> int:
    from atlas.api_http import ApiConfigError, TransientGaveUp
    from atlas.embed import store_root
    from atlas.embed_api import ApiEmbedder, dim_mismatch
    from atlas.embed_store import EmbeddingStore, store_dir

    if cfg["embedding"]["provider"] != "api":
        typer.echo("[check] --check \N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER CHO CHANG}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER BO BAIMAI} embedding.provider: api \N{THAI CHARACTER SARA E}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NO NU} / --check needs embedding.provider: api",
                   err=True)
        return EXIT_CONFIG
    try:
        emb = ApiEmbedder(cfg)
        info = emb.check()
    except ApiConfigError as e:
        typer.echo(f"[check] FAILED — \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI THO} config / fix the config:\n  {e}", err=True)
        return EXIT_CONFIG
    except TransientGaveUp as e:
        typer.echo(f"[check] FAILED — server \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER BO BAIMAI} / the server is not answering: {e}", err=True)
        return EXIT_CONFIG
    key = "set" if info["api_key_set"] else "NOT set (no Authorization header sent)"
    typer.echo(f"[check] OK  model={info['model']}  dim={info['dim']}  latency={info['latency_ms']:.0f} ms")
    typer.echo(f"[check] base_url={info['base_url']}  store_id={info['store_id']}  ${info['api_key_env']}: {key}")
    if store_dir(store_root(cfg), info["store_id"]).exists():
        store = EmbeddingStore(store_root(cfg), info["store_id"])
        if store.dim is not None and store.dim != info["dim"]:
            typer.echo(f"[check] {dim_mismatch(store.dim, info['dim'], info['store_id'])}", err=True)
            return EXIT_CONFIG
        typer.echo(f"[check] store: {len(store):,} vectors already in {store.dir}")
    return 0


def _embed_dry_run(cfg: dict) -> int:
    import re

    from atlas.embed import runner_cfg, store_id_for, store_root
    from atlas.embed_runner import JOURNAL, pack_batches, read_journal
    from atlas.embed_store import EmbeddingStore, store_dir, text_key
    from atlas.io_utils import read_table

    _ensure_docs(cfg)
    texts = read_table(Path(cfg["pipeline"]["work_dir"]) / "02_docs.parquet")["doc_text"].tolist()
    sid = store_id_for(cfg)
    row = "  {:<15}: {}".format
    typer.echo(f"[dry-run] provider={cfg['embedding']['provider']}  store_id={sid}  (no API call is made)")
    typer.echo(row("documents", f"{len(texts):,}"))
    if sid is None:
        typer.echo("  provider lite: TF-IDF+SVD on this machine, nothing to pay and nothing stored")
        return 0
    uniq: dict[str, str] = {}
    for k, t in zip((text_key(sid, t) for t in texts), texts):
        uniq.setdefault(k, t)
    sdir = store_dir(store_root(cfg), sid)
    store = EmbeddingStore(store_root(cfg), sid) if sdir.exists() else None
    journaled = set(read_journal(sdir / JOURNAL)[0]) if (sdir / JOURNAL).exists() else set()
    todo = [k for k in uniq if not (store and store.has(k)) and k not in journaled]
    thai = re.compile(f"[{chr(0x0E00)}-{chr(0x0E7F)}]")
    chars = sum(len(uniq[k]) for k in todo)
    thai_chars = sum(len(thai.findall(uniq[k])) for k in todo)
    rc = runner_cfg(cfg)
    n_req = len(pack_batches([len(uniq[k]) for k in todo], int(rc.get("batch_size") or 32), rc.get("max_batch_chars")))
    cached = len(uniq) - len(todo)
    typer.echo(row("unique texts", f"{len(uniq):,}"))
    typer.echo(row("cached", f"{cached:,}" + (f" (incl. {len(journaled):,} in journal.bin)" if journaled else "")))
    typer.echo(row("to embed", f"{len(todo):,}"))
    typer.echo(row("characters", f"{chars:,} (Thai {thai_chars:,})"))
    typer.echo(row("~tokens", f"{round(thai_chars + 0.3 * (chars - thai_chars)):,} "
                              f"(rough: Thai ≈ 1 token/char, other ≈ 0.3)"))
    typer.echo(row("requests", f"~{n_req:,} (batch_size {rc.get('batch_size')}, "
                               f"max_batch_chars {rc.get('max_batch_chars')})"))
    return 0


def _tail(path: Path, n: int = 15) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").replace("\r", "\n").splitlines()
    except OSError:
        return ""
    return "\n".join("    " + x for x in [x for x in lines if x.strip()][-n:])


def _embed_background(cfg: dict, config: Path | None, concurrency: int | None) -> int:
    import time

    from atlas.embed import store_id_for, store_root
    from atlas.embed_store import store_dir
    from atlas.jobs import LOCK, LOG, PROGRESS, lock_state, now_iso, os_lock_held, spawn_background

    sid = store_id_for(cfg)
    if sid is None:
        typer.echo("[embed] provider lite \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU} / provider lite needs no background run", err=True)
        return EXIT_CONFIG
    sdir = store_dir(store_root(cfg), sid)
    sdir.mkdir(parents=True, exist_ok=True)
    lock = lock_state(sdir / LOCK, sdir / PROGRESS, _lock_stale(cfg))
    c = _cfg_arg(config)
    if os_lock_held(sdir):
        typer.echo(f"[embed] \N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK} (PID {lock['pid'] or 'unknown'}) / already running (PID {lock['pid'] or 'unknown'})"
                   f"{' — hung (no heartbeat)' if lock['hung'] else ''}\n"
                   f"  \N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA A} / status: uv run atlas status -c {c}", err=True)
        return EXIT_LOCKED
    args = ["-m", "atlas", "embed"]
    if config:
        args += ["-c", str(Path(config).resolve())]
    if concurrency:
        args += ["--concurrency", str(concurrency)]
    log = sdir / LOG
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n=== background run requested {now_iso()} ===\n")
    spawned = spawn_background(args, log, cwd=Path.cwd())
    # watch the child for a moment: a run that dies at once (bad config, lock held, 401 on the first
    # request) must not look started
    window = float(os.environ.get("ATLAS_BACKGROUND_CHECK_S", "3"))
    deadline = time.monotonic() + window
    while time.monotonic() < deadline:
        code = spawned.proc.poll()
        if code is not None:
            typer.echo(f"[embed] background run ended at once — exit code {code}; last lines of {log}:\n"
                       f"{_tail(log)}", err=code != 0)
            return code if code else 0
        time.sleep(0.1)
    typer.echo(f"[embed] \N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN} / running in the background: PID {spawned.pid} — \N{THAI CHARACTER PO PLA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO} / "
               f"you may close this window")
    if spawned.warning:
        typer.echo(f"[embed] WARNING: {spawned.warning}", err=True)
    typer.echo(f"  log           : {log}")
    typer.echo(f"  \N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA A} / status: uv run atlas status -c {c}")
    typer.echo(f"  \N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK} / stop   : uv run atlas embed-stop -c {c}   (\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG} / resume: uv run atlas embed -c {c})")
    return 0


@app.command("embed-stop")
def embed_stop_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
) -> None:
    """Ask the embedding run to stop cleanly: in-flight requests finish, everything is saved. A run that has
    not reached the embedding step yet (still ingesting) stops as soon as it gets there."""
    from atlas.config import load_config
    from atlas.embed import store_id_for, store_root
    from atlas.embed_store import store_dir
    from atlas.jobs import LOCK, PROGRESS, STOP, StopFlag, lock_state, os_lock_held

    cfg = load_config(config)
    sid = store_id_for(cfg)
    if sid is None:
        typer.echo("[embed-stop] provider lite has no embedding run to stop")
        raise typer.Exit(0)
    sdir = store_dir(store_root(cfg), sid)
    lock = lock_state(sdir / LOCK, sdir / PROGRESS, _lock_stale(cfg))
    StopFlag(sdir / STOP).request()
    if os_lock_held(sdir):
        typer.echo(f"[embed-stop] \N{THAI CHARACTER SO SUA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA UE}\N{THAI CHARACTER NGO NGU} PID {lock['pid'] or 'unknown'} \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN} — request \N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER CHO CHAN}\N{THAI CHARACTER SARA A}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER CHO CHAN}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA A}\N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA UE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER KO KAI} / "
                   f"stop requested: PID {lock['pid'] or 'unknown'} finishes in-flight requests, saves and exits (status: stopped)")
    else:
        typer.echo(f"[embed-stop] \N{THAI CHARACTER YO YAK}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU} embed \N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU} ({sid}) — \N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA} (\N{THAI CHARACTER SARA E}\N{THAI CHARACTER CHO CHANG}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NO NU} ingest \N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK}) "
                   f"\N{THAI CHARACTER CHO CHAN}\N{THAI CHARACTER SARA A}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA UE}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER KHO KHAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NO NU} embed / no embedding run is active right now; a run that is still "
                   f"starting (e.g. ingesting) will stop as soon as it reaches the embedding step")
    typer.echo(f"  \N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA A} / status: uv run atlas status -c {_cfg_arg(config)}")


def render_status(cfg: dict) -> str:
    """The `atlas status` text. A live run's store/journal numbers come from its progress.json — the files
    of a store a live run holds are never opened (on Windows an open reader blocks its checkpoint)."""
    import atlas.embed_runner as er
    from atlas.jobs import find_jobs, format_job_status, job_status

    state = Path(cfg["pipeline"]["state_dir"])
    jobs = find_jobs(state)
    if not jobs:
        return f"\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU} / nothing has run yet (no progress.json under {state})"
    blocks = []
    for job in jobs:
        llm_job = job.name == "llm_cache"
        info = job_status(job, float(cfg["llm"]["lock_stale_seconds"]) if llm_job else _lock_stale(cfg))
        extra: list[str] = []
        if info.get("kind") == "llm":
            from atlas.llm_runner import status_extra

            extra = status_extra(info)
        elif info.get("kind") == "embedding":
            if info.get("lock_alive"):
                extra = er.store_lines(int(info.get("store_vectors") or 0), int(info.get("journal_pending") or 0),
                                       int(info.get("truncated_total") or 0), active=True)
            else:
                extra = er.store_status_lines(job)
        blocks.append(format_job_status(info, extra))
    return "\n\n".join(blocks) + "\n"


def status_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
) -> None:
    """Status of every long job under state_dir (embedding runs; LLM runs from P1): progress, rate, ETA,
    retries, last error, and whether the run is still alive (or hung)."""
    from atlas.config import load_config

    typer.echo(render_status(load_config(config)))


app.command("status")(status_cmd)
app.command("embed-status", help="Alias of `atlas status`.")(status_cmd)


# ---------- LLM work: atlas llm / llm-stop (progress: `atlas status`)
@app.command("llm")
def llm_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    check: bool = typer.Option(False, "--check", help="one tiny request per endpoint/model: reachable, JSON, Thai"),
    dry_run: bool = typer.Option(False, "--dry-run", help="estimate calls, tokens and cost — no network"),
    task: list[str] = typer.Option(None, "--task", "-t", help="limit --dry-run to these tasks"),
    background: bool = typer.Option(False, "--background", help="run detached from this window (you may close it); "
                                                                "log in state_dir/llm_cache/run.log"),
) -> None:
    """LLM work (labels, merge checks, narratives, brief, methods notes). Without flags: run the label, methods
    and narrate steps (methods notes only when methods.provider is llm).

    Exit codes (as `atlas embed`): 0 done, 2 endpoint/config error, 3 another LLM job runs, 130 stopped
    (`atlas llm-stop`, Ctrl-C or llm.budget_usd) — run the same command again to continue.
    """
    from atlas.config import load_config
    from atlas.llm_runner import check_endpoints, dry_run_all
    from atlas.pipeline import STEPS

    cfg = load_config(config)
    if check:
        rows = check_endpoints(cfg)
        if not rows:
            typer.echo("no llm.tasks.<task>.model is set — nothing to check")
            raise typer.Exit(EXIT_CONFIG)
        for r in rows:
            state = "OK  " if r["json_ok"] and r["thai_ok"] else "FAIL"
            typer.echo(f"{state} {r['endpoint']} · {r['model']} ({r['tasks']}): json={r['json_ok']} "
                       f"thai={r['thai_ok']} {r['seconds']}s {r['error']}")
        raise typer.Exit(0 if all(r["json_ok"] and r["thai_ok"] for r in rows) else EXIT_CONFIG)
    if dry_run:
        rows = dry_run_all(cfg, task or None)
        if not rows:
            typer.echo("no LLM tasks are registered yet")
        for r in rows:
            if "skipped" in r:
                typer.echo(f"{r['task']:<10} skipped — {r['skipped']}")
                continue
            cost = "unknown (set price_per_mtok_in/out)" if r["est_cost_usd"] is None else f"≤ {r['est_cost_usd']} USD"
            typer.echo(f"{r['task']:<10} {r['model'] or '(no model)'}: {r['items']} items, {r['cached']} cached, "
                       f"{r['to_call']} to call · ~{r['est_input_tokens']:,} input tokens, ≤ {r['max_output_tokens']:,} "
                       f"output · cost {cost} · spent this release {r['release_spend_usd']} USD"
                       + (f" of {r['budget_usd']}" if r["budget_usd"] is not None else ""))
        return
    if background:
        raise typer.Exit(_llm_background(cfg, config))
    steps = [s for s in ("label", "methods", "narrate")
             if s in STEPS and (s != "methods" or cfg["methods"]["provider"] == "llm")]    # notes are opt-in
    code = _run_guarded(cfg, steps, config, tag="llm", resume="llm")
    if code == 0:
        typer.echo(f"[llm] done — publish with: uv run atlas run -c {_cfg_arg(config)} --step export")
    raise typer.Exit(code)


def _llm_background(cfg: dict, config: Path | None) -> int:
    """`atlas llm` in a detached process (P0 spawn_background); a child that dies at once is reported."""
    import time

    from atlas.jobs import LOG, os_lock_held, spawn_background
    from atlas.llm_runner import llm_dir

    d, c = llm_dir(cfg), _cfg_arg(config)
    d.mkdir(parents=True, exist_ok=True)
    if os_lock_held(d):
        typer.echo(f"[llm] another LLM job is running — status: uv run atlas status -c {c}", err=True)
        return EXIT_LOCKED
    args = ["-m", "atlas", "llm"] + (["-c", str(Path(config).resolve())] if config else [])
    spawned = spawn_background(args, d / LOG, cwd=Path.cwd())
    deadline = time.monotonic() + float(os.environ.get("ATLAS_BACKGROUND_CHECK_S", "3"))
    while time.monotonic() < deadline:
        code = spawned.proc.poll()
        if code is not None:
            typer.echo(f"[llm] background run ended at once — exit code {code}; last lines of {d / LOG}:\n"
                       f"{_tail(d / LOG)}", err=code != 0)
            return code
        time.sleep(0.1)
    typer.echo(f"[llm] running in the background: PID {spawned.pid} — you may close this window")
    if spawned.warning:
        typer.echo(f"[llm] WARNING: {spawned.warning}", err=True)
    typer.echo(f"  log    : {d / LOG}\n  status : uv run atlas status -c {c}\n  stop   : uv run atlas llm-stop -c {c}")
    return 0


@app.command("llm-stop")
def llm_stop_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
) -> None:
    """Ask the LLM job to stop after the calls in flight (run `atlas llm` again to continue)."""
    from atlas.config import load_config
    from atlas.jobs import os_lock_held
    from atlas.llm_runner import llm_dir, request_stop

    cfg = load_config(config)
    flag = request_stop(cfg)
    if os_lock_held(llm_dir(cfg)):
        typer.echo(f"[llm-stop] stop requested ({flag}): the LLM job finishes the calls in flight, saves and exits")
    else:
        typer.echo(f"[llm-stop] stop requested ({flag}); no LLM job is running now — a pipeline that is still at an "
                   f"earlier step stops when its LLM step starts")
    typer.echo(f"  status: uv run atlas status -c {_cfg_arg(config)}")


@app.command("quarterly")
def quarterly_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (default: pipeline/config.yaml if it exists)"),
    corpus: Path = typer.Option(None, "--corpus", help="this round's corpus folder (default: input.path of the config)"),
    release: str = typer.Option(None, "--release", "-r", help="YYYYQn (default: the quarter of today)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="do not ask before paying for LLM calls"),
    strict: bool = typer.Option(False, help="stop on validate warnings (exit 1) too"),
    build_web: bool = typer.Option(False, "--build-web", help="rebuild web/dist even when it exists"),
    prepare: bool = typer.Option(False, help="stop after the corpus profile (before the first big embedding)"),
    runs_dir: Path = typer.Option(None, help="where rounds are archived (default: <repo>/runs)"),
    deploy_dir: Path = typer.Option(None, help="where the upload-ready site goes (default: <repo>/deploy)"),
    site: Path = typer.Option(None, help="the built web site (default: <repo>/web/dist)"),
) -> None:
    """The whole quarterly round in one command: corpus → pipeline → validate → publish → upload-ready site."""
    from atlas.quarterly import ROOT, RoundError, run_round

    if config is None and (ROOT / "pipeline" / "config.yaml").is_file():
        config = ROOT / "pipeline" / "config.yaml"
    try:
        code = run_round(config, corpus, release, yes, strict, build_web, prepare,
                         runs_dir or ROOT / "runs", deploy_dir or ROOT / "deploy", site or ROOT / "web" / "dist",
                         confirm=lambda q: typer.confirm(q, default=False))
    except (RoundError, ValueError) as e:
        typer.echo(f"[quarterly] STOPPED: {e}", err=True)
        raise typer.Exit(getattr(e, "code", 2)) from e
    raise typer.Exit(code)


corpus_app = typer.Typer(help="Corpus format 1.0 (JSON Lines): schema file and conversion from Markdown "
                              "(docs/corpus/README.md).", no_args_is_help=True)
app.add_typer(corpus_app, name="corpus")


@corpus_app.command("schema")
def corpus_schema_cmd(
    out: Path = typer.Option(Path("../docs/corpus/corpus.schema.json"), help="where to write the JSON Schema"),
) -> None:
    """Write the corpus JSON Schema (CI checks it is up to date)."""
    from atlas.schema.corpus import write_corpus_schema

    typer.echo(f"wrote {write_corpus_schema(out)}")


@corpus_app.command("convert")
def corpus_convert_cmd(
    src: Path = typer.Argument(..., help="folder of ThaiJO .md files"),
    out: Path = typer.Option(..., "--out", "-o", help="new corpus folder (articles/ + journals.csv are written here)"),
    pattern: str = typer.Option("**/*.md"),
    per_file: int = typer.Option(50_000, min=1, help="articles per articles/part-NNNN.jsonl.gz"),
    workers: int = typer.Option(4, min=1),
) -> None:
    """Convert the Markdown corpus to corpus format 1.0 — same ids, same ingest tables."""
    from atlas.corpus_convert import convert_markdown

    r = convert_markdown(src, out, pattern, per_file, workers)
    typer.echo(f"[corpus] {r['articles']:,} articles → {r['files']} file(s) in {out / 'articles'}; "
               f"journals: {r['journals_csv']}")
    if r["skipped"]:
        typer.echo(f"[corpus] skipped {len(r['skipped']):,} (first: {r['skipped'][0]})")


review_app = typer.Typer(help="Editors' spot check of topic names (export a CSV, import the corrections).",
                         no_args_is_help=True)
app.add_typer(review_app, name="review")


@review_app.command("export")
def review_export_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    out: Path = typer.Option(None, help="CSV path (default: output/review/<release>_label_review.csv)"),
    n: int = typer.Option(None, help="number of topics (default: review.sample_size)"),
) -> None:
    """Write the review CSV: keyword-fallback names and possible duplicates first, then a seeded sample."""
    from atlas.config import load_config
    from atlas.review import export_review

    typer.echo(f"wrote {export_review(load_config(config), out, n)}")


@review_app.command("import")
def review_import_cmd(
    file: Path = typer.Argument(..., help="the filled-in review CSV"),
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
) -> None:
    """Copy corrected names (name_th_fixed / name_en_fixed) into labeling.overrides_path."""
    from atlas.config import load_config
    from atlas.review import import_review

    r = import_review(load_config(config), file)
    typer.echo(f"{r['applied']} corrections from {r['reviewed']} reviewed topics → {r['path']} "
               f"({r['overrides_total']} overrides in total; they apply from the next label step)")


@app.command("validate")
def validate_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    release: str = typer.Option(None, help="release to check (default: pipeline.release, else the release "
                                            "work_dir was clustered for, else the current quarter)"),
    release_dir: Path = typer.Option(None, "--dir", help="check this folder instead of output/data/<release>"),
    previous: Path = typer.Option(None, help="previous release folder (default: manifest.previous_release)"),
) -> None:
    """Validate a data-contract v2 release (schema + integrity + diff vs the previous release).

    Exit code 0 = clean, 1 = warnings, 2 = errors.
    """
    from atlas.config import load_config
    from atlas.state import _checked, default_release
    from atlas.validate import render_report, validate_release

    cfg = load_config(config)
    try:
        name = _checked(release) if release else default_release(cfg)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    root = release_dir or Path(cfg["pipeline"]["output_dir"]) / "data" / name
    rep = validate_release(root, previous, cfg["validation"], cfg["pipeline"]["work_dir"])
    typer.echo(render_report(rep))
    raise typer.Exit(rep.exit_code)


@app.command("publish")
def publish_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    release: str = typer.Option(None, help="release to publish (default: pipeline.release, else the release "
                                            "work_dir was clustered for, else the current quarter)"),
    site: Path = typer.Option(None, "--site", help="the static web folder: writes data/<release>/, "
                              "data/latest.json and atlas-offline.html"),
    tarball: bool = typer.Option(False, "--tarball", help="also package a reproducible tar.gz + notes "
                                 "for a GitHub Release (printed command, never uploaded)"),
    allow_warnings: bool = typer.Option(False, "--allow-warnings", help="publish even when validation warns"),
    set_latest: bool = typer.Option(False, "--set-latest", help="point the site's latest.json at this release even "
                                    "when a newer release is on the site"),
) -> None:
    """Validate a release, then put it on the static site and/or package it. Never uploads anything.

    Exit code 0 = published, 2 = refused (validation) or nothing to do.
    """
    from atlas.config import load_config
    from atlas.publish import PublishRefused, publish

    if site is None and not tarball:
        typer.echo("nothing to do: pass --site <web folder> and/or --tarball", err=True)
        raise typer.Exit(2)
    try:
        r = publish(load_config(config), release, allow_warnings, site, tarball, set_latest)
    except PublishRefused as e:
        typer.echo(f"refused: {e}", err=True)
        raise typer.Exit(2) from e
    if site is not None:
        typer.echo(f"site data: {r['site_data']}\nlatest:    {r['latest']}\n"
                   f"offline:   {r['offline_html'] or 'skipped (no offline-template.html in the site folder)'}\n"
                   f"feeds:     {r['feeds']['releases'] + ' + topics/' if r.get('feeds') else 'none (publish.site_url not set)'}")
    if tarball:
        typer.echo(f"tarball: {r['tarball']}\nsha256:  {r['sha256']}\nnotes:   {r['notes']}")
        typer.echo(f"upload it yourself (needs the owner's go-ahead):\n  {r['gh_command']}")


@app.command("sdg-scores")
def sdg_scores_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
) -> None:
    """Calibrate sdg.min_similarity: cosine quantiles and topic–goal links per threshold 0.30…0.60 (read-only)."""
    from atlas.config import load_config
    from atlas.sdg import score_report

    typer.echo(score_report(load_config(config)))


@app.command("bakeoff")
def bakeoff_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    kind: str = typer.Option("all", help="embedding | clustering | all"),
    truth: Path = typer.Option(None, help="CSV with article_id,topic (synthetic corpus _truth.csv)"),
    out: Path = typer.Option(None, help="write the Markdown report here"),
) -> None:
    """Compare embedding models and clustering algorithms on the current work_dir (Markdown report)."""
    from atlas.bakeoff import run_bakeoff
    from atlas.config import load_config

    if kind not in ("embedding", "clustering", "all"):
        raise typer.BadParameter("kind must be embedding, clustering or all")
    md = run_bakeoff(load_config(config), kind, truth)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
    typer.echo(md)
