# P0 — Foundation & Data Reality Check — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Python pipeline run correctly end-to-end on real ThaiJO Markdown and on a synthetic corpus with planted trends — CPU-only, with Emerging v2, skill-gated forecasts, tests and CI — so P1 (web v2) builds on numbers we can trust.

**Architecture:** Keep the batch-pipeline → checkpoint files → `atlas_data.json` design. Replace the input layer with a tested ThaiJO Markdown parser, replace BERTopic with our own PCA→UMAP→HDBSCAN→merge clustering, rewrite emerging metrics to the v2 definition (Poisson-GLM share growth + CI + breadth), move persistent state (embedding store, label cache, previous centroids) out of `work_dir` into `state_dir`, and drive everything from one Typer CLI (`atlas`) that works on Windows and Linux.

**Tech Stack:** Python 3.12 via `uv`; pandas ≥2.2 (pandas 3 compatible), numpy, pyarrow, pydantic v2, typer, scikit-learn ≥1.5 (`HDBSCAN`, `AgglomerativeClustering`, `TruncatedSVD`, `PCA`), umap-learn, pythainlp, statsmodels; pytest + hypothesis + ruff; GitHub Actions. Web stays React 19 + Vite (minimal patch only).

**Spec:** `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md` (sections "รีวิวอัลกอริทึม", "Emerging v2", "Forecast v2", "P0"). Read it before starting any task.

## Global Constraints

- All pipeline commands run from `pipeline/` with `uv run …`; Python ≥ 3.11 (dev/CI on 3.12).
- pandas 3 is allowed: never test `dtype == object`; normalise text columns with `.fillna("").astype(str)`.
- All tables go through `atlas.io_utils.read_table` / `write_table` (never call `to_parquet`/`read_parquet` directly).
- No hard-coded thresholds: every number that changes results lives in `AtlasConfig` (Task 4) and `config.example.yaml`.
- Thai code points in source code are written as `"\N{THAI CHARACTER ...}"` names or `chr(0x....)` — **never** as backslash-u escapes (tool pipelines decode those into invisible literal characters).
- Every CLI entry point reconfigures stdout/stderr to UTF-8 (Windows consoles default to cp1252).
- API keys only from the env var named in config (`ATLAS_API_KEY`); never written to any file.
- The real corpus is never committed. Only the 11 sample files are copied into `pipeline/tests/fixtures/thaijo_md/`.
- Persistent state lives in `pipeline.state_dir` (default `./state`); `work_dir` must stay safe to delete.
- Emerging statuses are exactly: `EMERGING`, `WATCH`, `HOT`, `DECLINING`, `STABLE`, `LOW_DATA`; `definition_version` is `2`.
- Forecasts are exported only when `show` is true (skill vs naive > `forecast.min_skill`); otherwise `forecast: null` and `forecast_uncertain: true`.
- Exported JSON must be strict JSON (no `NaN`/`Infinity`).
- Tests must pass on Windows (local) and Ubuntu (CI). Run `uv run ruff check --fix .` before each commit (import order in the snippets may need sorting). End every commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Deferred from the spec's P0 row (explicitly):** near-duplicate detection by embedding similarity (cos > 0.97) moves to P2 with the journal module — P0 dedups by article_id, DOI and normalised title + year only.
- Never `git push` or create a GitHub remote without asking the user first.

## Review Focus

1. **Files with a UTF-8 BOM or CRLF line endings** (common when exports pass through Windows tools) must parse exactly like the LF originals — test added in Task 3.
2. **An article file with no `Article URL`** (broken scrape) must get a stable, unique fallback id (`file:<sha1 of filename>`), never an empty id that collides — test added in Task 5.
3. **A corpus subset covering only 1–2 years** must run through series → emerging without exceptions; topics become `LOW_DATA` — test added in Task 12.
4. **A topic with zero articles inside the trend window W** must not crash the GLM; its growth is NaN and it can never be `EMERGING`/`HOT`/`DECLINING` — test added in Task 12.
5. **An embed run interrupted half-way** must resume from the persistent store and still produce a matrix row-aligned with `02_docs` — test added in Task 8.

---

## File Structure

```
pipeline/
├── pyproject.toml                  NEW  uv project, deps, `atlas` script, pytest/ruff config
├── requirements.txt                MOD  regenerated from pyproject (pip users)
├── config.example.yaml             MOD  v2 config (every key documented, Thai comments)
├── configs/ci.yaml                 NEW  synthetic e2e config (lite embeddings, small clusters)
├── atlas/
│   ├── __init__.py                 MOD  __version__
│   ├── cli.py                      NEW  Typer app: version | run | synth | profile | schema
│   ├── config.py                   MOD  pydantic AtlasConfig + load_config() -> dict
│   ├── io_utils.py                 KEEP
│   ├── thai.py                     NEW  clean_text, fold_thai, thai_ratio, norm_key, tokenize
│   ├── sources/__init__.py         NEW
│   ├── sources/thaijo_md.py        NEW  parse_markdown(), fill_years_from_issue()
│   ├── orgs.py                     NEW  org_key() — coarse institution key for breadth counts
│   ├── ingest.py                   MOD  thaijo_md | table → 01_articles / 01_authors / 01_references
│   ├── preprocess.py               MOD  vectorised doc_text
│   ├── embed_store.py              NEW  EmbeddingStore (append-only shards keyed by text hash)
│   ├── embed.py                    MOD  providers api | local | lite + store
│   ├── ctfidf.py                   NEW  class-based TF-IDF over Thai/Latin tokens and author keywords
│   ├── cluster.py                  MOD  reduce → HDBSCAN → merge → outliers → coarse groups → coherence
│   ├── label.py                    MOD  prompt-hash cache in state_dir, MMR representative docs
│   ├── topics_time.py              MOD  + journal/org/first-year tables, configurable backfill guard
│   ├── emerging.py                 MOD  Emerging v2
│   ├── forecast.py                 MOD  + naive baseline, raw history, skill gating, MASE
│   ├── layout.py                   MOD  io_utils for edges, json centroid ids
│   ├── export.py                   MOD  v1.1 atlas_data.json (+v2 statuses, strict JSON), state_dir/prev
│   ├── pipeline.py                 MOD  orchestrator uses new modules
│   ├── profile.py                  NEW  corpus quality report (json + markdown)
│   ├── synth.py                    NEW  synthetic ThaiJO corpus with planted trends
│   └── schema/
│       ├── __init__.py             NEW
│       └── contract.py             NEW  pydantic data-contract v2 skeleton + JSON Schema writer
├── scripts/run_all.sh              MOD  thin wrapper over `uv run atlas run`
├── scripts/validate_input.py       DEL  replaced by `atlas profile`
└── tests/
    ├── conftest.py                 NEW
    ├── fixtures/thaijo_md/*.md     NEW  11 real files (byte copies, ASCII names)
    ├── test_cli.py  test_thai.py  test_thaijo_md.py  test_config.py  test_ingest.py
    ├── test_synth.py  test_profile.py  test_embed.py  test_ctfidf.py  test_cluster.py
    ├── test_label.py  test_emerging.py (rewritten)  test_forecast.py  test_export.py
    ├── test_schema.py
    └── test_e2e_synth.py           NEW  @slow: synth 20K → full pipeline → planted signals recovered
web/
├── package.json                    MOD  + json-schema-to-typescript, `gen:types`
├── src/data/contract.schema.json   NEW  generated by `atlas schema`
├── src/data/contract.ts            NEW  generated by `npm run gen:types`
├── src/data/atlas.ts               MOD  TopicStatus += WATCH | LOW_DATA (interface line only)
├── src/sections/AtlasMap.tsx       MOD  STATUS_STYLE += WATCH, LOW_DATA
└── src/sections/EmergingThemes.tsx MOD  ORDER += WATCH, LOW_DATA
.github/workflows/ci.yml            NEW
docs/EMERGING_SPEC.md               MOD  rewritten as v2 (v1 kept as appendix)
docs/{ARCHITECTURE,DATA_SPEC,OPERATIONS,ROADMAP}.md, README.md, pipeline/README.md, CLAUDE.md   MOD  sync
.gitignore                          MOD  + pipeline/.ci/, .hypothesis/
```

---

### Task 1: Python project scaffold, CLI skeleton, test fixtures

**Files:**
- Create: `pipeline/pyproject.toml`, `pipeline/atlas/cli.py`, `pipeline/tests/conftest.py`, `pipeline/tests/test_cli.py`, `pipeline/tests/fixtures/thaijo_md/` (11 copies)
- Modify: `pipeline/atlas/__init__.py`, `pipeline/requirements.txt`, `.gitignore`

**Interfaces:**
- Produces: `atlas.__version__ == "2.0.0.dev0"`; `atlas.cli.app` (Typer) with command `version`; pytest fixture `thaijo_dir() -> Path` and constant `FIXTURES`.

- [ ] **Step 1: Create `pipeline/pyproject.toml`**

```toml
[project]
name = "tci-atlas"
version = "2.0.0.dev0"
description = "TCI Research Atlas batch pipeline"
requires-python = ">=3.11"
dependencies = [
  "pandas>=2.2",
  "numpy>=1.26",
  "pyarrow>=15",
  "pyyaml>=6",
  "pydantic>=2.7",
  "typer>=0.12",
  "tqdm>=4.66",
  "scikit-learn>=1.5",
  "umap-learn>=0.5.6",
  "pythainlp>=5.0",
  "statsmodels>=0.14",
]

[project.optional-dependencies]
api = ["openai>=1.40"]
local = ["sentence-transformers>=3.0"]

[project.scripts]
atlas = "atlas.cli:app"

[dependency-groups]
dev = ["pytest>=8", "hypothesis>=6.100", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["atlas"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["slow: end-to-end tests on the synthetic corpus (run with: pytest -m slow)"]
addopts = "-m 'not slow'"

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]
ignore = ["E501", "B008", "B905"]   # B905: zip(strict=) not required — inputs are aligned by construction
```

- [ ] **Step 2: Replace `pipeline/atlas/__init__.py`**

```python
"""TCI Research Atlas — batch pipeline."""

__version__ = "2.0.0.dev0"
```

- [ ] **Step 3: Create `pipeline/atlas/cli.py`**

```python
"""`atlas` command-line interface. UTF-8 safe on Windows consoles.

Commands are added by later modules: run, synth, profile, schema.
"""
from __future__ import annotations

import sys

import typer

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

app = typer.Typer(help="TCI Research Atlas pipeline", no_args_is_help=True, add_completion=False)


@app.command()
def version() -> None:
    """Print the pipeline version."""
    from atlas import __version__

    typer.echo(__version__)
```

- [ ] **Step 4: Copy the 11 corpus files as byte-identical fixtures with ASCII names**

Run (from `pipeline/`):
```bash
uv run python -c "import re,pathlib,shutil; d=pathlib.Path('tests/fixtures/thaijo_md'); d.mkdir(parents=True, exist_ok=True); [shutil.copyfile(p, d/('so02_BECJournal_'+re.search(r'article/view/(\d+)', p.read_text(encoding='utf-8')).group(1)+'.md')) for p in pathlib.Path('../corpus').glob('*.md')]"
ls tests/fixtures/thaijo_md | wc -l
```
Expected: `11`

- [ ] **Step 5: Create `pipeline/tests/conftest.py`**

```python
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def thaijo_dir() -> Path:
    return FIXTURES / "thaijo_md"
```

- [ ] **Step 6: Write the failing test `pipeline/tests/test_cli.py`**

```python
from typer.testing import CliRunner

from atlas.cli import app
from tests.conftest import FIXTURES


def test_version_command_prints_version():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert "2.0.0" in result.stdout


def test_eleven_real_fixtures_present():
    assert len(list((FIXTURES / "thaijo_md").glob("*.md"))) == 11
```

Add an empty `pipeline/tests/__init__.py` so `from tests.conftest import FIXTURES` resolves.

- [ ] **Step 7: Sync the environment and run the tests**

Run: `uv sync && uv run pytest tests/test_cli.py -v`
Expected: 2 passed. (The old `tests/test_emerging.py` still imports removed names later — leave it until Task 12; if it errors at collection now, run only `tests/test_cli.py`.)

- [ ] **Step 8: Regenerate `requirements.txt` and extend `.gitignore`**

```bash
uv export --no-hashes --no-dev --format requirements-txt > requirements.txt
```
Append to the repo-root `.gitignore`:
```
# synthetic e2e scratch + hypothesis db
pipeline/.ci/
.hypothesis/
pipeline/.hypothesis/
```

- [ ] **Step 9: Commit**

```bash
git add pipeline/pyproject.toml pipeline/uv.lock pipeline/requirements.txt pipeline/atlas/__init__.py pipeline/atlas/cli.py pipeline/tests .gitignore
git commit -m "build(pipeline): uv project, atlas CLI skeleton, real ThaiJO fixtures

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Thai text helpers (`atlas/thai.py`)

**Files:**
- Create: `pipeline/atlas/thai.py`, `pipeline/tests/test_thai.py`

**Interfaces:**
- Produces:
  - `clean_text(s: str | None) -> str` — repairs Thai PUA glyphs, `nikhahit+sara aa → sara am`, removes whitespace before Thai combining marks, strips HTML, collapses whitespace.
  - `repair_glyphs(s: str) -> str` — PUA + sara am repair only, **keeps runs of spaces** (abstract segment separators).
  - `fold_thai(s: str) -> str` — removes Thai tone marks/diacritics U+0E47–U+0E4E.
  - `thai_ratio(s: str) -> float` — Thai letters / (Thai + Latin letters); 0.0 when no letters.
  - `norm_key(s: str) -> str` — lowercase, folded, only `[0-9a-z]` and Thai letters/digits.
  - `tokenize(text: str) -> list[str]` — Thai words (pythainlp `newmm`) + lowercase Latin words, stopwords and 1-char tokens removed.
  - `THAI_PUA: dict[int, int]`, `has_pua(s: str) -> bool`.

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_thai.py`**

```python
from atlas.thai import clean_text, fold_thai, has_pua, norm_key, repair_glyphs, thai_ratio, tokenize

MAI_THO = "\N{THAI CHARACTER MAI THO}"
SARA_AM = "\N{THAI CHARACTER SARA AM}"


def test_clean_text_maps_pua_tone_marks_to_standard():
    broken = "ความต" + chr(0xF70B) + "องการ"          # PUA mai tho from PDF extraction
    assert clean_text(broken) == "ความต" + MAI_THO + "องการ"
    assert has_pua(broken) and not has_pua(clean_text(broken))


def test_clean_text_repairs_split_sara_am_and_space_before_mark():
    split = "ตำแหน่ง".replace(SARA_AM, "\N{THAI CHARACTER NIKHAHIT}\N{THAI CHARACTER SARA AA}")
    assert clean_text(split) == "ตำแหน่ง"
    assert clean_text("เจ้าหน้าท ี่ประสานงาน") == "เจ้าหน้าที่ประสานงาน"


def test_clean_text_strips_html_and_collapses_space():
    assert clean_text("  <b>สวัสดี</b>\n  world  ") == "สวัสดี world"
    assert clean_text(None) == ""


def test_repair_glyphs_keeps_space_runs():
    assert repair_glyphs("ก   B") == "ก   B"


def test_fold_and_ratio_and_key():
    assert fold_thai("รองศาสตราจารย์") == "รองศาสตราจารย"
    assert thai_ratio("ภาษาไทย") == 1.0
    assert thai_ratio("English") == 0.0
    assert thai_ratio("123 !!") == 0.0
    assert norm_key("Thai Journal, ฉบับที่ 1!") == "thaijournalฉบับที1"   # vowels kept, tone mark folded


def test_tokenize_mixed_text():
    toks = tokenize("การศึกษาผู้สูงอายุ and Long-term Care ในประเทศไทย")
    assert "การศึกษา" in toks
    assert "care" in toks
    assert "and" not in toks
    assert all(len(t) >= 2 for t in toks)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_thai.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.thai'`

- [ ] **Step 3: Implement `pipeline/atlas/thai.py`**

```python
"""Thai text helpers shared by the parser, ingest, c-TF-IDF and search.

Thai code points are written with \\N{...} names on purpose: readable, and immune to
tools that decode backslash-u escapes.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

MARKS = "\N{THAI CHARACTER MAITAIKHU}-\N{THAI CHARACTER YAMAKKAN}"               # U+0E47–U+0E4E
ABOVE_BELOW = "\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER SARA I}-\N{THAI CHARACTER PHINTHU}"
THAI_LETTER = re.compile("[\N{THAI CHARACTER KO KAI}-\N{THAI CHARACTER HO NOKHUK}]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
THAI_MARKS = re.compile(f"[{MARKS}]")
NIKHAHIT_SARA_AA = "\N{THAI CHARACTER NIKHAHIT}\N{THAI CHARACTER SARA AA}"
SARA_AM = "\N{THAI CHARACTER SARA AM}"

# Thai glyph variants in the Private Use Area left behind by PDF text extraction
# (legacy Thai font layout) → standard code points
THAI_PUA = {
    0xF700: 0x0E10, 0xF701: 0x0E34, 0xF702: 0x0E35, 0xF703: 0x0E36, 0xF704: 0x0E37,
    0xF705: 0x0E48, 0xF706: 0x0E49, 0xF707: 0x0E4A, 0xF708: 0x0E4B, 0xF709: 0x0E4C,
    0xF70A: 0x0E48, 0xF70B: 0x0E49, 0xF70C: 0x0E4A, 0xF70D: 0x0E4B, 0xF70E: 0x0E4C,
    0xF70F: 0x0E0D, 0xF710: 0x0E31, 0xF711: 0x0E4D, 0xF712: 0x0E47, 0xF713: 0x0E48,
    0xF714: 0x0E49, 0xF715: 0x0E4A, 0xF716: 0x0E4B, 0xF717: 0x0E4C, 0xF718: 0x0E38,
    0xF719: 0x0E39, 0xF71A: 0x0E3A,
}
_PUA_TABLE = str.maketrans(THAI_PUA)
_PUA_CHARS = re.compile("[" + "".join(map(chr, THAI_PUA)) + "]")
_SPACE_BEFORE_MARK = re.compile(f"\\s+([{ABOVE_BELOW}{MARKS}])")
_KEY_DROP = re.compile("[^0-9a-z\N{THAI CHARACTER KO KAI}-\N{THAI DIGIT NINE}]+")
_HAS_WORD_CHAR = re.compile("[0-9a-z\N{THAI CHARACTER KO KAI}-\N{THAI CHARACTER HO NOKHUK}]")
EN_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in into is it its of on or that the this to was were "
    "with which we our their study research results using based among between".split()
)


def has_pua(s: str) -> bool:
    return bool(_PUA_CHARS.search(s or ""))


def repair_glyphs(s: str | None) -> str:
    """PUA + split sara-am repair only. Keeps whitespace runs (they separate abstract segments)."""
    if not s:
        return ""
    return unicodedata.normalize("NFC", s.translate(_PUA_TABLE)).replace(NIKHAHIT_SARA_AA, SARA_AM)


def clean_text(s: str | None) -> str:
    s = repair_glyphs(s)
    if not s:
        return ""
    s = _SPACE_BEFORE_MARK.sub(r"\1", s)          # "เจ้าหน้าท ี่" → "เจ้าหน้าที่"
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fold_thai(s: str) -> str:
    """Remove Thai tone marks/diacritics — for matching text whose marks were lost."""
    return THAI_MARKS.sub("", s)


def thai_ratio(s: str) -> float:
    th, la = len(THAI_LETTER.findall(s)), len(LATIN_LETTER.findall(s))
    return th / (th + la) if th + la else 0.0


def norm_key(s: str) -> str:
    return _KEY_DROP.sub("", fold_thai(s.lower()))


@lru_cache(maxsize=1)
def _thai_stopwords() -> frozenset[str]:
    from pythainlp.corpus import thai_stopwords

    return frozenset(thai_stopwords())


def tokenize(text: str) -> list[str]:
    """Words for c-TF-IDF and search: Thai via pythainlp newmm, Latin lowercased."""
    from pythainlp.tokenize import word_tokenize

    stop = _thai_stopwords()
    out: list[str] = []
    for tok in word_tokenize(clean_text(text), engine="newmm", keep_whitespace=False):
        tok = tok.strip().lower().strip(".,;:()[]{}\"'“”‘’!?-–—/")
        if len(tok) < 2 or not _HAS_WORD_CHAR.search(tok) or tok.isdigit():
            continue
        if tok in stop or tok in EN_STOPWORDS:
            continue
        out.append(tok)
    return out
```

Verified with pythainlp 5.4: `word_tokenize("การศึกษาผู้สูงอายุ and Long-term Care ในประเทศไทย")` → `['การศึกษา', 'ผู้สูงอายุ', 'and', 'Long-term', 'Care', 'ในประเทศ', 'ไทย']`; `"การ"` and `"ใน"` are in `thai_stopwords()`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_thai.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add pipeline/atlas/thai.py pipeline/tests/test_thai.py
git commit -m "feat(pipeline): Thai text helpers (PUA repair, folding, tokenization)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: ThaiJO Markdown parser (`atlas/sources/thaijo_md.py`)

This code was prototyped and verified against all 11 real files on 2026-10-18; keep the logic as written.

**Files:**
- Create: `pipeline/atlas/sources/__init__.py` (empty), `pipeline/atlas/sources/thaijo_md.py`, `pipeline/tests/test_thaijo_md.py`

**Interfaces:**
- Consumes: `atlas.thai` (`clean_text`, `repair_glyphs`, `fold_thai`, `thai_ratio`, `norm_key`, `has_pua`, `THAI_LETTER`, `LATIN_LETTER`, `MARKS`).
- Produces:
  - `parse_markdown(text: str, source_path: str = "") -> dict` with keys: `article_id, source_path, url, issue_url, journal_name, published, year (int|None), year_source ("published"|"doi"|"issue_median"|""), pages, title_th, title_en, abstract_th, abstract_en, doi, keywords_th (list[str]), keywords_en (list[str]), authors (list[dict]), references (list[dict]), n_references, has_references, self_citation_only, text_quality (list[str])`.
  - author dict: `name, name_en, affiliation_th, affiliation_en, role, is_student`.
  - reference dict: `text, year (int|None), translated (bool), lang ("th"|"latin"), self_citation (bool)`.
  - `fill_years_from_issue(records: list[dict]) -> None` (mutates: fills `year`, sets `year_source="issue_median"`).
  - `split_title`, `split_abstract`, `split_keywords`, `parse_author`, `rejoin_references`, `resolve_year` (public for tests).

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_thaijo_md.py`**

```python
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from atlas.sources.thaijo_md import (
    fill_years_from_issue,
    parse_markdown,
    rejoin_references,
    resolve_year,
    split_title,
)

# Expected facts for the 11 real files, verified by hand against the source Markdown.
GOLDEN = {
    "54971": dict(year=2014, src="published", doi="10.14456/becj.2014.15",
                  title_th="ทักษะแห่งอนาคตใหม่การศึกษาเพื่อศตวรรษที่ 21",
                  title_en="21st Century Skills Rethinking How Students Learn",
                  abs_en="", n_auth=1, kw=(2, 1), refs=0, counted=0, self_only=False, flags=[]),
    "62642": dict(year=2018, src="published", doi="", title_th="",
                  title_en_start="Attitudes of Naresuan University BBA",
                  abs_en_start="There are a large number", n_auth=1, kw=(0, 4),
                  refs=13, counted=10, self_only=False, flags=[]),
    "54895": dict(year=2014, src="doi", doi="10.14456/becj.2014.27",
                  title_en="A Development of Operating Process Model for TQA Implementation",
                  abs_en_start="The purpose of this paper", n_auth=4, kw=(3, 3),
                  refs=0, counted=0, self_only=False, flags=[]),
    "74141": dict(year=2016, src="published", doi="10.14456/becj.2016.34",
                  title_en="Developmentof Production Supervisor’s Competency Standards in the Automotive Part Industries",
                  abs_en_start="This research aims to study the production", n_auth=2, kw=(4, 4),
                  refs=1, counted=0, self_only=True, flags=[]),
    "54905": dict(year=2013, src="published", doi="10.14456/becj.2013.20",
                  title_en="The Study of Employees’ Competency Requirement in MICE Industry of Thailand",
                  abs_en_start="The research objectives were", n_auth=2, kw=(5, 6),
                  refs=0, counted=0, self_only=False, flags=["thai_pua_repaired"]),
    "54875": dict(year=2014, src="doi", doi="10.14456/becj.2014.24",
                  title_en="Daily Newspapers Reading by Naresuan University Freshmen",
                  abs_en_start="This research aims to study daily", n_auth=1, kw=(3, 3),
                  refs=0, counted=0, self_only=False, flags=[]),
    "62409": dict(year=2016, src="published", doi="10.14456/becj.2016.13",
                  title_en_start="Effectiveness of Innovative Social Marketing Communication",
                  abs_en_start="This research aimed to study the effectiveness", n_auth=2, kw=(5, 5),
                  refs=1, counted=0, self_only=True, flags=[]),
    "91640": dict(year=2017, src="published", doi="10.14456/becj.2017.2",
                  title_en="Cultural Strategies for Thailand to be a High-Income Country",
                  abs_en_start="Many factors are involved", n_auth=1, kw=(5, 5),
                  refs=1, counted=0, self_only=True, flags=[]),
    "62430": dict(year=2016, src="published", doi="10.14456/becj.2016.18",
                  title_en="Communication Proficiency of Comedy Show “Jam Aud Na Marn”",
                  abs_en_start="The study of the Communication Proficiency", n_auth=1, kw=(3, 3),
                  refs=1, counted=0, self_only=True, flags=[]),
    "87805": dict(year=2018, src="published", doi="",
                  title_en="Marketing Mix Affecting the Decision Making on Purchasing the Products of Akha Ama Coffee",
                  abs_th="", abs_en_start="This research aimed to study the marketing mix", n_auth=5, kw=(3, 0),
                  refs=14, counted=14, self_only=False, flags=["stat_symbols_missing"]),
    "74136": dict(year=2016, src="published", doi="10.14456/becj.2016.29",
                  title_en="Barriers to e-commerce adoption in Thai small and medium enterprises",
                  abs_en_start="This research studies of barriers", n_auth=1, kw=(4, 4),
                  refs=1, counted=0, self_only=True, flags=[]),
}


def _parse(thaijo_dir, art_id):
    p = thaijo_dir / f"so02_BECJournal_{art_id}.md"
    return parse_markdown(p.read_text(encoding="utf-8"), p.name)


@pytest.mark.parametrize("art_id", sorted(GOLDEN))
def test_golden_real_files(thaijo_dir, art_id):
    g, r = GOLDEN[art_id], _parse(thaijo_dir, art_id)
    assert r["article_id"] == f"so02:BECJournal:{art_id}"
    assert r["journal_name"] == "BECJournal"
    assert (r["year"], r["year_source"]) == (g["year"], g["src"])
    assert r["doi"] == g["doi"]
    if "title_th" in g:
        assert r["title_th"] == g["title_th"]
    if "title_en" in g:
        assert r["title_en"] == g["title_en"]
    if "title_en_start" in g:
        assert r["title_en"].startswith(g["title_en_start"])
    if "abs_en" in g:
        assert r["abstract_en"] == g["abs_en"]
    if "abs_en_start" in g:
        assert r["abstract_en"].startswith(g["abs_en_start"])
    if "abs_th" in g:
        assert r["abstract_th"] == g["abs_th"]
    assert len(r["authors"]) == g["n_auth"]
    assert (len(r["keywords_th"]), len(r["keywords_en"])) == g["kw"]
    assert len(r["references"]) == g["refs"]
    assert r["n_references"] == g["counted"]
    assert r["self_citation_only"] is g["self_only"]
    assert r["text_quality"] == g["flags"]
    assert "DOI" not in r["abstract_en"] and "DOI" not in r["abstract_th"]


def test_pua_file_text_is_repaired(thaijo_dir):
    r = _parse(thaijo_dir, "54905")
    assert "ความต้องการ" in r["abstract_th"]
    assert "เจ้าหน้าที่" in r["abstract_th"]
    assert r["keywords_th"][0] == "ความต้องการ"
    assert r["authors"][1]["role"] == "รองศาสตราจารย์"
    assert r["authors"][1]["affiliation_th"].startswith("ภาควิชาการท่องเที่ยว")


def test_roles_students_and_nested_affiliations(thaijo_dir):
    tqa = _parse(thaijo_dir, "54895")
    assert tqa["authors"][0]["role"] == "นิสิตปริญญาเอก" and tqa["authors"][0]["is_student"]
    assert tqa["authors"][1]["role"] == "รองศาสตราจารย์" and not tqa["authors"][1]["is_student"]
    gp = _parse(thaijo_dir, "62409")
    a0, a1 = gp["authors"]
    assert a0["is_student"] and a0["role"] == "นักศึกษาปริญญาโท"
    assert a0["affiliation_en"].startswith("Department of Innovative Marketing Communication")
    assert a1["role"] == "ผู้ช่วยศาสตราจารย์"
    assert a1["affiliation_en"].startswith("Graduate School of Communication Arts")
    en = _parse(thaijo_dir, "62642")["authors"][0]
    assert (en["name"], en["name_en"]) == ("ชาตรี ปรีดาอนันทสุข", "Chatree Preedaananthasuk")
    assert en["affiliation_th"] == "" and en["affiliation_en"].startswith("Faculty of Business")


def test_bom_and_crlf_parse_identically(thaijo_dir):
    text = (thaijo_dir / "so02_BECJournal_54895.md").read_text(encoding="utf-8")
    variant = "\N{ZERO WIDTH NO-BREAK SPACE}" + text.replace("\n", "\r\n")
    assert parse_markdown(variant) == parse_markdown(text)


def test_split_title_variants():
    assert split_title("ภาษาไทยยาวพอสมควร [An English Title Here]") == ("ภาษาไทยยาวพอสมควร", "An English Title Here")
    # the alternate-language part must hold >= 15 letters (Thai consonants + Latin) to count as a title
    assert split_title("An English Title Here (ชื่อเรื่องภาษาไทยที่ยาวพอสมควรแน่นอน)") == (
        "ชื่อเรื่องภาษาไทยที่ยาวพอสมควรแน่นอน", "An English Title Here")
    th, en = split_title("การพัฒนาตัวแบบรางวัลคุณภาพแห่งชาติ (TQA)")      # short acronym stays in the title
    assert th.endswith("(TQA)") and en == ""


def test_rejoin_references_wrapped_lines(thaijo_dir):
    refs = _parse(thaijo_dir, "62642")["references"]
    assert len(refs) == 13
    assert sum(r["translated"] for r in refs) == 3
    assert refs[0]["year"] == 2013                      # (2556) BE → CE
    assert refs[5]["text"].startswith("Freeman, R.E.") and refs[5]["year"] == 2010
    assert refs[9]["text"].startswith("Webometrics.") and refs[9]["year"] == 2016


def test_resolve_year_rules():
    assert resolve_year("2016-06-29", "") == (2016, "published")
    assert resolve_year("1970-01-01", "10.14456/becj.2014.27") == (2014, "doi")
    assert resolve_year("2559-01-01", "") == (2016, "published")
    assert resolve_year("", "") == (None, "")


def test_fill_years_from_issue():
    recs = [{"year": 2015, "issue_url": "u1", "year_source": "published"},
            {"year": None, "issue_url": "u1", "year_source": ""},
            {"year": None, "issue_url": "u2", "year_source": ""}]
    fill_years_from_issue(recs)
    assert recs[1]["year"] == 2015 and recs[1]["year_source"] == "issue_median"
    assert recs[2]["year"] is None


def test_rejoin_handles_empty():
    assert rejoin_references([]) == []


@settings(max_examples=300, deadline=None)
@given(st.text())
def test_parser_never_raises_on_arbitrary_text(text):
    r = parse_markdown(text)
    assert set(r) >= {"article_id", "year", "authors", "references", "text_quality"}


LINES = ["# ชื่อเรื่อง", "**Journal:** J", "**Published:** 1970-01-01", "**Authors:**", "- ก (", "- x [y] ((",
         "**Keywords:** ,,;", "## Abstract", "   DOI:   ", "## References", "- (2559)", "- Smith, A. (", ""]


@settings(max_examples=300, deadline=None)
@given(st.lists(st.sampled_from(LINES), max_size=30))
def test_parser_never_raises_on_broken_structure(lines):
    parse_markdown("\n".join(lines))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_thaijo_md.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.sources'`

- [ ] **Step 3: Implement `pipeline/atlas/sources/thaijo_md.py`**

```python
"""Parser for ThaiJO-scraped Markdown articles (one .md file per article).

Pure functions, stdlib + atlas.thai only. `parse_markdown` never raises on malformed
input: missing sections simply yield empty values.
"""
from __future__ import annotations

import re
from statistics import median

from atlas.thai import (
    LATIN_LETTER,
    MARKS,
    THAI_LETTER,
    clean_text,
    fold_thai,
    has_pua,
    norm_key,
    repair_glyphs,
    thai_ratio,
)

MAI_THO = "\N{THAI CHARACTER MAI THO}"
BOM = "\N{ZERO WIDTH NO-BREAK SPACE}"

_FIELD = re.compile(r"^\*\*(?P<key>[A-Za-z ]+):\*\*\s*(?P<val>.*)$")
_URL_ID = re.compile(r"https?://(?P<host>[^./]+)\.[^/]+/index\.php/(?P<journal>[^/]+)/article/view/(?P<id>\d+)")
_DOI = re.compile(r"DOI:\s*(?:https?://(?:dx\.)?doi\.org/)?(?P<doi>10\.\d{4,9}/\S+)", re.I)
_DOI_YEAR = re.compile(r"\.((?:19|20)\d{2})\.\d+$")
_PAREN_YEAR = re.compile(r"\([^()]*?\b((?:19|20|25)\d{2})[a-z]?\b[^()]*?\)")
_LATIN_AUTHOR_START = re.compile(r"^[A-Z][A-Za-z'\-]+,\s+(?:[A-Z]\.|[A-Z][a-z]+)")
_LONE_INITIAL = re.compile(r"^[A-Z]\.\s*\(")
_SEG_SPLIT = re.compile(r"\s{2,}")
_ABSTRACT_LABEL = re.compile(r"^(abstract|บทคัดย่อ)[:.]?$", re.I)
_STAT_SYMBOL_LOSS = re.compile(r"\(\s*=\s*\d")

STUDENT_ROLES = ["นักศึกษาปริญญาเอก", "นักศึกษาปริญญาโท", "นิสิตปริญญาเอก", "นิสิตปริญญาโท",
                 "นักศึกษา", "นิสิต", "Graduate student", "Ph.D. student", "PhD student",
                 "Doctoral student", "Master's student", "Student"]
ACADEMIC_ROLES = ["รองศาสตราจารย์", "ผู้ช่วยศาสตราจารย์", "ศาสตราจารย์", "อาจารย์",
                  "Associate Professor", "Assistant Professor", "Professor", "Lecturer"]


# ------------------------------------------------------------------ sections
def _split_sections(text: str) -> tuple[str, dict, dict[str, str]]:
    """→ (h1 title, header fields, {lower-case section name: body})."""
    lines = text.replace("\r\n", "\n").lstrip(BOM).split("\n")
    title = ""
    fields: dict = {}
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    key: str | None = None
    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(buf).strip()
            current, buf = line[3:].strip().lower(), []
            continue
        if current:
            buf.append(line)
            continue
        m = _FIELD.match(line.strip())
        if m:
            key = m.group("key").strip().lower()
            fields[key] = m.group("val").strip()
        elif line.strip().startswith("- ") and key == "authors":
            fields.setdefault("authors_list", []).append(line.strip()[2:].strip())
    if current:
        sections[current] = "\n".join(buf).strip()
    return title, fields, sections


# ------------------------------------------------------------------ title
def split_title(h1: str) -> tuple[str, str]:
    """'TH [EN]' or 'EN (TH)' or single-language → (title_th, title_en)."""
    h1 = clean_text(h1)
    m = re.match(r"^(?P<main>.+?)\s*[\[(](?P<alt>[^\[\]()]+)[\])]\s*$", h1)
    if m:
        main, alt = m.group("main").strip(), m.group("alt").strip()
        main_th, alt_th = thai_ratio(main) > 0.5, thai_ratio(alt) > 0.5
        substantial = len(THAI_LETTER.findall(alt)) + len(LATIN_LETTER.findall(alt)) >= 15
        if main_th != alt_th and substantial:
            return (main, alt) if main_th else (alt, main)
    return (h1, "") if thai_ratio(h1) > 0.5 else ("", h1)


# ------------------------------------------------------------------ abstract
def split_abstract(raw: str, need_en_title: bool) -> dict:
    """ThaiJO joins TH abstract, EN title, EN abstract and DOI with runs of >=2 spaces."""
    raw = repair_glyphs(raw).replace("\n", " ")
    doi = ""
    m = _DOI.search(raw)
    if m:
        doi = m.group("doi").rstrip(".,;)")
        raw = raw[: m.start()]
    segs = [s.strip() for s in _SEG_SPLIT.split(raw) if s.strip()]
    segs = [s for s in segs if not _ABSTRACT_LABEL.match(s)]
    th_parts: list[str] = []
    en_segs: list[str] = []
    for s in segs:
        (th_parts if thai_ratio(s) > 0.5 else en_segs).append(s)
    en_title = ""
    if need_en_title and len(en_segs) >= 2:
        first = en_segs[0]
        if len(first) <= 250 and not first.endswith("."):
            title_parts, i = [first], 1
            # a title broken by a space run continues with a lower-case fragment
            while (i < len(en_segs) - 1 and en_segs[i][:1].islower()
                   and len(en_segs[i]) <= 120 and not en_segs[i].endswith(".")):
                title_parts.append(en_segs[i])
                i += 1
            en_title, en_segs = " ".join(title_parts), en_segs[i:]
    return {
        "abstract_th": clean_text(" ".join(th_parts)),
        "abstract_en": clean_text(" ".join(en_segs)),
        "title_en_from_abstract": clean_text(en_title),
        "doi": doi,
    }


# ------------------------------------------------------------------ keywords
def split_keywords(raw: str) -> tuple[list[str], list[str]]:
    th: list[str] = []
    en: list[str] = []
    for k in re.split(r"[,;]", clean_text(raw)):
        k = k.strip()
        if k:
            (th if thai_ratio(k) > 0.5 else en).append(k)
    return th, en


# ------------------------------------------------------------------ authors
def _role_regex(word: str) -> re.Pattern:
    # tolerate missing/extra Thai marks between letters (marks are often lost in extraction)
    parts = [re.escape(ch) + f"[{MARKS}]*" for ch in fold_thai(word)]
    return re.compile(r"^\s*" + "".join(parts) + r"\s*(?:ประจำ)?\s*", re.I)


_ROLE_PATTERNS = [(w, _role_regex(w), w in STUDENT_ROLES) for w in STUDENT_ROLES + ACADEMIC_ROLES]


def _strip_role(s: str) -> tuple[str, str, bool]:
    for word, rx, is_student in _ROLE_PATTERNS:
        m = rx.match(s)
        if m:
            return s[m.end():].strip().lstrip(",;:- ").strip(), word, is_student
    return s.strip(), "", False


def _outer_paren(s: str) -> tuple[str, str]:
    """'name ... (affiliation (nested))' → (prefix, content of the trailing top-level group)."""
    depth, start = 0, 0
    for i, ch in enumerate(s):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0 and s[i + 1:].strip() == "":
                return s[:start].strip(), s[start + 1:i].strip()
    return s.strip(), ""


def parse_author(line: str) -> dict:
    line = clean_text(line)
    head, aff = _outer_paren(line)
    name, name_en = head, ""
    m = re.match(r"^(?P<name>[^\[]+?)\s*\[(?P<en>[^\]]+)\]\s*$", head)
    if m:
        name, name_en = m.group("name").strip(), m.group("en").strip()
    aff_th, aff_en = aff, ""
    inner = re.match(r"^(?P<th>.*?)\s*\((?P<en>.*)\)\s*$", aff)
    if inner and thai_ratio(inner.group("th")) > 0.5 and thai_ratio(inner.group("en")) <= 0.5:
        aff_th, aff_en = inner.group("th"), inner.group("en")
    elif aff and thai_ratio(aff) <= 0.5:
        aff_th, aff_en = "", aff
    aff_th, role, is_student = _strip_role(aff_th)
    aff_en, role_en, student_en = _strip_role(aff_en)
    return {"name": name, "name_en": name_en,
            "affiliation_th": aff_th, "affiliation_en": aff_en,
            "role": role or role_en, "is_student": is_student or student_en}


# ------------------------------------------------------------------ references
def rejoin_references(lines: list[str]) -> list[dict]:
    """ThaiJO wraps long references onto new bullets — stitch them back together."""
    refs: list[dict] = []
    translated = False
    for raw in lines:
        line = clean_text(raw.strip().lstrip("-").strip())
        if not line:
            continue
        if re.fullmatch(r"translated (thai )?references", line, re.I):
            translated = True
            continue
        cur = refs[-1] if refs else None
        has_year = bool(_PAREN_YEAR.search(line[:150]))
        starts_new = (
            cur is None
            or (has_year and cur["year"] is not None and not _LONE_INITIAL.match(line))
            or (bool(_LATIN_AUTHOR_START.match(line)) and cur["year"] is not None
                and cur["text"].endswith("."))
        )
        if starts_new or cur is None:
            refs.append({"text": line, "year": None, "translated": translated})
        else:
            cur["text"] = f"{cur['text']} {line}"
        last = refs[-1]
        if last["year"] is None:
            y = _PAREN_YEAR.search(last["text"])
            if y:
                year = int(y.group(1))
                last["year"] = year - 543 if year > 2400 else year
    for r in refs:
        r["lang"] = "th" if thai_ratio(r["text"]) > 0.3 else "latin"
    return refs


# ------------------------------------------------------------------ year
def resolve_year(published: str, doi: str) -> tuple[int | None, str]:
    m = re.match(r"^(\d{4})", published or "")
    if m and int(m.group(1)) != 1970:          # 1970-01-01 = date lost in the scrape
        y = int(m.group(1))
        return (y - 543 if y > 2400 else y), "published"
    m = _DOI_YEAR.search(doi or "")
    if m:
        return int(m.group(1)), "doi"
    return None, ""


def fill_years_from_issue(records: list[dict]) -> None:
    """Corpus-level pass: articles still missing a year take the median year of their issue."""
    by_issue: dict[str, list[int]] = {}
    for r in records:
        if r["year"] is not None and r["issue_url"]:
            by_issue.setdefault(r["issue_url"], []).append(r["year"])
    for r in records:
        if r["year"] is None and by_issue.get(r["issue_url"]):
            r["year"] = int(median(by_issue[r["issue_url"]]))
            r["year_source"] = "issue_median"


# ------------------------------------------------------------------ main
def parse_markdown(text: str, source_path: str = "") -> dict:
    h1, f, sec = _split_sections(text)
    title_th, title_en = split_title(h1)
    ab = split_abstract(sec.get("abstract", ""), need_en_title=not title_en)
    title_en = title_en or ab["title_en_from_abstract"]
    kw_th, kw_en = split_keywords(f.get("keywords", ""))
    authors = [parse_author(a) for a in f.get("authors_list", [])]

    url = f.get("article url", "")
    article_id, journal = "", f.get("journal", "")
    um = _URL_ID.search(url)
    if um:
        article_id = f"{um.group('host')}:{um.group('journal')}:{um.group('id')}"
        journal = journal or um.group("journal")
    year, year_source = resolve_year(f.get("published", ""), ab["doi"])

    ref_lines = [ln for ln in sec.get("references", "").split("\n") if ln.strip()]
    refs = rejoin_references(ref_lines)
    keys = [norm_key(t)[:40] for t in (title_th, title_en) if len(norm_key(t)) >= 12]
    for r in refs:
        r["self_citation"] = any(k in norm_key(r["text"]) for k in keys)
    counted = [r for r in refs if not r["self_citation"] and not r["translated"]]

    flags = ["thai_pua_repaired"] if has_pua(text) else []
    th_letters = len(THAI_LETTER.findall(ab["abstract_th"]))
    if th_letters >= 200 and ab["abstract_th"].count(MAI_THO) / th_letters < 0.005:
        flags.append("tone_marks_missing")
    if _STAT_SYMBOL_LOSS.search(ab["abstract_th"] + " " + ab["abstract_en"]):
        flags.append("stat_symbols_missing")

    return {
        "article_id": article_id,
        "source_path": source_path,
        "url": url,
        "issue_url": f.get("issue url", ""),
        "journal_name": journal,
        "published": f.get("published", ""),
        "year": year,
        "year_source": year_source,
        "pages": f.get("pages", ""),
        "title_th": title_th,
        "title_en": title_en,
        "abstract_th": ab["abstract_th"],
        "abstract_en": ab["abstract_en"],
        "doi": ab["doi"],
        "keywords_th": kw_th,
        "keywords_en": kw_en,
        "authors": authors,
        "references": refs,
        "n_references": len(counted),
        "has_references": bool(refs),
        "self_citation_only": bool(refs) and not counted and any(r["self_citation"] for r in refs),
        "text_quality": flags,
    }
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_thaijo_md.py -q`
Expected: all pass (11 golden + 10 others). Verified against the prototype: with the BOM stripped in `_split_sections`, BOM+CRLF variants of all 11 files parse identically to the originals; Attitudes references come out in order `0 ชาตรี(2013) … 5 Freeman(2010) … 9 Webometrics(2016) … 10–12 translated`.

- [ ] **Step 5: Commit**

```bash
git add pipeline/atlas/sources pipeline/tests/test_thaijo_md.py
git commit -m "feat(pipeline): ThaiJO Markdown parser with golden tests on 11 real files

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Validated configuration v2 (`atlas/config.py`, `config.example.yaml`, `configs/ci.yaml`)

**Files:**
- Modify: `pipeline/atlas/config.py`, `pipeline/config.example.yaml`
- Create: `pipeline/configs/ci.yaml`, `pipeline/tests/test_config.py`

**Interfaces:**
- Produces: `AtlasConfig` (pydantic, `extra="forbid"` everywhere) and `load_config(path: str | Path | None = None) -> dict` — a plain dict (so existing `cfg["section"]["key"]` access keeps working) with `pipeline.work_dir`, `pipeline.output_dir`, `pipeline.state_dir`, `input.path` resolved to absolute paths relative to the config file's directory (or the CWD when `path` is None).
- Config keys used by later tasks (exact names): see the YAML in Step 4.

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_config.py`**

```python
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from atlas.config import AtlasConfig, load_config

PIPELINE = Path(__file__).resolve().parent.parent


def _keys(d, prefix=""):
    out = set()
    for k, v in d.items():
        out.add(prefix + k)
        if isinstance(v, dict) and k != "columns":
            out |= _keys(v, prefix + k + ".")
    return out


def test_defaults_load_and_paths_are_absolute():
    cfg = load_config(None)
    for k in ("work_dir", "output_dir", "state_dir"):
        assert Path(cfg["pipeline"][k]).is_absolute()
    assert cfg["emerging"]["definition_version"] == 2


def test_example_yaml_is_valid_and_documents_every_key():
    raw = yaml.safe_load((PIPELINE / "config.example.yaml").read_text(encoding="utf-8"))
    AtlasConfig.model_validate(raw)
    assert _keys(raw) == _keys(AtlasConfig().model_dump())


def test_unknown_key_is_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("emerging:\n  recnt_window: 3\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="recnt_window"):
        load_config(p)


def test_bad_provider_is_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("embedding:\n  provider: magic\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(p)


def test_relative_paths_resolve_against_config_dir(tmp_path):
    p = tmp_path / "sub" / "c.yaml"
    p.parent.mkdir()
    p.write_text("pipeline:\n  work_dir: ./w\ninput:\n  path: ../data\n", encoding="utf-8")
    cfg = load_config(p)
    assert Path(cfg["pipeline"]["work_dir"]) == (tmp_path / "sub" / "w").resolve()
    assert Path(cfg["input"]["path"]) == (tmp_path / "data").resolve()


def test_ci_config_loads():
    cfg = load_config(PIPELINE / "configs" / "ci.yaml")
    assert cfg["embedding"]["provider"] == "lite"
    assert cfg["labeling"]["provider"] == "off"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL — `ImportError: cannot import name 'AtlasConfig'`

- [ ] **Step 3: Replace `pipeline/atlas/config.py`**

```python
"""Validated configuration for the TCI Research Atlas pipeline (pydantic v2).

`load_config()` returns a plain dict so modules keep using cfg["section"]["key"].
Every field has a default equal to config.example.yaml; unknown keys are errors.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PipelineCfg(_Strict):
    name: str = "tci-research-atlas"
    work_dir: str = "./work"          # regenerable checkpoints — safe to delete
    output_dir: str = "./output"
    state_dir: str = "./state"        # persistent: embedding store, label cache, previous run
    seed: int = 42


class DedupCfg(_Strict):
    enabled: bool = True


class InputCfg(_Strict):
    format: Literal["thaijo_md", "table"] = "thaijo_md"
    path: str = "../corpus"
    glob: str = "**/*.md"
    workers: int = Field(4, ge=1)
    min_year: int = 1990
    max_year: int | None = None
    columns: dict[str, str] = Field(default_factory=lambda: {
        "article_id": "id", "title_th": "title_th", "title_en": "title_en",
        "abstract_th": "abstract_th", "abstract_en": "abstract_en",
        "keywords_th": "keywords_th", "keywords_en": "keywords_en",
        "authors": "authors", "affiliations": "affiliations", "journal_name": "journal",
        "year": "year", "doi": "doi", "url": "url",
    })
    dedup: DedupCfg = Field(default_factory=DedupCfg)


class ApiEmbedCfg(_Strict):
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "ATLAS_API_KEY"
    model: str = "text-embedding-3-large"
    dimensions: int | None = 1024
    batch_size: int = 256
    max_retries: int = 6
    checkpoint_every: int = 5000


class LocalEmbedCfg(_Strict):
    model: str = "BAAI/bge-m3"
    device: str = "cuda"
    batch_size: int = 32
    fp16: bool = True
    max_seq_length: int = 1024
    checkpoint_every: int = 5000


class LiteEmbedCfg(_Strict):
    dim: int = 128
    ngram_min: int = 2
    ngram_max: int = 4
    max_features: int = 100_000
    min_df: int = 2


class EmbeddingCfg(_Strict):
    provider: Literal["api", "local", "lite"] = "lite"
    api: ApiEmbedCfg = Field(default_factory=ApiEmbedCfg)
    local: LocalEmbedCfg = Field(default_factory=LocalEmbedCfg)
    lite: LiteEmbedCfg = Field(default_factory=LiteEmbedCfg)
    doc_fields: list[str] = Field(default_factory=lambda: [
        "title_th", "title_en", "keywords_th", "keywords_en", "abstract_th", "abstract_en"])
    max_chars_per_doc: int = 6000


class FineLevelCfg(_Strict):
    umap_n_components: int = 10
    umap_n_neighbors: int = 15
    umap_min_dist: float = 0.0
    hdbscan_min_cluster_size: int = 150
    hdbscan_min_samples: int = 20


class ClusteringCfg(_Strict):
    reducer: Literal["umap", "pca"] = "umap"
    pca_dims: int = 128
    umap_fit_sample: int = 150_000
    fine: FineLevelCfg = Field(default_factory=FineLevelCfg)
    merge_similarity: float = Field(0.8, ge=0.0, le=1.0)
    outlier_min_similarity: float = Field(0.35, ge=-1.0, le=1.0)
    n_groups: int = Field(20, ge=1)
    ctfidf_top_n: int = 20
    ctfidf_max_docs_per_topic: int = 400


class LabelApiCfg(_Strict):
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "ATLAS_API_KEY"
    model: str = "gpt-5-mini"
    temperature: float = 0.2
    max_retries: int = 5
    concurrency: int = 8


class LabelingCfg(_Strict):
    provider: Literal["api", "off"] = "off"
    api: LabelApiCfg = Field(default_factory=LabelApiCfg)
    n_repr_docs: int = 8
    mmr_lambda: float = Field(0.7, ge=0.0, le=1.0)


class SizeCfg(_Strict):
    rule: Literal["quantile", "absolute"] = "quantile"
    large_quantile: float = Field(0.75, gt=0.0, lt=1.0)
    large_share: float = 0.015


class EmergingRuleCfg(_Strict):
    min_growth_lo: float = 0.10
    min_share_ratio: float = 1.8


class HotRuleCfg(_Strict):
    min_growth_lo: float = 0.0


class DecliningRuleCfg(_Strict):
    max_growth_hi: float = 0.0
    max_share_ratio: float = 0.8


class BreadthCfg(_Strict):
    min_journals: int = 3
    min_orgs: int = 3
    max_new_journal_share: float = 0.5
    min_org_coverage: float = 0.5     # apply the institution rule only when >= 50% of R articles have affiliations


class BurstCfg(_Strict):
    s: float = 2.0
    gamma: float = 1.0


class ScoreWeightsCfg(_Strict):
    growth: float = 0.30
    acceleration: float = 0.20
    burst: float = 0.15
    novelty: float = 0.15
    coherence: float = 0.10
    breadth: float = 0.10


class EmergingCfg(_Strict):
    definition_version: Literal[2] = 2
    min_year_complete: int | None = None
    backfill_min_ratio: float = 0.6
    recent_window: int = 3
    baseline_window: int = 5
    trend_window: int = 5
    min_articles_recent: int = 30
    ci_level: float = Field(0.90, gt=0.5, lt=1.0)
    size: SizeCfg = Field(default_factory=SizeCfg)
    emerging: EmergingRuleCfg = Field(default_factory=EmergingRuleCfg)
    hot: HotRuleCfg = Field(default_factory=HotRuleCfg)
    declining: DecliningRuleCfg = Field(default_factory=DecliningRuleCfg)
    breadth: BreadthCfg = Field(default_factory=BreadthCfg)
    burst: BurstCfg = Field(default_factory=BurstCfg)
    score_weights: ScoreWeightsCfg = Field(default_factory=ScoreWeightsCfg)


class ForecastCfg(_Strict):
    horizon: int = 2
    min_history_years: int = 6
    models: list[Literal["naive", "linear", "poisson"]] = Field(
        default_factory=lambda: ["naive", "linear", "poisson"])
    backtest_years: int = 3
    min_skill: float = 0.0


class LayoutCfg(_Strict):
    umap_2d_neighbors: int = 12
    umap_2d_min_dist: float = 0.35
    view_w: int = 1680
    view_h: int = 1040
    edge_similarity_threshold: float = 0.55
    max_edges_per_node: int = 4


class ExportCfg(_Strict):
    formats: list[Literal["json", "csv"]] = Field(default_factory=lambda: ["json", "csv"])
    include_forecast_in_json: bool = True


class AtlasConfig(_Strict):
    pipeline: PipelineCfg = Field(default_factory=PipelineCfg)
    input: InputCfg = Field(default_factory=InputCfg)
    embedding: EmbeddingCfg = Field(default_factory=EmbeddingCfg)
    clustering: ClusteringCfg = Field(default_factory=ClusteringCfg)
    labeling: LabelingCfg = Field(default_factory=LabelingCfg)
    emerging: EmergingCfg = Field(default_factory=EmergingCfg)
    forecast: ForecastCfg = Field(default_factory=ForecastCfg)
    layout: LayoutCfg = Field(default_factory=LayoutCfg)
    export: ExportCfg = Field(default_factory=ExportCfg)


def _resolve(p: str, base: Path) -> str:
    q = Path(p)
    return str((q if q.is_absolute() else base / q).resolve())


def load_config(path: str | Path | None = None) -> dict:
    """Validate a YAML config (missing keys take defaults) and resolve relative paths."""
    raw: dict = {}
    base = Path.cwd()
    if path:
        p = Path(path)
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        base = p.resolve().parent
    cfg = AtlasConfig.model_validate(raw).model_dump()
    for key in ("work_dir", "output_dir", "state_dir"):
        cfg["pipeline"][key] = _resolve(cfg["pipeline"][key], base)
    cfg["input"]["path"] = _resolve(cfg["input"]["path"], base)
    return cfg
```

- [ ] **Step 4: Replace `pipeline/config.example.yaml`** (every key, Thai comments)

```yaml
# ============================================================
# TCI Research Atlas — Pipeline configuration (v2)
# คัดลอกเป็น config.yaml แล้วแก้ตามสภาพแวดล้อม — key ที่ไม่รู้จักจะถูกปฏิเสธ (กันพิมพ์ผิด)
# ============================================================

pipeline:
  name: tci-research-atlas
  work_dir: ./work            # checkpoint ที่สร้างใหม่ได้ — ลบทิ้งได้เสมอ
  output_dir: ./output        # ผลลัพธ์สำหรับเว็บ/นักวิเคราะห์
  state_dir: ./state          # ข้อมูลถาวรข้ามรอบ: embedding store, label cache, รอบก่อน — ห้ามลบ
  seed: 42

input:
  format: thaijo_md           # thaijo_md = โฟลเดอร์ไฟล์ .md จาก ThaiJO | table = csv/json/jsonl/parquet ไฟล์เดียว
  path: ../corpus             # โฟลเดอร์ .md (หรือไฟล์ตารางถ้า format: table)
  glob: "**/*.md"
  workers: 4                  # จำนวน process ตอน parse (ใช้เมื่อไฟล์ > 2,000)
  min_year: 1990              # ตัดปีผิดปกติ (หลังแปลง พ.ศ.→ค.ศ.)
  max_year: null              # null = ปีปัจจุบัน + 1
  columns:                    # ใช้เฉพาะ format: table — ชื่อคอลัมน์มาตรฐาน: ชื่อคอลัมน์ในไฟล์
    article_id: id
    title_th: title_th
    title_en: title_en
    abstract_th: abstract_th
    abstract_en: abstract_en
    keywords_th: keywords_th
    keywords_en: keywords_en
    authors: authors
    affiliations: affiliations
    journal_name: journal
    year: year
    doi: doi
    url: url
  dedup:
    enabled: true             # ตัดซ้ำด้วย article_id → DOI → ชื่อเรื่อง+ปี (เก็บ record ที่ครบที่สุด)

embedding:
  provider: lite              # api | local | lite (lite = TF-IDF+SVD บน CPU สำหรับทดสอบ/CI — คุณภาพต่ำกว่า)
  api:                        # OpenAI-compatible (OpenAI, Gemini, OpenRouter, vLLM, Ollama)
    base_url: https://api.openai.com/v1
    api_key_env: ATLAS_API_KEY
    model: text-embedding-3-large
    dimensions: 1024
    batch_size: 256
    max_retries: 6
    checkpoint_every: 5000
  local:                      # sentence-transformers บน GPU/CPU ของเราเอง
    model: BAAI/bge-m3
    device: cuda
    batch_size: 32
    fp16: true
    max_seq_length: 1024      # 512 ตัดบทคัดย่อไทยทิ้งเกือบหมด — BGE-M3 รองรับถึง 8192
    checkpoint_every: 5000
  lite:
    dim: 128
    ngram_min: 2
    ngram_max: 4
    max_features: 100000
    min_df: 2
  doc_fields: [title_th, title_en, keywords_th, keywords_en, abstract_th, abstract_en]
  max_chars_per_doc: 6000

clustering:
  reducer: umap               # umap | pca
  pca_dims: 128               # ลดมิติด้วย PCA ก่อน UMAP เมื่อ embedding ใหญ่กว่านี้
  umap_fit_sample: 150000     # fit UMAP บนตัวอย่างแล้ว transform ที่เหลือ (ประหยัด RAM ที่ 500K)
  fine:
    umap_n_components: 10
    umap_n_neighbors: 15
    umap_min_dist: 0.0
    hdbscan_min_cluster_size: 150
    hdbscan_min_samples: 20
  merge_similarity: 0.8       # รวม cluster ที่ centroid cosine ≥ ค่านี้ (แก้ HDBSCAN over-split)
  outlier_min_similarity: 0.35  # outlier เข้าหัวข้อเฉพาะเมื่อใกล้พอ ไม่งั้น "ยังไม่จัดหมวด"
  n_groups: 20                # จำนวนกลุ่มใหญ่บนแผนที่ (P1 จะเปลี่ยนเป็น OpenAlex fields)
  ctfidf_top_n: 20
  ctfidf_max_docs_per_topic: 400

labeling:
  provider: "off"             # api | "off" (ต้องใส่เครื่องหมายคำพูด — YAML อ่าน off เปล่า ๆ เป็น false) — off = ตั้งชื่อจากคำสำคัญของผู้เขียน + c-TF-IDF
  api:
    base_url: https://api.openai.com/v1
    api_key_env: ATLAS_API_KEY
    model: gpt-5-mini         # ตั้งเป็นโมเดลรุ่นปัจจุบันที่ถนัดไทยได้ เช่น Claude Haiku / Gemini Flash / Typhoon
    temperature: 0.2
    max_retries: 5
    concurrency: 8
  n_repr_docs: 8              # บทความตัวแทน (ใกล้ centroid + กระจายด้วย MMR)
  mmr_lambda: 0.7

# ---------- Emerging v2 — นิยามเต็มใน docs/EMERGING_SPEC.md ----------
emerging:
  definition_version: 2
  min_year_complete: null     # null = backfill guard อัตโนมัติ
  backfill_min_ratio: 0.6     # ปีล่าสุดที่ยอด < 60% ของ median ถือว่ายังไม่ครบ
  recent_window: 3            # R
  baseline_window: 5          # B (ก่อน R)
  trend_window: 5             # W (ใช้วัดอัตราโตของ share ด้วย GLM)
  min_articles_recent: 30     # ต่ำกว่านี้ = LOW_DATA (ไม่ฟันธง)
  ci_level: 0.90
  size:
    rule: quantile            # quantile | absolute
    large_quantile: 0.75      # "ใหญ่" = share_R ≥ quantile นี้ของหัวข้อที่จำแนกได้
    large_share: 0.015        # ใช้เมื่อ rule: absolute
  emerging:
    min_growth_lo: 0.10       # CI ล่างของอัตราโตของ share ≥ +10%/ปี
    min_share_ratio: 1.8      # share_R / share_B
  hot:
    min_growth_lo: 0.0        # หัวข้อใหญ่ที่ CI ล่าง > 0
  declining:
    max_growth_hi: 0.0        # CI บน < 0
    max_share_ratio: 0.8
  breadth:
    min_journals: 3           # ใน R ต้องมี ≥ 3 วารสาร
    min_orgs: 3               # และ ≥ 3 สถาบัน
    max_new_journal_share: 0.5  # บทความจากวารสารที่เพิ่งเข้าระบบใน R ต้อง < 50%
    min_org_coverage: 0.5     # ใช้เกณฑ์สถาบันเฉพาะเมื่อบทความใน R มีข้อมูลสังกัด ≥ 50% (กันข้อมูลตารางที่ไม่มีสังกัด)
  burst:
    s: 2.0                    # Kleinberg: อัตราในสถานะ burst = s × ปกติ
    gamma: 1.0                # ค่าเข้าสถานะ burst = γ·ln(T)
  score_weights:
    growth: 0.30
    acceleration: 0.20
    burst: 0.15
    novelty: 0.15
    coherence: 0.10
    breadth: 0.10

forecast:
  horizon: 2
  min_history_years: 6
  models: [naive, linear, poisson]
  backtest_years: 3
  min_skill: 0.0              # แสดงตัวเลขเฉพาะเมื่อ skill เทียบ naive > ค่านี้ (ไม่งั้น "แนวโน้มไม่แน่นอน")

layout:
  umap_2d_neighbors: 12
  umap_2d_min_dist: 0.35
  view_w: 1680
  view_h: 1040
  edge_similarity_threshold: 0.55
  max_edges_per_node: 4

export:
  formats: [json, csv]
  include_forecast_in_json: true
```

- [ ] **Step 5: Create `pipeline/configs/ci.yaml`**

```yaml
# Synthetic end-to-end config (CPU only). Paths are relative to this file → pipeline/.ci/
pipeline:
  work_dir: ../.ci/work
  output_dir: ../.ci/output
  state_dir: ../.ci/state
  seed: 42
input:
  format: thaijo_md
  path: ../.ci/synth
  workers: 2
embedding:
  provider: lite
clustering:
  fine:
    umap_n_components: 10
    umap_n_neighbors: 15
    umap_min_dist: 0.0
    hdbscan_min_cluster_size: 40
    hdbscan_min_samples: 10
  merge_similarity: 0.8
  outlier_min_similarity: 0.35
  n_groups: 6
labeling:
  provider: "off"            # quoted: bare `off` is YAML boolean false
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_config.py -q`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/config.py pipeline/config.example.yaml pipeline/configs/ci.yaml pipeline/tests/test_config.py
git commit -m "feat(pipeline): pydantic-validated config v2 + CI config

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: Ingest rewrite + institution keys (`atlas/ingest.py`, `atlas/orgs.py`)

**Files:**
- Create: `pipeline/atlas/orgs.py`, `pipeline/tests/test_ingest.py`
- Modify: `pipeline/atlas/ingest.py` (full rewrite), `pipeline/tests/conftest.py` (add `make_cfg`)

**Interfaces:**
- Consumes: `parse_markdown`, `fill_years_from_issue` (Task 3); `clean_text`, `norm_key` (Task 2); `load_config` (Task 4).
- Produces:
  - `org_key(affiliation_th: str, affiliation_en: str) -> str` — coarse institution key (empty when no affiliation).
  - `read_thaijo_corpus(root: str | Path, pattern: str = "**/*.md", workers: int = 1) -> list[dict]` (parsed records, years filled from issues; files whose name starts with `_` are skipped).
  - `records_to_tables(records: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]` → `(articles, authors, references)`.
  - `ingest(cfg: dict) -> pd.DataFrame` writing `work/01_articles`, `work/01_authors`, `work/01_references`.
  - `ARTICLE_COLUMNS` (list) — article table columns: `article_id, source_path, url, issue_url, journal_name, published, year (Int64), year_source, pages, doi, title_th, title_en, abstract_th, abstract_en, keywords_th, keywords_en, authors, affiliations, n_authors, n_student_authors, n_references, has_references, self_citation_only, text_quality` + convenience `title, abstract, keywords`. List-valued fields are joined with `"; "`.
  - authors table: `article_id, position, name, name_en, affiliation_th, affiliation_en, role, is_student, org_key`.
  - references table: `article_id, position, text, year, lang, translated, self_citation`.
  - conftest fixture `make_cfg(tmp_path) -> Callable[[Path, str], dict]`.

- [ ] **Step 1: Add the `make_cfg` fixture to `pipeline/tests/conftest.py`**

```python
from atlas.config import load_config


@pytest.fixture
def make_cfg(tmp_path):
    """cfg factory with all dirs inside tmp_path; usage: cfg = make_cfg(input_path, "thaijo_md")."""
    def _make(input_path: Path, fmt: str = "thaijo_md") -> dict:
        cfg = load_config(None)
        cfg["pipeline"].update(work_dir=str(tmp_path / "work"), output_dir=str(tmp_path / "out"),
                               state_dir=str(tmp_path / "state"))
        cfg["input"].update(path=str(input_path), format=fmt, workers=1)
        return cfg
    return _make
```

- [ ] **Step 2: Write the failing tests `pipeline/tests/test_ingest.py`**

```python
import shutil

import pandas as pd

from atlas.ingest import ingest
from atlas.io_utils import read_table
from atlas.orgs import org_key
from atlas.thai import norm_key


def test_org_key_prefers_university_level():
    # keys are norm_key()-folded (tone marks / thanthakhat removed) so spelling variants of marks collapse
    assert org_key("สาขาบริหารธุรกิจ คณะบริหารธุรกิจ เศรษฐศาสตร์และการสื่อสาร มหาวิทยาลัยนเรศวร", "") == "มหาวิทยาลัยนเรศวร"
    assert org_key("วิทยาลัยพาณิชยศาสตร์ มหาวิทยาลัยบูรพา", "") == "มหาวิทยาลัยบูรพา"
    assert org_key("คณะนิเทศศาสตร์ สถาบันบัณฑิตพัฒนบริหารศาสตร์", "") == norm_key("สถาบันบัณฑิตพัฒนบริหารศาสตร์")
    assert org_key("", "Faculty of Business, Economics and Communications, Naresuan University") == "naresuanuniversity"
    assert org_key("", "") == ""
    assert org_key("ศูนย์ถ่ายทอดองค์ความรู้ ภูมิปัญญาและนวัตกรรมชุมชน", "") != ""


def test_ingest_real_fixtures(make_cfg, thaijo_dir):
    cfg = make_cfg(thaijo_dir)
    df = ingest(cfg)
    work = cfg["pipeline"]["work_dir"]
    assert len(df) == 11 and df["article_id"].is_unique
    assert df["year"].notna().all()
    row = df.set_index("article_id").loc["so02:BECJournal:54895"]
    assert (int(row["year"]), row["year_source"]) == (2014, "doi")
    assert "; " in row["keywords_th"]
    authors = read_table(f"{work}/01_authors.parquet")
    refs = read_table(f"{work}/01_references.parquet")
    assert len(authors) == 21
    assert len(refs) == 32
    # 9 authors carry a Thai Naresuan affiliation; the English-only one maps to "naresuanuniversity"
    assert authors["org_key"].eq("มหาวิทยาลัยนเรศวร").sum() == 9
    assert authors["org_key"].eq("naresuanuniversity").sum() == 1


def test_duplicate_file_is_dropped(make_cfg, thaijo_dir, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    for name in ("so02_BECJournal_54895.md", "so02_BECJournal_62642.md"):
        shutil.copyfile(thaijo_dir / name, src / name)
    shutil.copyfile(thaijo_dir / "so02_BECJournal_54895.md", src / "copy_of_tqa.md")
    assert len(ingest(make_cfg(src))) == 2


def test_missing_url_gets_stable_unique_file_id(make_cfg, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    for i in (1, 2):
        (src / f"broken{i}.md").write_text(f"# ชื่อเรื่องที่ {i} สำหรับทดสอบระบบ\n\n**Published:** 2020-01-0{i}\n", encoding="utf-8")
    ids1 = sorted(ingest(make_cfg(src))["article_id"])
    ids2 = sorted(ingest(make_cfg(src))["article_id"])
    assert ids1 == ids2 and len(set(ids1)) == 2 and all(i.startswith("file:") for i in ids1)


def test_thai_filename_is_read(make_cfg, thaijo_dir, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    shutil.copyfile(thaijo_dir / "so02_BECJournal_74136.md", src / "อุปสรรคต่อการนำพาณิชย์อิเล็กทรอนิกส์.md")
    assert ingest(make_cfg(src))["article_id"].tolist() == ["so02:BECJournal:74136"]


def test_table_input_converts_buddhist_years_and_filters(make_cfg, tmp_path):
    csv = tmp_path / "t.csv"
    pd.DataFrame({"id": ["a", "b", "c"], "title_th": ["หนึ่ง", "สอง", "สาม"],
                  "year": ["2560", "2018", "1800"]}).to_csv(csv, index=False)
    df = ingest(make_cfg(csv, "table")).set_index("article_id")
    assert int(df.loc["a", "year"]) == 2017 and int(df.loc["b", "year"]) == 2018
    assert "c" not in df.index


def test_dedup_keeps_most_complete_record(make_cfg, tmp_path):
    csv = tmp_path / "t.csv"
    pd.DataFrame({"id": ["x1", "x2"], "title_th": ["ชื่อเดียวกัน", "ชื่อเดียวกัน"],
                  "abstract_th": ["", "มีบทคัดย่อ"], "doi": ["10.1/abc", "10.1/ABC"],
                  "year": ["2020", "2020"]}).to_csv(csv, index=False)
    df = ingest(make_cfg(csv, "table"))
    assert df["article_id"].tolist() == ["x2"]
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_ingest.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.orgs'`

- [ ] **Step 4: Implement `pipeline/atlas/orgs.py`**

```python
"""Coarse institution key from an affiliation string.

Good enough to COUNT distinct institutions (Emerging v2 breadth rule). P3 replaces it
with the curated alias table + ROR matching.
"""
from __future__ import annotations

import re

from atlas.thai import clean_text, norm_key

_TH_LEVELS = ("มหาวิทยาลัย", "สถาบัน", "วิทยาลัย", "โรงพยาบาล")
_EN_ORG = re.compile(
    r"((?:[A-Z][\w'&.\-]*\s+){0,5}(?:University|Institute|College|Hospital|Polytechnic)"
    r"(?:\s+of(?:\s+[A-Z][\w'&.\-]*){1,4})?)"
)


def org_key(affiliation_th: str, affiliation_en: str) -> str:
    th = clean_text(affiliation_th)
    if th:
        for word in _TH_LEVELS:                 # most general organisation level first
            m = re.search(rf"\S*{word}\S*", th)
            if m:
                return norm_key(m.group(0))
        return norm_key(th)[:60]
    en = clean_text(affiliation_en)
    if en:
        m = _EN_ORG.search(en)
        return norm_key(m.group(1) if m else en)[:60]
    return ""
```

- [ ] **Step 5: Replace `pipeline/atlas/ingest.py`**

```python
"""Ingest: a folder of ThaiJO Markdown files (default) or one table file → canonical tables.

Outputs (work_dir): 01_articles, 01_authors, 01_references  (via io_utils)
"""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from atlas.io_utils import read_table, write_table
from atlas.orgs import org_key
from atlas.sources.thaijo_md import fill_years_from_issue, parse_markdown
from atlas.thai import clean_text, norm_key

ARTICLE_COLUMNS = [
    "article_id", "source_path", "url", "issue_url", "journal_name", "published", "year", "year_source",
    "pages", "doi", "title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en",
    "authors", "affiliations", "n_authors", "n_student_authors", "n_references", "has_references",
    "self_citation_only", "text_quality",
]
AUTHOR_COLUMNS = ["article_id", "position", "name", "name_en", "affiliation_th", "affiliation_en",
                  "role", "is_student", "org_key"]
REFERENCE_COLUMNS = ["article_id", "position", "text", "year", "lang", "translated", "self_citation"]
_TEXT = ["source_path", "url", "issue_url", "journal_name", "published", "year_source", "pages", "doi",
         "title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en",
         "authors", "affiliations", "text_quality"]


# ------------------------------------------------------------------ markdown corpus
def _parse_file(path_str: str) -> dict:
    p = Path(path_str)
    rec = parse_markdown(p.read_text(encoding="utf-8-sig", errors="replace"), source_path=str(p))
    if not rec["article_id"]:                     # broken scrape: stable id from the file name
        rec["article_id"] = "file:" + hashlib.sha1(p.name.encode("utf-8")).hexdigest()[:16]
    return rec


def read_thaijo_corpus(root: str | Path, pattern: str = "**/*.md", workers: int = 1) -> list[dict]:
    files = sorted(str(p) for p in Path(root).glob(pattern) if p.is_file() and not p.name.startswith("_"))
    if workers > 1 and len(files) > 2000:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            recs = list(tqdm(ex.map(_parse_file, files, chunksize=256), total=len(files), desc="parse"))
    else:
        recs = [_parse_file(f) for f in tqdm(files, desc="parse", disable=len(files) < 2000)]
    fill_years_from_issue(recs)
    return recs


def records_to_tables(records: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    arts, auths, refs = [], [], []
    for r in records:
        a = r["authors"]
        arts.append({
            **{k: r[k] for k in ("article_id", "source_path", "url", "issue_url", "journal_name", "published",
                                 "year", "year_source", "pages", "doi", "title_th", "title_en",
                                 "abstract_th", "abstract_en", "n_references", "has_references",
                                 "self_citation_only")},
            "keywords_th": "; ".join(r["keywords_th"]),
            "keywords_en": "; ".join(r["keywords_en"]),
            "authors": "; ".join(x["name"] for x in a),
            "affiliations": "; ".join(x["affiliation_th"] or x["affiliation_en"] for x in a),
            "n_authors": len(a),
            "n_student_authors": sum(bool(x["is_student"]) for x in a),
            "text_quality": "; ".join(r["text_quality"]),
        })
        for i, x in enumerate(a):
            auths.append({"article_id": r["article_id"], "position": i, **x,
                          "org_key": org_key(x["affiliation_th"], x["affiliation_en"])})
        for i, x in enumerate(r["references"]):
            refs.append({"article_id": r["article_id"], "position": i, **{k: x[k] for k in REFERENCE_COLUMNS[2:]}})
    return (pd.DataFrame(arts, columns=ARTICLE_COLUMNS),
            pd.DataFrame(auths, columns=AUTHOR_COLUMNS),
            pd.DataFrame(refs, columns=REFERENCE_COLUMNS))


# ------------------------------------------------------------------ table input
def _read_any(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"input not found: {p}")
    if p.suffix == ".csv":
        return pd.read_csv(p, dtype=str, keep_default_na=False)
    if p.suffix == ".parquet":
        return read_table(p)
    if p.suffix in (".jsonl", ".ndjson"):
        return pd.read_json(p, lines=True, dtype=False)
    if p.suffix == ".json":
        obj = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            obj = next(v for v in obj.values() if isinstance(v, list))
        return pd.DataFrame(obj)
    raise ValueError(f"unsupported input type: {p.suffix}")


def read_table_input(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = _read_any(cfg["input"]["path"])
    colmap = {k: v for k, v in cfg["input"]["columns"].items() if v in raw.columns}
    if "article_id" not in colmap:
        raise ValueError("table input needs an id column mapped to article_id")
    df = raw.rename(columns={v: k for k, v in colmap.items()})
    for c in ARTICLE_COLUMNS:
        if c not in df.columns:
            df[c] = None
    df = df[ARTICLE_COLUMNS].copy()
    for c in _TEXT:
        df[c] = df[c].fillna("").astype(str).map(clean_text)
    df["article_id"] = df["article_id"].astype(str)
    df["year_source"] = "table"
    df["n_authors"] = df["authors"].map(lambda s: len([x for x in s.split(";") if x.strip()]))
    for c in ("n_student_authors", "n_references"):
        df[c] = 0
    for c in ("has_references", "self_citation_only"):
        df[c] = False
    auth_rows = []
    for aid, names, affs in zip(df["article_id"], df["authors"], df["affiliations"]):
        aff_list = [x.strip() for x in affs.split(";")]
        for i, name in enumerate(x.strip() for x in names.split(";") if x.strip()):
            aff = aff_list[i] if i < len(aff_list) else ""
            auth_rows.append({"article_id": aid, "position": i, "name": name, "name_en": "",
                              "affiliation_th": aff, "affiliation_en": "", "role": "", "is_student": False,
                              "org_key": org_key(aff, "")})
    return df, pd.DataFrame(auth_rows, columns=AUTHOR_COLUMNS), pd.DataFrame(columns=REFERENCE_COLUMNS)


# ------------------------------------------------------------------ normalisation
def normalize_years(df: pd.DataFrame, min_year: int, max_year: int | None) -> pd.DataFrame:
    y = pd.to_numeric(df["year"], errors="coerce")
    y = y.where(y <= 2400, y - 543)                       # Buddhist Era → Common Era
    max_year = max_year or date.today().year + 1
    df = df.assign(year=y.astype("Int64"))
    bad = df["year"].notna() & ((df["year"] < min_year) | (df["year"] > max_year))
    return df[~bad]


def add_convenience_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["title"] = df["title_th"].where(df["title_th"] != "", df["title_en"])
    df["abstract"] = (df["abstract_th"] + " " + df["abstract_en"]).str.strip()
    df["keywords"] = [("; ".join(x for x in (a, b) if x)) for a, b in zip(df["keywords_th"], df["keywords_en"])]
    return df


def _completeness(df: pd.DataFrame) -> pd.Series:
    cols = ("title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en", "doi", "authors")
    return sum((df[c].astype(str).str.len() > 0).astype(int) for c in cols)


def _drop_dup_keys(df: pd.DataFrame, key: pd.Series) -> pd.DataFrame:
    has = key != ""
    return pd.concat([df[has].loc[~key[has].duplicated()], df[~has]])


def dedup(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """article_id → DOI → normalised title + year; keep the most complete record."""
    n0 = len(df)
    df = df.assign(_c=_completeness(df)).sort_values(["_c", "article_id"], ascending=[False, True], kind="stable")
    df = df.drop_duplicates("article_id", keep="first")
    df = _drop_dup_keys(df, df["doi"].str.lower().str.strip())
    title_key = df["title"].map(norm_key).str[:80]
    df = _drop_dup_keys(df, title_key.where(title_key == "", title_key + "|" + df["year"].astype(str)))
    return df.drop(columns="_c").sort_values("article_id").reset_index(drop=True), n0 - len(df)


# ------------------------------------------------------------------ step
def ingest(cfg: dict) -> pd.DataFrame:
    icfg = cfg["input"]
    if icfg["format"] == "thaijo_md":
        articles, authors, refs = records_to_tables(
            read_thaijo_corpus(icfg["path"], icfg["glob"], int(icfg["workers"])))
    else:
        articles, authors, refs = read_table_input(cfg)
    n_raw = len(articles)
    articles = normalize_years(articles, int(icfg["min_year"]), icfg["max_year"])
    articles = add_convenience_columns(articles)
    articles = articles[articles["title"] != ""]
    n_dup = 0
    if icfg["dedup"]["enabled"]:
        articles, n_dup = dedup(articles)
    keep = set(articles["article_id"])
    authors = authors[authors["article_id"].isin(keep)].drop_duplicates(["article_id", "position"])
    refs = refs[refs["article_id"].isin(keep)].drop_duplicates(["article_id", "position"])

    work = Path(cfg["pipeline"]["work_dir"])
    write_table(articles.reset_index(drop=True), work / "01_articles.parquet")
    write_table(authors.reset_index(drop=True), work / "01_authors.parquet")
    write_table(refs.reset_index(drop=True), work / "01_references.parquet")
    print(f"[ingest] {n_raw:,} records → {len(articles):,} articles (duplicates dropped: {n_dup:,}; "
          f"year missing: {int(articles['year'].isna().sum()):,}) → {work}")
    return articles
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_ingest.py -q`
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/ingest.py pipeline/atlas/orgs.py pipeline/tests/test_ingest.py pipeline/tests/conftest.py
git commit -m "feat(pipeline): ingest ThaiJO markdown → articles/authors/references tables

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Synthetic ThaiJO corpus with planted trends (`atlas/synth.py`, `atlas synth`)

Prototyped on 2026-10-18 with this exact generator (`n=20000, seed=7`) and the Task 8–12 logic: 106 raw HDBSCAN clusters → 29 topics after merge, purity 1.000; emerging→EMERGING, confound→WATCH, hot→HOT, declining→DECLINING, stable topics only STABLE/LOW_DATA. Keep topic vocabularies, shares and quirk rates exactly as written — the e2e test (Task 15) depends on them.

**Files:**
- Create: `pipeline/atlas/synth.py`, `pipeline/tests/test_synth.py`
- Modify: `pipeline/atlas/cli.py` (add `synth` command)

**Interfaces:**
- Produces: `generate(out_dir: str | Path, n: int = 20_000, seed: int = 7) -> pd.DataFrame` (truth table, also written to `out_dir/_truth.csv` with columns `article_id, topic, role, journal, year`); `yearly_counts(n, seed) -> DataFrame[topic, year, count]`; constants `TOPICS`, `YEARS`, `NEW_JOURNAL`, `METHODS_TH`, `METHODS_EN`; CLI `atlas synth --n 20000 --out DIR --seed 7`.

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_synth.py`**

```python
import pandas as pd

from atlas.ingest import read_thaijo_corpus
from atlas.synth import NEW_JOURNAL, TOPICS, YEARS, generate, yearly_counts


def test_yearly_counts_shape_and_total():
    c = yearly_counts(20_000, seed=7)
    assert abs(c["count"].sum() - 20_000) / 20_000 < 0.02
    em = c[c.topic == "genai_edu"].set_index("year")["count"]
    assert em[2024] > em[2023] > em[2022] > em[2019]
    conf = c[c.topic == "buddhist_media"].set_index("year")["count"]
    assert conf[[y for y in YEARS if y < 2022]].sum() == 0
    dec = c[c.topic == "print_media"].set_index("year")["count"]
    assert dec[2024] < dec[2023] < dec[2022] < dec[2019]


def test_generate_writes_parseable_corpus(tmp_path):
    truth = generate(tmp_path, n=600, seed=3)
    assert (tmp_path / "_truth.csv").exists()
    assert set(truth["role"]) >= {"stable", "hot", "declining"}
    recs = read_thaijo_corpus(tmp_path)
    parsed = pd.DataFrame(recs).drop_duplicates("article_id").set_index("article_id")
    t = truth.set_index("article_id")
    assert set(parsed.index) == set(t.index)
    assert (parsed.loc[t.index, "year"].astype(int) == t["year"]).all()     # 1970 dates recovered from DOI
    assert parsed["authors"].map(len).min() >= 1


def test_confound_topic_uses_only_new_journal(tmp_path):
    truth = generate(tmp_path, n=4000, seed=1)
    conf = truth[truth.role == "confound"]
    assert len(conf) > 0 and set(conf.journal) == {NEW_JOURNAL} and conf.year.min() >= 2022


def test_topics_have_six_terms_each():
    for _key, _role, th, en in TOPICS:
        assert len(th) == 6 and len(en) == 6
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_synth.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.synth'`

- [ ] **Step 3: Implement `pipeline/atlas/synth.py`**

```python
"""Synthetic ThaiJO-style Markdown corpus with planted trends — for tests, CI and demos.

`generate(out_dir, n, seed)` writes one .md per article in the exact ThaiJO scrape layout
plus `_truth.csv` (article_id, topic, role, journal, year). Planted roles:

  emerging   small topic exploding in the recent window      → must become EMERGING
  confound   topic that exists only because a NEW journal joined in the recent window
             (looks emerging, single journal)                 → must become WATCH
  hot        large topic with rising share                    → must become HOT
  declining  topic whose share falls ~30%/year since 2018     → must become DECLINING
  stable     background topics

Data-quality quirks are injected on purpose: lost dates (1970-01-01 + year in DOI),
Thai PUA glyphs, English-only articles, self-citation-only references, duplicate files.
Every abstract uses all six topic terms so each planted topic forms one coherent cluster.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

YEARS = list(range(2012, 2026))      # 2025 is a partial year (the backfill guard must drop it)
PARTIAL_YEAR, PARTIAL_FACTOR = 2025, 0.4

TOPICS = [
    ("genai_edu", "emerging",
     ["ปัญญาประดิษฐ์เชิงสร้างสรรค์", "แชตจีพีที", "การเรียนรู้ด้วยเอไอ", "โมเดลภาษาขนาดใหญ่", "จริยธรรมเอไอ", "การประเมินงานเขียน"],
     ["generative AI", "ChatGPT", "AI-assisted learning", "large language model", "AI ethics", "writing assessment"]),
    ("buddhist_media", "confound",
     ["พุทธศาสนา", "สื่อธรรมะออนไลน์", "พระสงฆ์", "การเผยแผ่ศาสนา", "วัด", "ศีลธรรม"],
     ["Buddhism", "online dharma media", "monks", "religious propagation", "temple", "morality"]),
    ("elderly_care", "hot",
     ["ผู้สูงอายุ", "การดูแลระยะยาว", "ภาวะพึ่งพิง", "สังคมสูงวัย", "ผู้ดูแล", "คุณภาพชีวิตผู้สูงอายุ"],
     ["older adults", "long-term care", "dependency", "aging society", "caregivers", "quality of life"]),
    ("print_media", "declining",
     ["หนังสือพิมพ์", "สื่อสิ่งพิมพ์", "การอ่านหนังสือพิมพ์", "นิตยสาร", "ยอดจำหน่าย", "บรรณาธิกรณ์"],
     ["newspaper", "print media", "newspaper reading", "magazine", "circulation", "editing"]),
    ("tourism", "stable",
     ["การท่องเที่ยวชุมชน", "นักท่องเที่ยว", "โฮมสเตย์", "แหล่งท่องเที่ยว", "มัคคุเทศก์", "การตลาดท่องเที่ยว"],
     ["community-based tourism", "tourists", "homestay", "destination", "tour guide", "tourism marketing"]),
    ("rice_farming", "stable",
     ["ข้าว", "เกษตรกร", "ผลผลิตข้าว", "ปุ๋ยอินทรีย์", "นาข้าว", "โรคข้าว"],
     ["rice", "farmers", "rice yield", "organic fertilizer", "paddy field", "rice disease"]),
    ("sme_ecommerce", "stable",
     ["วิสาหกิจขนาดกลางและขนาดย่อม", "พาณิชย์อิเล็กทรอนิกส์", "ร้านค้าออนไลน์", "การชำระเงิน", "ผู้ประกอบการ", "ช่องทางจำหน่าย"],
     ["SMEs", "e-commerce", "online store", "e-payment", "entrepreneurs", "distribution channel"]),
    ("nursing_edu", "stable",
     ["นักศึกษาพยาบาล", "การฝึกปฏิบัติการพยาบาล", "สมรรถนะพยาบาล", "หอผู้ป่วย", "การสอนทางคลินิก", "วิชาชีพพยาบาล"],
     ["nursing students", "clinical practicum", "nursing competency", "ward", "clinical teaching", "nursing profession"]),
    ("diabetes", "stable",
     ["เบาหวาน", "ระดับน้ำตาลในเลือด", "ผู้ป่วยเบาหวาน", "การควบคุมอาหาร", "ภาวะแทรกซ้อน", "อินซูลิน"],
     ["diabetes", "blood glucose", "diabetic patients", "diet control", "complications", "insulin"]),
    ("local_gov", "stable",
     ["องค์กรปกครองส่วนท้องถิ่น", "การมีส่วนร่วมของประชาชน", "ธรรมาภิบาล", "เทศบาล", "งบประมาณท้องถิ่น", "การกระจายอำนาจ"],
     ["local government", "public participation", "good governance", "municipality", "local budget", "decentralization"]),
    ("math_learning", "stable",
     ["การจัดการเรียนรู้คณิตศาสตร์", "ผลสัมฤทธิ์ทางการเรียน", "นักเรียนมัธยม", "แบบฝึกทักษะ", "การแก้โจทย์ปัญหา", "เจตคติต่อคณิตศาสตร์"],
     ["mathematics learning", "learning achievement", "secondary students", "skill exercises", "problem solving", "attitude toward mathematics"]),
    ("water_quality", "stable",
     ["คุณภาพน้ำ", "แหล่งน้ำ", "โลหะหนัก", "น้ำเสีย", "การบำบัดน้ำ", "ลุ่มน้ำ"],
     ["water quality", "water sources", "heavy metals", "wastewater", "water treatment", "watershed"]),
    ("herbal_medicine", "stable",
     ["สมุนไพร", "สารสกัด", "ฤทธิ์ต้านอนุมูลอิสระ", "การแพทย์แผนไทย", "ตำรับยา", "พืชสมุนไพร"],
     ["herbal medicine", "extract", "antioxidant activity", "Thai traditional medicine", "formulation", "medicinal plants"]),
    ("hrm", "stable",
     ["การบริหารทรัพยากรมนุษย์", "ความผูกพันต่อองค์กร", "แรงจูงใจในการทำงาน", "พนักงาน", "ความพึงพอใจในงาน", "การลาออก"],
     ["human resource management", "organizational commitment", "work motivation", "employees", "job satisfaction", "turnover"]),
    ("thai_literature", "stable",
     ["วรรณกรรมไทย", "วรรณคดี", "กวีนิพนธ์", "นวนิยาย", "ภาษาถิ่น", "คติชน"],
     ["Thai literature", "classical literature", "poetry", "novels", "dialect", "folklore"]),
    ("energy", "stable",
     ["พลังงานแสงอาทิตย์", "เซลล์แสงอาทิตย์", "การประหยัดพลังงาน", "พลังงานทดแทน", "ไฟฟ้า", "ชีวมวล"],
     ["solar energy", "photovoltaic", "energy saving", "renewable energy", "electricity", "biomass"]),
]

JOURNALS = ["jedu", "nursingjournal", "jhealth", "jsoc", "jmgt", "jagri", "jsci", "jhum",
            "jtour", "jpolsci", "jcomm", "jeng"]
NEW_JOURNAL = "jnewbuddhist"          # joins ThaiJO in 2022 — the confound
INSTITUTIONS = [
    ("มหาวิทยาลัยนเรศวร", "Naresuan University"),
    ("จุฬาลงกรณ์มหาวิทยาลัย", "Chulalongkorn University"),
    ("มหาวิทยาลัยเชียงใหม่", "Chiang Mai University"),
    ("มหาวิทยาลัยขอนแก่น", "Khon Kaen University"),
    ("มหาวิทยาลัยราชภัฏเชียงราย", "Chiang Rai Rajabhat University"),
    ("มหาวิทยาลัยเทคโนโลยีราชมงคลล้านนา", "Rajamangala University of Technology Lanna"),
    ("มหาวิทยาลัยสงขลานครินทร์", "Prince of Songkla University"),
    ("มหาวิทยาลัยมหิดล", "Mahidol University"),
]
ROLES = ["", "", "อาจารย์ ", "ผู้ช่วยศาสตราจารย์ ", "รองศาสตราจารย์ ", "นักศึกษาปริญญาโท ", "นิสิตปริญญาเอก "]
FIRST = ["สมชาย", "สุดา", "วิภา", "ประเสริฐ", "กมล", "อรทัย", "ธนา", "จิราพร", "ณัฐ", "พิมพ์ชนก"]
LAST = ["ใจดี", "ศรีสุข", "ทองดี", "แก้วมณี", "บุญมา", "วงศ์ไทย", "สายทอง", "ประเสริฐศรี"]
METHODS_TH = ["โดยใช้แบบสอบถามกับกลุ่มตัวอย่าง", "ด้วยการสัมภาษณ์เชิงลึก", "เป็นการวิจัยกึ่งทดลอง",
              "วิเคราะห์ข้อมูลด้วยสถิติ t-test และ ANOVA", "เป็นการวิจัยเชิงคุณภาพ", "ใช้การวิเคราะห์สมการโครงสร้าง"]
METHODS_EN = ["using a questionnaire survey", "through in-depth interviews", "with a quasi-experimental design",
              "analysed with t-test and ANOVA", "as qualitative research", "using structural equation modelling"]
PUA_MAI_THO = chr(0xF70B)


def _share_profile(role: str, year: int) -> float:
    """Share of the year's corpus for planted topics (background topics fill the rest)."""
    if role == "emerging":
        return {2022: 0.005, 2023: 0.011, 2024: 0.024, 2025: 0.03}.get(year, 0.0008)
    if role == "confound":
        return {2022: 0.007, 2023: 0.012, 2024: 0.016, 2025: 0.02}.get(year, 0.0)
    if role == "hot":               # share +7%/year — statistically clear even with Poisson noise
        return 0.05 * 1.07 ** (year - YEARS[0])
    if role == "declining":         # flat, then falls ~30%/year — survives topic fragmentation
        return 0.06 * 0.7 ** max(0, year - 2018)
    raise ValueError(role)


def yearly_counts(n: int, seed: int) -> pd.DataFrame:
    """Deterministic topic × year article counts summing to ≈ n (corpus grows 5%/year)."""
    rng = np.random.default_rng(seed)
    units = np.array([1.05 ** i * (PARTIAL_FACTOR if y == PARTIAL_YEAR else 1.0) for i, y in enumerate(YEARS)])
    volume = units / units.sum() * n
    background = [t for t in TOPICS if t[1] == "stable"]
    bg_weight = rng.uniform(0.7, 1.3, len(background))
    rows = []
    for y, vol in zip(YEARS, volume):
        planted = {t[0]: _share_profile(t[1], y) for t in TOPICS if t[1] != "stable"}
        rest = 1.0 - sum(planted.values())
        w = bg_weight * rng.uniform(0.97, 1.03, len(background))
        shares = {**planted, **{t[0]: rest * wi / w.sum() for t, wi in zip(background, w)}}
        for key, sh in shares.items():
            rows.append({"topic": key, "year": y, "count": int(round(sh * vol))})
    return pd.DataFrame(rows)


def _sentence_th(rng, a, b):
    return rng.choice([f"งานวิจัยนี้มีวัตถุประสงค์เพื่อศึกษา{a}และ{b}",
                       f"ผลการวิจัยพบว่า{a}มีความสัมพันธ์กับ{b}อย่างมีนัยสำคัญ",
                       f"ข้อเสนอแนะคือควรส่งเสริม{a}ร่วมกับการพัฒนา{b}",
                       f"การศึกษา{a}ในบริบทของ{b}ยังมีอยู่จำกัด"])


def _sentence_en(rng, a, b):
    return rng.choice([f"This study examines {a} and {b}.",
                       f"Results show that {a} is significantly related to {b}.",
                       f"We recommend strengthening {a} together with {b}.",
                       f"Research on {a} in the context of {b} remains limited."])


def _article_md(rng, idx, topic, year, journal, host) -> tuple[str, str]:
    _key, _role, th, en = topic
    art_id = 100000 + idx
    article_id = f"{host}:{journal}:{art_id}"
    a_th, b_th = rng.choice(th, 2, replace=False)
    a_en, b_en = rng.choice(en, 2, replace=False)
    title_th = f"{a_th}กับ{b_th}: กรณีศึกษาที่ {idx}"
    title_en = f"{a_en.capitalize()} and {b_en}: case study {idx}"
    pth, pen = rng.permutation(th), rng.permutation(en)
    abs_th = " ".join([_sentence_th(rng, pth[i], pth[i + 1]) for i in (0, 2, 4)] + [str(rng.choice(METHODS_TH))])
    abs_en = " ".join([_sentence_en(rng, pen[i], pen[i + 1]) for i in (0, 2, 4)]
                      + [f"The study was conducted {rng.choice(METHODS_EN)}."])
    if rng.random() < 0.02:                                   # PDF glyph corruption
        abs_th = abs_th.replace("\N{THAI CHARACTER MAI THO}", PUA_MAI_THO)
    english_only = rng.random() < 0.05
    has_doi = rng.random() < 0.7
    doi = f"10.14456/{journal}.{year}.{idx % 50 + 1}" if has_doi else ""
    published = f"{year}-{rng.integers(1, 13):02d}-{rng.integers(1, 29):02d}"
    if has_doi and rng.random() < 0.04:                       # scrape lost the date
        published = "1970-01-01"
    authors = []
    for _ in range(int(rng.integers(1, 4))):
        inst_th, inst_en = INSTITUTIONS[int(rng.integers(len(INSTITUTIONS)))]
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        authors.append(f"- {name} ({rng.choice(ROLES)}คณะวิชาการ {inst_th} (Faculty, {inst_en}))")
    kw = list(rng.choice(th, 3, replace=False)) + list(rng.choice(en, 3, replace=False))
    if english_only:
        h1, kw = title_en, kw[3:]
        abstract = abs_en
    else:
        h1 = title_th
        abstract = f"{abs_th}   {title_en}   {abs_en}"
    if doi:
        abstract += f"      DOI:   http://dx.doi.org/{doi}"
    refs = []
    if rng.random() < 0.3:                                    # how-to-cite of the article itself
        refs.append(f"- {authors[0][2:].split(' (')[0]}. ({year + 543}). {h1}. วารสาร{journal}, 1(1), 1-10.")
    else:
        for r in range(int(rng.integers(0, 7))):
            ry = int(rng.integers(1995, year + 1))
            refs.append(f"- Author{r}, A. ({ry}). A reference about {rng.choice(en)}. Journal of Studies, {r + 1}(2), 10-20.")
    lines = [f"# {h1}", "", f"**Journal:** {journal}", f"**Published:** {published}",
             f"**Pages:** {idx % 90 + 1}-{idx % 90 + 12}",
             f"**Article URL:** https://{host}.tci-thaijo.org/index.php/{journal}/article/view/{art_id}",
             f"**Issue URL:** https://{host}.tci-thaijo.org/index.php/{journal}/issue/view/{year * 10 + idx % 3}",
             "", "**Authors:**", *authors, "", f"**Keywords:** {', '.join(kw)}", "", "## Abstract", "", abstract]
    if refs:
        lines += ["", "## References", *refs]
    return article_id, "\n".join(lines) + "\n"


def generate(out_dir: str | Path, n: int = 20_000, seed: int = 7) -> pd.DataFrame:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    counts = yearly_counts(n, seed)
    by_key = {t[0]: t for t in TOPICS}
    home = {t[0]: list(rng.choice(JOURNALS, 4, replace=False)) for t in TOPICS}
    truth, idx = [], 0
    for row in counts.itertuples(index=False):
        topic = by_key[row.topic]
        for _ in range(row.count):
            journal = NEW_JOURNAL if topic[1] == "confound" else str(rng.choice(home[row.topic]))
            host = f"so0{idx % 6 + 1}"
            article_id, md = _article_md(rng, idx, topic, row.year, journal, host)
            (out / f"{article_id.replace(':', '_')}.md").write_text(md, encoding="utf-8")
            if rng.random() < 0.01:                           # duplicate scrape of the same article
                (out / f"{article_id.replace(':', '_')}_dup.md").write_text(md, encoding="utf-8")
            truth.append({"article_id": article_id, "topic": row.topic, "role": topic[1],
                          "journal": journal, "year": row.year})
            idx += 1
    df = pd.DataFrame(truth)
    df.to_csv(out / "_truth.csv", index=False, encoding="utf-8")
    return df
```

- [ ] **Step 4: Add the `synth` command to `pipeline/atlas/cli.py`** (append)

```python
from pathlib import Path  # noqa: E402  (keep imports at top when editing; shown here for clarity)


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
```
(Move `from pathlib import Path` to the top-of-file import block.)

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_synth.py -q`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/synth.py pipeline/atlas/cli.py pipeline/tests/test_synth.py
git commit -m "feat(pipeline): synthetic ThaiJO corpus generator with planted trends

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Corpus quality profile (`atlas/profile.py`, `atlas profile`)

**Files:**
- Create: `pipeline/atlas/profile.py`, `pipeline/tests/test_profile.py`
- Modify: `pipeline/atlas/cli.py` (add `profile`)
- Delete: `pipeline/scripts/validate_input.py`

**Interfaces:**
- Consumes: `read_thaijo_corpus`, `records_to_tables` (Task 5).
- Produces: `profile_corpus(root, pattern="**/*.md", workers=1) -> dict` with keys `files, unique_articles, duplicate_files, missing_article_url, years{min,max,missing,by_source}, by_year, journals{count,top,year_spikes}, coverage_pct{title_th,title_en,abstract_th,abstract_en,keywords_th,keywords_en,doi,references,self_citation_only}, references{articles_with_references,median_counted_per_article}, authors{median_per_article,pct_with_affiliation,pct_student_authors}, text_quality{flag: count}`; `render_markdown(report: dict) -> str`; CLI `atlas profile PATH [--out report.json] [--md report.md] [--workers N]`.

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_profile.py`**

```python
import json

from typer.testing import CliRunner

from atlas.cli import app
from atlas.profile import profile_corpus, render_markdown


def test_profile_real_fixtures(thaijo_dir):
    r = profile_corpus(thaijo_dir)
    assert (r["files"], r["unique_articles"], r["duplicate_files"]) == (11, 11, 0)
    assert (r["years"]["min"], r["years"]["max"], r["years"]["missing"]) == (2013, 2018, 0)
    assert r["years"]["by_source"] == {"published": 9, "doi": 2}
    cov = r["coverage_pct"]
    assert cov["title_en"] == 100.0 and cov["abstract_en"] == 90.9
    assert cov["references"] == 63.6 and cov["self_citation_only"] == 45.5
    assert r["text_quality"] == {"thai_pua_repaired": 1, "stat_symbols_missing": 1}
    assert r["journals"]["count"] == 1


def test_render_markdown_mentions_key_numbers(thaijo_dir):
    md = render_markdown(profile_corpus(thaijo_dir))
    assert md.startswith("# รายงานคุณภาพคลังบทความ")
    assert "11" in md and "BECJournal" in md


def test_cli_profile_writes_json(thaijo_dir, tmp_path):
    out = tmp_path / "r.json"
    res = CliRunner().invoke(app, ["profile", str(thaijo_dir), "--out", str(out)])
    assert res.exit_code == 0, res.stdout
    assert json.loads(out.read_text(encoding="utf-8"))["files"] == 11
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_profile.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.profile'`

- [ ] **Step 3: Implement `pipeline/atlas/profile.py`**

```python
"""Corpus quality profile — run on the full .md corpus BEFORE any modelling.

Answers: how many files/articles, which years (and how they were recovered), which
journals and whether any journal uploaded a backlog in one year, coverage of English
metadata/DOI/references, author affiliation coverage, and text-quality flags.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from atlas.ingest import read_thaijo_corpus, records_to_tables


def _pct(mask: pd.Series) -> float:
    return round(100 * float(mask.mean()), 1) if len(mask) else 0.0


def profile_corpus(root: str | Path, pattern: str = "**/*.md", workers: int = 1) -> dict:
    arts, auths, _ = records_to_tables(read_thaijo_corpus(root, pattern, workers))
    n = len(arts)
    years = pd.to_numeric(arts["year"], errors="coerce")
    nonempty = {c: arts[c].astype(str).str.len() > 0
                for c in ("title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en", "doi")}

    journals, spikes = [], []
    for name, g in arts.assign(y=years).groupby("journal_name"):
        yc = g["y"].dropna().astype(int).value_counts()
        entry = {"journal": name, "articles": int(len(g)),
                 "first_year": int(yc.index.min()) if len(yc) else None,
                 "last_year": int(yc.index.max()) if len(yc) else None,
                 "peak_year_share": round(float(yc.max() / yc.sum()), 3) if len(yc) else 0.0}
        journals.append(entry)
        if entry["articles"] >= 20 and entry["peak_year_share"] >= 0.5:
            spikes.append(entry)                     # likely a backlog upload → interpret trends with care
    journals.sort(key=lambda j: -j["articles"])

    flags = Counter(f for s in arts["text_quality"] for f in str(s).split("; ") if f)
    return {
        "files": n,
        "unique_articles": int(arts["article_id"].nunique()),
        "duplicate_files": int(n - arts["article_id"].nunique()),
        "missing_article_url": int(arts["article_id"].str.startswith("file:").sum()),
        "years": {
            "min": int(years.min()) if years.notna().any() else None,
            "max": int(years.max()) if years.notna().any() else None,
            "missing": int(years.isna().sum()),
            "by_source": {str(k): int(v) for k, v in arts["year_source"].replace("", "none").value_counts().items()},
        },
        "by_year": {int(y): int(c) for y, c in years.dropna().astype(int).value_counts().sort_index().items()},
        "journals": {"count": int(arts["journal_name"].nunique()), "top": journals[:50], "year_spikes": spikes},
        "coverage_pct": {**{c: _pct(m) for c, m in nonempty.items()},
                         "references": _pct(arts["has_references"].astype(bool)),
                         "self_citation_only": _pct(arts["self_citation_only"].astype(bool))},
        "references": {"articles_with_references": int(arts["has_references"].astype(bool).sum()),
                       "median_counted_per_article": float(arts["n_references"].median()) if n else 0.0},
        "authors": {"median_per_article": float(arts["n_authors"].median()) if n else 0.0,
                    "pct_with_affiliation": _pct((auths["affiliation_th"] + auths["affiliation_en"]).str.len() > 0),
                    "pct_student_authors": _pct(auths["is_student"].astype(bool))},
        "text_quality": dict(flags),
    }


def render_markdown(r: dict) -> str:
    cov = r["coverage_pct"]
    lines = [
        "# รายงานคุณภาพคลังบทความ (Corpus profile)",
        "",
        f"- ไฟล์ทั้งหมด **{r['files']:,}** · บทความไม่ซ้ำ **{r['unique_articles']:,}** · "
        f"ไฟล์ซ้ำ {r['duplicate_files']:,} · ไม่มี Article URL {r['missing_article_url']:,}",
        f"- ปี {r['years']['min']}–{r['years']['max']} · ไม่มีปี {r['years']['missing']:,} · "
        f"ที่มาของปี: " + ", ".join(f"{k} {v:,}" for k, v in r["years"]["by_source"].items()),
        f"- วารสาร {r['journals']['count']:,} ฉบับ",
        "",
        "## ความครบถ้วนของ metadata (%)",
        "",
        "| ฟิลด์ | % |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in cov.items()],
        "",
        "## วารสารใหญ่สุด",
        "",
        "| วารสาร | บทความ | ปีแรก | ปีล่าสุด | สัดส่วนปีสูงสุด |",
        "|---|---|---|---|---|",
        *[f"| {j['journal']} | {j['articles']:,} | {j['first_year']} | {j['last_year']} | {j['peak_year_share']} |"
          for j in r["journals"]["top"][:20]],
        "",
        "## วารสารที่อัปโหลดย้อนหลังในปีเดียว (ระวังแนวโน้มเทียม)",
        "",
        *([f"- {j['journal']}: {j['peak_year_share'] * 100:.0f}% ของบทความอยู่ในปีเดียว"
           for j in r["journals"]["year_spikes"]] or ["- ไม่พบ"]),
        "",
        "## Text-quality flags",
        "",
        *([f"- {k}: {v:,}" for k, v in r["text_quality"].items()] or ["- ไม่พบ"]),
        "",
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Add the `profile` command to `pipeline/atlas/cli.py`**

```python
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
```

- [ ] **Step 5: Delete the old validator** — `git rm pipeline/scripts/validate_input.py`

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_profile.py -q`
Expected: 3 passed. Also smoke-test the real corpus folder: `uv run atlas profile ../corpus` prints the Markdown report.

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/profile.py pipeline/atlas/cli.py pipeline/tests/test_profile.py
git commit -m "feat(pipeline): atlas profile — corpus quality report (replaces validate_input.py)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 8: Preprocess + embedding store + providers (`preprocess.py`, `embed_store.py`, `embed.py`)

**Files:**
- Create: `pipeline/atlas/embed_store.py`, `pipeline/tests/test_embed.py`
- Modify: `pipeline/atlas/preprocess.py`, `pipeline/atlas/embed.py` (full rewrites)

**Interfaces:**
- Consumes: `work/01_articles` (Task 5), cfg keys `embedding.*`, `pipeline.state_dir`, `pipeline.seed`.
- Produces:
  - `build_doc_texts(df: pd.DataFrame, fields: list[str], max_chars: int) -> list[str]`; `preprocess(cfg) -> DataFrame` writing `work/02_docs` (all article columns + `doc_text`; rows with `len(doc_text) < 10` dropped).
  - `text_key(model_id: str, text: str) -> str`; `EmbeddingStore(root, model_id)` with `has(key) -> bool`, `add(keys, vectors)`, `get(keys) -> np.ndarray[float32]`, `__len__`.
  - Embedder protocol: object with `model_id: str` and `embed_batch(list[str]) -> np.ndarray`.
  - `lite_embed(texts, lite_cfg: dict, seed: int) -> np.ndarray`; `embed(cfg, embedder=None) -> np.ndarray` writing `work/03_embeddings.npy` (L2-normalised, row-aligned with `02_docs`) and `work/03_meta.json` `{model_id, n, dim}`.

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_embed.py`**

```python
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from atlas.embed import embed, lite_embed
from atlas.embed_store import EmbeddingStore, text_key
from atlas.io_utils import write_table
from atlas.preprocess import build_doc_texts


class FakeEmbedder:
    model_id = "fake|1"

    def __init__(self, fail_on_call: int | None = None):
        self.calls, self.fail_on_call = 0, fail_on_call

    def embed_batch(self, texts):
        self.calls += 1
        if self.fail_on_call and self.calls == self.fail_on_call:
            raise RuntimeError("simulated crash")
        return np.stack([np.frombuffer(hashlib.sha256(t.encode()).digest()[:16], dtype=np.uint8)
                         .astype(np.float32) + 1 for t in texts])


def _norm(a):
    return a / np.linalg.norm(a, axis=1, keepdims=True)


def test_build_doc_texts_joins_non_empty_fields():
    df = pd.DataFrame({"a": ["x", ""], "b": ["y", "z"]})
    assert build_doc_texts(df, ["a", "b", "missing"], 100) == ["x . y", "z"]
    assert build_doc_texts(df, ["a", "b"], 3) == ["x .", "z"]


def test_store_roundtrip_and_resume(tmp_path):
    a = np.arange(6, dtype=np.float32).reshape(2, 3)
    s = EmbeddingStore(tmp_path, "m")
    s.add(["k1", "k2"], a)
    s2 = EmbeddingStore(tmp_path, "m")                     # a new process sees what was flushed
    assert len(s2) == 2 and s2.has("k1")
    s2.add(["k2", "k3"], np.array([[9, 9, 9], [7, 7, 7]], dtype=np.float32))   # k2 already stored
    got = s2.get(["k3", "k1", "k2"])
    assert np.array_equal(got, np.array([[7, 7, 7], [0, 1, 2], [3, 4, 5]], dtype=np.float32))
    with pytest.raises(KeyError):
        s2.get(["nope"])


def test_store_keys_depend_on_model():
    assert text_key("m1", "t") != text_key("m2", "t")


def test_lite_embed_is_deterministic():
    texts = [f"การศึกษาเรื่องที่ {i} about topic {i % 3}" for i in range(40)]
    cfg = {"dim": 8, "ngram_min": 2, "ngram_max": 4, "max_features": 5000, "min_df": 1}
    a, b = lite_embed(texts, cfg, 42), lite_embed(texts, cfg, 42)
    assert a.shape == (40, 8) and np.allclose(a, b)


def _docs(make_cfg, tmp_path, n=10):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "api"
    cfg["embedding"]["api"].update(batch_size=2, checkpoint_every=2)
    texts = [f"เอกสารทดสอบหมายเลข {i} for embedding" for i in range(n)]
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(n)], "doc_text": texts}),
                f"{cfg['pipeline']['work_dir']}/02_docs.parquet")
    return cfg, texts


def test_embed_resumes_after_interruption(make_cfg, tmp_path):
    cfg, texts = _docs(make_cfg, tmp_path)
    with pytest.raises(RuntimeError):
        embed(cfg, embedder=FakeEmbedder(fail_on_call=3))        # crashes on the 3rd batch
    fake = FakeEmbedder()
    arr = embed(cfg, embedder=fake)
    assert fake.calls == 3                                        # 10 texts − 4 already stored = 3 batches of 2
    assert np.allclose(arr, _norm(FakeEmbedder().embed_batch(texts)), atol=1e-6)
    meta = json.loads(open(f"{cfg['pipeline']['work_dir']}/03_meta.json", encoding="utf-8").read())
    assert meta == {"model_id": "fake|1", "n": 10, "dim": 16}


def test_embed_second_run_uses_store_only(make_cfg, tmp_path):
    cfg, _ = _docs(make_cfg, tmp_path)
    embed(cfg, embedder=FakeEmbedder())
    again = FakeEmbedder()
    embed(cfg, embedder=again)
    assert again.calls == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_embed.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.embed_store'`

- [ ] **Step 3: Replace `pipeline/atlas/preprocess.py`**

```python
"""Build doc_text (the text that gets embedded) from title + keywords + abstract."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table


def build_doc_texts(df: pd.DataFrame, fields: list[str], max_chars: int) -> list[str]:
    cols = [df[f].fillna("").astype(str).str.strip().tolist() for f in fields if f in df.columns]
    if not cols:
        return [""] * len(df)
    return [" . ".join(v for v in vals if v)[:max_chars] for vals in zip(*cols)]


def preprocess(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    df = read_table(work / "01_articles.parquet")
    ecfg = cfg["embedding"]
    df = df.assign(doc_text=build_doc_texts(df, ecfg["doc_fields"], int(ecfg["max_chars_per_doc"])))
    df = df[df["doc_text"].str.len() >= 10].reset_index(drop=True)
    write_table(df, work / "02_docs.parquet")
    print(f"[preprocess] {len(df):,} docs (avg {df['doc_text'].str.len().mean():.0f} chars) → 02_docs")
    return df
```

- [ ] **Step 4: Create `pipeline/atlas/embed_store.py`**

```python
"""Append-only embedding store keyed by a hash of (model_id, text) — lives in state_dir.

Layout: <root>/<model-slug>/index.parquet (key, shard, row) + shard_00000.npy, ...
Every add() writes a NEW shard and then the index. A run interrupted mid-way keeps all
fully written shards, so re-running embeds only what is missing; texts that did not
change between quarters are never paid for twice.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table


def text_key(model_id: str, text: str) -> str:
    return hashlib.sha1(f"{model_id}\n{text}".encode()).hexdigest()


class EmbeddingStore:
    def __init__(self, root: str | Path, model_id: str):
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", model_id)[:80]
        self.dir = Path(root) / f"{slug}-{hashlib.sha1(model_id.encode()).hexdigest()[:8]}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.dir / "index.parquet"
        try:
            self.index = read_table(self._index_path)
        except FileNotFoundError:
            self.index = pd.DataFrame({"key": pd.Series(dtype=str), "shard": pd.Series(dtype="int64"),
                                       "row": pd.Series(dtype="int64")})
        self._lookup = dict(zip(self.index["key"], zip(self.index["shard"], self.index["row"])))

    def __len__(self) -> int:
        return len(self._lookup)

    def has(self, key: str) -> bool:
        return key in self._lookup

    def add(self, keys: list[str], vectors: np.ndarray) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        if len(keys) != len(vectors):
            raise ValueError("keys and vectors differ in length")
        new, seen = [], set()
        for i, k in enumerate(keys):
            if k not in self._lookup and k not in seen:
                new.append((k, i))
                seen.add(k)
        if not new:
            return
        shard = int(self.index["shard"].max()) + 1 if len(self.index) else 0
        np.save(self.dir / f"shard_{shard:05d}.npy", vectors[[i for _, i in new]])
        add = pd.DataFrame({"key": [k for k, _ in new], "shard": shard, "row": np.arange(len(new))})
        self.index = pd.concat([self.index, add], ignore_index=True)
        write_table(self.index, self._index_path)
        self._lookup.update({k: (shard, int(r)) for k, r in zip(add["key"], add["row"])})

    def get(self, keys: list[str]) -> np.ndarray:
        missing = [k for k in keys if k not in self._lookup]
        if missing:
            raise KeyError(f"{len(missing)} keys not in store")
        by_shard: dict[int, list[tuple[int, int]]] = {}
        for pos, k in enumerate(keys):
            s, r = self._lookup[k]
            by_shard.setdefault(int(s), []).append((pos, int(r)))
        out: np.ndarray | None = None
        for s, items in by_shard.items():
            arr = np.load(self.dir / f"shard_{s:05d}.npy", mmap_mode="r")
            if out is None:
                out = np.empty((len(keys), arr.shape[1]), dtype=np.float32)
            pos, rows = zip(*items)
            out[list(pos)] = arr[list(rows)]
        return out if out is not None else np.empty((0, 0), dtype=np.float32)
```

- [ ] **Step 5: Replace `pipeline/atlas/embed.py`**

```python
"""Embedding step. Providers:

  api   : any OpenAI-compatible endpoint (OpenAI, Gemini, OpenRouter, vLLM, Ollama)
  local : sentence-transformers (default BAAI/bge-m3, max_seq_length 1024)
  lite  : TF-IDF char n-grams + TruncatedSVD on CPU — for tests/CI/demos (lower quality)

api/local vectors are cached in state_dir/embeddings (EmbeddingStore): resumable and
incremental across quarters. Output: work/03_embeddings.npy (+ 03_meta.json).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
from tqdm import tqdm

from atlas.embed_store import EmbeddingStore, text_key
from atlas.io_utils import read_table


class ApiEmbedder:
    def __init__(self, cfg: dict):
        from openai import OpenAI  # optional dependency: uv sync --extra api

        acfg = cfg["embedding"]["api"]
        api_key = os.environ.get(acfg["api_key_env"], "")
        if not api_key:
            raise OSError(f"set ${acfg['api_key_env']} before running with embedding.provider=api")
        self.client = OpenAI(base_url=acfg["base_url"], api_key=api_key, timeout=120)
        self.model, self.dimensions = acfg["model"], acfg.get("dimensions")
        self.max_retries = int(acfg.get("max_retries", 6))
        self.model_id = f"api|{acfg['base_url']}|{self.model}|{self.dimensions}"

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        kwargs = {"model": self.model, "input": texts}
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions
        delay = 2.0
        for attempt in range(self.max_retries):
            try:
                resp = self.client.embeddings.create(**kwargs)
                return np.array([d.embedding for d in resp.data], dtype=np.float32)
            except Exception as e:  # noqa: BLE001 — retry any transport/API error
                if attempt == self.max_retries - 1:
                    raise
                print(f"[embed] retry {attempt + 1}/{self.max_retries}: {e}")
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")


class LocalEmbedder:
    def __init__(self, cfg: dict):
        from sentence_transformers import SentenceTransformer  # optional: uv sync --extra local

        lcfg = cfg["embedding"]["local"]
        self.model = SentenceTransformer(lcfg["model"], device=lcfg["device"])
        self.model.max_seq_length = int(lcfg["max_seq_length"])
        self.batch_size = int(lcfg["batch_size"])
        if lcfg.get("fp16") and lcfg["device"] == "cuda":
            self.model.half()
        self.model_id = f"local|{lcfg['model']}|{lcfg['max_seq_length']}"

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        vec = self.model.encode(texts, batch_size=self.batch_size, convert_to_numpy=True,
                                normalize_embeddings=True, show_progress_bar=False)
        return vec.astype(np.float32)


def get_embedder(cfg: dict):
    provider = cfg["embedding"]["provider"]
    if provider == "api":
        return ApiEmbedder(cfg)
    if provider == "local":
        return LocalEmbedder(cfg)
    raise ValueError(f"no embedder object for provider {provider!r}")


def lite_embed(texts: list[str], lite_cfg: dict, seed: int) -> np.ndarray:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(int(lite_cfg["ngram_min"]), int(lite_cfg["ngram_max"])),
                          max_features=int(lite_cfg["max_features"]), sublinear_tf=True,
                          min_df=min(int(lite_cfg["min_df"]), max(1, len(texts))))
    X = vec.fit_transform(texts)
    k = max(1, min(int(lite_cfg["dim"]), X.shape[1] - 1, len(texts) - 1))
    return TruncatedSVD(k, random_state=seed).fit_transform(X).astype(np.float32)


def _normalize(arr: np.ndarray) -> np.ndarray:
    return (arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-9)).astype(np.float32)


def embed(cfg: dict, embedder=None) -> np.ndarray:
    work = Path(cfg["pipeline"]["work_dir"])
    texts = read_table(work / "02_docs.parquet")["doc_text"].tolist()
    provider = cfg["embedding"]["provider"]
    if embedder is None and provider == "lite":
        lcfg = cfg["embedding"]["lite"]
        arr = lite_embed(texts, lcfg, int(cfg["pipeline"]["seed"]))
        model_id = f"lite|char{lcfg['ngram_min']}-{lcfg['ngram_max']}|svd{arr.shape[1]}"
    else:
        embedder = embedder or get_embedder(cfg)
        pcfg = cfg["embedding"].get(provider, {}) if provider in ("api", "local") else {}
        batch, every = int(pcfg.get("batch_size", 64)), int(pcfg.get("checkpoint_every", 5000))
        store = EmbeddingStore(Path(cfg["pipeline"]["state_dir"]) / "embeddings", embedder.model_id)
        keys = [text_key(embedder.model_id, t) for t in texts]
        text_of = dict(zip(keys, texts))
        todo = list(dict.fromkeys(k for k in keys if not store.has(k)))
        print(f"[embed] {len(keys) - len(todo):,} cached, {len(todo):,} to embed ({embedder.model_id})")
        buf_k: list[str] = []
        buf_v: list[np.ndarray] = []
        for i in tqdm(range(0, len(todo), batch), desc="embed", disable=not todo):
            chunk = todo[i:i + batch]
            buf_k += chunk
            buf_v.append(embedder.embed_batch([text_of[k] for k in chunk]))
            if len(buf_k) >= every:
                store.add(buf_k, np.vstack(buf_v))
                buf_k, buf_v = [], []
        if buf_k:
            store.add(buf_k, np.vstack(buf_v))
        arr, model_id = store.get(keys), embedder.model_id
    arr = _normalize(arr)
    work.mkdir(parents=True, exist_ok=True)
    np.save(work / "03_embeddings.npy", arr)
    (work / "03_meta.json").write_text(json.dumps({"model_id": model_id, "n": int(arr.shape[0]),
                                                   "dim": int(arr.shape[1])}), encoding="utf-8")
    print(f"[embed] {arr.shape} → 03_embeddings.npy")
    return arr
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_embed.py -q`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/preprocess.py pipeline/atlas/embed_store.py pipeline/atlas/embed.py pipeline/tests/test_embed.py
git commit -m "feat(pipeline): resumable embedding store in state_dir + lite CPU embedder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: c-TF-IDF over Thai/Latin words and author keywords (`atlas/ctfidf.py`)

**Files:**
- Create: `pipeline/atlas/ctfidf.py`, `pipeline/tests/test_ctfidf.py`

**Interfaces:**
- Consumes: `tokenize` (Task 2).
- Produces: `ctfidf_top_terms(class_tokens: dict[int, list[list[str]]], top_n: int) -> dict[int, list[str]]`; `topic_terms(texts_by_topic: dict[int, list[str]], top_n: int, max_docs: int, seed: int) -> dict[int, list[str]]`; `topic_keywords(keywords_by_topic: dict[int, list[str]], top_n: int) -> dict[int, list[str]]` (input strings are `"; "`-joined keyword phrases).

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_ctfidf.py`**

```python
from atlas.ctfidf import ctfidf_top_terms, topic_keywords, topic_terms


def test_class_specific_terms_rank_first():
    toks = {0: [["rice", "farmer", "study"], ["rice", "yield", "study"]],
            1: [["diabetes", "insulin", "study"], ["diabetes", "glucose", "study"]]}
    top = ctfidf_top_terms(toks, 2)
    assert top[0][0] == "rice" and top[1][0] == "diabetes"
    assert "study" not in top[0] and "study" not in top[1]   # shared by every class → low weight


def test_topic_terms_tokenize_thai():
    texts = {0: ["การปลูกข้าวของเกษตรกร", "ผลผลิตข้าวของเกษตรกร"], 1: ["ผู้ป่วยเบาหวานและอินซูลิน"] * 2}
    top = topic_terms(texts, top_n=3, max_docs=10, seed=1)
    assert "ข้าว" in top[0] and "เบาหวาน" in top[1]


def test_topic_keywords_keep_phrases():
    kws = {0: ["ผู้สูงอายุ; long-term care", "ผู้สูงอายุ; ผู้ดูแล"], 1: ["เบาหวาน; insulin"]}
    top = topic_keywords(kws, 2)
    assert top[0][0] == "ผู้สูงอายุ"                          # appears twice in class 0
    assert set(top[0]) <= {"ผู้สูงอายุ", "long-term care", "ผู้ดูแล"}
    assert top[1][0] in {"เบาหวาน", "insulin"}


def test_empty_class_gives_empty_list():
    assert ctfidf_top_terms({0: [], 1: [["a"]]}, 3) == {0: [], 1: ["a"]}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_ctfidf.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.ctfidf'`

- [ ] **Step 3: Implement `pipeline/atlas/ctfidf.py`**

```python
"""Class-based TF-IDF (c-TF-IDF, Grootendorst 2022) over pre-tokenised documents.

score(t, c) = tf(t, c) · log(1 + A / f(t))
  tf(t, c) = count of t in class c / total tokens in c
  A        = average tokens per class
  f(t)     = count of t over all classes
Words come from pythainlp tokenisation (real Thai words, not char n-gram fragments);
author keywords are scored as whole phrases.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from atlas.thai import tokenize


def ctfidf_top_terms(class_tokens: dict[int, list[list[str]]], top_n: int) -> dict[int, list[str]]:
    counts = {c: Counter(tok for doc in docs for tok in doc) for c, docs in class_tokens.items()}
    freq: Counter = Counter()
    for cnt in counts.values():
        freq.update(cnt)
    totals = {c: sum(cnt.values()) for c, cnt in counts.items()}
    nonempty = [v for v in totals.values() if v]
    avg = sum(nonempty) / len(nonempty) if nonempty else 0.0
    out: dict[int, list[str]] = {}
    for c, cnt in counts.items():
        if not totals[c]:
            out[c] = []
            continue
        scores = {t: (n / totals[c]) * np.log(1 + avg / freq[t]) for t, n in cnt.items()}
        out[c] = [t for t, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]]
    return out


def topic_terms(texts_by_topic: dict[int, list[str]], top_n: int, max_docs: int, seed: int) -> dict[int, list[str]]:
    rng = np.random.default_rng(seed)
    toks: dict[int, list[list[str]]] = {}
    for t, docs in texts_by_topic.items():
        if len(docs) > max_docs:
            docs = [docs[i] for i in sorted(rng.choice(len(docs), max_docs, replace=False))]
        toks[t] = [tokenize(d) for d in docs]
    return ctfidf_top_terms(toks, top_n)


def topic_keywords(keywords_by_topic: dict[int, list[str]], top_n: int) -> dict[int, list[str]]:
    toks = {t: [[k.strip() for k in s.split(";") if k.strip()] for s in kws] for t, kws in keywords_by_topic.items()}
    return ctfidf_top_terms(toks, top_n)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_ctfidf.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add pipeline/atlas/ctfidf.py pipeline/tests/test_ctfidf.py
git commit -m "feat(pipeline): c-TF-IDF on real Thai words + author keyword phrases

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Clustering rewrite (`atlas/cluster.py`)

Replaces BERTopic. Prototype result (20K synthetic, 2026-10-18): HDBSCAN alone → 98 clusters for 16 planted topics; `merge_similar` at cosine ≥ 0.8 → 29 clusters, purity 1.000.

**Files:**
- Modify: `pipeline/atlas/cluster.py` (full rewrite)
- Create: `pipeline/tests/test_cluster.py`

**Interfaces:**
- Consumes: `work/02_docs`, `work/03_embeddings.npy`; `topic_terms`, `topic_keywords` (Task 9); cfg `clustering.*`.
- Produces:
  - `reduce_embeddings(emb, ccfg, seed) -> np.ndarray`, `hdbscan_labels(red, fine_cfg) -> np.ndarray`, `centroids(labels, emb) -> (list[int], np.ndarray)`, `merge_similar(labels, emb, threshold) -> np.ndarray`, `assign_outliers(labels, emb, min_sim) -> np.ndarray`, `relabel_by_size(labels) -> np.ndarray`, `coarse_groups(C, n_groups) -> np.ndarray`, `cluster(cfg) -> np.ndarray`.
  - Files: `04_fine_topics` (`article_id, fine_topic`, −1 = unassigned), `04_coarse_topics` (`article_id, coarse_topic`, −1 = unassigned), `04_topic_info` (`level="fine", topic_id, size, top_terms, top_keywords, coarse_topic, coherence`; topic 0 = largest), `04_centroids.npy` (row i ↔ `04_centroid_ids.json[i]`), `04_centroid_ids.json` (JSON list of ints).

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_cluster.py`**

```python
import json

import numpy as np
import pandas as pd

from atlas.cluster import assign_outliers, cluster, coarse_groups, merge_similar, relabel_by_size
from atlas.io_utils import read_table, write_table


def blobs(n_per=60, k=5, dim=32, noise=0.05, seed=0):
    rng = np.random.default_rng(seed)
    centers = np.eye(dim)[:k]                                   # orthogonal centres
    X = np.vstack([c + rng.normal(0, noise, (n_per, dim)) for c in centers])
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    return X.astype(np.float32), np.repeat(np.arange(k), n_per)


def test_merge_similar_rejoins_a_split_cluster():
    X, y = blobs()
    labels = y.copy()
    labels[(y == 0) & (np.arange(len(y)) % 2 == 0)] = 9          # split blob 0 in two
    merged = merge_similar(labels, X, threshold=0.8)
    assert len(set(merged[y == 0])) == 1
    assert len(set(merged)) == 5


def test_assign_outliers_respects_threshold():
    X, y = blobs()
    near = X[y == 1][0] * 0.98
    far = np.eye(32)[20].astype(np.float32)                       # orthogonal to every centre
    X2 = np.vstack([X, near / np.linalg.norm(near), far])
    labels = np.concatenate([y, [-1, -1]])
    out = assign_outliers(labels, X2, min_sim=0.35)
    assert out[-2] == 1 and out[-1] == -1


def test_coarse_groups_do_not_collapse():
    e = np.eye(8, dtype=np.float32)
    C = np.vstack([e[0], e[0] * 0.9 + e[7] * 0.1, e[1], e[1] * 0.9 + e[7] * 0.1, e[2], e[2] * 0.9 + e[7] * 0.1])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    g3 = coarse_groups(C, 3)
    assert len(set(g3)) == 3 and g3[0] == g3[1] and g3[2] == g3[3]
    assert len(set(coarse_groups(C, 20))) == 6                    # regression: v1 collapsed to one group


def test_relabel_by_size_largest_is_zero():
    assert relabel_by_size(np.array([5, 5, 2, -1, 5, 2, 7])).tolist() == [0, 0, 1, -1, 0, 1, 2]


def test_cluster_step_on_blobs(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["clustering"].update(reducer="pca", n_groups=3)
    cfg["clustering"]["fine"].update(hdbscan_min_cluster_size=20, hdbscan_min_samples=5)
    X, y = blobs(n_per=80)
    words = ["ข้าว เกษตรกร", "เบาหวาน อินซูลิน", "ท่องเที่ยว โฮมสเตย์", "พลังงาน แสงอาทิตย์", "วรรณกรรม กวีนิพนธ์"]
    work = tmp_path / "work"
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(len(y))],
                              "doc_text": [f"การศึกษา{words[t]}" for t in y],
                              "keywords_th": [words[t].split()[0] for t in y],
                              "keywords_en": [""] * len(y)}), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", X)
    labels = cluster(cfg)
    info = read_table(work / "04_topic_info.parquet")
    assert len(info) == 5 and (labels >= 0).mean() > 0.95
    assert info["coherence"].min() > 0.9
    assert info["coarse_topic"].nunique() == 3
    assert all(info["top_keywords"].str.len() > 0)
    ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    assert ids == sorted(info["topic_id"].tolist()) and np.load(work / "04_centroids.npy").shape == (5, 32)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cluster.py -q`
Expected: FAIL — `ImportError: cannot import name 'merge_similar'`

- [ ] **Step 3: Replace `pipeline/atlas/cluster.py`**

```python
"""Topic clustering (no BERTopic dependency):

  embeddings → [PCA] → UMAP (fit on a sample, transform the rest) → HDBSCAN
  → merge over-split clusters (centroid cosine ≥ merge_similarity)
  → outliers join the nearest topic only if cosine ≥ outlier_min_similarity (else −1 = unassigned)
  → coarse groups = agglomerative clustering of topic centroids (P1: OpenAlex fields)
  → per topic: c-TF-IDF words, author keywords, coherence (mean cosine to centroid)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.ctfidf import topic_keywords, topic_terms
from atlas.io_utils import read_table, write_table


def _sample(n: int, k: int, seed: int) -> np.ndarray:
    return np.sort(np.random.default_rng(seed).choice(n, k, replace=False)) if n > k else np.arange(n)


def reduce_embeddings(emb: np.ndarray, ccfg: dict, seed: int) -> np.ndarray:
    n, d = emb.shape
    fine = ccfg["fine"]
    n_comp = int(fine["umap_n_components"])
    if ccfg["reducer"] == "pca" or n < 10:
        from sklearn.decomposition import PCA

        return PCA(max(1, min(n_comp, d, n - 1)), random_state=seed).fit_transform(emb)
    X = emb
    pca_dims = int(ccfg["pca_dims"])
    if d > pca_dims and n > pca_dims:
        from sklearn.decomposition import PCA

        X = PCA(pca_dims, random_state=seed).fit(emb[_sample(n, 100_000, seed)]).transform(emb)
    import umap

    reducer = umap.UMAP(n_components=min(n_comp, n - 2), n_neighbors=min(int(fine["umap_n_neighbors"]), n - 1),
                        min_dist=float(fine["umap_min_dist"]), metric="cosine", random_state=seed)
    fit_n = int(ccfg["umap_fit_sample"])
    if n > fit_n:
        reducer.fit(X[_sample(n, fit_n, seed)])
        return reducer.transform(X)
    return reducer.fit_transform(X)


def hdbscan_labels(red: np.ndarray, fine: dict) -> np.ndarray:
    from sklearn.cluster import HDBSCAN

    n = len(red)
    mcs = max(2, min(int(fine["hdbscan_min_cluster_size"]), max(2, n // 2)))
    ms = max(1, min(int(fine["hdbscan_min_samples"]), mcs))
    return HDBSCAN(min_cluster_size=mcs, min_samples=ms).fit_predict(red)


def centroids(labels: np.ndarray, emb: np.ndarray) -> tuple[list[int], np.ndarray]:
    ids = sorted(set(int(x) for x in labels) - {-1})
    if not ids:
        return [], np.zeros((0, emb.shape[1]), dtype=np.float32)
    C = np.stack([emb[labels == i].mean(axis=0) for i in ids])
    C /= np.maximum(np.linalg.norm(C, axis=1, keepdims=True), 1e-9)
    return ids, C.astype(np.float32)


def merge_similar(labels: np.ndarray, emb: np.ndarray, threshold: float) -> np.ndarray:
    ids, C = centroids(labels, emb)
    if len(ids) < 2:
        return labels.copy()
    from sklearn.cluster import AgglomerativeClustering

    grp = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                  distance_threshold=1.0 - threshold).fit_predict(C)
    mapping = dict(zip(ids, (int(g) for g in grp)))
    return np.array([mapping.get(int(x), -1) for x in labels])


def assign_outliers(labels: np.ndarray, emb: np.ndarray, min_sim: float) -> np.ndarray:
    labels = labels.copy()
    mask = labels == -1
    ids, C = centroids(labels, emb)
    if not mask.any() or not ids:
        return labels
    sim = emb[mask] @ C.T
    labels[mask] = np.where(sim.max(axis=1) >= min_sim, np.array(ids)[sim.argmax(axis=1)], -1)
    return labels


def relabel_by_size(labels: np.ndarray) -> np.ndarray:
    order = pd.Series(labels[labels >= 0]).value_counts(sort=True).index.tolist()
    mapping = {int(old): new for new, old in enumerate(order)}
    return np.array([mapping.get(int(x), -1) for x in labels])


def coarse_groups(C: np.ndarray, n_groups: int) -> np.ndarray:
    if len(C) <= 1:
        return np.zeros(len(C), dtype=int)
    from sklearn.cluster import AgglomerativeClustering

    return AgglomerativeClustering(n_clusters=min(n_groups, len(C)), metric="cosine",
                                   linkage="average").fit_predict(C)


def cluster(cfg: dict) -> np.ndarray:
    work = Path(cfg["pipeline"]["work_dir"])
    df = read_table(work / "02_docs.parquet")
    emb = np.load(work / "03_embeddings.npy")
    ccfg, seed = cfg["clustering"], int(cfg["pipeline"]["seed"])

    raw = hdbscan_labels(reduce_embeddings(emb, ccfg, seed), ccfg["fine"])
    n_raw = len(set(raw.tolist()) - {-1})
    labels = merge_similar(raw, emb, float(ccfg["merge_similarity"]))
    labels = assign_outliers(labels, emb, float(ccfg["outlier_min_similarity"]))
    if (labels < 0).all():                    # tiny corpora: everything is one topic
        labels = np.zeros(len(labels), dtype=int)
    labels = relabel_by_size(labels)
    ids, C = centroids(labels, emb)
    groups = coarse_groups(C, int(ccfg["n_groups"]))
    group_of = dict(zip(ids, (int(g) for g in groups)))

    texts = {t: df["doc_text"][labels == t].tolist() for t in ids}
    kw_col = (df.get("keywords_th", pd.Series([""] * len(df))).fillna("").astype(str) + "; "
              + df.get("keywords_en", pd.Series([""] * len(df))).fillna("").astype(str))
    kws = {t: kw_col[labels == t].tolist() for t in ids}
    top_n = int(ccfg["ctfidf_top_n"])
    terms = topic_terms(texts, top_n, int(ccfg["ctfidf_max_docs_per_topic"]), seed)
    keys = topic_keywords(kws, top_n)

    info = pd.DataFrame([{
        "level": "fine", "topic_id": t, "size": int((labels == t).sum()),
        "top_terms": "; ".join(terms[t]), "top_keywords": "; ".join(keys[t]),
        "coarse_topic": group_of[t], "coherence": float((emb[labels == t] @ C[i]).mean()),
    } for i, t in enumerate(ids)])
    write_table(pd.DataFrame({"article_id": df["article_id"], "fine_topic": labels}), work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"article_id": df["article_id"],
                              "coarse_topic": [group_of.get(int(x), -1) for x in labels]}),
                work / "04_coarse_topics.parquet")
    write_table(info, work / "04_topic_info.parquet")
    np.save(work / "04_centroids.npy", C)
    (work / "04_centroid_ids.json").write_text(json.dumps(ids), encoding="utf-8")
    print(f"[cluster] HDBSCAN {n_raw} → merged {len(ids)} topics, {len(set(groups.tolist()))} groups, "
          f"unassigned {(labels < 0).mean():.1%}")
    return labels
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_cluster.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add pipeline/atlas/cluster.py pipeline/tests/test_cluster.py
git commit -m "feat(pipeline): own clustering — HDBSCAN + over-split merge + outlier threshold + coarse groups

Fixes the v1 bug where coarse HDBSCAN on a few hundred centroids collapsed every topic
into one group. Drops the BERTopic dependency (pulled in torch).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Labeling fixes (`atlas/label.py`, `prompts/topic_label.th.md`)

**Files:**
- Modify: `pipeline/atlas/label.py` (full rewrite), `prompts/topic_label.th.md` (sync the master prompt text)
- Create: `pipeline/tests/test_label.py`

**Interfaces:**
- Consumes: `work/02_docs`, `03_embeddings.npy`, `04_fine_topics`, `04_topic_info`, `04_centroids.npy`, `04_centroid_ids.json`; `thai_ratio`.
- Produces: `PROMPT_TEMPLATE`, `representative_indices(member_emb, centroid, n, lam) -> list[int]`, `label(cfg, client=None) -> DataFrame` writing `work/05_labels` (`level, topic_id, name_th, name_en, description, keywords, cache_key`) and the persistent cache `state/label_cache` (`cache_key, name_th, name_en, description, keywords`). `client` is any object with `.chat.completions.create(**kwargs)` returning `.choices[0].message.content` (OpenAI-compatible); tests inject a fake.

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_label.py`**

```python
import json

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.label import label, representative_indices


class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls += 1
        return _Resp(json.dumps({"name_th": f"หัวข้อ {self.calls}", "name_en": f"Topic {self.calls}",
                                 "description": "d", "keywords": ["a", "b"]}))


def _workdir(cfg, titles_by_topic):
    work = cfg["pipeline"]["work_dir"]
    rows, labels = [], []
    for t, titles in titles_by_topic.items():
        for title in titles:
            rows.append({"article_id": f"a{len(rows)}", "title": title, "doc_text": title})
            labels.append(t)
    labels = np.array(labels)
    rng = np.random.default_rng(0)
    emb = rng.normal(size=(len(rows), 8)).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    ids = sorted(titles_by_topic)
    C = np.stack([emb[labels == t].mean(0) for t in ids])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    write_table(pd.DataFrame(rows), f"{work}/02_docs.parquet")
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows], "fine_topic": labels}),
                f"{work}/04_fine_topics.parquet")
    write_table(pd.DataFrame({"level": "fine", "topic_id": ids, "size": [len(titles_by_topic[t]) for t in ids],
                              "top_terms": "ข้าว; rice", "top_keywords": "ข้าว; rice", "coarse_topic": 0,
                              "coherence": 0.9}), f"{work}/04_topic_info.parquet")
    np.save(f"{work}/03_embeddings.npy", emb)
    np.save(f"{work}/04_centroids.npy", C)
    open(f"{work}/04_centroid_ids.json", "w", encoding="utf-8").write(json.dumps(ids))


def test_representative_indices_central_then_diverse():
    c = np.array([1.0, 0.0, 0.0])
    m = np.array([[1, 0, 0], [0.999, 0.045, 0], [0.9, 0, 0.436]], dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    # λ=0.3 favours diversity: the near-duplicate of the first pick (row 1) loses to row 2
    assert representative_indices(m, c, 2, lam=0.3) == [0, 2]


def test_fallback_labels_use_author_keywords(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    _workdir(cfg, {0: ["ก", "ข"]})
    info = read_table(f"{cfg['pipeline']['work_dir']}/04_topic_info.parquet")
    info["top_keywords"] = "ผู้สูงอายุ; การดูแลระยะยาว; older adults"
    write_table(info, f"{cfg['pipeline']['work_dir']}/04_topic_info.parquet")
    out = label(cfg)
    assert out.loc[0, "name_th"] == "ผู้สูงอายุ / การดูแลระยะยาว"
    assert out.loc[0, "name_en"] == "older adults"


def test_llm_labels_cached_by_prompt_content(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["provider"] = "api"
    _workdir(cfg, {0: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 1: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})
    first = FakeClient()
    label(cfg, client=first)
    assert first.calls == 2
    second = FakeClient()
    label(cfg, client=second)
    assert second.calls == 0                                   # nothing changed → all from cache
    _workdir(cfg, {0: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 1: ["หัวข้อใหม่ทั้งหมด 1", "หัวข้อใหม่ทั้งหมด 2"]})
    third = FakeClient()
    out = label(cfg, client=third)
    assert third.calls == 1                                    # only the topic whose members changed
    assert len(out) == 2 and set(out["topic_id"]) == {0, 1}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_label.py -q`
Expected: FAIL — `ImportError: cannot import name 'representative_indices'`

- [ ] **Step 3: Replace `pipeline/atlas/label.py`**

```python
"""Topic labeling.

LLM mode: author keywords + c-TF-IDF words + representative titles (nearest to the
centroid, diversified with MMR) → strict JSON (TH/EN name, description, keywords).
The cache key is a hash of the exact prompt + model, stored in state_dir — so a topic is
re-labelled only when its content changes (v1 keyed by topic_id, which silently swapped
names after re-clustering). Master prompt text: prompts/topic_label.th.md (keep in sync).

Off mode: names from the topic's most distinctive author keywords (TH and EN).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.thai import thai_ratio

PROMPT_TEMPLATE = """คุณคือบรรณาธิการวารสารวิชาการไทย ช่วยตั้งชื่อหัวข้อวิจัย (research topic) จากข้อมูลต่อไปนี้

คำสำคัญที่ผู้เขียนใช้บ่อยในกลุ่มนี้: {keywords}
คำเด่นจากเนื้อหา (c-TF-IDF): {terms}

ตัวอย่างชื่อเรื่องบทความที่เป็นตัวแทนของกลุ่ม:
{titles}

ตอบกลับเป็น JSON เท่านั้น ตาม schema นี้ ห้ามมีข้อความอื่น:
{{
  "name_th": "ชื่อหัวข้อภาษาไทย กระชับ ไม่เกิน 8 คำ",
  "name_en": "Concise English topic name, max 6 words",
  "description": "คำอธิบาย 1 บรรทัดว่าหัวข้อนี้ครอบคลุมงานวิจัยแบบไหน",
  "keywords": ["คำสำคัญ", "4-6", "คำ"]
}}"""
LABEL_COLUMNS = ["level", "topic_id", "name_th", "name_en", "description", "keywords", "cache_key"]
CACHE_COLUMNS = ["cache_key", "name_th", "name_en", "description", "keywords"]


def representative_indices(member_emb: np.ndarray, centroid: np.ndarray, n: int, lam: float) -> list[int]:
    """Maximal Marginal Relevance: close to the centroid, but not near-duplicates of each other."""
    sims = member_emb @ centroid
    chosen = [int(np.argmax(sims))]
    while len(chosen) < min(n, len(member_emb)):
        redundancy = (member_emb @ member_emb[chosen].T).max(axis=1)
        score = lam * sims - (1 - lam) * redundancy
        score[chosen] = -np.inf
        chosen.append(int(np.argmax(score)))
    return chosen


def _cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest()[:16]


def _call_llm(client, model: str, prompt: str, temperature: float, max_retries: int) -> dict:
    delay = 2.0
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model, temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            kws = data.get("keywords", [])
            return {"name_th": str(data.get("name_th", "")), "name_en": str(data.get("name_en", "")),
                    "description": str(data.get("description", "")),
                    "keywords": "; ".join(kws) if isinstance(kws, list) else str(kws)}
        except Exception:  # noqa: BLE001 — retry transport/JSON errors
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def _fallback(top_keywords: str, top_terms: str, tid: int) -> dict:
    kws = [k for k in str(top_keywords).split("; ") if k]
    terms = [t for t in str(top_terms).split("; ") if t]
    th = [k for k in kws if thai_ratio(k) > 0.5][:2] or [t for t in terms if thai_ratio(t) > 0.5][:3]
    en = [k for k in kws if thai_ratio(k) <= 0.5][:2] or [t for t in terms if thai_ratio(t) <= 0.5][:3]
    return {"name_th": " / ".join(th) or f"หัวข้อ {tid}", "name_en": " / ".join(en) or f"Topic {tid}",
            "description": "", "keywords": "; ".join(kws[:6])}


def label(cfg: dict, client=None) -> pd.DataFrame:
    work, state = Path(cfg["pipeline"]["work_dir"]), Path(cfg["pipeline"]["state_dir"])
    info = read_table(work / "04_topic_info.parquet")
    lcfg = cfg["labeling"]

    if lcfg["provider"] == "off" and client is None:
        out = pd.DataFrame([{"level": "fine", "topic_id": int(r.topic_id),
                             **_fallback(r.top_keywords, r.top_terms, int(r.topic_id)), "cache_key": "fallback"}
                            for r in info.itertuples()], columns=LABEL_COLUMNS)
        write_table(out, work / "05_labels.parquet")
        print(f"[label] provider=off → keyword-based labels for {len(out)} topics")
        return out

    df = read_table(work / "02_docs.parquet")
    labels = (df[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id", how="left")
              ["fine_topic"].fillna(-1).astype(int).to_numpy())
    emb = np.load(work / "03_embeddings.npy")
    C = np.load(work / "04_centroids.npy")
    pos = {t: i for i, t in enumerate(json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8")))}
    acfg = lcfg["api"]
    model = acfg["model"]

    prompts: dict[int, tuple[str, str]] = {}
    for r in info.itertuples():
        tid = int(r.topic_id)
        members = np.where(labels == tid)[0]
        idx = representative_indices(emb[members], C[pos[tid]], int(lcfg["n_repr_docs"]), float(lcfg["mmr_lambda"]))
        titles = "\n".join(f"- {t}" for t in df["title"].iloc[members[idx]])
        prompt = PROMPT_TEMPLATE.format(keywords=r.top_keywords, terms=r.top_terms, titles=titles)
        prompts[tid] = (_cache_key(model, prompt), prompt)

    cache_path = state / "label_cache.parquet"
    try:
        cache = read_table(cache_path)
    except FileNotFoundError:
        cache = pd.DataFrame(columns=CACHE_COLUMNS)
    known = set(cache["cache_key"])
    todo = [(k, p) for k, p in dict(prompts.values()).items() if k not in known]
    print(f"[label] {len(todo)} topics to label, {len(prompts) - len(todo)} from cache")
    if todo:
        if client is None:
            from openai import OpenAI  # optional dependency

            api_key = os.environ.get(acfg["api_key_env"], "")
            if not api_key:
                raise OSError(f"set ${acfg['api_key_env']} for labeling.provider=api")
            client = OpenAI(base_url=acfg["base_url"], api_key=api_key, timeout=120)

        def one(item):
            key, prompt = item
            return {"cache_key": key, **_call_llm(client, model, prompt, float(acfg["temperature"]),
                                                  int(acfg["max_retries"]))}

        with ThreadPoolExecutor(max_workers=int(acfg["concurrency"])) as ex:
            new = list(ex.map(one, todo))
        cache = pd.concat([cache, pd.DataFrame(new, columns=CACHE_COLUMNS)], ignore_index=True)
        write_table(cache.drop_duplicates("cache_key", keep="last"), cache_path)

    by_key = cache.drop_duplicates("cache_key", keep="last").set_index("cache_key")
    out = pd.DataFrame([{"level": "fine", "topic_id": tid, **by_key.loc[key, CACHE_COLUMNS[1:]].to_dict(),
                         "cache_key": key} for tid, (key, _) in sorted(prompts.items())], columns=LABEL_COLUMNS)
    write_table(out, work / "05_labels.parquet")
    return out
```

- [ ] **Step 4: Sync `prompts/topic_label.th.md`** — replace its "Prompt (master)" code block with `PROMPT_TEMPLATE` exactly (with single braces, i.e. as rendered), and note under it: "inputs: `keywords` = top author keywords, `terms` = c-TF-IDF words, `titles` = MMR representative titles; cache key = sha256(model + prompt)".

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_label.py -q`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/label.py pipeline/tests/test_label.py prompts/topic_label.th.md
git commit -m "fix(pipeline): label cache keyed by prompt content; MMR representative titles

Prompt changed (adds author keywords) — prompts/topic_label.th.md synced.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 12: Series tables + Emerging v2 + `EMERGING_SPEC.md` v2

The `compute_emerging` code below was validated on 2026-10-18 against the 9 unit scenarios in Step 1 and the full 20K synthetic run (all planted roles recovered). Two traps found while validating, already handled: (1) a perfectly flat topic made statsmodels' χ² scale 0 → NaN growth → wrongly `LOW_DATA`; fixed by `φ = max(1, χ²/df)`; (2) the institution rule must be skipped when affiliations are unknown (table inputs).

**Files:**
- Modify: `pipeline/atlas/topics_time.py`, `pipeline/atlas/emerging.py` (full rewrites), `docs/EMERGING_SPEC.md` (rewrite)
- Replace: `pipeline/tests/test_emerging.py`
- Create: `pipeline/tests/test_series.py`

**Interfaces:**
- Consumes: `work/02_docs`, `04_fine_topics`, `04_topic_info`, `01_authors`; cfg `emerging.*`.
- Produces:
  - `last_complete_year(totals: pd.Series, ecfg: dict) -> int`; `build_series(cfg) -> pd.DataFrame` writing `06_series` (`topic_id, year, count, count_with_org, corpus_total, share`; corpus_total counts ALL dated articles incl. unassigned), `06_topic_journal_year` (`topic_id, journal, year, count`), `06_topic_org_year` (`topic_id, org_key, year, count`), `06_journal_first_year` (`journal, first_year`), `06_meta.json` (`{"last_complete_year": int, "years": [...], "totals": {"YYYY": n}}` — plain JSON).
  - `share_growth(counts, totals, years, z) -> (growth, lo, hi)`, `kleinberg_burst(counts, totals, s, gamma) -> list[int]`, `topic_novelty(cnt, yrs, r_years, last_year) -> float`, `compute_emerging(series, last_year, ecfg, jseries, oseries, jfirst, coherence=None) -> DataFrame`, `emerging(cfg) -> DataFrame` writing `07_emerging`.
  - `07_emerging` columns: `topic_id, count_recent, share_recent, share_baseline, share_ratio, share_growth, share_growth_lo, share_growth_hi, cagr_recent, acceleration, burst_frac, burst_years, novelty, coherence, n_journals_R, journal_hhi, new_journal_share, n_orgs_R, org_coverage_R, status, journal_driven, large_share_threshold, emerging_score, last_complete_year, definition_version`.
  - `STATUSES = ("EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA")`.

- [ ] **Step 1: Write the failing tests — replace `pipeline/tests/test_emerging.py` entirely**

```python
import numpy as np
import pandas as pd
import pytest

from atlas.config import load_config
from atlas.emerging import STATUSES, compute_emerging, kleinberg_burst, share_growth

ECFG = load_config(None)["emerging"]          # tests lock the shipped defaults
YEARS = list(range(2015, 2025))               # last complete 2024 → R 2022–24, W 2020–24, B 2017–21
OLD4 = [("j_old_a", .25), ("j_old_b", .25), ("j_old_c", .25), ("j_old_d", .25)]


def make_inputs(specs, years=YEARS, corpus=100_000):
    rows, jrows, orows = [], [], []
    for tid, sp in specs.items():
        orgs = sp.get("orgs", 5)
        for y in years:
            c = int(sp["counts"].get(y, 0))
            rows.append(dict(topic_id=tid, year=y, count=c, corpus_total=corpus, share=c / corpus,
                             count_with_org=c if orgs else 0))
            for j, frac in sp.get("journals", OLD4):
                if round(c * frac):
                    jrows.append(dict(topic_id=tid, journal=j, year=y, count=round(c * frac)))
            for o in range(orgs):
                if c:
                    orows.append(dict(topic_id=tid, org_key=f"org{o}", year=y, count=max(1, c // orgs)))
    js = pd.DataFrame(jrows, columns=["topic_id", "journal", "year", "count"])
    os_ = pd.DataFrame(orows, columns=["topic_id", "org_key", "year", "count"])
    jf = js.groupby("journal")["year"].min().rename("first_year").reset_index()
    return pd.DataFrame(rows), js, os_, jf


EM = {**{y: 10 for y in range(2015, 2020)}, 2020: 15, 2021: 25, 2022: 60, 2023: 120, 2024: 240}
SPECS = {
    1: {"counts": EM},                                                            # EMERGING
    2: {"counts": {2022: 60, 2023: 120, 2024: 240}, "journals": [("j_new", 1.0)], "orgs": 1},  # new journal → WATCH
    3: {"counts": {y: round(3000 * 1.03 ** (y - 2015)) for y in YEARS}},          # large & growing → HOT
    4: {"counts": {y: round(2000 * 0.85 ** (y - 2015)) for y in YEARS}},          # → DECLINING
    5: {"counts": {y: 2500 for y in YEARS}},                                      # perfectly flat → STABLE
    6: {"counts": {2022: 3, 2023: 5, 2024: 8}},                                   # tiny → LOW_DATA
    7: {"counts": {2015: 40, 2016: 40}},                                          # nothing in W → LOW_DATA, no crash
    8: {"counts": EM, "journals": [("j_old_a", 1.0)]},                            # one journal → WATCH
    9: {"counts": EM, "orgs": 0},                                                 # affiliations unknown → rule skipped
}
EXPECTED = {1: "EMERGING", 2: "WATCH", 3: "HOT", 4: "DECLINING", 5: "STABLE", 6: "LOW_DATA",
            7: "LOW_DATA", 8: "WATCH", 9: "EMERGING"}


@pytest.fixture(scope="module")
def result():
    s, js, os_, jf = make_inputs(SPECS)
    return compute_emerging(s, 2024, ECFG, js, os_, jf, coherence={1: 0.9, 5: 0.8}).set_index("topic_id")


@pytest.mark.parametrize("tid", sorted(EXPECTED))
def test_status_rules(result, tid):
    assert result.loc[tid, "status"] == EXPECTED[tid]


def test_journal_driven_flag(result):
    assert bool(result.loc[2, "journal_driven"]) and bool(result.loc[8, "journal_driven"])
    assert not bool(result.loc[1, "journal_driven"])
    assert result.loc[2, "new_journal_share"] == 1.0


def test_scores_bounded_and_ranked(result):
    assert result["emerging_score"].between(0, 100.0001).all()
    assert result.loc[1, "emerging_score"] > result.loc[5, "emerging_score"]
    assert set(result["status"]) <= set(STATUSES)
    assert (result["definition_version"] == 2).all()


def test_two_year_corpus_does_not_crash():
    s, js, os_, jf = make_inputs({1: {"counts": {2023: 50, 2024: 80}}, 2: {"counts": {2023: 5, 2024: 9}}},
                                 years=[2023, 2024])
    m = compute_emerging(s, 2024, ECFG, js, os_, jf)
    assert set(m["status"]) == {"LOW_DATA"}


def test_share_growth_recovers_known_rate():
    years = np.arange(2020, 2025)
    counts = 100 * 1.2 ** (years - 2020)
    g, lo, hi = share_growth(counts, np.full(5, 10_000.0), years, z=1.645)
    assert abs(g - 0.2) < 0.01 and lo < g < hi
    assert all(np.isnan(share_growth([0, 0, 0], [10, 10, 10], [1, 2, 3], 1.645)))


def test_kleinberg_detects_planted_burst_and_ignores_flat():
    corp = np.full(8, 10_000.0)
    assert kleinberg_burst(np.array([5, 5, 5, 5, 5, 50, 50, 5.0]), corp) == [5, 6]
    assert kleinberg_burst(np.full(8, 20.0), corp) == []
```

- [ ] **Step 2: Write the failing series test `pipeline/tests/test_series.py`**

```python
import json

import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.topics_time import build_series


def test_series_backfill_guard_and_tables(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    rows, topics = [], []
    for y in range(2019, 2025):
        n = 2 if y == 2024 else 10                         # 2024 incomplete (< 60% of median)
        for i in range(n):
            aid = f"{y}-{i}"
            rows.append({"article_id": aid, "year": y, "journal_name": "jA" if i % 2 else "jB"})
            topics.append({"article_id": aid, "fine_topic": 0 if i < n / 2 else -1})
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    write_table(pd.DataFrame(topics), work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows[::2]], "org_key": "orgX"}),
                work / "01_authors.parquet")
    s = build_series(cfg)
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    assert meta["last_complete_year"] == 2023 and s["year"].max() == 2023
    assert set(s["topic_id"]) == {0}                          # unassigned (-1) never becomes a topic
    assert (s["corpus_total"] == 10).all()                    # ... but counts in the denominator
    assert (s["count"] == 5).all() and (s["count_with_org"] <= s["count"]).all()
    jf = read_table(work / "06_journal_first_year.parquet").set_index("journal")["first_year"]
    assert jf.to_dict() == {"jA": 2019, "jB": 2019}
    assert len(read_table(work / "06_topic_org_year.parquet")) > 0
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_emerging.py tests/test_series.py -q`
Expected: FAIL — `ImportError: cannot import name 'STATUSES'` / `compute_emerging`.

- [ ] **Step 4: Replace `pipeline/atlas/topics_time.py`**

```python
"""Yearly series per topic + journal/institution tables for Emerging v2, with backfill guard.

corpus_total counts ALL dated articles (assigned or not) — it is the share denominator.
Outputs: 06_series, 06_topic_journal_year, 06_topic_org_year, 06_journal_first_year, 06_meta.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table


def last_complete_year(totals: pd.Series, ecfg: dict) -> int:
    if ecfg.get("min_year_complete") is not None:
        return int(ecfg["min_year_complete"])
    ymax = int(totals.index.max())
    if len(totals) > 1 and totals.loc[ymax] < float(ecfg["backfill_min_ratio"]) * totals.median():
        print(f"[series] {ymax} looks incomplete (backfill guard) — analysis stops at {ymax - 1}")
        return ymax - 1
    return ymax


def build_series(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    docs = read_table(work / "02_docs.parquet")[["article_id", "year", "journal_name"]]
    fine = read_table(work / "04_fine_topics.parquet")
    try:
        authors = read_table(work / "01_authors.parquet")[["article_id", "org_key"]]
    except FileNotFoundError:
        authors = pd.DataFrame(columns=["article_id", "org_key"])

    d = docs.merge(fine, on="article_id", how="left")
    d = d[d["year"].notna()].copy()
    d["year"] = d["year"].astype(int)
    d["fine_topic"] = d["fine_topic"].fillna(-1).astype(int)
    jfirst = (d.groupby("journal_name")["year"].min().rename("first_year").reset_index()
              .rename(columns={"journal_name": "journal"}))

    totals = d.groupby("year").size()
    cutoff = last_complete_year(totals, cfg["emerging"])
    d, totals = d[d["year"] <= cutoff], totals[totals.index <= cutoff]
    a = d[d["fine_topic"] >= 0]

    orgs = authors[authors["org_key"].astype(str) != ""].drop_duplicates(["article_id", "org_key"])
    a = a.assign(has_org=a["article_id"].isin(set(orgs["article_id"])))
    counts = (a.groupby(["fine_topic", "year"]).agg(count=("article_id", "size"), count_with_org=("has_org", "sum"))
              .reset_index().rename(columns={"fine_topic": "topic_id"}))
    grid = pd.MultiIndex.from_product([sorted(a["fine_topic"].unique()), sorted(totals.index)],
                                      names=["topic_id", "year"]).to_frame(index=False)
    s = grid.merge(counts, on=["topic_id", "year"], how="left").fillna({"count": 0, "count_with_org": 0})
    s[["count", "count_with_org"]] = s[["count", "count_with_org"]].astype(int)
    s = s.merge(totals.rename("corpus_total").reset_index(), on="year")
    s["share"] = s["count"] / s["corpus_total"]

    js = (a.groupby(["fine_topic", "journal_name", "year"]).size().rename("count").reset_index()
          .rename(columns={"fine_topic": "topic_id", "journal_name": "journal"}))
    oa = a[["article_id", "fine_topic", "year"]].merge(orgs, on="article_id")
    os_ = (oa.groupby(["fine_topic", "org_key", "year"]).size().rename("count").reset_index()
           .rename(columns={"fine_topic": "topic_id"}))

    write_table(s, work / "06_series.parquet")
    write_table(js, work / "06_topic_journal_year.parquet")
    write_table(os_, work / "06_topic_org_year.parquet")
    write_table(jfirst, work / "06_journal_first_year.parquet")
    (work / "06_meta.json").write_text(json.dumps({
        "last_complete_year": int(cutoff),
        "years": [int(y) for y in totals.index],
        "totals": {str(int(y)): int(c) for y, c in totals.items()},
    }), encoding="utf-8")
    print(f"[series] {s['topic_id'].nunique()} topics × {len(totals)} years (≤ {cutoff}) → 06_series")
    return s
```

- [ ] **Step 5: Replace `pipeline/atlas/emerging.py`**

```python
"""Emerging Topic Analysis — definition v2 (source of truth: docs/EMERGING_SPEC.md).

Windows: R = recent_window last complete years, B = baseline_window years before R,
W = trend_window last years. Per topic:
  share_growth (+90% CI)  Poisson GLM log E[c_t] = log N_t + a + b·t, quasi-Poisson SE
  share_ratio             share_R / share_B
  acceleration            log growth in R − log growth in B
  burst_frac              Kleinberg burst years ∩ R / |R|
  novelty                 recency + topic age
  breadth                 journals / institutions in R, share from journals new in R
Statuses (in order): LOW_DATA, EMERGING, WATCH, HOT, DECLINING, STABLE.
Score 0–100 = weighted percentile ranks within the run (ranking only; not comparable across runs).
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table

EPS = 1e-12
STATUSES = ("EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA")


def _cagr(first: float, last: float, periods: int) -> float:
    return 0.0 if periods <= 0 else float(((last + 0.5) / (first + 0.5)) ** (1 / periods) - 1)


def share_growth(counts, totals, years, z: float) -> tuple[float, float, float]:
    """Annual growth of the topic's SHARE of the corpus with a confidence interval.

    Poisson GLM  log E[c_t] = log N_t + a + b·(t − t̄)  (offset = corpus size).
    Quasi-Poisson standard errors: se = se_Poisson · sqrt(φ), φ = max(1, Pearson χ²/df) —
    overdispersion widens the interval, underdispersion never narrows it below Poisson.
    Returns (e^b − 1, e^(b − z·se) − 1, e^(b + z·se) − 1); NaNs when not estimable.
    """
    c, n, t = (np.asarray(a, dtype=float) for a in (counts, totals, years))
    ok = n > 0
    c, n, t = c[ok], n[ok], t[ok]
    nan = (math.nan, math.nan, math.nan)
    if len(c) < 3 or c.sum() == 0:
        return nan
    import statsmodels.api as sm

    X = sm.add_constant(t - t.mean(), has_constant="add")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = sm.GLM(c, X, family=sm.families.Poisson(), offset=np.log(n)).fit()
        phi = max(1.0, float(fit.pearson_chi2) / max(float(fit.df_resid), 1.0))
        b, se = float(fit.params[1]), float(fit.bse[1]) * math.sqrt(phi)
    except Exception:  # noqa: BLE001 — degenerate series → not estimable
        return nan
    if not (math.isfinite(b) and math.isfinite(se)):
        return nan
    return math.exp(b) - 1, math.exp(b - z * se) - 1, math.exp(b + z * se) - 1


def _poisson_nll(c: np.ndarray, lam: np.ndarray) -> np.ndarray:
    lam = np.maximum(lam, EPS)
    return -(c * np.log(lam) - lam - np.array([math.lgamma(x + 1) for x in c]))


def kleinberg_burst(counts, totals, s: float = 2.0, gamma: float = 1.0) -> list[int]:
    """Kleinberg (2003) two-state burst automaton on yearly batches.

    The burst state expects s × the topic's base rate (scaled by each year's corpus size);
    moving UP into it costs γ·ln(T) (T = number of years), moving down is free.
    Returns the indices of burst years.
    """
    counts = np.asarray(counts, dtype=float)
    totals = np.asarray(totals, dtype=float)
    T = len(counts)
    if T == 0 or counts.sum() == 0:
        return []
    p0 = counts.sum() / max(totals.sum(), 1.0)
    p1 = min(p0 * s, 0.9999)
    if p1 <= p0:
        return []
    cost = np.vstack([_poisson_nll(counts, totals * p0), _poisson_nll(counts, totals * p1)])
    up = gamma * math.log(T) if T > 1 else gamma
    dp = np.zeros((T, 2))
    back = np.zeros((T, 2), dtype=int)
    dp[0] = [cost[0, 0], cost[1, 0] + up]
    for t in range(1, T):
        stay0, from1 = dp[t - 1, 0], dp[t - 1, 1]            # into state 0: free from either
        dp[t, 0], back[t, 0] = (stay0, 0) if stay0 <= from1 else (from1, 1)
        stay1, from0 = dp[t - 1, 1], dp[t - 1, 0] + up       # into state 1: pay to move up
        dp[t, 1], back[t, 1] = (stay1, 1) if stay1 <= from0 else (from0, 0)
        dp[t] += cost[:, t]
    state = int(np.argmin(dp[-1]))
    states = [0] * T
    for t in range(T - 1, -1, -1):
        states[t] = state
        state = back[t, state]
    return [i for i, st in enumerate(states) if st == 1]


def topic_novelty(cnt: np.ndarray, yrs: np.ndarray, r_years: list[int], last_year: int) -> float:
    """0.5 × share of the topic's articles that fall in R + 0.5 × (1 − age/15).

    age = years since the topic first reached max(3, 10% of its peak) articles.
    """
    total = cnt.sum()
    if total <= 0:
        return 0.0
    recent = cnt[np.isin(yrs, r_years)].sum() / total
    hit = cnt >= max(3.0, 0.1 * cnt.max())
    first = int(yrs[np.argmax(hit)]) if hit.any() else last_year
    age = max(0, last_year - first)
    return float(0.5 * recent + 0.5 * (1 - min(age, 15) / 15))


def compute_emerging(series: pd.DataFrame, last_year: int, ecfg: dict, jseries: pd.DataFrame,
                     oseries: pd.DataFrame, jfirst: pd.DataFrame,
                     coherence: dict | None = None) -> pd.DataFrame:
    wR, wB, wW = int(ecfg["recent_window"]), int(ecfg["baseline_window"]), int(ecfg["trend_window"])
    R = list(range(last_year - wR + 1, last_year + 1))
    B = list(range(last_year - wR - wB + 1, last_year - wR + 1))
    W = list(range(last_year - wW + 1, last_year + 1))
    z = NormalDist().inv_cdf(0.5 + float(ecfg["ci_level"]) / 2)
    bcfg, br = ecfg["burst"], ecfg["breadth"]
    new_j = set(jfirst.loc[jfirst["first_year"] >= R[0], "journal"])
    jR = jseries[jseries["year"].isin(R) & (jseries["count"] > 0)]
    oR = oseries[oseries["year"].isin(R) & (oseries["count"] > 0)]
    coherence = coherence or {}

    rows = []
    for tid, g in series.groupby("topic_id"):
        g = g.sort_values("year")
        yrs = g["year"].to_numpy()
        cnt = g["count"].to_numpy(dtype=float)
        tot = g["corpus_total"].to_numpy(dtype=float)
        with_org = g["count_with_org"].to_numpy(dtype=float) if "count_with_org" in g else cnt
        inR, inB, inW = np.isin(yrs, R), np.isin(yrs, B), np.isin(yrs, W)
        count_R = float(cnt[inR].sum())
        share_R = count_R / max(tot[inR].sum(), 1.0)
        share_B = cnt[inB].sum() / max(tot[inB].sum(), 1.0)
        growth, lo, hi = share_growth(cnt[inW], tot[inW], yrs[inW], z)
        g_R = share_growth(cnt[inR], tot[inR], yrs[inR], z)[0]
        g_B = share_growth(cnt[inB], tot[inB], yrs[inB], z)[0]
        accel = (math.log1p(g_R) if math.isfinite(g_R) else 0.0) - (math.log1p(g_B) if math.isfinite(g_B) else 0.0)
        bursts = [int(yrs[i]) for i in kleinberg_burst(cnt, tot, float(bcfg["s"]), float(bcfg["gamma"]))]
        tj = jR[jR["topic_id"] == tid].groupby("journal")["count"].sum()
        tj_total = float(tj.sum())
        rows.append({
            "topic_id": tid,
            "count_recent": int(count_R),
            "share_recent": share_R,
            "share_baseline": share_B,
            "share_ratio": (share_R + EPS) / (share_B + EPS),
            "share_growth": growth,
            "share_growth_lo": lo,
            "share_growth_hi": hi,
            "cagr_recent": _cagr(cnt[inR][0], cnt[inR][-1], int(inR.sum()) - 1) if inR.any() else 0.0,
            "acceleration": accel,
            "burst_frac": len(set(bursts) & set(R)) / len(R),
            "burst_years": ",".join(map(str, bursts)),
            "novelty": topic_novelty(cnt, yrs, R, last_year),
            "coherence": float(coherence.get(tid, math.nan)),
            "n_journals_R": int(len(tj)),
            "journal_hhi": float(((tj / tj_total) ** 2).sum()) if tj_total else 0.0,
            "new_journal_share": float(tj[tj.index.isin(new_j)].sum() / tj_total) if tj_total else 0.0,
            "n_orgs_R": int(oR.loc[oR["topic_id"] == tid, "org_key"].nunique()),
            "org_coverage_R": float(with_org[inR].sum() / count_R) if count_R else 0.0,
        })
    m = pd.DataFrame(rows)
    if m.empty:
        return m

    low = (m["count_recent"] < int(ecfg["min_articles_recent"])) | m["share_growth"].isna()
    size = ecfg["size"]
    if size["rule"] == "quantile":
        thr = float(m.loc[~low, "share_recent"].quantile(float(size["large_quantile"]))) if (~low).any() else math.inf
    else:
        thr = float(size["large_share"])
    large = m["share_recent"] >= thr
    em, hot, dec = ecfg["emerging"], ecfg["hot"], ecfg["declining"]
    growth_ok = ~large & (m["share_growth_lo"] >= em["min_growth_lo"]) & (m["share_ratio"] >= em["min_share_ratio"])
    # the institution rule only applies when we actually know the institutions (>= min_org_coverage)
    orgs_ok = (m["n_orgs_R"] >= br["min_orgs"]) | (m["org_coverage_R"] < br["min_org_coverage"])
    breadth_ok = ((m["n_journals_R"] >= br["min_journals"]) & orgs_ok
                  & (m["new_journal_share"] < br["max_new_journal_share"]))
    m["status"] = np.select(
        [low, growth_ok & breadth_ok, growth_ok,
         large & (m["share_growth_lo"] > hot["min_growth_lo"]),
         (m["share_growth_hi"] < dec["max_growth_hi"]) & (m["share_ratio"] <= dec["max_share_ratio"])],
        ["LOW_DATA", "EMERGING", "WATCH", "HOT", "DECLINING"], default="STABLE")
    m["journal_driven"] = growth_ok & ~breadth_ok
    m["large_share_threshold"] = thr

    w = ecfg["score_weights"]
    coh = m["coherence"]
    parts = {
        "growth": m["share_growth_lo"].fillna(-1.0),
        "acceleration": m["acceleration"].fillna(0.0),
        "burst": m["burst_frac"],
        "novelty": m["novelty"],
        "coherence": coh.fillna(coh.median() if coh.notna().any() else 0.0),
        "breadth": np.log1p(m["n_journals_R"]) + np.log1p(m["n_orgs_R"]),
    }
    m["emerging_score"] = 100 * sum(float(w[k]) * v.rank(pct=True) for k, v in parts.items())
    m["last_complete_year"] = last_year
    m["definition_version"] = 2
    return m.sort_values("emerging_score", ascending=False).reset_index(drop=True)


def emerging(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    info = read_table(work / "04_topic_info.parquet")
    m = compute_emerging(
        read_table(work / "06_series.parquet"), int(meta["last_complete_year"]), cfg["emerging"],
        read_table(work / "06_topic_journal_year.parquet"), read_table(work / "06_topic_org_year.parquet"),
        read_table(work / "06_journal_first_year.parquet"),
        coherence=dict(zip(info["topic_id"], info["coherence"])),
    )
    write_table(m, work / "07_emerging.parquet")
    print(f"[emerging] v2 {len(m)} topics | " + ", ".join(f"{k}={v}" for k, v in m["status"].value_counts().items()))
    return m
```

- [ ] **Step 6: Rewrite `docs/EMERGING_SPEC.md` as v2** (full replacement)

````markdown
# EMERGING_SPEC — นิยาม "Emerging" ของ TCI (definition_version 2)

> **source of truth** ของนิยาม — ถ้าโค้ดกับเอกสารไม่ตรงกัน ถือเป็นบั๊ก
> Implementation: `pipeline/atlas/emerging.py` · Thresholds: `config.yaml → emerging:` · Tests: `pipeline/tests/test_emerging.py`
> อนุมัติใช้ v2 เมื่อ 2026-10-18 (ยังไม่เคยเผยแพร่ตัวเลข v1 ต่อสาธารณะ) — v1 อยู่ในภาคผนวก

## 1. ปรัชญา
คำถามของผู้บริหาร: **"อะไรที่ยังเล็ก แต่โตเร็วอย่างมีนัยสำคัญ และโตจากหลายวารสาร/หลายสถาบัน — ที่อีก 2–3 ปีจะกลายเป็นเรื่องใหญ่?"**
ยึดกรอบ 5 คุณลักษณะของ emergence (Rotolo, Hicks & Martin 2015): ใหม่ · โตเร็ว · เกาะกลุ่ม · มีผลกระทบ · ไม่แน่นอน
- วัด **สัดส่วน (share)** ไม่ใช่จำนวนดิบ (corpus โตทุกปี)
- ทุกการ "โต/ลด" ต้อง **มีนัยสำคัญทางสถิติ** (ช่วงเชื่อมั่น) ไม่ใช่แค่ทิศทางของ noise
- ต้อง **กว้างพอ** (หลายวารสาร หลายสถาบัน) — กันหัวข้อที่ "โต" เพียงเพราะวารสารใหม่เข้าระบบ
- หัวข้อที่ข้อมูลน้อยเกินจะ **ไม่ถูกฟันธง** (`LOW_DATA`)

## 2. หน้าต่างเวลา
- `last_complete_year` = ปีล่าสุดที่ข้อมูลสมบูรณ์ (backfill guard: ปีล่าสุดที่ยอดรวม < `backfill_min_ratio` × median ถูกตัด; ตั้งเองได้ด้วย `min_year_complete`)
- **R** = `recent_window` ปีล่าสุด (3) · **B** = `baseline_window` ปีก่อน R (5) · **W** = `trend_window` ปีล่าสุด (5) ใช้วัดแนวโน้ม

## 3. มิติที่วัดต่อหัวข้อ
| มิติ | วิธีคำนวณ | ความหมาย |
|---|---|---|
| `share_recent`, `share_baseline` | บทความหัวข้อ ÷ บทความทั้งหมด ในช่วง R / B (ตัวหารรวมบทความที่ยังไม่จัดหมวด) | ขนาดสัมพัทธ์ |
| `share_ratio` | share_R ÷ share_B | โตเร็วกว่าภาพรวมกี่เท่า |
| `share_growth` (+`_lo`, `_hi`) | Poisson GLM `log E[c_t] = log N_t + a + b·t` บนปีใน W; growth = e^b − 1; ช่วงเชื่อมั่น `ci_level` (90%) ด้วย quasi-Poisson SE `se·√φ`, `φ = max(1, χ²/df)` | อัตราโตต่อปีของ share พร้อมความไม่แน่นอน |
| `acceleration` | log growth ใน R − log growth ใน B | เร่งตัวหรือชะลอ |
| `burst_frac`, `burst_years` | Kleinberg 2 สถานะ (§5) | สัดส่วนปีใน R ที่ "ระเบิด" |
| `novelty` | 0.5 × สัดส่วนบทความของหัวข้อที่อยู่ใน R + 0.5 × (1 − อายุ/15), อายุ = ปีนับจากปีแรกที่ยอด ≥ max(3, 10% ของจุดสูงสุด) | ความใหม่ |
| `coherence` | cosine เฉลี่ยของบทความกับ centroid | หัวข้อเกาะกลุ่มชัดเจนแค่ไหน |
| `n_journals_R`, `n_orgs_R` | จำนวนวารสาร / สถาบันที่มีบทความในหัวข้อช่วง R | ความกว้างของชุมชน |
| `new_journal_share` | สัดส่วนบทความใน R ที่มาจากวารสารที่ปรากฏครั้งแรกในช่วง R | ตัวชี้ journal-entry bias |
| `journal_hhi` | Herfindahl ของวารสารใน R | การกระจุกตัว |

## 4. ขนาด "ใหญ่/เล็ก"
`large` = `share_recent` ≥ quantile `size.large_quantile` (0.75) ของหัวข้อที่จำแนกได้ (ไม่รวม `LOW_DATA`) — ใช้ค่าตายตัว `size.large_share` ได้ด้วย `size.rule: absolute`

## 5. Kleinberg burst detection
สถานะ burst คาดหวังอัตรา `s` × อัตราปกติ (ปรับตามขนาด corpus รายปี, Poisson) · ค่าเข้าสถานะ burst = `γ·ln(T)` (T = จำนวนปี) ลงฟรี · หาเส้นทางด้วย Viterbi · `burst_frac` = |burst ∩ R| / |R|

## 6. เกณฑ์สถานะ (ตรวจตามลำดับ — ข้อแรกที่เข้าคือคำตอบ)
| ลำดับ | สถานะ | เงื่อนไข (ค่าดีฟอลต์) |
|---|---|---|
| 1 | `LOW_DATA` ข้อมูลน้อย | count_R < 30 **หรือ** ประมาณ share_growth ไม่ได้ |
| 2 | `EMERGING` กำลังเกิดใหม่ | เล็ก **และ** `share_growth_lo` ≥ +10%/ปี **และ** `share_ratio` ≥ 1.8 **และ** ความกว้างผ่าน |
| 3 | `WATCH` จับตา | เข้าเกณฑ์การเติบโตของข้อ 2 แต่ **ความกว้างไม่ผ่าน** |
| 4 | `HOT` กำลังร้อน | ใหญ่ **และ** `share_growth_lo` > 0 |
| 5 | `DECLINING` กำลังลดลง | `share_growth_hi` < 0 **และ** `share_ratio` ≤ 0.8 |
| 6 | `STABLE` คงที่ | อื่น ๆ |

**ความกว้างผ่าน** = `n_journals_R` ≥ 3 **และ** (`n_orgs_R` ≥ 3 **หรือ** บทความใน R มีข้อมูลสังกัด < 50%) **และ** `new_journal_share` < 0.5
`journal_driven` = เข้าเกณฑ์การเติบโต แต่ความกว้างไม่ผ่าน (ตรงกับ `WATCH`)

## 7. Emerging Score (0–100)
`score = 100 × Σ wᵢ · P(มิติᵢ)` — P = percentile rank ภายในรอบรันเดียวกัน
น้ำหนัก: growth (`share_growth_lo`) 0.30 · acceleration 0.20 · burst 0.15 · novelty 0.15 · coherence 0.10 · breadth (`log(1+journals) + log(1+orgs)`) 0.10
⚠️ ใช้ **จัดอันดับ** เท่านั้น — เทียบ score ข้ามรอบรันไม่ได้ (ใช้มิติดิบ เช่น `share_growth` ถ้าต้องการเทียบ)

## 8. ตัวอย่าง (จาก tests)
| หัวข้อ | ข้อมูล | ผล |
|---|---|---|
| A | 10/ปี → 60, 120, 240 ใน R, 4 วารสาร 5 สถาบัน | `EMERGING` |
| B | เกิดปี 2022 จากวารสารใหม่ 1 ฉบับ | `WATCH` (journal_driven) |
| C | ใหญ่ โต +3%/ปี สม่ำเสมอ | `HOT` |
| D | ลด 15%/ปี | `DECLINING` |
| E | คงที่ 2,500/ปี | `STABLE` |
| F | 3, 5, 8 เรื่องใน R | `LOW_DATA` |

## 9. การทดสอบ
`pipeline/tests/test_emerging.py` ล็อก: สถานะของทั้ง 9 สถานการณ์, flag journal_driven, ขอบเขต score, corpus 2 ปีไม่ crash, GLM คืนอัตราโตที่ฝังไว้, Kleinberg เจอ burst ที่ฝังไว้
`pipeline/tests/test_e2e_synth.py` (slow): corpus สังเคราะห์ 20K เรื่อง — ต้องได้ EMERGING / WATCH / HOT / DECLINING ตามที่ฝังไว้ และไม่มี HOT/DECLINING ปลอมในหัวข้อคงที่

แก้นิยาม = แก้เอกสารนี้ + `config.example.yaml` + tests พร้อมกันเสมอ และเพิ่ม `definition_version`

## ภาคผนวก — นิยาม v1 (เลิกใช้ 2026-10-18)
EMERGING: share_R < 1.5% และ CAGR(ปีแรก–ปีสุดท้ายของ R) ≥ 25% และ share_ratio ≥ 1.8 และ count_R ≥ 30 · HOT: share_R ≥ 1.5% และ slope_share > 0 · DECLINING: share ลด 3 ปีติด · score 4 มิติ (growth 0.35, acceleration 0.25, burst 0.20, novelty 0.20)
เหตุผลที่เลิก: เกณฑ์ไม่มีความไม่แน่นอน (HOT/DECLINING ถูก noise หลอก — DECLINING พังในการทดสอบจริง), 1.5% ขึ้นกับจำนวนหัวข้อ, ไม่กันหัวข้อที่โตเพราะวารสารใหม่, novelty ไม่ทำงานในรอบแรก, burst intensity เอียงไปหาหัวข้อใหญ่
````

- [ ] **Step 7: Run tests**

Run: `uv run pytest tests/test_emerging.py tests/test_series.py -q`
Expected: 15 passed (9 parametrized + 5 + 1).

- [ ] **Step 8: Commit**

```bash
git add pipeline/atlas/topics_time.py pipeline/atlas/emerging.py pipeline/tests/test_emerging.py pipeline/tests/test_series.py docs/EMERGING_SPEC.md
git commit -m "feat(pipeline)!: Emerging v2 — GLM share growth with CI, breadth rule, WATCH/LOW_DATA

Definition change approved by the project owner on 2026-10-18 (definition_version 2).
Spec, config and tests updated together per CLAUDE.md.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 13: Forecast — naive baseline, raw history, skill gating (`atlas/forecast.py`)

**Files:**
- Modify: `pipeline/atlas/forecast.py` (full rewrite)
- Create: `pipeline/tests/test_forecast.py`

**Interfaces:**
- Consumes: `work/06_series`, `06_meta.json` (Task 12); cfg `forecast.*`.
- Produces: `forecast_topic(yrs, cnt, last_year, horizon, backtest_years, models, min_skill) -> dict | None`; `forecast(cfg) -> DataFrame` writing `work/08_forecasts` with columns `FORECAST_COLUMNS = ["topic_id", "model", "backtest_mae", "backtest_mape", "mase", "skill_vs_naive", "show", "hist_years", "hist_counts", "fc_years", "fc_mean", "fc_lo", "fc_hi"]` (list columns stored as JSON strings, as in v1).

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_forecast.py`**

```python
import json

import numpy as np

from atlas.forecast import forecast_topic

YRS = np.arange(2015, 2025)
MODELS = ["naive", "linear", "poisson"]


def test_linear_trend_is_skilful_and_shown():
    r = forecast_topic(YRS, np.arange(10, 110, 10), 2024, 2, 3, MODELS, 0.0)
    assert r["model"] == "linear" and r["show"] is True and r["skill_vs_naive"] == 1.0
    assert json.loads(r["fc_mean"]) == [110.0, 120.0]


def test_unpredictable_jump_is_not_shown():
    r = forecast_topic(YRS, np.array([100] * 7 + [100, 300, 100]), 2024, 2, 3, MODELS, 0.0)
    assert r["model"] == "naive" and r["show"] is False          # nothing beats "same as last year"


def test_history_is_raw_not_winsorized():
    cnt = np.array([10, 12, 500, 14, 15, 16, 18, 19, 20, 22])
    assert 500 in json.loads(forecast_topic(YRS, cnt, 2024, 2, 3, MODELS, 0.0)["hist_counts"])


def test_too_short_history_returns_none():
    assert forecast_topic(np.arange(2021, 2025), np.array([1, 2, 3, 4]), 2024, 2, 3, MODELS, 0.0) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_forecast.py -q`
Expected: FAIL — `ImportError: cannot import name 'forecast_topic'`

- [ ] **Step 3: Replace `pipeline/atlas/forecast.py`**

```python
"""Per-topic forecast (P0): naive / linear / Poisson, chosen by backtest MAE, skill-gated.

skill = 1 − MAE(best) / MAE(naive) over the last `backtest_years`. A forecast is SHOWN only
when the best model is not naive and skill > forecast.min_skill; otherwise the web says
"แนวโน้มไม่แน่นอน". History is exported raw (v1 winsorised it, which distorted charts).
Forecast v2 (share × total, NB/ETS, rolling-origin CV, conformal intervals) arrives in P1.
Output: work/08_forecasts
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table

FORECAST_COLUMNS = ["topic_id", "model", "backtest_mae", "backtest_mape", "mase", "skill_vs_naive", "show",
                    "hist_years", "hist_counts", "fc_years", "fc_mean", "fc_lo", "fc_hi"]


def _fit_predict_naive(yrs, cnt, future):
    d = np.diff(cnt)
    sigma = float(d.std(ddof=1)) if len(d) > 1 else 1.0
    return np.repeat(float(cnt[-1]), len(future)), sigma


def _fit_predict_linear(yrs, cnt, future):
    coef = np.polyfit(yrs, cnt, 1)
    resid = cnt - np.polyval(coef, yrs)
    sigma = float(resid.std(ddof=2)) if len(cnt) > 2 else 1.0
    return np.polyval(coef, future), sigma


def _fit_predict_poisson(yrs, cnt, future):
    import statsmodels.api as sm

    X = sm.add_constant(yrs - yrs.mean(), has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.GLM(cnt, X, family=sm.families.Poisson()).fit()
    resid = cnt - np.asarray(model.predict(X))
    sigma = float(resid.std(ddof=2)) if len(cnt) > 2 else 1.0
    Xf = sm.add_constant(future - yrs.mean(), has_constant="add")
    return np.asarray(model.predict(Xf)), sigma


MODELS = {"naive": _fit_predict_naive, "linear": _fit_predict_linear, "poisson": _fit_predict_poisson}


def _mae(a, p) -> float:
    return float(np.mean(np.abs(a - p)))


def _mape(a, p) -> float:
    return float(np.mean(np.abs(a - p) / np.maximum(np.abs(a), 1.0)) * 100)


def forecast_topic(yrs, cnt, last_year: int, horizon: int, backtest_years: int,
                   models: list[str], min_skill: float) -> dict | None:
    yrs, cnt = np.asarray(yrs, dtype=float), np.asarray(cnt, dtype=float)
    tr = yrs <= last_year - backtest_years
    te = ~tr
    if tr.sum() < 3 or te.sum() == 0:
        return None
    maes: dict[str, float] = {}
    mapes: dict[str, float] = {}
    for name in dict.fromkeys(["naive", *models]):             # naive first → wins ties
        try:
            p, _ = MODELS[name](yrs[tr], cnt[tr], yrs[te])
        except Exception:  # noqa: BLE001 — a failing model is skipped, never fatal
            continue
        p = np.maximum(p, 0)
        maes[name], mapes[name] = _mae(cnt[te], p), _mape(cnt[te], p)
    best = min(maes, key=maes.get)
    skill = 1 - maes[best] / maes["naive"] if maes["naive"] > 0 else 0.0
    scale = float(np.mean(np.abs(np.diff(cnt[tr]))))
    mase = maes[best] / scale if scale > 0 else math.nan
    future = np.arange(last_year + 1, last_year + 1 + horizon, dtype=float)
    pred, sigma = MODELS[best](yrs, cnt, future)
    pred = np.maximum(pred, 0)
    return {
        "model": best,
        "backtest_mae": round(maes[best], 2),
        "backtest_mape": round(mapes[best], 2),
        "mase": round(mase, 3) if math.isfinite(mase) else None,
        "skill_vs_naive": round(skill, 3),
        "show": bool(best != "naive" and skill > min_skill),
        "hist_years": json.dumps([int(y) for y in yrs]),
        "hist_counts": json.dumps([int(c) for c in cnt]),
        "fc_years": json.dumps([int(y) for y in future]),
        "fc_mean": json.dumps([round(float(v), 1) for v in pred]),
        "fc_lo": json.dumps([round(max(float(v) - 1.96 * sigma, 0.0), 1) for v in pred]),
        "fc_hi": json.dumps([round(float(v) + 1.96 * sigma, 1) for v in pred]),
    }


def forecast(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    series = read_table(work / "06_series.parquet")
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    f = cfg["forecast"]
    rows = []
    for tid, g in series.groupby("topic_id"):
        g = g.sort_values("year")
        if len(g) < int(f["min_history_years"]) or g["count"].sum() == 0:
            continue
        r = forecast_topic(g["year"], g["count"], last, int(f["horizon"]), int(f["backtest_years"]),
                           list(f["models"]), float(f["min_skill"]))
        if r:
            rows.append({"topic_id": int(tid), **r})
    out = pd.DataFrame(rows, columns=FORECAST_COLUMNS)
    write_table(out, work / "08_forecasts.parquet")
    shown = int(out["show"].sum()) if len(out) else 0
    print(f"[forecast] {len(out)} topics forecast, {shown} skilful enough to show")
    return out
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_forecast.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add pipeline/atlas/forecast.py pipeline/tests/test_forecast.py
git commit -m "feat(pipeline): forecast naive baseline, raw history, skill gating

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Layout fixes, export v1.1 (strict JSON), minimal web patch

**Files:**
- Modify: `pipeline/atlas/layout.py` (two edits), `pipeline/atlas/export.py` (full rewrite), `web/src/data/atlas.ts` (line 3 only), `web/src/sections/AtlasMap.tsx` (`STATUS_STYLE`), `web/src/sections/EmergingThemes.tsx` (`ORDER`)
- Create: `pipeline/tests/test_export.py`

**Interfaces:**
- Consumes: outputs of Tasks 10–13 (`04_*`, `05_labels`, `07_emerging`, `08_forecasts`, `09_layout`, `09_edges`, `06_meta.json`, `02_docs`).
- Produces: `clean_json(obj)`; `build_atlas(info, labels, layout_df, edges, em, fc, meta, n_articles, include_forecast) -> dict`; `export(cfg) -> dict` writing `output/atlas_data.json` (schema `1.1`), `topics.csv`, `emerging.csv`, `forecasts.csv`, `manifest.json`, and `state/prev/centroids.npy` + `state/prev/centroid_ids.json`.
- atlas_data.json v1.1 = v1 + per topic node: `share_growth, share_growth_lo, share_growth_hi, n_journals_R, n_orgs_R, journal_driven, coherence, forecast_uncertain`; `meta.schema_version="1.1"`, `meta.definition_version=2`, `meta.assigned_articles`, `meta.unassigned_articles`. `forecast` is non-null only when `show` is true.

- [ ] **Step 1: Write the failing test `pipeline/tests/test_export.py`**

```python
import json
import math

import pandas as pd

from atlas.export import build_atlas, clean_json


def _frames():
    info = pd.DataFrame({"topic_id": [0, 1], "size": [30, 10], "top_terms": ["a", "b"], "top_keywords": ["a", "b"],
                         "coarse_topic": [0, 0], "coherence": [0.91, math.nan]})
    labels = pd.DataFrame({"level": "fine", "topic_id": [0, 1], "name_th": ["หนึ่ง", "สอง"], "name_en": ["One", "Two"],
                           "description": "", "keywords": "", "cache_key": "fallback"})
    layout = pd.DataFrame([
        {"kind": "group", "id": 0, "x": 10.0, "y": 10.0, "r": 40.0, "parent": -1},
        {"kind": "topic", "id": 0, "x": 5.0, "y": 5.0, "r": 20.0, "parent": 0},
        {"kind": "topic", "id": 1, "x": 15.0, "y": 15.0, "r": 10.0, "parent": 0}])
    edges = pd.DataFrame({"s": [0], "t": [1], "w": [0.7]})
    em = pd.DataFrame({"topic_id": [0, 1], "status": ["EMERGING", "LOW_DATA"], "emerging_score": [80.0, 20.0],
                       "cagr_recent": [0.5, math.nan], "burst_years": ["2023", ""], "share_growth": [0.4, math.nan],
                       "share_growth_lo": [0.2, math.nan], "share_growth_hi": [0.6, math.nan],
                       "n_journals_R": [4, 1], "n_orgs_R": [5, 1], "journal_driven": [False, False]})
    hist = json.dumps([2019, 2020, 2021, 2022, 2023, 2024])
    fc = pd.DataFrame({"topic_id": [0, 1], "model": ["linear", "naive"], "backtest_mae": [1.0, 2.0],
                       "backtest_mape": [5.0, 9.0], "mase": [0.5, None], "skill_vs_naive": [0.6, 0.0],
                       "show": [True, False], "hist_years": [hist, hist], "hist_counts": ["[1,2,3,4,5,6]"] * 2,
                       "fc_years": ["[2025,2026]"] * 2, "fc_mean": ["[7,8]"] * 2, "fc_lo": ["[6,7]"] * 2,
                       "fc_hi": ["[8,9]"] * 2})
    return info, labels, layout, edges, em, fc


def test_build_atlas_v11_is_strict_json_and_gated():
    atlas = build_atlas(*_frames(), meta={"last_complete_year": 2024}, n_articles=50, include_forecast=True)
    json.dumps(atlas, allow_nan=False)                                   # raises if NaN slipped through
    m = atlas["meta"]
    assert (m["schema_version"], m["definition_version"]) == ("1.1", 2)
    assert (m["total_articles"], m["assigned_articles"], m["unassigned_articles"]) == (50, 40, 10)
    topics = {n["nodeId"]: n for n in atlas["nodes"] if n["kind"] == "topic"}
    assert topics["t0"]["status"] == "EMERGING" and topics["t0"]["forecast"]["fc_mean"] == [7, 8]
    assert topics["t1"]["forecast"] is None and topics["t1"]["forecast_uncertain"] is True
    assert topics["t1"]["coherence"] is None and topics["t1"]["share_growth"] is None
    assert atlas["links"] == [{"s": "t0", "t": "t1", "w": 0.7}]


def test_clean_json_handles_numpy_and_nan():
    import numpy as np

    assert clean_json({"a": np.float64("nan"), "b": [np.int64(3), np.bool_(True)], "c": float("inf")}) == \
        {"a": None, "b": [3, True], "c": None}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_export.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_atlas'`

- [ ] **Step 3: Apply the two `layout.py` edits**

Add `import json` to the imports, then replace
```python
    ids = pd.read_json(work / "04_centroid_ids.json", typ="series").tolist()
```
with
```python
    ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
```
and replace
```python
    pd.DataFrame(edges).to_parquet(work / "09_edges.parquet", index=False)
```
with
```python
    write_table(pd.DataFrame(edges, columns=["s", "t", "w"]), work / "09_edges.parquet")
```

- [ ] **Step 4: Replace `pipeline/atlas/export.py`**

```python
"""Export web-ready JSON (atlas_data.json, schema 1.1) + analyst CSVs + manifest.

1.1 = the v1 contract read by web/src/lib/loader.ts, plus per topic:
  status ∈ EMERGING | WATCH | HOT | DECLINING | STABLE | LOW_DATA   (definition_version 2)
  share_growth(_lo/_hi), n_journals_R, n_orgs_R, journal_driven, coherence, forecast_uncertain
  forecast is non-null only when the skill gate `show` is true
Strict JSON: NaN/Infinity → null (browsers reject NaN in JSON).
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table

SCHEMA_VERSION = "1.1"
# categorical palette for coarse groups (matches the current web atlas)
PALETTE = ["#E5484D", "#8E4EC6", "#3E63DD", "#F76B15", "#30A46C", "#0091FF", "#E93D82",
           "#D6409F", "#AB4ABA", "#12A594", "#00A2C7", "#46A758", "#C44A6B", "#6E56CF",
           "#AD7F58", "#5B5BD6", "#FFB224", "#FF8FA3", "#0E9F6E", "#697177"]


def _git_hash() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or "nogit"
    except Exception:  # noqa: BLE001
        return "nogit"


def clean_json(obj):
    if isinstance(obj, bool | np.bool_):
        return bool(obj)
    if isinstance(obj, int | np.integer):
        return int(obj)
    if isinstance(obj, float | np.floating):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [clean_json(v) for v in obj]
    return obj


def _r(v, nd: int = 3):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, nd) if math.isfinite(f) else None


def build_atlas(info: pd.DataFrame, labels: pd.DataFrame, layout_df: pd.DataFrame, edges: pd.DataFrame,
                em: pd.DataFrame, fc: pd.DataFrame, meta: dict, n_articles: int, include_forecast: bool) -> dict:
    labels = labels[labels["level"] == "fine"].drop_duplicates("topic_id", keep="last").set_index("topic_id")
    em = em.set_index("topic_id")
    fcm = fc.set_index("topic_id") if len(fc) else pd.DataFrame()
    info_i = info.set_index("topic_id")

    coarse_ids = sorted(int(c) for c in info["coarse_topic"].unique())
    color_of = {cid: PALETTE[i % len(PALETTE)] for i, cid in enumerate(coarse_ids)}
    sizes = info.groupby("coarse_topic")["size"].sum()
    groups = []
    for cid in coarse_ids:
        big = int(info[info["coarse_topic"] == cid].sort_values("size", ascending=False)["topic_id"].iloc[0])
        groups.append({"id": f"g{cid}",
                       "th": labels["name_th"].get(big, f"กลุ่ม {cid}"),
                       "en": labels["name_en"].get(big, f"Group {cid}"),
                       "color": color_of[cid], "articles": int(sizes[cid])})
    groups.sort(key=lambda g: -g["articles"])
    for i, g in enumerate(groups):
        g["rank"] = i + 1
    by_gid = {g["id"]: g for g in groups}

    nodes = []
    for _, row in layout_df.iterrows():
        if row["kind"] == "group":
            cid = int(row["id"])
            g = by_gid[f"g{cid}"]
            nodes.append({**g, "nodeId": g["id"], "kind": "group", "x": row["x"], "y": row["y"], "r": row["r"],
                          "nTopics": int((info["coarse_topic"] == cid).sum())})
            continue
        tid = int(row["id"])
        lb = labels.loc[tid] if tid in labels.index else None
        e = em.loc[tid] if tid in em.index else None
        f = fcm.loc[tid] if len(fcm) and tid in fcm.index else None
        show = f is not None and bool(f["show"]) and include_forecast
        nodes.append({
            "nodeId": f"t{tid}", "kind": "topic", "group": f"g{int(row['parent'])}",
            "th": lb["name_th"] if lb is not None else f"หัวข้อ {tid}",
            "en": lb["name_en"] if lb is not None else f"Topic {tid}",
            "description": lb["description"] if lb is not None else "",
            "keywords": lb["keywords"] if lb is not None else "",
            "articles": int(info_i.loc[tid, "size"]),
            "color": color_of[int(row["parent"])],
            "x": row["x"], "y": row["y"], "r": row["r"],
            "status": e["status"] if e is not None else "LOW_DATA",
            "emerging_score": _r(e["emerging_score"], 1) if e is not None else None,
            "cagr_recent": _r(e["cagr_recent"]) if e is not None else None,
            "burst_years": (e["burst_years"] or "") if e is not None else "",
            "share_growth": _r(e["share_growth"]) if e is not None else None,
            "share_growth_lo": _r(e["share_growth_lo"]) if e is not None else None,
            "share_growth_hi": _r(e["share_growth_hi"]) if e is not None else None,
            "n_journals_R": int(e["n_journals_R"]) if e is not None else 0,
            "n_orgs_R": int(e["n_orgs_R"]) if e is not None else 0,
            "journal_driven": bool(e["journal_driven"]) if e is not None else False,
            "coherence": _r(info_i.loc[tid, "coherence"]),
            "forecast": ({
                "model": f["model"], "backtest_mape": _r(f["backtest_mape"], 2), "mase": _r(f["mase"]),
                "skill_vs_naive": _r(f["skill_vs_naive"]),
                "hist_years": json.loads(f["hist_years"]), "hist_counts": json.loads(f["hist_counts"]),
                "fc_years": json.loads(f["fc_years"]), "fc_mean": json.loads(f["fc_mean"]),
                "fc_lo": json.loads(f["fc_lo"]), "fc_hi": json.loads(f["fc_hi"]),
            } if show else None),
            "forecast_uncertain": bool(f is not None and not show),
        })

    assigned = int(info["size"].sum())
    atlas = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": _git_hash(),
            "schema_version": SCHEMA_VERSION,
            "definition_version": 2,
            "last_complete_year": int(meta["last_complete_year"]),
            "total_articles": int(n_articles),
            "assigned_articles": assigned,
            "unassigned_articles": int(n_articles) - assigned,
            "total_topics": int(len(info)),
            "total_groups": len(groups),
        },
        "groups": groups,
        "nodes": nodes,
        "links": [{"s": f"t{int(r['s'])}", "t": f"t{int(r['t'])}", "w": r["w"]} for _, r in edges.iterrows()],
    }
    return clean_json(atlas)


def export(cfg: dict) -> dict:
    work, outdir = Path(cfg["pipeline"]["work_dir"]), Path(cfg["pipeline"]["output_dir"])
    state = Path(cfg["pipeline"]["state_dir"])
    outdir.mkdir(parents=True, exist_ok=True)
    info = read_table(work / "04_topic_info.parquet")
    labels = read_table(work / "05_labels.parquet")
    em = read_table(work / "07_emerging.parquet")
    fc = read_table(work / "08_forecasts.parquet")
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    atlas = build_atlas(info, labels, read_table(work / "09_layout.parquet"), read_table(work / "09_edges.parquet"),
                        em, fc, meta, n_articles=len(read_table(work / "02_docs.parquet")),
                        include_forecast=bool(cfg["export"]["include_forecast_in_json"]))
    (outdir / "atlas_data.json").write_text(json.dumps(atlas, ensure_ascii=False, indent=1, allow_nan=False),
                                            encoding="utf-8")
    if "csv" in cfg["export"]["formats"]:
        lab = labels[["topic_id", "name_th", "name_en", "description", "keywords"]]
        info.merge(lab, on="topic_id", how="left").to_csv(outdir / "topics.csv", index=False, encoding="utf-8")
        em.to_csv(outdir / "emerging.csv", index=False, encoding="utf-8")
        fc.to_csv(outdir / "forecasts.csv", index=False, encoding="utf-8")
    manifest = {
        "pipeline_version": atlas["meta"]["pipeline_version"],
        "generated_at": atlas["meta"]["generated_at"],
        "schema_version": SCHEMA_VERSION,
        "definition_version": 2,
        "config_emerging": cfg["emerging"],
        "counts": atlas["meta"],
        "artifacts": sorted(p.name for p in outdir.iterdir()),
    }
    (outdir / "manifest.json").write_text(json.dumps(clean_json(manifest), ensure_ascii=False, indent=2,
                                                     allow_nan=False), encoding="utf-8")
    prev = state / "prev"                          # next run's novelty/lineage input — persistent
    prev.mkdir(parents=True, exist_ok=True)
    shutil.copy(work / "04_centroids.npy", prev / "centroids.npy")
    shutil.copy(work / "04_centroid_ids.json", prev / "centroid_ids.json")
    print(f"[export] → {outdir / 'atlas_data.json'} (+ csv, manifest); centroids → {prev}")
    return atlas
```

- [ ] **Step 5: Patch the web for the new statuses (minimal, P1 replaces this UI)**

In `web/src/data/atlas.ts` line 3 replace
```ts
export type TopicStatus = "EMERGING" | "HOT" | "DECLINING" | "STABLE"
```
with
```ts
export type TopicStatus = "EMERGING" | "WATCH" | "HOT" | "DECLINING" | "STABLE" | "LOW_DATA"
```
In `web/src/sections/AtlasMap.tsx` add two entries to `STATUS_STYLE` (after `EMERGING` and after `STABLE`):
```ts
  WATCH: { th: 'จับตา', en: 'Watch', color: '#A16207' },
```
```ts
  LOW_DATA: { th: 'ข้อมูลน้อย', en: 'Low data', color: '#57534E' },
```
In `web/src/sections/EmergingThemes.tsx` replace
```ts
const ORDER = ['EMERGING', 'HOT', 'DECLINING', 'STABLE'] as const
```
with
```ts
const ORDER = ['EMERGING', 'WATCH', 'HOT', 'DECLINING', 'STABLE', 'LOW_DATA'] as const
```

- [ ] **Step 6: Run tests + web build**

Run: `uv run pytest tests/test_export.py -q` → Expected: 2 passed.
Run (from `web/`): `npm ci && npm run build` → Expected: build succeeds (`dist/` written). If the build fails on code untouched by this task, record the error in the task report and do not fix unrelated code.

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/layout.py pipeline/atlas/export.py pipeline/tests/test_export.py web/src/data/atlas.ts web/src/sections/AtlasMap.tsx web/src/sections/EmergingThemes.tsx
git commit -m "feat(export): atlas_data.json 1.1 — v2 statuses, strict JSON, skill-gated forecasts, state/prev

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Orchestrator, `atlas run`, integration + end-to-end tests

**Files:**
- Modify: `pipeline/atlas/pipeline.py` (full rewrite), `pipeline/atlas/cli.py` (add `run`)
- Create: `pipeline/tests/test_pipeline_small.py`, `pipeline/tests/test_e2e_synth.py`

**Interfaces:**
- Consumes: every step function from Tasks 5–14.
- Produces: `STEPS: list[str]`; `run(cfg: dict, steps: list[str] | None = None) -> None`; CLI `atlas run [--config FILE] [--step NAME ...]`; `python -m atlas.pipeline --config FILE --steps a b` still works.

- [ ] **Step 1: Write the failing tests**

`pipeline/tests/test_pipeline_small.py` (fast — real fixtures, PCA reducer):
```python
import json

from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run


def test_full_pipeline_on_eleven_real_files(make_cfg, thaijo_dir, tmp_path):
    cfg = make_cfg(thaijo_dir)
    cfg["clustering"]["reducer"] = "pca"
    run(cfg, STEPS)
    atlas = json.loads((tmp_path / "out" / "atlas_data.json").read_text(encoding="utf-8"),
                       parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert atlas["meta"]["total_articles"] == 11 and atlas["meta"]["definition_version"] == 2
    em = read_table(tmp_path / "work" / "07_emerging.parquet")
    assert set(em["status"]) == {"LOW_DATA"}               # 11 articles can never support a trend claim
    assert (tmp_path / "state" / "prev" / "centroids.npy").exists()
```

`pipeline/tests/test_e2e_synth.py` (slow — the P0 acceptance test):
```python
import json
from pathlib import Path

import pandas as pd
import pytest

from atlas.config import load_config
from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run
from atlas.synth import TOPICS, generate

PIPELINE = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_synthetic_corpus_recovers_planted_signals(tmp_path):
    corpus = tmp_path / "synth"
    generate(corpus, n=20_000, seed=7)
    cfg = load_config(PIPELINE / "configs" / "ci.yaml")
    cfg["pipeline"].update(work_dir=str(tmp_path / "work"), output_dir=str(tmp_path / "out"),
                           state_dir=str(tmp_path / "state"))
    cfg["input"]["path"] = str(corpus)
    run(cfg, STEPS)

    em = read_table(tmp_path / "work" / "07_emerging.parquet").set_index("topic_id")
    fine = read_table(tmp_path / "work" / "04_fine_topics.parquet")
    truth = pd.read_csv(corpus / "_truth.csv")
    tt = fine.merge(truth, on="article_id")
    tt = tt[tt["fine_topic"] >= 0]

    def status_of(role):
        tid = tt[tt["role"] == role]["fine_topic"].value_counts().index[0]
        return em.loc[tid, "status"], bool(em.loc[tid, "journal_driven"])

    assert status_of("emerging") == ("EMERGING", False)
    assert status_of("confound") == ("WATCH", True)
    assert status_of("hot")[0] == "HOT"
    assert status_of("declining")[0] == "DECLINING"
    dominant = tt.groupby("fine_topic")["role"].agg(lambda x: x.value_counts().index[0])
    stable = em.loc[dominant[dominant == "stable"].index, "status"]
    assert not stable.isin(["HOT", "DECLINING", "EMERGING"]).any()
    assert len(em) <= 2 * len(TOPICS)
    purity = tt.groupby("fine_topic")["topic"].agg(lambda x: x.value_counts().iloc[0] / len(x)).mean()
    assert purity >= 0.95
    atlas = json.loads((tmp_path / "out" / "atlas_data.json").read_text(encoding="utf-8"))
    assert atlas["meta"]["definition_version"] == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_pipeline_small.py -q`
Expected: FAIL (old `pipeline.run` signature / BERTopic import).

- [ ] **Step 3: Replace `pipeline/atlas/pipeline.py`**

```python
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

STEPS = ["ingest", "preprocess", "embed", "cluster", "label", "series", "emerging", "forecast", "layout", "export"]
_FUNCS = {
    "ingest": ("atlas.ingest", "ingest"),
    "preprocess": ("atlas.preprocess", "preprocess"),
    "embed": ("atlas.embed", "embed"),
    "cluster": ("atlas.cluster", "cluster"),
    "label": ("atlas.label", "label"),
    "series": ("atlas.topics_time", "build_series"),
    "emerging": ("atlas.emerging", "emerging"),
    "forecast": ("atlas.forecast", "forecast"),
    "layout": ("atlas.layout", "layout"),
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
```

- [ ] **Step 4: Add `run` to `pipeline/atlas/cli.py`**

```python
@app.command("run")
def run_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    step: list[str] = typer.Option(None, "--step", "-s", help="run only these steps, repeatable, in order"),
) -> None:
    """Run the batch pipeline (all steps, or the given --step list)."""
    from atlas.config import load_config
    from atlas.pipeline import run

    run(load_config(config), step or None)
```

- [ ] **Step 5: Run the fast integration test, then the slow acceptance test**

Run: `uv run pytest tests/test_pipeline_small.py -q` → Expected: 1 passed.
Run: `uv run pytest -m slow -q` → Expected: 1 passed in < 10 min (prototype: ~6 min on Windows, dominated by first reads of 20K new files).

- [ ] **Step 6: Run the whole suite + lint**

Run: `uv run ruff check . && uv run pytest -q`
Expected: ruff clean; all non-slow tests pass.

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/pipeline.py pipeline/atlas/cli.py pipeline/tests/test_pipeline_small.py pipeline/tests/test_e2e_synth.py
git commit -m "feat(pipeline): orchestrator + atlas run; e2e acceptance test on synthetic corpus

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 16: Data contract v2 skeleton (pydantic → JSON Schema → TypeScript)

**Files:**
- Create: `pipeline/atlas/schema/__init__.py` (empty), `pipeline/atlas/schema/contract.py`, `pipeline/tests/test_schema.py`, `web/scripts/gen-types.mjs`, `web/src/data/contract.schema.json` (generated), `web/src/data/contract.ts` (generated)
- Modify: `pipeline/atlas/cli.py` (add `schema`), `web/package.json` (devDependency + script)

**Interfaces:**
- Produces: `SCHEMA_VERSION = "2.0.0"`; models `FileEntry, Manifest, TopicMetrics, TopicForecast, TopicLineage, Topic, TopicsFile`; `contract_json_schema() -> dict` (draft-07, `definitions` key); `write_json_schema(path) -> Path`; CLI `atlas schema [--out PATH]` (default `../web/src/data/contract.schema.json`); web `npm run gen:types` → `src/data/contract.ts`. P1's export will emit these shapes; P0 only defines and locks them.

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_schema.py`**

```python
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas.schema.contract import SCHEMA_VERSION, Topic, contract_json_schema

REPO = Path(__file__).resolve().parents[2]
SAMPLE = {
    "id": "T000123", "group": "G01", "th": "ผู้สูงอายุ", "en": "Older adults", "size": 120,
    "x": 1.0, "y": 2.0, "r": 3.0, "status": "EMERGING", "score": 88.5,
    "metrics": {"count_recent": 90, "share_recent": 0.01, "share_baseline": 0.004, "share_ratio": 2.5,
                "share_growth": 0.4, "share_growth_lo": 0.2, "share_growth_hi": 0.6, "acceleration": 0.1,
                "burst_frac": 0.67, "burst_years": [2023, 2024], "novelty": 0.7, "coherence": 0.8,
                "n_journals_R": 5, "n_orgs_R": 7, "new_journal_share": 0.0, "journal_hhi": 0.3,
                "journal_driven": False},
}


def test_schema_lists_all_statuses():
    status = contract_json_schema()["definitions"]["Topic"]["properties"]["status"]
    assert set(status["enum"]) == {"EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA"}


def test_sample_topic_validates_and_bad_id_fails():
    assert Topic.model_validate(SAMPLE).lineage.event == "new"
    with pytest.raises(ValidationError):
        Topic.model_validate({**SAMPLE, "id": "t1"})
    with pytest.raises(ValidationError):
        Topic.model_validate({**SAMPLE, "status": "RISING"})


def test_committed_schema_is_up_to_date():
    committed = json.loads((REPO / "web" / "src" / "data" / "contract.schema.json").read_text(encoding="utf-8"))
    assert committed == contract_json_schema(), "run: uv run atlas schema && (cd ../web && npm run gen:types)"
    assert SCHEMA_VERSION == "2.0.0"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_schema.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.schema'`

- [ ] **Step 3: Implement `pipeline/atlas/schema/contract.py`**

```python
"""Data contract v2 skeleton — the JSON that web v2 (P1) reads.

Pydantic models are the source of truth → JSON Schema (`atlas schema`) → TypeScript
(`npm run gen:types` in web/). CI fails when either generated file drifts.
P0 defines and locks the shapes; P1's export writes them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "2.0.0"
Status = Literal["EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileEntry(_Model):
    path: str
    bytes: int
    sha256: str


class Manifest(_Model):
    schema_version: str = SCHEMA_VERSION
    release: str = Field(description="release tag, e.g. 2026Q4")
    generated_at: str
    pipeline_version: str
    config_hash: str
    definition_version: int = 2
    embedding_model: str
    taxonomy_version: str | None = None
    modules: list[str] = Field(default_factory=list)
    files: list[FileEntry] = Field(default_factory=list)
    previous_release: str | None = None


class TopicMetrics(_Model):
    count_recent: int
    share_recent: float
    share_baseline: float
    share_ratio: float
    share_growth: float | None
    share_growth_lo: float | None
    share_growth_hi: float | None
    acceleration: float
    burst_frac: float
    burst_years: list[int] = Field(default_factory=list)
    novelty: float
    coherence: float | None = None
    n_journals_R: int
    n_orgs_R: int
    new_journal_share: float
    journal_hhi: float
    journal_driven: bool


class TopicForecast(_Model):
    model: str
    mase: float | None
    skill_vs_naive: float
    show: bool
    years: list[int]
    mean: list[float]
    lo80: list[float]
    hi80: list[float]
    lo95: list[float]
    hi95: list[float]


class TopicLineage(_Model):
    born: str | None = None
    event: Literal["new", "continue", "split", "merge"] = "new"
    parents: list[str] = Field(default_factory=list)


class Topic(_Model):
    id: str = Field(pattern=r"^T\d{6}$")
    group: str
    th: str
    en: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    size: int
    x: float
    y: float
    r: float
    status: Status
    score: float
    metrics: TopicMetrics
    forecast: TopicForecast | None = None
    lineage: TopicLineage = Field(default_factory=TopicLineage)
    sdg: list[int] = Field(default_factory=list)


class TopicsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    topics: list[Topic]


def contract_json_schema() -> dict:
    from pydantic.json_schema import models_json_schema

    _, top = models_json_schema([(Manifest, "validation"), (TopicsFile, "validation")],
                                ref_template="#/definitions/{model}")
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "AtlasContract",
        "type": "object",
        "properties": {"manifest": {"$ref": "#/definitions/Manifest"},
                       "topics": {"$ref": "#/definitions/TopicsFile"}},
        "required": ["manifest", "topics"],
        "additionalProperties": False,
        "definitions": top["$defs"],
    }


def write_json_schema(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(contract_json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                 encoding="utf-8")
    return p
```

- [ ] **Step 4: Add the `schema` command to `pipeline/atlas/cli.py`**

```python
@app.command()
def schema(
    out: Path = typer.Option(Path("../web/src/data/contract.schema.json"), help="where to write the JSON Schema"),
) -> None:
    """Write the data-contract v2 JSON Schema (then run `npm run gen:types` in web/)."""
    from atlas.schema.contract import write_json_schema

    typer.echo(f"wrote {write_json_schema(out)}")
```

- [ ] **Step 5: Web type generation**

Create `web/scripts/gen-types.mjs`:
```js
// Generate TypeScript types for the data contract from the pipeline's JSON Schema.
// Source of truth: pipeline/atlas/schema/contract.py → `uv run atlas schema` → this script.
import { writeFileSync } from 'node:fs'
import { compileFromFile } from 'json-schema-to-typescript'

const ts = await compileFromFile('src/data/contract.schema.json', {
  bannerComment: '/* Generated by `npm run gen:types` from pipeline/atlas/schema/contract.py — do not edit. */',
  additionalProperties: false,
})
writeFileSync('src/data/contract.ts', ts)
```
In `web/package.json` add `"gen:types": "node scripts/gen-types.mjs"` to `scripts`, then run `npm install --save-dev json-schema-to-typescript` (records the current version in `package.json`/`package-lock.json`).

- [ ] **Step 6: Generate both files and run tests**

```bash
cd pipeline && uv run atlas schema && cd ../web && npm run gen:types && cd ../pipeline
uv run pytest tests/test_schema.py -q
```
Expected: `wrote ../web/src/data/contract.schema.json`; `web/src/data/contract.ts` contains `export interface Topic` and a `status` union of the six statuses; 3 tests passed.

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/schema pipeline/atlas/cli.py pipeline/tests/test_schema.py web/scripts/gen-types.mjs web/package.json web/package-lock.json web/src/data/contract.schema.json web/src/data/contract.ts
git commit -m "feat(contract): data contract v2 skeleton — pydantic → JSON Schema → TypeScript

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: CI workflow + operational scripts

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `scripts/quarterly_run.sh`, `scripts/import_atlas.sh`, `pipeline/scripts/run_all.sh`

**Interfaces:**
- Produces: GitHub Actions jobs `pipeline` (ruff, pytest, schema drift), `e2e` (pytest -m slow), `web` (types drift, build). Before writing the workflow, confirm the current major versions of `actions/checkout`, `astral-sh/setup-uv` and `actions/setup-node` (context7 or the actions' READMEs) and use those; the versions below are the minimum known-good.

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI
on:
  push:
  pull_request:

jobs:
  pipeline:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: pipeline
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.12"
          enable-cache: true
      - run: uv sync --locked
      - run: uv run ruff check .
      - run: uv run pytest -q
      - name: data-contract JSON Schema is up to date
        run: uv run atlas schema --out ../web/src/data/contract.schema.json && git diff --exit-code -- ../web/src/data/contract.schema.json

  e2e:
    needs: pipeline
    runs-on: ubuntu-latest
    timeout-minutes: 30
    defaults:
      run:
        working-directory: pipeline
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.12"
          enable-cache: true
      - run: uv sync --locked
      - name: synthetic corpus recovers planted EMERGING / WATCH / HOT / DECLINING
        run: uv run pytest -m slow -q

  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: web/package-lock.json
      - run: npm ci
      - name: TypeScript contract types are up to date
        run: npm run gen:types && git diff --exit-code -- src/data/contract.ts
      - run: npm run build
```

- [ ] **Step 2: Replace `scripts/quarterly_run.sh`**

```bash
#!/usr/bin/env bash
# quarterly_run.sh — รอบรันรายไตรมาส: profile คลัง → pipeline ทั้งสาย
#   bash scripts/quarterly_run.sh [pipeline/config.yaml]
# อ่าน input.path จาก config (โฟลเดอร์ .md) — ผล profile อยู่ที่ logs/profile_YYYYMMDD.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$(realpath "${1:-$ROOT/pipeline/config.yaml}")"
STAMP="$(date +%Y%m%d)"
mkdir -p "$ROOT/logs"
cd "$ROOT/pipeline"
CORPUS="$(uv run python -c "from atlas.config import load_config; print(load_config(r'$CONFIG')['input']['path'])")"
uv run atlas profile "$CORPUS" --out "$ROOT/logs/profile_$STAMP.json" --md "$ROOT/logs/profile_$STAMP.md" --workers 4 > /dev/null
echo "[quarterly] profile → logs/profile_$STAMP.md  (ตรวจปี/วารสารที่อัปโหลดย้อนหลังก่อนเชื่อผล)"
uv run atlas run --config "$CONFIG"
echo "[quarterly] เสร็จ → pipeline/output/  ต่อด้วย: bash scripts/import_atlas.sh"
```

- [ ] **Step 3: Update `scripts/import_atlas.sh`** — replace the validation heredoc invocation `python3 - "$SRC" <<'PY'` with `(cd "$ROOT/pipeline" && uv run python - "$SRC") <<'PY'`, and inside the Python block replace the `print(...)` line with:
```python
print(f"[import] JSON OK — schema {d['meta'].get('schema_version', '1.0')}, definition v{d['meta'].get('definition_version', 1)}, "
      f"{g} groups, {n} nodes, {d['meta'].get('total_articles', 0):,} articles, "
      f"data through {d['meta'].get('last_complete_year', '?')}")
```

- [ ] **Step 4: Replace `pipeline/scripts/run_all.sh`**

```bash
#!/usr/bin/env bash
# run_all.sh — รัน pipeline ทั้งสาย (เทียบเท่า uv run atlas run)
#   bash scripts/run_all.sh [config.yaml]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
uv run atlas run --config "${1:-config.yaml}"
```

- [ ] **Step 5: Verify locally**

Run: `bash -n scripts/quarterly_run.sh scripts/import_atlas.sh pipeline/scripts/run_all.sh` (syntax check) → no output.
Run (from `pipeline/`): `uv run ruff check . && uv run pytest -q` → all green.

- [ ] **Step 6: Commit** (do NOT push — pushing/creating the GitHub repo needs the user's go-ahead)

```bash
git add .github/workflows/ci.yml scripts/quarterly_run.sh scripts/import_atlas.sh pipeline/scripts/run_all.sh
git commit -m "ci: pipeline tests, synthetic e2e, schema/type drift and web build

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 18: Documentation sync (ARCHITECTURE, DATA_SPEC, OPERATIONS, READMEs, ROADMAP, CLAUDE.md)

**Files:**
- Modify: `docs/ARCHITECTURE.md`, `docs/DATA_SPEC.md`, `docs/OPERATIONS.md`, `docs/ROADMAP.md`, `README.md`, `pipeline/README.md`, `CLAUDE.md`

**Interfaces:** none (docs only). Every statement must match the code from Tasks 1–17; grep for stale terms when done.

- [ ] **Step 1: `docs/ARCHITECTURE.md` — replace §2 "การไหลของข้อมูล" code block with:**

```
corpus/*.md (ThaiJO scrape)            ← ตรวจก่อนด้วย: atlas profile
        │
        ▼
[ingest]     parse .md (ซ่อม PUA/สระอำ, แยก TH/EN, ปี: Published→DOI→median issue, ID จาก URL), dedup
        │  → work/01_articles · 01_authors (+org_key) · 01_references
        ▼
[preprocess] doc_text = title + keywords + abstract (≤ 6000 ตัวอักษร)          → work/02_docs
        ▼
[embed]      api | local (BGE-M3, 1024 tokens) | lite (TF-IDF+SVD สำหรับ CI)
             เวกเตอร์ api/local เก็บถาวรใน state/embeddings (resume + incremental)  → work/03_embeddings.npy
        ▼
[cluster]    [PCA] → UMAP → HDBSCAN → merge cluster ซ้ำ (cos ≥ 0.8) → outlier เข้าเฉพาะที่ใกล้พอ
             → กลุ่มใหญ่ (agglomerative) → c-TF-IDF (pythainlp) + author keywords + coherence
        │  → work/04_fine_topics · 04_coarse_topics · 04_topic_info · 04_centroids.npy · 04_centroid_ids.json
        ▼
[label]      LLM (cache = hash ของ prompt ใน state/label_cache) หรือ off (ชื่อจาก author keywords)  → work/05_labels
        ▼
[series]     topic × ปี + ตารางวารสาร/สถาบัน + backfill guard
        │  → work/06_series · 06_topic_journal_year · 06_topic_org_year · 06_journal_first_year · 06_meta.json
        ▼
[emerging]   Emerging v2 (docs/EMERGING_SPEC.md)                                   → work/07_emerging
        ▼
[forecast]   naive / linear / Poisson + backtest + skill gating                    → work/08_forecasts
        ▼
[layout]     UMAP 2D บน centroid + edges                                           → work/09_layout · 09_edges
        ▼
[export]     output/atlas_data.json (schema 1.1) + CSVs + manifest; centroids → state/prev/
        ▼
เว็บ: fetch('/data/atlas_data.json') → loader.normalize() → render
```
Also in §1 add principle 6: "**state แยกจาก work** — `work_dir` ลบได้เสมอ; `state_dir` เก็บสิ่งที่ต้องอยู่ข้ามรอบ (embedding store, label cache, centroids รอบก่อน)". In §6 replace the "emerging score" bullet with "สถานะใช้ช่วงเชื่อมั่น (v2) — score ยังเป็น percentile ภายในรอบ เทียบข้ามรอบไม่ได้".

- [ ] **Step 2: `docs/DATA_SPEC.md`** — replace §1 with the ThaiJO Markdown input spec and §2 with the new checkpoint table:

```markdown
## 1. Input: ThaiJO Markdown (ค่าดีฟอลต์ `input.format: thaijo_md`)
หนึ่งไฟล์ .md ต่อบทความ (ตัวอย่างจริงใน `pipeline/tests/fixtures/thaijo_md/`):
| ส่วน | รูปแบบ | ที่ pipeline ทำ |
|---|---|---|
| `# ชื่อเรื่อง` | ไทย, อังกฤษ, `TH [EN]` หรือ `EN (TH)` | แยก title_th / title_en (วงเล็บสั้นอย่าง `(TQA)` ไม่ถูกแยก) |
| `**Journal:**` | OJS path เช่น `BECJournal` | journal_name (ชื่อเต็ม/ISSN มาจาก registry ใน P2) |
| `**Published:**` | YYYY-MM-DD; `1970-01-01` = วันที่หาย | ปี: Published → ปีใน DOI → median ของ issue → ว่าง |
| `**Article URL:**` | `https://so02.tci-thaijo.org/index.php/<journal>/article/view/<id>` | article_id = `so02:<journal>:<id>` (ไม่มี URL → `file:<sha1 ชื่อไฟล์>`) |
| `**Authors:**` | `- ชื่อ [EN name] (สังกัดไทย (สังกัด EN))` + คำนำหน้าวิชาการ | ชื่อ, สังกัด TH/EN, role, is_student, org_key |
| `**Keywords:**` | ไทย+อังกฤษคั่น `,` | keywords_th / keywords_en |
| `## Abstract` | บทคัดย่อไทย␣␣␣ชื่ออังกฤษ␣␣␣บทคัดย่ออังกฤษ␣␣␣DOI: … | แยกด้วยช่องว่าง ≥2 + สัดส่วนอักษร; ดึง DOI; ตัด label "Abstract" |
| `## References` | bullet ที่ถูกตัดบรรทัด | ต่อบรรทัด, ปี พ.ศ.→ค.ศ., ตัด self-citation และส่วน "Translated Thai References" ออกจากการนับ |
ปัญหาข้อความที่ซ่อมให้อัตโนมัติ: อักษรไทย Private-Use (U+F700–F71A) จาก PDF, `ํา`→`ำ`, ช่องว่างก่อนสระบน/ล่าง · flag ใน `text_quality`: `thai_pua_repaired`, `tone_marks_missing`, `stat_symbols_missing`
ตาราง (`input.format: table`, csv/json/jsonl/parquet) ยังรองรับผ่าน `input.columns`

## 2. Checkpoints (work_dir — ลบได้) และ state (state_dir — ห้ามลบ)
| ไฟล์ | step | คอลัมน์สำคัญ |
|---|---|---|
| `01_articles` | ingest | article_id, journal_name, year, year_source, title_th/en, abstract_th/en, keywords_th/en, authors, affiliations, n_authors, n_student_authors, n_references, has_references, self_citation_only, text_quality |
| `01_authors` | ingest | article_id, position, name, name_en, affiliation_th/en, role, is_student, org_key |
| `01_references` | ingest | article_id, position, text, year, lang, translated, self_citation |
| `02_docs` | preprocess | 01_articles + doc_text |
| `03_embeddings.npy`, `03_meta.json` | embed | matrix (แถวตรงกับ 02_docs), model_id |
| `04_fine_topics`, `04_coarse_topics` | cluster | article_id → topic (−1 = ยังไม่จัดหมวด) |
| `04_topic_info` | cluster | topic_id, size, top_terms, top_keywords, coarse_topic, coherence |
| `04_centroids.npy`, `04_centroid_ids.json` | cluster | centroid ต่อหัวข้อ |
| `05_labels` | label | topic_id, name_th, name_en, description, keywords, cache_key |
| `06_series` | series | topic_id, year, count, count_with_org, corpus_total, share |
| `06_topic_journal_year`, `06_topic_org_year`, `06_journal_first_year`, `06_meta.json` | series | ใช้คำนวณความกว้าง + ปีสมบูรณ์ล่าสุด |
| `07_emerging` | emerging | ดู docs/EMERGING_SPEC.md §3 + status, journal_driven, emerging_score, definition_version |
| `08_forecasts` | forecast | model, backtest_mae/mape, mase, skill_vs_naive, show, hist/fc (JSON) |
| `09_layout`, `09_edges` | layout | id, kind, x, y, r, parent · s, t, w |
| `state/embeddings/<model>/` | embed | index + shards (ถาวร) |
| `state/label_cache` | label | cache_key → ชื่อหัวข้อ |
| `state/prev/centroids.npy` | export | centroid รอบนี้ สำหรับรอบหน้า |
```
In §3 (atlas_data.json) add a "schema 1.1 additions" list (the fields from Task 14 Interfaces) and note `forecast` is null unless skill-gated, `forecast_uncertain` explains why. Add §6: "Data contract v2 (P1): `pipeline/atlas/schema/contract.py` → `web/src/data/contract.schema.json` → `web/src/data/contract.ts`".

- [ ] **Step 3: `docs/OPERATIONS.md`** — replace the §1 runbook commands with:

```bash
cd pipeline
uv sync --extra local                      # หรือ --extra api
uv run atlas profile /path/to/corpus --md ../logs/profile.md   # ขั้น 1: อ่านรายงานก่อนเสมอ
uv run atlas run --config config.yaml      # ขั้น 2: ทั้งสาย (หรือ bash ../scripts/quarterly_run.sh)
bash ../scripts/import_atlas.sh            # ขั้น 3: นำเข้าเว็บ + build
```
and add troubleshooting rows: "หัวข้อเกือบทั้งหมดเป็น LOW_DATA → corpus เล็ก/ช่วงปีสั้น หรือ `min_articles_recent` สูงไป" · "หัวข้อขึ้น WATCH เยอะ → ดู profile §วารสารที่อัปโหลดย้อนหลัง; เป็นสัญญาณ journal-entry bias" · "`provider: off` ใน YAML ต้องใส่เครื่องหมายคำพูด" · "Windows แสดงภาษาไทยเพี้ยนใน console → ใช้ `uv run atlas …` (ตั้ง UTF-8 ให้แล้ว)". Replace every `python -m atlas.pipeline` and `validate_input.py` mention with the `atlas` CLI.

- [ ] **Step 4: `README.md` and `pipeline/README.md`** — replace Quick start blocks with the Step 3 commands (+ `uv run pytest -q`), replace the v1 emerging table with a 6-row v2 status table pointing to `docs/EMERGING_SPEC.md`, remove the BERTopic/hdbscan install notes, and state that real data never goes into git.

- [ ] **Step 5: `docs/ROADMAP.md`** — add at the top: "แผนหลักปัจจุบันอยู่ที่ `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md` (เฟส P0–P4)". Mark as done in the baseline table: ThaiJO ingest, Emerging v2, skill-gated forecast, synthetic e2e, CI.

- [ ] **Step 6: `CLAUDE.md`** — update:
  - §2 tree: add `pipeline/atlas/sources/`, `pipeline/atlas/schema/`, `pipeline/configs/ci.yaml`, `pipeline/state/` (git-ignored), `docs/superpowers/` (specs + plans).
  - §4 commands: replace the pipeline block with
    ```bash
    cd pipeline
    uv sync                                    # + --extra api / --extra local
    cp config.example.yaml config.yaml         # แก้ input.path → โฟลเดอร์ .md
    uv run atlas profile ../corpus             # ตรวจคุณภาพคลังก่อนเสมอ
    uv run atlas run --config config.yaml      # ทั้งสาย
    uv run atlas run -c config.yaml -s emerging -s forecast -s export
    uv run atlas synth --out .ci/synth --n 20000
    uv run pytest -q && uv run pytest -m slow -q
    ```
  - §5: atlas_data.json is schema 1.1 (list new fields); v2 contract lives in `atlas/schema/contract.py` and must be regenerated (`atlas schema` + `npm run gen:types`) together.
  - §6 Pipeline DO/DON'T — add: persistent data only in `state_dir`; statuses are the six v2 values and `definition_version` must bump on any definition change; write Thai code points as `\N{THAI CHARACTER …}`; pandas 3 — no `dtype == object`; quote `"off"` in YAML.
  - §7 Thai: add "ข้อความไทยจาก PDF อาจมีอักษร Private-Use (U+F700–F71A) — `atlas.thai.clean_text` ซ่อมให้; ห้ามลบทิ้ง".

- [ ] **Step 7: Stale-term sweep**

Run (from repo root):
```bash
grep -rn "validate_input\|python -m atlas.pipeline\|BERTopic\|bertopic\|burst_intensity\|1.5%\|04_topics.parquet\|06_topic_year" --include=*.md . | grep -v "docs/superpowers/"
```
Expected: no hits except intentional historical mentions in `docs/EMERGING_SPEC.md` (v1 appendix). Fix any other hit.

- [ ] **Step 8: Commit**

```bash
git add docs README.md pipeline/README.md CLAUDE.md
git commit -m "docs: sync architecture, data spec, operations, READMEs and CLAUDE.md with P0

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## P0 Definition of Done

- `uv run ruff check .` and `uv run pytest -q` pass on Windows and in CI; `uv run pytest -m slow -q` passes (planted EMERGING / WATCH / HOT / DECLINING recovered, no false HOT/DECLINING on stable topics, ≤ 2× planted topics, purity ≥ 0.95).
- `uv run atlas profile ../corpus` prints a report for the 11 real files; `uv run atlas run` on them finishes with every topic `LOW_DATA` (honest: 11 articles cannot support trend claims).
- `web/` builds with the v1.1 JSON (new statuses render); contract schema/types are generated and drift-checked.
- Docs and CLAUDE.md describe what the code does; nothing pushed to GitHub without the user's go-ahead.

