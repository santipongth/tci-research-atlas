"""LLM prompts: prompts/*.md is the single source of truth, read at run time.

Each prompt file has a section "## Prompt (master)" followed by one fenced code block —
that block is the template. Placeholders are {lower_case_names}; the JSON examples in
the templates use braces followed by a newline/quote, so they are never mistaken for
placeholders and need no escaping. prompt_version() hashes the template only, so editing
the notes around it never invalidates the LLM cache; editing the template does.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_BLOCK = re.compile(r"^## Prompt \(master\)[^\n]*\n+```[^\n]*\n(.*?)\n```", re.S | re.M)
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def load_prompt(name: str, prompts_dir: str | Path | None = None) -> str:
    """Template text of prompts/<name>.md (e.g. name="topic_label.th")."""
    path = Path(prompts_dir or DEFAULT_PROMPTS_DIR) / f"{name}.md"
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = _BLOCK.search(text)
    if not m:
        raise ValueError(f"{path}: no '## Prompt (master)' fenced code block")
    return m.group(1)


def prompt_version(template: str) -> str:
    return hashlib.sha256(template.encode("utf-8")).hexdigest()[:12]


def placeholders(template: str) -> set[str]:
    return set(_PLACEHOLDER.findall(template))


def render_prompt(template: str, **values: object) -> str:
    """Fill {name} placeholders in one pass (values are never re-scanned)."""
    missing = placeholders(template) - set(values)
    if missing:
        raise KeyError(f"prompt placeholders without values: {sorted(missing)}")
    return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), template)
