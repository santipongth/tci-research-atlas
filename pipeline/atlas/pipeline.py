"""Pipeline orchestrator — run the whole batch or individual steps.

Usage:
  python -m atlas.pipeline --config config.yaml                 # run everything
  python -m atlas.pipeline --config config.yaml --steps embed cluster
  python -m atlas.pipeline --steps emerging forecast export     # reuse checkpoints

Steps: ingest → preprocess → embed → cluster → label → series → emerging → forecast → layout → export
Every step reads its predecessor's checkpoint in work_dir — safe to stop/resume anywhere.
"""
from __future__ import annotations

import argparse
import sys
import time

from . import config as cfg_mod

STEPS = ["ingest", "preprocess", "embed", "cluster", "label",
         "series", "emerging", "forecast", "layout", "export"]


def run(cfg: dict, steps: list[str]) -> None:
    t0 = time.time()
    for step in steps:
        print(f"\n=== STEP: {step} ===")
        t = time.time()
        if step == "ingest":
            from . import ingest
            ingest.ingest(cfg)
        elif step == "preprocess":
            from . import preprocess
            preprocess.preprocess(cfg)
        elif step == "embed":
            from . import embed
            embed.embed(cfg)
        elif step == "cluster":
            from . import cluster
            cluster.cluster(cfg)
        elif step == "label":
            from . import label
            label.label(cfg)
        elif step == "series":
            from . import topics_time
            topics_time.build_series(cfg)
        elif step == "emerging":
            from . import emerging
            emerging.emerging(cfg)
        elif step == "forecast":
            from . import forecast
            forecast.forecast(cfg)
        elif step == "layout":
            from . import layout
            layout.layout(cfg)
        elif step == "export":
            from . import export
            export.export(cfg)
        else:
            raise ValueError(f"unknown step: {step} (choose from {STEPS})")
        print(f"=== {step} done in {time.time() - t:.1f}s ===")
    print(f"\n[pipeline] all steps finished in {(time.time() - t0) / 60:.1f} min")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="TCI Research Atlas batch pipeline")
    ap.add_argument("--config", default=None, help="path to config.yaml (defaults to config.example.yaml)")
    ap.add_argument("--steps", nargs="*", default=None,
                    help=f"subset of steps to run (default: all). Choices: {STEPS}")
    args = ap.parse_args(argv)

    cfg = cfg_mod.load_config(args.config)
    steps = args.steps or STEPS
    unknown = set(steps) - set(STEPS)
    if unknown:
        sys.exit(f"unknown steps: {unknown}")
    run(cfg, steps)


if __name__ == "__main__":
    main()
