"""Write tests/fixtures/match_parity.json — the fold + trigram output of atlas.matcher for PARITY_CASES.

The web test (web/src/lib/matcher.test.ts) reads the same file, so the Python and TypeScript analyzers cannot
drift apart. Run from pipeline/:  uv run python scripts/write_match_parity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atlas.matcher import PARITY_CASES, analyze, match_fold  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "match_parity.json"


def parity_cases() -> list[dict]:
    return [{"text": t, "fold": match_fold(t), "grams": analyze(t)} for t in PARITY_CASES]


if __name__ == "__main__":
    OUT.write_text(json.dumps(parity_cases(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(PARITY_CASES)} cases)")
