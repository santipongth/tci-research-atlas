"""Pipeline orchestrator — run all steps or a subset; every step reads the previous
step's checkpoint from work_dir, so the run can stop and resume anywhere.

  uv run atlas run --config config.yaml
  uv run atlas run --config config.yaml --step emerging --step forecast --step export
  python -m atlas.pipeline --config config.yaml --steps emerging forecast export
"""
from __future__ import annotations

import argparse
import importlib
import sys
import time

from atlas import config as cfg_mod
from atlas.console import use_utf8_stdio

STEPS = ["ingest", "preprocess", "embed", "cluster", "taxonomy", "label", "series", "emerging", "keywords",
         "forecast", "narrate", "layout", "methods", "journals", "match", "institutions", "export"]
_FUNCS = {
    "ingest": ("atlas.ingest", "ingest"),
    "preprocess": ("atlas.preprocess", "preprocess"),
    "embed": ("atlas.embed", "embed"),
    "cluster": ("atlas.cluster", "cluster"),
    "taxonomy": ("atlas.taxonomy", "taxonomy"),
    "label": ("atlas.label", "label"),
    "series": ("atlas.topics_time", "build_series"),
    "emerging": ("atlas.emerging", "emerging"),
    "keywords": ("atlas.keywords", "keywords"),
    "forecast": ("atlas.forecast", "forecast"),
    "narrate": ("atlas.narrative", "narrate"),
    "layout": ("atlas.layout", "layout"),
    "methods": ("atlas.methods", "methods"),
    "journals": ("atlas.journals", "journals"),
    "match": ("atlas.matcher", "match"),
    "institutions": ("atlas.institutions", "institutions"),
    "export": ("atlas.export", "export"),
}


def run(cfg: dict, steps: list[str] | None = None) -> None:
    steps = steps or STEPS
    unknown = [s for s in steps if s not in _FUNCS]
    if unknown:
        raise ValueError(f"unknown steps {unknown}; choose from {STEPS}")
    t0 = time.time()
    for step in steps:
        print(f"\n=== STEP: {step} ===")
        t = time.time()
        module, fn = _FUNCS[step]
        getattr(importlib.import_module(module), fn)(cfg)
        print(f"=== {step} done in {time.time() - t:.1f}s ===")
    print(f"\n[pipeline] {len(steps)} steps finished in {(time.time() - t0) / 60:.1f} min")


def main(argv: list[str] | None = None) -> None:
    use_utf8_stdio()                     # redirected output on Windows would crash on "≤" otherwise
    ap = argparse.ArgumentParser(description="TCI Research Atlas batch pipeline")
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", nargs="*", default=None, help=f"subset of {STEPS}")
    args = ap.parse_args(argv)
    try:
        run(cfg_mod.load_config(args.config), args.steps)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
