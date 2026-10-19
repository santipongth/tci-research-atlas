# P4 — Researchers' deep tools (article search · galaxy · keyword trends + glossary · references · RIS/BibTeX · feeds · embeds) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Lean plan (owner, 2026-10-19: "ปรับลดการ review และทดสอบลง เน้นเฉพาะเรื่องที่จำเป็น"):** tasks state requirements, interfaces, rulings and the tests that must exist; implementers write the code. One end-of-phase review; Critical/Important only.

**Goal:** Ship the researchers' release of TCI Research Atlas v2: whole-corpus article search (R2, sharded static index), the article galaxy (R8, WebGL), keyword trend explorer + TH↔EN glossary (R7), reference analytics + "cited in TCI" (D7, R12 — gated on coverage), RIS/BibTeX export + cite-this-atlas (R9), Atom feeds per release and per topic (R11) and embeddable chart widgets — as contract **2.3.0** (additive) and lazy pages `/search`, `/galaxy`, `/keywords`, `/references`, `/embed/*`.

**Architecture:** Same batch → checkpoint → JSON design as P2/P3. New steps after `gaps`: `references` (19_*), `search` (20_* — doc store, inverted index, galaxy points), `kwtrends` (21_*). `export_v2.build_release` adds optional module files (listed in `manifest.modules`, skips with a reason in `manifest.skipped_modules`). Feeds are written by `atlas publish` (they need the public site URL and every release on the site). The web reuses `ModuleFile`/`useReleaseFile`/`MODULE_FILES`, lazy routes and `check:bundle`.

**Tech Stack:** unchanged pins — Python 3.12 via `uv` (pandas 3, numpy, scikit-learn, pythainlp, pydantic v2, pytest, ruff); web React 19.3.1, react-router 7.18.4, Vite 7.3.7, vitest 4.1.12, Playwright 1.64.1 + axe 4.14.0, TypeScript 5.9.3. **No new dependency** (WebGL2 and Atom XML are written by hand).

**Spec:** `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md` — P4 section; catalog D7, R2, R7, R8, R9, R11, R12; "embed widget (iframe, P4)". Builds on the P2 plan (`ModuleFile`, `useReleaseFile`, `MODULE_FILES`, `check-bundle.mjs`, `make-fixtures.mjs`) and the P3 plan (contract 2.2, `skipped_modules`, grouped nav).

## Prerequisites
- `main` at the P3 fix commit (`6fca875` or later), CI green. Work on branch `p4-researchers`.
- Pushes/Pages/releases are pre-authorised by the owner for this repo (memory: feedback-minimal-autonomous) — but implementers never push; the controller does after the final review.

## Global Constraints (binding on every task)

Pipeline:
- Run from `pipeline/` with `uv run …`; pandas 3 safe (never test `dtype == object`; text via `.fillna("").astype(str)`); tables only via `atlas.io_utils.read_table`/`write_table`; strict JSON (no NaN/Infinity); persistent data only in `state_dir`; `work_dir` deletable.
- Every result-changing number is a key in `AtlasConfig` (`atlas/config.py`) **and** documented in `config.example.yaml` (`test_example_yaml_is_valid_and_documents_every_key`). New sections: `references`, `search`, `kwtrends`; `publish.site_url` (Task 4).
- Emerging `definition_version` stays 3; nobody touches `emerging.py` or status rules.
- Tests never touch the network. Thai single code points as `\N{THAI CHARACTER …}`/`chr()`; never a backslash-u escape (Python, TS, JS).
- Contract: every published file is a pydantic model in `atlas/schema/contract.py`; bump `SCHEMA_VERSION` to `2.3.0` (Task 1); after changing models run `uv run atlas schema` (in `pipeline/`) and `npm run gen:types` (in `web/`) and commit both generated files.
- `uv run ruff check --fix .` and the fast suite (`uv run pytest -q -m "not slow"`) green before each commit. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (or the model that actually wrote it).

Privacy & publishing (PDPA, owner rules — never relax):
- **No person data:** no author names, per-author rows or rankings of people in any published file — search docs, galaxy, references, RIS/BibTeX included. Article metadata published = id, title TH/EN, year, journal name, topic, DOI, ThaiJO URL, "cited in TCI" count.
- **No abstracts** in any published file (search indexes titles + author keywords only).
- Large module files (`search/`, `galaxy.json`) are excluded from the offline single HTML (`export.offline_exclude`); their pages explain that in the offline edition (the file is absent → `ModuleFile` reason).
- Synthetic demo data stays labelled (existing banner + noindex).

Web:
- Gate per web task (in `web/`): `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e`.
- Types only via generated `src/data/contract.ts` → `src/data/types.ts`. HashRouter; relative `${import.meta.env.BASE_URL}data/…`; no third-party request at run time; never call an API/LLM.
- DESIGN.md wins (tokens via `var(--…)`, no hex in `.tsx`, no dynamic Tailwind classes, status = glyph + colour + text, Thai: no italics, no letter-spacing, line-height ≥ 1.5). UI tasks invoke the `impeccable` skill first; charts follow `dataviz` (table view, numbered caption, "ที่มา:" line).
- Every string in `src/strings/*.ts` (th + en). New pages' strings live in their own strings file imported only by the lazy page (entry budget).
- Self-hiding sections; absent module → h1 + reason via `ModuleFile`; never a white page; axe serious/critical = 0 light + dark; targets ≥ 24 px; sortable headers `aria-sort`; info never by colour alone.
- Lint shapes: `.tsx` exports components only; no synchronous setState in effect bodies; no ref reads during render; copy before `.sort()`.
- **Entry budget 180 KB gzip** (was 175.9 after P3): new pages are `React.lazy`; Task 8 also makes `/atlas` and `/brief` lazy (P2 follow-up) to regain headroom.

## Rulings (decided)

1. **Contract 2.3.0, additive:** new optional files `references.json`, `search/meta.json`, `search/vocab.json`, `search/idx-<NNN>.json`, `search/docs-<NNN>.json`, `galaxy.json`, `kwtrends.json`; `TopicDetail` gains optional `glossary` (list of `{th, en, n}`) and `cited_in_tci` (int); `Latest` (latest.json) gains optional `feeds` (bool). Module names: `references`, `search`, `galaxy`, `kwtrends`.
2. **Doc order:** one ordinal per published article = position in `01_articles` sorted by `article_id` (only articles with a year in the analysed window and a non-empty title). Helper `atlas.search_index.doc_order(work) -> pd.DataFrame` used by search docs and galaxy so ordinals align.
3. **Search tokens** (`atlas.search_index.tokens(text) -> list[str]`): NFC, lowercase; Latin/digit runs split on non-alphanumerics, keep length ≥ 2, drop pure numbers except 4-digit years; Thai runs segmented with pythainlp `newmm`, keep tokens of ≥ 2 Thai chars; drop a small committed stopword list (TH/EN, in the module). Indexed fields: `title_th`, `title_en`, `keywords_th`, `keywords_en`. Index = token → sorted unique doc ordinals.
4. **Query tokenisation in the browser = greedy longest match against the published vocabulary** (Thai runs; max token length `search.max_token_chars`, 24), whitespace/punct split for Latin — implemented identically in Python (`atlas.search_index.query_tokens(q, vocab)`) and TS (`web/src/lib/searchTokens.ts`), pinned by a committed parity fixture `pipeline/tests/fixtures/search_parity.json` (vocab + ≥ 12 TH/EN/mixed queries → tokens). Unknown tokens are reported ("ไม่พบคำว่า …"), not silently dropped. Results = AND over known tokens; rank by number of title hits desc, then year desc, then ordinal; cap `search.max_results` (500) in UI.
5. **Shards:** index shard of a token = `fnv1a32(token) % search.index_shards` (default 64; FNV-1a over UTF-8 bytes, same in Python and TS, in the parity fixture); postings delta-encoded int arrays. Doc shards = ordinal // `search.docs_per_shard` (2000); a doc row = `[article_id, title_th, title_en, year, journal_index, topic_code|null, doi|null, url|null, cited_in_tci]` with `meta.json.journals` as the journal name list. Vocab = tokens with df ≥ `search.min_df` (1) sorted; `meta.json` carries `n_docs, index_shards, docs_per_shard, tokenizer_version, max_token_chars, journals, years`.
6. **Galaxy** (`galaxy.json`): columnar, aligned with doc ordinals: `x`, `y` quantised to 0…65535 over the map bounds (−1 = unassigned/no coordinate), `t` topic index into `topics` (list of topic codes, −1 = none), `yr` year; plus `bounds`. Source = `09_galaxy` (`gx, gy`) from P1 layout; skipped with a reason when `layout.galaxy` is false or the table is missing.
7. **Keyword trends** (`kwtrends.json`): author keywords (TH and EN separately, normalised like `atlas.keywords` does), keep the top `kwtrends.max_keywords` (3000) by total count with ≥ `kwtrends.min_count` (5); per keyword yearly counts over the series years, plus yearly article totals (`totals`) so the web plots share. **Glossary:** per article, when `keywords_th` and `keywords_en` have the same length ≥ 1, pair them by position; count pairs per topic and overall; publish per topic top `kwtrends.glossary_per_topic` (15) pairs with n ≥ `kwtrends.glossary_min_pairs` (2) into `topics/<id>.json.glossary`, and the overall top `kwtrends.glossary_max` (2000) into `kwtrends.json.glossary`.
8. **References (D7 + R12):** from `01_references` (counted = not self-citation, not translated duplicate). Coverage = share of window articles with ≥ 1 counted reference; module published only if coverage ≥ `references.min_coverage` (0.5), else `skipped_modules.references` = reason with the number. Per-journal practice (journals with ≥ `references.min_journal_articles` (20) articles with refs): median refs/article, median reference age (article year − ref year, refs with a year), share recent (age ≤ `references.recent_years`, 5), share Thai-script refs, share with a DOI. **Internal citation:** match a reference to a corpus article by (a) DOI (regex `10\.\d{4,9}/\S+`, lowercased, trailing punctuation stripped) else (b) exact normalised title segment: split the reference on `". "`/`"."`/`"? "`, normalise (casefold, strip spaces/punct, Thai kept), segments ≥ `references.min_title_chars` (15) looked up in a dict of normalised `title_th`/`title_en` (titles occurring once only); self-matches (same article) dropped; an article cited by another article counts once per citing article. Outputs: `cited_in_tci` per article (search docs, topic details), per topic received/given counts, top topic→topic flows (≥ `references.min_flow`, 3), top `references.top_articles` (50) most-cited articles (title, journal, year, link, count — no authors), matching method shares (doi/title). Internal citation is published only if ≥ `references.min_internal_matches` (20) matches; otherwise those sections are null with a reason.
9. **Feeds (R11):** `atlas publish --site` writes Atom 1.0 when `publish.site_url` is set (else prints a note and writes none): `data/feeds/releases.xml` (one entry per release present on the site, newest first, max `publish.feed_max_entries` 12: title = release, summary = overview headline + diff counts (new/gone/status changes) when `diff.json` exists, link `<site_url>#/changes`), and `data/feeds/topics/<code>.xml` for every topic of the newest release (entries = releases where that topic exists: status, articles in R, share growth; link `<site_url>#/topics/<code>`). Built only from the files on the site → idempotent; XML escaped by hand (`xml.sax.saxutils.escape`), `<updated>` = manifest `generated_at`. `latest.json.feeds = true` when written.
10. **RIS/BibTeX (R9):** generated in the browser from search results, topic representative articles and most-cited lists: `TY JOUR`/`@article` with title (TH, EN as `T2`/`note` when both), journal, year, DOI, URL, `N1 Source: TCI Research Atlas <release>`; **no authors** (Ruling: PDPA rule + we do not publish author names; DOI resolves the full citation). Cite-this-atlas: `/about` block with APA-like text + BibTeX `@misc` for the Atlas release, and `CITATION.cff` at the repo root.
11. **Embeds:** routes `/embed/topic/:id` (trend chart + status + title) and `/embed/emerging` (top 10 EMERGING/WATCH list), rendered without the app shell (no nav/footer, small attribution link "TCI Research Atlas" opening the full page in a new tab, demo banner kept when synthetic). Topic and emerging pages get an "ฝังกราฟ / Embed" disclosure with a copyable `<iframe>` snippet using `location.origin + location.pathname`. Embeds are lazy chunks.
12. **Navigation:** สำหรับนักวิจัย menu gains ค้นหาบทความ (`/search`), กาแล็กซีบทความ (`/galaxy`), แนวโน้มคำสำคัญ (`/keywords`); สำหรับบรรณาธิการ gains การอ้างอิง (`/references`). Global search box (header) stays topic search; the `/search` page links "ค้นหาบทความทั้งคลัง".
13. **Galaxy rendering:** raw WebGL2 (`gl.POINTS`, one draw call, colour by group token resolved from CSS at mount, size by zoom), pan/zoom with pointer + wheel + keyboard (+/−/arrows), hover/click → nearest point via a CPU grid → fetch its doc shard → card with title, journal, year, topic link, ThaiJO link. Filters: year range, topic group. No WebGL2 → h1 + explanation + link to `/atlas`. Accessible alternative: the page's "ตาราง" tab lists topics with article counts (from `topics.json`), as every chart does.
14. **SDG calibration helper (P3 follow-up):** `uv run atlas sdg-scores -c config.yaml` prints, from `16_topic_goal_scores` (write it in `sdg.py` when method is embedding: every topic×goal cosine), the score quantiles and how many topic–goal links each candidate threshold 0.30…0.60 (step 0.05) would give — read-only, no publish. Lexical runs print "embedding scores not computed (method lexical)".
15. **Tests (minimal):** one focused test file per new pipeline module (`test_references.py`, `test_search_index.py`, `test_kwtrends.py`, `test_feeds.py`), one appended `test_release` assertion (new files valid, no author name, no abstract text on the 11-real-file release), contract file list updated in `test_contract_v2`; web: `searchTokens.test.ts` (parity fixture), `citation.test.ts` (RIS/BibTeX), one e2e check per new route (+ the existing example/empty/axe loop covers them), fixtures extended in `make-fixtures.mjs`.

## Review Focus
1. **Thai query vs index tokenisation mismatch** → greedy-on-vocab in both languages, parity fixture; a query word absent from the vocab is named to the user — Task 2, Task 5.
2. **Author names or abstracts leaking** via search docs, references top lists or RIS/BibTeX → `test_release` scans every new file for author names/abstract snippets of the 11 real files; citation tests assert no `AU`/`author` — Tasks 1–3, 5.
3. **Low reference coverage (real corpus may have few parsed refs)** → `references` skipped with the coverage number; `/references` shows h1 + reason; topic pages hide "cited in TCI" — Task 1, Task 7.
4. **Large corpora (250–500K)** → search/galaxy built vectorised (no per-article Python loops over the full corpus except tokenisation, which is batched); shard sizes logged; files excluded from offline HTML — Task 2.
5. **Empty / pre-P4 release** → every new page shows h1 + reason; embeds of an unknown topic show a small "not found" — fixtures' empty release, e2e loop.

---

## File Structure

```
pipeline/atlas/references.py        (new)  step "references" → 19_ref_matches, 19_article_cites, 19_journal_refs, 19_topic_flows, 19_refs_meta.json
pipeline/atlas/search_index.py      (new)  step "search" → 20_docs, 20_postings (token, ordinal), 20_galaxy_points, 20_search_meta.json; tokens/query_tokens/fnv1a32/doc_order
pipeline/atlas/kwtrends.py          (new)  step "kwtrends" → 21_kw_years, 21_glossary, 21_kwtrends_meta.json
pipeline/atlas/export_research.py   (new)  checkpoints → contract 2.3 models/files (references.json, search/*, galaxy.json, kwtrends.json, glossary + cited_in_tci per topic)
pipeline/atlas/feeds.py             (new)  Atom writer used by publish
pipeline/atlas/{pipeline,config,export_v2,publish,cli,sdg}.py, schema/contract.py, config.example.yaml   (modified)
pipeline/tests/test_{references,search_index,kwtrends,feeds}.py (new), fixtures/search_parity.json (new)
web/src/lib/{searchTokens,searchClient,citation,galaxyGl}.ts (+ tests)
web/src/pages/{Search,Galaxy,Keywords,References}Page.tsx, web/src/embed/{EmbedTopic,EmbedEmerging}.tsx
web/src/strings/{search,galaxy,keywords,references,embed}.ts
web/scripts/make-fixtures.mjs (extend), web/e2e/* (extend)
CITATION.cff, docs/{DATA_SPEC,OPERATIONS,ROADMAP,ARCHITECTURE}.md, CLAUDE.md, README.md
```

---

### Task 1: references step + contract 2.3 skeleton (pipeline)

**Files:** create `atlas/references.py`, `atlas/export_research.py`, `tests/test_references.py`; modify `atlas/pipeline.py` (STEPS: add `references`, `search`, `kwtrends` after `gaps`, before `export`; map entries — `search`/`kwtrends` may point at stub functions that Task 2/3 fill), `atlas/config.py` + `config.example.yaml` (`references` section with every key of Ruling 8), `atlas/schema/contract.py` (`SCHEMA_VERSION = "2.3.0"`, `ReferencesFile`, `TopicDetail.cited_in_tci`, module names), `atlas/export_v2.py` (call `export_research.references_file(...)`; add module; skip reason), regenerate schema + TS types.

**Interfaces:**
- `references(cfg) -> None` (pipeline step): reads `01_articles`, `01_references`, `03_labels`/topic assignment the way `institutions.py` does; writes the 19_* checkpoints; prints coverage.
- `match_references(articles: pd.DataFrame, refs: pd.DataFrame, min_title_chars: int) -> pd.DataFrame[citing_id, cited_id, method]` (pure, unit-tested).
- `export_research.references_file(cfg, work, code_of_topic) -> (ReferencesFile | None, skip_reason | None)`; `cited_counts(work) -> dict[article_id, int]`.

**Required tests (`test_references.py`):** DOI match incl. trailing punctuation + case; Thai title-segment match; ambiguous duplicate titles not matched; self-citation dropped; one count per citing article; coverage below threshold → no file + reason containing the coverage %; per-journal practice medians on a tiny table; ReferencesFile has no author/abstract field.

- [ ] Implement, `uv run atlas schema`, `npm run gen:types` (web), ruff, fast suite, commit `feat(p4): references step — reference practice per journal and cited-in-TCI (contract 2.3)`.

### Task 2: search index + doc store + galaxy points (pipeline)

**Files:** create `atlas/search_index.py`, `tests/test_search_index.py`, `tests/fixtures/search_parity.json` (generated by a small function in the test module `--regen` style or a committed script `scripts/make_search_parity.py`; commit the JSON); modify `atlas/config.py` + example (`search`: `enabled`, `index_shards`, `docs_per_shard`, `min_df`, `max_token_chars`; galaxy uses `layout.galaxy`), `export_research.py` (search files + galaxy.json), `contract.py` (`SearchMeta`, `SearchVocab`, `SearchIndexShard` = dict token→delta list, `SearchDocShard`, `GalaxyFile`), `export_v2.py` (write `search/…` files and `galaxy.json`; modules `search`, `galaxy`), `config.py` `export.offline_exclude` default → `["match.json", "search", "galaxy.json"]` (and the example yaml), schema + types.

**Interfaces:** `tokens(text) -> list[str]`; `query_tokens(q, vocab: set[str], max_chars) -> tuple[list[str], list[str]]` (known, unknown); `fnv1a32(s) -> int`; `doc_order(work) -> DataFrame[ordinal, article_id, …]`; `search(cfg)` step writes `20_docs`, `20_postings`, `20_galaxy_points`, `20_search_meta.json`.

**Required tests:** Thai + English tokenisation of the 11 real fixture titles is stable (snapshot a few); stopwords dropped; years kept, other numbers dropped; postings sorted/unique and delta-decoding round-trips; shard of token stable (`fnv1a32("การ") ` value pinned); doc rows have no author/abstract; galaxy arrays length = n_docs and align with doc ordinals; parity fixture regenerates identically; scale smoke: 20K synthetic titles index in < 60 s (mark slow if needed).

- [ ] Implement, regenerate schema/types, ruff, fast suite, commit `feat(p4): sharded article search index, doc store and galaxy points`.

### Task 3: keyword trends + glossary (pipeline)

**Files:** create `atlas/kwtrends.py`, `tests/test_kwtrends.py`; modify config + example (`kwtrends` keys of Ruling 7), `export_research.py` (`kwtrends.json`, per-topic glossary), `contract.py` (`KwTrendsFile`, `GlossaryItem`, `TopicDetail.glossary`), `export_v2.py`; schema + types.

**Required tests:** normalisation merges case/spacing variants; min_count/max_keywords respected; totals per year equal article counts per year; glossary pairs by position only when list lengths match; per-topic top-N and min_pairs; JSON strict.

- [ ] Implement, ruff, fast suite, commit `feat(p4): keyword trends and TH-EN glossary per topic`.

### Task 4: feeds in publish + `publish.site_url` + sdg-scores CLI + release test + fixtures for slow e2e (pipeline)

**Files:** create `atlas/feeds.py`, `tests/test_feeds.py`; modify `atlas/publish.py` (call feeds after data copy when `publish.site_url`; set `latest.feeds`), `atlas/config.py` + example (`publish: {site_url: null, feed_max_entries: 12}` — if a `publish` section already exists, extend it), `contract.py` (`Latest.feeds: bool | None = None`), `atlas/sdg.py` (write `16_topic_goal_scores` when embedding), `atlas/cli.py` (`sdg-scores`), `tests/test_release.py` (append: P4 files valid, no author names/abstract text), `tests/test_contract_v2.py` file list; the slow two-quarter e2e gets one assertion that `search/meta.json` and `kwtrends.json` exist.

**Required tests (`test_feeds.py`):** valid XML (parse with `xml.etree`), escaping of `&<>` in Thai/English titles, newest-first ordering and max entries, per-topic feed count = topics of newest release, no feeds without site_url, idempotent (two runs → same bytes).

- [ ] Implement, ruff, fast + slow suite (`uv run pytest -q` and `uv run pytest -m slow -q`), commit `feat(p4): Atom feeds on publish, sdg-scores helper, release checks`.

### Task 5: web data layer + fixtures + `/search` + citation export

**Files:** `web/scripts/make-fixtures.mjs` (schema 2.3.0; example release gains synthetic `references.json`, `search/*` for ~600 synthetic docs, `galaxy.json`, `kwtrends.json`, topic `glossary` + `cited_in_tci`; empty release has none; `latest.json.feeds` false), `src/data/release.ts` (`MODULE_FILES` entries; helper to load `search/*` shards with an in-memory cache), `src/lib/searchTokens.ts` (+ test against `../pipeline/tests/fixtures/search_parity.json`), `src/lib/searchClient.ts` (vocab load, query → shards → AND → rank → docs), `src/lib/citation.ts` (+ test: RIS/BibTeX escaping, Thai titles, no author lines), `src/pages/SearchPage.tsx`, `src/strings/search.ts`, `App.tsx` (lazy route), nav entry, e2e check.

**Behaviour:** URL state `q`, `from`, `to`, `topic`, `journal` via `useUrlState`; results list (title in UI language with the other as subtitle, journal · year · topic link · ThaiJO link · DOI · "ถูกอ้างใน TCI n" when > 0); unknown words named; result count; export CSV / RIS / BibTeX of the (filtered) results; empty query shows tips; module absent → `ModuleFile` reason (also the offline edition).

- [ ] Gate, commit `feat(p4-web): whole-corpus article search with RIS/BibTeX export`.

### Task 6: `/galaxy` (WebGL2)

**Files:** `src/lib/galaxyGl.ts` (shader setup, buffers, draw, pick grid — pure functions unit-tested where possible: quantise/dequantise, grid nearest), `src/pages/GalaxyPage.tsx`, `src/strings/galaxy.ts`, route + nav, e2e check (canvas present or the no-WebGL message; in headless Chromium WebGL2 via SwiftShader normally exists — the e2e accepts either).

- [ ] Gate (impeccable first), commit `feat(p4-web): article galaxy (WebGL2) with pick-to-article`.

### Task 7: `/keywords`, `/references`, topic page additions

**Files:** `src/pages/KeywordsPage.tsx` (pick ≤ 5 keywords via accessible combobox over `kwtrends.json` keywords, `MultiLineChart` of share per year (count / totals) with table tab, URL state `k`; glossary table with filter), `src/pages/ReferencesPage.tsx` (coverage panel; per-journal practice table sortable + CSV; most-cited-in-TCI articles with RIS export; topic citation flows table; internal-citation null → reason), topic page: glossary section, "ถูกอ้างใน TCI" figure, SDG chips (P3 follow-up, from `Topic.sdg`), RIS/BibTeX buttons on representative articles; strings files; routes + nav; e2e checks.

- [ ] Gate (impeccable + dataviz), commit `feat(p4-web): keyword trends, glossary, reference practice and cited-in-TCI`.

### Task 8: embeds + cite-this-atlas + feed links + lazy `/atlas` `/brief` + polish

**Files:** `src/embed/EmbedTopic.tsx`, `src/embed/EmbedEmerging.tsx` (lazy, rendered outside the shell route), embed disclosure on topic + emerging pages, `/about` cite block (+ BibTeX copy), `CITATION.cff` (repo root; title, authors = organisation "Thai-Journal Citation Index Centre (TCI)", license CC-BY-4.0 for data, repository URL, version 2.0.0-p4), feed links (changes page + topic page, only when `latest.feeds`), make `AtlasPage` and `BriefPage` lazy (keep `/brief` PDF script working), `offline-template.html` gets `noindex` meta (P1 follow-up), `/match` result list max width (P2 follow-up); e2e: embed routes render without nav, about cite block.

- [ ] Gate, commit `feat(p4-web): embeddable widgets, cite this atlas, feed links; lazy atlas and brief`.

### Task 9: docs

Update `CLAUDE.md` (§2 tree, §3 table P4 row, §4 commands `sdg-scores`, `publish.site_url`, §5 contract 2.3 paragraph, §6 rules for search/galaxy/references privacy), `docs/DATA_SPEC.md` (new files + checkpoints 19–21), `docs/OPERATIONS.md` (search size notes, feeds + site_url, references gating, sdg-scores), `docs/ARCHITECTURE.md` (steps), `docs/ROADMAP.md` (P4 done section + follow-ups), `README.md` (feature list), `web/src/content/method.ts`/dictionary if they list files.

- [ ] Commit `docs(p4): researchers' release — contract 2.3, search, galaxy, references, feeds`.
