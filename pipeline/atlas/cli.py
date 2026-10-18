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
