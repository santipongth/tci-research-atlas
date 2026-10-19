# P3 — Executives release (institutions · provinces · SDG & Thai plans · Thailand vs the world · gaps) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the executives' release of TCI Research Atlas v2: canonical institutions (curated alias table + optional local ROR dump → institution, type, province, country), the collaboration network between institutions and with other countries, research output per province (E6, E7), SDG 17 + BCG + แผนด้าน ววน. + หมุดหมายแผนฯ 13 coverage and gaps (E8), the OpenAlex "Thailand vs the world" benchmark (E9), the gap finder (R5), concentration risk (E10), the collaboration finder (R6) and institution links from topic pages (D6), the full KPI set and the executive brief additions — as contract **2.2.0** files and six lazy pages `/institutions`, `/institutions/:id`, `/regions`, `/sdg`, `/global`, `/gaps`, with the navigation grouped into "สำหรับผู้บริหาร / บรรณาธิการ / นักวิจัย".

**Architecture:** Same batch → checkpoint → JSON design as P2. Four new pipeline steps run after `match`: `institutions` (15_*), `sdg` (16_*), `benchmark` (17_*), `gaps` (18_*). Pure helpers live in small modules (`places`, `institutions_ref`, `countries` extended); `export_exec.py` turns the checkpoints into contract 2.2 models that `export_v2.build_release` adds to the release (each module optional, listed in `manifest.modules`; a module skipped for a reason is named in `manifest.skipped_modules`). The web reuses P2's lazy `ModuleFile`/`useReleaseFile`; the province map is an SVG of 77 committed paths generated once from Natural Earth (public domain) — no runtime geo library.

**Tech Stack:** Python 3.12 via `uv` — pandas 3, numpy, scikit-learn, pyyaml, pydantic v2, pytest, ruff (no new dependency; `zipfile`/`csv` from the standard library). Web — the P2 pins unchanged: React 19.3.1, react-router 7.18.4, Vite 7.3.7 + vite-plugin-singlefile 2.3.4, vitest 4.1.12, Playwright 1.64.1 + axe 4.14.0, TypeScript 5.9.3 (no new dependency).

**Spec:** `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md` — P3 section, catalog E1, E4, E6–E10, D6, R1 (institutions), R5, R6, "Institutions", "SDG", Data contract v2 (`institutions.json`, `sdg.json`, `global.json`, `gaps.json`; pages self-hide by `manifest.modules`). Builds on `docs/superpowers/plans/2026-10-19-p2-editors.md` (contract 2.1, `ModuleFile`, `useReleaseFile`, `MODULE_FILES`, lazy routes, `check-bundle.mjs`, `tests/p2_work.py`).

## Prerequisites (stop if any is false)

- P2 is finished on `p2-editors` (its Task 17 committed) and merged or branched from: `git log --oneline -1` shows the P2 docs commit; `web/src/App.tsx` has `const MatchPage = lazy(() => import('./pages/MatchPage'))`.
- From `pipeline/`: `uv run pytest -q` is green; from `web/`: `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e` is green.
- Work on a new branch `p3-executives`. Never `git push`, create remotes or run `gh` without the owner's go-ahead.

## Global Constraints

Pipeline (from P1a/P2, still binding):
- Run from `pipeline/` with `uv run …`; pandas 3 safe (never test `dtype == object`; text via `.fillna("").astype(str)`; boolean masks `.fillna(False).astype(bool)`); tables only through `atlas.io_utils.read_table` / `write_table`; strict JSON (no NaN/Infinity); persistent data only in `state_dir`; `uv run ruff check --fix .` before each commit; every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **No hard-coded thresholds:** every result-changing number is a key in `AtlasConfig` **and** documented in `config.example.yaml` (`test_example_yaml_is_valid_and_documents_every_key`). New sections: `institutions`, `risk`, `gaps`, `sdg`, `benchmark` (Task 1).
- **Emerging definition stays at `definition_version` 3.** No task touches `emerging.py`, `docs/EMERGING_SPEC.md` or a status rule.
- **Tests never touch the network** (`tests/conftest.py` blocks non-loopback sockets and sets `ATLAS_OFFLINE=1`). OpenAlex is faked with a `fetch(path, params) -> dict` callable; the ROR dump is a tiny file written by the test.
- **Thai text in code:** literal UTF-8 words are fine; single Thai code points as `\N{THAI CHARACTER …}` / `chr()`; never a backslash-u escape in Python, TypeScript or JavaScript.
- **Contract:** every published file is a pydantic model in `atlas/schema/contract.py`; after changing a model run `uv run atlas schema` (from `pipeline/`) and `npm run gen:types` (from `web/`) and commit both generated files. Colours are token keys, never hex.

Web (from P1b/P1c/P2, still binding):
- Gate for every web task (in `web/`): `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e`. Pins exact, no new dependency.
- Types only from the generated `src/data/contract.ts` through `src/data/types.ts` (containers by name, nested types by indexed access; defaulted fields are optional — read them with `??`).
- HashRouter only; relative `${import.meta.env.BASE_URL}data/…` URLs; no third-party request at run time.
- DESIGN.md wins: colours only through CSS custom properties in `src/styles/tokens.css`; no hex in `.tsx`; no dynamic Tailwind classes; dynamic sizes via `style={{ … }}`.
- Status = glyph + colour + text; Thai typography (no italics, no letter-spacing on Thai, line-height ≥ 1.5); every string in `src/strings/*.ts` (th + en, same placeholders, a key defined once).
- Self-hiding sections; a page whose module is absent shows its `h1` and why (`ModuleFile`), never a white page, never `role="alert"`.
- WCAG 2.2 AA: axe serious/critical = 0 in light and dark on every route; targets ≥ 24 px (nav 44 px); sortable headers carry `aria-sort`; information never by colour alone; every chart has a table view.
- Lint rules that shape code: a `.tsx` exports components only; no synchronous `setState` in an effect body; no ref access during render; copy before `.sort()`.
- **UI tasks: the implementer invokes the `impeccable` skill (craft mode) before writing UI and follows DESIGN.md; the choropleth follows the `dataviz` skill (sequential palette, legend, table view).**

New in P3:
- **Privacy (PDPA):** author rows are read inside `institutions_ref` / `institutions` for affiliations only — never a name, never a per-author row. Only institutions with ≥ `institutions.min_articles` articles in the window get a row in `institutions.json`, a page and a place in the network (pairs need both ends published and ≥ `institutions.network_min_articles` co-authored articles). Topic pages keep naming their top institutions as P1 does; only published ones get a link.
- **Offline first:** the ROR dump and the population table are local files; OpenAlex is called only by the `benchmark` step through P1's `HttpFetcher` (request cache in `state_dir/openalex`, `ATLAS_OFFLINE=1` honoured). Every failure is a skip with a reason, never a crash.
- **Curated data is not committed:** `pipeline/registry/institutions_aliases.csv` and `pipeline/registry/province_population.csv` stay git-ignored (`pipeline/registry/*` with `!*.example.csv` — already in `.gitignore`); reference data that is public and not about people IS committed: `pipeline/atlas/data/th_provinces.csv` (77 ISO 3166-2:TH codes and names), `pipeline/atlas/data/frameworks.yaml` (goal names + keywords), `web/src/geo/thProvinces.ts` (Natural Earth outlines).
- **Bundle:** the six pages are `React.lazy` routes; the province outlines (< 300 KB) live in the `/regions` chunk only; `check:bundle` keeps the entry chunk ≤ 180 KB gzip.

## Rulings this plan takes (decided; one line each)

1. **Contract 2.2.0, additive:** new files `institutions.json`, `institutions/<id>.json`, `regions.json`, `sdg.json`, `global.json`, `gaps.json`; `Kpis` gains optional `pct_international`, `pct_multi_institution`, `provinces`; `Overview.executive`; `Manifest.skipped_modules`; `CountItem.id` now also links institutions.
2. **Institution identity order:** alias table → foreign country named → ROR name (labels, display name, aliases; never acronyms) → the organisation as written (P1 `org_key`); the published id is the alias `inst_id`, `ror-<ROR id>` or `o` + 10 hex of sha1(org_key) — stable across releases.
3. **Alias matching:** folded text (`norm_key`) equals the `org_key` or occurs in the folded affiliation, leftmost then longest; aliases shorter than `institutions.alias_min_chars` (4) are refused, so Rajabhat/Rajamangala campuses and abbreviations ("มรภ.เชียงราย", "มทร.ล้านนา") are curated rows, not guesses.
4. **Province** = the institution's alias/ROR province (institution level, headquarters), else a province named in the affiliation (Thai: after จังหวัด/จ./ราชภัฏ/มหาวิทยาลัย/โรงพยาบาล, or กรุงเทพ; English: whole word) — recorded as `source: name`; an article counts once in every province among its authors (full counting).
5. **Small-unit guard:** institutions below `institutions.min_articles` (5) are counted in every total but never listed, linked or paired.
6. **Province map:** Natural Earth 1:10m admin-1 v5.1.2 (public domain, https://www.naturalearthdata.com/about/terms-of-use/), filtered to the 77 provinces, projected and simplified once by `web/scripts/make-province-map.mjs` into `web/src/geo/thProvinces.ts` (asserted < 300 KB); SVG choropleth (5 quantile classes of a new sequential token ramp) with a table view.
7. **Per capita** only when the optional `registry/province_population.csv` (code, population, year — e.g. DOPA civil registration) covers the province; otherwise the column shows "–".
8. **Network as tables:** top institution pairs, partner countries, per-institution partners; a node-link drawing is deferred to P4 (ROADMAP).
9. **SDG/Thai frameworks:** packaged `atlas/data/frameworks.yaml` (SDG 17 · BCG 3 · แผนด้าน ววน. 2566–2570 4 platforms · หมุดหมายแผนฯ 13 13 milestones, editable keywords); `sdg.method: auto` = cosine of topic centroids to embedded goal texts when the provider is `api`/`local` and centroids exist, else lexical (share of a topic's articles whose title/keywords name the goal ≥ 15 %); top 3 goals per topic per framework. LLM confirmation is **not built** in P3 (no dead config key) — ROADMAP.
10. **Benchmark:** 16 OpenAlex `group_by=primary_topic.subfield.id` requests (4 domains × recent/baseline × world/country) through P1's `HttpFetcher`; world growth = the subfield's share of world output recent ÷ baseline; activity index = share of Thai output ÷ share of world output; opportunity = world ≥ 1,000 works, growth ≥ 1.2, activity index ≤ 0.5. Skipped (reason in `manifest.skipped_modules.global`) when disabled, offline or the map is not anchored to OpenAlex subfields. Config section is `benchmark` (`global` is a Python keyword); the published file stays `global.json`.
11. **Gaps (R5) + risk (E10)** in one `gaps.json`: world opportunities with their topics; EMERGING/WATCH topics with ≤ 5 institutions in R; neighbouring topics (map edge ≥ 0.6) whose institution sets overlap ≤ 0.1 (Jaccard); concentration per topic and per field, by institution and by journal (HHI and top share over articles in R; flag at top share ≥ 0.5 or HHI ≥ 0.25; units with ≥ 30 articles).
12. **Collaboration finder (R6):** on each institution page, the published institutions with the most similar topic mix (cosine ≥ 0.3) that share no article in the window, with the shared topics; D6 = topic pages link their institutions.
13. **Executive brief additions** are deterministic template bullets (`overview.executive`) built at export from the P3 modules — no LLM, every number from the files; YoY KPIs are not added (ROADMAP).
14. **Navigation:** Overview · Topic map · Topic status, then three disclosure menus — สำหรับผู้บริหาร (Institutions, Provinces, SDGs and plans, Thailand vs the world, What changed, Executive brief), สำหรับบรรณาธิการ (Journals, Methods), สำหรับนักวิจัย (Research gaps, Match an abstract, Compare) — then Open data · About. Every page stays two clicks away; no ARIA menu role (disclosure pattern).
15. **Tests (owner: minimal):** one focused test file per new pipeline module, one contract test, one appended `test_release` test (real files: valid + no person name), one assertion in the slow two-quarter e2e; web: one vitest file for the new helpers and one e2e check per new route (the existing loop adds example/empty/axe runs).

## Review Focus

1. **"Bangkok University" / "มหาวิทยาลัยกรุงเทพ" style names** (a province word inside an institution name) → the alias row wins over the province guess; a guessed province is labelled `source: name` — Task 1 (`test_alias_table_merges_campuses_spellings_and_abbreviations`).
2. **Offline run, OpenAlex down, or a map not anchored to OpenAlex** → no `global.json`, `manifest.skipped_modules.global` gives the reason, `/global` shows its h1 and the reason — Task 4 (`test_offline_or_unanchored_runs_skip_with_a_reason`), Task 7 (`ModuleFile`), empty-release e2e.
3. **A pre-P3 or empty release** → `/institutions`, `/regions`, `/sdg`, `/global`, `/gaps` show h1 + "not in this release", no alert, no console error — Task 7 fixtures (empty release has none), the e2e empty loop.
4. **Person names or tiny institutions leaking** → no 15_* table has a person column; unpublished institutions never appear in `institutions.json`, pairs or links; no author name in any published file of the real 11-file release — Task 2 (`test_no_person_column_and_small_units_stay_internal`), Task 6 (`test_executive_modules_are_published_valid_and_name_no_person`).
5. **Provinces without data or without an outline** → "no data" fill + legend entry; the table still lists every province with data; the map has a text alternative — Task 9 e2e (`regions` check counts 77 outlines and the table rows).

## Verification status of this plan (2026-10-19)

A cheap mechanical check, on a scratch copy only (the repo was not touched): every code block of Tasks 1–12 was applied by script to `p2-editors` as it stood (pipeline at `f0b38cf` + P2's uncommitted fixes; web with P2 Tasks 11–16 in the working tree). Pipeline: `pytest -q` **734 passed, 2 skipped** (incl. the 11-real-file two-release export with every P3 module, validate clean, no person name), `ruff check .` clean. Web: `eslint .` clean, `tsc -b` clean, vitest **121 passed** (fixtures validate against the 2.2 schema), build OK, `check:bundle` entry **175.9 KB gzip** (budget 180 — P3 adds ≈ 6 KB of strings and the grouped nav to the entry; the six pages are lazy chunks of 1–4 KB, `/regions` ≈ 17 KB with the outlines), Playwright **51 passed** (every route × example/empty, axe light + dark, 360 px, the nav test). `make-province-map.mjs` was run on the real Natural Earth v5.1.2 file: 77 provinces, 42 KB. The slow synthetic two-quarter e2e (with P3's one added assertion) **passed** in 6 min 19 s. The fixes the check found are already in the plan (a rounding tolerance in a test, the file list pinned by `test_contract_v2`, two e2e counts that grow with the new KPIs).

---
## File Structure

```
pipeline/
├── config.example.yaml / atlas/config.py   MOD  institutions · risk · gaps · sdg · benchmark sections                 T1
├── registry/institutions_aliases.example.csv  NEW  curated alias table columns + Rajabhat/Rajamangala examples        T1
├── registry/province_population.example.csv   NEW  code,population,year (real file git-ignored)                       T1
├── atlas/
│   ├── data/th_provinces.csv     NEW  77 provinces: ISO 3166-2:TH code, Thai/English names, other spellings           T1
│   ├── data/frameworks.yaml      NEW  SDG 17 · BCG · แผนด้าน ววน. 2566–2570 · หมุดหมายแผนฯ 13 (names + keywords)       T3
│   ├── places.py                 NEW  provinces(), region_of(), province_finder().find(th, en)                         T1
│   ├── countries.py              MOD  COUNTRY_NAMES, country_of(th, en) → ISO 3166-1 alpha-2                           T1
│   ├── institutions_ref.py       NEW  Institution, inst_code, type_from_name, load_aliases, load_ror, Resolver           T1
│   ├── institutions.py           NEW  step `institutions` → work/15_*                                                 T2
│   ├── sdg.py                    NEW  load_frameworks, goal_patterns, lexical/similarity scoring, step `sdg` → 16_*    T3
│   ├── global_bench.py           NEW  group_counts, benchmark_table, step `benchmark` → 17_*                           T4
│   ├── gaps.py                   NEW  concentration, few_institution_topics, weak_bridges, step `gaps` → 18_*          T5
│   ├── export_exec.py            NEW  contract 2.2 files + executive bullets from 15_–18_                              T6
│   ├── schema/contract.py        MOD  contract 2.2 models                                                             T6
│   ├── export_v2.py              MOD  P3 files, institution links, Topic.sdg, KPIs, executive, skipped modules        T6
│   ├── validate.py               MOD  cross-file checks of the P3 modules                                             T6
│   └── pipeline.py               MOD  STEPS += institutions (T2), sdg (T3), benchmark (T4), gaps (T5)
└── tests/ test_institutions_ref T1 · test_institutions T2 · test_sdg T3 · test_global_bench T4 · test_gaps T5 ·
          test_contract_p3 + test_release (appended) + test_schema/test_release version pins T6 · test_e2e_p1 (1 assertion) T6
web/
├── scripts/make-fixtures.mjs               MOD  P3 modules in the example release, skipped global in the empty one      T7
├── scripts/make-province-map.mjs           NEW  Natural Earth → src/geo/thProvinces.ts (run once, output committed)      T9
├── fixtures/example/** · fixtures/empty/** REGEN                                                                       T7
├── e2e/smoke.spec.ts                       MOD  routes + checks for every new page; nav menu test                         T7–T11
└── src/
    ├── data/ types.ts · release.ts · fixtures.test.ts       MOD  T7          contract.schema.json · contract.ts  REGEN T6
    ├── components/ Header.tsx (grouped nav) · ModuleFile.tsx (skip reason) T7 · InstitutionLink.tsx T8 · ProvinceMap.tsx T9
    ├── geo/thProvinces.ts                    NEW (generated)  77 province outlines                                       T9
    ├── lib/ executive.ts + executive.test.ts T7 · urlState.ts (codecs) T8–T11
    ├── strings/ executive.ts · modules.ts (absent text) · index.ts                                                      T7
    ├── styles/ executive.css · tokens.css (--seq-1…5) · index.css                                                       T7
    └── pages/ InstitutionsPage · InstitutionPage + TopicPage links T8 · RegionsPage T9 · SdgPage · GlobalPage T10 ·
               GapsPage T11 · overview/KpiGrid · OverviewPage · BriefPage · data/ModuleDownloads · App.tsx T7–T12
docs/ (DATA_SPEC, OPERATIONS, ARCHITECTURE, ROADMAP), CLAUDE.md, DESIGN.md, README.md, web/README.md          T12
```

Work checkpoints added by P3: `15_article_institutions`, `15_institutions`, `15_inst_years`, `15_inst_topics`, `15_inst_pairs`, `15_inst_countries`, `15_inst_suggest`, `15_provinces`, `15_regions`, `15_institutions_meta.json`, `16_topic_goals`, `16_sdg_meta.json`, `17_benchmark`, `17_benchmark_meta.json`, `18_gap_few_institutions`, `18_gap_bridges`, `18_gap_world`, `18_concentration`, `18_gaps_meta.json`. State: `state_dir/ror/<dump>.<country>.json` (ROR subset cache).

**How to read the edit steps:** "Replace …", "Insert … above/below …", "Append …" are exact text operations on the file as it is after the earlier tasks (and after P2). A code block after "Create" is the complete file.

## Task overview

| # | Task | Main outputs |
|---|---|---|
| 1 | P3 config, provinces, countries, institution resolver | `config.py`, `places.py`, `institutions_ref.py`, example CSVs |
| 2 | Step `institutions` (aggregates, network, provinces, R6) | `institutions.py` → 15_* |
| 3 | SDG + Thai frameworks | `frameworks.yaml`, `sdg.py` → 16_* |
| 4 | OpenAlex benchmark | `global_bench.py` → 17_* |
| 5 | Gap finder + concentration risk | `gaps.py` → 18_* |
| 6 | Contract 2.2, export, validate, executive bullets | `contract.py`, `export_exec.py`, `export_v2.py`, `validate.py` |
| 7 | Web data layer, fixtures, grouped navigation, strings, styles | `types.ts`, `release.ts`, `Header.tsx`, `executive.ts` |
| 8 | `/institutions` + `/institutions/:id` + topic-page links (D6, R6) | `InstitutionsPage`, `InstitutionPage` |
| 9 | `/regions` (province choropleth + tables) | `make-province-map.mjs`, `thProvinces.ts`, `ProvinceMap`, `RegionsPage` |
| 10 | `/sdg` + `/global` | `SdgPage`, `GlobalPage` |
| 11 | `/gaps` | `GapsPage` |
| 12 | KPIs, overview + brief additions, docs, final gates | `KpiGrid`, `OverviewPage`, `BriefPage`, docs |

---
### Task 1: P3 config, provinces, countries and the institution resolver

Every P3 threshold enters the config at once (one documented block), the 77 provinces become reference data, `countries` learns ISO codes, and `institutions_ref` turns one affiliation into a canonical institution. No step runs it yet (Task 2).

**Files:**
- Create: `pipeline/atlas/data/th_provinces.csv`, `pipeline/atlas/places.py`, `pipeline/atlas/institutions_ref.py`, `pipeline/registry/institutions_aliases.example.csv`, `pipeline/registry/province_population.example.csv`, `pipeline/tests/test_institutions_ref.py`
- Modify: `pipeline/atlas/config.py`, `pipeline/config.example.yaml`, `pipeline/atlas/countries.py`

**Interfaces:**
- Consumes: `atlas.thai.clean_text / norm_key / thai_ratio`, `atlas.orgs.org_key / org_name`, `atlas.openalex.short_id`, `atlas.countries` (P2).
- Produces: config sections `institutions`, `risk`, `gaps`, `sdg`, `benchmark` (keys below); `atlas.places` — `REGIONS`, `Province(code, name_th, name_en, region)`, `provinces() -> dict[str, Province]`, `region_of(code) -> str`, `province_finder().find(th, en) -> str | None`; `atlas.countries` — `COUNTRY_ISO`, `COUNTRY_ISO_TH`, `COUNTRY_NAMES: dict[str, tuple[str, str]]`, `country_of(th, en) -> str | None`; `atlas.institutions_ref` — `INST_TYPES`, `AliasError`, `Institution(key, name_th, name_en, type, province, country, source, ror)`, `inst_code(key) -> str`, `type_from_name(name) -> str`, `load_aliases(path, min_chars) -> (dict[inst_id, Institution], dict[folded alias, inst_id])`, `load_ror(path, country, cache_dir) -> list[dict]`, `Resolver(aliases, ror, find_province=True).resolve(th, en, org_key) -> Institution | None`.

- [ ] **Step 1: Write the failing test** — create `pipeline/tests/test_institutions_ref.py`:

```python
"""Canonical institutions: alias table → foreign → ROR → as written; provinces named in affiliations."""
import json
import zipfile

import pytest

from atlas.countries import COUNTRIES_EN, COUNTRIES_TH, COUNTRY_ISO, COUNTRY_ISO_TH, COUNTRY_NAMES, country_of
from atlas.institutions_ref import AliasError, Resolver, inst_code, load_aliases, load_ror, type_from_name
from atlas.orgs import org_key
from atlas.places import province_finder, provinces, region_of

ALIASES = """alias,inst_id,name_th,name_en,type,province,country,ror
มหาวิทยาลัยราชภัฏเชียงราย,crru,มหาวิทยาลัยราชภัฏเชียงราย,Chiang Rai Rajabhat University,rajabhat,TH-57,TH,
Chiang Rai Rajabhat University,crru,,,,,,
มรภ.เชียงราย,crru,,,,,,
มหาวิทยาลัยเทคโนโลยีราชมงคลล้านนา,rmutl,มหาวิทยาลัยเทคโนโลยีราชมงคลล้านนา,Rajamangala University of Technology Lanna,rajamangala,TH-50,TH,
มทร.ล้านนา,rmutl,,,,,,
Bangkok University,bu,มหาวิทยาลัยกรุงเทพ,Bangkok University,university,TH-13,TH,
"""
NARESUAN_ROR = {
    "id": "https://ror.org/0abcdef12", "status": "active", "types": ["education"],
    "names": [{"value": "Naresuan University", "types": ["ror_display", "label"], "lang": "en"},
              {"value": "มหาวิทยาลัยนเรศวร", "types": ["label"], "lang": "th"},
              {"value": "NU", "types": ["acronym"], "lang": None}],
    "locations": [{"geonames_id": 1607708, "geonames_details": {"name": "Phitsanulok", "country_code": "TH",
                                                               "country_subdivision_name": "Phitsanulok"}}],
}
TOKYO_ROR = {"id": "https://ror.org/0tokyo000", "status": "active", "types": ["education"],
             "names": [{"value": "University of Tokyo", "types": ["ror_display"], "lang": "en"}],
             "locations": [{"geonames_details": {"name": "Tokyo", "country_code": "JP"}}]}


def _resolver(tmp_path, ror=()):
    p = tmp_path / "aliases.csv"
    p.write_text(ALIASES, encoding="utf-8")
    return Resolver(load_aliases(p), list(ror))


def _resolve(r, th, en=""):
    return r.resolve(th, en, org_key(th, en))


def test_provinces_are_the_77_iso_codes_with_regions():
    p = provinces()
    assert len(p) == 77 and p["TH-10"].region == "bangkok" and p["TH-38"].name_en == "Bueng Kan"
    assert {region_of(c) for c in p} == {"bangkok", "central", "northeast", "north", "south"}
    assert (region_of("TH-65"), region_of("TH-40"), region_of("TH-90"), region_of("TH-71")) == (
        "north", "northeast", "south", "central")


@pytest.mark.parametrize("th, en, code", [
    ("คณะเกษตรศาสตร์ มหาวิทยาลัยขอนแก่น", "", "TH-40"),
    ("มหาวิทยาลัยราชภัฏนครราชสีมา", "", "TH-30"),
    ("โรงพยาบาลเชียงรายประชานุเคราะห์ จ.เชียงราย", "", "TH-57"),
    ("", "Faculty of Medicine, Chiang Mai University", "TH-50"),
    ("", "Chiangmai Rajabhat University", "TH-50"),
    ("สำนักงานสาธารณสุข กรุงเทพมหานคร", "", "TH-10"),
    ("คณะครุศาสตร์ จุฬาลงกรณ์มหาวิทยาลัย", "", None),               # no province named
    ("สำนักงานเผยแพร่ความรู้", "", None),                           # แพร่ inside a word is not Phrae
])
def test_province_named_in_an_affiliation(th, en, code):
    assert province_finder().find(th, en) == code


def test_alias_table_merges_campuses_spellings_and_abbreviations(tmp_path):
    r = _resolver(tmp_path)
    a = _resolve(r, "คณะวิทยาการจัดการ มหาวิทยาลัยราชภัฏเชียงราย")
    b = _resolve(r, "", "Faculty of Education, Chiang Rai Rajabhat University, Thailand")
    c = _resolve(r, "สาขาการตลาด มรภ.เชียงราย")
    assert a == b == c and a.key == "alias:crru" and a.type == "rajabhat" and a.province == "TH-57"
    assert a.source == "alias" and a.country == "TH"
    d = _resolve(r, "มทร.ล้านนา น่าน")                 # a campus in Nan is its university (institution level)
    assert d.key == "alias:rmutl" and d.province == "TH-50" and d.type == "rajamangala"
    e = _resolve(r, "", "School of Communication Arts, Bangkok University")
    assert e.key == "alias:bu" and e.province == "TH-13"          # the alias beats "Bangkok" in the name
    assert inst_code(a.key) == "crru" and inst_code("ror:0ABCdef12") == "ror-0abcdef12"
    assert inst_code("org:abc").startswith("o") and len(inst_code("org:abc")) == 11


@pytest.mark.parametrize("body, msg", [
    ("alias,inst_id\nมหาวิทยาลัยนเรศวร,NU\n", "inst_id"),
    ("alias,inst_id,province\nมหาวิทยาลัยนเรศวร,nu,TH-99\n", "province"),
    ("alias,inst_id\nนร,nu\n", "shorter"),
    ("alias,inst_id\nมหาวิทยาลัยนเรศวร,nu\nมหาวิทยาลัยนเรศวร,cu\n", "already maps"),
    ("alias,inst_id,type\nมหาวิทยาลัยนเรศวร,nu,uni\n", "type"),
    ("alias,inst_id,colour\nx,y,z\n", "columns"),
])
def test_bad_alias_rows_stop_with_the_row(tmp_path, body, msg):
    p = tmp_path / "a.csv"
    p.write_text(body, encoding="utf-8")
    with pytest.raises(AliasError, match=msg):
        load_aliases(p)
    assert load_aliases(None) == ({}, {}) and load_aliases(tmp_path / "missing.csv") == ({}, {})


def test_ror_dump_gives_names_and_province_and_is_cached(tmp_path):
    dump = tmp_path / "ror.zip"
    with zipfile.ZipFile(dump, "w") as z:
        z.writestr("v9-ror-data_schema_v2.json", json.dumps([NARESUAN_ROR, TOKYO_ROR]))
    recs = load_ror(dump, "TH", tmp_path / "cache")
    assert [x["id"] for x in recs] == ["0abcdef12"] and recs[0]["province"] == "TH-65"
    assert (tmp_path / "cache" / "ror.TH.json").exists() and load_ror(dump, "TH", tmp_path / "cache") == recs
    r = Resolver(({}, {}), recs)
    th = _resolve(r, "คณะบริหารธุรกิจ มหาวิทยาลัยนเรศวร")
    en = _resolve(r, "", "Faculty of Business, Naresuan University")
    assert th == en and th.key == "ror:0abcdef12" and th.name_en == "Naresuan University" and th.source == "ror"
    assert _resolve(r, "", "NU").source == "name"                  # acronyms are never matched
    assert load_ror(tmp_path / "nope.zip", "TH", tmp_path / "cache") == []


def test_foreign_and_unplaced_institutions(tmp_path):
    r = _resolver(tmp_path)
    jp = _resolve(r, "", "Graduate School of Education, University of Tokyo, Japan")
    assert jp.country == "JP" and jp.province is None and jp.source == "name" and jp.key.startswith("org:")
    assert _resolve(r, "คณะศึกษาศาสตร์ มหาวิทยาลัยแห่งชาติลาว สปป.ลาว").country == "LA"
    cu = _resolve(r, "คณะครุศาสตร์ จุฬาลงกรณ์มหาวิทยาลัย")
    assert cu.country == "TH" and cu.province is None and cu.type == "university"
    assert r.resolve("", "", "") is None
    assert country_of("", "Mahidol University, Thailand") == "TH" and country_of("ภาควิชาภาษาจีน", "") is None
    assert type_from_name("โรงพยาบาลศิริราช") == "hospital" and type_from_name("Chiang Rai Rajabhat University") == "rajabhat"
    assert set(COUNTRY_ISO) == set(COUNTRIES_EN) and set(COUNTRY_ISO_TH) == set(COUNTRIES_TH)
    assert set(COUNTRY_ISO.values()) | set(COUNTRY_ISO_TH.values()) | {"TH"} <= set(COUNTRY_NAMES)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_institutions_ref.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.institutions_ref'`.

- [ ] **Step 3: Config.** In `pipeline/atlas/config.py` insert directly above `class ExportCfg(_Strict):`:

```python
class InstitutionsCfg(_Strict):
    """Institutions (P3): canonical institution, type, province and country from the curated alias table and an
    optional local ROR dump; collaboration network; output per province. Institution level only (PDPA)."""
    enabled: bool = True
    aliases_path: str | None = None       # registry/institutions_aliases.csv (optional); the example config sets ./registry/…
    ror_path: str | None = None           # a ROR data dump (.json or .zip, CC0) on local disk; null = no ROR matching
    population_path: str | None = None    # registry/province_population.csv (optional) → articles per 100,000 people
    alias_min_chars: int = Field(4, ge=2)
    province_from_name: bool = True
    window_years: int = Field(5, ge=1)
    min_articles: int = Field(5, ge=1)    # fewer articles in the window → counted, never listed, linked or paired
    network_min_articles: int = Field(3, ge=1)
    network_max_edges: int = Field(300, ge=0)
    top_topics: int = Field(15, ge=1)
    max_partners: int = Field(15, ge=0)
    suggest_k: int = Field(5, ge=0)
    suggest_min_similarity: float = Field(0.3, ge=0.0, le=1.0)


class RiskCfg(_Strict):
    """E10 concentration risk over the emerging recent window R."""
    min_articles: int = Field(30, ge=1)
    max_top_share: float = Field(0.5, gt=0.0, le=1.0)
    max_hhi: float = Field(0.25, gt=0.0, le=1.0)


class GapsCfg(_Strict):
    """R5 gap finder."""
    statuses: list[Literal["EMERGING", "WATCH", "HOT"]] = Field(default_factory=lambda: ["EMERGING", "WATCH"])
    max_institutions: int = Field(5, ge=0)
    bridge_min_similarity: float = Field(0.6, ge=0.0, le=1.0)
    bridge_max_jaccard: float = Field(0.1, ge=0.0, le=1.0)
    max_items: int = Field(30, ge=1)


class SdgCfg(_Strict):
    """E8 SDGs + Thai frameworks, mapped at topic level (atlas/data/frameworks.yaml)."""
    enabled: bool = True
    frameworks_path: str | None = None    # null = the packaged atlas/data/frameworks.yaml
    method: Literal["auto", "embedding", "lexical"] = "auto"
    min_similarity: float = Field(0.45, ge=-1.0, le=1.0)
    min_article_share: float = Field(0.15, gt=0.0, le=1.0)
    max_goals_per_topic: int = Field(3, ge=1)
    docs_per_topic: int = Field(400, ge=1)


class BenchmarkCfg(_Strict):
    """E9 Thailand vs the world (OpenAlex, through taxonomy.openalex). `global` is a Python keyword."""
    enabled: bool = True
    min_world_works: int = Field(1000, ge=1)
    min_world_ratio: float = Field(1.2, gt=0.0)
    max_activity_index: float = Field(0.5, gt=0.0)


```

In `class AtlasConfig(_Strict):` insert below `    changes: ChangesCfg = Field(default_factory=ChangesCfg)`:

```python
    institutions: InstitutionsCfg = Field(default_factory=InstitutionsCfg)
    risk: RiskCfg = Field(default_factory=RiskCfg)
    gaps: GapsCfg = Field(default_factory=GapsCfg)
    sdg: SdgCfg = Field(default_factory=SdgCfg)
    benchmark: BenchmarkCfg = Field(default_factory=BenchmarkCfg)
```

In `load_config` insert below the two lines that resolve `cfg["journals"]["registry_path"]`:

```python
    for key in ("aliases_path", "ror_path", "population_path"):
        if cfg["institutions"][key]:
            cfg["institutions"][key] = _resolve(cfg["institutions"][key], base)
    if cfg["sdg"]["frameworks_path"]:
        cfg["sdg"]["frameworks_path"] = _resolve(cfg["sdg"]["frameworks_path"], base)
```

In `pipeline/config.example.yaml` insert directly above the line `export:`:

```yaml
# ---------- P3 ผู้บริหาร: สถาบัน เครือข่ายความร่วมมือ จังหวัด (ระดับสถาบันเท่านั้น — ไม่มีข้อมูลรายบุคคล) ----------
institutions:
  enabled: true
  aliases_path: ./registry/institutions_aliases.csv   # ไม่บังคับ: ตารางชื่อสถาบันที่คัดเอง (คอลัมน์ดู registry/institutions_aliases.example.csv) — วิทยาเขต/ชื่อย่อของราชภัฏ ราชมงคล ฯลฯ → มหาวิทยาลัยเดียว
  ror_path: null              # ไม่บังคับ: ไฟล์ ROR data dump (.json หรือ .zip, CC0) ที่ดาวน์โหลดไว้ในเครื่อง — null = ไม่จับคู่กับ ROR
  population_path: ./registry/province_population.csv   # ไม่บังคับ: code,population,year (เช่น สถิติทะเบียนราษฎร) → บทความต่อประชากรแสนคน
  alias_min_chars: 4          # ชื่อในตารางที่สั้นกว่านี้ (หลังตัดวรรณยุกต์/ช่องว่าง/จุด) ไม่รับ — กันจับผิดสถาบัน
  province_from_name: true    # สถาบันที่ไม่อยู่ในตาราง/ROR → อนุมานจังหวัดจากชื่อจังหวัดในสังกัด (ติดป้าย "ตามที่เขียนในบทความ")
  window_years: 5             # ตัวชี้วัดสถาบัน/จังหวัด/เครือข่ายคิดจาก 5 ปีล่าสุดที่ข้อมูลครบ
  min_articles: 5             # สถาบันที่มีบทความในช่วงนั้น < 5 เรื่อง ถูกนับรวม แต่ไม่แสดงเป็นรายการ/หน้า/คู่ความร่วมมือ
  network_min_articles: 3     # คู่สถาบันต้องมีบทความร่วมกัน ≥ 3 เรื่องจึงแสดง
  network_max_edges: 300      # คู่ความร่วมมือที่แสดงสูงสุด (เรียงจากบทความร่วมมากไปน้อย)
  top_topics: 15              # หัวข้อที่แสดงต่อสถาบัน
  max_partners: 15            # สถาบันคู่ความร่วมมือ/ประเทศที่แสดงต่อสถาบัน
  suggest_k: 5                # R6 สถาบันที่อาจร่วมงานได้ ต่อสถาบัน
  suggest_min_similarity: 0.3 # ...สัดส่วนหัวข้อคล้ายกัน (cosine) ≥ ค่านี้ และยังไม่มีบทความร่วมกันในช่วงนั้น

risk:                         # E10 ความเสี่ยงการกระจุกตัว (บทความช่วงล่าสุด R ของ emerging)
  min_articles: 30            # ประเมินเฉพาะหัวข้อ/สาขาที่มีบทความ ≥ 30 เรื่อง
  max_top_share: 0.5          # สถาบัน/วารสารรายใหญ่สุดอยู่ใน ≥ 50% ของบทความ = กระจุกตัว
  max_hhi: 0.25               # หรือ HHI (ผลรวมกำลังสองของสัดส่วน) ≥ 0.25 = กระจุกตัว

gaps:                         # R5 ตัวหาช่องว่างงานวิจัย
  statuses: [EMERGING, WATCH] # สถานะหัวข้อที่ตรวจ "สถาบันทำน้อย"
  max_institutions: 5         # มีสถาบันทำ ≤ 5 แห่งในช่วงล่าสุด = สถาบันทำน้อย
  bridge_min_similarity: 0.6  # หัวข้อเพื่อนบ้าน = เส้นเชื่อมบนแผนที่ที่ความคล้าย ≥ ค่านี้
  bridge_max_jaccard: 0.1     # ...และชุดสถาบันที่ทำซ้อนกัน (Jaccard) ≤ ค่านี้ = ยังไม่ค่อยมีใครเชื่อม
  max_items: 30               # รายการสูงสุดต่อหมวด

sdg:                          # E8 SDG 17 เป้า + กรอบไทย (BCG / แผนด้าน ววน. / หมุดหมายแผนฯ 13) ระดับหัวข้อ
  enabled: true
  frameworks_path: null       # null = atlas/data/frameworks.yaml ที่มากับโค้ด (แก้คำสำคัญได้) — หรือชี้ไปไฟล์ YAML ของผู้ดูแล
  method: auto                # auto = ความคล้ายของ centroid หัวข้อกับข้อความเป้าหมาย (embedding api/local) ถ้ามี ไม่งั้นนับคำสำคัญ; embedding | lexical
  min_similarity: 0.45        # embedding: cosine ≥ ค่านี้ (ปรับตามโมเดล)
  min_article_share: 0.15     # lexical: บทความของหัวข้อที่ชื่อเรื่อง/คำสำคัญมีคำของเป้าหมาย ≥ 15%
  max_goals_per_topic: 3      # เป้าหมายสูงสุดต่อหัวข้อ ต่อกรอบ
  docs_per_topic: 400         # lexical: สุ่มบทความต่อหัวข้อ (คงที่ด้วย pipeline.seed)

benchmark:                    # E9 ไทยเทียบโลก (OpenAlex ผ่าน taxonomy.openalex: base_url, api_key_env, country_code)
  enabled: true               # false = ไม่เรียก OpenAlex (หน้า /global บอกเหตุผล)
  min_world_works: 1000       # subfield ที่มีงานทั้งโลกช่วงล่าสุด < 1,000 เรื่อง ไม่นับเป็นโอกาส
  min_world_ratio: 1.2        # โลกโต: สัดส่วนของ subfield ในงานทั้งโลก ช่วงล่าสุด ÷ ช่วงฐาน ≥ 1.2
  max_activity_index: 0.5     # ไทยยังเล็ก: ดัชนีความเข้มข้น (สัดส่วนในงานไทย ÷ สัดส่วนในงานโลก) ≤ 0.5

```

- [ ] **Step 4: Province reference data.** Create `pipeline/atlas/data/th_provinces.csv` (ISO 3166-2:TH; Thai names as the Royal Institute writes them; English names as the Department of Provincial Administration writes them; `alt_*` = other spellings, `;`-separated):

```csv
code,name_th,name_en,alt_th,alt_en
TH-10,กรุงเทพมหานคร,Bangkok,,Krung Thep
TH-11,สมุทรปราการ,Samut Prakan,,Samut Prakarn
TH-12,นนทบุรี,Nonthaburi,,
TH-13,ปทุมธานี,Pathum Thani,,
TH-14,พระนครศรีอยุธยา,Phra Nakhon Si Ayutthaya,อยุธยา,Ayutthaya;Ayudhya
TH-15,อ่างทอง,Ang Thong,,
TH-16,ลพบุรี,Lop Buri,,
TH-17,สิงห์บุรี,Sing Buri,,
TH-18,ชัยนาท,Chai Nat,,
TH-19,สระบุรี,Saraburi,,
TH-20,ชลบุรี,Chon Buri,,
TH-21,ระยอง,Rayong,,
TH-22,จันทบุรี,Chanthaburi,,
TH-23,ตราด,Trat,,
TH-24,ฉะเชิงเทรา,Chachoengsao,,
TH-25,ปราจีนบุรี,Prachin Buri,,
TH-26,นครนายก,Nakhon Nayok,,
TH-27,สระแก้ว,Sa Kaeo,,
TH-30,นครราชสีมา,Nakhon Ratchasima,โคราช,Korat
TH-31,บุรีรัมย์,Buri Ram,,
TH-32,สุรินทร์,Surin,,
TH-33,ศรีสะเกษ,Si Sa Ket,,Sisaket
TH-34,อุบลราชธานี,Ubon Ratchathani,,
TH-35,ยโสธร,Yasothon,,
TH-36,ชัยภูมิ,Chaiyaphum,,
TH-37,อำนาจเจริญ,Amnat Charoen,,
TH-38,บึงกาฬ,Bueng Kan,,
TH-39,หนองบัวลำภู,Nong Bua Lam Phu,,
TH-40,ขอนแก่น,Khon Kaen,,
TH-41,อุดรธานี,Udon Thani,,
TH-42,เลย,Loei,,
TH-43,หนองคาย,Nong Khai,,
TH-44,มหาสารคาม,Maha Sarakham,,
TH-45,ร้อยเอ็ด,Roi Et,,
TH-46,กาฬสินธุ์,Kalasin,,
TH-47,สกลนคร,Sakon Nakhon,,
TH-48,นครพนม,Nakhon Phanom,,
TH-49,มุกดาหาร,Mukdahan,,
TH-50,เชียงใหม่,Chiang Mai,,
TH-51,ลำพูน,Lamphun,,
TH-52,ลำปาง,Lampang,,
TH-53,อุตรดิตถ์,Uttaradit,,
TH-54,แพร่,Phrae,,
TH-55,น่าน,Nan,,
TH-56,พะเยา,Phayao,,
TH-57,เชียงราย,Chiang Rai,,
TH-58,แม่ฮ่องสอน,Mae Hong Son,,
TH-60,นครสวรรค์,Nakhon Sawan,,
TH-61,อุทัยธานี,Uthai Thani,,
TH-62,กำแพงเพชร,Kamphaeng Phet,,
TH-63,ตาก,Tak,,
TH-64,สุโขทัย,Sukhothai,,
TH-65,พิษณุโลก,Phitsanulok,,
TH-66,พิจิตร,Phichit,,
TH-67,เพชรบูรณ์,Phetchabun,,
TH-70,ราชบุรี,Ratchaburi,,
TH-71,กาญจนบุรี,Kanchanaburi,,
TH-72,สุพรรณบุรี,Suphan Buri,,
TH-73,นครปฐม,Nakhon Pathom,,
TH-74,สมุทรสาคร,Samut Sakhon,,
TH-75,สมุทรสงคราม,Samut Songkhram,,
TH-76,เพชรบุรี,Phetchaburi,,
TH-77,ประจวบคีรีขันธ์,Prachuap Khiri Khan,,
TH-80,นครศรีธรรมราช,Nakhon Si Thammarat,,
TH-81,กระบี่,Krabi,,
TH-82,พังงา,Phangnga,,Phang Nga
TH-83,ภูเก็ต,Phuket,,
TH-84,สุราษฎร์ธานี,Surat Thani,,
TH-85,ระนอง,Ranong,,
TH-86,ชุมพร,Chumphon,,
TH-90,สงขลา,Songkhla,,
TH-91,สตูล,Satun,,
TH-92,ตรัง,Trang,,
TH-93,พัทลุง,Phatthalung,,
TH-94,ปัตตานี,Pattani,,
TH-95,ยะลา,Yala,,
TH-96,นราธิวาส,Narathiwat,,
```

Create `pipeline/atlas/places.py`:

```python
"""Thai provinces (77, ISO 3166-2:TH) and the province named in an affiliation.

atlas/data/th_provinces.csv is public reference data (codes, Thai and English names, other spellings). The region
follows the National Statistical Office's four regions + Bangkok and is decided by the code: 10 Bangkok · 11–27 and
70–77 central (incl. east and west) · 30–49 northeast · 50–67 north · 80–96 south.

province_finder().find(th, en) — precision first (a wrong province is worse than none):
  Thai     a province name right after จังหวัด / จ. / ราชภัฏ / มหาวิทยาลัย / โรงพยาบาล / วิทยาลัยพยาบาลบรมราชชนนี,
           or กรุงเทพ anywhere (text folded like org keys: tone marks, spaces and dots ignored)
  English  a province name as a whole word, spaces optional ("Chiang Mai", "Chiangmai"), or an alt_en spelling
  The first province named wins (an affiliation names its main location first). Thai text is read before English.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from atlas.thai import clean_text, norm_key

PROVINCES_CSV = Path(__file__).parent / "data" / "th_provinces.csv"
REGIONS = ("bangkok", "central", "northeast", "north", "south")
_TH_PREFIXES = ("จังหวัด", "จ", "ราชภัฏ", "มหาวิทยาลัย", "โรงพยาบาล", "วิทยาลัยพยาบาลบรมราชชนนี")


@dataclass(frozen=True)
class Province:
    code: str
    name_th: str
    name_en: str
    region: str


def region_of(code: str) -> str:
    n = int(code.split("-")[1])
    if n == 10:
        return "bangkok"
    if 11 <= n <= 27 or 70 <= n <= 77:
        return "central"
    if 30 <= n <= 49:
        return "northeast"
    if 50 <= n <= 67:
        return "north"
    return "south"


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    with PROVINCES_CSV.open(encoding="utf-8", newline="") as f:
        return tuple({k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f))


@lru_cache(maxsize=1)
def provinces() -> dict[str, Province]:
    return {r["code"]: Province(r["code"], r["name_th"], r["name_en"], region_of(r["code"])) for r in _rows()}


class ProvinceFinder:
    def __init__(self, rows):
        th_names: dict[str, str] = {}
        en_names: dict[str, str] = {}
        for r in rows:
            for n in [r["name_th"], *filter(None, r["alt_th"].split(";"))]:
                th_names[norm_key(n)] = r["code"]
            for n in [r["name_en"], *filter(None, r["alt_en"].split(";"))]:
                en_names[n.strip().lower()] = r["code"]
        self._th_code = th_names
        names = "|".join(re.escape(k) for k in sorted(th_names, key=len, reverse=True))
        prefixes = "|".join(re.escape(norm_key(p)) for p in _TH_PREFIXES)
        self._th = re.compile(f"(?:{prefixes})({names})")
        self._bangkok = norm_key("กรุงเทพ")
        self._en_code = {re.sub(r"\s", "", k): v for k, v in en_names.items()}
        words = [r"\s?".join(re.escape(w) for w in k.split()) for k in sorted(en_names, key=len, reverse=True)]
        self._en = re.compile(r"(?<![a-z])(" + "|".join(words) + r")(?![a-z])")

    def find(self, affiliation_th: str | None, affiliation_en: str | None) -> str | None:
        th = norm_key(clean_text(affiliation_th))
        hits = []
        if m := self._th.search(th):
            hits.append((m.start(), self._th_code[m.group(1)]))
        if (b := th.find(self._bangkok)) >= 0:
            hits.append((b, "TH-10"))
        if hits:
            return min(hits)[1]
        m = self._en.search(clean_text(affiliation_en).lower())
        return self._en_code[re.sub(r"\s", "", m.group(1))] if m else None


@lru_cache(maxsize=1)
def province_finder() -> ProvinceFinder:
    return ProvinceFinder(_rows())
```

- [ ] **Step 5: Countries with ISO codes.** Append to `pipeline/atlas/countries.py`:

```python


# ISO 3166-1 alpha-2 of every name above (England, Scotland, UK → GB) and the names the web shows (th, en)
COUNTRY_ISO = {
    "Australia": "AU", "Austria": "AT", "Bangladesh": "BD", "Belgium": "BE", "Bhutan": "BT", "Brazil": "BR",
    "Brunei": "BN", "Cambodia": "KH", "Canada": "CA", "China": "CN", "Denmark": "DK", "Egypt": "EG", "England": "GB",
    "Finland": "FI", "France": "FR", "Germany": "DE", "Hong Kong": "HK", "India": "IN", "Indonesia": "ID", "Iran": "IR",
    "Italy": "IT", "Japan": "JP", "Kenya": "KE", "Korea": "KR", "Lao PDR": "LA", "Laos": "LA", "Macau": "MO",
    "Malaysia": "MY", "Mongolia": "MN", "Myanmar": "MM", "Nepal": "NP", "Netherlands": "NL", "New Zealand": "NZ",
    "Nigeria": "NG", "Norway": "NO", "Pakistan": "PK", "Philippines": "PH", "Poland": "PL", "Russia": "RU",
    "Saudi Arabia": "SA", "Scotland": "GB", "Singapore": "SG", "South Africa": "ZA", "Spain": "ES", "Sri Lanka": "LK",
    "Sweden": "SE", "Switzerland": "CH", "Taiwan": "TW", "Timor-Leste": "TL", "Turkey": "TR", "United Kingdom": "GB",
    "United States": "US", "USA": "US", "U.S.A.": "US", "UK": "GB", "Viet Nam": "VN", "Vietnam": "VN",
}
COUNTRY_ISO_TH = {
    "ญี่ปุ่น": "JP", "จีน": "CN", "เกาหลีใต้": "KR", "เกาหลี": "KR", "ลาว": "LA", "กัมพูชา": "KH", "เวียดนาม": "VN",
    "เมียนมา": "MM", "พม่า": "MM", "มาเลเซีย": "MY", "อินโดนีเซีย": "ID", "ฟิลิปปินส์": "PH", "สิงคโปร์": "SG", "บรูไน": "BN",
    "อินเดีย": "IN", "ภูฏาน": "BT", "เนปาล": "NP", "บังกลาเทศ": "BD", "ศรีลังกา": "LK", "ปากีสถาน": "PK", "ไต้หวัน": "TW",
    "ออสเตรเลีย": "AU", "นิวซีแลนด์": "NZ", "สหรัฐอเมริกา": "US", "อังกฤษ": "GB", "สหราชอาณาจักร": "GB", "เยอรมนี": "DE",
    "ฝรั่งเศส": "FR", "เนเธอร์แลนด์": "NL", "สวีเดน": "SE", "แคนาดา": "CA",
}
COUNTRY_NAMES: dict[str, tuple[str, str]] = {
    "TH": ("ไทย", "Thailand"), "AU": ("ออสเตรเลีย", "Australia"), "AT": ("ออสเตรีย", "Austria"),
    "BD": ("บังกลาเทศ", "Bangladesh"), "BE": ("เบลเยียม", "Belgium"), "BT": ("ภูฏาน", "Bhutan"), "BR": ("บราซิล", "Brazil"),
    "BN": ("บรูไน", "Brunei"), "KH": ("กัมพูชา", "Cambodia"), "CA": ("แคนาดา", "Canada"), "CN": ("จีน", "China"),
    "DK": ("เดนมาร์ก", "Denmark"), "EG": ("อียิปต์", "Egypt"), "GB": ("สหราชอาณาจักร", "United Kingdom"),
    "FI": ("ฟินแลนด์", "Finland"), "FR": ("ฝรั่งเศส", "France"), "DE": ("เยอรมนี", "Germany"), "HK": ("ฮ่องกง", "Hong Kong"),
    "IN": ("อินเดีย", "India"), "ID": ("อินโดนีเซีย", "Indonesia"), "IR": ("อิหร่าน", "Iran"), "IT": ("อิตาลี", "Italy"),
    "JP": ("ญี่ปุ่น", "Japan"), "KE": ("เคนยา", "Kenya"), "KR": ("เกาหลีใต้", "South Korea"), "LA": ("ลาว", "Laos"),
    "MO": ("มาเก๊า", "Macau"), "MY": ("มาเลเซีย", "Malaysia"), "MN": ("มองโกเลีย", "Mongolia"), "MM": ("เมียนมา", "Myanmar"),
    "NP": ("เนปาล", "Nepal"), "NL": ("เนเธอร์แลนด์", "Netherlands"), "NZ": ("นิวซีแลนด์", "New Zealand"),
    "NG": ("ไนจีเรีย", "Nigeria"), "NO": ("นอร์เวย์", "Norway"), "PK": ("ปากีสถาน", "Pakistan"),
    "PH": ("ฟิลิปปินส์", "Philippines"), "PL": ("โปแลนด์", "Poland"), "RU": ("รัสเซีย", "Russia"),
    "SA": ("ซาอุดีอาระเบีย", "Saudi Arabia"), "SG": ("สิงคโปร์", "Singapore"), "ZA": ("แอฟริกาใต้", "South Africa"),
    "ES": ("สเปน", "Spain"), "LK": ("ศรีลังกา", "Sri Lanka"), "SE": ("สวีเดน", "Sweden"),
    "CH": ("สวิตเซอร์แลนด์", "Switzerland"), "TW": ("ไต้หวัน", "Taiwan"), "TL": ("ติมอร์-เลสเต", "Timor-Leste"),
    "TR": ("ตุรกี", "Türkiye"), "US": ("สหรัฐอเมริกา", "United States"), "VN": ("เวียดนาม", "Vietnam"),
}


def country_of(affiliation_th: str | None, affiliation_en: str | None) -> str | None:
    """ISO alpha-2 of the country an affiliation names: "TH" when it names Thailand, a foreign code under the rules
    of is_foreign_affiliation, None when it names no country (most Thai affiliations)."""
    th, en = clean_text(affiliation_th), clean_text(affiliation_en)
    if _THAILAND.search(th) or _THAILAND.search(en):
        return "TH"
    if m := _TH.search(th):
        name = re.sub(r"^ประเทศ\s*", "", m.group(0))
        return "LA" if name.startswith("สปป") else COUNTRY_ISO_TH.get(name)
    m = _EN.search(en)
    return COUNTRY_ISO.get(m.group(0)) if m else None
```

- [ ] **Step 6: The resolver.** Create `pipeline/atlas/institutions_ref.py`:

```python
"""Canonical institutions (P3): curated alias table → foreign country → ROR dump (CC0, local file) → the
organisation as written.

Resolver.resolve(affiliation_th, affiliation_en, org_key) — the first rule that answers wins:
  1. alias    registry/institutions_aliases.csv (curated; the real file is git-ignored). An alias matches when its
              folded text (atlas.thai.norm_key: case, tone marks, spaces and punctuation ignored) equals the org_key
              or occurs in the folded affiliation — the leftmost, then the longest alias. Rajabhat / Rajamangala
              campuses and abbreviations are rows that map to their university.
  2. foreign  the affiliation names a country other than Thailand (atlas.countries.country_of) → the organisation
              as written, with that country and no province.
  3. ror      a ROR record of the home country whose label, display name or alias (acronyms are too ambiguous)
              equals the organisation part of the affiliation (atlas.orgs.org_name), folded.
  4. name     the organisation as written (P1 org_key), its type from its name, the province named in the
              affiliation (atlas.places) and country TH when the text is Thai or names a Thai province.
Published ids (inst_code) are stable: the alias inst_id, "ror-<id>", or "o" + 10 hex of sha1(org_key).
Institution level only — author names are never read here (PDPA).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from atlas.countries import country_of
from atlas.openalex import short_id
from atlas.orgs import org_name
from atlas.places import province_finder, provinces
from atlas.thai import clean_text, norm_key, thai_ratio

INST_TYPES = ("university", "rajabhat", "rajamangala", "hospital", "government", "research", "company", "other")
ALIAS_COLUMNS = ("alias", "inst_id", "name_th", "name_en", "type", "province", "country", "ror")
INST_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
ROR_TYPES = {"education": "university", "healthcare": "hospital", "government": "government",
             "facility": "research", "company": "company"}
# (type, folded words) checked in order on the organisation's name — the first hit wins
_TYPE_RULES = tuple((t, tuple(norm_key(w) for w in words)) for t, words in (
    ("rajabhat", ("ราชภัฏ", "rajabhat")),
    ("rajamangala", ("ราชมงคล", "rajamangala")),
    ("hospital", ("โรงพยาบาล", "hospital")),
    ("university", ("มหาวิทยาลัย", "university", "วิทยาลัย", "college", "institute of technology", "สถาบันเทคโนโลยี",
                    "สถาบันบัณฑิต")),
    ("research", ("สถาบันวิจัย", "ศูนย์วิจัย", "research institute", "research center", "research centre")),
    ("company", ("บริษัท", "company", "co ltd", "corporation")),
    ("government", ("กระทรวง", "สำนักงาน", "ministry", "department of", "office of")),
))
_DEPARTMENT = norm_key("กรม")


class AliasError(ValueError):
    """registry/institutions_aliases.csv cannot be used — the message names the row."""


@dataclass(frozen=True)
class Institution:
    key: str
    name_th: str = ""
    name_en: str = ""
    type: str = "other"
    province: str | None = None
    country: str | None = None
    source: str = "name"          # alias | ror | name
    ror: str = ""


def inst_code(key: str) -> str:
    """Published, URL- and file-safe id of an institution key (alias:<id> | ror:<id> | org:<org_key>)."""
    kind, _, rest = key.partition(":")
    if kind == "alias":
        return rest
    if kind == "ror":
        return f"ror-{rest.lower()}"
    return "o" + hashlib.sha1(rest.encode("utf-8")).hexdigest()[:10]


def type_from_name(name: str) -> str:
    folded = norm_key(clean_text(name))
    for t, words in _TYPE_RULES:
        if any(w in folded for w in words):
            return t
    return "government" if folded.startswith(_DEPARTMENT) else "other"   # กรม… (a department), not อุตสาหกรรม


def load_aliases(path: str | Path | None, min_chars: int = 4) -> tuple[dict[str, Institution], dict[str, str]]:
    """({inst_id: Institution}, {folded alias: inst_id}). No path or no file → ({}, {}). Errors name the row."""
    if not path or not Path(path).exists():
        return {}, {}
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = [str(c).strip() for c in (reader.fieldnames or [])]
        unknown = sorted(set(cols) - set(ALIAS_COLUMNS))
        if unknown or not {"alias", "inst_id"} <= set(cols):
            raise AliasError(f"{path}: columns must come from {list(ALIAS_COLUMNS)} and include alias and inst_id "
                             f"(unknown columns: {unknown})")
        rows = [{str(k).strip(): (v or "").strip() for k, v in r.items() if k} for r in reader]
    known = provinces()
    attrs: dict[str, dict[str, str]] = {}
    first: dict[str, str] = {}
    aliases: dict[str, str] = {}
    for n, r in enumerate(rows, start=2):
        where, iid, alias = f"{path} row {n}", r.get("inst_id", ""), r.get("alias", "")
        if not INST_ID.fullmatch(iid) or iid.startswith("ror-"):
            raise AliasError(f"{where}: inst_id {iid!r} must be 2–41 lower-case letters, digits or '-' (not ror-…)")
        folded = norm_key(clean_text(alias))
        if len(folded) < min_chars:
            raise AliasError(f"{where}: alias {alias!r} is shorter than institutions.alias_min_chars ({min_chars}) "
                             "once folded — too ambiguous")
        if aliases.get(folded, iid) != iid:
            raise AliasError(f"{where}: alias {alias!r} already maps to {aliases[folded]!r}")
        aliases[folded] = iid
        first.setdefault(iid, alias)
        given = {"name_th": r.get("name_th", ""), "name_en": r.get("name_en", ""), "type": r.get("type", ""),
                 "province": r.get("province", "").upper(), "country": r.get("country", "").upper(),
                 "ror": short_id(r.get("ror", "")).lower()}
        if given["type"] and given["type"] not in INST_TYPES:
            raise AliasError(f"{where}: type {given['type']!r} is not one of {list(INST_TYPES)}")
        if given["province"] and given["province"] not in known:
            raise AliasError(f"{where}: province {given['province']!r} is not an ISO 3166-2:TH code such as TH-10")
        if given["country"] and not re.fullmatch(r"[A-Z]{2}", given["country"]):
            raise AliasError(f"{where}: country {given['country']!r} is not a two-letter ISO code")
        a = attrs.setdefault(iid, {})
        for k, v in given.items():
            if v and a.get(k, v) != v:
                raise AliasError(f"{where}: {k} {v!r} contradicts {a[k]!r} given for {iid} on an earlier row")
            if v:
                a[k] = v
    insts = {}
    for iid, a in attrs.items():
        th = a.get("name_th") or (first[iid] if thai_ratio(first[iid]) > 0.5 else "")
        en = a.get("name_en") or ("" if th else first[iid])
        insts[iid] = Institution(key=f"alias:{iid}", name_th=th, name_en=en,
                                 type=a.get("type") or type_from_name(f"{th} {en}"), province=a.get("province"),
                                 country=a.get("country") or "TH", source="alias", ror=a.get("ror", ""))
    return insts, aliases


def _read_dump(p: Path) -> list:
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".json")]
            if not names:
                raise ValueError(f"{p}: no .json file inside the zip")
            pick = next((n for n in names if n.lower().endswith("schema_v2.json")), names[0])
            with z.open(pick) as f:
                return json.load(f)
    return json.loads(p.read_text(encoding="utf-8"))


def _ror_province(d: dict) -> str | None:
    code = str(d.get("country_subdivision_code") or "").upper()
    if code in provinces():                 # ISO "TH-65"; bare GeoNames admin codes are not ISO → read the names
        return code
    return province_finder().find("", f"{d.get('country_subdivision_name') or ''}, {d.get('name') or ''}")


def ror_record(x: dict, country: str) -> dict | None:
    """The fields the resolver uses from one ROR v2 record located in `country` (None: elsewhere or inactive)."""
    details = [loc.get("geonames_details") or {} for loc in x.get("locations") or []]
    here = next((d for d in details if d.get("country_code") == country), None)
    if here is None or x.get("status", "active") != "active":
        return None
    names = x.get("names") or []
    usable = [n["value"] for n in names
              if n.get("value") and set(n.get("types") or []) & {"ror_display", "label", "alias"}]
    th = next((n["value"] for n in names if n.get("lang") == "th" and n.get("value")), "")
    en = next((n["value"] for n in names if "ror_display" in (n.get("types") or [])), usable[0] if usable else "")
    base = next((ROR_TYPES[t] for t in x.get("types") or [] if t in ROR_TYPES), "other")
    refined = type_from_name(f"{th} {en}")
    return {"id": short_id(x.get("id")).lower(), "names": usable, "name_th": th, "name_en": en,
            "type": refined if refined in ("rajabhat", "rajamangala") else base, "province": _ror_province(here)}


def load_ror(path: str | Path | None, country: str, cache_dir: str | Path) -> list[dict]:
    """ROR records located in `country`. The dump (downloaded by the maintainer) is read once; the subset is cached
    as cache_dir/<dump name>.<country>.json and reused while it is newer than the dump. Never touches the network."""
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        print(f"[institutions] WARNING: institutions.ror_path {p} does not exist — ROR matching skipped")
        return []
    cache = Path(cache_dir) / f"{p.stem}.{country}.json"
    if cache.exists() and cache.stat().st_mtime >= p.stat().st_mtime:
        return json.loads(cache.read_text(encoding="utf-8"))
    out = [r for r in (ror_record(x, country) for x in _read_dump(p)) if r]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"[institutions] ROR: {len(out):,} records in {country} from {p.name}")
    return out


class Resolver:
    """Affiliation → Institution (None when the author row names no organisation at all)."""

    def __init__(self, aliases: tuple[dict[str, Institution], dict[str, str]], ror: list[dict],
                 find_province: bool = True):
        self.insts, self.alias_to_id = aliases
        self._alias_rx = (re.compile("|".join(re.escape(a) for a in sorted(self.alias_to_id, key=len, reverse=True)))
                          if self.alias_to_id else None)
        self.ror: dict[str, dict] = {}
        for r in ror:
            for name in r["names"]:
                self.ror.setdefault(norm_key(name), r)
        self.find_province = find_province

    def _alias(self, th: str, en: str, key: str) -> Institution | None:
        iid = self.alias_to_id.get(key)
        if iid is None and self._alias_rx is not None:
            m = self._alias_rx.search(norm_key(f"{th} {en}"))
            iid = self.alias_to_id[m.group(0)] if m else None
        return self.insts[iid] if iid is not None else None

    def resolve(self, affiliation_th: str | None, affiliation_en: str | None, org_key: str | None) -> Institution | None:
        th, en, key = clean_text(affiliation_th), clean_text(affiliation_en), str(org_key or "")
        if not (th or en or key):
            return None
        found = self._alias(th, en, key)
        if found is not None:
            return found
        if not key:
            return None
        name = org_name(th, en)
        names = {"name_th": name, "name_en": ""} if thai_ratio(name) > 0.5 else {"name_th": "", "name_en": name}
        country = country_of(th, en)
        if country and country != "TH":
            return Institution(key=f"org:{key}", type=type_from_name(name), country=country, **names)
        for cand in (org_name(th, ""), org_name("", en)):
            r = self.ror.get(norm_key(cand)) if cand else None
            if r is not None:
                return Institution(key=f"ror:{r['id']}", name_th=r["name_th"], name_en=r["name_en"], type=r["type"],
                                   province=r["province"], country="TH", source="ror", ror=r["id"])
        province = province_finder().find(th, en) if self.find_province else None
        thai = country == "TH" or thai_ratio(th) > 0 or province is not None
        return Institution(key=f"org:{key}", type=type_from_name(name), province=province,
                           country="TH" if thai else None, **names)
```

- [ ] **Step 7: Example registry files.** Create `pipeline/registry/institutions_aliases.example.csv` (copy to `institutions_aliases.csv`, which git ignores, and extend it):

```csv
alias,inst_id,name_th,name_en,type,province,country,ror
มหาวิทยาลัยราชภัฏเชียงราย,crru,มหาวิทยาลัยราชภัฏเชียงราย,Chiang Rai Rajabhat University,rajabhat,TH-57,TH,
Chiang Rai Rajabhat University,crru,,,,,,
มรภ.เชียงราย,crru,,,,,,
มหาวิทยาลัยเทคโนโลยีราชมงคลล้านนา,rmutl,มหาวิทยาลัยเทคโนโลยีราชมงคลล้านนา,Rajamangala University of Technology Lanna,rajamangala,TH-50,TH,
Rajamangala University of Technology Lanna,rmutl,,,,,,
มทร.ล้านนา,rmutl,,,,,,
RMUTL,rmutl,,,,,,
มหาวิทยาลัยนเรศวร,nu,มหาวิทยาลัยนเรศวร,Naresuan University,university,TH-65,TH,
Naresuan University,nu,,,,,,
```

Create `pipeline/registry/province_population.example.csv` (header only — fill `province_population.csv` from the Department of Provincial Administration's civil-registration statistics; every code must be a `th_provinces.csv` code, population a positive integer):

```csv
code,population,year
```

- [ ] **Step 8: Run the tests**

Run: `uv run pytest tests/test_institutions_ref.py tests/test_config.py -q`
Expected: PASS (the config test proves every new key is documented in `config.example.yaml`).

- [ ] **Step 9: Commit**

```bash
uv run ruff check --fix .
git add atlas/config.py config.example.yaml atlas/data/th_provinces.csv atlas/places.py atlas/countries.py atlas/institutions_ref.py registry/institutions_aliases.example.csv registry/province_population.example.csv tests/test_institutions_ref.py
git commit -m "feat(institutions): P3 config, Thai provinces, country codes and the alias → ROR → as-written institution resolver

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 2: Step `institutions` → work/15_* (aggregates, network, provinces, R6)

**Files:**
- Create: `pipeline/atlas/institutions.py`, `pipeline/tests/test_institutions.py`
- Modify: `pipeline/atlas/pipeline.py`

**Interfaces:**
- Consumes: Task 1 (`Resolver`, `load_aliases`, `load_ror`, `inst_code`, `provinces`, `region_of`), P1/P2 checkpoints `01_articles`, `01_authors`, `02_docs`, `04_fine_topics`, `06_meta.json`; `atlas.orgs.org_display_names`; `tests/p2_work.make_p2_work`, `NU`, `CU`, `TOKYO`.
- Produces: step `institutions(cfg) -> DataFrame` (15_institutions); `INST_COLUMNS`; `windows(cfg, last) -> {"W": (a, b), "R": (a, b)}`; `resolve_authors(authors, resolver, display) -> (links, ident)`; `suggest(mix, coauthored, k, min_sim) -> DataFrame`; `load_population(path) -> dict | None`; checkpoints listed in the module docstring (column names are the contract with Tasks 5 and 6).

- [ ] **Step 1: Write the failing test** — create `pipeline/tests/test_institutions.py`:

```python
"""Step institutions: canonical institutions, network, provinces, R6 — aggregates only (PDPA)."""
import json
from pathlib import Path

import pandas as pd
import pytest

from atlas.institutions import institutions, suggest
from atlas.io_utils import read_table, write_table
from atlas.orgs import org_key
from atlas.pipeline import STEPS
from tests.p2_work import CU, TOKYO, make_p2_work

PEOPLE = ("สมชาย ใจดี", "สุดา ศรีสุข")


def _work(tmp_path):
    """p2 work + an alias for Naresuan, Chula co-authors on six J1 articles of 2020+, one Tokyo co-author in W."""
    cfg = make_p2_work(tmp_path)
    work = Path(cfg["pipeline"]["work_dir"])
    aliases = tmp_path / "aliases.csv"
    aliases.write_text("alias,inst_id,name_th,name_en,type,province\n"
                       "มหาวิทยาลัยนเรศวร,nu,มหาวิทยาลัยนเรศวร,Naresuan University,university,TH-65\n", encoding="utf-8")
    cfg["institutions"]["aliases_path"] = str(aliases)
    arts = read_table(work / "01_articles.parquet")
    recent = arts[(arts["journal_name"] == "J1") & (arts["year"] >= 2020)]["article_id"].tolist()
    extra = [{"article_id": a, "position": 5, "affiliation_th": CU, "affiliation_en": "", "org_key": org_key(CU, "")}
             for a in recent[:6]]
    extra.append({"article_id": recent[0], "position": 6, "affiliation_th": "", "affiliation_en": TOKYO,
                  "org_key": org_key("", TOKYO)})
    authors = read_table(work / "01_authors.parquet").assign(name=PEOPLE[0])
    write_table(pd.concat([authors, pd.DataFrame(extra).assign(name=PEOPLE[1])], ignore_index=True),
                work / "01_authors.parquet")
    return cfg, work


def test_institutions_resolve_publish_pair_and_place(tmp_path):
    cfg, work = _work(tmp_path)
    inst = institutions(cfg).set_index("inst_key")
    nu = inst.loc["alias:nu"]
    assert nu["province"] == "TH-65" and nu["source"] == "alias" and bool(nu["published"]) and nu["code"] == "nu"
    tokyo = inst.loc[f"org:{org_key('', TOKYO)}"]
    assert tokyo["country"] == "JP" and not bool(tokyo["published"])          # 1 article in W < min_articles
    pairs = read_table(work / "15_inst_pairs.parquet")
    assert len(pairs) == 1 and set(pairs.iloc[0][["a", "b"]]) == {"alias:nu", f"org:{org_key(CU, '')}"}
    assert pairs.iloc[0]["articles"] >= cfg["institutions"]["network_min_articles"]
    meta = json.loads((work / "15_institutions_meta.json").read_text(encoding="utf-8"))
    assert meta["with_org"] == 56 and meta["pct_international"] == pytest.approx(1 / 56, abs=1e-6)
    assert meta["institutions_total"] == len(inst) and meta["windows"]["W"] == [2020, 2024]
    prov = read_table(work / "15_provinces.parquet").set_index("code")
    assert prov.loc["TH-65", "articles"] == nu["articles"] and "TH-10" not in prov.index
    countries = read_table(work / "15_inst_countries.parquet")
    assert countries[countries["inst_key"] == ""].set_index("country")["articles"].to_dict() == {"JP": 1}
    assert STEPS.index("match") < STEPS.index("institutions") < STEPS.index("export")


def test_no_person_column_and_small_units_stay_internal(tmp_path):
    cfg, work = _work(tmp_path)
    institutions(cfg)
    tokyo = f"org:{org_key('', TOKYO)}"
    for p in work.glob("15_*"):
        if p.suffix == ".json":
            blob = p.read_text(encoding="utf-8")
        else:
            table = read_table(p.with_suffix(".parquet"))
            assert not {"name", "position", "role", "is_student"} & set(table.columns), p.name
            blob = table.astype(str).to_csv()
            if p.stem != "15_institutions" and p.stem != "15_article_institutions":
                assert tokyo not in blob, p.name                       # unpublished: in totals only
        assert not any(person in blob for person in PEOPLE), p.name


def test_suggestions_skip_partners_and_need_similar_topics():
    mix = pd.DataFrame({"inst_key": ["a", "a", "b", "b", "c", "d"], "topic_id": [1, 2, 1, 2, 1, 3],
                        "count": [5, 5, 4, 6, 9, 9], "share": [0.5, 0.5, 0.4, 0.6, 1.0, 1.0]})
    out = suggest(mix, coauthored={("a", "b")}, k=2, min_sim=0.3)
    got = {(r.inst_key, r.other_key) for r in out.itertuples()}
    assert ("a", "b") not in got and ("a", "c") in got and ("a", "d") not in got   # partners and unrelated skipped
    assert out.set_index(["inst_key", "other_key"]).loc[("a", "c"), "topics"] == "1"
```

Run: `uv run pytest tests/test_institutions.py -q` — Expected: FAIL (`No module named 'atlas.institutions'`).

- [ ] **Step 2: The step.** Create `pipeline/atlas/institutions.py`:

```python
"""Step `institutions` (after match): institutions, collaboration and provinces → work/15_* (export publishes them).

Every author row is resolved to a canonical institution (atlas.institutions_ref); an article counts once for each
institution among its authors (full counting). W = the last institutions.window_years complete years (06_meta.json
last_complete_year), R = the emerging recent window.

  15_article_institutions   article_id, inst_key — distinct pairs, all years (internal: gaps and export read it)
  15_institutions           one row per institution: inst_key, code, name_th, name_en, type, province, country,
                            source, ror, articles (W), articles_total, articles_recent (R), intl_share (W: share of its
                            articles that pair Thai and foreign institutions), partners (published co-authors in W),
                            topics (W), published (≥ institutions.min_articles in W)
  15_inst_years             inst_key, year, articles (published institutions)
  15_inst_topics            inst_key, topic_id, count, share (W, published institutions)
  15_inst_pairs             a, b, articles — co-authored articles in W between published institutions,
                            ≥ network_min_articles, the network_max_edges largest
  15_inst_countries         inst_key ("" = the whole corpus), country, articles — articles in W pairing a Thai (or
                            unplaced) institution with one in that foreign country (published institutions only)
  15_inst_suggest           inst_key, other_key, similarity, topics ("1;7;9") — R6: published institutions with the
                            most similar topic mix (cosine ≥ suggest_min_similarity) and no co-authored article in W
  15_provinces              code, articles, articles_recent, institutions — articles with ≥ 1 author placed in the
                            province (once per province), published institutions placed there
  15_regions                region, articles
  15_institutions_meta.json windows, coverage, KPI shares, sources, population
Author rows are read for their affiliations only — the name columns are dropped on read (PDPA).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.institutions_ref import Institution, Resolver, inst_code, load_aliases, load_ror
from atlas.io_utils import read_table, write_table
from atlas.orgs import org_display_names
from atlas.places import provinces, region_of
from atlas.thai import thai_ratio

INST_COLUMNS = ["inst_key", "code", "name_th", "name_en", "type", "province", "country", "source", "ror",
                "articles", "articles_total", "articles_recent", "intl_share", "partners", "topics", "published"]
AUTHOR_COLUMNS = ["article_id", "affiliation_th", "affiliation_en", "org_key"]
IDENT_COLUMNS = ["name_th", "name_en", "type", "province", "country", "source", "ror"]


def windows(cfg: dict, last: int) -> dict[str, tuple[int, int]]:
    r0 = last - int(cfg["emerging"]["recent_window"]) + 1
    return {"W": (last - int(cfg["institutions"]["window_years"]) + 1, last), "R": (r0, last)}


def _in(years: pd.Series, span: tuple[int, int]) -> pd.Series:
    return years.between(*span).fillna(False).astype(bool)


def _text(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].fillna("").astype(str) if col in df.columns else pd.Series("", index=df.index, dtype=str)


def _given(v) -> bool:
    return isinstance(v, str) and v != ""


def _mode(s: pd.Series):
    """Most frequent non-empty value (ties: alphabetically first); None when there is none."""
    s = s[s.map(_given)]
    if s.empty:
        return None
    vc = s.value_counts()
    return sorted(vc[vc == vc.max()].index)[0]


def resolve_authors(authors: pd.DataFrame, resolver: Resolver, display: dict[str, str]
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(article_id, inst_key) distinct, and one identity row per inst_key. Each distinct affiliation is resolved once;
    an institution's province and country are the most frequent among its author rows; an institution known only as
    written takes the P1 display name of its org_key (most frequent written form)."""
    a = pd.DataFrame({"article_id": authors["article_id"], "th": _text(authors, "affiliation_th"),
                      "en": _text(authors, "affiliation_en"), "org_key": _text(authors, "org_key")})
    trip = a[["th", "en", "org_key"]].drop_duplicates().reset_index(drop=True)
    found: list[Institution | None] = [resolver.resolve(t, e, k) for t, e, k in zip(trip["th"], trip["en"], trip["org_key"])]
    res = pd.DataFrame([asdict(f) if f is not None else {"key": ""} for f in found],
                       columns=["key", *IDENT_COLUMNS]).rename(columns={"key": "inst_key"})
    rows = a.merge(pd.concat([trip, res], axis=1), on=["th", "en", "org_key"], how="left")
    rows = rows[rows["inst_key"].map(_given)]
    links = rows[["article_id", "inst_key"]].drop_duplicates().reset_index(drop=True)
    ident = rows.groupby("inst_key").agg(
        name_th=("name_th", "first"), name_en=("name_en", "first"), type=("type", "first"),
        province=("province", _mode), country=("country", _mode), source=("source", "first"), ror=("ror", "first"),
        org_key=("org_key", "first")).reset_index()
    th_out, en_out = [], []
    for k, th, en, src in zip(ident["org_key"], ident["name_th"].fillna(""), ident["name_en"].fillna(""),
                              ident["source"]):
        if src == "name":
            shown = display.get(k) or th or en
            th, en = (shown, "") if thai_ratio(shown) > 0.5 else ("", shown)
        th_out.append(str(th))
        en_out.append(str(en))
    ident["name_th"], ident["name_en"] = th_out, en_out
    ident["country"] = [c if _given(c) else ("TH" if _given(p) else None)
                        for c, p in zip(ident["country"], ident["province"])]
    ident["province"] = [p if _given(p) else None for p in ident["province"]]
    ident["ror"] = ident["ror"].fillna("").astype(str)
    return links, ident.drop(columns=["org_key"])


def suggest(mix: pd.DataFrame, coauthored: set[tuple[str, str]], k: int, min_sim: float, chunk: int = 512
            ) -> pd.DataFrame:
    """R6 — for each institution of `mix` (inst_key, topic_id, share) the k most similar others (cosine of topic
    shares ≥ min_sim) that it has not co-authored with; topics = up to 3 topics both work on (largest common share)."""
    cols = ["inst_key", "other_key", "similarity", "topics"]
    if mix.empty or k == 0:
        return pd.DataFrame(columns=cols)
    insts = sorted(mix["inst_key"].unique())
    topics = sorted(mix["topic_id"].unique())
    ii, ti = {x: i for i, x in enumerate(insts)}, {t: i for i, t in enumerate(topics)}
    m = np.zeros((len(insts), len(topics)))
    m[mix["inst_key"].map(ii).to_numpy(), mix["topic_id"].map(ti).to_numpy()] = mix["share"].to_numpy(dtype=float)
    unit = m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)
    rows = []
    for s in range(0, len(insts), chunk):
        sim = unit[s:s + chunk] @ unit.T
        for r, i in enumerate(range(s, min(s + chunk, len(insts)))):
            sim[r, i] = -1.0
            picked = 0
            for j in np.argsort(-sim[r], kind="stable"):
                if picked >= k or sim[r, j] < min_sim:
                    break
                a, b = insts[i], insts[j]
                if (min(a, b), max(a, b)) in coauthored:
                    continue
                common = np.minimum(m[i], m[j])
                shared = [topics[t] for t in np.argsort(-common, kind="stable")[:3] if common[t] > 0]
                rows.append({"inst_key": a, "other_key": b, "similarity": round(float(sim[r, j]), 4),
                             "topics": ";".join(str(int(t)) for t in shared)})
                picked += 1
    return pd.DataFrame(rows, columns=cols)


def load_population(path: str | Path | None) -> dict | None:
    """{"year": int | None, "by_code": {province code: population}} from registry/province_population.csv, or None."""
    if not path or not Path(path).exists():
        return None
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    known, by, years = provinces(), {}, set()
    for n, r in enumerate(df.to_dict("records"), start=2):
        code = str(r.get("code", "")).strip().upper()
        if code not in known:
            raise ValueError(f"{path} row {n}: {code!r} is not a province code of atlas/data/th_provinces.csv")
        pop = int(str(r.get("population", "")).replace(",", "").strip() or 0)
        if pop <= 0:
            raise ValueError(f"{path} row {n}: population must be a positive whole number")
        by[code] = pop
        if str(r.get("year", "")).strip():
            years.add(int(r["year"]))
    return {"year": max(years) if years else None, "by_code": by} if by else None


def institutions(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    icfg = cfg["institutions"]
    for stale in work.glob("15_*"):          # a re-run that stops half-way must not leave the old release's tables
        stale.unlink()
    if not icfg["enabled"]:
        print("[institutions] institutions.enabled is false — no institutions module")
        return pd.DataFrame(columns=INST_COLUMNS)
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    win = windows(cfg, last)
    W, R = win["W"], win["R"]
    arts = read_table(work / "01_articles.parquet")[["article_id", "year"]]
    arts = arts.assign(year=pd.to_numeric(arts["year"], errors="coerce"))
    try:
        authors = read_table(work / "01_authors.parquet")
    except FileNotFoundError:
        authors = pd.DataFrame(columns=AUTHOR_COLUMNS)
    authors = authors[[c for c in AUTHOR_COLUMNS if c in authors.columns]]      # affiliations only — never a name
    ror = load_ror(icfg["ror_path"], cfg["taxonomy"]["openalex"]["country_code"],
                   Path(cfg["pipeline"]["state_dir"]) / "ror")
    resolver = Resolver(load_aliases(icfg["aliases_path"], int(icfg["alias_min_chars"])), ror,
                        bool(icfg["province_from_name"]))
    links, ident = resolve_authors(authors, resolver, org_display_names(authors))
    links = links.merge(arts, on="article_id", how="inner")

    # ---- counts, publication rule, international collaboration
    country = ident.set_index("inst_key")["country"]
    lw = links[_in(links["year"], W)].copy()
    lw["foreign"] = lw["inst_key"].map(country).map(lambda c: _given(c) and c != "TH").astype(bool)
    per_w = lw.groupby("inst_key")["article_id"].nunique()
    per_r = links[_in(links["year"], R)].groupby("inst_key")["article_id"].nunique()
    per_all = links.groupby("inst_key")["article_id"].nunique()
    published = set(per_w[per_w >= int(icfg["min_articles"])].index)
    intl = set(lw.loc[lw["foreign"], "article_id"]) & set(lw.loc[~lw["foreign"], "article_id"])
    lw["intl"] = lw["article_id"].isin(intl).astype(bool)
    with_org = int(lw["article_id"].nunique())
    multi = int((lw.groupby("article_id")["inst_key"].nunique() >= 2).sum())

    # ---- network among published institutions
    pw = lw.loc[lw["inst_key"].isin(published), ["article_id", "inst_key"]]
    both = pw.merge(pw, on="article_id")
    both = both[both["inst_key_x"] < both["inst_key_y"]]
    pairs = (both.groupby(["inst_key_x", "inst_key_y"]).size().rename("articles").reset_index()
             .rename(columns={"inst_key_x": "a", "inst_key_y": "b"}))
    partners = pd.concat([pairs["a"], pairs["b"]]).value_counts()
    edges = (pairs[pairs["articles"] >= int(icfg["network_min_articles"])]
             .sort_values(["articles", "a", "b"], ascending=[False, True, True]).head(int(icfg["network_max_edges"])))

    # ---- topics (W) and R6 suggestions
    docs = read_table(work / "02_docs.parquet")[["article_id"]]
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    topic_of = docs.merge(fine, on="article_id").rename(columns={"fine_topic": "topic_id"})
    topic_of = topic_of[topic_of["topic_id"].fillna(-1).astype(int) >= 0].astype({"topic_id": int})
    lwt = lw[["article_id", "inst_key"]].merge(topic_of, on="article_id")
    n_topics = lwt.groupby("inst_key")["topic_id"].nunique()
    mix = lwt[lwt["inst_key"].isin(published)].groupby(["inst_key", "topic_id"]).size().rename("count").reset_index()
    mix["share"] = mix["count"] / mix.groupby("inst_key")["count"].transform("sum")
    mix = mix.sort_values(["inst_key", "count", "topic_id"], ascending=[True, False, True]).reset_index(drop=True)
    coauthored = set(zip(pairs["a"], pairs["b"]))
    sugg = suggest(mix, coauthored, int(icfg["suggest_k"]), float(icfg["suggest_min_similarity"]))

    # ---- years and partner countries
    dated = links[links["inst_key"].isin(published) & links["year"].notna() & (links["year"] <= last)]
    years = dated.astype({"year": int}).groupby(["inst_key", "year"]).size().rename("articles").reset_index()
    foreign_side = lw.loc[lw["intl"] & lw["foreign"], ["article_id", "inst_key"]]
    foreign_side = foreign_side.assign(country=foreign_side["inst_key"].map(country))[["article_id", "country"]]
    foreign_side = foreign_side.drop_duplicates()
    national = foreign_side.groupby("country").size().rename("articles").reset_index().assign(inst_key="")
    home = lw.loc[lw["intl"] & ~lw["foreign"] & lw["inst_key"].isin(published), ["article_id", "inst_key"]]
    per_inst = (home.merge(foreign_side, on="article_id").drop_duplicates(["inst_key", "article_id", "country"])
                .groupby(["inst_key", "country"]).size().rename("articles").reset_index()
                .sort_values(["inst_key", "articles", "country"], ascending=[True, False, True])
                .groupby("inst_key").head(int(icfg["max_partners"])))
    countries = pd.concat([national, per_inst], ignore_index=True)[["inst_key", "country", "articles"]]

    # ---- provinces and regions (articles once per province of their authors)
    placed = links.assign(province=links["inst_key"].map(ident.set_index("inst_key")["province"]))
    placed = placed[placed["province"].map(_given)]
    pwy = placed[_in(placed["year"], W)][["article_id", "province"]].drop_duplicates()
    pry = placed[_in(placed["year"], R)][["article_id", "province"]].drop_duplicates()
    pub = ident[ident["inst_key"].isin(published) & ident["province"].map(_given)]
    prov = pd.DataFrame({"articles": pwy.groupby("province").size(), "articles_recent": pry.groupby("province").size(),
                         "institutions": pub.groupby("province").size()}).fillna(0).astype(int)
    prov = prov.rename_axis("code").reset_index().sort_values("code")
    regions = (pwy.assign(region=pwy["province"].map(region_of))[["article_id", "region"]].drop_duplicates()
               .groupby("region").size().rename("articles").reset_index())

    # ---- the institutions table
    intl_share = lw.groupby("inst_key")["intl"].mean()
    out = ident.assign(
        code=ident["inst_key"].map(inst_code), articles=ident["inst_key"].map(per_w).fillna(0).astype(int),
        articles_total=ident["inst_key"].map(per_all).fillna(0).astype(int),
        articles_recent=ident["inst_key"].map(per_r).fillna(0).astype(int),
        intl_share=ident["inst_key"].map(intl_share).astype(float),
        partners=ident["inst_key"].map(partners).fillna(0).astype(int),
        topics=ident["inst_key"].map(n_topics).fillna(0).astype(int),
        published=ident["inst_key"].isin(published))[INST_COLUMNS]

    write_table(links[["article_id", "inst_key"]], work / "15_article_institutions.parquet")
    write_table(out, work / "15_institutions.parquet")
    write_table(years, work / "15_inst_years.parquet")
    write_table(mix, work / "15_inst_topics.parquet")
    write_table(edges.reset_index(drop=True), work / "15_inst_pairs.parquet")
    write_table(countries, work / "15_inst_countries.parquet")
    write_table(sugg, work / "15_inst_suggest.parquet")
    write_table(prov, work / "15_provinces.parquet")
    write_table(regions, work / "15_regions.parquet")
    meta = {
        "windows": {k: list(v) for k, v in win.items()}, "articles_window": int(_in(arts["year"], W).sum()),
        "with_org": with_org, "located": int(pwy["article_id"].nunique()),
        "pct_international": round(len(intl) / with_org, 6) if with_org else None,
        "pct_multi_institution": round(multi / with_org, 6) if with_org else None,
        "institutions_total": int(len(ident)), "published": len(published),
        "sources": {str(k): int(v) for k, v in out.loc[out["published"], "source"].value_counts().items()},
        "aliases": len(resolver.alias_to_id), "ror_records": len(ror),
        "population": load_population(icfg["population_path"]),
    }
    (work / "15_institutions_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[institutions] {len(ident):,} institutions ({len(published):,} with ≥ {icfg['min_articles']} articles in "
          f"{W[0]}–{W[1]}); {len(edges):,} partnerships; {meta['located']:,} of {with_org:,} articles placed in a province")
    return out
```

In `pipeline/atlas/pipeline.py` replace `         "forecast", "narrate", "layout", "methods", "journals", "match", "export"]` with

```python
         "forecast", "narrate", "layout", "methods", "journals", "match", "institutions", "export"]
```

and below `    "match": ("atlas.matcher", "match"),` insert `    "institutions": ("atlas.institutions", "institutions"),`.

- [ ] **Step 3: Run the tests**

Run: `uv run pytest tests/test_institutions.py tests/test_institutions_ref.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
uv run ruff check --fix .
git add atlas/institutions.py atlas/pipeline.py tests/test_institutions.py
git commit -m "feat(institutions): step institutions — canonical institutions, network, partner countries, provinces, R6 suggestions (aggregates only)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 3: SDG + Thai frameworks — `frameworks.yaml` and step `sdg` → work/16_*

**Files:**
- Create: `pipeline/atlas/data/frameworks.yaml`, `pipeline/atlas/sdg.py`, `pipeline/tests/test_sdg.py`
- Modify: `pipeline/atlas/pipeline.py`

**Interfaces:**
- Consumes: Task 1 config `sdg.*`; `atlas.matcher.match_fold` (P2); `atlas.embed.embed_texts(cfg, texts, embedder=None)` (P1); checkpoints `02_docs`, `04_fine_topics`, `04_centroids.npy` + `04_centroid_ids.json`.
- Produces: `load_frameworks(path=None) -> dict` (adds `sha1`), `FrameworkError`, `goal_patterns(goals) -> {goal_id: re.Pattern}`, `lexical_scores(texts, patterns) -> DataFrame[topic_id, goal_id, score]`, `similarity_scores(C, topic_ids, G, goal_ids) -> same`, `pick(scores, goal_framework, threshold, k) -> DataFrame[topic_id, framework, goal_id, score]`, step `sdg(cfg, embedder=None)`; `16_topic_goals`, `16_sdg_meta.json` = `{method, version, frameworks: [{key, th, en, goals: [{id, number, th, en}]}]}`.

- [ ] **Step 1: Write the failing test** — create `pipeline/tests/test_sdg.py`:

```python
"""SDG + Thai frameworks at topic level: packaged goals, lexical mapping, cosine mapping (no network)."""
import json
from pathlib import Path

import numpy as np
import pytest

from atlas.pipeline import STEPS
from atlas.sdg import FrameworkError, goal_patterns, load_frameworks, pick, sdg, similarity_scores
from tests.p2_work import make_p2_work


def test_packaged_frameworks_are_complete():
    fw = load_frameworks()
    assert [f["key"] for f in fw["frameworks"]] == ["sdg", "bcg", "hesi", "nesdp13"]
    assert {f["key"]: len(f["goals"]) for f in fw["frameworks"]} == {"sdg": 17, "bcg": 3, "hesi": 4, "nesdp13": 13}
    assert [g["number"] for g in fw["frameworks"][0]["goals"]] == list(range(1, 18))


def test_a_bad_frameworks_file_is_refused(tmp_path):
    p = tmp_path / "f.yaml"
    p.write_text("frameworks:\n- {key: x, th: x, en: x, goals: [{id: a1, number: 1, th: a, en: a, keywords: []}]}\n",
                 encoding="utf-8")
    with pytest.raises(FrameworkError, match="keywords"):
        load_frameworks(p)


def test_latin_keywords_are_whole_words_and_thai_ones_text():
    rx = goal_patterns([{"id": "g", "keywords": ["aging", "การเรียนรู้"]}])["g"]
    assert rx.search("healthy aging") and not rx.search("managing staff") and rx.search("ชุมชนแห่งการเรียนรู")


def test_lexical_mapping_on_titles_and_keywords(tmp_path):
    cfg = make_p2_work(tmp_path)                       # provider "local" but no centroids → auto = lexical
    out = sdg(cfg)
    pairs = set(zip(out["topic_id"], out["goal_id"]))
    assert {(3, "sdg-04"), (1, "sdg-08"), (1, "nesdp13-02"), (2, "nesdp13-06")} <= pairs
    assert (2, "sdg-04") not in pairs
    assert out.groupby(["topic_id", "framework"]).size().max() <= cfg["sdg"]["max_goals_per_topic"]
    meta = json.loads((Path(cfg["pipeline"]["work_dir"]) / "16_sdg_meta.json").read_text(encoding="utf-8"))
    assert meta["method"] == "lexical" and meta["frameworks"][0]["goals"][3]["id"] == "sdg-04"
    assert STEPS.index("institutions") < STEPS.index("sdg") < STEPS.index("export")


def test_similarity_scores_rank_goals_by_cosine():
    s = similarity_scores(np.array([[1.0, 0.0], [0.0, 2.0]]), [7, 8], np.array([[0.9, 0.1], [0.1, 0.9]]),
                          ["sdg-01", "sdg-02"])
    top = pick(s, {"sdg-01": "sdg", "sdg-02": "sdg"}, 0.5, 1)
    assert list(zip(top["topic_id"], top["goal_id"])) == [(7, "sdg-01"), (8, "sdg-02")]
```

Run: `uv run pytest tests/test_sdg.py -q` — Expected: FAIL (`No module named 'atlas.sdg'`).

- [ ] **Step 2: The goals.** Create `pipeline/atlas/data/frameworks.yaml`:

```yaml
# Goals and keywords for the topic-level mapping of atlas/sdg.py (P3, E8). Curated and editable by the maintainers:
# keywords are matched in article titles and keywords (Thai as text, Latin words as whole words, tone marks ignored);
# avoid words that are also common in other senses (e.g. การศึกษา also means "a study of", เมือง is in การเมือง).
# Names follow the official titles; check them against the source documents before a public release:
#   SDGs — United Nations, https://sdgs.un.org/goals (Thai names as used by สศช.)
#   BCG Model — โมเดลเศรษฐกิจ BCG (เศรษฐกิจชีวภาพ · เศรษฐกิจหมุนเวียน · เศรษฐกิจสีเขียว)
#   แผนด้านการอุดมศึกษา วิทยาศาสตร์ วิจัยและนวัตกรรม พ.ศ. 2566–2570 — 4 แพลตฟอร์ม
#   แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ ฉบับที่ 13 (พ.ศ. 2566–2570) — 13 หมุดหมาย
version: 1
frameworks:
  - key: sdg
    th: "เป้าหมายการพัฒนาที่ยั่งยืน (SDGs)"
    en: "Sustainable Development Goals"
    goals:
      - {id: sdg-01, number: 1, th: "ขจัดความยากจน", en: "No poverty", keywords: [ความยากจน, คนจน, ผู้มีรายได้น้อย, หนี้ครัวเรือน, สวัสดิการสังคม, poverty, low-income, household debt, social welfare, social protection]}
      - {id: sdg-02, number: 2, th: "ขจัดความหิวโหย", en: "Zero hunger", keywords: [ความมั่นคงทางอาหาร, ภาวะทุพโภชนาการ, เกษตรกร, ผลผลิตทางการเกษตร, การปลูกข้าว, food security, malnutrition, farmers, crop yield, agriculture]}
      - {id: sdg-03, number: 3, th: "สุขภาพและความเป็นอยู่ที่ดี", en: "Good health and well-being", keywords: [สุขภาพ, ผู้ป่วย, โรงพยาบาล, สาธารณสุข, การพยาบาล, โรคเรื้อรัง, health, patients, nursing, public health, disease, mortality]}
      - {id: sdg-04, number: 4, th: "การศึกษาที่มีคุณภาพ", en: "Quality education", keywords: [การเรียนการสอน, การเรียนรู้, นักเรียน, ผู้เรียน, หลักสูตร, สถานศึกษา, ครู, education, learning, students, teachers, curriculum, school]}
      - {id: sdg-05, number: 5, th: "ความเท่าเทียมทางเพศ", en: "Gender equality", keywords: [ความเท่าเทียมทางเพศ, สตรี, ผู้หญิง, เพศสภาพ, ความรุนแรงในครอบครัว, gender, women, female, domestic violence, LGBT]}
      - {id: sdg-06, number: 6, th: "น้ำสะอาดและการสุขาภิบาล", en: "Clean water and sanitation", keywords: [น้ำดื่ม, น้ำเสีย, คุณภาพน้ำ, การสุขาภิบาล, ทรัพยากรน้ำ, drinking water, wastewater, water quality, sanitation, water resources]}
      - {id: sdg-07, number: 7, th: "พลังงานสะอาดที่เข้าถึงได้", en: "Affordable and clean energy", keywords: [พลังงานทดแทน, พลังงานแสงอาทิตย์, เซลล์แสงอาทิตย์, ชีวมวล, การอนุรักษ์พลังงาน, renewable energy, solar, biomass, energy efficiency, electricity]}
      - {id: sdg-08, number: 8, th: "งานที่มีคุณค่าและการเติบโตทางเศรษฐกิจ", en: "Decent work and economic growth", keywords: [การจ้างงาน, แรงงาน, การเติบโตทางเศรษฐกิจ, ผู้ประกอบการ, การท่องเที่ยว, employment, labour, labor, economic growth, entrepreneurship, tourism]}
      - {id: sdg-09, number: 9, th: "อุตสาหกรรม นวัตกรรม และโครงสร้างพื้นฐาน", en: "Industry, innovation and infrastructure", keywords: [นวัตกรรม, อุตสาหกรรม, โครงสร้างพื้นฐาน, การผลิต, เทคโนโลยีดิจิทัล, innovation, industry, infrastructure, manufacturing, digital technology]}
      - {id: sdg-10, number: 10, th: "ลดความเหลื่อมล้ำ", en: "Reduced inequalities", keywords: [ความเหลื่อมล้ำ, ความไม่เท่าเทียม, แรงงานข้ามชาติ, คนพิการ, ผู้พิการ, กลุ่มเปราะบาง, inequality, migrant workers, disability, vulnerable groups, social inclusion]}
      - {id: sdg-11, number: 11, th: "เมืองและชุมชนที่ยั่งยืน", en: "Sustainable cities and communities", keywords: [ชุมชนเมือง, ผังเมือง, การพัฒนาเมือง, ที่อยู่อาศัย, การขนส่งสาธารณะ, มรดกทางวัฒนธรรม, urban, housing, public transport, urban planning, cultural heritage, smart city]}
      - {id: sdg-12, number: 12, th: "การผลิตและการบริโภคที่ยั่งยืน", en: "Responsible consumption and production", keywords: [การบริโภคอย่างยั่งยืน, ขยะ, การรีไซเคิล, ขยะอาหาร, ห่วงโซ่อุปทานสีเขียว, sustainable consumption, waste, recycling, food waste, green supply chain]}
      - {id: sdg-13, number: 13, th: "การรับมือการเปลี่ยนแปลงสภาพภูมิอากาศ", en: "Climate action", keywords: [การเปลี่ยนแปลงสภาพภูมิอากาศ, ภาวะโลกร้อน, ก๊าซเรือนกระจก, การปล่อยคาร์บอน, climate change, global warming, greenhouse gas, carbon emissions, climate adaptation]}
      - {id: sdg-14, number: 14, th: "ทรัพยากรทางทะเล", en: "Life below water", keywords: [ทะเล, ชายฝั่ง, ปะการัง, การประมง, ไมโครพลาสติก, ทรัพยากรทางทะเล, marine, coastal, coral, fisheries, microplastics]}
      - {id: sdg-15, number: 15, th: "ระบบนิเวศบนบก", en: "Life on land", keywords: [ป่าไม้, ป่าชุมชน, ความหลากหลายทางชีวภาพ, สัตว์ป่า, การใช้ที่ดิน, ระบบนิเวศ, forest, biodiversity, wildlife, land use, ecosystem]}
      - {id: sdg-16, number: 16, th: "สันติภาพ ความยุติธรรม และสถาบันที่เข้มแข็ง", en: "Peace, justice and strong institutions", keywords: [กฎหมาย, กระบวนการยุติธรรม, การทุจริต, ธรรมาภิบาล, สิทธิมนุษยชน, การเมือง, law, justice, corruption, governance, human rights]}
      - {id: sdg-17, number: 17, th: "ความร่วมมือเพื่อการพัฒนาที่ยั่งยืน", en: "Partnerships for the goals", keywords: [ความร่วมมือระหว่างประเทศ, การค้าระหว่างประเทศ, อาเซียน, ภาคีเครือข่าย, international cooperation, international trade, ASEAN, partnership]}
  - key: bcg
    th: "โมเดลเศรษฐกิจ BCG"
    en: "BCG economy model"
    goals:
      - {id: bcg-bio, number: 1, th: "เศรษฐกิจชีวภาพ", en: "Bio-economy", keywords: [เศรษฐกิจชีวภาพ, เทคโนโลยีชีวภาพ, สมุนไพร, จุลินทรีย์, อาหารเพื่อสุขภาพ, bioeconomy, biotechnology, herbal, microbial, functional food]}
      - {id: bcg-circular, number: 2, th: "เศรษฐกิจหมุนเวียน", en: "Circular economy", keywords: [เศรษฐกิจหมุนเวียน, ขยะ, การรีไซเคิล, การใช้ซ้ำ, วัสดุเหลือใช้, circular economy, recycling, waste, upcycling, by-product]}
      - {id: bcg-green, number: 3, th: "เศรษฐกิจสีเขียว", en: "Green economy", keywords: [เศรษฐกิจสีเขียว, พลังงานทดแทน, การท่องเที่ยวเชิงนิเวศ, คาร์บอนต่ำ, สิ่งแวดล้อม, green economy, renewable energy, ecotourism, low carbon, environment]}
  - key: hesi
    th: "แผนด้าน ววน. พ.ศ. 2566–2570"
    en: "Higher education, science, research and innovation plan 2023–2027"
    goals:
      - {id: hesi-1, number: 1, th: "การพัฒนากำลังคนและสถาบันความรู้", en: "Workforce and knowledge institutions", keywords: [กำลังคน, การพัฒนาบุคลากร, ทักษะ, อุดมศึกษา, สถาบันอุดมศึกษา, workforce, human resource development, skills, higher education, upskilling]}
      - {id: hesi-2, number: 2, th: "การวิจัยและนวัตกรรมเพื่อตอบโจทย์ท้าทายของสังคม", en: "Research and innovation for societal challenges", keywords: [สังคมสูงวัย, ผู้สูงอายุ, คุณภาพชีวิต, ภัยพิบัติ, สาธารณสุข, ageing society, older adults, quality of life, disaster, public health]}
      - {id: hesi-3, number: 3, th: "การวิจัยและนวัตกรรมเพื่อเพิ่มขีดความสามารถในการแข่งขัน", en: "Research and innovation for competitiveness", keywords: [ขีดความสามารถในการแข่งขัน, นวัตกรรม, อุตสาหกรรม, ผู้ประกอบการ, สตาร์ทอัพ, competitiveness, innovation, industry, entrepreneurs, startup]}
      - {id: hesi-4, number: 4, th: "การวิจัยและนวัตกรรมเพื่อการพัฒนาเชิงพื้นที่และลดความเหลื่อมล้ำ", en: "Research and innovation for area development and less inequality", keywords: [ชุมชน, ท้องถิ่น, เศรษฐกิจฐานราก, วิสาหกิจชุมชน, ความเหลื่อมล้ำ, community, local development, grassroots economy, community enterprise, rural development]}
  - key: nesdp13
    th: "หมุดหมายแผนพัฒนาฯ ฉบับที่ 13"
    en: "Milestones of the 13th National Economic and Social Development Plan"
    goals:
      - {id: nesdp13-01, number: 1, th: "ไทยเป็นประเทศชั้นนำด้านสินค้าเกษตรและเกษตรแปรรูปมูลค่าสูง", en: "High-value agricultural and processed agricultural products", keywords: [เกษตรแปรรูป, ผลิตภัณฑ์เกษตร, เกษตรอัจฉริยะ, มูลค่าเพิ่ม, agro-processing, agricultural products, smart farming, value added]}
      - {id: nesdp13-02, number: 2, th: "ไทยเป็นจุดหมายของการท่องเที่ยวที่เน้นคุณภาพและความยั่งยืน", en: "Quality and sustainable tourism", keywords: [การท่องเที่ยว, นักท่องเที่ยว, ท่องเที่ยวโดยชุมชน, การท่องเที่ยวอย่างยั่งยืน, tourism, tourists, community-based tourism, sustainable tourism]}
      - {id: nesdp13-03, number: 3, th: "ไทยเป็นฐานการผลิตยานยนต์ไฟฟ้าที่สำคัญของโลก", en: "A global production base for electric vehicles", keywords: [ยานยนต์ไฟฟ้า, รถยนต์ไฟฟ้า, แบตเตอรี่, สถานีอัดประจุ, electric vehicle, electric vehicles, EV, battery, charging station]}
      - {id: nesdp13-04, number: 4, th: "ไทยเป็นศูนย์กลางทางการแพทย์และสุขภาพมูลค่าสูง", en: "A high-value medical and health hub", keywords: [การแพทย์, ท่องเที่ยวเชิงสุขภาพ, อุปกรณ์การแพทย์, เวชภัณฑ์, medical, health tourism, wellness, medical devices, pharmaceutical]}
      - {id: nesdp13-05, number: 5, th: "ไทยเป็นประตูการค้าการลงทุนและยุทธศาสตร์ทางโลจิสติกส์ที่สำคัญของภูมิภาค", en: "A regional gateway for trade, investment and logistics", keywords: [โลจิสติกส์, การค้าระหว่างประเทศ, การลงทุน, โซ่อุปทาน, ห่วงโซ่อุปทาน, ระเบียงเศรษฐกิจพิเศษภาคตะวันออก, logistics, international trade, investment, supply chain]}
      - {id: nesdp13-06, number: 6, th: "ไทยเป็นฐานการผลิตอุปกรณ์อิเล็กทรอนิกส์อัจฉริยะและอุตสาหกรรมดิจิทัลของอาเซียน", en: "ASEAN's base for smart electronics and the digital industry", keywords: [ดิจิทัล, อิเล็กทรอนิกส์, ปัญญาประดิษฐ์, อินเทอร์เน็ตของสรรพสิ่ง, ซอฟต์แวร์, digital, electronics, artificial intelligence, internet of things, software]}
      - {id: nesdp13-07, number: 7, th: "ไทยมีวิสาหกิจขนาดกลางและขนาดย่อมที่เข้มแข็ง มีศักยภาพสูง และสามารถแข่งขันได้", en: "Strong and competitive SMEs", keywords: [วิสาหกิจขนาดกลางและขนาดย่อม, เอสเอ็มอี, ธุรกิจขนาดย่อม, ผู้ประกอบการ, SME, SMEs, small business, entrepreneurs]}
      - {id: nesdp13-08, number: 8, th: "ไทยมีพื้นที่และเมืองอัจฉริยะที่น่าอยู่ ปลอดภัย เติบโตได้อย่างยั่งยืน", en: "Liveable, safe and smart cities and areas", keywords: [เมืองอัจฉริยะ, ผังเมือง, การพัฒนาเมือง, ชุมชนเมือง, smart city, urban development, urban planning]}
      - {id: nesdp13-09, number: 9, th: "ไทยมีความยากจนข้ามรุ่นลดลง และมีความคุ้มครองทางสังคมที่เพียงพอ เหมาะสม", en: "Less intergenerational poverty and adequate social protection", keywords: [ความยากจน, ความคุ้มครองทางสังคม, สวัสดิการ, ผู้มีรายได้น้อย, poverty, social protection, welfare, low-income]}
      - {id: nesdp13-10, number: 10, th: "ไทยมีเศรษฐกิจหมุนเวียนและสังคมคาร์บอนต่ำ", en: "A circular economy and low-carbon society", keywords: [เศรษฐกิจหมุนเวียน, คาร์บอนต่ำ, ก๊าซเรือนกระจก, ขยะ, circular economy, low carbon, greenhouse gas, waste]}
      - {id: nesdp13-11, number: 11, th: "ไทยสามารถลดความเสี่ยงและผลกระทบจากภัยธรรมชาติและการเปลี่ยนแปลงสภาพภูมิอากาศ", en: "Lower risks from natural disasters and climate change", keywords: [ภัยพิบัติ, อุทกภัย, น้ำท่วม, ภัยแล้ง, การเปลี่ยนแปลงสภาพภูมิอากาศ, disaster, flood, drought, climate change]}
      - {id: nesdp13-12, number: 12, th: "ไทยมีกำลังคนสมรรถนะสูง มุ่งเรียนรู้อย่างต่อเนื่อง ตอบโจทย์การพัฒนาแห่งอนาคต", en: "A high-skilled workforce learning throughout life", keywords: [กำลังคน, ทักษะ, การเรียนรู้ตลอดชีวิต, สมรรถนะ, workforce, skills, lifelong learning, competency]}
      - {id: nesdp13-13, number: 13, th: "ไทยมีภาครัฐที่ทันสมัย มีประสิทธิภาพ และตอบโจทย์ประชาชน", en: "A modern, efficient and responsive public sector", keywords: [ภาครัฐ, การบริหารราชการ, รัฐบาลดิจิทัล, การบริการสาธารณะ, ธรรมาภิบาล, public sector, public administration, digital government, public service, governance]}
```

- [ ] **Step 3: The step.** Create `pipeline/atlas/sdg.py`:

```python
"""Step `sdg` (after institutions): research topics → the SDGs and Thai frameworks (BCG, แผนด้าน ววน. 2566–2570,
หมุดหมายแผนพัฒนาฯ ฉบับที่ 13) → work/16_* (export publishes sdg.json and Topic.sdg).

Goals and keywords are curated in atlas/data/frameworks.yaml (sdg.frameworks_path replaces it). Each topic keeps at
most sdg.max_goals_per_topic goals per framework, scored by
  embedding  cosine of the topic centroid (04_centroids.npy) and the embedded goal text "th en: keywords" — used for
             sdg.method embedding, or auto with an api/local embedding provider and centroids on disk; ≥ min_similarity
  lexical    otherwise (or when embedding fails): the share of the topic's articles (≤ sdg.docs_per_topic, seeded
             sample) whose title or keywords name a goal keyword (text folded like the web search; Latin keywords as
             whole words); ≥ sdg.min_article_share
  16_topic_goals    topic_id, framework, goal_id, score
  16_sdg_meta.json  method, version (yaml version + sha1), frameworks [{key, th, en, goals [{id, number, th, en}]}]
A machine-made overview, not an official classification (the web says so). Abstracts are not read.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from atlas.embed import embed_texts
from atlas.io_utils import read_table, write_table
from atlas.matcher import match_fold

FRAMEWORKS_YAML = Path(__file__).parent / "data" / "frameworks.yaml"
TEXT_COLUMNS = ("title", "title_th", "title_en", "keywords_th", "keywords_en")
GOAL_COLUMNS = ["topic_id", "framework", "goal_id", "score"]
GOAL_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")


class FrameworkError(ValueError):
    """frameworks.yaml cannot be used — the message names the goal."""


def load_frameworks(path: str | Path | None = None) -> dict:
    p = Path(path) if path else FRAMEWORKS_YAML
    raw = p.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    seen: set[str] = set()
    for fw in data.get("frameworks") or []:
        if not fw.get("key") or not fw.get("th") or not fw.get("en"):
            raise FrameworkError(f"{p}: every framework needs key, th and en")
        for g in fw.get("goals") or []:
            gid = str(g.get("id", ""))
            if not GOAL_ID.fullmatch(gid) or gid in seen:
                raise FrameworkError(f"{p}: goal id {gid!r} is missing, malformed or repeated")
            seen.add(gid)
            if not isinstance(g.get("number"), int) or not g.get("th") or not g.get("en"):
                raise FrameworkError(f"{p}: goal {gid} needs number, th and en")
            kws = g.get("keywords") or []
            if not kws or not all(isinstance(k, str) and k.strip() for k in kws):
                raise FrameworkError(f"{p}: goal {gid} needs a non-empty list of keywords")
    if not seen:
        raise FrameworkError(f"{p}: no goals")
    data["sha1"] = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return data


def goal_patterns(goals: list[dict]) -> dict[str, re.Pattern]:
    out = {}
    for g in goals:
        parts = []
        for kw in g["keywords"]:
            f = match_fold(kw)
            if f:
                parts.append(rf"(?<![a-z0-9]){re.escape(f)}(?![a-z0-9])" if re.search("[a-z0-9]", f) else re.escape(f))
        out[g["id"]] = re.compile("|".join(sorted(parts, key=len, reverse=True)))
    return out


def lexical_scores(texts: pd.DataFrame, patterns: dict[str, re.Pattern]) -> pd.DataFrame:
    """texts: topic_id, text (folded) → topic_id, goal_id, score (share of the topic's texts naming the goal)."""
    n = texts.groupby("topic_id").size()
    rows = []
    for gid, rx in patterns.items():
        hit = texts["text"].map(lambda s, rx=rx: rx.search(s) is not None).astype(int)
        share = hit.groupby(texts["topic_id"]).sum() / n
        rows += [{"topic_id": int(t), "goal_id": gid, "score": float(v)} for t, v in share.items() if v > 0]
    return pd.DataFrame(rows, columns=["topic_id", "goal_id", "score"])


def similarity_scores(C: np.ndarray, topic_ids: list[int], G: np.ndarray, goal_ids: list[str]) -> pd.DataFrame:
    unit = lambda m: m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)  # noqa: E731
    sim = unit(np.asarray(C, dtype=float)) @ unit(np.asarray(G, dtype=float)).T
    return pd.DataFrame([{"topic_id": int(t), "goal_id": g, "score": float(sim[i, j])}
                         for i, t in enumerate(topic_ids) for j, g in enumerate(goal_ids)],
                        columns=["topic_id", "goal_id", "score"])


def pick(scores: pd.DataFrame, goal_framework: dict[str, str], threshold: float, k: int) -> pd.DataFrame:
    s = scores[scores["score"] >= threshold].assign(framework=lambda d: d["goal_id"].map(goal_framework))
    s = s.sort_values(["topic_id", "framework", "score", "goal_id"], ascending=[True, True, False, True])
    return s.groupby(["topic_id", "framework"]).head(k)[GOAL_COLUMNS].reset_index(drop=True)


def _topic_texts(work: Path, per_topic: int, seed: int) -> pd.DataFrame:
    docs = read_table(work / "02_docs.parquet")
    cols = [c for c in TEXT_COLUMNS if c in docs.columns]
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    d = docs[["article_id", *cols]].merge(fine, on="article_id")
    d = d[d["fine_topic"].fillna(-1).astype(int) >= 0]
    d = d.sample(frac=1.0, random_state=seed).groupby("fine_topic").head(per_topic)
    text = d[cols].fillna("").astype(str).agg(" ".join, axis=1).map(match_fold)
    return pd.DataFrame({"topic_id": d["fine_topic"].astype(int).to_numpy(), "text": text.to_numpy()})


def _goal_text(g: dict) -> str:
    return f"{g['th']} {g['en']}: " + ", ".join(g["keywords"])


def sdg(cfg: dict, embedder=None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    scfg = cfg["sdg"]
    for stale in work.glob("16_*"):
        stale.unlink()
    if not scfg["enabled"]:
        print("[sdg] sdg.enabled is false — no SDG module")
        return pd.DataFrame(columns=GOAL_COLUMNS)
    fw = load_frameworks(scfg["frameworks_path"])
    goals = [dict(g, framework=f["key"]) for f in fw["frameworks"] for g in f["goals"]]
    goal_framework = {g["id"]: g["framework"] for g in goals}
    method = scfg["method"]
    centroids = work / "04_centroids.npy"
    if method == "auto":
        method = "embedding" if cfg["embedding"]["provider"] in ("api", "local") and centroids.exists() else "lexical"
    scores, threshold = None, 0.0
    if method == "embedding":
        try:
            ids = [int(t) for t in json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))]
            G = embed_texts(cfg, [_goal_text(g) for g in goals], embedder)
            scores = similarity_scores(np.load(centroids), ids, G, [g["id"] for g in goals])
            threshold = float(scfg["min_similarity"])
        except (FileNotFoundError, ImportError, OSError, ValueError, RuntimeError) as e:
            print(f"[sdg] WARNING: embedding mapping unavailable ({type(e).__name__}: {e}) — lexical mapping instead")
            method = "lexical"
    if method == "lexical":
        texts = _topic_texts(work, int(scfg["docs_per_topic"]), int(cfg["pipeline"]["seed"]))
        scores, threshold = lexical_scores(texts, goal_patterns(goals)), float(scfg["min_article_share"])
    out = pick(scores, goal_framework, threshold, int(scfg["max_goals_per_topic"]))
    write_table(out, work / "16_topic_goals.parquet")
    meta = {"method": method, "version": f"{fw.get('version', 1)}-{fw['sha1']}",
            "frameworks": [{"key": f["key"], "th": f["th"], "en": f["en"],
                            "goals": [{"id": g["id"], "number": int(g["number"]), "th": g["th"], "en": g["en"]}
                                      for g in f["goals"]]} for f in fw["frameworks"]]}
    (work / "16_sdg_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[sdg] {method}: {out['topic_id'].nunique():,} topics matched to {out['goal_id'].nunique():,} goals")
    return out
```

In `pipeline/atlas/pipeline.py` replace `"match", "institutions", "export"]` with `"match", "institutions", "sdg", "export"]` and below `    "institutions": ("atlas.institutions", "institutions"),` insert `    "sdg": ("atlas.sdg", "sdg"),`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_sdg.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
uv run ruff check --fix .
git add atlas/data/frameworks.yaml atlas/sdg.py atlas/pipeline.py tests/test_sdg.py
git commit -m "feat(sdg): SDG 17 + BCG + แผนด้าน ววน. + หมุดหมายแผนฯ 13 at topic level (centroid cosine or keyword share)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 4: OpenAlex benchmark — step `benchmark` → work/17_*

**Files:**
- Create: `pipeline/atlas/global_bench.py`, `pipeline/tests/test_global_bench.py`
- Modify: `pipeline/atlas/pipeline.py`

**Interfaces:**
- Consumes: P1 `atlas.openalex` — `Fetch` (`(path, params) -> dict`), `HttpFetcher(ocfg, cache_dir)`, `OpenAlexUnavailable`, `short_id`; config `taxonomy.openalex.*`, `emerging.recent_window / baseline_window`, `benchmark.*`; checkpoints `10_taxonomy` (topic_id, subfield_id, source), `07_emerging` (topic_id, count_recent), `06_meta.json`.
- Produces: `DOMAINS`, `BENCH_COLUMNS`, `group_counts(fetch, years, country) -> {subfield_id: (name, count)}`, `benchmark_table(world_r, world_b, country_r, country_b, tci_r, bcfg) -> DataFrame`, step `benchmark(cfg, fetch=None)`; `17_benchmark` (BENCH_COLUMNS), `17_benchmark_meta.json` = `{"skipped": reason}` or `{"skipped": null, source, country, recent, baseline, world_recent, country_recent, subfields, opportunities}`.

- [ ] **Step 1: Write the failing test** — create `pipeline/tests/test_global_bench.py`:

```python
"""Thailand vs the world (OpenAlex): share-based world growth, activity index, opportunities; skips, never fails."""
import json
from pathlib import Path

import pandas as pd
import pytest

from atlas.global_bench import benchmark
from atlas.io_utils import write_table
from atlas.pipeline import STEPS
from tests.p2_work import make_p2_work

NAMES = {"1702": "Artificial Intelligence", "2208": "Electrical and Electronic Engineering"}


def fake_fetch(calls):
    """group_by answers for domain 3 only; recent = 2022–2024, baseline = 2017–2021."""
    def fetch(path, params):
        calls.append(params)
        flt = params["filter"]
        if "primary_topic.domain.id:3" not in flt:
            return {"group_by": []}
        recent = "publication_year:2022-2024" in flt
        if "country_code:TH" in flt:
            counts = {"1702": 100, "2208": 900} if recent else {"1702": 50, "2208": 1_000}
        else:
            counts = {"1702": 50_000, "2208": 40_000} if recent else {"1702": 30_000, "2208": 60_000}
        return {"meta": {"count": sum(counts.values())}, "group_by": [
            {"key": f"https://openalex.org/subfields/{k}", "key_display_name": NAMES[k], "count": v}
            for k, v in counts.items()]}
    return fetch


def _cfg(tmp_path, source="openalex"):
    cfg = make_p2_work(tmp_path)
    work = Path(cfg["pipeline"]["work_dir"])
    write_table(pd.DataFrame({
        "topic_id": [1, 2, 3], "group_id": [22, 22, 17], "group_en": ["Engineering", "Engineering", "Computer Science"],
        "group_th": ["วิศวกรรมศาสตร์", "วิศวกรรมศาสตร์", "วิทยาการคอมพิวเตอร์"], "subfield_id": ["2208", "2208", "1702"],
        "subfield_en": [NAMES["2208"], NAMES["2208"], NAMES["1702"]], "vote_share": [0.9, 0.9, 0.9],
        "cross_field": [False, False, False], "source": [source] * 3}), work / "10_taxonomy.parquet")
    return cfg, work


def test_world_growth_activity_index_and_opportunities(tmp_path):
    cfg, work = _cfg(tmp_path)
    calls = []
    b = benchmark(cfg, fetch=fake_fetch(calls)).set_index("subfield_id")
    assert len(calls) == 16 and all(c["group_by"] == "primary_topic.subfield.id" and c["per_page"] == 200 for c in calls)
    assert b.loc["1702", "world_ratio"] == pytest.approx(5 / 3) and b.loc["1702", "activity_index"] == pytest.approx(0.18)
    assert bool(b.loc["1702", "opportunity"]) and not bool(b.loc["2208", "opportunity"])
    assert b.loc["1702", "tci_R"] == 12 and b.loc["1702", "field_id"] == "17"
    meta = json.loads((work / "17_benchmark_meta.json").read_text(encoding="utf-8"))
    assert meta["skipped"] is None and meta["recent"] == [2022, 2024] and meta["baseline"] == [2017, 2021]
    assert STEPS.index("sdg") < STEPS.index("benchmark") < STEPS.index("export")


def test_offline_or_unanchored_runs_skip_with_a_reason(tmp_path):
    cfg, work = _cfg(tmp_path)
    assert benchmark(cfg).empty                                  # the real fetcher: ATLAS_OFFLINE=1 in every test
    assert "ATLAS_OFFLINE" in json.loads((work / "17_benchmark_meta.json").read_text(encoding="utf-8"))["skipped"]
    assert not (work / "17_benchmark.parquet").exists()
    cfg, work = _cfg(tmp_path / "agg", source="agglomerative")
    assert benchmark(cfg, fetch=fake_fetch([])).empty
    assert "OpenAlex subfields" in json.loads((work / "17_benchmark_meta.json").read_text(encoding="utf-8"))["skipped"]
    cfg["benchmark"]["enabled"] = False
    benchmark(cfg, fetch=fake_fetch([]))
    assert "enabled" in json.loads((work / "17_benchmark_meta.json").read_text(encoding="utf-8"))["skipped"]
```

Run: `uv run pytest tests/test_global_bench.py -q` — Expected: FAIL (`No module named 'atlas.global_bench'`).

- [ ] **Step 2: The step.** Create `pipeline/atlas/global_bench.py`:

```python
"""Step `benchmark` (after sdg): Thailand vs the world in OpenAlex (E9) → work/17_* (export publishes global.json).

Counts per OpenAlex subfield for the emerging recent window R and its baseline B, for the whole world and for works
with an author in taxonomy.openalex.country_code — 16 requests (4 domains × R/B × world/country):
  GET /works?filter=publication_year:<a>-<b>,primary_topic.domain.id:<1-4>[,authorships.institutions.country_code:TH]
      &group_by=primary_topic.subfield.id&per_page=200
through P1's HttpFetcher (request cache in state_dir/openalex, keyless or with the API key, ATLAS_OFFLINE honoured;
every domain has fewer than 200 subfields, so one page each). Per subfield:
  world_ratio     (world_R / ΣR) ÷ (world_B / ΣB) — growth of its share of world output (window lengths cancel)
  activity_index  (country_R / Σcountry_R) ÷ (world_R / ΣR) — 1 = the country publishes it as much as the world does
  country_share   country_R / world_R
  opportunity     world_R ≥ benchmark.min_world_works, world_ratio ≥ min_world_ratio, activity_index ≤ max_activity_index
  tci_R           TCI corpus articles in R on topics anchored to the subfield (10_taxonomy + 07_emerging)
Never fails a run: disabled, a map not anchored to OpenAlex, offline or an API error → no table and
17_benchmark_meta.json {"skipped": reason} (the export names it in manifest.skipped_modules.global).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.openalex import Fetch, HttpFetcher, OpenAlexUnavailable, short_id

DOMAINS = (1, 2, 3, 4)
BENCH_COLUMNS = ["subfield_id", "subfield_en", "field_id", "world_R", "world_B", "country_R", "country_B", "tci_R",
                 "world_ratio", "activity_index", "country_share", "opportunity"]


def group_counts(fetch: Fetch, years: tuple[int, int], country: str | None) -> dict[str, tuple[str, int]]:
    out: dict[str, tuple[str, int]] = {}
    for d in DOMAINS:
        flt = f"publication_year:{years[0]}-{years[1]},primary_topic.domain.id:{d}"
        if country:
            flt += f",authorships.institutions.country_code:{country}"
        res = fetch("/works", {"filter": flt, "group_by": "primary_topic.subfield.id", "per_page": 200})
        for g in res.get("group_by") or []:
            sid = short_id(g.get("key"))
            if sid.isdigit():
                out[sid] = (str(g.get("key_display_name") or ""), int(g.get("count") or 0))
    return out


def _total(counts: dict[str, tuple[str, int]]) -> int:
    return sum(c for _, c in counts.values())


def benchmark_table(world_r: dict, world_b: dict, country_r: dict, country_b: dict, tci_r: dict[str, int],
                    bcfg: dict) -> pd.DataFrame:
    wr_all, wb_all, cr_all = _total(world_r), _total(world_b), _total(country_r)
    rows = []
    for sid in sorted(set(world_r) | set(world_b)):
        name = (world_r.get(sid) or world_b.get(sid))[0]
        wr, wb = world_r.get(sid, ("", 0))[1], world_b.get(sid, ("", 0))[1]
        cr, cb = country_r.get(sid, ("", 0))[1], country_b.get(sid, ("", 0))[1]
        ratio = (wr / wr_all) / (wb / wb_all) if wr and wb and wr_all and wb_all else None
        ai = (cr / cr_all) / (wr / wr_all) if wr and cr_all and wr_all else None
        opportunity = bool(ratio is not None and ai is not None and wr >= int(bcfg["min_world_works"])
                           and ratio >= float(bcfg["min_world_ratio"]) and ai <= float(bcfg["max_activity_index"]))
        rows.append({"subfield_id": sid, "subfield_en": name, "field_id": sid[:2], "world_R": wr, "world_B": wb,
                     "country_R": cr, "country_B": cb, "tci_R": int(tci_r.get(sid, 0)), "world_ratio": ratio,
                     "activity_index": ai, "country_share": cr / wr if wr else None, "opportunity": opportunity})
    return pd.DataFrame(rows, columns=BENCH_COLUMNS)


def _skip(work: Path, reason: str) -> pd.DataFrame:
    print(f"[benchmark] skipped: {reason}")
    (work / "17_benchmark_meta.json").write_text(json.dumps({"skipped": reason}, ensure_ascii=False), encoding="utf-8")
    return pd.DataFrame(columns=BENCH_COLUMNS)


def benchmark(cfg: dict, fetch: Fetch | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    bcfg = cfg["benchmark"]
    for stale in work.glob("17_*"):
        stale.unlink()
    if not bcfg["enabled"]:
        return _skip(work, "benchmark.enabled is false")
    try:
        tax = read_table(work / "10_taxonomy.parquet")
    except FileNotFoundError:
        return _skip(work, "no 10_taxonomy — run the taxonomy step first")
    if tax.empty or not (tax["source"] == "openalex").all():
        return _skip(work, "the topic map is not anchored to OpenAlex subfields (taxonomy fell back to agglomerative "
                           "groups)")
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    e = cfg["emerging"]
    r0 = last - int(e["recent_window"]) + 1
    R, B = (r0, last), (r0 - int(e["baseline_window"]), r0 - 1)
    ocfg = cfg["taxonomy"]["openalex"]
    cc = str(ocfg["country_code"])
    fetcher = fetch or HttpFetcher(ocfg, Path(cfg["pipeline"]["state_dir"]) / "openalex")
    try:
        wr, wb = group_counts(fetcher, R, None), group_counts(fetcher, B, None)
        cr, cb = group_counts(fetcher, R, cc), group_counts(fetcher, B, cc)
    except OpenAlexUnavailable as err:
        return _skip(work, f"OpenAlex unavailable: {err}")
    if not wr or not wb:
        return _skip(work, "OpenAlex returned no subfield counts")
    em = read_table(work / "07_emerging.parquet")[["topic_id", "count_recent"]]
    tci = (tax[["topic_id", "subfield_id"]].astype({"subfield_id": str}).merge(em, on="topic_id")
           .groupby("subfield_id")["count_recent"].sum())
    table = benchmark_table(wr, wb, cr, cb, {str(k): int(v) for k, v in tci.items()}, bcfg)
    write_table(table, work / "17_benchmark.parquet")
    meta = {"skipped": None, "source": f"openalex@{datetime.now(UTC).strftime('%Y-%m-%d')}", "country": cc,
            "recent": list(R), "baseline": list(B), "world_recent": _total(wr), "country_recent": _total(cr),
            "subfields": int(len(table)), "opportunities": int(table["opportunity"].sum())}
    (work / "17_benchmark_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[benchmark] {len(table)} subfields, {meta['opportunities']} opportunities ({cc} vs the world, "
          f"{R[0]}–{R[1]} vs {B[0]}–{B[1]})")
    return table
```

In `pipeline/atlas/pipeline.py` replace `"institutions", "sdg", "export"]` with `"institutions", "sdg", "benchmark", "export"]` and below `    "sdg": ("atlas.sdg", "sdg"),` insert `    "benchmark": ("atlas.global_bench", "benchmark"),`.

- [ ] **Step 3: Run the tests**

Run: `uv run pytest tests/test_global_bench.py tests/test_openalex.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
uv run ruff check --fix .
git add atlas/global_bench.py atlas/pipeline.py tests/test_global_bench.py
git commit -m "feat(benchmark): Thailand vs the world per OpenAlex subfield — world growth, activity index, opportunities; skip with a reason

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 5: Gap finder (R5) and concentration risk (E10) — step `gaps` → work/18_*

**Files:**
- Create: `pipeline/atlas/gaps.py`, `pipeline/tests/test_gaps.py`
- Modify: `pipeline/atlas/pipeline.py`

**Interfaces:**
- Consumes: Task 2 `15_article_institutions`; Task 4 `17_benchmark`; `10_taxonomy`, `07_emerging` (status, orgs_unverified), `09_edges` (s, t, w), `01_articles`, `02_docs`, `04_fine_topics`, `06_meta.json`; `atlas.registry.journal_keys`; `atlas.taxonomy.load_topic_groups`.
- Produces: `concentration(df, unit, item) -> DataFrame[<unit>, articles, hhi, top_share, top_key]`, `few_institution_topics(status, n_inst, statuses, max_n) -> Series`, `weak_bridges(edges, inst_sets, min_sim, max_jaccard, limit) -> DataFrame[s, t, similarity, shared, jaccard]`, `world_gaps(work, limit) -> DataFrame[subfield_id, subfield_en, world_ratio, activity_index, topics]`, step `gaps(cfg) -> dict`; checkpoints `18_gap_few_institutions` (topic_id, status, institutions), `18_gap_bridges`, `18_gap_world`, `18_concentration` (scope, unit, kind, articles, hhi, top_share, top_key, concentrated), `18_gaps_meta.json` (`{"R": [a, b]}`).

- [ ] **Step 1: Write the failing test** — create `pipeline/tests/test_gaps.py`:

```python
"""Gap finder and concentration risk: HHI / top share, few institutions, weak bridges, world opportunities."""
from pathlib import Path

import pandas as pd
import pytest

from atlas.gaps import concentration, few_institution_topics, gaps, weak_bridges
from atlas.institutions import institutions
from atlas.io_utils import read_table, write_table
from atlas.pipeline import STEPS
from tests.p2_work import make_p2_work


def test_concentration_hhi_and_top_share():
    df = pd.DataFrame({"article_id": [1, 2, 3, 4, 4], "unit": [7] * 5, "item": ["a", "a", "a", "b", "a"]})
    out = concentration(df, "unit", "item").set_index("unit")
    assert out.loc[7, "articles"] == 4 and out.loc[7, "top_key"] == "a" and out.loc[7, "top_share"] == 1.0
    assert out.loc[7, "hhi"] == pytest.approx(0.8 ** 2 + 0.2 ** 2)


def test_weak_bridges_and_few_institution_topics():
    edges = pd.DataFrame({"s": [1, 2, 1], "t": [2, 3, 3], "w": [0.7, 0.9, 0.5]})
    out = weak_bridges(edges, {1: {"a", "b"}, 2: {"a", "b"}, 3: {"c"}}, 0.6, 0.1, 10)
    assert list(zip(out["s"], out["t"])) == [(2, 3)] and out.iloc[0]["jaccard"] == 0.0
    status = pd.Series({1: "STABLE", 2: "EMERGING", 3: "WATCH"})
    assert few_institution_topics(status, pd.Series({1: 1, 2: 9, 3: 2}), ["EMERGING", "WATCH"], 5).to_dict() == {3: 2}


def test_step_lists_world_gaps_concentration_and_thin_topics(tmp_path):
    cfg = make_p2_work(tmp_path)
    cfg["risk"]["min_articles"] = 5
    work = Path(cfg["pipeline"]["work_dir"])
    institutions(cfg)
    write_table(pd.DataFrame({"topic_id": [1, 2, 3], "group_id": [14, 14, 17], "group_en": ["B", "B", "C"],
                              "group_th": ["ข", "ข", "ค"], "subfield_id": ["1409", "1406", "1702"],
                              "subfield_en": ["Tourism", "Marketing", "Artificial Intelligence"],
                              "vote_share": [0.9] * 3, "cross_field": [False] * 3, "source": ["openalex"] * 3}),
                work / "10_taxonomy.parquet")
    write_table(pd.DataFrame({"subfield_id": ["1702", "1406"], "subfield_en": ["Artificial Intelligence", "Marketing"],
                              "field_id": ["17", "14"], "world_R": [50_000, 9_000], "world_B": [30_000, 9_000],
                              "country_R": [100, 400], "country_B": [50, 300], "tci_R": [12, 21],
                              "world_ratio": [1.67, 1.0], "activity_index": [0.18, 2.1], "country_share": [0.002, 0.04],
                              "opportunity": [True, False]}), work / "17_benchmark.parquet")
    gaps(cfg)
    world = read_table(work / "18_gap_world.parquet")
    assert world["subfield_id"].tolist() == ["1702"] and world.iloc[0]["topics"] == "3"
    conc = read_table(work / "18_concentration.parquet")
    t3 = conc[(conc["scope"] == "topic") & (conc["unit"] == 3)].set_index("kind")
    assert t3.loc["journal", "top_key"] == "so03:J2" and t3.loc["journal", "top_share"] == 1.0
    assert bool(t3.loc["journal", "concentrated"]) and bool(t3.loc["institution", "concentrated"])
    assert (conc["articles"] >= 5).all()
    few = read_table(work / "18_gap_few_institutions.parquet")
    assert few.set_index("topic_id")["institutions"].to_dict() == {3: 1}          # EMERGING, one institution
    assert STEPS.index("benchmark") < STEPS.index("gaps") < STEPS.index("export")
```

Run: `uv run pytest tests/test_gaps.py -q` — Expected: FAIL (`No module named 'atlas.gaps'`).

- [ ] **Step 2: The step.** Create `pipeline/atlas/gaps.py`:

```python
"""Step `gaps` (after benchmark): the gap finder (R5) and concentration risk (E10) → work/18_* (export: gaps.json).

Articles of the emerging recent window R; institutions from 15_article_institutions, journals from the corpus.
  18_gap_few_institutions  topic_id, status, institutions — topics in gaps.statuses studied by ≤ gaps.max_institutions
                           institutions in R (topics flagged orgs_unverified are left out: too little affiliation data
                           for "few institutions" to mean anything)
  18_gap_bridges           s, t, similarity, shared, jaccard — map neighbours (09_edges w ≥ bridge_min_similarity)
                           whose institution sets in R barely overlap (Jaccard ≤ bridge_max_jaccard)
  18_gap_world             subfield_id, subfield_en, world_ratio, activity_index, topics ("3;7") — benchmark
                           opportunities with the corpus topics anchored there (none without 17_benchmark)
  18_concentration         scope (topic | group), unit (topic id | group id), kind (institution | journal), articles,
                           hhi, top_share, top_key, concentrated — units with ≥ risk.min_articles articles in R (articles
                           with ≥ 1 known institution for kind=institution); HHI = Σ p² over the items' article counts;
                           top_share = articles with the largest item ÷ the unit's articles; concentrated =
                           top_share ≥ risk.max_top_share or hhi ≥ risk.max_hhi
  18_gaps_meta.json        {"R": [first, last]}
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.registry import journal_keys
from atlas.taxonomy import load_topic_groups

CONC_COLUMNS = ["scope", "unit", "kind", "articles", "hhi", "top_share", "top_key", "concentrated"]
WORLD_COLUMNS = ["subfield_id", "subfield_en", "world_ratio", "activity_index", "topics"]


def _opt(path: Path, columns: list[str]) -> pd.DataFrame:
    try:
        return read_table(path)
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)


def concentration(df: pd.DataFrame, unit: str, item: str) -> pd.DataFrame:
    """df: article_id, <unit>, <item> → <unit>, articles, hhi, top_share, top_key (one row per unit)."""
    cols = [unit, "articles", "hhi", "top_share", "top_key"]
    d = df[["article_id", unit, item]].drop_duplicates()
    if d.empty:
        return pd.DataFrame(columns=cols)
    arts = d.groupby(unit)["article_id"].nunique()
    n = d.groupby([unit, item]).size().rename("n").reset_index()
    n["p"] = n["n"] / n.groupby(unit)["n"].transform("sum")
    hhi = (n["p"] ** 2).groupby(n[unit]).sum()
    top = n.sort_values([unit, "n", item], ascending=[True, False, True]).drop_duplicates(unit).set_index(unit)
    return pd.DataFrame({unit: arts.index, "articles": arts.to_numpy(), "hhi": hhi.reindex(arts.index).to_numpy(),
                         "top_share": (top["n"].reindex(arts.index) / arts).to_numpy(),
                         "top_key": top[item].reindex(arts.index).to_numpy()}, columns=cols)


def few_institution_topics(status: pd.Series, n_inst: pd.Series, statuses: Iterable[str], max_n: int) -> pd.Series:
    """{topic: institutions} for topics whose status is in `statuses` and with ≤ max_n institutions (missing = 0)."""
    s = status[status.isin(list(statuses))]
    n = n_inst.reindex(s.index).fillna(0).astype(int)
    return n[n <= max_n].sort_values(kind="stable")


def weak_bridges(edges: pd.DataFrame, inst_sets: dict[int, set], min_sim: float, max_jaccard: float,
                 limit: int) -> pd.DataFrame:
    cols = ["s", "t", "similarity", "shared", "jaccard"]
    rows = []
    for e in edges.itertuples():
        if float(e.w) < min_sim:
            continue
        a, b = inst_sets.get(int(e.s), set()), inst_sets.get(int(e.t), set())
        if not a or not b:
            continue
        shared = len(a & b)
        j = shared / len(a | b)
        if j <= max_jaccard:
            rows.append({"s": int(e.s), "t": int(e.t), "similarity": round(float(e.w), 4), "shared": shared,
                         "jaccard": round(j, 4)})
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(["similarity", "s", "t"], ascending=[False, True, True]).head(limit).reset_index(drop=True)


def world_gaps(work: Path, limit: int) -> pd.DataFrame:
    bench = _opt(work / "17_benchmark.parquet", [])
    tax = _opt(work / "10_taxonomy.parquet", ["topic_id", "subfield_id"])
    if bench.empty:
        return pd.DataFrame(columns=WORLD_COLUMNS)
    anchored = (tax.astype({"subfield_id": str}).groupby("subfield_id")["topic_id"]
                .agg(lambda s: ";".join(str(int(t)) for t in sorted(s))))
    opp = bench[bench["opportunity"].fillna(False).astype(bool)].astype({"subfield_id": str})
    out = opp.assign(topics=opp["subfield_id"].map(anchored).fillna(""))
    return out.sort_values(["world_ratio", "subfield_id"], ascending=[False, True]).head(limit)[WORLD_COLUMNS]


def gaps(cfg: dict) -> dict:
    work = Path(cfg["pipeline"]["work_dir"])
    gcfg, rcfg = cfg["gaps"], cfg["risk"]
    for stale in work.glob("18_*"):
        stale.unlink()
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    R = (last - int(cfg["emerging"]["recent_window"]) + 1, last)
    limit = int(gcfg["max_items"])

    arts = read_table(work / "01_articles.parquet")[["article_id", "journal_name", "year"]]
    arts = arts.assign(journal_key=journal_keys(arts), year=pd.to_numeric(arts["year"], errors="coerce"))
    in_r = arts[arts["year"].between(*R).fillna(False).astype(bool)]
    docs = read_table(work / "02_docs.parquet")[["article_id"]]
    fine = read_table(work / "04_fine_topics.parquet")[["article_id", "fine_topic"]]
    topic_of = docs.merge(fine, on="article_id").rename(columns={"fine_topic": "topic_id"})
    topic_of = topic_of[topic_of["topic_id"].fillna(-1).astype(int) >= 0].astype({"topic_id": int})
    ar = in_r[["article_id", "journal_key"]].merge(topic_of, on="article_id")
    links = _opt(work / "15_article_institutions.parquet", ["article_id", "inst_key"])
    ai = ar.merge(links, on="article_id")

    # R5: emerging topics few institutions work on
    em = read_table(work / "07_emerging.parquet").set_index("topic_id")
    unverified = (em["orgs_unverified"].fillna(False).astype(bool) if "orgs_unverified" in em.columns
                  else pd.Series(False, index=em.index))
    n_inst = ai.groupby("topic_id")["inst_key"].nunique()
    few = few_institution_topics(em.loc[~unverified, "status"], n_inst, gcfg["statuses"],
                                 int(gcfg["max_institutions"])).head(limit)
    few_df = pd.DataFrame({"topic_id": few.index.astype(int), "status": em.loc[few.index, "status"].to_numpy(),
                           "institutions": few.to_numpy(dtype=int)})

    # R5: neighbouring topics whose communities barely meet; world opportunities
    edges = _opt(work / "09_edges.parquet", ["s", "t", "w"])
    sets = {int(t): set(g) for t, g in ai.groupby("topic_id")["inst_key"]}
    bridges = weak_bridges(edges, sets, float(gcfg["bridge_min_similarity"]), float(gcfg["bridge_max_jaccard"]), limit)
    world = world_gaps(work, limit)

    # E10: concentration per topic and per field, by institution and by journal
    sources = (("institution", ai[["article_id", "topic_id", "inst_key"]], "inst_key"),
               ("journal", ar[ar["journal_key"] != ""][["article_id", "topic_id", "journal_key"]], "journal_key"))
    try:
        groups = load_topic_groups(work)[["topic_id", "group_id"]]
    except FileNotFoundError:
        groups = None
    parts = []
    for kind, df, item in sources:
        parts.append(concentration(df, "topic_id", item).rename(columns={"topic_id": "unit"})
                     .assign(scope="topic", kind=kind))
        if groups is not None:
            parts.append(concentration(df.merge(groups, on="topic_id"), "group_id", item)
                         .rename(columns={"group_id": "unit"}).assign(scope="group", kind=kind))
    parts = [p for p in parts if len(p)]
    conc = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=CONC_COLUMNS)
    conc = conc[conc["articles"] >= int(rcfg["min_articles"])].copy()
    conc["concentrated"] = ((conc["top_share"] >= float(rcfg["max_top_share"]))
                            | (conc["hhi"] >= float(rcfg["max_hhi"]))).astype(bool)
    conc = conc.astype({"unit": int, "articles": int}).sort_values(
        ["concentrated", "top_share", "scope", "unit", "kind"], ascending=[False, False, True, True, True])

    write_table(few_df, work / "18_gap_few_institutions.parquet")
    write_table(bridges, work / "18_gap_bridges.parquet")
    write_table(world.reset_index(drop=True), work / "18_gap_world.parquet")
    write_table(conc[CONC_COLUMNS].reset_index(drop=True), work / "18_concentration.parquet")
    meta = {"R": list(R)}
    (work / "18_gaps_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    print(f"[gaps] {len(few_df)} thin emerging topics, {len(bridges)} weak bridges, {len(world)} world opportunities, "
          f"{int(conc['concentrated'].sum())} concentrated units")
    return meta
```

In `pipeline/atlas/pipeline.py` replace `"sdg", "benchmark", "export"]` with `"sdg", "benchmark", "gaps", "export"]` and below `    "benchmark": ("atlas.global_bench", "benchmark"),` insert `    "gaps": ("atlas.gaps", "gaps"),`.

- [ ] **Step 3: Run the tests**

Run: `uv run pytest tests/test_gaps.py tests/test_institutions.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
uv run ruff check --fix .
git add atlas/gaps.py atlas/pipeline.py tests/test_gaps.py
git commit -m "feat(gaps): gap finder (world opportunities, thin emerging topics, weak bridges) and concentration risk (HHI, top share)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 6: Contract 2.2, export of the executives' files, validation, executive bullets

**Files:**
- Create: `pipeline/atlas/export_exec.py`, `pipeline/tests/test_contract_p3.py`
- Modify: `pipeline/atlas/schema/contract.py`, `pipeline/atlas/export_v2.py`, `pipeline/atlas/validate.py`, `pipeline/tests/test_schema.py`, `pipeline/tests/test_contract_v2.py`, `pipeline/tests/test_release.py`, `pipeline/tests/test_e2e_p1.py`; web (the regenerated optional KPIs must still compile): `web/src/strings/overview.ts`, `web/src/pages/overview/KpiGrid.tsx`, `web/src/pages/BriefPage.tsx`
- Regenerate: `web/src/data/contract.schema.json` (`uv run atlas schema`), `web/src/data/contract.ts` (`npm run gen:types` in `web/`)

**Interfaces:**
- Consumes: Tasks 2–5 checkpoints; P2 `export_v2.build_release` locals (`code`, `topic_group`, `jid`, `jname`, `group_code`, `source`, `ids`, `labels_arr`, `docs`), `C.JournalYear`, `C.TopicShare`, `C.CountItem`.
- Produces: contract 2.2 models `ExecutiveSummary`, `InstitutionSummary`, `CollabEdge`, `CountryCount`, `ProvinceName`, `InstitutionsFile`, `Partner`, `Suggestion`, `InstitutionDetail`, `ProvinceStat`, `RegionStat`, `RegionsFile`, `FrameworkInfo`, `GoalStat`, `SdgFile`, `SubfieldBench`, `GlobalFile`, `FewInstitutions`, `Bridge`, `WorldGap`, `Concentration`, `GapsFile`, `P3_FILE_MODELS`; `Kpis.pct_international | pct_multi_institution | provinces`, `Overview.executive`, `Manifest.skipped_modules`; manifest modules `institutions`, `institution_detail`, `regions`, `sdg`, `global`, `gaps`. `export_exec` — `institution_files(cfg, work, code, topic_group) -> (files, {inst_key: id}, kpis)`, `regions_file`, `sdg_file`, `topic_sdg_numbers`, `global_file`, `gaps_file`, `topic_institutions`, `skipped_modules`, `executive_summary`. Units: KPI percentages are 0–100 (like `pct_abstract_en`); shares inside module files are fractions.

- [ ] **Step 1: Write the failing tests.** Create `pipeline/tests/test_contract_p3.py`:

```python
"""Contract 2.2: the executives' files validate strictly, are additive, and appear in the JSON Schema."""
import pytest
from pydantic import ValidationError

from atlas.schema.contract import (
    SCHEMA_VERSION,
    InstitutionSummary,
    Kpis,
    Manifest,
    ProvinceStat,
    contract_json_schema,
    model_for,
)


def test_version_definitions_and_paths():
    assert SCHEMA_VERSION == "2.2.0"
    assert {"institutions", "institution_detail", "regions", "sdg", "global", "gaps"} <= set(
        contract_json_schema()["properties"])
    assert model_for("institutions/nu.json").__name__ == "InstitutionDetail"
    assert model_for("gaps.json").__name__ == "GapsFile" and model_for("institutions.json").__name__ == "InstitutionsFile"


def test_p3_fields_are_strict_and_older_files_still_validate():
    base = {"id": "nu", "source": "alias", "articles": 40, "articles_total": 90}
    assert InstitutionSummary.model_validate(base).province is None
    for bad in ({"id": "NU"}, {"province": "TH-1"}, {"country": "tha"}, {"type": "school"}, {"intl_share": float("nan")}):
        with pytest.raises(ValidationError):
            InstitutionSummary.model_validate({**base, **bad})
    with pytest.raises(ValidationError):
        ProvinceStat.model_validate({"code": "TH-99x", "name_th": "x", "name_en": "x", "region": "north", "articles": 1})
    kpis = {"articles": 1, "assigned_articles": 1, "topics": 1, "groups": 1, "journals": 1, "institutions": 1,
            "pct_abstract_en": 0, "pct_doi": 0, "pct_keywords": 0}
    assert Kpis.model_validate(kpis).pct_international is None                 # a 2.1 overview still validates
    m = Manifest.model_validate({"release": "2026Q4", "generated_at": "x", "pipeline_version": "x",
                                 "config_hash": "x", "embedding_model": "x"})
    assert m.skipped_modules == {}
```

Append to `pipeline/tests/test_release.py`:

```python


# ---------------------------------------------------------------- P3: executives' modules (contract 2.2)
def test_executive_modules_are_published_valid_and_name_no_person(two_releases):
    from atlas.validate import validate_release

    root, cfg = two_releases
    rel = root / "out" / "data" / "2026Q2"
    man = Manifest.model_validate_json((rel / "manifest.json").read_text(encoding="utf-8"))
    assert {"institutions", "institution_detail", "regions", "sdg", "gaps"} <= set(man.modules)
    assert "global" not in man.modules and man.skipped_modules.get("global")       # offline, no OpenAlex map
    assert validate_release(rel, None, cfg["validation"]).errors == []
    people = {n for n in read_table(root / "work" / "01_authors.parquet")["name"].fillna("").astype(str) if len(n) >= 6}
    blob = "".join(p.read_text(encoding="utf-8") for p in rel.rglob("*.json"))
    assert people and not any(n in blob for n in people)                         # no person, anywhere
    inst = json.loads((rel / "institutions.json").read_text(encoding="utf-8"))
    assert all(i["articles"] >= cfg["institutions"]["min_articles"] for i in inst["institutions"])
    sdg = json.loads((rel / "sdg.json").read_text(encoding="utf-8"))
    assert sdg["method"] == "lexical" and len([g for g in sdg["goals"] if g["framework"] == "sdg"]) == 17
```

In `pipeline/tests/test_release.py` replace `    assert man.schema_version == "2.1.0"` with `    assert man.schema_version == "2.2.0"`; in `pipeline/tests/test_schema.py` replace `    assert SCHEMA_VERSION == "2.1.0"` with `    assert SCHEMA_VERSION == "2.2.0"`; in `pipeline/tests/test_contract_v2.py` replace `                          "keywords", "latest", "journals", "journal_detail", "methods", "diff", "match"}` with

```python
                          "keywords", "latest", "journals", "journal_detail", "methods", "diff", "match",
                          "institutions", "institution_detail", "regions", "sdg", "global", "gaps"}
```

In `pipeline/tests/test_e2e_p1.py` insert directly below `    assert rep.stats["kept_ids"] >= 0.9 and rep.previous_dir is not None` (the one slow assertion P3 adds):

```python
    man = json.loads((tmp_path / "out" / "data" / "2026Q2" / "manifest.json").read_text(encoding="utf-8"))
    assert {"institutions", "regions", "sdg", "gaps"} <= set(man["modules"]) and man["skipped_modules"].get("global")
```

Run: `uv run pytest tests/test_contract_p3.py -q` — Expected: FAIL (`ImportError: cannot import name 'InstitutionSummary'`).

- [ ] **Step 2: Contract 2.2.** In `pipeline/atlas/schema/contract.py`:

Replace `SCHEMA_VERSION = "2.1.0"                  # 2.1: editors' modules (journals, methods, diff, match)` with

```python
SCHEMA_VERSION = "2.2.0"                  # 2.1: editors' modules; 2.2: executives' modules (institutions … gaps)
```

and in the module docstring replace `edges.json, keywords.json; P2 (2.1): journals.json, journals/<id>.json, methods.json, diff.json, match.json —` with

```text
edges.json, keywords.json; P2 (2.1): journals.json, journals/<id>.json, methods.json, diff.json, match.json; P3 (2.2):
institutions.json, institutions/<id>.json, regions.json, sdg.json, global.json, gaps.json —
```

In `class Manifest(_Model):` insert below `    llm: list[LlmTaskStats] = Field(default_factory=list)`:

```python
    skipped_modules: dict[str, str] = Field(default_factory=dict, description="optional modules left out of this "
                                                                             "release for a reason: module → reason")
```

In `class Kpis(_Model):` insert below `    pct_keywords: float`:

```python
    pct_international: float | None = Field(None, description="% of window articles pairing Thai and foreign "
                                                              "institutions (P3)")
    pct_multi_institution: float | None = Field(None, description="% of window articles by ≥ 2 institutions (P3)")
    provinces: int | None = Field(None, description="provinces with ≥ 1 article in the window (P3)")
```

Insert directly above `class Overview(_Model):`:

```python
class ExecutiveSummary(_Model):
    """Template sentences built at export from the executives' modules — every number comes from those files."""
    bullets_th: list[str] = Field(default_factory=list)
    bullets_en: list[str] = Field(default_factory=list)
    source: Literal["template"] = "template"


```

In `class Overview(_Model):` insert below `    brief: Brief | None = None`: `    executive: ExecutiveSummary | None = None`.

In `class CountItem(_Model):` replace the `id` field with

```python
    id: str | None = Field(None, description="journal id (journals/<id>.json) or institution id "
                                             "(institutions/<id>.json) when the release has that module")
```

Insert directly above `P2_FILE_MODELS: dict[str, type[_Model]] = {"journals.json": JournalsFile, "methods.json": MethodsFile,`:

```python
# ---------------------------------------------------------------------- P3 executives' modules (schema 2.2)
INST_ID = r"^[a-z0-9][a-z0-9-]{1,48}$"
PROVINCE_CODE = r"^TH-\d{2}$"
COUNTRY_CODE = r"^[A-Z]{2}$"
InstType = Literal["university", "rajabhat", "rajamangala", "hospital", "government", "research", "company", "other"]
RegionKey = Literal["bangkok", "central", "northeast", "north", "south"]


class InstitutionSummary(_Model):
    id: str = Field(pattern=INST_ID, description="institutions/<id>.json — the alias inst_id, ror-<ROR id> or "
                                                 "o<10 hex of sha1(org key)>; stable across releases")
    name_th: str = ""
    name_en: str = ""
    type: InstType = "other"
    province: str | None = Field(None, pattern=PROVINCE_CODE)
    country: str | None = Field(None, pattern=COUNTRY_CODE, description="ISO 3166-1 alpha-2; null = not named")
    source: Literal["alias", "ror", "name"] = Field(description="curated alias table, ROR, or the name as written")
    ror: str = ""
    articles: int = Field(description="window articles with ≥ 1 author from the institution")
    articles_total: int
    articles_recent: int = 0
    intl_share: float | None = Field(None, description="share of its window articles that pair Thai and foreign "
                                                       "institutions")
    partners: int = 0
    topics: int = 0
    group: str | None = Field(None, description="map group holding most of its window articles")


class CollabEdge(_Model):
    a: str = Field(pattern=INST_ID)
    b: str = Field(pattern=INST_ID)
    articles: int


class CountryCount(_Model):
    code: str = Field(pattern=COUNTRY_CODE)
    name_th: str
    name_en: str
    articles: int


class ProvinceName(_Model):
    code: str = Field(pattern=PROVINCE_CODE)
    name_th: str
    name_en: str


class InstitutionsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    window: YearWindow
    recent: YearWindow
    min_articles: int
    network_min_articles: int
    articles_with_org: int = Field(description="window articles with ≥ 1 recognised institution")
    pct_international: float | None = None
    pct_multi_institution: float | None = None
    sources: dict[str, int] = Field(default_factory=dict, description="published institutions by identification")
    institutions: list[InstitutionSummary]
    edges: list[CollabEdge] = Field(default_factory=list)
    countries: list[CountryCount] = Field(default_factory=list)
    province_names: list[ProvinceName] = Field(default_factory=list)


class Partner(_Model):
    id: str = Field(pattern=INST_ID)
    articles: int


class Suggestion(_Model):
    id: str = Field(pattern=INST_ID)
    similarity: float
    topics: list[str] = Field(default_factory=list)


class InstitutionDetail(_Model):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(pattern=INST_ID)
    years: list[JournalYear] = Field(default_factory=list)
    topics: list[TopicShare] = Field(default_factory=list)
    partners: list[Partner] = Field(default_factory=list)
    countries: list[CountryCount] = Field(default_factory=list)
    suggested: list[Suggestion] = Field(default_factory=list)


class ProvinceStat(_Model):
    code: str = Field(pattern=PROVINCE_CODE)
    name_th: str
    name_en: str
    region: RegionKey
    articles: int
    articles_recent: int = 0
    share: float | None = None
    institutions: int = 0
    per_100k: float | None = None
    top: list[str] = Field(default_factory=list, description="ids of its largest published institutions")


class RegionStat(_Model):
    key: RegionKey
    articles: int
    share: float | None = None


class RegionsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    window: YearWindow
    articles_with_org: int
    articles_located: int
    coverage: float | None = None
    population_year: int | None = None
    provinces: list[ProvinceStat]
    regions: list[RegionStat]


class FrameworkInfo(_Model):
    key: str
    th: str
    en: str


class GoalStat(_Model):
    id: str
    framework: str
    number: int
    th: str
    en: str
    topics: list[str] = Field(default_factory=list)
    articles_recent: int = 0
    share_recent: float = 0.0
    share_ratio: float | None = None


class SdgFile(_Model):
    schema_version: str = SCHEMA_VERSION
    method: Literal["embedding", "lexical"]
    version: str
    frameworks: list[FrameworkInfo]
    goals: list[GoalStat]


class SubfieldBench(_Model):
    id: str
    en: str
    group: str = Field(pattern=GROUP_ID)
    world_recent: int
    world_baseline: int
    country_recent: int
    country_baseline: int
    tci_recent: int = 0
    world_ratio: float | None = None
    activity_index: float | None = None
    country_share: float | None = None
    opportunity: bool = False
    topics: list[str] = Field(default_factory=list)


class GlobalFile(_Model):
    schema_version: str = SCHEMA_VERSION
    source: str
    country: str = Field(pattern=COUNTRY_CODE)
    recent: YearWindow
    baseline: YearWindow
    min_world_works: int
    min_world_ratio: float
    max_activity_index: float
    subfields: list[SubfieldBench]


class FewInstitutions(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    institutions: int


class Bridge(_Model):
    a: str = Field(pattern=TOPIC_ID)
    b: str = Field(pattern=TOPIC_ID)
    similarity: float
    shared: int
    jaccard: float


class WorldGap(_Model):
    subfield: str
    en: str
    world_ratio: float | None = None
    activity_index: float | None = None
    topics: list[str] = Field(default_factory=list)


class Concentration(_Model):
    scope: Literal["topic", "group"]
    id: str
    kind: Literal["institution", "journal"]
    articles: int
    hhi: float
    top_share: float
    top: str = Field("", description="institution or journal id; empty when it has no page")
    top_name: str = ""
    concentrated: bool


class GapsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    recent: YearWindow
    statuses: list[Status]
    max_institutions: int
    bridge_min_similarity: float
    bridge_max_jaccard: float
    min_articles: int
    max_top_share: float
    max_hhi: float
    few_institutions: list[FewInstitutions]
    bridges: list[Bridge]
    world: list[WorldGap]
    concentration: list[Concentration]


P3_FILE_MODELS: dict[str, type[_Model]] = {"institutions.json": InstitutionsFile, "regions.json": RegionsFile,
                                           "sdg.json": SdgFile, "global.json": GlobalFile, "gaps.json": GapsFile}


```

Replace `    **P2_FILE_MODELS,` with

```python
    **P2_FILE_MODELS,
    **P3_FILE_MODELS,
```

In `def model_for(path: str)` insert above `    return FILE_MODELS.get(path)`:

```python
    if path.startswith("institutions/") and path.endswith(".json"):
        return InstitutionDetail
```

In `contract_json_schema()` replace `             "diff": DiffFile, "match": MatchIndex}` with

```python
             "diff": DiffFile, "match": MatchIndex, "institutions": InstitutionsFile,
             "institution_detail": InstitutionDetail, "regions": RegionsFile, "sdg": SdgFile, "global": GlobalFile,
             "gaps": GapsFile}
```

Run: `uv run pytest tests/test_contract_p3.py -q` — Expected: PASS.

- [ ] **Step 3: The export.** Create `pipeline/atlas/export_exec.py`:

```python
"""Contract 2.2 files of the executives' release (P3), built from work/15_* (institutions), 16_* (SDG), 17_*
(benchmark) and 18_* (gaps). Called by atlas.export_v2.build_release; each module is optional — a missing checkpoint
leaves its file (and its manifest.modules entry) out; a module skipped for a reason is named in
manifest.skipped_modules.

institutions.json          published institutions (≥ institutions.min_articles in the window), KPI shares, the
                           partnership network (top pairs), partner countries, names of the provinces used
institutions/<id>.json     years, topics, partners, partner countries, R6 suggestions
regions.json               articles per province and region (+ per 100,000 people when the population table is given)
sdg.json                   the goals of every framework with their topics and recent output
global.json                Thailand vs the world per OpenAlex subfield (E9)
gaps.json                  R5 gap lists and E10 concentration
overview.executive         template sentences from the files above (no LLM; every number from the files)
Only institution-level aggregates are published; no person, no abstract.
"""
from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from atlas.countries import COUNTRY_NAMES
from atlas.institutions_ref import INST_TYPES
from atlas.io_utils import read_table
from atlas.places import REGIONS, provinces
from atlas.registry import journal_path
from atlas.schema import contract as C


def _f(v, nd: int = 4) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def _opt(path: Path) -> pd.DataFrame | None:
    try:
        return read_table(path)
    except FileNotFoundError:
        return None


def _meta(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _window(pair) -> C.YearWindow:
    return C.YearWindow(start=int(pair[0]), end=int(pair[1]))


def _given(v) -> bool:
    return isinstance(v, str) and v != ""


def _groups(t: pd.DataFrame | None, key: str) -> dict:
    return dict(tuple(t.groupby(key))) if t is not None and len(t) else {}


def _country(code: str, n) -> C.CountryCount:
    th, en = COUNTRY_NAMES.get(code, (code, code))
    return C.CountryCount(code=code, name_th=th, name_en=en, articles=int(n))


def institution_files(cfg: dict, work: Path, code: dict[int, str], topic_group: dict[int, str]
                      ) -> tuple[dict[str, C._Model], dict[str, str], dict]:
    """({path: model}, {inst_key: published id}, KPI additions) — empty when the institutions step did not run."""
    inst = _opt(work / "15_institutions.parquet")
    meta = _meta(work / "15_institutions_meta.json")
    if inst is None or not meta:
        return {}, {}, {}
    icfg = cfg["institutions"]
    pub = inst[inst["published"].fillna(False).astype(bool)].sort_values(["articles", "code"], ascending=[False, True])
    iid = dict(zip(pub["inst_key"], pub["code"]))
    mix_by = _groups(_opt(work / "15_inst_topics.parquet"), "inst_key")
    years_by = _groups(_opt(work / "15_inst_years.parquet"), "inst_key")
    countries = _opt(work / "15_inst_countries.parquet")
    countries_by = _groups(countries[countries["inst_key"] != ""] if countries is not None else None, "inst_key")
    sugg_by = _groups(_opt(work / "15_inst_suggest.parquet"), "inst_key")
    pairs = _opt(work / "15_inst_pairs.parquet")
    pairs = pairs[pairs["a"].isin(list(iid)) & pairs["b"].isin(list(iid))] if pairs is not None else pd.DataFrame(
        columns=["a", "b", "articles"])
    both = pd.concat([pairs.rename(columns={"a": "k", "b": "o"}), pairs.rename(columns={"b": "k", "a": "o"})])
    partners_by = {k: g.sort_values(["articles", "o"], ascending=[False, True]).head(int(icfg["max_partners"]))
                   for k, g in both.groupby("k")} if len(both) else {}
    group_of = {}
    for k, g in mix_by.items():
        per = g.assign(group=g["topic_id"].astype(int).map(topic_group)).groupby("group")["count"].sum()
        group_of[k] = str(per.sort_values(ascending=False, kind="stable").index[0]) if len(per) else None

    rows, files = [], {}
    for r in pub.itertuples():
        k = r.inst_key
        rows.append(C.InstitutionSummary(
            id=r.code, name_th=r.name_th or "", name_en=r.name_en or "",
            type=r.type if r.type in INST_TYPES else "other",
            province=r.province if _given(r.province) else None, country=r.country if _given(r.country) else None,
            source=r.source, ror=r.ror if _given(r.ror) else "", articles=int(r.articles),
            articles_total=int(r.articles_total), articles_recent=int(r.articles_recent),
            intl_share=_f(r.intl_share), partners=int(r.partners), topics=int(r.topics), group=group_of.get(k)))
        mix, yrs, ptn = mix_by.get(k), years_by.get(k), partners_by.get(k)
        ctr, sug = countries_by.get(k), sugg_by.get(k)
        files[f"institutions/{r.code}.json"] = C.InstitutionDetail(
            id=r.code,
            years=[C.JournalYear(year=int(y.year), articles=int(y.articles)) for y in yrs.itertuples()]
            if yrs is not None else [],
            topics=[C.TopicShare(topic=code[int(t.topic_id)], count=int(t.count), share=_f(t.share) or 0.0)
                    for t in mix.head(int(icfg["top_topics"])).itertuples() if int(t.topic_id) in code]
            if mix is not None else [],
            partners=[C.Partner(id=iid[p.o], articles=int(p.articles)) for p in ptn.itertuples()]
            if ptn is not None else [],
            countries=[_country(c.country, c.articles) for c in ctr.itertuples()] if ctr is not None else [],
            suggested=[C.Suggestion(id=iid[s.other_key], similarity=_f(s.similarity) or 0.0,
                                    topics=[code[int(t)] for t in str(s.topics).split(";") if t and int(t) in code])
                       for s in sug.itertuples() if s.other_key in iid] if sug is not None else [])
    national = (countries[countries["inst_key"] == ""].sort_values(["articles", "country"], ascending=[False, True])
                if countries is not None else pd.DataFrame(columns=["country", "articles"]))
    P = provinces()
    used = sorted({p for p in pub["province"] if _given(p) and p in P})
    w = meta["windows"]
    files["institutions.json"] = C.InstitutionsFile(
        window=_window(w["W"]), recent=_window(w["R"]), min_articles=int(icfg["min_articles"]),
        network_min_articles=int(icfg["network_min_articles"]), articles_with_org=int(meta["with_org"]),
        pct_international=_f(meta.get("pct_international")), pct_multi_institution=_f(meta.get("pct_multi_institution")),
        sources={str(s): int(n) for s, n in (meta.get("sources") or {}).items()}, institutions=rows,
        edges=[C.CollabEdge(a=iid[e.a], b=iid[e.b], articles=int(e.articles)) for e in pairs.itertuples()],
        countries=[_country(c.country, c.articles) for c in national.itertuples()],
        province_names=[C.ProvinceName(code=p, name_th=P[p].name_th, name_en=P[p].name_en) for p in used])
    prov = _opt(work / "15_provinces.parquet")
    pct = lambda key: round(100 * float(meta[key]), 1) if meta.get(key) is not None else None  # noqa: E731
    kpis = {"institutions": int(meta["institutions_total"]), "pct_international": pct("pct_international"),
            "pct_multi_institution": pct("pct_multi_institution"),
            "provinces": int((prov["articles"] > 0).sum()) if prov is not None else None}
    return files, iid, kpis


def regions_file(cfg: dict, work: Path, iid: dict[str, str]) -> C.RegionsFile | None:
    prov = _opt(work / "15_provinces.parquet")
    meta = _meta(work / "15_institutions_meta.json")
    if prov is None or not meta:
        return None
    reg = _opt(work / "15_regions.parquet")
    inst = _opt(work / "15_institutions.parquet")
    located, with_org = int(meta["located"]), int(meta["with_org"])
    population = meta.get("population") or {}
    pop = population.get("by_code") or {}
    top: dict[str, list[str]] = {}
    if inst is not None:
        placed = inst[inst["inst_key"].isin(list(iid)) & inst["province"].map(_given)]
        for p, g in placed.groupby("province"):
            top[str(p)] = [iid[k] for k in g.sort_values(["articles", "inst_key"], ascending=[False, True])["inst_key"].head(3)]
    P = provinces()
    rows = [C.ProvinceStat(
        code=r.code, name_th=P[r.code].name_th, name_en=P[r.code].name_en, region=P[r.code].region,
        articles=int(r.articles), articles_recent=int(r.articles_recent),
        share=_f(r.articles / located) if located else None, institutions=int(r.institutions),
        per_100k=_f(100_000 * r.articles / pop[r.code], 2) if r.code in pop else None, top=top.get(r.code, []))
        for r in prov.itertuples() if r.code in P]
    regions = [C.RegionStat(key=x.region, articles=int(x.articles), share=_f(x.articles / located) if located else None)
               for x in reg.itertuples() if x.region in REGIONS] if reg is not None else []
    return C.RegionsFile(window=_window(meta["windows"]["W"]), articles_with_org=with_org, articles_located=located,
                         coverage=_f(located / with_org) if with_org else None,
                         population_year=population.get("year") if population else None, provinces=rows,
                         regions=regions)


def topic_sdg_numbers(work: Path) -> dict[int, list[int]]:
    """{topic id: SDG numbers} for Topic.sdg (framework "sdg" only)."""
    goals = _opt(work / "16_topic_goals.parquet")
    meta = _meta(work / "16_sdg_meta.json")
    if goals is None or not meta:
        return {}
    number = {g["id"]: int(g["number"]) for f in meta["frameworks"] if f["key"] == "sdg" for g in f["goals"]}
    s = goals[goals["goal_id"].isin(number)]
    return {int(t): sorted({number[g] for g in grp["goal_id"]}) for t, grp in s.groupby("topic_id")}


def sdg_file(cfg: dict, work: Path, code: dict[int, str]) -> C.SdgFile | None:
    goals = _opt(work / "16_topic_goals.parquet")
    meta = _meta(work / "16_sdg_meta.json")
    if goals is None or not meta:
        return None
    em = read_table(work / "07_emerging.parquet").set_index("topic_id")
    by_goal = _groups(goals, "goal_id")
    out = []
    for fw in meta["frameworks"]:
        for g in fw["goals"]:
            grp = by_goal.get(g["id"])
            tids = ([int(t) for t in grp.sort_values(["score", "topic_id"], ascending=[False, True])["topic_id"]]
                    if grp is not None else [])
            tids = [t for t in tids if t in code]
            sub = em.loc[[t for t in tids if t in em.index]]
            share_r = float(sub["share_recent"].sum()) if len(sub) else 0.0
            share_b = float(sub["share_baseline"].sum()) if len(sub) else 0.0
            out.append(C.GoalStat(id=g["id"], framework=fw["key"], number=int(g["number"]), th=g["th"], en=g["en"],
                                  topics=[code[t] for t in tids],
                                  articles_recent=int(sub["count_recent"].sum()) if len(sub) else 0,
                                  share_recent=round(share_r, 6),
                                  share_ratio=_f(share_r / share_b) if share_b > 0 else None))
    return C.SdgFile(method=meta["method"], version=str(meta["version"]),
                     frameworks=[C.FrameworkInfo(key=f["key"], th=f["th"], en=f["en"]) for f in meta["frameworks"]],
                     goals=out)


def global_file(cfg: dict, work: Path, code: dict[int, str], gcode: Callable[[int], str]) -> C.GlobalFile | None:
    meta = _meta(work / "17_benchmark_meta.json")
    table = _opt(work / "17_benchmark.parquet")
    if table is None or not meta or meta.get("skipped"):
        return None
    tax = _opt(work / "10_taxonomy.parquet")
    anchored = ({str(s): [code[int(t)] for t in sorted(g["topic_id"]) if int(t) in code]
                 for s, g in tax.groupby("subfield_id")} if tax is not None else {})
    bcfg = cfg["benchmark"]
    return C.GlobalFile(
        source=str(meta["source"]), country=str(meta["country"]), recent=_window(meta["recent"]),
        baseline=_window(meta["baseline"]), min_world_works=int(bcfg["min_world_works"]),
        min_world_ratio=float(bcfg["min_world_ratio"]), max_activity_index=float(bcfg["max_activity_index"]),
        subfields=[C.SubfieldBench(
            id=str(r.subfield_id), en=str(r.subfield_en), group=gcode(int(r.field_id)), world_recent=int(r.world_R),
            world_baseline=int(r.world_B), country_recent=int(r.country_R), country_baseline=int(r.country_B),
            tci_recent=int(r.tci_R), world_ratio=_f(r.world_ratio), activity_index=_f(r.activity_index),
            country_share=_f(r.country_share, 6), opportunity=bool(r.opportunity),
            topics=anchored.get(str(r.subfield_id), [])) for r in table.itertuples()])


def gaps_file(cfg: dict, work: Path, code: dict[int, str], iid: dict[str, str], jid: dict[str, str],
              jname: dict[str, str], gcode: Callable[[int], str]) -> C.GapsFile | None:
    meta = _meta(work / "18_gaps_meta.json")
    if not meta:
        return None
    few = _opt(work / "18_gap_few_institutions.parquet")
    bridges = _opt(work / "18_gap_bridges.parquet")
    world = _opt(work / "18_gap_world.parquet")
    conc = _opt(work / "18_concentration.parquet")
    inst = _opt(work / "15_institutions.parquet")
    inst_name = {r.inst_key: (r.name_th or r.name_en) for r in inst.itertuples()} if inst is not None else {}

    def top_of(kind: str, key: str) -> tuple[str, str]:
        if kind == "institution":                  # an institution without a page is neither linked nor named
            return (iid[key], inst_name.get(key, "")) if key in iid else ("", "")
        return jid.get(key, ""), jname.get(key) or journal_path(key)

    items = []
    for c in (conc.itertuples() if conc is not None else []):
        if c.scope == "topic" and int(c.unit) not in code:
            continue
        top, name = top_of(c.kind, str(c.top_key))
        items.append(C.Concentration(scope=c.scope, id=code[int(c.unit)] if c.scope == "topic" else gcode(int(c.unit)),
                                     kind=c.kind, articles=int(c.articles), hhi=_f(c.hhi) or 0.0,
                                     top_share=_f(c.top_share) or 0.0, top=top, top_name=name,
                                     concentrated=bool(c.concentrated)))
    g, r = cfg["gaps"], cfg["risk"]
    return C.GapsFile(
        recent=_window(meta["R"]), statuses=list(g["statuses"]), max_institutions=int(g["max_institutions"]),
        bridge_min_similarity=float(g["bridge_min_similarity"]), bridge_max_jaccard=float(g["bridge_max_jaccard"]),
        min_articles=int(r["min_articles"]), max_top_share=float(r["max_top_share"]), max_hhi=float(r["max_hhi"]),
        few_institutions=[C.FewInstitutions(topic=code[int(x.topic_id)], institutions=int(x.institutions))
                          for x in (few.itertuples() if few is not None else []) if int(x.topic_id) in code],
        bridges=[C.Bridge(a=code[int(b.s)], b=code[int(b.t)], similarity=_f(b.similarity) or 0.0, shared=int(b.shared),
                          jaccard=_f(b.jaccard) or 0.0)
                 for b in (bridges.itertuples() if bridges is not None else [])
                 if int(b.s) in code and int(b.t) in code],
        world=[C.WorldGap(subfield=str(x.subfield_id), en=str(x.subfield_en), world_ratio=_f(x.world_ratio),
                          activity_index=_f(x.activity_index),
                          topics=[code[int(t)] for t in str(x.topics).split(";") if t and int(t) in code])
               for x in (world.itertuples() if world is not None else [])],
        concentration=items)


def topic_institutions(work: Path, article_ids, labels_arr, iid: dict[str, str], max_n: int
                       ) -> dict[int, list[C.CountItem]] | None:
    """Top institutions per topic (canonical — alias/ROR merge spelling variants), linked when published (D6)."""
    links = _opt(work / "15_article_institutions.parquet")
    inst = _opt(work / "15_institutions.parquet")
    if links is None or inst is None:
        return None
    names = {r.inst_key: (r.name_th or r.name_en or r.inst_key) for r in inst.itertuples()}
    topic_of = pd.Series(labels_arr, index=article_ids)
    t = links.assign(topic_id=links["article_id"].map(topic_of)).dropna(subset=["topic_id"]).astype({"topic_id": int})
    c = (t[t["topic_id"] >= 0].groupby(["topic_id", "inst_key"]).size().rename("count").reset_index()
         .sort_values(["topic_id", "count", "inst_key"], ascending=[True, False, True]).groupby("topic_id").head(max_n))
    return {int(tid): [C.CountItem(key=names.get(k, k), count=int(n), id=iid.get(k))
                       for k, n in zip(g["inst_key"], g["count"])] for tid, g in c.groupby("topic_id")}


def skipped_modules(cfg: dict, work: Path) -> dict[str, str]:
    out = {}
    bench = _meta(work / "17_benchmark_meta.json")
    if bench.get("skipped"):
        out["global"] = str(bench["skipped"])
    if not cfg["institutions"]["enabled"]:
        out["institutions"] = out["regions"] = "institutions.enabled is false"
    if not cfg["sdg"]["enabled"]:
        out["sdg"] = "sdg.enabled is false"
    return out


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def executive_summary(files: dict[str, C._Model]) -> C.ExecutiveSummary | None:
    """Policy sentences for the overview and the PDF brief, from the executives' files only."""
    th: list[str] = []
    en: list[str] = []
    reg = files.get("regions.json")
    if reg is not None and reg.articles_located and reg.provinces:
        top = sorted(reg.provinces, key=lambda p: (-p.articles, p.code))[:5]
        th.append("จังหวัดที่มีบทความมากที่สุด: " + ", ".join(f"{p.name_th} ({p.articles:,})" for p in top)
                  + f" จากบทความที่ระบุจังหวัดได้ {reg.articles_located:,} เรื่อง")
        en.append("Provinces with the most articles: " + ", ".join(f"{p.name_en} ({p.articles:,})" for p in top)
                  + f", of {reg.articles_located:,} articles with a known province")
    inst = files.get("institutions.json")
    if inst is not None and inst.pct_international is not None:
        cs = inst.countries[:3]
        th.append(f"บทความ {_pct(inst.pct_international)} มีผู้แต่งร่วมจากต่างประเทศ"
                  + (f" ประเทศคู่ความร่วมมือหลัก: {', '.join(c.name_th for c in cs)}" if cs else ""))
        en.append(f"{_pct(inst.pct_international)} of articles have a foreign co-author"
                  + (f"; main partner countries: {', '.join(c.name_en for c in cs)}" if cs else ""))
    sdg = files.get("sdg.json")
    goals = [g for g in sdg.goals if g.framework == "sdg"] if sdg is not None else []
    if goals:
        covered = sum(1 for g in goals if g.topics)
        missing = [g for g in goals if not g.topics][:3]
        th.append(f"หัวข้อวิจัยครอบคลุม {covered} จาก {len(goals)} เป้าหมาย SDG"
                  + (" ยังไม่พบหัวข้อใน " + ", ".join(f"SDG {g.number} {g.th}" for g in missing) if missing else ""))
        en.append(f"Research topics cover {covered} of {len(goals)} SDGs"
                  + ("; none yet for " + ", ".join(f"SDG {g.number} {g.en}" for g in missing) if missing else ""))
    glob = files.get("global.json")
    opp = sorted((s for s in glob.subfields if s.opportunity), key=lambda s: (-(s.world_ratio or 0.0), s.id)) if glob else []
    if opp:
        names = ", ".join(s.en for s in opp[:3])
        th.append(f"{len(opp)} สาขาย่อยที่โลกเติบโตเร็วแต่ไทยยังมีสัดส่วนน้อย เช่น {names}")
        en.append(f"{len(opp)} subfields grow fast worldwide while Thailand's share is small, e.g. {names}")
    gaps = files.get("gaps.json")
    risky = sorted({c.id for c in gaps.concentration if c.scope == "topic" and c.concentrated}) if gaps else []
    if risky:
        th.append(f"{len(risky)} หัวข้อพึ่งสถาบันหรือวารสารรายเดียวสูง (รายใหญ่สุดอยู่ใน {_pct(gaps.max_top_share)} "
                  f"ของบทความขึ้นไป หรือ HHI ≥ {gaps.max_hhi:g})")
        en.append(f"{len(risky)} topics depend heavily on one institution or journal (the largest is in at least "
                  f"{_pct(gaps.max_top_share)} of articles, or HHI ≥ {gaps.max_hhi:g})")
    return C.ExecutiveSummary(bullets_th=th, bullets_en=en) if th else None
```

- [ ] **Step 4: Wire the export.** In `pipeline/atlas/export_v2.py`:

Below `from atlas.export_editors import journal_files, match_file, methods_file` insert:

```python
from atlas.export_exec import (
    executive_summary,
    gaps_file,
    global_file,
    institution_files,
    regions_file,
    sdg_file,
    skipped_modules,
    topic_institutions,
    topic_sdg_numbers,
)
```

Replace

```python
    # ---- topics.json
    topics = []
```

with

```python
    # ---- topics.json
    sdg_of = topic_sdg_numbers(work)                # P3: SDG numbers per topic (empty without the sdg step)
    topics = []
```

Replace `            nowcast=nowcast))` with `            sdg=sdg_of.get(t, []), nowcast=nowcast))`.

Below `    jkey_of = pd.Series(journal_keys(docs).to_numpy(), index=docs["article_id"].to_numpy())` insert:

```python

    # ---- executives' modules (P3, optional) — before the topic details, which link institutions by id
    exec_files, iid, inst_kpis = institution_files(cfg, work, code, topic_group)
    files.update(exec_files)
    gcode = lambda gid: group_code(gid, source)  # noqa: E731
    for name, model in (("regions.json", regions_file(cfg, work, iid)), ("sdg.json", sdg_file(cfg, work, code)),
                        ("global.json", global_file(cfg, work, code, gcode)),
                        ("gaps.json", gaps_file(cfg, work, code, iid, jid, jname, gcode))):
        if model is not None:
            files[name] = model
```

Replace

```python
    institutions = {int(t): [C.CountItem(key=org_names.get(k, k), count=int(n)) for k, n in zip(g["org_key"], g["count"])]
                    for t, g in oc.groupby("topic_id")}
```

with

```python
    institutions = {int(t): [C.CountItem(key=org_names.get(k, k), count=int(n)) for k, n in zip(g["org_key"], g["count"])]
                    for t, g in oc.groupby("topic_id")}
    canonical = topic_institutions(work, docs["article_id"].to_numpy(), labels_arr, iid, int(ecfg["max_topic_orgs"]))
    if canonical is not None:                        # P3: canonical institutions (variants merged), linked when published
        institutions = canonical
```

Replace `                    institutions=int(orgs["org_key"].nunique()),` with

```python
                    institutions=int(inst_kpis.get("institutions", orgs["org_key"].nunique())),
                    pct_international=inst_kpis.get("pct_international"),
                    pct_multi_institution=inst_kpis.get("pct_multi_institution"),
                    provinces=inst_kpis.get("provinces"),
```

Replace `        brief=C.Brief(**brief["brief"]) if brief.get("brief") else None,` with

```python
        brief=C.Brief(**brief["brief"]) if brief.get("brief") else None, executive=executive_summary(files),
```

Replace

```python
    if editor_files:
        modules += ["journals", "journal_detail"]
```

with

```python
    if editor_files:
        modules += ["journals", "journal_detail"]
    modules += [m for m in ("institutions", "regions", "sdg", "global", "gaps") if f"{m}.json" in files]
    if "institutions.json" in files:
        modules.append("institution_detail")
```

Replace `        labels=_label_stats(cfg, labels), llm=_llm_stats(cfg, work, brief, release))` with

```python
        labels=_label_stats(cfg, labels), llm=_llm_stats(cfg, work, brief, release),
        skipped_modules=skipped_modules(cfg, work))
```

- [ ] **Step 5: Validate the new modules.** In `pipeline/atlas/validate.py` replace

```python
              diff (incl. restructured / merged_into) and match is a topic of this release (retired ones
              are not); files above
```

with

```python
              diff (incl. restructured / merged_into) and match is a topic of this release (retired ones
              are not); executives' modules (2.2): unique institution ids with one institutions/<id>.json each,
              edges / partners / suggestions / province tops / topic institution links / concentration tops
              name published institutions, every topic id in sdg, global and gaps is a topic of this release,
              gaps' fields are taxonomy groups; files above
```

insert directly above `def _diff(models: dict, prev_root: Path, vcfg: dict, rep: Report) -> None:`:

```python
def _check_executives(models: dict, rep: Report) -> None:
    """Cross-file references of the P3 modules (institutions, regions, sdg, global, gaps)."""
    topics = models.get("topics.json")
    if topics is None:
        return
    known = {t.id for t in topics.topics}
    groups = {g.id for g in models["taxonomy.json"].groups} if "taxonomy.json" in models else None
    inf = models.get("institutions.json")
    iids: set[str] | None = None
    if inf is not None:
        ids = [i.id for i in inf.institutions]
        iids = set(ids)
        if len(iids) != len(ids):
            rep.errors.append("institutions.json: duplicate institution ids")
        missing = [i for i in ids if f"institutions/{i}.json" not in models]
        if missing:
            rep.errors.append(f"{len(missing)} institutions have no valid institutions/<id>.json (e.g. {missing[0]})")
        if bad := _unknown((x for e in inf.edges for x in (e.a, e.b)), iids):
            rep.errors.append(f"institutions.json: edges name unknown institutions: {bad[:5]}")
    for path, m in models.items():
        if path.startswith("institutions/"):
            if bad := _unknown([t.topic for t in m.topics] + [t for s in m.suggested for t in s.topics], known):
                rep.errors.append(f"{path}: topics not in topics.json: {bad[:5]}")
            if iids is not None and (bad := _unknown([p.id for p in m.partners] + [s.id for s in m.suggested], iids)):
                rep.errors.append(f"{path}: institutions not in institutions.json: {bad[:5]}")
        elif path.startswith("topics/") and iids is not None:
            if bad := _unknown((i.id for i in m.institutions if i.id), iids):
                rep.errors.append(f"{path}: institution links not in institutions.json: {bad[:5]}")
    if (rf := models.get("regions.json")) is not None and iids is not None:
        if bad := _unknown((i for p in rf.provinces for i in p.top), iids):
            rep.errors.append(f"regions.json: institutions not in institutions.json: {bad[:5]}")
    if (sf := models.get("sdg.json")) is not None and (bad := _unknown((t for g in sf.goals for t in g.topics), known)):
        rep.errors.append(f"sdg.json: topics not in topics.json: {bad[:5]}")
    if (gf := models.get("global.json")) is not None and (
            bad := _unknown((t for s in gf.subfields for t in s.topics), known)):
        rep.errors.append(f"global.json: topics not in topics.json: {bad[:5]}")
    if (gp := models.get("gaps.json")) is not None:
        refs = ([f.topic for f in gp.few_institutions] + [x for b in gp.bridges for x in (b.a, b.b)]
                + [t for w in gp.world for t in w.topics] + [c.id for c in gp.concentration if c.scope == "topic"])
        if bad := _unknown(refs, known):
            rep.errors.append(f"gaps.json: topics not in topics.json: {bad[:5]}")
        if groups is not None and (bad := _unknown((c.id for c in gp.concentration if c.scope == "group"), groups)):
            rep.errors.append(f"gaps.json: fields not in taxonomy.json: {bad[:5]}")
        if iids is not None and (bad := _unknown((c.top for c in gp.concentration
                                                  if c.kind == "institution" and c.top), iids)):
            rep.errors.append(f"gaps.json: institutions not in institutions.json: {bad[:5]}")


```

and in `validate_release` replace `    _check_editors(models, rep)` with

```python
    _check_editors(models, rep)
    _check_executives(models, rep)
```

- [ ] **Step 6: Keep the web compiling with the optional KPIs.** The regenerated `Kpis` has optional numbers, so `kpis[key]` is no longer always a number. In `web/src/strings/overview.ts` insert below `  'kpi.abstractEn': { th: 'มีบทคัดย่อภาษาอังกฤษ', en: 'With an English abstract' },`:

```ts
  'kpi.international': { th: 'มีผู้แต่งร่วมจากต่างประเทศ', en: 'With foreign co-authors' },
  'kpi.provinces': { th: 'จังหวัดที่มีผลงาน', en: 'Provinces with output' },
```

Replace `web/src/pages/overview/KpiGrid.tsx` with:

```tsx
import type { AtlasRelease } from '../../data/release'
import type { Kpis } from '../../data/types'
import { fmtInt, fmtNum, kpiDelta, kpiDir } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import type { StrKey } from '../../strings'

const KPIS: readonly { key: keyof Kpis; label: StrKey; unit: 'count' | 'pct' }[] = [
  { key: 'articles', label: 'kpi.articles', unit: 'count' },
  { key: 'topics', label: 'kpi.topics', unit: 'count' },
  { key: 'groups', label: 'kpi.groups', unit: 'count' },
  { key: 'journals', label: 'kpi.journals', unit: 'count' },
  { key: 'institutions', label: 'kpi.institutions', unit: 'count' },
  { key: 'pct_abstract_en', label: 'kpi.abstractEn', unit: 'pct' },
  { key: 'pct_international', label: 'kpi.international', unit: 'pct' },
  { key: 'provinces', label: 'kpi.provinces', unit: 'count' },
]

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

/** E1: KPI tiles — a KPI the release does not carry (e.g. P3 KPIs of an older release) is left out; Δ only when the
 *  previous release's overview carries it too. */
export function KpiGrid({ release }: { release: AtlasRelease }) {
  const { t, lang } = useI18n()
  const now = release.overview.kpis
  const prev = release.previousOverview
  return (
    <dl className="kpis">
      {KPIS.map((k) => {
        const value = num(now[k.key])
        if (value === null) return null
        const before = prev ? num(prev.kpis[k.key]) : null
        const delta = kpiDelta(value, before, k.unit, lang)
        // the arrow follows the change as printed: no arrow beside "±0.0"
        const dir = kpiDir(value, before, k.unit)
        return (
          <div className="kpi" key={k.key}>
            <dt>{t(k.label)}</dt>
            <dd>
              <span className="v">{k.unit === 'pct' ? `${fmtNum(value, 1)}%` : fmtInt(value)}</span>
              {delta && prev ? (
                <span className={dir < 0 ? 'd is-down' : 'd'}>
                  {dir !== 0 ? (
                    <svg viewBox="0 0 10 10" aria-hidden="true" focusable="false">
                      <path d={dir > 0 ? 'M5 1.5L9 7.5H1z' : 'M5 8.5L9 2.5H1z'} fill="currentColor" />
                    </svg>
                  ) : null}
                  <span>{delta}</span>
                  <span className="d-ref">{t('delta', { prev: prev.release })}</span>
                </span>
              ) : null}
            </dd>
          </div>
        )
      })}
    </dl>
  )
}
```

In `web/src/pages/BriefPage.tsx` replace

```tsx
  { key: 'pct_abstract_en', label: 'kpi.abstractEn', unit: 'pct' },
]
const TOP = 5
```

with

```tsx
  { key: 'pct_abstract_en', label: 'kpi.abstractEn', unit: 'pct' },
  { key: 'pct_international', label: 'kpi.international', unit: 'pct' },
  { key: 'provinces', label: 'kpi.provinces', unit: 'count' },
]
const TOP = 5
```

and replace

```tsx
            {KPIS.map((k) => (
              <tr key={k.key}>
                <th scope="row">{t(k.label)}</th>
                <td className="num">{k.unit === 'pct' ? `${fmtNum(ov.kpis[k.key], 1)}%` : fmtInt(ov.kpis[k.key])}</td>
                {prev ? <td className="num">{kpiDelta(ov.kpis[k.key], prev.kpis[k.key], k.unit, lang) ?? ''}</td> : null}
              </tr>
            ))}
```

with

```tsx
            {KPIS.filter((k) => typeof ov.kpis[k.key] === 'number').map((k) => {
              const value = ov.kpis[k.key] as number
              const before = prev ? prev.kpis[k.key] : null
              return (
                <tr key={k.key}>
                  <th scope="row">{t(k.label)}</th>
                  <td className="num">{k.unit === 'pct' ? `${fmtNum(value, 1)}%` : fmtInt(value)}</td>
                  {prev ? <td className="num">{typeof before === 'number' ? (kpiDelta(value, before, k.unit, lang) ?? '') : ''}</td> : null}
                </tr>
              )
            })}
```

- [ ] **Step 7: Regenerate the schema and types, run the suites**

```bash
uv run atlas schema
cd ../web && npm run gen:types && npm run lint && npx tsc -b && npm test && cd ../pipeline
uv run pytest -q
```

Expected: PASS — `test_contract_p3`, the appended `test_release` test, `test_schema` (committed schema = generated), every P1/P2 test; web lint, type-check and unit tests green (the 2.1 fixtures stay valid: every 2.2 field is optional or lives in a new file, so the overview still shows 6 KPI tiles until Task 7's fixtures).

- [ ] **Step 8: Commit**

```bash
uv run ruff check --fix .
git add atlas/schema/contract.py atlas/export_exec.py atlas/export_v2.py atlas/validate.py tests/test_contract_p3.py tests/test_contract_v2.py tests/test_release.py tests/test_schema.py tests/test_e2e_p1.py ../web/src/data/contract.schema.json ../web/src/data/contract.ts ../web/src/strings/overview.ts ../web/src/pages/overview/KpiGrid.tsx ../web/src/pages/BriefPage.tsx
git commit -m "feat(contract): contract 2.2 — institutions, regions, SDG, global benchmark and gaps in every release; executive bullets, skipped modules, validation; optional P3 KPIs on the web

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 7: Web data layer, fixtures, grouped navigation, strings and styles

Invoke `impeccable` (craft) for "a grouped site navigation for a civic data atlas: three disclosure menus (สำหรับผู้บริหาร / บรรณาธิการ / นักวิจัย) between top-level links, 44 px targets, keyboard and Escape, works at 360 px; DESIGN.md tokens" before Step 5, and keep DESIGN.md's navigation spec (4 px underline for the current page).

**Files:**
- Create: `web/src/strings/executive.ts`, `web/src/styles/executive.css`, `web/src/lib/executive.ts`, `web/src/lib/executive.test.ts`
- Modify: `web/src/data/types.ts`, `web/src/data/release.ts`, `web/src/data/fixtures.test.ts`, `web/src/components/ModuleFile.tsx`, `web/src/components/Header.tsx`, `web/src/pages/data/ModuleDownloads.tsx`, `web/src/strings/modules.ts`, `web/src/strings/index.ts`, `web/src/styles/tokens.css`, `web/src/styles/index.css`, `web/scripts/make-fixtures.mjs`, `web/e2e/smoke.spec.ts`
- Regenerate: `web/fixtures/**` (`npm run fixtures`)

**Interfaces:**
- Consumes: Task 6 generated types (`InstitutionsFile`, `InstitutionDetail`, `RegionsFile`, `SdgFile`, `GlobalFile`, `GapsFile`, `Overview.executive`, `Manifest.skipped_modules`); P2 `MODULE_FILES`, `hasModule`, `ModuleFile`, `ModuleDownloads`, `foldText`.
- Produces: `types.ts` aliases `InstitutionSummary`, `CollabEdge`, `CountryCount`, `ProvinceName`, `Partner`, `Suggestion`, `ProvinceStat`, `RegionStat`, `GoalStat`, `FrameworkInfo`, `SubfieldBench`, `FewInstitutions`, `Bridge`, `WorldGap`, `Concentration`, `ExecutiveSummary`; `MODULE_FILES.{institutions, regions, sdg, global, gaps}`; `hasModule(…, 'institution_detail')`; `lib/executive.ts` — `ShownName`, `instName(i, lang)`, `otherInstName(i, lang)`, `INST_TYPES`, `type InstType`, `type TypeFilter`, `filterInstitutions(list, q, type)`, `quantileBreaks(values, k=5)`, `bucketOf(value, breaks)`; strings `nav.group.*`, `nav.{institutions,regions,sdg,global,gaps}`, `mod.skipped`, `data.file.{institutions,regions,sdg,global,gaps}`, `in.*`, `rg.*`, `sdg.*`, `gl.*`, `gp.*`, `brief.exec*`, `ov.exec.h`; CSS `.nav-group/.nav-btn/.nav-menu*`, `.pmap`, `.pv-*`, `.pkey`, `.sw-*`, `.metric-switch`, `.sug-list`, `.sug-topics`, `.exec-points`, `.flag-on`, `.sdg-ex`, `.goal-name`, `.pair`; tokens `--seq-1…--seq-5`; fixture ids `mu-a`, `mu-b`, `rbu-x`, `ror-0example1`, `rmu-y`, `o1a2b3c4d5e`, `o9f8e7d6c5b`, `o0123456789`.

- [ ] **Step 1: Write the failing unit test** — create `web/src/lib/executive.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { bundleOf } from '../../test/fixtureData'
import type { InstitutionsFile } from '../data/types'
import { bucketOf, filterInstitutions, instName, otherInstName, quantileBreaks } from './executive'

const file = bundleOf('example').files['institutions.json'] as InstitutionsFile
const byId = new Map(file.institutions.map((i) => [i.id, i]))

describe('executive helpers', () => {
  it('names an institution in the UI language, else in the other language with its lang', () => {
    expect(instName(byId.get('o1a2b3c4d5e')!, 'en')).toEqual({ text: 'โรงพยาบาลตัวอย่าง', lang: 'th' })
    expect(instName(byId.get('mu-a')!, 'en')).toEqual({ text: 'Example University A', lang: null })
    expect(otherInstName(byId.get('mu-a')!, 'th')).toBe('Example University A')
  })

  it('filters by folded name and by type', () => {
    expect(filterInstitutions(file.institutions, 'ราชภัฏ', 'all').map((i) => i.id)).toEqual(['rbu-x'])
    expect(filterInstitutions(file.institutions, '', 'rajamangala').map((i) => i.id)).toEqual(['rmu-y'])
    expect(filterInstitutions(file.institutions, 'EXAMPLE UNIVERSITY', 'university').map((i) => i.id)).toEqual(['mu-a', 'mu-b'])
  })

  it('splits values into quantile classes and keeps no data apart', () => {
    const breaks = quantileBreaks([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(breaks).toEqual([2, 4, 6, 8, 10])
    expect([1, 3, 10, 11].map((v) => bucketOf(v, breaks))).toEqual([0, 1, 4, 4])
    expect(bucketOf(null, breaks)).toBe(-1)
    expect(quantileBreaks([5, 5, 5])).toEqual([5])
  })
})
```

Run: `npx vitest run src/lib/executive.test.ts` — Expected: FAIL (`./executive` not found).

- [ ] **Step 2: Types and loader.** In `web/src/data/types.ts` add `GapsFile, GlobalFile, InstitutionDetail, InstitutionsFile, RegionsFile, SdgFile` to both the `import type { … } from './contract'` list and the `export type { … } from './contract'` list (keep them alphabetical), and append below the P2 aliases:

```ts
/* P3 executives' modules (contract 2.2) — optional files listed in manifest.modules */
export type InstitutionSummary = InstitutionsFile['institutions'][number]
export type CollabEdge = NonNullable<InstitutionsFile['edges']>[number]
export type CountryCount = NonNullable<InstitutionsFile['countries']>[number]
export type ProvinceName = NonNullable<InstitutionsFile['province_names']>[number]
export type Partner = NonNullable<InstitutionDetail['partners']>[number]
export type Suggestion = NonNullable<InstitutionDetail['suggested']>[number]
export type ProvinceStat = RegionsFile['provinces'][number]
export type RegionStat = RegionsFile['regions'][number]
export type GoalStat = SdgFile['goals'][number]
export type FrameworkInfo = SdgFile['frameworks'][number]
export type SubfieldBench = GlobalFile['subfields'][number]
export type FewInstitutions = GapsFile['few_institutions'][number]
export type Bridge = GapsFile['bridges'][number]
export type WorldGap = GapsFile['world'][number]
export type Concentration = GapsFile['concentration'][number]
export type ExecutiveSummary = NonNullable<Overview['executive']>
```

In `web/src/data/release.ts` replace

```ts
export const MODULE_FILES = { journals: 'journals.json', methods: 'methods.json', diff: 'diff.json', match: 'match.json' } as const
```

with

```ts
export const MODULE_FILES = {
  journals: 'journals.json', methods: 'methods.json', diff: 'diff.json', match: 'match.json',
  institutions: 'institutions.json', regions: 'regions.json', sdg: 'sdg.json', global: 'global.json', gaps: 'gaps.json',
} as const
```

and replace `export function hasModule(release: AtlasRelease, module: ModuleName | 'journal_detail'): boolean {` with `export function hasModule(release: AtlasRelease, module: ModuleName | 'journal_detail' | 'institution_detail'): boolean {`.

In `web/src/data/fixtures.test.ts` replace `  'journals.json': 'JournalsFile', 'methods.json': 'MethodsFile', 'diff.json': 'DiffFile', 'match.json': 'MatchIndex',` with

```ts
  'journals.json': 'JournalsFile', 'methods.json': 'MethodsFile', 'diff.json': 'DiffFile', 'match.json': 'MatchIndex',
  'institutions.json': 'InstitutionsFile', 'regions.json': 'RegionsFile', 'sdg.json': 'SdgFile', 'global.json': 'GlobalFile', 'gaps.json': 'GapsFile',
```

and `path.startsWith('journals/') ? 'JournalDetail' : MODEL[path]` with `path.startsWith('journals/') ? 'JournalDetail' : path.startsWith('institutions/') ? 'InstitutionDetail' : MODEL[path]`.

In `web/src/pages/data/ModuleDownloads.tsx` replace `  match: 'data.file.match',` with

```ts
  match: 'data.file.match',
  institutions: 'data.file.institutions',
  regions: 'data.file.regions',
  sdg: 'data.file.sdg',
  global: 'data.file.global',
  gaps: 'data.file.gaps',
```

In `web/src/components/ModuleFile.tsx` replace `        <EmptyState title={t('mod.absent')}><p>{t('mod.absentBody')}</p></EmptyState>` with

```tsx
        <EmptyState title={t('mod.absent')}>
          <p>{t('mod.absentBody')}</p>
          {skipped ? <p>{t('mod.skipped')} <span lang="en">{skipped}</span></p> : null}
        </EmptyState>
```

and below `  const present = hasModule(release, module)` insert `  const skipped = release.manifest.skipped_modules?.[module] ?? null`.

In `web/src/strings/modules.ts` replace the whole `'mod.absentBody'` line with

```ts
  'mod.absentBody': { th: 'ส่วนนี้เพิ่มในรุ่นหลังของ Atlas รอบข้อมูลที่สร้างก่อนหน้านั้น หรือที่ปิดโมดูลนี้ จะไม่มีข้อมูลให้แสดง', en: 'This part was added in a later version of the Atlas. Releases built before it, or with the module switched off, have nothing to show here.' },
```

- [ ] **Step 3: Helpers.** Create `web/src/lib/executive.ts`:

```ts
import type { InstitutionSummary } from '../data/types'
import type { Lang } from './i18n'
import { foldText } from './search'

export interface ShownName {
  text: string
  /** language of `text` when it differs from the UI language (for a lang attribute) */
  lang: Lang | null
}

type Named = Pick<InstitutionSummary, 'id' | 'name_th' | 'name_en'>

/** The institution's name in the UI language, else in the other language, else its id (never an empty title). */
export function instName(i: Named, lang: Lang): ShownName {
  const own = lang === 'en' ? i.name_en : i.name_th
  const other = lang === 'en' ? i.name_th : i.name_en
  if (own) return { text: own, lang: null }
  if (other) return { text: other, lang: lang === 'en' ? 'th' : 'en' }
  return { text: i.id, lang: null }
}

/** The name in the other language when both exist and differ. */
export function otherInstName(i: Named, lang: Lang): string {
  const own = lang === 'en' ? i.name_en : i.name_th
  const other = lang === 'en' ? i.name_th : i.name_en
  return own && other && own !== other ? other : ''
}

export const INST_TYPES = ['university', 'rajabhat', 'rajamangala', 'hospital', 'government', 'research', 'company', 'other'] as const
export type InstType = (typeof INST_TYPES)[number]
export type TypeFilter = 'all' | InstType

/** Institutions whose names or id contain the query (Thai folded, tone marks ignored) and match the type. */
export function filterInstitutions(list: readonly InstitutionSummary[], query: string, type: TypeFilter): InstitutionSummary[] {
  const q = foldText(query)
  return list.filter((i) => (type === 'all' || (i.type ?? 'other') === type) && (!q || [i.name_th, i.name_en, i.id].some((v) => v && foldText(v).includes(q))))
}

/** Upper bounds of k quantile classes (ascending, without repeats) — a choropleth's classes. */
export function quantileBreaks(values: readonly number[], k = 5): number[] {
  const v = values.filter((x) => Number.isFinite(x)).slice().sort((a, b) => a - b)
  const out: number[] = []
  for (let c = 1; c <= k && v.length; c++) {
    const b = v[Math.min(v.length - 1, Math.ceil((c * v.length) / k) - 1)]
    if (!out.length || b > out[out.length - 1]) out.push(b)
  }
  return out
}

/** Class of a value (0 = lowest); -1 = no data. */
export function bucketOf(value: number | null | undefined, breaks: readonly number[]): number {
  if (value === null || value === undefined || !Number.isFinite(value) || breaks.length === 0) return -1
  const i = breaks.findIndex((b) => value <= b)
  return i < 0 ? breaks.length - 1 : i
}
```

- [ ] **Step 4: Strings.** Create `web/src/strings/executive.ts`:

```ts
import { defineStrings } from './define'

/** P3 executives' release: grouped navigation, /institutions, /regions, /sdg, /global, /gaps, KPI and brief additions. */
export const executive = defineStrings({
  'nav.group.exec': { th: 'สำหรับผู้บริหาร', en: 'For executives' },
  'nav.group.editors': { th: 'สำหรับบรรณาธิการ', en: 'For editors' },
  'nav.group.research': { th: 'สำหรับนักวิจัย', en: 'For researchers' },
  'nav.institutions': { th: 'สถาบัน', en: 'Institutions' },
  'nav.regions': { th: 'แผนที่จังหวัด', en: 'Provinces' },
  'nav.sdg': { th: 'SDG และแผนชาติ', en: 'SDGs and national plans' },
  'nav.global': { th: 'ไทยเทียบโลก', en: 'Thailand vs the world' },
  'nav.gaps': { th: 'ช่องว่างงานวิจัย', en: 'Research gaps' },
  'mod.skipped': { th: 'เหตุผลจากระบบประมวลผล:', en: 'Reason given by the pipeline:' },
  'data.file.institutions': { th: 'สถาบัน เครือข่ายความร่วมมือ และประเทศคู่ความร่วมมือ (ระดับสถาบัน)', en: 'Institutions, the collaboration network and partner countries (institution level)' },
  'data.file.regions': { th: 'บทความรายจังหวัดและรายภาค', en: 'Articles by province and region' },
  'data.file.sdg': { th: 'หัวข้อวิจัยตาม SDG และกรอบไทย', en: 'Research topics by SDG and Thai framework' },
  'data.file.global': { th: 'ไทยเทียบโลกราย subfield ของ OpenAlex', en: 'Thailand vs the world by OpenAlex subfield' },
  'data.file.gaps': { th: 'ช่องว่างงานวิจัยและความเสี่ยงการกระจุกตัว', en: 'Research gaps and concentration risk' },

  'in.title': { th: 'สถาบัน', en: 'Institutions' },
  'in.lede': { th: 'สถาบันที่มีบทความอย่างน้อย {n} เรื่องในช่วง {a}–{b} บทความหนึ่งนับให้ทุกสถาบันของผู้แต่ง แสดงระดับสถาบันเท่านั้น ไม่มีข้อมูลรายบุคคล', en: 'Institutions with at least {n} articles in {a}–{b}. An article counts for every institution among its authors. Institution level only — nothing about individuals.' },
  'in.search': { th: 'ค้นหาสถาบัน', en: 'Find an institution' },
  'in.type': { th: 'ประเภทสถาบัน', en: 'Institution type' },
  'in.type.all': { th: 'ทุกประเภท', en: 'All types' },
  'in.type.university': { th: 'มหาวิทยาลัย', en: 'University' },
  'in.type.rajabhat': { th: 'มหาวิทยาลัยราชภัฏ', en: 'Rajabhat university' },
  'in.type.rajamangala': { th: 'มหาวิทยาลัยเทคโนโลยีราชมงคล', en: 'Rajamangala university of technology' },
  'in.type.hospital': { th: 'โรงพยาบาล', en: 'Hospital' },
  'in.type.government': { th: 'หน่วยงานรัฐ', en: 'Government agency' },
  'in.type.research': { th: 'สถาบันวิจัย', en: 'Research institute' },
  'in.type.company': { th: 'บริษัท', en: 'Company' },
  'in.type.other': { th: 'อื่น ๆ', en: 'Other' },
  'in.count': { th: 'แสดง {n} จาก {total} สถาบัน', en: 'Showing {n} of {total} institutions' },
  'in.table': { th: 'ผลงานของสถาบัน {a}–{b}', en: 'Institutions’ output, {a}–{b}' },
  'in.none': { th: 'ไม่พบสถาบันที่ตรงเงื่อนไข', en: 'No institution matches' },
  'in.col.type': { th: 'ประเภท', en: 'Type' },
  'in.col.province': { th: 'จังหวัด', en: 'Province' },
  'in.col.recent': { th: 'ช่วงล่าสุด', en: 'Recent' },
  'in.col.intl': { th: 'ร่วมกับต่างประเทศ', en: 'With foreign partners' },
  'in.col.partners': { th: 'สถาบันที่ร่วมงาน', en: 'Partner institutions' },
  'in.col.pair': { th: 'คู่ความร่วมมือ', en: 'Partnership' },
  'in.col.country': { th: 'ประเทศ', en: 'Country' },
  'in.col.similarity': { th: 'ความคล้ายของหัวข้อ', en: 'Topic similarity' },
  'in.abroad': { th: 'ต่างประเทศ ({c})', en: 'Abroad ({c})' },
  'in.unplaced': { th: 'ไม่ทราบ', en: 'Unknown' },
  'in.source.alias': { th: 'ตามทะเบียนชื่อสถาบัน', en: 'From the institution table' },
  'in.source.ror': { th: 'ตาม ROR', en: 'From ROR' },
  'in.source.name': { th: 'ตามที่เขียนในบทความ', en: 'As written in the articles' },
  'in.foot': { th: 'ชื่อสถาบันมาจากทะเบียนชื่อสถาบันที่คัดกรองแล้ว ฐานข้อมูล ROR หรือชื่อตามที่เขียนในบทความ (ชื่อที่สะกดต่างกันอาจแยกเป็นคนละแถว) · จังหวัดของสถาบันที่ไม่อยู่ในทะเบียนอนุมานจากชื่อจังหวัดในสังกัด · “ร่วมกับต่างประเทศ” = สัดส่วนบทความที่มีทั้งสถาบันไทยและสถาบันต่างประเทศ', en: 'Names come from the curated institution table, ROR, or the name as written in the articles (spelling variants may show as separate rows). The province of an institution outside the table is inferred from a province named in the affiliation. “With foreign partners” = share of its articles that have both a Thai and a foreign institution.' },
  'in.kpi.h': { th: 'ภาพรวมความร่วมมือ', en: 'Collaboration at a glance' },
  'in.kpi.shown': { th: 'สถาบันที่แสดง', en: 'Institutions shown' },
  'in.kpi.shownSub': { th: 'มีบทความอย่างน้อย {n} เรื่องในช่วง {a}–{b}', en: 'At least {n} articles in {a}–{b}' },
  'in.kpi.intl': { th: 'บทความที่มีผู้แต่งร่วมจากต่างประเทศ', en: 'Articles with foreign co-authors' },
  'in.kpi.intlSub': { th: 'ของบทความที่ระบุสังกัดได้ {n} เรื่อง', en: 'Of {n} articles with a known affiliation' },
  'in.kpi.multi': { th: 'บทความที่ร่วมกันหลายสถาบัน', en: 'Articles by several institutions' },
  'in.pairs.h': { th: 'คู่ความร่วมมือระหว่างสถาบัน', en: 'Partnerships between institutions' },
  'in.pairs.intro': { th: 'คู่สถาบันที่เขียนบทความร่วมกันมากที่สุดในช่วง {a}–{b} (อย่างน้อย {n} เรื่อง)', en: 'The institution pairs with the most co-authored articles in {a}–{b} (at least {n})' },
  'in.pairs.table': { th: 'คู่สถาบันที่ร่วมงานกันบ่อยที่สุด', en: 'The most frequent partnerships' },
  'in.countries.h': { th: 'ประเทศคู่ความร่วมมือ', en: 'Partner countries' },
  'in.countries.intro': { th: 'บทความช่วง {a}–{b} ที่สถาบันไทยเขียนร่วมกับสถาบันในแต่ละประเทศ', en: 'Articles in {a}–{b} that Thai institutions co-authored with institutions in each country' },
  'in.countries.table': { th: 'บทความร่วมกับต่างประเทศ จำแนกตามประเทศ', en: 'Articles with foreign partners, by country' },
  'in.back': { th: 'สถาบันทั้งหมด', en: 'All institutions' },
  'in.notFound': { th: 'ไม่พบสถาบัน {id} ในรอบข้อมูลนี้', en: 'Institution {id} is not in this release' },
  'in.notFound.body': { th: 'ลิงก์อาจผิด หรือสถาบันนี้มีบทความน้อยกว่าเกณฑ์ที่แสดง', en: 'The link may be wrong, or the institution has fewer articles than the listing needs.' },
  'in.numbers.h': { th: 'ตัวเลขสำคัญ', en: 'Key figures' },
  'in.articlesSub': { th: 'ช่วง {a}–{b} · ทั้งหมด {all} เรื่อง', en: '{a}–{b} · {all} in total' },
  'in.recentSub': { th: 'ช่วง {a}–{b}', en: '{a}–{b}' },
  'in.intlSub': { th: 'บทความที่มีทั้งสถาบันไทยและสถาบันต่างประเทศ', en: 'Articles with both a Thai and a foreign institution' },
  'in.partnersSub': { th: 'สถาบันที่เขียนบทความร่วมกันในช่วงนี้', en: 'Institutions it co-authored with in this window' },
  'in.topicsSub': { th: 'หัวข้อที่มีบทความของสถาบัน', en: 'Topics with its articles' },
  'in.topics.h': { th: 'หัวข้อที่สถาบันทำ', en: 'Topics it works on' },
  'in.topics.table': { th: 'หัวข้อของสถาบัน', en: 'The institution’s topics' },
  'in.emerging': { th: 'หัวข้อกำลังเกิดใหม่หรือจับตาที่สถาบันนี้มีบทความ', en: 'Emerging or watch topics it publishes on' },
  'in.partners.h': { th: 'สถาบันที่ร่วมงาน', en: 'Partner institutions' },
  'in.partners.table': { th: 'สถาบันที่เขียนบทความร่วมกัน', en: 'Co-authoring institutions' },
  'in.suggest.h': { th: 'สถาบันที่อาจร่วมงานได้', en: 'Possible partners' },
  'in.suggest.intro': { th: 'สถาบันที่ทำหัวข้อคล้ายกัน (ความคล้ายของสัดส่วนหัวข้อ) แต่ยังไม่มีบทความร่วมกันในช่วง {a}–{b} เป็นข้อเสนอจากข้อมูล ไม่ใช่การรับรอง', en: 'Institutions with a similar topic mix that have not co-authored an article in {a}–{b}. A suggestion from the data, not an endorsement.' },
  'in.suggest.sub': { th: 'ความคล้าย {s} · หัวข้อร่วม:', en: 'Similarity {s} · shared topics:' },
  'in.years.h': { th: 'บทความรายปี', en: 'Articles by year' },
  'in.years.table': { th: 'บทความของสถาบันรายปี', en: 'The institution’s articles by year' },

  'rg.title': { th: 'แผนที่จังหวัด', en: 'Provinces' },
  'rg.lede': { th: 'บทความช่วง {a}–{b} ตามจังหวัดของสถาบันผู้แต่ง บทความที่มีผู้แต่งหลายจังหวัดนับในทุกจังหวัด ระบุจังหวัดได้ {p} ของบทความที่ระบุสังกัดได้', en: 'Articles in {a}–{b} by the province of the authors’ institutions; an article with authors in several provinces counts in each. The province is known for {p} of the articles with a known affiliation.' },
  'rg.metric': { th: 'ตัวชี้วัดบนแผนที่', en: 'Measure on the map' },
  'rg.metric.articles': { th: 'จำนวนบทความ', en: 'Articles' },
  'rg.metric.per100k': { th: 'บทความต่อประชากรแสนคน', en: 'Articles per 100,000 people' },
  'rg.fig': { th: 'ผลผลิตงานวิจัยรายจังหวัด: {m}', en: 'Research output by province: {m}' },
  'rg.map': { th: 'แผนที่จังหวัดของไทย ระบายสีตาม{m} {n} จังหวัดมีข้อมูล ดูตัวเลขทุกจังหวัดได้ในมุมมองตาราง', en: 'Map of Thailand’s provinces shaded by {m}; {n} provinces have data. Every figure is in the table view.' },
  'rg.noData': { th: 'ไม่มีข้อมูล', en: 'No data' },
  'rg.range': { th: '{a} ถึง {b}', en: '{a} to {b}' },
  'rg.table': { th: 'บทความรายจังหวัด', en: 'Articles by province' },
  'rg.col.region': { th: 'ภาค', en: 'Region' },
  'rg.col.share': { th: 'สัดส่วน', en: 'Share' },
  'rg.col.institutions': { th: 'สถาบัน', en: 'Institutions' },
  'rg.col.per100k': { th: 'ต่อแสนคน', en: 'Per 100,000' },
  'rg.col.top': { th: 'สถาบันหลัก', en: 'Main institutions' },
  'rg.region.bangkok': { th: 'กรุงเทพมหานคร', en: 'Bangkok' },
  'rg.region.central': { th: 'ภาคกลาง (รวมตะวันออกและตะวันตก)', en: 'Central (incl. east and west)' },
  'rg.region.northeast': { th: 'ภาคตะวันออกเฉียงเหนือ', en: 'Northeast' },
  'rg.region.north': { th: 'ภาคเหนือ', en: 'North' },
  'rg.region.south': { th: 'ภาคใต้', en: 'South' },
  'rg.regions.h': { th: 'รายภาค', en: 'By region' },
  'rg.regions.table': { th: 'บทความรายภาค', en: 'Articles by region' },
  'rg.provinces.h': { th: 'รายจังหวัด', en: 'By province' },
  'rg.popNote': { th: 'ประชากรจากตารางของผู้ดูแลระบบ ปี {y}', en: 'Population from the maintainers’ table, {y}' },
  'rg.source': { th: 'เส้นขอบจังหวัด: Natural Earth (สาธารณสมบัติ) · ที่มา: TCI Research Atlas รอบข้อมูล {release}', en: 'Province outlines: Natural Earth (public domain) · Source: TCI Research Atlas, release {release}' },

  'sdg.title': { th: 'SDG และแผนชาติ', en: 'SDGs and national plans' },
  'sdg.lede': { th: 'หัวข้อวิจัยจับคู่กับเป้าหมาย SDG และกรอบของไทยด้วย{method} เป็นการจัดกลุ่มโดยเครื่องเพื่อดูภาพรวม ไม่ใช่การจัดประเภทอย่างเป็นทางการ', en: 'Research topics matched to the SDGs and Thai frameworks by {method}. A machine-made grouping for an overview, not an official classification.' },
  'sdg.method.embedding': { th: 'ความคล้ายเชิงความหมายกับคำอธิบายเป้าหมาย', en: 'semantic similarity to the goal descriptions' },
  'sdg.method.lexical': { th: 'คำสำคัญของเป้าหมายในชื่อเรื่องและคำสำคัญของบทความ', en: 'goal keywords in article titles and keywords' },
  'sdg.frameworks': { th: 'กรอบเป้าหมาย', en: 'Frameworks' },
  'sdg.coverage': { th: '{n} จาก {total} เป้าหมายมีหัวข้อวิจัยอย่างน้อย 1 หัวข้อ', en: '{n} of {total} goals have at least one research topic' },
  'sdg.table': { th: 'หัวข้อวิจัยตามเป้าหมาย: {f}', en: 'Research topics by goal: {f}' },
  'sdg.col.goal': { th: 'เป้าหมาย', en: 'Goal' },
  'sdg.col.topics': { th: 'หัวข้อ', en: 'Topics' },
  'sdg.col.ratio': { th: 'เทียบช่วงฐาน', en: 'vs baseline' },
  'sdg.col.examples': { th: 'ตัวอย่างหัวข้อ', en: 'Example topics' },
  'sdg.gap': { th: 'ยังไม่พบหัวข้อ', en: 'No topic yet' },
  'sdg.foot': { th: 'หัวข้อหนึ่งจับคู่ได้หลายเป้าหมาย สัดส่วนรวมจึงอาจเกิน 100% · “เทียบช่วงฐาน” = สัดส่วนบทความช่วงล่าสุดหารด้วยช่วงฐาน', en: 'A topic can match several goals, so shares can add up to more than 100%. “vs baseline” = recent share ÷ baseline share.' },

  'gl.title': { th: 'ไทยเทียบโลก', en: 'Thailand vs the world' },
  'gl.lede': { th: 'ผลงานของประเทศ{c}เทียบกับทั้งโลกใน OpenAlex ราย subfield ช่วงล่าสุด {r} เทียบช่วงฐาน {b}', en: 'Output of {c} compared with the whole world in OpenAlex, by subfield: recent {r} vs baseline {b}' },
  'gl.thailand': { th: 'ไทย', en: 'Thailand' },
  'gl.def': { th: 'อัตราโตของโลก = สัดส่วนของ subfield ในงานทั้งโลก ช่วงล่าสุด ÷ ช่วงฐาน · ดัชนีความเข้มข้น = สัดส่วนของ subfield ในงานของไทย ÷ สัดส่วนในงานทั้งโลก (1 = เท่ากับโลก)', en: 'World growth = the subfield’s share of world output, recent ÷ baseline. Activity index = its share of Thai output ÷ its share of world output (1 = the same as the world).' },
  'gl.opp.h': { th: 'โอกาส: โลกโตเร็ว แต่ไทยยังเล็ก', en: 'Opportunities: the world grows fast, Thailand is small' },
  'gl.opp.intro': { th: 'subfield ที่โลกโตอย่างน้อย {r} เท่า มีงานทั้งโลกอย่างน้อย {n} เรื่อง และดัชนีความเข้มข้นของไทยไม่เกิน {ai}', en: 'Subfields where world output grew at least {r}×, with at least {n} works worldwide and a Thai activity index of at most {ai}' },
  'gl.opp.table': { th: 'subfield ที่เป็นโอกาส', en: 'Opportunity subfields' },
  'gl.all.h': { th: 'ทุก subfield', en: 'Every subfield' },
  'gl.all.table': { th: 'ไทยเทียบโลกราย subfield', en: 'Thailand vs the world by subfield' },
  'gl.col.subfield': { th: 'subfield', en: 'Subfield' },
  'gl.col.ratio': { th: 'อัตราโตของโลก', en: 'World growth' },
  'gl.col.ai': { th: 'ดัชนีความเข้มข้นของไทย', en: 'Thai activity index' },
  'gl.col.share': { th: 'สัดส่วนไทยในโลก', en: 'Thai share of the world' },
  'gl.col.country': { th: 'งานของไทย (OpenAlex)', en: 'Thai works (OpenAlex)' },
  'gl.col.world': { th: 'งานทั้งโลก', en: 'World works' },
  'gl.col.tci': { th: 'บทความใน TCI', en: 'Articles in TCI' },
  'gl.col.topics': { th: 'หัวข้อใน Atlas', en: 'Atlas topics' },
  'gl.opp': { th: 'โอกาส', en: 'Opportunity' },
  'gl.source': { th: 'ที่มา: OpenAlex ({v}) สัญญาอนุญาต CC0 · subfield ตามอนุกรมวิธานของ OpenAlex', en: 'Source: OpenAlex ({v}), CC0 · subfields follow the OpenAlex taxonomy' },

  'gp.title': { th: 'ช่องว่างงานวิจัย', en: 'Research gaps' },
  'gp.lede': { th: 'จุดที่งานวิจัยไทยยังบาง คำนวณจากบทความช่วง {a}–{b} เป็นข้อสังเกตจากข้อมูลเพื่อช่วยตั้งคำถาม ไม่ใช่ข้อสรุป', en: 'Where Thai research is still thin, from articles in {a}–{b}. Signals to start a conversation, not conclusions.' },
  'gp.world.h': { th: 'โลกโตเร็วแต่ไทยยังเล็ก', en: 'The world grows fast, Thailand is small' },
  'gp.world.intro': { th: 'subfield ที่เป็นโอกาสจากหน้าไทยเทียบโลก พร้อมหัวข้อใน Atlas ที่อยู่ใน subfield นั้น', en: 'Opportunity subfields from Thailand vs the world, with the Atlas topics in them' },
  'gp.world.table': { th: 'subfield ที่เป็นโอกาสและหัวข้อที่เกี่ยวข้อง', en: 'Opportunity subfields and their topics' },
  'gp.few.h': { th: 'หัวข้อเกิดใหม่ที่มีสถาบันทำน้อย', en: 'Emerging topics few institutions work on' },
  'gp.few.intro': { th: 'หัวข้อสถานะ{statuses}ที่มีสถาบันทำไม่เกิน {n} แห่งในช่วงล่าสุด', en: '{statuses} topics with at most {n} institutions in the recent window' },
  'gp.few.table': { th: 'หัวข้อที่มีสถาบันทำน้อย', en: 'Topics few institutions work on' },
  'gp.bridge.h': { th: 'หัวข้อเพื่อนบ้านที่ยังไม่ค่อยมีใครเชื่อม', en: 'Neighbouring topics few people connect' },
  'gp.bridge.intro': { th: 'คู่หัวข้อที่เนื้อหาใกล้กัน (ความคล้ายอย่างน้อย {s}) แต่สถาบันที่ทำแทบไม่ซ้ำกัน (Jaccard ไม่เกิน {j}) อาจเป็นโอกาสวิจัยข้ามหัวข้อ', en: 'Topic pairs close in content (similarity at least {s}) whose institutions barely overlap (Jaccard at most {j}) — room for work across them' },
  'gp.bridge.table': { th: 'คู่หัวข้อที่เชื่อมกันน้อย', en: 'Weakly connected topic pairs' },
  'gp.risk.h': { th: 'ความเสี่ยงการกระจุกตัว', en: 'Concentration risk' },
  'gp.risk.intro': { th: 'หัวข้อและสาขาที่มีบทความช่วงล่าสุดอย่างน้อย {m} เรื่อง แต่พึ่งสถาบันหรือวารสารรายเดียว (รายใหญ่สุดอยู่ใน {p} ของบทความขึ้นไป หรือ HHI อย่างน้อย {h})', en: 'Topics and fields with at least {m} recent articles that depend on one institution or journal (the largest is in at least {p} of articles, or HHI at least {h})' },
  'gp.risk.table': { th: 'หน่วยที่พึ่งสถาบันหรือวารสารรายเดียว', en: 'Units that depend on one institution or journal' },
  'gp.risk.all': { th: 'แสดงหน่วยที่ไม่กระจุกตัวด้วย', en: 'Also show units that are not concentrated' },
  'gp.col.unit': { th: 'หัวข้อหรือสาขา', en: 'Topic or field' },
  'gp.col.kind': { th: 'พึ่ง', en: 'Depends on' },
  'gp.col.top': { th: 'รายใหญ่สุด', en: 'Largest' },
  'gp.col.topShare': { th: 'สัดส่วนของรายใหญ่สุด', en: 'Share of the largest' },
  'gp.col.hhi': { th: 'HHI', en: 'HHI' },
  'gp.col.institutions': { th: 'สถาบัน', en: 'Institutions' },
  'gp.col.pair': { th: 'คู่หัวข้อ', en: 'Topic pair' },
  'gp.col.shared': { th: 'สถาบันที่ทำทั้งสอง', en: 'Institutions in both' },
  'gp.kind.institution': { th: 'สถาบัน', en: 'Institution' },
  'gp.kind.journal': { th: 'วารสาร', en: 'Journal' },
  'gp.flag': { th: 'กระจุกตัว', en: 'Concentrated' },
  'gp.withheld': { th: 'สถาบันขนาดเล็ก (ไม่แสดงชื่อ)', en: 'A small institution (not named)' },
  'gp.collab': { th: 'หาสถาบันที่อาจร่วมงาน: เปิดหน้าของสถาบันแล้วดูส่วน “สถาบันที่อาจร่วมงานได้”', en: 'To find possible partners, open an institution’s page and see “Possible partners”.' },
  'gp.collabLink': { th: 'ไปที่รายชื่อสถาบัน', en: 'Go to the institutions' },

  'ov.exec.h': { th: 'ภาพรวมเชิงนโยบาย', en: 'Policy overview' },
  'brief.exec': { th: 'ภาพรวมเชิงนโยบาย', en: 'Policy overview' },
  'brief.execNote': { th: 'ประโยคสร้างจากตัวเลขของระบบ (ประโยคแม่แบบ)', en: 'Sentences built from the system’s figures (templates)' },
})
```

In `web/src/strings/index.ts` add `import { executive } from './executive'` (alphabetical, below `import { emerging } from './emerging'`), append `, executive` as the last entry of `PARTS` and `, ...executive` as the last entry of `STR`.

- [ ] **Step 5: Styles and tokens.** In `web/src/styles/tokens.css` insert below `  --series-4: #eda100;` (light):

```css
  --seq-1: #e4edf6;
  --seq-2: #b9d0e8;
  --seq-3: #7ea8d4;
  --seq-4: #3f74b5;
  --seq-5: #123f7c;
```

and below **each** of the two `--series-4: #c98500;` lines (the OS-dark block and `:root[data-theme="dark"]`; keep each block's indentation):

```css
--seq-1: #1b2a3a;
--seq-2: #24466d;
--seq-3: #2f67a3;
--seq-4: #4f8fd6;
--seq-5: #a6caf3;
```

Create `web/src/styles/executive.css`:

```css
/* P3 executives' pages + the grouped navigation. Tokens only (DESIGN.md). */
@layer components {
  .nav-group { position: relative; }
  .nav-btn { gap: 6px; background: none; border: 0; border-bottom: 4px solid transparent; font: inherit; font-weight: 600; cursor: pointer; }
  .nav-btn.is-active { border-bottom-color: var(--link); }
  .nav-btn svg { transition: transform 120ms ease-out; }
  .nav-btn[aria-expanded="true"] svg { transform: rotate(180deg); }
  .nav-menu { position: absolute; z-index: 40; top: 100%; left: 0; min-width: 15rem; max-width: calc(100vw - 32px); margin: 0; padding: 6px 0; list-style: none; background: var(--bg); border: 1px solid var(--border); box-shadow: var(--shadow); }
  .nav-menu[hidden] { display: none; }
  .nav-menu-link { display: flex; align-items: center; min-height: 44px; padding: 0 16px; color: var(--ink); font-weight: 600; text-decoration: none; }
  .nav-menu-link:hover { color: var(--link); text-decoration: underline; }
  .nav-menu-link[aria-current="page"] { box-shadow: inset 4px 0 0 var(--link); }
  @media (max-width: 640px) { .nav-group { position: static; } .nav-menu { left: 16px; right: 16px; min-width: 0; } }
  @media (prefers-reduced-motion: reduce) { .nav-btn svg { transition: none; } }

  .pmap { display: block; width: 100%; max-width: 440px; height: auto; margin-inline: auto; }
  .pmap path { stroke: var(--bg); stroke-width: 0.8; vector-effect: non-scaling-stroke; }
  .pv-none { fill: var(--surface); }
  .pv-0 { fill: var(--seq-1); }
  .pv-1 { fill: var(--seq-2); }
  .pv-2 { fill: var(--seq-3); }
  .pv-3 { fill: var(--seq-4); }
  .pv-4 { fill: var(--seq-5); }
  .pkey { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 0 0 12px; padding: 0; list-style: none; font-size: 0.875rem; font-variant-numeric: tabular-nums; }
  .pkey li { display: inline-flex; align-items: center; gap: 6px; }
  .sw { display: inline-block; width: 14px; height: 14px; box-shadow: inset 0 0 0 1px var(--border); }
  .sw-none { background: var(--surface); }
  .sw-0 { background: var(--seq-1); }
  .sw-1 { background: var(--seq-2); }
  .sw-2 { background: var(--seq-3); }
  .sw-3 { background: var(--seq-4); }
  .sw-4 { background: var(--seq-5); }
  .metric-switch { display: flex; flex-wrap: wrap; gap: 4px 18px; margin: 14px 0 0; padding: 0; border: 0; }
  .metric-switch legend { font-weight: 600; margin-bottom: 4px; }
  .metric-switch label { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; cursor: pointer; }
  .metric-switch input { width: 18px; height: 18px; margin: 0; accent-color: var(--ink); }
  .sug-list { list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 12px; }
  .sug-list li { display: grid; gap: 4px; padding-bottom: 12px; border-bottom: 1px solid var(--border-2); }
  .sug-topics { display: flex; flex-wrap: wrap; gap: 4px 14px; }
  .exec-points { margin: 12px 0 0; padding-left: 1.2em; display: grid; gap: 8px; max-width: 46em; }
  .sdg-ex { display: grid; gap: 2px; }
  .goal-name strong { font-variant-numeric: tabular-nums; margin-right: 4px; }
  .pair { display: grid; gap: 2px; }
  .flag-on { display: inline-block; margin-left: 6px; padding: 0 6px; border: 2px solid var(--ink); font-size: 0.8125rem; font-weight: 700; line-height: 1.5; }
}
```

In `web/src/styles/index.css` insert below `@import "./editors.css";`: `@import "./executive.css";`.

- [ ] **Step 6: Grouped navigation.** Replace `web/src/components/Header.tsx` with (if P2's polish pass added anything else to this file, keep it):

```tsx
import { useState, type FocusEvent, type KeyboardEvent } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { Wordmark } from '../brand/Wordmark'
import { useI18n } from '../lib/i18n'
import type { StrKey } from '../strings'
import { LangSwitch } from './LangSwitch'
import { ThemeToggle } from './ThemeToggle'
import { TopicSearch } from './TopicSearch'

interface Item {
  to: string
  key: StrKey
}

const START: readonly Item[] = [
  { to: '/overview', key: 'nav.overview' },
  { to: '/atlas', key: 'nav.atlas' },
  { to: '/emerging', key: 'nav.emerging' },
]
/** Pages grouped by who uses them most — every page stays two clicks away. */
const GROUPS: readonly { id: string; key: StrKey; items: readonly Item[] }[] = [
  {
    id: 'nav-exec',
    key: 'nav.group.exec',
    items: [
      { to: '/institutions', key: 'nav.institutions' },
      { to: '/regions', key: 'nav.regions' },
      { to: '/sdg', key: 'nav.sdg' },
      { to: '/global', key: 'nav.global' },
      { to: '/changes', key: 'nav.changes' },
      { to: '/brief', key: 'nav.brief' },
    ],
  },
  { id: 'nav-editors', key: 'nav.group.editors', items: [{ to: '/journals', key: 'nav.journals' }, { to: '/methods', key: 'nav.methods' }] },
  {
    id: 'nav-research',
    key: 'nav.group.research',
    items: [
      { to: '/gaps', key: 'nav.gaps' },
      { to: '/match', key: 'nav.match' },
      { to: '/compare', key: 'nav.compare' },
    ],
  },
]
const END: readonly Item[] = [
  { to: '/data', key: 'nav.data' },
  { to: '/about', key: 'nav.about' },
]

/** A disclosure menu (not an ARIA menu): Enter/Space toggles, Escape closes and returns focus, leaving it closes. */
function NavGroup({ id, label, items, pathname }: { id: string; label: string; items: readonly Item[]; pathname: string }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const active = items.some((i) => pathname === i.to || pathname.startsWith(`${i.to}/`))
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape' && open) {
      setOpen(false)
      e.currentTarget.querySelector('button')?.focus()
    }
  }
  const onBlur = (e: FocusEvent<HTMLDivElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOpen(false)
  }
  return (
    <div className="nav-group" onKeyDown={onKeyDown} onBlur={onBlur}>
      <button type="button" className={`nav-link nav-btn${active ? ' is-active' : ''}`} aria-expanded={open} aria-controls={`${id}-menu`} onClick={() => setOpen((o) => !o)}>
        <span>{label}</span>
        <svg viewBox="0 0 10 6" width="10" height="6" aria-hidden="true" focusable="false">
          <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      </button>
      <ul id={`${id}-menu`} className="nav-menu" hidden={!open}>
        {items.map((i) => (
          <li key={i.to}>
            <NavLink to={i.to} className="nav-menu-link" onClick={() => setOpen(false)}>
              {t(i.key)}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

function SiteSearch() {
  const navigate = useNavigate()
  const { t } = useI18n()
  return <TopicSearch id="site-search" label={t('search.label')} hideLabel onPick={(id) => navigate(`/topics/${id}`)} />
}

export function Header() {
  const { t, lang } = useI18n()
  const { pathname } = useLocation()
  const link = (item: Item) => (
    <li key={item.to}>
      <NavLink to={item.to} className="nav-link">
        {t(item.key)}
      </NavLink>
    </li>
  )
  return (
    <>
      <header className="hdr">
        <div className="container hdr-row">
          <Link to="/overview" className="hdr-wm">
            <Wordmark sub={t('brandSub')} lang={lang} />
          </Link>
          <div className="hdr-tools">
            <LangSwitch />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <nav className="nav" aria-label={t('nav.label')}>
        <div className="container nav-row">
          <ul className="nav-list">
            {START.map(link)}
            {GROUPS.map((g) => (
              <li key={g.id}>
                {/* a new route remounts the group, so an open menu closes after navigation */}
                <NavGroup key={`${g.id}:${pathname}`} id={g.id} label={t(g.key)} items={g.items} pathname={pathname} />
              </li>
            ))}
            {END.map(link)}
          </ul>
          <div className="nav-search">
            <SiteSearch />
          </div>
        </div>
      </nav>
    </>
  )
}
```

- [ ] **Step 7: Fixtures.** In `web/scripts/make-fixtures.mjs` replace `const SCHEMA = '2.1.0'` with `const SCHEMA = '2.2.0'`; insert directly above `function manifest(release, previous, modules, entries, extra = {}) {`:

```js
// ---- P3 executives' modules (contract 2.2): institutions, regions, SDG + BCG, global benchmark, gaps — synthetic, NOT real data
// Institution ids follow the pipeline's rules: alias ids, ror-<id>, o<10 hex>. Topic details link ORGS[0..3] to the first four.
const INSTS = [
  // id, name_th, name_en, type, province, country, source, articles in the window, share with foreign partners
  ['mu-a', 'มหาวิทยาลัยตัวอย่าง ก', 'Example University A', 'university', 'TH-10', 'TH', 'alias', 1840, 0.09],
  ['mu-b', 'มหาวิทยาลัยตัวอย่าง ข', 'Example University B', 'university', 'TH-50', 'TH', 'alias', 1210, 0.12],
  ['rbu-x', 'มหาวิทยาลัยราชภัฏตัวอย่าง', 'Example Rajabhat University', 'rajabhat', 'TH-57', 'TH', 'alias', 640, 0.01],
  ['ror-0example1', 'สถาบันวิจัยตัวอย่าง', 'Example Research Institute', 'research', 'TH-13', 'TH', 'ror', 420, 0.21],
  ['rmu-y', 'มหาวิทยาลัยเทคโนโลยีราชมงคลตัวอย่าง', 'Example Rajamangala University of Technology', 'rajamangala', 'TH-30', 'TH', 'alias', 380, 0.02],
  ['o1a2b3c4d5e', 'โรงพยาบาลตัวอย่าง', '', 'hospital', 'TH-40', 'TH', 'name', 150, 0],
  ['o9f8e7d6c5b', '', 'Example Institute of Technology', 'university', null, null, 'name', 95, 0.04],
  ['o0123456789', '', 'University of Example', 'university', null, 'JP', 'name', 12, 1],
]
const INST_OF_ORG = ['mu-a', 'mu-b', 'rbu-x', 'ror-0example1']
const INST_TOPICS = {
  'mu-a': ['T000101', 'T000102', 'T000106', 'T000701', 'T000702'], 'mu-b': ['T000201', 'T000202', 'T000301', 'T000302'],
  'rbu-x': ['T000201', 'T000203', 'T000601', 'T000806'], 'ror-0example1': ['T000401', 'T000406', 'T000501'],
  'rmu-y': ['T000501', 'T000502', 'T000505'], 'o1a2b3c4d5e': ['T000101', 'T000801', 'T000802', 'T000806'],
  'o9f8e7d6c5b': ['T000703', 'T000704'], 'o0123456789': ['T000701'],
}
const EDGES = [['mu-a', 'mu-b', 214], ['mu-a', 'ror-0example1', 121], ['mu-b', 'rbu-x', 64], ['mu-a', 'o1a2b3c4d5e', 48], ['rbu-x', 'rmu-y', 22], ['mu-b', 'o0123456789', 9]]
const COUNTRY = { JP: ['ญี่ปุ่น', 'Japan'], CN: ['จีน', 'China'], US: ['สหรัฐอเมริกา', 'United States'], LA: ['ลาว', 'Laos'], GB: ['สหราชอาณาจักร', 'United Kingdom'] }
const NATIONAL = [['JP', 210], ['CN', 160], ['US', 120], ['LA', 64], ['GB', 51]]
const INST_COUNTRIES = { 'mu-a': [['JP', 80], ['US', 41]], 'mu-b': [['JP', 60], ['LA', 20]], 'ror-0example1': [['CN', 40]] }
const SUGGEST = {
  'mu-a': [{ id: 'rmu-y', similarity: 0.41, topics: ['T000106'] }],
  'rbu-x': [{ id: 'o1a2b3c4d5e', similarity: 0.36, topics: ['T000806'] }],
  'ror-0example1': [{ id: 'rmu-y', similarity: 0.58, topics: ['T000501'] }],
}
const PROVINCE_NAMES = {
  'TH-10': ['กรุงเทพมหานคร', 'Bangkok'], 'TH-13': ['ปทุมธานี', 'Pathum Thani'], 'TH-20': ['ชลบุรี', 'Chon Buri'],
  'TH-30': ['นครราชสีมา', 'Nakhon Ratchasima'], 'TH-34': ['อุบลราชธานี', 'Ubon Ratchathani'], 'TH-40': ['ขอนแก่น', 'Khon Kaen'],
  'TH-44': ['มหาสารคาม', 'Maha Sarakham'], 'TH-50': ['เชียงใหม่', 'Chiang Mai'], 'TH-57': ['เชียงราย', 'Chiang Rai'],
  'TH-65': ['พิษณุโลก', 'Phitsanulok'], 'TH-83': ['ภูเก็ต', 'Phuket'], 'TH-90': ['สงขลา', 'Songkhla'],
}
// code, articles (window), recent, population (null = not in the population table)
const PROVINCES = [
  ['TH-10', 5210, 3290, 5500000], ['TH-50', 2140, 1360, 1800000], ['TH-40', 1530, 990, 1790000], ['TH-90', 1380, 860, 1430000],
  ['TH-13', 1220, 800, 1200000], ['TH-65', 960, 600, 860000], ['TH-30', 870, 540, 2630000], ['TH-57', 720, 450, 1300000],
  ['TH-20', 650, 430, null], ['TH-44', 610, 380, 960000], ['TH-34', 480, 300, 1870000], ['TH-83', 210, 140, null],
]
const regionOf = (code) => {
  const n = Number(code.slice(3))
  return n === 10 ? 'bangkok' : n <= 27 || (n >= 70 && n <= 77) ? 'central' : n <= 49 ? 'northeast' : n <= 67 ? 'north' : 'south'
}
const SDG_NAMES = [
  ['ขจัดความยากจน', 'No poverty'], ['ขจัดความหิวโหย', 'Zero hunger'], ['สุขภาพและความเป็นอยู่ที่ดี', 'Good health and well-being'],
  ['การศึกษาที่มีคุณภาพ', 'Quality education'], ['ความเท่าเทียมทางเพศ', 'Gender equality'], ['น้ำสะอาดและการสุขาภิบาล', 'Clean water and sanitation'],
  ['พลังงานสะอาดที่เข้าถึงได้', 'Affordable and clean energy'], ['งานที่มีคุณค่าและการเติบโตทางเศรษฐกิจ', 'Decent work and economic growth'],
  ['อุตสาหกรรม นวัตกรรม และโครงสร้างพื้นฐาน', 'Industry, innovation and infrastructure'], ['ลดความเหลื่อมล้ำ', 'Reduced inequalities'],
  ['เมืองและชุมชนที่ยั่งยืน', 'Sustainable cities and communities'], ['การผลิตและการบริโภคที่ยั่งยืน', 'Responsible consumption and production'],
  ['การรับมือการเปลี่ยนแปลงสภาพภูมิอากาศ', 'Climate action'], ['ทรัพยากรทางทะเล', 'Life below water'], ['ระบบนิเวศบนบก', 'Life on land'],
  ['สันติภาพ ความยุติธรรม และสถาบันที่เข้มแข็ง', 'Peace, justice and strong institutions'], ['ความร่วมมือเพื่อการพัฒนาที่ยั่งยืน', 'Partnerships for the goals'],
]
const SDG_TOPICS = {
  2: ['T000401', 'T000403'], 3: ['T000101', 'T000102', 'T000103', 'T000801', 'T000802', 'T000805'], 4: ['T000201', 'T000202', 'T000203', 'T000803'],
  6: ['T000504'], 7: ['T000501'], 8: ['T000301', 'T000302', 'T000303'], 9: ['T000502', 'T000506', 'T000702', 'T000703'], 13: ['T000504'],
  14: ['T000406', 'T000403'], 15: ['T000404'],
}
const BCG = [['bcg-bio', 'เศรษฐกิจชีวภาพ', 'Bio-economy', ['T000104', 'T000401']], ['bcg-circular', 'เศรษฐกิจหมุนเวียน', 'Circular economy', ['T000406']], ['bcg-green', 'เศรษฐกิจสีเขียว', 'Green economy', ['T000501', 'T000502', 'T000306']]]
// id, name, group, world recent, world baseline, Thailand recent, Thailand baseline, Atlas topics
const SUBFIELDS = [
  ['1702', 'Artificial Intelligence', 'F17', 182000, 210000, 1450, 1300, ['T000701']],
  ['1710', 'Information Systems', 'F17', 96000, 160000, 2100, 2600, ['T000705']],
  ['3304', 'Education', 'F33', 140000, 230000, 6900, 9800, ['T000201', 'T000202', 'T000203']],
  ['2739', 'Public Health, Environmental and Occupational Health', 'F27', 260000, 470000, 7400, 11000, ['T000101', 'T000103']],
  ['1406', 'Marketing', 'F14', 52000, 84000, 1900, 2500, ['T000301']],
  ['1102', 'Agronomy and Crop Science', 'F11', 61000, 110000, 2600, 4100, ['T000401']],
  ['2208', 'Electrical and Electronic Engineering', 'F22', 150000, 240000, 2300, 3300, ['T000501', 'T000502']],
  ['2310', 'Pollution', 'F23', 74000, 80000, 420, 300, []],
  ['2105', 'Renewable Energy, Sustainability and the Environment', 'F21', 98000, 104000, 900, 700, []],
  ['1212', 'Religious studies', 'F12', 9000, 16000, 600, 900, ['T000601']],
  ['2902', 'Advanced and Specialized Nursing', 'F29', 21000, 39000, 1600, 2300, ['T000801']],
]

function buildExecutives(files) {
  const topics = files['topics.json'].topics
  const byId = new Map(topics.map((t) => [t.id, t]))
  const sumOf = (ids, f) => sum(ids.map((id) => f(byId.get(id))))
  const named = (code, articles) => ({ code, name_th: COUNTRY[code][0], name_en: COUNTRY[code][1], articles })
  for (const [path, d] of Object.entries(files)) {
    if (!path.startsWith('topics/')) continue
    d.institutions = d.institutions.map((c) => {
      const k = ORGS.indexOf(c.key)
      return k >= 0 ? { ...c, id: INST_OF_ORG[k] } : c
    })
  }
  for (const t of topics) t.sdg = Object.entries(SDG_TOPICS).filter(([, ids]) => ids.includes(t.id)).map(([n]) => Number(n))

  // institutions.json + institutions/<id>.json
  const partnersOf = (id) => EDGES.filter(([a, b]) => a === id || b === id).map(([a, b, n]) => ({ id: a === id ? b : a, articles: n })).sort((x, y) => y.articles - x.articles)
  const summaries = INSTS.map(([id, th, en, type, province, country, source, articles, intl]) => ({
    id, name_th: th, name_en: en, type, province, country, source, ror: source === 'ror' ? '0example1' : '',
    articles, articles_total: Math.round(articles * 2.1), articles_recent: Math.round(articles * 0.62), intl_share: intl,
    partners: partnersOf(id).length, topics: INST_TOPICS[id].length, group: byId.get(INST_TOPICS[id][0]).group,
  }))
  files['institutions.json'] = {
    schema_version: SCHEMA, window: { start: 2020, end: 2024 }, recent: { start: 2022, end: 2024 }, min_articles: 5, network_min_articles: 3,
    articles_with_org: 16900, pct_international: 0.068, pct_multi_institution: 0.314, sources: { alias: 4, ror: 1, name: 3 },
    institutions: summaries, edges: EDGES.map(([a, b, articles]) => ({ a, b, articles })), countries: NATIONAL.map(([c, n]) => named(c, n)),
    province_names: [...new Set(summaries.map((s) => s.province).filter(Boolean))].sort().map((code) => ({ code, name_th: PROVINCE_NAMES[code][0], name_en: PROVINCE_NAMES[code][1] })),
  }
  for (const s of summaries) {
    const tl = INST_TOPICS[s.id]
    const w = tl.map((_, i) => 1 / (i + 1.5))
    const ws = sum(w) / 0.8
    files[`institutions/${s.id}.json`] = {
      schema_version: SCHEMA, id: s.id,
      years: YEARS.map((year, i) => ({ year, articles: Math.round((s.articles_total / 10) * (0.7 + 0.06 * i)) })),
      topics: tl.map((topic, i) => ({ topic, count: Math.round((s.articles * w[i]) / ws), share: r4(w[i] / ws) })),
      partners: partnersOf(s.id), countries: (INST_COUNTRIES[s.id] ?? []).map(([c, n]) => named(c, n)), suggested: SUGGEST[s.id] ?? [],
    }
  }

  // regions.json — an article with authors in two provinces counts in both, so shares add up to more than 1
  const located = 14200
  files['regions.json'] = {
    schema_version: SCHEMA, window: { start: 2020, end: 2024 }, articles_with_org: 16900, articles_located: located, coverage: r4(located / 16900), population_year: 2024,
    provinces: PROVINCES.map(([code, articles, recent, pop]) => ({
      code, name_th: PROVINCE_NAMES[code][0], name_en: PROVINCE_NAMES[code][1], region: regionOf(code), articles, articles_recent: recent,
      share: r4(articles / located), institutions: summaries.filter((s) => s.province === code).length,
      per_100k: pop ? Number(((100000 * articles) / pop).toFixed(2)) : null, top: summaries.filter((s) => s.province === code).map((s) => s.id).slice(0, 3),
    })),
    regions: ['bangkok', 'central', 'northeast', 'north', 'south'].map((key) => {
      const a = sum(PROVINCES.filter(([c]) => regionOf(c) === key).map(([, n]) => n))
      return { key, articles: a, share: r4(a / located) }
    }),
  }

  // sdg.json — SDGs and BCG; goals without topics are the gaps the page lists
  const goal = (id, framework, number, th, en, ids) => {
    const sR = sumOf(ids, (t) => t.metrics.share_recent)
    const sB = sumOf(ids, (t) => t.metrics.share_baseline)
    return { id, framework, number, th, en, topics: ids, articles_recent: sumOf(ids, (t) => t.metrics.count_recent), share_recent: r6(sR), share_ratio: sB > 0 ? r4(sR / sB) : null }
  }
  files['sdg.json'] = {
    schema_version: SCHEMA, method: 'lexical', version: '1-fixture',
    frameworks: [{ key: 'sdg', th: 'เป้าหมายการพัฒนาที่ยั่งยืน (SDGs)', en: 'Sustainable Development Goals' }, { key: 'bcg', th: 'โมเดลเศรษฐกิจ BCG', en: 'BCG economy model' }],
    goals: [
      ...SDG_NAMES.map(([th, en], i) => goal(`sdg-${String(i + 1).padStart(2, '0')}`, 'sdg', i + 1, th, en, SDG_TOPICS[i + 1] ?? [])),
      ...BCG.map(([id, th, en, ids], i) => goal(id, 'bcg', i + 1, th, en, ids)),
    ],
  }

  // global.json — share-based world growth and activity index, computed as the pipeline does
  const WR = sum(SUBFIELDS.map((s) => s[3]))
  const WB = sum(SUBFIELDS.map((s) => s[4]))
  const CR = sum(SUBFIELDS.map((s) => s[5]))
  const bench = SUBFIELDS.map(([id, en, group, wr, wb, cr, cb, tl]) => {
    const ratio = wr / WR / (wb / WB)
    const ai = cr / CR / (wr / WR)
    return {
      id, en, group, world_recent: wr, world_baseline: wb, country_recent: cr, country_baseline: cb, tci_recent: sumOf(tl, (t) => t.metrics.count_recent),
      world_ratio: r4(ratio), activity_index: r4(ai), country_share: r6(cr / wr), opportunity: wr >= 1000 && ratio >= 1.2 && ai <= 0.5, topics: tl,
    }
  })
  files['global.json'] = {
    schema_version: SCHEMA, source: 'openalex@fixture', country: 'TH', recent: { start: 2022, end: 2024 }, baseline: { start: 2017, end: 2021 },
    min_world_works: 1000, min_world_ratio: 1.2, max_activity_index: 0.5, subfields: bench,
  }

  // gaps.json
  files['gaps.json'] = {
    schema_version: SCHEMA, recent: { start: 2022, end: 2024 }, statuses: ['EMERGING', 'WATCH'], max_institutions: 5, bridge_min_similarity: 0.6, bridge_max_jaccard: 0.1,
    min_articles: 30, max_top_share: 0.5, max_hhi: 0.25,
    few_institutions: [{ topic: 'T000406', institutions: 3 }, { topic: 'T000806', institutions: 2 }],
    bridges: [{ a: 'T000201', b: 'T000701', similarity: 0.82, shared: 1, jaccard: 0.05 }, { a: 'T000106', b: 'T000701', similarity: 0.77, shared: 0, jaccard: 0 }],
    world: bench.filter((b) => b.opportunity).map((b) => ({ subfield: b.id, en: b.en, world_ratio: b.world_ratio, activity_index: b.activity_index, topics: b.topics })),
    concentration: [
      { scope: 'topic', id: 'T000806', kind: 'institution', articles: 41, hhi: 0.58, top_share: 0.71, top: 'rbu-x', top_name: 'มหาวิทยาลัยราชภัฏตัวอย่าง', concentrated: true },
      { scope: 'topic', id: 'T000305', kind: 'journal', articles: 64, hhi: 0.62, top_share: 0.78, top: 'so02.example1', top_name: JOURNALS[1], concentrated: true },
      { scope: 'group', id: 'F12', kind: 'journal', articles: 812, hhi: 0.21, top_share: 0.38, top: 'so02.example4', top_name: JOURNALS[4], concentrated: false },
      { scope: 'topic', id: 'T000101', kind: 'institution', articles: 300, hhi: 0.08, top_share: 0.22, top: 'mu-a', top_name: 'มหาวิทยาลัยตัวอย่าง ก', concentrated: false },
    ],
  }

  // KPI additions (percent, like pct_abstract_en) and the policy sentences
  const ov = files['overview.json']
  ov.kpis = { ...ov.kpis, pct_international: 6.8, pct_multi_institution: 31.4, provinces: PROVINCES.length }
  ov.executive = {
    bullets_th: [
      'จังหวัดที่มีบทความมากที่สุด: กรุงเทพมหานคร (5,210), เชียงใหม่ (2,140), ขอนแก่น (1,530), สงขลา (1,380), ปทุมธานี (1,220) จากบทความที่ระบุจังหวัดได้ 14,200 เรื่อง (ข้อมูลตัวอย่าง)',
      'บทความ 6.8% มีผู้แต่งร่วมจากต่างประเทศ ประเทศคู่ความร่วมมือหลัก: ญี่ปุ่น, จีน, สหรัฐอเมริกา',
      'หัวข้อวิจัยครอบคลุม 10 จาก 17 เป้าหมาย SDG ยังไม่พบหัวข้อใน SDG 1 ขจัดความยากจน, SDG 5 ความเท่าเทียมทางเพศ, SDG 10 ลดความเหลื่อมล้ำ',
    ],
    bullets_en: [
      'Provinces with the most articles: Bangkok (5,210), Chiang Mai (2,140), Khon Kaen (1,530), Songkhla (1,380), Pathum Thani (1,220), of 14,200 articles with a known province (sample data)',
      '6.8% of articles have a foreign co-author; main partner countries: Japan, China, United States',
      'Research topics cover 10 of 17 SDGs; none yet for SDG 1 No poverty, SDG 5 Gender equality, SDG 10 Reduced inequalities',
    ],
    source: 'template',
  }
  return ['institutions', 'institution_detail', 'regions', 'sdg', 'global', 'gaps']
}
```

Below `const editorModules = buildEditors(ex.files, ex.previousOverview)` insert `const execModules = buildExecutives(ex.files)`, and replace `'keywords', ...editorModules], entries, {` with `'keywords', ...editorModules, ...execModules], entries, {`. In the empty release's `manifest(RELEASE, null, [...], entries, { trimmed_years: [] })` call replace `{ trimmed_years: [] }` with `{ trimmed_years: [], skipped_modules: { global: 'OpenAlex unavailable: ATLAS_OFFLINE=1 — network access disabled' } }`. Run `npm run fixtures`.

- [ ] **Step 8: e2e.** In `web/e2e/smoke.spec.ts` replace `    await expect(page.locator('#modules .dl-list li')).toHaveCount(4)` with `    await expect(page.locator('#modules .dl-list li')).toHaveCount(9)`, replace `    await expect(page.locator('.kpi')).toHaveCount(6)` with `    await expect(page.locator('.kpi')).toHaveCount(8)` and `    await expect(page.locator('.brief-t').first().locator('tbody tr')).toHaveCount(5)` with `    await expect(page.locator('.brief-t').first().locator('tbody tr')).toHaveCount(7)` (the example release now carries the two P3 KPIs), and append at the end of the file:

```ts
test('the grouped navigation opens with the keyboard, closes with Escape and marks the current group', async ({ page }) => {
  await page.goto(`${EXAMPLE}#/overview`)
  const exec = page.getByRole('button', { name: 'สำหรับผู้บริหาร' })
  await expect(exec).toHaveAttribute('aria-expanded', 'false')
  await exec.focus()
  await page.keyboard.press('Enter')
  await expect(exec).toHaveAttribute('aria-expanded', 'true')
  await expect(page.locator('#nav-exec-menu a')).toHaveCount(6)
  await page.keyboard.press('Escape')
  await expect(exec).toHaveAttribute('aria-expanded', 'false')
  await expect(exec).toBeFocused()
  const editors = page.getByRole('button', { name: 'สำหรับบรรณาธิการ' })
  await editors.click()
  await page.locator('#nav-editors-menu').getByRole('link', { name: 'วารสาร' }).click()
  await expect(page).toHaveURL(/#\/journals$/)
  await expect(page.getByRole('button', { name: 'สำหรับบรรณาธิการ' })).toHaveClass(/is-active/)
  await expect(page.locator('#nav-editors-menu')).toBeHidden()
})
```

- [ ] **Step 9: Run the gate**

Run: `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e`
Expected: PASS (fixtures validate against the 2.2 schema; /data lists 9 module files; the nav test passes; the six new routes are not routed yet — Tasks 8–11).

- [ ] **Step 10: Commit**

```bash
git add src/data src/lib/executive.ts src/lib/executive.test.ts src/strings src/styles src/components/Header.tsx src/components/ModuleFile.tsx src/pages/data/ModuleDownloads.tsx scripts/make-fixtures.mjs fixtures e2e/smoke.spec.ts
git commit -m "feat(web): contract 2.2 data layer and fixtures, grouped navigation (executives / editors / researchers), P3 strings and tokens

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 8: `/institutions`, `/institutions/:id` and institution links on topic pages (E7, D6, R6)

Invoke `impeccable` (craft) for "an institution index and an institution profile for executives: civic tables (output, international share, partners, province), partnership and partner-country tables, a 'possible partners' list that reads as a suggestion, not a ranking; DESIGN.md tokens; Thai typography" and keep DESIGN.md's table and summary specs.

**Files:**
- Create: `web/src/components/InstitutionLink.tsx`, `web/src/pages/InstitutionsPage.tsx`, `web/src/pages/InstitutionPage.tsx`
- Modify: `web/src/lib/urlState.ts`, `web/src/pages/TopicPage.tsx`, `web/src/App.tsx`, `web/e2e/smoke.spec.ts`

**Interfaces:**
- Consumes: Task 7 (`InstitutionsFile`, `InstitutionDetail`, `InstitutionSummary`, `CollabEdge`, `CountryCount`, `Partner`, `Suggestion`, `instName`, `otherInstName`, `filterInstitutions`, strings `in.*`), P2 (`ModuleFile`, `useReleaseFile`, `ShareBar`, `DataTable`, `TopicLink`, `OnThisPage`).
- Produces: `<InstitutionLink inst>`; `urlState` — `INST_SORTS`, `type InstSort`, `INST_TYPE_FILTERS`, `institutionsCodec`; routes `institutions`, `institutions/:id`; section ids `#institutions`, `#partnerships`, `#countries` (index) and `#numbers`, `#topics`, `#partners`, `#abroad`, `#suggested`, `#years` (profile).

- [ ] **Step 1: Write the failing e2e checks.** In `web/e2e/smoke.spec.ts` insert directly above the `] as const` that closes `ROUTES`:

```ts
  { name: 'institutions', path: '/institutions' },
  { name: 'institution', path: '/institutions/mu-a' },
```

insert directly above `  // checks:end`:

```ts
  institutions: async (page) => {
    const rows = page.locator('#institutions tbody tr')
    await expect(rows).toHaveCount(8)
    await page.getByLabel('ประเภทสถาบัน').selectOption('rajabhat')
    await expect(rows).toHaveCount(1)
    await expect(page).toHaveURL(/type=rajabhat/)
    await page.getByLabel('ประเภทสถาบัน').selectOption('all')
    await expect(page.locator('#partnerships tbody tr')).toHaveCount(6)
    await expect(page.locator('#countries')).toContainText('ญี่ปุ่น')
    await page.locator('#institutions').getByRole('link', { name: 'มหาวิทยาลัยตัวอย่าง ก' }).click()
    await expect(page).toHaveURL(/#\/institutions\/mu-a$/)
  },
  institution: async (page) => {
    await expect(page.locator('h1')).toHaveText('มหาวิทยาลัยตัวอย่าง ก')
    await expect(page.locator('#topics tbody tr')).toHaveCount(5)
    await expect(page.locator('#suggested')).toContainText('มหาวิทยาลัยเทคโนโลยีราชมงคลตัวอย่าง')
    await page.goto(`${EXAMPLE}#/topics/T000101`)
    await expect(page.locator('#orgs a[href$="/institutions/mu-a"]').first()).toBeVisible()
    await page.goto(`${EXAMPLE}#/institutions/nowhere`)
    await expect(page.locator('h1')).toContainText('nowhere')
  },
```

and append `'/institutions', '/institutions/mu-a'` to the `PHONE` array (before its closing `]`).

Run: `npm run build && npx playwright test -g "institution"` — Expected: FAIL (the routes are not found).

- [ ] **Step 2: URL state and the link.** Append to `web/src/lib/urlState.ts`:

```ts
export const INST_SORTS = ['name', 'province', 'articles', 'recent', 'intl', 'partners'] as const
export type InstSort = (typeof INST_SORTS)[number]
export const INST_TYPE_FILTERS = ['all', 'university', 'rajabhat', 'rajamangala', 'hospital', 'government', 'research', 'company', 'other'] as const
export interface InstitutionsUrlState {
  q: string
  type: (typeof INST_TYPE_FILTERS)[number]
  sort: InstSort
  dir: 'asc' | 'desc'
}
export const institutionsCodec = makeCodec<InstitutionsUrlState>({
  q: text('q', 80),
  type: oneOf('type', INST_TYPE_FILTERS, 'all'),
  sort: oneOf('sort', INST_SORTS, 'articles'),
  dir: oneOf('dir', ['asc', 'desc'] as const, 'desc'),
})
```

Create `web/src/components/InstitutionLink.tsx`:

```tsx
import { Link } from 'react-router'
import type { InstitutionSummary } from '../data/types'
import { instName } from '../lib/executive'
import { useI18n } from '../lib/i18n'

/** An institution's name linking to /institutions/:id (the other language's name carries its lang attribute). */
export function InstitutionLink({ inst }: { inst: Pick<InstitutionSummary, 'id' | 'name_th' | 'name_en'> }) {
  const { lang } = useI18n()
  const n = instName(inst, lang)
  return (
    <Link to={`/institutions/${inst.id}`} className="topic-link">
      <span lang={n.lang ?? undefined}>{n.text}</span>
    </Link>
  )
}
```

- [ ] **Step 3: The index.** Create `web/src/pages/InstitutionsPage.tsx`:

```tsx
import { DataTable, type Column } from '../components/DataTable'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { groupName, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CollabEdge, CountryCount, InstitutionSummary, InstitutionsFile } from '../data/types'
import { filterInstitutions, instName } from '../lib/executive'
import { DASH, fmtInt, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { INST_SORTS, INST_TYPE_FILTERS, institutionsCodec, type InstSort } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'

export default function InstitutionsPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('in.title')}>
      {(release) => (
        <ModuleFile<InstitutionsFile> release={release} module="institutions" path={MODULE_FILES.institutions} title={t('in.title')}>
          {(file) => <Institutions release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

const isSort = (v: string): v is InstSort => (INST_SORTS as readonly string[]).includes(v)

function Institutions({ release, file }: { release: AtlasRelease; file: InstitutionsFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(institutionsCodec)
  const w = file.window
  const rows = filterInstitutions(file.institutions, state.q, state.type)
  const byId = new Map(file.institutions.map((i) => [i.id, i]))
  const provinces = new Map((file.province_names ?? []).map((p) => [p.code, p]))
  const place = (i: InstitutionSummary): string => {
    if (i.province) {
      const p = provinces.get(i.province)
      return p ? (lang === 'en' ? p.name_en : p.name_th) : i.province
    }
    return i.country && i.country !== 'TH' ? t('in.abroad', { c: i.country }) : t('in.unplaced')
  }
  const columns: Column<InstitutionSummary>[] = [
    { key: 'id', header: 'id', csvHeader: 'institution_id', cell: () => null, csv: (i) => i.id, csvOnly: true },
    {
      key: 'name', header: t('col.institution'), rowHeader: true, cell: (i) => <InstitutionLink inst={i} />, sortValue: (i) => instName(i, lang).text,
      csvCols: [{ header: 'name_th', value: (i) => i.name_th ?? '' }, { header: 'name_en', value: (i) => i.name_en ?? '' }],
    },
    { key: 'type', csvHeader: 'type', header: t('in.col.type'), cell: (i) => t(`in.type.${i.type ?? 'other'}` as StrKey), csv: (i) => i.type ?? 'other' },
    { key: 'province', csvHeader: 'province', header: t('in.col.province'), cell: place, sortValue: place, csv: (i) => i.province ?? '' },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (i) => fmtInt(i.articles), sortValue: (i) => i.articles },
    { key: 'recent', csvHeader: 'articles_recent', header: t('in.col.recent'), numeric: true, cell: (i) => fmtInt(i.articles_recent ?? 0), sortValue: (i) => i.articles_recent ?? 0 },
    { key: 'intl', csvHeader: 'intl_share', header: t('in.col.intl'), numeric: true, cell: (i) => <ShareBar value={i.intl_share} />, sortValue: (i) => i.intl_share ?? null },
    { key: 'partners', csvHeader: 'partners', header: t('in.col.partners'), numeric: true, cell: (i) => fmtInt(i.partners ?? 0), sortValue: (i) => i.partners ?? 0 },
    { key: 'group', csvHeader: 'group', header: t('col.field'), cell: (i) => (i.group ? groupName(release, i.group, lang) : DASH), csv: (i) => i.group ?? '' },
  ]
  const valid = columns.some((c) => c.key === state.sort && c.sortValue)
  const edges = (file.edges ?? []).filter((e) => byId.has(e.a) && byId.has(e.b))
  const edgeColumns: Column<CollabEdge>[] = [
    {
      key: 'pair', csvHeader: 'institution_a', header: t('in.col.pair'), rowHeader: true,
      cell: (e) => (
        <span className="pair">
          <InstitutionLink inst={byId.get(e.a) as InstitutionSummary} />
          <InstitutionLink inst={byId.get(e.b) as InstitutionSummary} />
        </span>
      ),
      csvCols: [{ header: 'institution_a', value: (e) => e.a }, { header: 'institution_b', value: (e) => e.b }],
    },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (e) => fmtInt(e.articles), sortValue: (e) => e.articles },
  ]
  const countries = file.countries ?? []
  const countryColumns: Column<CountryCount>[] = [
    { key: 'name', csvHeader: 'country', header: t('in.col.country'), rowHeader: true, cell: (c) => (lang === 'en' ? c.name_en : c.name_th), sortValue: (c) => (lang === 'en' ? c.name_en : c.name_th), csv: (c) => c.code },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  const rel = release.overview.release
  return (
    <div className="container">
      <PageHeader title={t('in.title')} lede={t('in.lede', { n: fmtInt(file.min_articles), a: w.start, b: w.end })} />
      <Section id="glance" title={t('in.kpi.h')}>
        <dl className="summary">
          <div>
            <dt>{t('in.kpi.shown')}</dt>
            <dd>{fmtInt(file.institutions.length)}<small>{t('in.kpi.shownSub', { n: fmtInt(file.min_articles), a: w.start, b: w.end })}</small></dd>
          </div>
          <div>
            <dt>{t('in.kpi.intl')}</dt>
            <dd>{fmtPct(file.pct_international ?? null, 1)}<small>{t('in.kpi.intlSub', { n: fmtInt(file.articles_with_org) })}</small></dd>
          </div>
          <div>
            <dt>{t('in.kpi.multi')}</dt>
            <dd>{fmtPct(file.pct_multi_institution ?? null, 1)}</dd>
          </div>
        </dl>
      </Section>
      <div className="j-tools">
        <label>
          {t('in.search')}
          <input type="search" value={state.q} onChange={(e) => update({ q: e.target.value })} />
        </label>
        <label>
          {t('in.type')}
          <select value={state.type} onChange={(e) => update({ type: (INST_TYPE_FILTERS as readonly string[]).includes(e.target.value) ? (e.target.value as (typeof INST_TYPE_FILTERS)[number]) : 'all' })}>
            {INST_TYPE_FILTERS.map((ty) => (
              <option key={ty} value={ty}>{t(`in.type.${ty}` as StrKey)}</option>
            ))}
          </select>
        </label>
        <p className="hint" role="status">{t('in.count', { n: fmtInt(rows.length), total: fmtInt(file.institutions.length) })}</p>
      </div>
      <Section id="institutions" title={t('in.table', { a: w.start, b: w.end })}>
        <DataTable
          caption={t('table.n', { n: 1, title: t('in.table', { a: w.start, b: w.end }) })}
          rows={rows}
          columns={columns}
          rowKey={(i) => i.id}
          sort={valid ? { key: state.sort, dir: state.dir } : { key: 'articles', dir: 'desc' }}
          onSort={(s) => update({ sort: isSort(s.key) ? s.key : 'articles', dir: s.dir })}
          csvFilename={`atlas-${rel}-institutions.csv`}
          empty={t('in.none')}
          footnote={t('in.foot')}
        />
      </Section>
      {edges.length ? (
        <Section id="partnerships" title={t('in.pairs.h')} intro={t('in.pairs.intro', { a: w.start, b: w.end, n: fmtInt(file.network_min_articles) })}>
          <DataTable caption={t('table.n', { n: 2, title: t('in.pairs.table') })} rows={edges} columns={edgeColumns} rowKey={(e) => `${e.a}~${e.b}`} defaultSort={{ key: 'articles', dir: 'desc' }} csvFilename={`atlas-${rel}-partnerships.csv`} />
        </Section>
      ) : null}
      {countries.length ? (
        <Section id="countries" title={t('in.countries.h')} intro={t('in.countries.intro', { a: w.start, b: w.end })}>
          <DataTable caption={t('table.n', { n: 3, title: t('in.countries.table') })} rows={countries} columns={countryColumns} rowKey={(c) => c.code} defaultSort={{ key: 'articles', dir: 'desc' }} csvFilename={`atlas-${rel}-partner-countries.csv`} />
        </Section>
      ) : null}
    </div>
  )
}
```

- [ ] **Step 4: The profile.** Create `web/src/pages/InstitutionPage.tsx`:

```tsx
import { Link, useParams } from 'react-router'
import { DataTable, type Column } from '../components/DataTable'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { OnThisPage } from '../components/OnThisPage'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CountryCount, InstitutionDetail, InstitutionSummary, InstitutionsFile, Partner, Topic, TopicShare } from '../data/types'
import { instName, otherInstName } from '../lib/executive'
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import type { StrKey } from '../strings'

export default function InstitutionPage() {
  const { id } = useParams()
  const { t } = useI18n()
  return (
    <RequireRelease title={t('in.title')}>
      {(release) => (
        <ModuleFile<InstitutionsFile> release={release} module="institutions" path={MODULE_FILES.institutions} title={t('in.title')}>
          {(file) => <InstitutionView release={release} file={file} id={id ?? ''} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function InstitutionView({ release, file, id }: { release: AtlasRelease; file: InstitutionsFile; id: string }) {
  const { t } = useI18n()
  const inst = file.institutions.find((i) => i.id === id)
  if (!inst) {
    return (
      <div className="container">
        <PageHeader title={t('in.notFound', { id: id || DASH })} lede={t('in.notFound.body')} />
        <p className="mt-6"><Link to="/institutions">{t('in.back')}</Link></p>
      </div>
    )
  }
  return <InstitutionContent key={inst.id} release={release} file={file} inst={inst} />
}

function InstitutionContent({ release, file, inst }: { release: AtlasRelease; file: InstitutionsFile; inst: InstitutionSummary }) {
  const { t, lang } = useI18n()
  const detailFile = useReleaseFile<InstitutionDetail>(`institutions/${inst.id}.json`)
  const detail = detailFile.status === 'ready' ? detailFile.data : null
  const byId = new Map(file.institutions.map((i) => [i.id, i]))
  const topicOf = (tid: string): Topic | undefined => release.topicById.get(tid)
  const topics = (detail?.topics ?? []).filter((s) => topicOf(s.topic))
  const signals = topics.map((s) => topicOf(s.topic) as Topic).filter((tp) => tp.status === 'EMERGING' || tp.status === 'WATCH')
  const partners = (detail?.partners ?? []).filter((p) => byId.has(p.id))
  const countries = detail?.countries ?? []
  const suggested = (detail?.suggested ?? []).filter((s) => byId.has(s.id))
  const years = detail?.years ?? []
  const shown = instName(inst, lang)
  const other = otherInstName(inst, lang)
  const province = (file.province_names ?? []).find((p) => p.code === inst.province)
  const place = province ? (lang === 'en' ? province.name_en : province.name_th) : inst.country && inst.country !== 'TH' ? t('in.abroad', { c: inst.country }) : t('in.unplaced')
  const w = file.window
  const r = file.recent
  const rel = release.overview.release
  const toc = [
    { id: 'numbers', label: t('in.numbers.h') },
    ...(topics.length ? [{ id: 'topics', label: t('in.topics.h') }] : []),
    ...(partners.length ? [{ id: 'partners', label: t('in.partners.h') }] : []),
    ...(countries.length ? [{ id: 'abroad', label: t('in.countries.h') }] : []),
    ...(suggested.length ? [{ id: 'suggested', label: t('in.suggest.h') }] : []),
    ...(years.length ? [{ id: 'years', label: t('in.years.h') }] : []),
  ]
  const maxShare = Math.max(0.0001, ...topics.map((s) => s.share))
  const topicColumns: Column<TopicShare>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (s) => <TopicLink topic={topicOf(s.topic) as Topic} showStatus />, sortValue: (s) => s.topic, csv: (s) => s.topic },
    { key: 'count', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (s) => fmtInt(s.count), sortValue: (s) => s.count },
    { key: 'share', csvHeader: 'share', header: t('col.share'), numeric: true, cell: (s) => <ShareBar value={s.share} max={maxShare} />, sortValue: (s) => s.share },
  ]
  const partnerColumns: Column<Partner>[] = [
    { key: 'name', csvHeader: 'institution_id', header: t('col.institution'), rowHeader: true, cell: (p) => <InstitutionLink inst={byId.get(p.id) as InstitutionSummary} />, sortValue: (p) => instName(byId.get(p.id) as InstitutionSummary, lang).text, csv: (p) => p.id },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (p) => fmtInt(p.articles), sortValue: (p) => p.articles },
  ]
  const countryColumns: Column<CountryCount>[] = [
    { key: 'name', csvHeader: 'country', header: t('in.col.country'), rowHeader: true, cell: (c) => (lang === 'en' ? c.name_en : c.name_th), csv: (c) => c.code },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  const yearColumns: Column<{ year: number; articles: number }>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (y) => String(y.year), sortValue: (y) => y.year },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (y) => fmtInt(y.articles), sortValue: (y) => y.articles },
  ]
  return (
    <div className="container">
      <PageHeader title={shown.text} titleLang={shown.lang ?? undefined}>
        {other ? <p className="tp-alt" lang={lang === 'en' ? 'th' : 'en'}>{other}</p> : null}
        <div className="j-tags">
          <span className="tp-badge">{t(`in.type.${inst.type ?? 'other'}` as StrKey)}</span>
          <span>{place}</span>
          <span className="tp-sub">{t(`in.source.${inst.source}` as StrKey)}</span>
          {inst.ror ? (
            <a href={`https://ror.org/${inst.ror}`} target="_blank" rel="noopener noreferrer">ROR<span className="sr-only"> {t('newTab')}</span></a>
          ) : null}
        </div>
      </PageHeader>
      <div className="layout">
        <div className="main-col">
          <Section id="numbers" title={t('in.numbers.h')}>
            <dl className="summary">
              <div>
                <dt>{t('col.articles')}</dt>
                <dd>{fmtInt(inst.articles)}<small>{t('in.articlesSub', { a: w.start, b: w.end, all: fmtInt(inst.articles_total) })}</small></dd>
              </div>
              <div>
                <dt>{t('in.col.recent')}</dt>
                <dd>{fmtInt(inst.articles_recent ?? 0)}<small>{t('in.recentSub', { a: r.start, b: r.end })}</small></dd>
              </div>
              <div>
                <dt>{t('in.col.intl')}</dt>
                <dd>{fmtPct(inst.intl_share ?? null, 0)}<small>{t('in.intlSub')}</small></dd>
              </div>
              <div>
                <dt>{t('in.col.partners')}</dt>
                <dd>{fmtInt(inst.partners ?? 0)}<small>{t('in.partnersSub')}</small></dd>
              </div>
              <div>
                <dt>{t('col.topic')}</dt>
                <dd>{fmtInt(inst.topics ?? 0)}<small>{t('in.topicsSub')}</small></dd>
              </div>
            </dl>
          </Section>

          {topics.length ? (
            <Section id="topics" title={t('in.topics.h')}>
              <DataTable caption={t('table.n', { n: 1, title: t('in.topics.table') })} rows={topics} columns={topicColumns} rowKey={(s) => s.topic} defaultSort={{ key: 'count', dir: 'desc' }} csvFilename={`atlas-${rel}-${inst.id}-topics.csv`} />
              {signals.length ? (
                <>
                  <h3 className="mt-6">{t('in.emerging')}</h3>
                  <ul className="opp-list">
                    {signals.map((tp) => (
                      <li key={tp.id}><TopicLink topic={tp} showStatus /></li>
                    ))}
                  </ul>
                </>
              ) : null}
            </Section>
          ) : null}

          {partners.length ? (
            <Section id="partners" title={t('in.partners.h')}>
              <DataTable caption={t('table.n', { n: 2, title: t('in.partners.table') })} rows={partners} columns={partnerColumns} rowKey={(p) => p.id} defaultSort={{ key: 'articles', dir: 'desc' }} csvFilename={`atlas-${rel}-${inst.id}-partners.csv`} />
            </Section>
          ) : null}

          {countries.length ? (
            <Section id="abroad" title={t('in.countries.h')}>
              <DataTable caption={t('table.n', { n: 3, title: t('in.countries.table') })} rows={countries} columns={countryColumns} rowKey={(c) => c.code} stack={false} csvFilename={`atlas-${rel}-${inst.id}-countries.csv`} />
            </Section>
          ) : null}

          {suggested.length ? (
            <Section id="suggested" title={t('in.suggest.h')} intro={t('in.suggest.intro', { a: w.start, b: w.end })}>
              <ul className="sug-list">
                {suggested.map((s) => (
                  <li key={s.id}>
                    <InstitutionLink inst={byId.get(s.id) as InstitutionSummary} />
                    <span className="sug-topics">
                      <span className="topic-sub">{t('in.suggest.sub', { s: fmtNum(s.similarity, 2) })}</span>
                      {(s.topics ?? []).map((tid) => topicOf(tid)).filter((tp): tp is Topic => tp !== undefined).map((tp) => (
                        <TopicLink key={tp.id} topic={tp} />
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {years.length ? (
            <Section id="years" title={t('in.years.h')}>
              <DataTable caption={t('table.n', { n: 4, title: t('in.years.table') })} rows={years} columns={yearColumns} rowKey={(y) => String(y.year)} stack={false} defaultSort={{ key: 'year', dir: 'asc' }} csvFilename={`atlas-${rel}-${inst.id}-years.csv`} />
            </Section>
          ) : null}
          {detailFile.status === 'loading' ? <p className="loading" role="status">{t('loading')}</p> : null}
        </div>
        <aside className="rail" aria-label={t('onThisPage')}>
          <OnThisPage items={toc} />
          <p className="mt-6"><Link to="/institutions">{t('in.back')}</Link></p>
        </aside>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Topic pages link their institutions (D6).** In `web/src/pages/TopicPage.tsx` replace `  const countTable = (id: string, title: string, rows: readonly CountItem[], header: string) => (` with `  const countTable = (id: string, title: string, rows: readonly CountItem[], header: string, base: string) => (`, replace ``cell: (r) => (r.id ? <Link to={`/journals/${r.id}`}>{r.key}</Link> : r.key)`` with ``cell: (r) => (r.id ? <Link to={`${base}/${r.id}`}>{r.key}</Link> : r.key)``, replace `journals, t('col.journal'))}` with `journals, t('col.journal'), '/journals')}` and `institutions, t('col.institution'))}` with `institutions, t('col.institution'), '/institutions')}`.

- [ ] **Step 6: Routes.** In `web/src/App.tsx` below `const MatchPage = lazy(() => import('./pages/MatchPage'))` insert

```tsx
// The executives' pages (P3), also on demand.
const InstitutionsPage = lazy(() => import('./pages/InstitutionsPage'))
const InstitutionPage = lazy(() => import('./pages/InstitutionPage'))
```

and below `        <Route path="match" element={<Lazy><MatchPage /></Lazy>} />` insert

```tsx
        <Route path="institutions" element={<Lazy><InstitutionsPage /></Lazy>} />
        <Route path="institutions/:id" element={<Lazy><InstitutionPage /></Lazy>} />
```

- [ ] **Step 7: Run the gate**

Run: `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e`
Expected: PASS — both routes with the example and the empty release, axe clean in light and dark, no sideways scroll at 360 px; `check:bundle` lists `InstitutionsPage-*.js` and `InstitutionPage-*.js` as lazy chunks.

- [ ] **Step 8: Commit**

```bash
git add src/components/InstitutionLink.tsx src/pages/InstitutionsPage.tsx src/pages/InstitutionPage.tsx src/pages/TopicPage.tsx src/lib/urlState.ts src/App.tsx e2e/smoke.spec.ts
git commit -m "feat(web): /institutions and /institutions/:id — output, partnerships, partner countries, possible partners (R6); topic pages link institutions (D6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 9: `/regions` — province choropleth with a table view (E6)

Invoke `impeccable` (craft) and the `dataviz` skill for "a choropleth of Thailand's 77 provinces for executives: 5 quantile classes of one sequential hue, a 'no data' class apart, a legend with ranges, a measure switch (articles / per 100,000 people), chart ⇄ table tabs, a region summary table; DESIGN.md tokens; works at 360 px". Keep the map secondary to the numbers: the table view is complete, the map never carries a number alone.

**Files:**
- Create: `web/scripts/make-province-map.mjs`, `web/src/geo/thProvinces.ts` (generated by the script, committed), `web/src/components/ProvinceMap.tsx`, `web/src/pages/RegionsPage.tsx`
- Modify: `web/src/lib/urlState.ts`, `web/src/App.tsx`, `web/e2e/smoke.spec.ts`

**Interfaces:**
- Consumes: Task 7 (`RegionsFile`, `ProvinceStat`, `RegionStat`, `quantileBreaks`, `bucketOf`, strings `rg.*`, CSS `.pmap/.pv-*/.pkey/.sw-*/.metric-switch`), Task 8 (`InstitutionLink`), `Figure`, `DataTable`, `ShareBar`.
- Produces: `TH_VIEWBOX`, `TH_PROVINCE_PATHS: Record<code, path>`, `TH_PROVINCE_NAMES: Record<code, [th, en]>` (77 entries); `<ProvinceMap values format label noData range>`; `regionsCodec` (`m`: 'articles' | 'per100k', `view`: View); route `regions`; section ids `#map`, `#by-region`.

- [ ] **Step 1: Write the failing e2e check.** In `web/e2e/smoke.spec.ts` add `  { name: 'regions', path: '/regions' },` directly above the `] as const` that closes `ROUTES`, insert above `  // checks:end`:

```ts
  regions: async (page) => {
    await expect(page.locator('svg.pmap path')).toHaveCount(77)
    await expect(page.locator('svg.pmap path.pv-none')).toHaveCount(65)          // 12 provinces have data
    await expect(page.locator('.pkey li')).toHaveCount(6)                         // 5 classes + no data
    await page.getByLabel('บทความต่อประชากรแสนคน').check()
    await expect(page).toHaveURL(/m=per100k/)
    await expect(page.locator('svg.pmap path.pv-none')).toHaveCount(67)          // two have no population
    await page.locator('#map').getByRole('tab', { name: 'ตาราง' }).click()
    await expect(page.locator('#map tbody tr')).toHaveCount(12)
    await expect(page.locator('#by-region tbody tr')).toHaveCount(5)
  },
```

and append `'/regions'` to the `PHONE` array. Run: `npm run build && npx playwright test -g "regions"` — Expected: FAIL.

- [ ] **Step 2: The outlines (run once, commit the output).** Create `web/scripts/make-province-map.mjs`:

```js
#!/usr/bin/env node
// Thai province outlines for /regions — run once; the output src/geo/thProvinces.ts is committed (no runtime geo library).
//   curl -L -o ne_admin1.geojson https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_10m_admin_1_states_provinces.geojson
//   node scripts/make-province-map.mjs ne_admin1.geojson          (the download is ~40 MB: keep it outside the repo)
// Source: Natural Earth 1:10m Cultural Vectors, Admin 1 – States, Provinces, v5.1.2 — public domain
// (https://www.naturalearthdata.com/about/terms-of-use/). Names: pipeline/atlas/data/th_provinces.csv.
// The 77 provinces (iso_3166_2 TH-10 … TH-96; Pattaya TH-S is not a province) are projected equirectangularly around
// 13°N, simplified (Douglas–Peucker; the tolerance grows until the file is under 300 KB), islands smaller than MIN_AREA px²
// dropped (every province keeps its largest ring), rounded to 0.1 px and written as relative SVG paths.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'

const OUT = 'src/geo/thProvinces.ts'
const BUDGET = 300_000
const MIN_AREA = 6
const SCALE = 60
const PAD = 4
const COS = Math.cos((13 * Math.PI) / 180)

const csv = readFileSync('../pipeline/atlas/data/th_provinces.csv', 'utf8').trim().split(/\r?\n/).slice(1).map((l) => l.split(','))
const NAMES = Object.fromEntries(csv.map(([code, th, en]) => [code, [th, en]]))
const CODES = Object.keys(NAMES)
if (CODES.length !== 77) throw new Error(`th_provinces.csv lists ${CODES.length} provinces, expected 77`)

const src = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const feats = src.features.filter((f) => CODES.includes(f.properties.iso_3166_2))
const missing = CODES.filter((c) => !feats.some((f) => f.properties.iso_3166_2 === c))
if (missing.length) {
  console.error(`[map] Natural Earth has no outline for: ${missing.join(', ')}`)
  process.exit(1)
}

const project = ([lon, lat]) => [lon * COS * SCALE, -lat * SCALE]
const rings = new Map(feats.map((f) => {
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates
  return [f.properties.iso_3166_2, polys.map((p) => p[0].map(project))] // outer rings only
}))
let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
for (const rs of rings.values()) for (const r of rs) for (const [x, y] of r) {
  minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y)
}
const W = Math.ceil(maxX - minX + 2 * PAD)
const H = Math.ceil(maxY - minY + 2 * PAD)

function simplify(pts, tol) {
  if (pts.length < 3) return pts
  const keep = new Uint8Array(pts.length)
  keep[0] = keep[pts.length - 1] = 1
  const stack = [[0, pts.length - 1]]
  while (stack.length) {
    const [a, b] = stack.pop()
    const [ax, ay] = pts[a]
    const [bx, by] = pts[b]
    const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1
    let best = -1, dmax = 0
    for (let i = a + 1; i < b; i++) {
      const d = Math.abs(dy * (pts[i][0] - ax) - dx * (pts[i][1] - ay)) / len
      if (d > dmax) { dmax = d; best = i }
    }
    if (best > 0 && dmax > tol) { keep[best] = 1; stack.push([a, best], [best, b]) }
  }
  return pts.filter((_, i) => keep[i])
}

/** A closed ring is split at the point farthest from its start (a zero-length chord cannot be simplified). */
function simplifyRing(ring, tol) {
  let far = 1, dmax = -1
  for (let i = 1; i < ring.length - 1; i++) {
    const d = Math.hypot(ring[i][0] - ring[0][0], ring[i][1] - ring[0][1])
    if (d > dmax) { dmax = d; far = i }
  }
  return simplify(ring.slice(0, far + 1), tol).concat(simplify(ring.slice(far), tol).slice(1))
}

const area = (r) => Math.abs(r.reduce((s, [x, y], i) => { const [x2, y2] = r[(i + 1) % r.length]; return s + x * y2 - x2 * y }, 0)) / 2
const largest = (rs) => rs.reduce((m, r) => (area(r) > area(m) ? r : m), rs[0])

function pathOf(rs, tol) {
  const simplified = rs.map((r) => simplifyRing(r, tol)).filter((r) => r.length >= 4)
  const kept = simplified.length ? simplified : [largest(rs)]
  const big = largest(kept)
  const parts = []
  for (const r of kept) {
    if (r !== big && area(r) < MIN_AREA) continue
    const q = r.map(([x, y]) => [Math.round((x - minX + PAD) * 10), Math.round((y - minY + PAD) * 10)])
    const steps = []
    let prev = q[0]
    for (const p of q.slice(1, -1)) {
      const dx = p[0] - prev[0], dy = p[1] - prev[1]
      if (dx || dy) steps.push(`${dx / 10} ${dy / 10}`)
      prev = p
    }
    parts.push(`M${q[0][0] / 10} ${q[0][1] / 10}l${steps.join(' ')}z`.replace(/ -/g, '-'))
  }
  return parts.join('')
}

let tol = 0.5
let out = ''
for (;;) {
  const paths = CODES.map((c) => `  '${c}': '${pathOf(rings.get(c), tol)}',`)
  const names = CODES.map((c) => `  '${c}': ['${NAMES[c][0]}', '${NAMES[c][1]}'],`)
  out = '// Generated by scripts/make-province-map.mjs from Natural Earth 1:10m admin-1 v5.1.2 (public domain) — do not edit.\n'
    + `export const TH_VIEWBOX = '0 0 ${W} ${H}'\n\n`
    + '/** SVG path (in TH_VIEWBOX) of each province, keyed by its ISO 3166-2:TH code. */\n'
    + `export const TH_PROVINCE_PATHS: Readonly<Record<string, string>> = {\n${paths.join('\n')}\n}\n\n`
    + '/** [Thai, English] name of each province (pipeline/atlas/data/th_provinces.csv). */\n'
    + `export const TH_PROVINCE_NAMES: Readonly<Record<string, readonly [string, string]>> = {\n${names.join('\n')}\n}\n`
  if (Buffer.byteLength(out) <= BUDGET) break
  tol *= 1.5
}
mkdirSync('src/geo', { recursive: true })
writeFileSync(OUT, out)
console.log(`[map] ${CODES.length} provinces, view box ${W}×${H}, tolerance ${tol.toFixed(2)} px, ${(Buffer.byteLength(out) / 1024).toFixed(0)} KB → ${OUT}`)
```

Run (from `web/`, the download kept outside the repo):

```bash
curl -L -o ../../ne_admin1.geojson https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_10m_admin_1_states_provinces.geojson
node scripts/make-province-map.mjs ../../ne_admin1.geojson
```

Expected (checked 2026-10-19 on v5.1.2): `[map] 77 provinces, view box 494×897, tolerance 0.50 px, 42 KB → src/geo/thProvinces.ts` (the `/regions` chunk is then ≈ 17 KB gzip). Commit the generated file; delete the download. (The script needs no network itself; only this one-time download does.) If the script reports a province without an outline, stop and report it — never draw or invent an outline.

- [ ] **Step 3: The map component.** Create `web/src/components/ProvinceMap.tsx`:

```tsx
import { TH_PROVINCE_NAMES, TH_PROVINCE_PATHS, TH_VIEWBOX } from '../geo/thProvinces'
import { bucketOf, quantileBreaks } from '../lib/executive'
import { useI18n } from '../lib/i18n'

/**
 * Choropleth of Thailand's 77 provinces: 5 quantile classes of the sequential ramp (--seq-1…5), "no data" apart.
 * The figure's table view is the complete, accessible equivalent; each outline names its province and value on hover.
 */
export function ProvinceMap({ values, format, label, noData, range }: {
  values: ReadonlyMap<string, number | null>
  format: (v: number) => string
  label: string
  noData: string
  range: (from: string, to: string) => string
}) {
  const { lang } = useI18n()
  const known = [...values.values()].filter((v): v is number => v !== null && Number.isFinite(v))
  const breaks = quantileBreaks(known)
  const low = known.length ? Math.min(...known) : 0
  const name = (code: string) => {
    const n = TH_PROVINCE_NAMES[code]
    return n ? (lang === 'en' ? n[1] : n[0]) : code
  }
  return (
    <>
      <ul className="pkey">
        {breaks.map((b, i) => (
          <li key={b}>
            <span className={`sw sw-${i}`} aria-hidden="true" />
            {range(format(i === 0 ? low : breaks[i - 1]), format(b))}
          </li>
        ))}
        <li>
          <span className="sw sw-none" aria-hidden="true" />
          {noData}
        </li>
      </ul>
      <svg className="pmap" viewBox={TH_VIEWBOX} role="img" aria-label={label}>
        {Object.entries(TH_PROVINCE_PATHS).map(([code, d]) => {
          const v = values.get(code) ?? null
          const b = bucketOf(v, breaks)
          return (
            <path key={code} d={d} className={b < 0 ? 'pv-none' : `pv-${b}`}>
              <title>{`${name(code)}: ${v === null ? noData : format(v)}`}</title>
            </path>
          )
        })}
      </svg>
    </>
  )
}
```

- [ ] **Step 4: The page.** Append to `web/src/lib/urlState.ts`:

```ts
export const REGION_METRICS = ['articles', 'per100k'] as const
export const regionsCodec = makeCodec<{ m: (typeof REGION_METRICS)[number]; view: View }>({
  m: oneOf('m', REGION_METRICS, 'articles'),
  view: oneOf('view', VIEWS, 'chart'),
})
```

Create `web/src/pages/RegionsPage.tsx`:

```tsx
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { ProvinceMap } from '../components/ProvinceMap'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { InstitutionsFile, ProvinceStat, RegionStat, RegionsFile } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { REGION_METRICS, regionsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'

export default function RegionsPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('rg.title')}>
      {(release) => (
        <ModuleFile<RegionsFile> release={release} module="regions" path={MODULE_FILES.regions} title={t('rg.title')}>
          {(file) => <Regions release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Regions({ release, file }: { release: AtlasRelease; file: RegionsFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(regionsCodec)
  const instFile = useReleaseFile<InstitutionsFile>(hasModule(release, 'institutions') ? MODULE_FILES.institutions : null)
  const insts = new Map(instFile.status === 'ready' ? instFile.data.institutions.map((i) => [i.id, i]) : [])
  const hasPop = file.provinces.some((p) => p.per_100k != null)
  const metric = hasPop ? state.m : 'articles'
  const valueOf = (p: ProvinceStat): number | null => (metric === 'per100k' ? (p.per_100k ?? null) : p.articles)
  const format = (v: number) => (metric === 'per100k' ? fmtNum(v, 1) : fmtInt(v))
  const measure = t(metric === 'per100k' ? 'rg.metric.per100k' : 'rg.metric.articles')
  const pname = (p: ProvinceStat) => (lang === 'en' ? p.name_en : p.name_th)
  const maxShare = Math.max(0.0001, ...file.provinces.map((p) => p.share ?? 0))
  const w = file.window
  const rel = release.overview.release
  const columns: Column<ProvinceStat>[] = [
    { key: 'name', csvHeader: 'province', header: t('in.col.province'), rowHeader: true, cell: pname, sortValue: pname, csv: (p) => p.code },
    { key: 'region', csvHeader: 'region', header: t('rg.col.region'), cell: (p) => t(`rg.region.${p.region}` as StrKey), sortValue: (p) => p.region, csv: (p) => p.region },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (p) => fmtInt(p.articles), sortValue: (p) => p.articles },
    { key: 'share', csvHeader: 'share', header: t('rg.col.share'), numeric: true, cell: (p) => <ShareBar value={p.share} digits={1} max={maxShare} />, sortValue: (p) => p.share ?? null },
    { key: 'recent', csvHeader: 'articles_recent', header: t('in.col.recent'), numeric: true, cell: (p) => fmtInt(p.articles_recent ?? 0), sortValue: (p) => p.articles_recent ?? 0 },
    { key: 'institutions', csvHeader: 'institutions', header: t('rg.col.institutions'), numeric: true, cell: (p) => fmtInt(p.institutions ?? 0), sortValue: (p) => p.institutions ?? 0 },
    ...(hasPop ? [{ key: 'per100k', csvHeader: 'per_100k', header: t('rg.col.per100k'), numeric: true, cell: (p: ProvinceStat) => fmtNum(p.per_100k ?? null, 1), sortValue: (p: ProvinceStat) => p.per_100k ?? null }] : []),
    {
      key: 'top', csvHeader: 'top_institutions', header: t('rg.col.top'),
      cell: (p) => {
        const top = (p.top ?? []).map((id) => insts.get(id)).filter((i) => i !== undefined)
        return top.length ? <span className="pair">{top.map((i) => <InstitutionLink key={i.id} inst={i} />)}</span> : DASH
      },
      csv: (p) => (p.top ?? []).join(';'),
    },
  ]
  const regionColumns: Column<RegionStat>[] = [
    { key: 'name', csvHeader: 'region', header: t('rg.col.region'), rowHeader: true, cell: (r) => t(`rg.region.${r.key}` as StrKey), csv: (r) => r.key },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => fmtInt(r.articles), sortValue: (r) => r.articles },
    { key: 'share', csvHeader: 'share', header: t('rg.col.share'), numeric: true, cell: (r) => fmtPct(r.share ?? null, 1), sortValue: (r) => r.share ?? null },
  ]
  return (
    <div className="container">
      <PageHeader title={t('rg.title')} lede={t('rg.lede', { a: w.start, b: w.end, p: fmtPct(file.coverage ?? null, 0) })} />
      <Section id="map" title={t('rg.provinces.h')}>
        {hasPop ? (
          <fieldset className="metric-switch">
            <legend>{t('rg.metric')}</legend>
            {REGION_METRICS.map((m) => (
              <label key={m}>
                <input type="radio" name="rg-metric" value={m} checked={metric === m} onChange={() => update({ m })} />
                {t(m === 'per100k' ? 'rg.metric.per100k' : 'rg.metric.articles')}
              </label>
            ))}
          </fieldset>
        ) : null}
        <Figure
          id="fig-regions"
          number={1}
          title={t('rg.fig', { m: measure })}
          source={t('rg.source', { release: rel })}
          view={state.view}
          onView={(v) => update({ view: v })}
          chart={
            <ProvinceMap
              values={new Map(file.provinces.map((p) => [p.code, valueOf(p)]))}
              format={format}
              label={t('rg.map', { m: measure, n: fmtInt(file.provinces.filter((p) => valueOf(p) !== null).length) })}
              noData={t('rg.noData')}
              range={(a, b) => t('rg.range', { a, b })}
            />
          }
          table={
            <DataTable
              caption={t('table.n', { n: 1, title: t('rg.table') })}
              rows={file.provinces}
              columns={columns}
              rowKey={(p) => p.code}
              defaultSort={{ key: metric === 'per100k' ? 'per100k' : 'articles', dir: 'desc' }}
              csvFilename={`atlas-${rel}-provinces.csv`}
            />
          }
          note={hasPop ? <p className="note">{t('rg.popNote', { y: file.population_year ?? DASH })}</p> : undefined}
        />
      </Section>
      {file.regions.length ? (
        <Section id="by-region" title={t('rg.regions.h')}>
          <DataTable caption={t('table.n', { n: 2, title: t('rg.regions.table') })} rows={file.regions} columns={regionColumns} rowKey={(r) => r.key} stack={false} defaultSort={{ key: 'articles', dir: 'desc' }} csvFilename={`atlas-${rel}-regions.csv`} />
        </Section>
      ) : null}
    </div>
  )
}
```

In `web/src/App.tsx` below `const InstitutionPage = lazy(() => import('./pages/InstitutionPage'))` insert `const RegionsPage = lazy(() => import('./pages/RegionsPage'))` and below `        <Route path="institutions/:id" element={<Lazy><InstitutionPage /></Lazy>} />` insert `        <Route path="regions" element={<Lazy><RegionsPage /></Lazy>} />`.

- [ ] **Step 5: Run the gate**

Run: `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e`
Expected: PASS — `check:bundle` shows `RegionsPage-*.js` as a lazy chunk (it carries the outlines; the entry chunk stays ≤ 180 KB gzip); `/regions` with the example and the empty release; axe clean in light and dark; no sideways scroll at 360 px.

- [ ] **Step 6: Commit**

```bash
git add scripts/make-province-map.mjs src/geo/thProvinces.ts src/components/ProvinceMap.tsx src/pages/RegionsPage.tsx src/lib/urlState.ts src/App.tsx e2e/smoke.spec.ts
git commit -m "feat(web): /regions — province choropleth (Natural Earth, public domain) with a table view, per-capita switch, regions table (E6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 10: `/sdg` and `/global` (E8, E9)

Invoke `impeccable` (craft) for "an SDG and Thai-plan coverage page (framework tabs, a goal table where goals without research are marked, example topics) and a Thailand-vs-the-world page (opportunity table first, then every subfield; ratios and an activity index explained in one plain line); DESIGN.md tokens; Thai typography". Marks are text (`.flag`), never colour alone.

**Files:**
- Create: `web/src/pages/SdgPage.tsx`, `web/src/pages/GlobalPage.tsx`
- Modify: `web/src/lib/urlState.ts`, `web/src/App.tsx`, `web/e2e/smoke.spec.ts`

**Interfaces:**
- Consumes: Task 7 (`SdgFile`, `GoalStat`, `GlobalFile`, `SubfieldBench`, strings `sdg.*`, `gl.*`, CSS `.sdg-ex`, `.goal-name`), P1/P2 `Tabs`, `DataTable`, `ShareBar`, `TopicLink`, `groupName`, `fmtRatio`.
- Produces: `sdgCodec` (`fw`: framework key, '' = the first); routes `sdg`, `global`; section ids `#goals`, `#opportunities`, `#all`.

- [ ] **Step 1: Write the failing e2e checks.** In `web/e2e/smoke.spec.ts` add `  { name: 'sdg', path: '/sdg' },` and `  { name: 'global', path: '/global' },` directly above the `] as const` that closes `ROUTES`; insert above `  // checks:end`:

```ts
  sdg: async (page) => {
    await expect(page.getByRole('tab', { name: /SDGs/ })).toHaveAttribute('aria-selected', 'true')
    await expect(page.locator('#goals tbody tr')).toHaveCount(17)
    await expect(page.locator('#goals')).toContainText('ยังไม่พบหัวข้อ')
    await page.getByRole('tab', { name: 'โมเดลเศรษฐกิจ BCG' }).click()
    await expect(page).toHaveURL(/fw=bcg/)
    await expect(page.locator('#goals tbody tr')).toHaveCount(3)
  },
  global: async (page) => {
    await expect(page.locator('#opportunities tbody tr')).toHaveCount(3)
    await expect(page.locator('#opportunities')).toContainText('Artificial Intelligence')
    await expect(page.locator('#all tbody tr')).toHaveCount(11)
  },
```

append `'/sdg', '/global'` to `PHONE`, and append at the end of the file:

```ts
test('a module the pipeline skipped says why', async ({ page }) => {
  await page.goto(`${EMPTY}#/global`)
  await expect(page.locator('h1')).toHaveText('ไทยเทียบโลก')
  await expect(page.locator('.empty-state')).toContainText('ATLAS_OFFLINE')
})
```

Run: `npm run build && npx playwright test -g "sdg|global|skipped"` — Expected: FAIL.

- [ ] **Step 2: URL state.** Append to `web/src/lib/urlState.ts`:

```ts
export const sdgCodec = makeCodec<{ fw: string }>({ fw: text('fw', 24) })
```

- [ ] **Step 3: /sdg.** Create `web/src/pages/SdgPage.tsx`:

```tsx
import { DataTable, type Column } from '../components/DataTable'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { Tabs } from '../components/Tabs'
import { TopicLink } from '../components/TopicLink'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GoalStat, SdgFile, Topic } from '../data/types'
import { fmtInt, fmtRatio } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { sdgCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'

export default function SdgPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('sdg.title')}>
      {(release) => (
        <ModuleFile<SdgFile> release={release} module="sdg" path={MODULE_FILES.sdg} title={t('sdg.title')}>
          {(file) => <Sdg release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Sdg({ release, file }: { release: AtlasRelease; file: SdgFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(sdgCodec)
  const name = (o: { th: string; en: string }) => (lang === 'en' ? o.en : o.th)
  const fw = file.frameworks.find((f) => f.key === state.fw) ?? file.frameworks[0]
  const goals = fw ? file.goals.filter((g) => g.framework === fw.key) : []
  const count = (g: GoalStat) => (g.topics ?? []).length
  const covered = goals.filter((g) => count(g) > 0).length
  const maxShare = Math.max(0.0001, ...goals.map((g) => g.share_recent ?? 0))
  const label = (g: GoalStat) => (fw?.key === 'sdg' ? `SDG ${g.number}` : String(g.number))
  const columns: Column<GoalStat>[] = [
    {
      key: 'goal', csvHeader: 'goal_id', header: t('sdg.col.goal'), rowHeader: true, firstDir: 'asc',
      cell: (g) => <span className="goal-name"><strong>{label(g)}</strong> {name(g)}</span>, sortValue: (g) => g.number, csv: (g) => g.id,
    },
    { key: 'topics', csvHeader: 'topics', header: t('sdg.col.topics'), numeric: true, cell: (g) => (count(g) ? fmtInt(count(g)) : <span className="flag">{t('sdg.gap')}</span>), sortValue: count },
    { key: 'articles', csvHeader: 'articles_recent', header: t('col.articlesR'), numeric: true, cell: (g) => fmtInt(g.articles_recent ?? 0), sortValue: (g) => g.articles_recent ?? 0 },
    { key: 'share', csvHeader: 'share_recent', header: t('col.share'), numeric: true, cell: (g) => <ShareBar value={g.share_recent ?? 0} digits={1} max={maxShare} />, sortValue: (g) => g.share_recent ?? 0 },
    { key: 'ratio', csvHeader: 'share_ratio', header: t('sdg.col.ratio'), numeric: true, cell: (g) => fmtRatio(g.share_ratio ?? null), sortValue: (g) => g.share_ratio ?? null },
    {
      key: 'examples', csvHeader: 'topic_ids', header: t('sdg.col.examples'),
      cell: (g) => (
        <span className="sdg-ex">
          {(g.topics ?? []).slice(0, 3).map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined).map((tp) => (
            <TopicLink key={tp.id} topic={tp} showStatus />
          ))}
        </span>
      ),
      csv: (g) => (g.topics ?? []).join(';'),
    },
  ]
  const rel = release.overview.release
  return (
    <div className="container">
      <PageHeader title={t('sdg.title')} lede={t('sdg.lede', { method: t(file.method === 'embedding' ? 'sdg.method.embedding' : 'sdg.method.lexical') })} />
      {fw ? (
        <Section id="goals" title={t('sdg.frameworks')}>
          <Tabs id="sdg-fw" label={t('sdg.frameworks')} items={file.frameworks.map((f) => ({ id: f.key, label: name(f) }))} value={fw.key} onChange={(id) => update({ fw: id })}>
            <p className="note">{t('sdg.coverage', { n: fmtInt(covered), total: fmtInt(goals.length) })}</p>
            <DataTable
              caption={t('table.n', { n: 1, title: t('sdg.table', { f: name(fw) }) })}
              rows={goals}
              columns={columns}
              rowKey={(g) => g.id}
              defaultSort={{ key: 'goal', dir: 'asc' }}
              csvFilename={`atlas-${rel}-${fw.key}.csv`}
              footnote={t('sdg.foot')}
            />
          </Tabs>
        </Section>
      ) : null}
    </div>
  )
}
```

- [ ] **Step 4: /global.** Create `web/src/pages/GlobalPage.tsx`:

```tsx
import { DataTable, type Column } from '../components/DataTable'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { TopicLink } from '../components/TopicLink'
import { groupName, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GlobalFile, SubfieldBench, Topic } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct, fmtRatio } from '../lib/format'
import { useI18n } from '../lib/i18n'

export default function GlobalPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('gl.title')}>
      {(release) => (
        <ModuleFile<GlobalFile> release={release} module="global" path={MODULE_FILES.global} title={t('gl.title')}>
          {(file) => <Global release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Global({ release, file }: { release: AtlasRelease; file: GlobalFile }) {
  const { t, lang } = useI18n()
  const opp = file.subfields.filter((s) => s.opportunity)
  const topicsOf = (s: SubfieldBench): Topic[] => (s.topics ?? []).map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined)
  const columns = (mark: boolean): Column<SubfieldBench>[] => [
    {
      key: 'subfield', header: t('gl.col.subfield'), rowHeader: true, sortValue: (s) => s.en,
      cell: (s) => (
        <>
          <span lang="en">{s.en}</span>
          {mark && s.opportunity ? <span className="flag">{t('gl.opp')}</span> : null}
        </>
      ),
      csvCols: [{ header: 'subfield_id', value: (s) => s.id }, { header: 'subfield_en', value: (s) => s.en }],
    },
    { key: 'field', csvHeader: 'group', header: t('col.field'), cell: (s) => (release.groupById.has(s.group) ? groupName(release, s.group, lang) : DASH), csv: (s) => s.group },
    { key: 'ratio', csvHeader: 'world_ratio', header: t('gl.col.ratio'), numeric: true, cell: (s) => fmtRatio(s.world_ratio ?? null), sortValue: (s) => s.world_ratio ?? null },
    { key: 'ai', csvHeader: 'activity_index', header: t('gl.col.ai'), numeric: true, cell: (s) => fmtNum(s.activity_index ?? null, 2), sortValue: (s) => s.activity_index ?? null },
    { key: 'share', csvHeader: 'country_share', header: t('gl.col.share'), numeric: true, cell: (s) => fmtPct(s.country_share ?? null, 2), sortValue: (s) => s.country_share ?? null },
    { key: 'country', csvHeader: 'country_recent', header: t('gl.col.country'), numeric: true, cell: (s) => fmtInt(s.country_recent), sortValue: (s) => s.country_recent },
    { key: 'world', csvHeader: 'world_recent', header: t('gl.col.world'), numeric: true, cell: (s) => fmtInt(s.world_recent), sortValue: (s) => s.world_recent },
    { key: 'tci', csvHeader: 'tci_recent', header: t('gl.col.tci'), numeric: true, cell: (s) => fmtInt(s.tci_recent ?? 0), sortValue: (s) => s.tci_recent ?? 0 },
    {
      key: 'topics', csvHeader: 'topic_ids', header: t('gl.col.topics'),
      cell: (s) => {
        const tl = topicsOf(s).slice(0, 3)
        return tl.length ? <span className="sdg-ex">{tl.map((tp) => <TopicLink key={tp.id} topic={tp} showStatus />)}</span> : DASH
      },
      csv: (s) => (s.topics ?? []).join(';'),
    },
  ]
  const country = file.country === 'TH' ? t('gl.thailand') : file.country
  const rel = release.overview.release
  return (
    <div className="container">
      <PageHeader
        title={t('gl.title')}
        lede={t('gl.lede', { c: country, r: `${file.recent.start}–${file.recent.end}`, b: `${file.baseline.start}–${file.baseline.end}` })}
      >
        <p className="note">{t('gl.def')}</p>
      </PageHeader>
      {opp.length ? (
        <Section id="opportunities" title={t('gl.opp.h')} intro={t('gl.opp.intro', { r: fmtNum(file.min_world_ratio, 1), n: fmtInt(file.min_world_works), ai: fmtNum(file.max_activity_index, 1) })}>
          <DataTable caption={t('table.n', { n: 1, title: t('gl.opp.table') })} rows={opp} columns={columns(false)} rowKey={(s) => s.id} defaultSort={{ key: 'ratio', dir: 'desc' }} csvFilename={`atlas-${rel}-opportunities.csv`} />
        </Section>
      ) : null}
      <Section id="all" title={t('gl.all.h')}>
        <DataTable caption={t('table.n', { n: 2, title: t('gl.all.table') })} rows={file.subfields} columns={columns(true)} rowKey={(s) => s.id} defaultSort={{ key: 'world', dir: 'desc' }} csvFilename={`atlas-${rel}-global.csv`} />
      </Section>
      <p className="source">{t('gl.source', { v: file.source })}</p>
    </div>
  )
}
```

In `web/src/App.tsx` below `const RegionsPage = lazy(() => import('./pages/RegionsPage'))` insert

```tsx
const SdgPage = lazy(() => import('./pages/SdgPage'))
const GlobalPage = lazy(() => import('./pages/GlobalPage'))
```

and below `        <Route path="regions" element={<Lazy><RegionsPage /></Lazy>} />` insert

```tsx
        <Route path="sdg" element={<Lazy><SdgPage /></Lazy>} />
        <Route path="global" element={<Lazy><GlobalPage /></Lazy>} />
```

- [ ] **Step 5: Run the gate**

Run: `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e`
Expected: PASS — both routes with the example and the empty release (the empty `/global` shows the pipeline's reason), axe clean, 360 px without sideways scroll, two new lazy chunks.

- [ ] **Step 6: Commit**

```bash
git add src/pages/SdgPage.tsx src/pages/GlobalPage.tsx src/lib/urlState.ts src/App.tsx e2e/smoke.spec.ts
git commit -m "feat(web): /sdg (SDGs, BCG, แผน ววน., แผนฯ 13 — coverage and gaps) and /global (Thailand vs the world, opportunities)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 11: `/gaps` — gap finder and concentration risk (R5, E10, pointer to R6)

Invoke `impeccable` (craft) for "a research-gaps page for researchers and executives: four short sections (world opportunities with Atlas topics, emerging topics few institutions work on, neighbouring topics nobody bridges, concentration risk with a 'show all' switch), each a small table with a one-line rule; a note that points to possible partners on institution pages; DESIGN.md tokens". Signals are worded as questions to explore, never as verdicts.

**Files:**
- Create: `web/src/pages/GapsPage.tsx`
- Modify: `web/src/lib/urlState.ts`, `web/src/App.tsx`, `web/e2e/smoke.spec.ts`

**Interfaces:**
- Consumes: Task 7 (`GapsFile`, `FewInstitutions`, `Bridge`, `WorldGap`, `Concentration`, strings `gp.*`, CSS `.flag-on`, `.pair`, `.sdg-ex`), `statusName`, `TopicLink`, `groupName`, `hasModule`.
- Produces: `gapsCodec` (`all`: 'no' | 'yes'); route `gaps`; section ids `#world`, `#few`, `#bridges`, `#risk`.

- [ ] **Step 1: Write the failing e2e check.** In `web/e2e/smoke.spec.ts` add `  { name: 'gaps', path: '/gaps' },` directly above the `] as const` that closes `ROUTES`; insert above `  // checks:end`:

```ts
  gaps: async (page) => {
    await expect(page.locator('#world tbody tr')).toHaveCount(3)
    await expect(page.locator('#few tbody tr')).toHaveCount(2)
    await expect(page.locator('#bridges tbody tr')).toHaveCount(2)
    const risk = page.locator('#risk tbody tr')
    await expect(risk).toHaveCount(2)
    await page.getByLabel('แสดงหน่วยที่ไม่กระจุกตัวด้วย').check()
    await expect(risk).toHaveCount(4)
    await expect(page).toHaveURL(/all=yes/)
    await expect(page.locator('#risk')).toContainText('มหาวิทยาลัยราชภัฏตัวอย่าง')
  },
```

and append `'/gaps'` to `PHONE`. Run: `npm run build && npx playwright test -g "gaps"` — Expected: FAIL.

- [ ] **Step 2: The page.** Append to `web/src/lib/urlState.ts`:

```ts
export const gapsCodec = makeCodec<{ all: 'no' | 'yes' }>({ all: oneOf('all', ['no', 'yes'] as const, 'no') })
```

Create `web/src/pages/GapsPage.tsx`:

```tsx
import { Link } from 'react-router'
import { DataTable, type Column } from '../components/DataTable'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { groupName, hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { Bridge, Concentration, FewInstitutions, GapsFile, Topic, WorldGap } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct, fmtRatio } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { statusName } from '../lib/topicText'
import { gapsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'

export default function GapsPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('gp.title')}>
      {(release) => (
        <ModuleFile<GapsFile> release={release} module="gaps" path={MODULE_FILES.gaps} title={t('gp.title')}>
          {(file) => <Gaps release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Gaps({ release, file }: { release: AtlasRelease; file: GapsFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(gapsCodec)
  const topic = (id: string): Topic | undefined => release.topicById.get(id)
  const few = file.few_institutions.filter((f) => topic(f.topic))
  const bridges = file.bridges.filter((b) => topic(b.a) && topic(b.b))
  const risk = file.concentration.filter((c) => (c.scope === 'topic' ? topic(c.id) : true) && (state.all === 'yes' || c.concentrated))
  const r = file.recent
  const rel = release.overview.release
  const topicList = (ids: readonly string[]) => {
    const tl = ids.map(topic).filter((tp): tp is Topic => tp !== undefined).slice(0, 3)
    return tl.length ? <span className="sdg-ex">{tl.map((tp) => <TopicLink key={tp.id} topic={tp} showStatus />)}</span> : DASH
  }
  const worldColumns: Column<WorldGap>[] = [
    { key: 'subfield', header: t('gl.col.subfield'), rowHeader: true, cell: (w) => <span lang="en">{w.en}</span>, sortValue: (w) => w.en, csvCols: [{ header: 'subfield_id', value: (w) => w.subfield }, { header: 'subfield_en', value: (w) => w.en }] },
    { key: 'ratio', csvHeader: 'world_ratio', header: t('gl.col.ratio'), numeric: true, cell: (w) => fmtRatio(w.world_ratio ?? null), sortValue: (w) => w.world_ratio ?? null },
    { key: 'ai', csvHeader: 'activity_index', header: t('gl.col.ai'), numeric: true, cell: (w) => fmtNum(w.activity_index ?? null, 2), sortValue: (w) => w.activity_index ?? null },
    { key: 'topics', csvHeader: 'topic_ids', header: t('gl.col.topics'), cell: (w) => topicList(w.topics ?? []), csv: (w) => (w.topics ?? []).join(';') },
  ]
  const fewColumns: Column<FewInstitutions>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (f) => <TopicLink topic={topic(f.topic) as Topic} showStatus />, sortValue: (f) => f.topic, csv: (f) => f.topic },
    { key: 'institutions', csvHeader: 'institutions', header: t('gp.col.institutions'), numeric: true, firstDir: 'asc', cell: (f) => fmtInt(f.institutions), sortValue: (f) => f.institutions },
  ]
  const bridgeColumns: Column<Bridge>[] = [
    {
      key: 'pair', header: t('gp.col.pair'), rowHeader: true,
      cell: (b) => (
        <span className="pair">
          <TopicLink topic={topic(b.a) as Topic} showStatus />
          <TopicLink topic={topic(b.b) as Topic} showStatus />
        </span>
      ),
      csvCols: [{ header: 'topic_a', value: (b) => b.a }, { header: 'topic_b', value: (b) => b.b }],
    },
    { key: 'similarity', csvHeader: 'similarity', header: t('in.col.similarity'), numeric: true, cell: (b) => fmtNum(b.similarity, 2), sortValue: (b) => b.similarity },
    { key: 'shared', csvHeader: 'shared', header: t('gp.col.shared'), numeric: true, firstDir: 'asc', cell: (b) => fmtInt(b.shared), sortValue: (b) => b.shared },
    { key: 'jaccard', csvHeader: 'jaccard', header: 'Jaccard', numeric: true, firstDir: 'asc', cell: (b) => fmtNum(b.jaccard, 2), sortValue: (b) => b.jaccard },
  ]
  const topName = (c: Concentration) => {
    if (!c.top && !c.top_name) return <span className="topic-sub">{t('gp.withheld')}</span>
    const module = c.kind === 'institution' ? 'institutions' : 'journals'
    return c.top && hasModule(release, module) ? <Link to={`/${module}/${c.top}`}>{c.top_name || c.top}</Link> : c.top_name || c.top
  }
  const riskColumns: Column<Concentration>[] = [
    {
      key: 'unit', csvHeader: 'unit', header: t('gp.col.unit'), rowHeader: true,
      cell: (c) => (c.scope === 'topic' ? <TopicLink topic={topic(c.id) as Topic} showStatus /> : groupName(release, c.id, lang)),
      sortValue: (c) => c.id, csv: (c) => c.id,
    },
    { key: 'kind', csvHeader: 'kind', header: t('gp.col.kind'), cell: (c) => t(c.kind === 'institution' ? 'gp.kind.institution' : 'gp.kind.journal'), csv: (c) => c.kind },
    { key: 'top', csvHeader: 'top', header: t('gp.col.top'), cell: topName, csv: (c) => c.top ?? '' },
    {
      key: 'share', csvHeader: 'top_share', header: t('gp.col.topShare'), numeric: true, sortValue: (c) => c.top_share,
      cell: (c) => (
        <>
          <ShareBar value={c.top_share} />
          {c.concentrated ? <span className="flag-on">{t('gp.flag')}</span> : null}
        </>
      ),
    },
    { key: 'hhi', csvHeader: 'hhi', header: t('gp.col.hhi'), numeric: true, cell: (c) => fmtNum(c.hhi, 2), sortValue: (c) => c.hhi },
    { key: 'articles', csvHeader: 'articles', header: t('col.articlesR'), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  return (
    <div className="container">
      <PageHeader title={t('gp.title')} lede={t('gp.lede', { a: r.start, b: r.end })} />
      {file.world.length ? (
        <Section id="world" title={t('gp.world.h')} intro={t('gp.world.intro')}>
          <DataTable caption={t('table.n', { n: 1, title: t('gp.world.table') })} rows={file.world} columns={worldColumns} rowKey={(w) => w.subfield} defaultSort={{ key: 'ratio', dir: 'desc' }} csvFilename={`atlas-${rel}-gaps-world.csv`} />
        </Section>
      ) : null}
      {few.length ? (
        <Section
          id="few"
          title={t('gp.few.h')}
          intro={t('gp.few.intro', { statuses: file.statuses.map((s) => statusName(t, s)).join(lang === 'en' ? ' or ' : 'หรือ'), n: fmtInt(file.max_institutions) })}
        >
          <DataTable caption={t('table.n', { n: 2, title: t('gp.few.table') })} rows={few} columns={fewColumns} rowKey={(f) => f.topic} stack={false} defaultSort={{ key: 'institutions', dir: 'asc' }} csvFilename={`atlas-${rel}-gaps-few-institutions.csv`} />
        </Section>
      ) : null}
      {bridges.length ? (
        <Section id="bridges" title={t('gp.bridge.h')} intro={t('gp.bridge.intro', { s: fmtNum(file.bridge_min_similarity, 2), j: fmtNum(file.bridge_max_jaccard, 2) })}>
          <DataTable caption={t('table.n', { n: 3, title: t('gp.bridge.table') })} rows={bridges} columns={bridgeColumns} rowKey={(b) => `${b.a}~${b.b}`} defaultSort={{ key: 'similarity', dir: 'desc' }} csvFilename={`atlas-${rel}-gaps-bridges.csv`} />
        </Section>
      ) : null}
      {file.concentration.length ? (
        <Section id="risk" title={t('gp.risk.h')} intro={t('gp.risk.intro', { m: fmtInt(file.min_articles), p: fmtPct(file.max_top_share, 0), h: fmtNum(file.max_hhi, 2) })}>
          <label className="check">
            <input type="checkbox" checked={state.all === 'yes'} onChange={(e) => update({ all: e.target.checked ? 'yes' : 'no' })} />
            {t('gp.risk.all')}
          </label>
          <DataTable caption={t('table.n', { n: 4, title: t('gp.risk.table') })} rows={risk} columns={riskColumns} rowKey={(c) => `${c.scope}:${c.id}:${c.kind}`} defaultSort={{ key: 'share', dir: 'desc' }} csvFilename={`atlas-${rel}-concentration.csv`} />
        </Section>
      ) : null}
      {hasModule(release, 'institutions') ? (
        <p className="note mt-6">
          {t('gp.collab')} <Link to="/institutions">{t('gp.collabLink')}</Link>
        </p>
      ) : null}
    </div>
  )
}
```

In `web/src/App.tsx` below `const GlobalPage = lazy(() => import('./pages/GlobalPage'))` insert `const GapsPage = lazy(() => import('./pages/GapsPage'))` and below `        <Route path="global" element={<Lazy><GlobalPage /></Lazy>} />` insert `        <Route path="gaps" element={<Lazy><GapsPage /></Lazy>} />`.

- [ ] **Step 3: Run the gate**

Run: `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e`
Expected: PASS — `/gaps` with the example and the empty release, axe clean in light and dark, 360 px without sideways scroll, `GapsPage-*.js` a lazy chunk.

- [ ] **Step 4: Commit**

```bash
git add src/pages/GapsPage.tsx src/lib/urlState.ts src/App.tsx e2e/smoke.spec.ts
git commit -m "feat(web): /gaps — world opportunities, thin emerging topics, weak bridges and concentration risk (R5, E10)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 12: Overview and brief additions, docs, polish pass and the final gates

**Files:**
- Modify: `web/src/pages/OverviewPage.tsx`, `web/src/pages/BriefPage.tsx`, `web/e2e/smoke.spec.ts`, `CLAUDE.md`, `README.md`, `web/README.md`, `DESIGN.md`, `docs/ARCHITECTURE.md`, `docs/DATA_SPEC.md`, `docs/OPERATIONS.md`, `docs/ROADMAP.md`
- Possibly modify (polish findings only): `web/src/styles/executive.css`, the six P3 pages, `web/src/strings/executive.ts`

**Interfaces:**
- Consumes: `Overview.executive` (Task 6), strings `ov.exec.h`, `brief.exec`, `brief.execNote`, CSS `.exec-points` (Task 7).
- Produces: overview section `#policy`; brief section `h2#brief-exec`; the P3 documentation.

- [ ] **Step 1: Failing e2e checks.** In `web/e2e/smoke.spec.ts` insert below `    await expect(page.locator('.kpi')).toHaveCount(8)`:

```ts
    await expect(page.locator('#policy li')).toHaveCount(3)
```

and below `    await expect(page.locator('[data-brief-ready="true"]')).toBeVisible()`:

```ts
    await expect(page.locator('h2#brief-exec')).toBeVisible()
```

Run: `npm run build && npx playwright test -g "overview|brief"` — Expected: FAIL.

- [ ] **Step 2: Policy sentences on the overview and in the brief.** In `web/src/pages/OverviewPage.tsx` insert below `  const bullets = brief ? ((lang === 'en' ? brief.bullets_en : brief.bullets_th) ?? []) : []`:

```tsx
  const exec = ov.executive ? ((lang === 'en' ? ov.executive.bullets_en : ov.executive.bullets_th) ?? []) : []
```

below `    ...(bullets.length ? [{ id: 'findings', label: t('ov.findings.h') }] : []),` insert `    ...(exec.length ? [{ id: 'policy', label: t('ov.exec.h') }] : []),`, and replace

```tsx
          {bullets.length ? (
            <Section id="findings" title={t('ov.findings.h')}>
              <Findings release={release} bullets={bullets} />
            </Section>
          ) : null}
```

with

```tsx
          {bullets.length ? (
            <Section id="findings" title={t('ov.findings.h')}>
              <Findings release={release} bullets={bullets} />
            </Section>
          ) : null}
          {exec.length ? (
            <Section id="policy" title={t('ov.exec.h')} intro={t('brief.execNote')}>
              <ul className="exec-points">
                {exec.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </Section>
          ) : null}
```

In `web/src/pages/BriefPage.tsx` insert below `  const bullets = brief ? ((lang === 'en' ? brief.bullets_en : brief.bullets_th) ?? []) : []`:

```tsx
  const exec = ov.executive ? ((lang === 'en' ? ov.executive.bullets_en : ov.executive.bullets_th) ?? []) : []
```

and insert directly above `      <section aria-labelledby="brief-status">`:

```tsx
      {exec.length ? (
        <section aria-labelledby="brief-exec">
          <h2 id="brief-exec">{t('brief.exec')}</h2>
          <ul className="brief-points">
            {exec.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
          <p className="note">{t('brief.execNote')}</p>
        </section>
      ) : null}
```

Run: `npm run lint && npx tsc -b && npm run build && npx playwright test -g "overview|brief"` — Expected: PASS. Run `npm run brief:pdf` against the example data once and look at the PDF: the policy section stays on the first two A4 pages with Thai fonts embedded.

- [ ] **Step 3: Polish pass.** Invoke `impeccable` in **audit/polish** mode on `/institutions`, `/institutions/mu-a`, `/regions`, `/sdg`, `/global`, `/gaps` and the grouped navigation at 1280 px and 360 px, light and dark, TH and EN (`npm run build && node scripts/serve.mjs --site dist --data fixtures/example/data --port 4173`). Fix only real findings (hierarchy, spacing, long Thai institution names wrapping, the map legend at 360 px, menu overlap with the search box), keep DESIGN.md tokens, re-run the web gate. Record anything deferred in `docs/ROADMAP.md`.

- [ ] **Step 4: Docs (Thai, matching the existing style).**
  - `DESIGN.md` — under `## Components` add `### Executives' pages (P3)`: the grouped navigation (disclosure buttons, 44 px items, 4 px underline on the group of the current page, Escape returns focus), the sequential ramp `--seq-1…5` (light/dark values; 5 quantile classes; "no data" = `--surface`; province strokes `--bg`), the choropleth rule (the table view is complete; the map never carries a number alone; legend with ranges), `.flag-on` (2 px border — "กระจุกตัว / Concentrated"), and the "possible partners" wording rule (a suggestion, never a ranking).
  - `CLAUDE.md` §2 tree: `pipeline/atlas/{places,institutions_ref,institutions,sdg,global_bench,gaps,export_exec}.py`, `pipeline/atlas/data/{th_provinces.csv,frameworks.yaml}`, `pipeline/registry/*.example.csv`, `web/src/geo/thProvinces.ts`, the six pages; §3 table: a row "P3 Executives: institutions + network + provinces (E6, E7, D6, R6), SDG/BCG/แผน ววน./แผนฯ 13 (E8), Thailand vs the world (E9), gaps + concentration (R5, E10), full KPIs + brief — ✅"; §5: contract **2.2** (new files, `Kpis` additions, `overview.executive`, `manifest.skipped_modules`); §6 Pipeline DO: "author rows are read for affiliations only (`institutions` drops name columns on read); institutions below `institutions.min_articles` are never listed, linked or paired"; Web DO: "a skipped module explains itself through `ModuleFile` (`manifest.skipped_modules`)".
  - `docs/DATA_SPEC.md`: the 15_–18_ checkpoints (columns as in each module docstring), `state_dir/ror/<dump>.<country>.json`, and the six contract files with every field (copy the pydantic fields and descriptions), plus the KPI units (percent in `Kpis`, fractions in module files).
  - `docs/OPERATIONS.md`: "ทะเบียนชื่อสถาบัน" — copy `pipeline/registry/institutions_aliases.example.csv` to `institutions_aliases.csv`, columns, the matching rule (folded, leftmost then longest, ≥ 4 characters), Rajabhat/Rajamangala campuses and abbreviations as rows, errors that stop the run; "ROR (ไม่บังคับ)" — download the latest ROR data dump from Zenodo (CC0) to a local folder, set `institutions.ror_path`, first run builds `state/ror/…` once; "ประชากรรายจังหวัด (ไม่บังคับ)" — `province_population.csv` from DOPA civil registration; "ไทยเทียบโลก" — 16 OpenAlex requests per release through the P1 fetcher and cache, keyless works, `OPENALEX_API_KEY` raises quotas, an offline run publishes no `global.json` and says why; "SDG/กรอบไทย" — editing `atlas/data/frameworks.yaml` (or `sdg.frameworks_path`), `sdg.method`, re-run `atlas run --step sdg --step export`; quarterly checklist gains "ตรวจ /institutions หาชื่อสถาบันที่ควรรวม แล้วเพิ่มในทะเบียนชื่อสถาบัน".
  - `docs/ARCHITECTURE.md`: steps `institutions → sdg → benchmark → gaps` after `match`; the ROR cache in `state_dir`.
  - `docs/ROADMAP.md`: "P3 — ผู้บริหาร (เสร็จ)" with the plan path; follow-ups: LLM confirmation of topic→goal links (off-by-default task), a node-link network drawing, YoY KPIs (4 quarters back), SDG chips on topic pages, campus-level provinces, hand-labelled precision sets (affiliations 500, SDG 300) from the spec's P2+ verification, official TCI journal/institution registries.
  - `README.md` and `web/README.md`: the six pages, the grouped navigation, `node scripts/make-province-map.mjs` (one-time, Natural Earth).

- [ ] **Step 5: Final gates**

```bash
cd pipeline && uv run ruff check . && uv run pytest -q && uv run pytest -m slow -q
cd ../web && npm run gen:types && git diff --exit-code -- src/data/contract.ts && npm run fixtures && git diff --exit-code -- fixtures
npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e
```

Expected: everything green; the slow two-quarter synthetic run keeps its P1 thresholds and now also exports institutions, regions, SDG and gaps (global skipped offline, with a reason).

- [ ] **Step 6: Commit**

```bash
git add -A ../CLAUDE.md ../README.md ../DESIGN.md ../docs src e2e README.md
git commit -m "feat(p3): policy sentences on the overview and in the brief; docs for the executives' release (registries, ROR, population, OpenAlex, SDG frameworks)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Definition of Done

- Pipeline: `uv run ruff check .`, `uv run pytest -q` and `uv run pytest -m slow -q` green; a release built with `atlas run` lists `institutions`, `institution_detail`, `regions`, `sdg`, `gaps` (and `global` when OpenAlex answered) in `manifest.modules`, and `manifest.skipped_modules` names any module left out with its reason; `atlas validate` reports no error; no person's name and no institution below `institutions.min_articles` appears in `institutions.json`, a detail file, a pair, a province top list or a concentration top; no network access in any test.
- Config: every new threshold is a key in `AtlasConfig` and documented in `config.example.yaml`; the alias table, ROR dump and population table are optional local files (real ones git-ignored).
- Web: the full gate is green — six new lazy routes render with the example and the empty release, axe 0 serious/critical in light and dark, no sideways scroll at 360 px, the grouped navigation works by keyboard; the entry chunk stays ≤ 180 KB gzip; the province outlines are < 300 KB and live in the `/regions` chunk; every chart has a table view and every list a CSV.
- Docs: CLAUDE.md, DESIGN.md, DATA_SPEC, OPERATIONS, ARCHITECTURE, ROADMAP and both READMEs describe P3.
- Not in this plan (recorded in ROADMAP): LLM confirmation of SDG links, a node-link network drawing, YoY KPIs, SDG chips on topic pages, hand-labelled precision sets.

## Self-review (2026-10-19)

- **Spec coverage:** institutions alias + ROR → province/type/country (T1, T2) · Rajabhat/Rajamangala via aliases (T1 example + test) · institution-level only / PDPA (T1, T2, T6 tests) · collaboration network + foreign countries (T2, T6, T8) · province map 77 provinces, per capita optional, public-domain outlines < 300 KB, table alternative (T1, T2, T6, T9) · SDG 17 + BCG + แผน ววน. + แผนฯ 13, embedding-or-lexical, coverage and gaps (T3, T6, T10) · OpenAlex benchmark with offline skip (T4, T6, T10) · gap finder R5 (T5, T6, T11) · concentration E10 (T5, T6, T11) · collaboration finder R6 (T2, T8) · D6 (T6 links, T8) · full KPI set + brief additions (T6, T7, T12) · pages + grouped nav + lazy routes (T7–T11) · contract 2.2.0 additive (T6) · config keys documented (T1) · docs (T12). Deliberately not built: LLM SDG confirmation (ruling 9), network drawing (ruling 8), YoY (ruling 13).
- **Placeholders:** none — every code step carries complete code; generated artifacts (`contract.schema.json`, `contract.ts`, fixtures, `thProvinces.ts`) come from committed scripts.
- **Type and name consistency (checked against `p2-editors` at `f0b38cf` and the P2 plan's Tasks 15–17):** pipeline — `journal_keys`, `journal_path`, `journal_code` (`atlas.registry`), `org_key`, `org_name`, `org_display_names` (`atlas.orgs`), `norm_key`, `clean_text`, `thai_ratio` (`atlas.thai`), `match_fold` (`atlas.matcher`), `HttpFetcher`, `OpenAlexUnavailable`, `Fetch`, `short_id` (`atlas.openalex`), `embed_texts` (`atlas.embed`), `load_topic_groups` (`atlas.taxonomy`), `C.JournalYear`, `C.TopicShare`, `C.CountItem`, `C.YearWindow`, `GROUP_ID`, `TOPIC_ID`, `Status`, `_unknown` (`atlas.validate`), `make_p2_work`, `NU`, `CU`, `TOKYO` (`tests/p2_work.py`); web — `ModuleFile`, `useReleaseFile`, `MODULE_FILES`, `hasModule`, `ShareBar`, `DataTable`/`Column` (`csvCols`, `csvOnly`, `firstDir`), `Figure`, `Tabs`, `TopicLink`, `OnThisPage`, `groupName`, `statusName`, `foldText`, `makeCodec`/`oneOf`/`text`/`VIEWS`, `fmtInt/fmtNum/fmtPct/fmtRatio/DASH`, CSS `.summary`, `.j-tools`, `.j-tags`, `.tp-badge`, `.tp-sub`, `.tp-alt`, `.flag`, `.check`, `.opp-list`, `.note`, `.source`. P3 names are defined once and reused: `inst_code` ids (`alias` id / `ror-…` / `o…`), checkpoint columns (`intl_share`, `inst_key`, `top_key`, `unit`), `executive_summary`, `skipped_modules`.
- **Known limits (accepted):** the province of an institution outside the alias table/ROR is guessed from the affiliation text (precision first; many stay unplaced, shown as coverage); the lexical SDG mapping depends on curated keywords (editable, shown as machine-made); OpenAlex counts use the primary topic of each work; full counting lets province and region shares exceed 100 % (said on the page).

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-19-p3-executives.md` (draft written to the scratchpad). The owner asked for minimal review: **Native** execution is recommended — the pipeline tasks (1–6) depend tightly on each other's checkpoint columns and the web tasks (7–12) on one fixture set, so one implementer keeping the whole picture plus one final whole-branch review is cheaper than a reviewer per task, and every task still ends on its own green gate.
