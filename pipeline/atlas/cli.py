"""`atlas` command-line interface. UTF-8 safe on Windows consoles.

Commands are added by later modules: run, synth, profile, schema.
"""
from __future__ import annotations

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
    path: Path = typer.Argument(..., help="folder of ThaiJO .md files"),
    out: Path = typer.Option(None, help="write the JSON report here"),
    md: Path = typer.Option(None, help="write a Markdown report here"),
    pattern: str = typer.Option("**/*.md"),
    workers: int = typer.Option(1),
) -> None:
    """Corpus quality report — run before the pipeline on every new corpus."""
    import json

    from atlas.profile import profile_corpus, render_markdown

    report = profile_corpus(path, pattern, workers)
    if out:
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    text = render_markdown(report)
    if md:
        md.write_text(text, encoding="utf-8")
    typer.echo(text)


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
    from atlas.pipeline import run

    run(load_config(config), step or None)
