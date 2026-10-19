"""Write tests/fixtures/match_parity.json — the fold + trigram output of atlas.matcher for PARITY_CASES.

The web test (web/src/lib/matcher.test.ts) reads the same file, so the Python and TypeScript analyzers cannot
drift apart. Run from pipeline/:  uv run python scripts/write_match_parity.py
Invisible characters (controls, format characters, every space but U+0020) are written as JSON escapes so the
fixture can be read and reviewed (the parsed values are unchanged). Grams are code-point slices: the web must cut
Array.from(word) — an astral emoji is one character there, not two UTF-16 units.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atlas.matcher import PARITY_CASES, analyze, match_fold  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "match_parity.json"
BACKSLASH = chr(92)


def _escape_invisible(text: str) -> str:
    """JSON text with every invisible BMP character written as a JSON escape (the JSON value is unchanged). A raw
    newline or space is layout (json.dumps already escapes control characters inside strings)."""
    def esc(c: str) -> str:
        hidden = c not in " \n" and ord(c) <= 0xFFFF and unicodedata.category(c) in ("Cc", "Cf", "Zs", "Zl", "Zp")
        return f"{BACKSLASH}u{ord(c):04x}" if hidden else c
    return "".join(esc(c) for c in text)


def parity_cases() -> list[dict]:
    return [{"text": t, "fold": match_fold(t), "grams": analyze(t)} for t in PARITY_CASES]


def fixture_text() -> str:
    return _escape_invisible(json.dumps(parity_cases(), ensure_ascii=False, indent=1)) + "\n"


if __name__ == "__main__":
    OUT.write_text(fixture_text(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(PARITY_CASES)} cases)")
