"""`atlas` command-line interface. UTF-8 safe on Windows consoles.

Commands are added by later modules: run, synth, profile, schema.
"""
from __future__ import annotations

import sys
from pathlib import Path

import typer

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

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
