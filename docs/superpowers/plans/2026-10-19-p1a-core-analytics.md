# P1a — Core analytics v2 + LLM via API + data contract v2 release — Implementation Plan (reconciled against `0426434`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the P0 pipeline into the analytics engine of the first public release: stable topic ids with lineage, OpenAlex-anchored groups, Forecast v2 (share × total, NB/ETS, rolling-origin CV, honest skill gate, conformal 80/95 % intervals, nowcast of the partial year), emerging keywords, a map that stays put, all topic-level LLM work through one OpenAI-compatible adapter and one budgeted, resumable runner on P0's job plumbing (labels, merge suggestions, grounded narratives, executive brief, editor review), and a validated data contract v2 release that `atlas publish --site` puts on any static host (plus a single-file offline HTML) — everything CPU-testable offline.

**Architecture:** Same batch → checkpoint → JSON design. New steps `taxonomy` (after cluster), `keywords` (after emerging) and `narrate` (after forecast) plug into the P0 orchestrator; new modules `state`, `checkpoints`, `prompts`, `llm`, `llm_runner`, `lineage`, `graph_cluster`, `openalex`, `taxonomy`, `keywords`, `review`, `narrative`, `export_v2`, `validate`, `publish`, `bakeoff`. Everything the next quarter needs lives in `state_dir` (`releases/<release>/`, `llm_cache/`, `embeddings/`, `openalex/`); re-running a step for the same release is idempotent. Contract v2 files are built from pydantic models and written to `output/data/<release>/` with a sha256 manifest and `output/data/latest.json`; `atlas_data.json` 1.1 keeps feeding the current web until web v2 (P1b) ships.

**Tech Stack:** Python 3.12 via `uv`; pandas 3, numpy, pydantic v2, typer, scikit-learn 1.9, umap-learn, statsmodels 0.15 (GLM NB, damped Holt ETS), pythainlp. HTTP and long jobs: P0 Task 19's stdlib core `atlas/api_http.py` and `atlas/jobs.py` (no vendor SDK for LLMs). Optional extras: `leiden` (igraph ≥ 1.0 — wheels for Windows/macOS/Linux), `fast` (fast_hdbscan ≥ 0.3). pytest + hypothesis + ruff. **statsforecast is not used** — its 2.1 release pins `pandas<3`, which conflicts with the locked pandas 3.0.6; damped ETS is statsmodels `ExponentialSmoothing(trend="add", damped_trend=True)`.

**Spec:** `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md` — sections "รีวิวอัลกอริทึม", "Emerging v2", "Forecast v2", "สถาปัตยกรรม v2", "Data contract v2", "P1", "Verification" — and the user-approved delivery/LLM design (sections "ภาพรวมการส่งมอบ" and "LLM ผ่าน API ทั้งหมด", 2026-10-18). Builds on `docs/superpowers/plans/2026-10-18-p0-foundation.md` Tasks 1–18, the P0 final-review fix wave (Emerging `definition_version` 3, commits `8ae68fc`, `9015f83` and the rest of F1–F13) P0 Task 19 (API embedding runner with the shared HTTP core `api_http.py` and job helpers `jobs.py`, `11da552..3a9236b`) and P0 Task 20 (pre-production hardening, `0426434`) — all merged; this plan is written against `0426434` (`main` = `p1-core-analytics`). The earlier draft `2026-10-18-p1-core-analytics.md` (written against `9015f83` with stand-ins for Task 19) is superseded.

## Global Constraints

- All P0 Global Constraints still apply: run from `pipeline/` with `uv run …`; Python ≥ 3.11 (CI 3.12); pandas 3 safe (never test `dtype == object`, normalise text with `.fillna("").astype(str)`); tables only through `atlas.io_utils.read_table` / `write_table`; no hard-coded thresholds — every result-changing number is a key in `AtlasConfig` **and** documented in `config.example.yaml` (the P0 test `test_example_yaml_is_valid_and_documents_every_key` enforces it); UTF-8 stdout in CLIs; API keys only from env vars named in config (`ATLAS_EMBED_API_KEY`, `ATLAS_LLM_API_KEY`, `OPENALEX_API_KEY`); strict JSON (no NaN/Infinity); persistent data only in `state_dir`, `work_dir` safe to delete; six statuses; tests pass on Windows and Ubuntu; `uv run ruff check --fix .` before each commit; every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; never `git push` / create remotes / run `gh` without the owner's go-ahead (`atlas publish` only *prints* a `gh` command).
- **Emerging definition stays at `definition_version` 3** (user decision 2026-10-19). No task changes the status rules, thresholds, `last_complete_year` rule or the version; Task 10 adds nowcast tables computed *after* the v3 cutoff only.
- Thai text: Thai words may appear as literal UTF-8 in Python (as in P0 `synth.py`, `orgs.py`, `label.py`); single Thai code points used as characters or regex parts are written `\N{THAI CHARACTER …}` or `chr(0x0E..)`; **never** `\uXXXX` escapes.
- **Tests never touch the network.** Task 1 adds a session-scoped autouse fixture setting `ATLAS_OFFLINE=1`; OpenAlex, LLM and embedding APIs are always fakes (injected transports/objects) or recorded fixtures. Optional extras are imported lazily; their tests `skipif` the extra is missing (CI installs `--extra leiden --extra fast`). Because the P0 pydantic default `embedding.provider` became `local`, every P1 test that embeds or runs the pipeline sets `provider = "lite"` explicitly (or uses `configs/ci.yaml`).
- **LLM:** topic level only (no article-level calls; article methods classification stays off). One adapter (`atlas.llm.OpenAICompatLLM`, `POST {base_url}/chat/completions`, `response_format` only when the endpoint's `json_mode` is true) and one runner (`atlas.llm_runner.run_job`): JSONL cache = journal in `state_dir/llm_cache/<task>.jsonl` keyed by sha256(model + prompt_version + rendered prompt), up to `llm.max_repairs` JSON repairs, `llm.max_regenerations` regenerations for failed content checks, then the item's fallback (never cached), `llm.budget_usd` per release. Long-job plumbing is P0's `atlas.jobs`, exactly as the embedding runner uses it — `RunLock` (OS lock on `state_dir/llm_cache/.lock`, one LLM job at a time), `StopFlag` (`atlas llm-stop`), `ProgressFile` (`progress.json`, `kind: "llm"`, listed by the P0 `atlas status`), `RunStopped`, `spawn_background` (`atlas llm --background`). Permanent endpoint errors raise `LlmConfigError` (CLI exit 2); a stop, Ctrl-C or the budget raises `RunStopped` after the calls in flight (exit 130, the step writes nothing, the same command continues from the cache); another LLM job → `LockHeld` (exit 3).
- **Prompts:** `prompts/*.md` is the only copy of every prompt (section `## Prompt (master)` + one fenced block), read at run time; `prompt_version` = hash of that block only. Editing a prompt = edit one file and say so in the commit.
- **Topic ids:** integer N inside the pipeline (`topic_id`), published as `T%06d`; an id is never reused; `-1` = unassigned.
- **Releases:** `pipeline.release` (default today's `YYYYQn`) names the run; per-release state goes to `state_dir/releases/<release>/` through `atlas.state`; re-running any step for the same release gives the same result (it reads the *previous* release and overwrites only its own folder).
- **Contract v2:** every published file is a pydantic model from `atlas/schema/contract.py`; after changing a model run `uv run atlas schema` (from `pipeline/`) and `npm run gen:types` (from `web/`) and commit both generated files (CI checks drift). No abstracts and no person-level data in published files; colours are token keys `cat-01…cat-12`, never hex. Interval bounds keep the level-agnostic names `share_growth_lo/_hi` and the level is published as `manifest.ci_level`; `share_ratio` is `null` with `no_baseline: true` when the baseline window is empty.
- **Upstream P0 code this plan builds on (not planned here):**
  - *Fix wave* (Emerging v3, F1–F13, `8ae68fc..11da552`): t-quantile CI, `orgs_unverified`, not-estimable → LOW_DATA, backfill guard v3 (`as_of_year`, `backfill_ref_years`, `backfill_max_trim`, `trimmed_years`), v1.1 manifest fields (`ci_level`, `as_of_year`, `trimmed_years`, `n_orgs_unverified`, `embedding_provider/model_id`, `n_labels_fallback`, `ingest_errors`), `embedding.provider` default `local` + `lite_max_docs` warning, the all-noise `ValueError` in `cluster()`, per-file ingest errors (`read_thaijo_corpus -> (records, errors)`, `_parse_file_safe`, `work/01_ingest_errors`, `decode_replaced`), DOI dedup with title match, profile DOI collisions / forward-dated years / year-over-year, no forecast for LOW_DATA (export gate) and finite backtest MAEs only (`forecast_topic`), UTF-8 for `python -m atlas.pipeline`.
  - *P0 Task 19* (`11da552..3a9236b`, real names): `atlas.api_http` — `ApiConfigError`, `HttpPermanentError(status, body, headers)`, `TransientError`/`MalformedResponse(kind=…)`, `TooLargeError`, `TransientGaveUp`, `Cancelled`, `Transport`, `EventHandler`, `urllib_transport`, `validate_base_url`, `post_json(transport, url, payload, *, headers, timeout)`, `RetryPolicy(initial, cap, max_retries=None, sleep=None, rand=…)` (`.delay/.wait/.exhausted/.cancel`), `call_with_retry(send, policy, on_event)`, `RateLimiter`, `explain_permanent(status, body, *, key_env, base_url, model, location)`; `atlas.jobs` — `LOCK/OSLOCK/PROGRESS/STOP/LOG`, `RunLock(path, *, stale_seconds, heartbeat, log, wait)` (`acquire/release`, context manager; OS lock via msvcrt/fcntl) + `LockHeld(message, pid, hung)`, `LockUnsupported`, `RunStopped(message, abandoned)`, `StopFlag(path)` (`request/is_set/clear/clear_if_older`), `ProgressFile(path, min_interval)`, `now_iso`, `process_started_epoch`, `os_lock_held`, `spawn_background`, `find_jobs/job_status/format_job_status`; `atlas.embed_api` — `ApiEmbedder(cfg, transport, sleep, on_event, rand)`, `EmbeddingConfigError`, `api_store_id`; `atlas.embed_runner` — `run_embedding(texts, embedder, store, rcfg, *, progress=True, run_started=None) -> {…, status ∈ {done, stopped}}`, `StoreSaveFailed`/`StoreBusy`, `say`; `atlas.embed` — `get_embedder`, `store_id_for`, `store_root`, `runner_cfg`, `LocalEmbedder`; `atlas.embed_store` — `EmbeddingStore(root, model_id)` (`reload`, `dim`, exclusive `"xb"` shards), `store_dir`, `text_key`; `atlas.io_utils` — `replace_with_retry`, `unlink_with_retry`, `fsync_dir`, `replace_blocked`; `atlas.console.use_utf8_stdio`; CLI `atlas embed [--check|--dry-run|--background|--concurrency] | status | embed-status | embed-stop`, `_run_guarded` with exit codes 0/1/2/3/130. P1 adds no embedding client, HTTP client, lock or status renderer of its own.
  - *P0 Task 20* (`0426434`): `input.max_error_ratio` + `check_error_ceiling`, one-sided DOI dedup (`_drop_doi_duplicates`, `doi_title_conflicts`), the export pre-v3 guard (`orgs_unverified` required), reference-window wording in `last_complete_year`, vectorised DOI scan in `profile`.
- **Merging with upstream code:** every anchor in this plan quotes `0426434` (+ the earlier P1 tasks). Steps that edit a file the fix wave or P0 Tasks 19/20 changed — `config.py`, `config.example.yaml`, `embed.py`, `cluster.py`, `ingest.py`, `export.py`, `forecast.py`, `topics_time.py`, `cli.py`, `jobs.py`, `test_embed.py`, `test_cluster.py`, the docs — say which upstream behaviour they keep; `preflight.md` (next to this plan) lists every collision.
- Tasks run in order; each leaves `uv run ruff check . && uv run pytest -q` green.

## Decisions this plan takes

Settled (user or controller):
1. **Emerging stays at `definition_version` 3** (user, 2026-10-19). The journal-completeness rule and every v4 bump step of the previous draft are removed; Task 10 ships only the partial-year/month tables for the nowcast, computed after the unchanged v3 cutoff (`06_meta.completeness.method` is `median` = the v3 backfill guard, or `configured`).
2. **LLM cache key** = sha256(model + prompt_version + rendered prompt) where `prompt_version` hashes the prompt *template block* (controller: accepted). The P0 `state/label_cache.parquet` is not migrated: the first P1 run labels every topic once more (controller: accepted).
3. **Forecast skill/MASE are scored on honest selection errors** (model chosen from earlier origins only); intervals are calibrated on the published model's CV errors; the acceptance coverage pools 3 cut-off years.
4. **Narratives and brief default to templates** (`narrative.provider: template`), LLM opt-in; the grounding check is strict (numbers must equal a fact, rounded to 0–1 decimals; no unnamed topic) — one regeneration, then the template (controller: accepted).
5. **Merge suggestions are advice only** — never merged automatically (controller: accepted).
6. **Editors' overrides** live in `labeling.overrides_path` (pydantic default `None`; example config `./registry/label_overrides.csv`), `pipeline/registry/` is git-ignored (controller: accepted).
7. **`atlas llm` without flags runs the `label` and `narrate` steps** (then `atlas run … --step export`); `--check` sends one tiny request per endpoint/model, `--dry-run` estimates calls, tokens (≈ 1 token per character, an upper bound for Thai) and cost.
8. **OpenAlex reference set** = up to 100 sampled Thai-affiliated works per subfield (first page only, no API key; ~280 requests, cached in `state_dir/openalex/`). OpenAlex is read with its own small GET fetcher (`api_http` is POST-only).
9. **`share_growth_lo/_hi` names kept + `manifest.ci_level`**; no-baseline → `share_ratio: null`, `no_baseline: true`; `low_data_reason ∈ {few_articles, not_estimable}`.
10. **Profile items** (DOI collisions, forward-dated years, year-over-year) and token-aware batching (`max_batch_chars`) are upstream — not re-planned.
11. **Streaming ingest builds on the fix wave's per-file errors and error ceiling** (controller): Task 20 only replaces the reading lines of `ingest()`.

New in this reconciliation (controller: confirm or override):
12. **An LLM stop is a stop, not a degraded publish.** `atlas llm-stop`, Ctrl-C and `llm.budget_usd` raise `jobs.RunStopped` after the calls in flight (exit 130, nothing written by that step; the same command continues from the cache) — exactly like an embedding stop. The previous draft published keyword/template fallbacks for the unfinished items and cleared the stop flag, which let the next LLM step (narrate) start paying right after a stop. Fallbacks remain for per-item failures only (invalid JSON after `max_repairs`, failed grounding after `max_regenerations`, transient errors past an endpoint's `max_retries`) — never cached, asked again next run.
13. **One job plumbing, one status.** The LLM job is a P0 job folder (`state_dir/llm_cache/`): `atlas status` lists it through the P0 `render_status` (+ 3 LLM lines), `jobs.format_job_status` reads a generic `this_run` counter (embedding keeps `embedded`), `atlas llm --background` reuses `spawn_background`. `_run_guarded` gains `tag`/`resume` (defaults keep `atlas embed` byte-identical); `atlas run` now prints `[run]` and "resume: uv run atlas run" (P0 printed `[embed]`/`atlas embed` for every stop).
14. **Bake-off API candidates never inherit `embedding.api.dimensions`** (a bge-m3 candidate with `dimensions: null` must not send 1024).

## Review Focus

1. **The same release is run twice** (operator re-runs after a fix) → ids, lineage events and published files identical, no duplicate events — Task 4 (`test_cluster_step_keeps_ids_across_releases`) and Task 16 (release folder replaced).
2. **OpenAlex unreachable / offline / empty** → taxonomy falls back to agglomerative groups with a reason, the pipeline never stops — Task 9 (`test_no_reference_falls_back_to_agglomerative_groups`).
3. **The embedding model changes between quarters** → `auto` refits, never assigns against stale vectors — Task 4 (`test_embedding_model_change_forces_refit`); preprocess re-run without embed stops with a clear message — Task 2 (`CheckpointMismatch`).
4. **LLM money and failure paths**: budget stop raises `RunStopped`, then a re-run pays only for what is missing (Task 3 `test_budget_stops_cleanly_and_a_rerun_continues`); `atlas llm-stop` mid-job ends after the call in flight and resumes from the cache (Task 3 `test_stop_flag_ends_the_job_after_the_calls_in_flight`); a wrong key/model stops at the first call and keeps finished items (Task 3 `test_permanent_error_stops_the_job_and_keeps_finished_items`); a second LLM job is refused by the P0 OS lock (Task 3 `test_second_job_is_refused_while_the_lock_is_held`); `atlas status` shows the LLM job (Task 3 `test_cached_items_need_no_endpoint_and_status_and_dry_run_report`).
5. **An invented number never reaches an executive**: Task 14 (`test_llm_narratives_are_grounded_or_replaced`) — and `atlas validate` warns about every fallback before publishing (Task 17).
6. **A prompt file saved with CRLF by a Windows editor** loads identically and keeps its version — Task 3 (`test_crlf_prompt_file_loads_identically_and_version_hashes_the_template_only`).
7. **The previous release folder is missing or unreadable** when validating → warning, diff skipped — Task 17 (`test_missing_previous_release_only_warns`).
8. **Upstream behaviour survives P1's rewrites**: the all-noise error (Task 4, P0 `test_all_noise_*`), LOW_DATA / non-finite forecast guards (Task 11), per-file ingest errors + error ceiling + one-sided DOI dedup under the batched reader (Task 20, P0 F11/ceiling tests + `test_batched_parsing_gives_the_p0_tables_and_errors`), `definition_version` 3 everywhere (Tasks 10, 15).

## Verification status of the code in this plan

- **Re-verified 2026-10-19 against `0426434`** (scope set by the user: minimal experiments, static checks; no full replay of the test suite per task, no slow suite). Every task's edits are machine-checkable and were applied **in order, Tasks 1–22, to a plain copy of `0426434`** (`git archive`, no worktree): every anchor matched exactly once and `ruff check` was clean after every task. On the final tree all 45 `atlas.*` modules import and an AST scan finds every `from atlas.… import …` in `atlas/` and `tests/` resolving (P0 Task 19 symbols used: see `preflight.md`). While this was being written the branch moved to `746f003` (`jobs.pid_alive` ignores Linux zombies; two P0 test tweaks): no anchor or interface the plan uses changed (`format_job_status` line and `cli.py` identical).
- Tests actually run on that copy: the full fast suite after Task 1 (357 → 362 passed, 1 skipped) and after Task 2 (393 passed, 1 skipped) — run before the scope change; afterwards only the files whose code this reconciliation rewrote: Task 3 `test_llm.py` (20 passed) + P0 `test_embed_cli.py`/`test_jobs.py` (53 passed, regression for the `_run_guarded`/`format_job_status` edits); Tasks 6–7 label/review (31); Task 8 embed/openalex (18); Task 9 taxonomy/export (14); Task 10 series (9); Task 11 forecast (12, before one redundant test was dropped); Task 14 narrative (24 with llm); Tasks 15–19 contract/schema/release/bakeoff (25); Task 20 ingest/profile (32); final tree: config/schema (19) and llm, label, forecast, embed, series, ingest, contract_v2, release, cluster, lineage together (116 passed, 1 skipped, 1 min 36 s).
- **Not re-run:** the complete fast suite after Tasks 3–22 and the slow suite (P0 synthetic e2e, the 11-file UMAP regression and P1's `test_e2e_p1.py`). The last full run of those was the previous draft's replay on `9015f83` + stand-ins (261 fast tests, 3 slow passed in 11 min). Implementers run both at the steps that say so; expect the e2e thresholds to hold (no task changes the clustering, emerging or forecast maths relative to that replay — only the LLM plumbing, `embed_texts`, the ingest reader and the dropped v4 rule).
- Earlier prototype measurements cited in tasks (20K synthetic corpus, 6 min on Windows): stable ids kept 100 %, ARI 1.0 after a forced refit, taxonomy 100 %, planted EMERGING/WATCH/HOT/DECLINING recovered, 12/12 generative-AI keywords emerging and 12/12 Buddhism-online keywords journal-driven, map median shift ~30 px, release validates with 0 warnings, pooled 80 % coverage 0.79–0.81; fast_hdbscan ARI 1.0 vs sklearn and ~24× faster; Leiden 0.3 s/run vs HDBSCAN 19 s/run.

---

## File Structure

```
pipeline/
├── pyproject.toml / uv.lock / requirements.txt   MOD  extras: leiden, fast
├── config.example.yaml / atlas/config.py         MOD  P1 sections (Tasks 1–3, 6, 7, 11, 14, 20)
├── atlas/
│   ├── state.py          NEW  release naming, previous release, state_dir/releases/<release>/
│   ├── checkpoints.py    NEW  docs_fingerprint, load_aligned (02_docs ↔ 03_embeddings)
│   ├── prompts.py        NEW  load_prompt / prompt_version / render_prompt from prompts/*.md
│   ├── llm.py            NEW  OpenAICompatLLM on api_http (post_json + call_with_retry, fail-fast), extract_json
│   ├── llm_runner.py     NEW  cache/journal, repairs, regenerations, fallback, budget, JOBS — lock/stop/progress via atlas.jobs
│   ├── lineage.py        NEW  match_topics, assign_to_previous, registry + per-release topic state
│   ├── cluster.py        MOD  fit/assign + stable ids, fast HDBSCAN, Leiden option, load_aligned
│   ├── graph_cluster.py  NEW  kNN graph + igraph Leiden (optional extra)
│   ├── label.py          MOD  labels through the runner, prompt from file, overrides, label_source
│   ├── review.py         NEW  merge suggestions (LLM task merge), review export/import
│   ├── embed.py          MOD  docs fingerprint; embed_texts on get_embedder + run_embedding
│   ├── openalex.py       NEW  fields → subfields → sampled Thai works; cache; offline guard
│   ├── taxonomy.py       NEW  kNN subfield vote, cross_field, OpenAlex fields as groups, fallback
│   ├── topics_time.py    MOD  months + partial-year tables for the nowcast (v3 cutoff unchanged)
│   ├── forecast.py       MOD  Forecast v2 (rewrite)
│   ├── keywords.py       NEW  emerging keywords (step)
│   ├── narrative.py      NEW  grounded topic narratives + executive brief (step narrate)
│   ├── layout.py         MOD  stable layout + galaxy (rewrite)
│   ├── schema/contract.py MOD contract v2 file models
│   ├── export.py         MOD  v1.1 uses taxonomy groups; calls export_v2
│   ├── export_v2.py      NEW  output/data/<release>/ + manifest sha256 + latest.json
│   ├── validate.py       NEW  integrity + schema + coherence + diff + LLM fallbacks; exit codes
│   ├── publish.py        NEW  --site (data, latest.json, offline HTML via Python) + optional tarball
│   ├── bakeoff.py        NEW  embedding & clustering bake-offs, Markdown report
│   ├── ingest.py         MOD  batched parse (fix wave's _parse_file_safe) straight into tables; issue-year fill on the table
│   ├── synth.py          MOD  SUBFIELDS + reference_works(); generate(id_offset)
│   ├── pipeline.py       MOD  STEPS += taxonomy, keywords, narrate
│   ├── jobs.py           MOD  format_job_status reads a generic this_run counter (one line)
│   └── cli.py            MOD  llm [--background] | llm-stop | review | validate | publish | bakeoff; _run_guarded tag/resume; status lists the LLM job
└── tests/  test_state, test_checkpoints, test_llm, test_lineage, test_graph_cluster, test_review, test_openalex
            (+ fixtures/openalex/*.json), test_taxonomy, test_keywords, test_layout, test_narrative, test_contract_v2,
            test_release, test_bakeoff, test_e2e_p1 (slow); replaced: test_label, test_forecast; appended:
            test_config, test_embed, test_cluster, test_thai, test_series, test_ingest, test_synth
prompts/topic_label.th.md (notes) · topic_merge.th.md (rewritten) · topic_narrative.th.md (was emerging_narrative) · executive_brief.th.md (new)
web/src/data/contract.schema.json, contract.ts    REGEN (Task 15)
docs/{ARCHITECTURE,DATA_SPEC,OPERATIONS,ROADMAP}.md, CLAUDE.md, READMEs (Task 22) — docs/EMERGING_SPEC.md is NOT touched (definition v3)
.github/workflows/ci.yml (Task 21) · .gitignore (Task 6)
```

Work checkpoints added by P1a: `04_lineage`, `04_topics_meta.json`, `05_labels_meta.json`, `05_merge_suggestions`, `05_merge_meta.json`, `06_months`, `06_partial_year`, `07_keywords`, `08_forecast_meta.json`, `09_galaxy`, `10_taxonomy`, `10_taxonomy_meta.json`, `11_narratives`, `11_brief.json`; `06_meta.json` gains `partial_totals`, `completeness` (`{method: median | configured}`). State: `releases/index.json`, `releases/<rel>/topics/{assignments,registry,lineage}.parquet + model.json`, `releases/<rel>/layout.parquet`, `llm_cache/<task>.jsonl` + the P0 job files `.lock`, `run.lock`, `progress.json`, `stop.flag`, `run.log`, `openalex/reference_*`.

**How to read the edit steps:** "Replace X with Y", "After X insert Y", "Before X insert Y", "Replace the whole top-level function", "Replace the body of the section" and "Replace everything from the line starting …" are exact text operations (each anchor occurs once in the file as of `0426434` + the earlier tasks); a code block after "Create" or "Append" is the complete content.

---

## Task overview

| # | Task | Main outputs |
|---|---|---|
| 1 | P1 config, per-release state, offline guard | `state.py`, config sections |
| 2 | Checkpoint fingerprints, PCA sample, fast HDBSCAN, PUA table test | `checkpoints.py` |
| 3 | LLM core: adapter on `api_http`, prompts from files, runner on `atlas.jobs`, `atlas llm`, status | `prompts.py`, `llm.py`, `llm_runner.py` |
| 4 | Stable topic ids + lineage | `lineage.py`, `cluster.py` |
| 5 | Leiden option | `graph_cluster.py` |
| 6 | Label v2 on the runner + editor overrides | `label.py` |
| 7 | Merge suggestions + `atlas review export/import` | `review.py`, `topic_merge.th.md` |
| 8 | `embed_texts` on the P0 embedding helpers + OpenAlex reference works | `embed.py`, `openalex.py` |
| 9 | Taxonomy (OpenAlex fields as groups) | `taxonomy.py` |
| 10 | Partial-year tables for the nowcast (definition v3 unchanged) | `topics_time.py` |
| 11 | Forecast v2 | `forecast.py` |
| 12 | Emerging keywords | `keywords.py` |
| 13 | Stable layout + galaxy | `layout.py` |
| 14 | Grounded narratives + executive brief | `narrative.py`, 2 prompts |
| 15 | Contract v2 models | `schema/contract.py` |
| 16 | Export v2 release + latest.json | `export_v2.py` |
| 17 | `atlas validate` | `validate.py` |
| 18 | `atlas publish --site` (+ offline HTML, tarball) | `publish.py` |
| 19 | `atlas bakeoff` | `bakeoff.py` |
| 20 | Streaming ingest on the per-file error path | `ingest.py` |
| 21 | P1 acceptance e2e + CI extras | `test_e2e_p1.py` |
| 22 | Docs sync | docs, CLAUDE.md, READMEs |

---


## Definition of Done (P1a)

- [ ] `uv run ruff check .`, `uv run pytest -q` and `uv run pytest -m slow -q` pass on Windows and in CI (Ubuntu, with `--extra leiden --extra fast`); the schema/type drift checks are clean. P1 adds exactly one slow test (`tests/test_e2e_p1.py`); P0's two slow tests are unchanged.
- [ ] P1 acceptance (`tests/test_e2e_p1.py`, two synthetic quarters with a forced refit): ids kept ≥ 90 %, ARI ≥ 0.8 on shared articles, pooled 80 % interval coverage within 70–90 %, shown forecasts MASE < 1, ≥ 90 % of topics in their planted subfield, planted EMERGING/WATCH/HOT/DECLINING recovered, `chatgpt` emerging and `buddhism` journal-driven, median map shift < 5 % of the view width, release validates without errors and publishes to a site (latest.json + offline HTML + tarball).
- [ ] `uv run atlas run -c config.yaml` on the 11 real fixture files completes; `atlas validate` exits 0 or 1; `atlas publish --site <dir>` writes `data/<release>/`, `data/latest.json` (and `atlas-offline.html` when the template exists).
- [ ] Manual, with a real endpoint (operator or controller — needs a key, not part of CI): `atlas llm --check` OK (JSON + Thai), `atlas llm --dry-run` shows calls/tokens/cost, labelling the 11-file corpus produces Thai/English names, a second run makes 0 calls, `atlas llm-stop` and a budget stop both exit 130 and resume cleanly (the next run makes only the missing calls); `atlas status` shows the LLM job next to the embedding store; `atlas llm --background` survives closing the window.
- [ ] Docs (Task 22) describe every new command, file and key; `prompts/*.md` are the only prompt copies; no doc names `ATLAS_API_KEY` or `label_cache` except the one-time migration note.
- [ ] Emerging `definition_version` is still 3 everywhere (config, contract default, v1.1 meta, manifests, EMERGING_SPEC) — user decision 2026-10-19.
- [ ] Nothing pushed, no remote created, no `gh` command run.

## Spec / brief coverage

| Requirement | Task |
|---|---|
| Stable topic ids T000123 + lineage (containment ≥ 0.5, cosine tie-break, fit yearly / assign quarterly, refit on model change) | 4 |
| OpenAlex taxonomy (kNN k≈20, cross_field < 50 %, fields as groups, agglomerative fallback) | 8, 9 |
| Forecast v2 (share × total; naive/drift/NB GLM/damped ETS; ≥ 3 CV origins; MASE; conformal 80/95; skill gate; nowcast) | 11 |
| ~~Per-journal completeness → definition v4~~ — **not shipped** (user, 2026-10-19: keep definition v3); partial-year tables for the nowcast only | 10 |
| Emerging keywords (+ no_baseline) | 12 |
| Layout stability + galaxy | 13 |
| Contract v2 models, manifest sha256, `ci_level`, `low_data_reason`, `no_baseline`, v3 manifest fields, LLM accounting; `atlas_data.json` 1.1 kept | 15, 16 |
| `atlas validate` with exit codes (+ LLM fallback warnings) | 17 |
| `atlas publish --site` (data/<release>, latest.json, offline HTML via Python; tarball optional; never calls gh) | 18 |
| Bake-off (embedding + clustering; Leiden and fast HDBSCAN optional) reusing the P0 runner | 19 |
| Synth extension (SUBFIELDS, reference works, id_offset) | 9, 21 |
| P1 acceptance e2e | 21 |
| LLM: one OpenAI-compatible adapter on `api_http`, `llm.endpoints/tasks`, JSON mode per endpoint, pydantic validation, ≤ 2 repairs, fallback counted | 3, 6 |
| LLM runner: cache keyed by model + prompt version + input, journal, lock, progress, stop, budget, `atlas llm --check/--dry-run/--background`, `atlas status` — on P0 Task 19's `api_http` + `jobs` (no second lock/status implementation) | 3 |
| Prompts loaded from `prompts/*.md`; embedded copy removed | 3, 6, 7, 14 |
| Grounded narratives (top EMERGING/HOT/DECLINING) + executive summary, number/name post-check, one regeneration, template fallback | 14 |
| `atlas review export` (50-topic spot check) + `label_overrides.csv` keyed by stable id winning over LLM names | 6, 7 |
| Topic-level LLM only (no article-level calls) | 3 (constraint), 6, 7, 14 |
| P0-review items: Forecast v2 before release · nowcast (partial-year tables; journal completeness dropped with v4) · lo/hi naming + `ci_level` · `low_data_reason` · checkpoint fingerprints · streaming ingest · fast HDBSCAN evaluation · LLM fail-fast + fallback count · PCA sample key · table-driven PUA test · "new — no baseline" | 11 · 10/11 · 15/16 · 16 · 2 · 20 · 2/19 · 3/16/17 · 2 · 2 · 12/15/16 (UI: P1b) |
| P0-review items delivered upstream (not re-planned): token-aware batching (P0 Task 19 `max_batch_chars`), profile DOI collisions / forward-dated years / YoY (fix wave F4/F7/F11) | — |

## P1b / P1c outline (next plans — not part of P1a)

The web work starts only after P1a's contract v2 and site layout exist. Per the user's preferences, UI design/review work uses the `impeccable` skill first; the project's DESIGN.md (P1b-1) then wins over generic catalogs.

**P1b — Web v2 MVP (hybrid design)**
1. **DESIGN.md + tokens first** (user-approved hybrid): Civic modern base — Sarabun, civic blue `#0f3557`, link blue `#1a5bb0`, focus yellow `#ffd43b`, numbered tables and figures each with a "ที่มา:" line, chart/table tabs on every figure, WCAG 2.2 AA; Editorial headline sentence + CI forest plot against the +10 %/yr EMERGING bar on Overview; Cartographic terrain map on `/atlas` (pan/zoom canvas, layer toggles, gazetteer). Mood boards: the controller's `scratchpad\moodboards\`. Tokens become CSS variables + a Tailwind theme; CLAUDE.md §6 "Web" design-token rules are rewritten to point at DESIGN.md (the P0 tokens `#f5f6f2`/`#FF5F1F` retire with the old web).
2. **DataSource + routing**: HashRouter; read `data/latest.json` relative to `import.meta.env.BASE_URL`, then `data/<release>/*.json` lazily (topic details on demand); if `#atlas-data` holds a bundle, serve from it (offline file); typed by the generated `contract.ts`; no runtime API calls; loading/error/empty states; "new — no baseline" and `low_data_reason` rendered in words.
3. **`offline-template.html` build target**: a second Vite build that inlines JS/CSS into one HTML with `<script type="application/json" id="atlas-data">null</script>`, shipped in `dist/` so `atlas publish --site` can fill it (Task 18 contract).
4. **Overview**: brief headline (with "สรุปอัตโนมัติจากตัวเลขของระบบ" and its source), KPI tiles, CI forest plot of share growth (lo/hi at `manifest.ci_level`) against the +10 % bar, status counts, corpus by year + forecast + nowcast, data-quality notes (trimmed years, completeness method).
5. **/atlas (Cartographic)**: canvas map of topics on stable coordinates, OpenAlex field layers, status layer, galaxy of articles on zoom, gazetteer search (Thai segmentation via `Intl.Segmenter`), URL state for view/selection.
6. **/topics/:id**: narrative, metrics with CI, forecast chart with 80/95 bands + nowcast, lineage (born/split/merge), representative articles linking to ThaiJO, journals/institutions, neighbours, cross-field badge.
7. **/emerging**: table ⇄ chart tabs for EMERGING/WATCH/HOT/DECLINING, journal-driven and `orgs_unverified` explanations, emerging keywords.
8. Accessibility/i18n pass (keyboard map navigation, focus ring, contrast, no Thai italics, every string in `i18n.ts` th + en) and Playwright smoke tests in CI.

**P1c — More views + delivery**
1. `/compare` (two releases side by side from `data/<release>/`), `/data` (downloads + CSV export of any table), `/about` (method, definitions, licences), dark mode, URL state everywhere.
2. **PDF brief**: a print route rendered by Playwright — in CI as an artifact, or locally via `atlas brief --pdf` behind an optional `pdf` extra (Python Playwright); content = Overview brief + top tables.
3. **Pages deploy** workflow with the base path + data downloaded from GitHub Releases (tarballs from `atlas publish --tarball`); every push/release step waits for the owner's go-ahead.
4. Optional later: article-level methods classification (LLM, off by default), author-free institution views.

## Self-review (reconciliation against `0426434`, 2026-10-19)

- Every code block that implementers type was applied mechanically, in task order, to a plain copy of `0426434` (see Verification status); every anchor exists exactly once at the point its step runs. Anchors in files the fix wave or P0 Task 19 changed (`config.py`, `embed.py`, `cluster.py`, `ingest.py`, `export.py`, `forecast.py`, `topics_time.py`, `cli.py`, `jobs.py`, `test_embed.py`, `test_cluster.py`, the docs) quote HEAD text, not `9015f83` text.
- The P0 Task 19 stand-in names of the previous draft are gone: no `write_progress`, `request_stop/stop_requested/clear_stop` (jobs), `RunLock(lock, progress, stale)`, `LlmTransientError`, `classify_http`/`parse_retry_after` call sites, or `ApiEmbedder` construction in P1 code. The LLM uses `post_json` + `call_with_retry` + `explain_permanent`; the runner uses `RunLock` / `StopFlag` / `ProgressFile` / `RunStopped` / `spawn_background`; `embed_texts` uses `get_embedder` / `runner_cfg` / `store_root` / `run_embedding`.
- Upstream behaviour kept where P1 rewrites a function: the all-noise `ValueError` (Task 4 `fit_labels`), the LOW_DATA and non-finite-MAE forecast guards (Task 11, each with a test), the per-file ingest errors + `input.max_error_ratio` ceiling + one-sided DOI dedup (Task 20 changes only the reading lines), the v1.1 manifest keys and pre-v3 export guard (Tasks 9, 16 add lines around them).
- Names are consistent across tasks: `run_job`/`LlmJob`/`LlmItem`/`LlmResult(key)`, `JOBS` grows label → merge → narrative/brief, `status_extra`, `topic_titles`, `load_aligned`, `publication_months`, `rolling_coverage`, `write_release`, `validate_release`, `publish(cfg, release, allow_warnings, site, tarball)`.
- Tests were trimmed to one focused test per behaviour (dropped: the adapter-level `max_retries` test — `call_with_retry` exhaustion is P0-tested, the LLM-level fallback has its own test; the second `embed_texts` wiring test; the three journal-completeness tests; the fenced-JSON label test — `extract_json` has its own; the forecast "defaults" lock; the duplicate unreadable-file ingest test — the fix wave's F11 tests cover it). P1 adds exactly one slow test.

### Task 1: P1 configuration, per-release state helpers, offline test guard

**Files:**
- Modify: `pipeline/atlas/config.py`, `pipeline/config.example.yaml`, `pipeline/tests/test_config.py` (append), `pipeline/tests/conftest.py` (append)
- Create: `pipeline/atlas/state.py`, `pipeline/tests/test_state.py`

**Interfaces:**
- Consumes: P0 `AtlasConfig`, `load_config(path) -> dict` (with the Emerging v3 keys of the fix wave).
- Produces:
  - Config keys used later (exact names): `pipeline.release`; `clustering.algorithm`, `clustering.leiden.{k,resolution,min_cluster_size,n_iterations}`; `topics.{mode,refit_every_releases,refit_max_unassigned,match_containment,match_min_shared}`; `taxonomy.{source,reference_path,openalex.{base_url,mailto,api_key_env,country_code,per_subfield,seed,timeout,max_retries},k,max_articles_per_topic,min_vote_share,holdout_frac}`; `keywords.{enabled,min_docs_recent,max_doc_share,novelty_min_ratio,min_active_years,min_orgs,min_journals,max_new_journal_share,min_growth_lo,max_terms}`; `layout.{stable,anchor,init_neighbors,galaxy}`; `export.{v2,repr_articles,max_topic_journals,max_topic_orgs,max_neighbors}`; `validation.{max_topic_count_change,min_kept_ids,max_status_change_frac,size_swing_ratio,size_swing_min_articles,max_article_drop}`; `bakeoff.{sample,k,holdout_frac,seeds,algorithms,npmi_top_n,embedding_candidates[{name,provider,model,base_url,dimensions,store_id}]}`. LLM keys (`llm.*`), labeling v2, review and narrative keys are added by Tasks 3, 6, 7 and 14. `load_config` resolves `taxonomy.reference_path` like the other paths.
  - `atlas.state`: `RELEASE_RE`, `release_from_date(d: date) -> str` (`"2026Q4"`), `current_release(cfg) -> str`, `known_releases(cfg) -> list[str]`, `previous_release(cfg) -> str | None`, `release_dir(cfg, release: str | None = None, create: bool = False) -> Path` (`create=True` registers the release in `state_dir/releases/index.json`).
  - conftest: session-scoped autouse fixture `_offline` (sets `ATLAS_OFFLINE=1`).

Read `config.py` and `config.example.yaml` first: the P0 fix wave (Emerging v3, `embedding.provider` default `local`, `embedding.lite_max_docs`) changed them; every anchor below is a line it did not touch (checked against `0426434`).

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_state.py`:

```python
from datetime import date

import pytest

from atlas.state import current_release, known_releases, previous_release, release_dir, release_from_date


def test_release_from_date_quarters():
    assert release_from_date(date(2026, 1, 5)) == "2026Q1"
    assert release_from_date(date(2026, 10, 18)) == "2026Q4"


def test_previous_release_tracks_index(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q1"
    assert previous_release(cfg) is None
    release_dir(cfg, create=True)
    cfg["pipeline"]["release"] = "2026Q2"
    assert previous_release(cfg) == "2026Q1"
    d = release_dir(cfg, create=True)
    assert d.name == "2026Q2" and d.is_dir()
    release_dir(cfg, create=True)                      # re-run of the same release: no duplicate
    assert known_releases(cfg) == ["2026Q1", "2026Q2"]
    assert previous_release(cfg) == "2026Q1"           # still the one BEFORE the current release
    cfg["pipeline"]["release"] = "2026Q1"
    assert previous_release(cfg) is None


def test_bad_release_name_rejected(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "../evil"
    with pytest.raises(ValueError):
        current_release(cfg)
```

Append to `pipeline/tests/test_config.py`:

```python


def test_p1_sections_have_defaults():
    cfg = load_config(None)
    assert cfg["pipeline"]["release"] is None
    assert cfg["topics"]["mode"] == "auto" and cfg["taxonomy"]["source"] == "openalex"
    assert "completeness" not in cfg["emerging"]                    # definition v3 stays (user, 2026-10-19)
    assert cfg["validation"]["min_kept_ids"] == 0.9 and cfg["bakeoff"]["embedding_candidates"] == []


def test_release_name_and_reference_path(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("pipeline:\n  release: 2026Q4\ntaxonomy:\n  reference_path: ref/works.jsonl\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg["pipeline"]["release"] == "2026Q4"
    assert Path(cfg["taxonomy"]["reference_path"]) == (tmp_path / "ref" / "works.jsonl").resolve()
    p.write_text("pipeline:\n  release: ../x\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(p)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_state.py tests/test_config.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.state'` and `KeyError: 'release'`.

- [ ] **Step 3: Edit `pipeline/atlas/config.py`** (each anchor occurs once)

3a. Release name in `PipelineCfg`:
After
```python
    state_dir: str = "./state"        # persistent: embedding store, label cache, previous run
    seed: int = 42
```
insert
```python
    release: str | None = Field(None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")  # None → YYYYQn of today
```

3b. Leiden settings and the clustering algorithm:
Replace
```python
class ClusteringCfg(_Strict):
    reducer: Literal["umap", "pca"] = "umap"
```
with
```python
class LeidenCfg(_Strict):
    k: int = Field(15, ge=2)
    resolution: float = Field(1.0, gt=0.0)
    min_cluster_size: int = Field(150, ge=2)
    n_iterations: int = -1


class ClusteringCfg(_Strict):
    algorithm: Literal["hdbscan", "leiden"] = "hdbscan"
    leiden: LeidenCfg = Field(default_factory=LeidenCfg)
    reducer: Literal["umap", "pca"] = "umap"
```

3c. Topic ids and taxonomy sections:
Before
```python
class SizeCfg(_Strict):
```
insert
```python
class TopicsCfg(_Strict):
    mode: Literal["auto", "fit", "assign"] = "auto"
    refit_every_releases: int = Field(4, ge=1)
    refit_max_unassigned: float = Field(0.15, ge=0.0, le=1.0)
    match_containment: float = Field(0.5, gt=0.0, le=1.0)
    match_min_shared: int = Field(5, ge=1)


class OpenAlexCfg(_Strict):
    base_url: str = "https://api.openalex.org"
    mailto: str = ""
    api_key_env: str = "OPENALEX_API_KEY"
    country_code: str = "TH"
    per_subfield: int = Field(100, ge=1, le=100)
    seed: int = 42
    timeout: float = 30.0
    max_retries: int = Field(3, ge=1)


class TaxonomyCfg(_Strict):
    source: Literal["openalex", "off"] = "openalex"
    reference_path: str | None = None
    openalex: OpenAlexCfg = Field(default_factory=OpenAlexCfg)
    k: int = Field(20, ge=1)
    max_articles_per_topic: int = Field(200, ge=1)
    min_vote_share: float = Field(0.5, ge=0.0, le=1.0)
    holdout_frac: float = Field(0.2, gt=0.0, lt=1.0)


```

3d. Emerging keywords:
Before
```python
class LayoutCfg(_Strict):
```
insert
```python
class KeywordsCfg(_Strict):
    enabled: bool = True
    min_docs_recent: int = Field(7, ge=1)
    max_doc_share: float = Field(0.15, gt=0.0, le=1.0)
    novelty_min_ratio: float = Field(2.0, gt=0.0)
    min_active_years: int = Field(3, ge=1)
    min_orgs: int = Field(3, ge=0)
    min_journals: int = Field(3, ge=0)
    max_new_journal_share: float = Field(0.5, gt=0.0, le=1.0)
    min_growth_lo: float = 0.0
    max_terms: int = Field(50, ge=1)


```

3e. Stable layout:
After
```python
    max_edges_per_node: int = 4
```
insert
```python
    stable: bool = True
    anchor: float = Field(0.9, ge=0.0, le=1.0)
    init_neighbors: int = Field(3, ge=1)
    galaxy: bool = True
```

3f. Export v2 keys, then the `validation` and `bakeoff` sections (named `validation`, not `validate`: a pydantic field called `validate` shadows `BaseModel.validate`):
After
```python
    include_forecast_in_json: bool = True
```
insert
```python
    v2: bool = True
    repr_articles: int = Field(12, ge=1)
    max_topic_journals: int = Field(10, ge=1)
    max_topic_orgs: int = Field(10, ge=1)
    max_neighbors: int = Field(6, ge=0)


class ValidateCfg(_Strict):
    max_topic_count_change: float = Field(0.25, ge=0.0)
    min_kept_ids: float = Field(0.9, ge=0.0, le=1.0)
    max_status_change_frac: float = Field(0.3, ge=0.0, le=1.0)
    size_swing_ratio: float = Field(2.0, gt=1.0)
    size_swing_min_articles: int = Field(50, ge=1)
    max_article_drop: float = Field(0.02, ge=0.0, le=1.0)


class BakeoffCandidate(_Strict):
    name: str
    provider: Literal["api", "local", "lite"]
    model: str = ""
    base_url: str = ""
    dimensions: int | None = None
    store_id: str | None = None       # api only; None → the P0 runner's default "api|<model>|<dimensions>"


class BakeoffCfg(_Strict):
    sample: int = Field(5000, ge=50)
    k: int = Field(10, ge=1)
    holdout_frac: float = Field(0.2, gt=0.0, lt=1.0)
    seeds: list[int] = Field(default_factory=lambda: [1, 2, 3])
    algorithms: list[Literal["hdbscan", "hdbscan_fast", "leiden"]] = Field(
        default_factory=lambda: ["hdbscan", "hdbscan_fast", "leiden"])
    npmi_top_n: int = Field(10, ge=2)
    embedding_candidates: list[BakeoffCandidate] = Field(default_factory=list)
```

3g. Register the sections in `AtlasConfig`:
Replace
```python
    labeling: LabelingCfg = Field(default_factory=LabelingCfg)
    emerging: EmergingCfg = Field(default_factory=EmergingCfg)
```
with
```python
    labeling: LabelingCfg = Field(default_factory=LabelingCfg)
    topics: TopicsCfg = Field(default_factory=TopicsCfg)
    taxonomy: TaxonomyCfg = Field(default_factory=TaxonomyCfg)
    emerging: EmergingCfg = Field(default_factory=EmergingCfg)
    keywords: KeywordsCfg = Field(default_factory=KeywordsCfg)
```
After
```python
    export: ExportCfg = Field(default_factory=ExportCfg)
```
insert
```python
    validation: ValidateCfg = Field(default_factory=ValidateCfg)
    bakeoff: BakeoffCfg = Field(default_factory=BakeoffCfg)
```

3h. Resolve the reference path in `load_config`:
Replace
```python
    cfg["input"]["path"] = _resolve(cfg["input"]["path"], base)
    return cfg
```
with
```python
    cfg["input"]["path"] = _resolve(cfg["input"]["path"], base)
    if cfg["taxonomy"]["reference_path"]:
        cfg["taxonomy"]["reference_path"] = _resolve(cfg["taxonomy"]["reference_path"], base)
    return cfg
```

- [ ] **Step 4: Edit `pipeline/config.example.yaml`** (every new key documented — the P0 test `test_example_yaml_is_valid_and_documents_every_key` compares the key sets)

4a. Release:
After
```yaml
  seed: 42
```
insert
```yaml
  release: null               # ชื่อรอบข้อมูล เช่น 2026Q4 — null = ไตรมาสของวันที่รัน (YYYYQn); state แยกตามรอบ
```

4b. Clustering algorithm:
Replace
```yaml
clustering:
  reducer: umap               # umap | pca
```
with
```yaml
clustering:
  algorithm: hdbscan          # hdbscan (UMAP→HDBSCAN) | leiden (Leiden บน kNN graph — ต้อง uv sync --extra leiden)
  leiden:
    k: 15                     # เพื่อนบ้านต่อบทความใน kNN graph
    resolution: 1.0           # สูง = หัวข้อเล็กลง/มากขึ้น
    min_cluster_size: 150     # community ที่เล็กกว่านี้ = ยังไม่จัดหมวด (−1)
    n_iterations: -1          # −1 = วนจนผลนิ่ง
  reducer: umap               # umap | pca
```

4c. Topic ids and taxonomy:
Before
```yaml
# ---------- Emerging v3 — นิยามเต็มใน docs/EMERGING_SPEC.md ----------
```
insert
```yaml
# ---------- หัวข้อที่มี ID ถาวรข้ามรอบ (T000123) ----------
topics:
  mode: auto                  # auto | fit | assign — auto: assign ทุกไตรมาส, fit ใหม่เมื่อครบรอบ/โมเดล embedding เปลี่ยน/บทความใหม่หาที่ลงไม่ได้
  refit_every_releases: 4     # fit ใหม่อย่างน้อยทุก 4 รอบ (ปีละครั้ง)
  refit_max_unassigned: 0.15  # auto: บทความใหม่ > 15% ไม่ใกล้หัวข้อใดเลย → fit ใหม่
  match_containment: 0.5      # ตอน fit ใหม่ จับคู่หัวข้อเก่า↔ใหม่เมื่อบทความร่วม ≥ 50% (ฝั่งใดฝั่งหนึ่ง)
  match_min_shared: 5         # และมีบทความร่วมอย่างน้อยเท่านี้

# ---------- กลุ่มใหญ่ = OpenAlex fields (นิ่งข้ามรอบ + เทียบสากลได้) ----------
taxonomy:
  source: openalex            # openalex | off (off = ใช้กลุ่ม agglomerative ของ P0)
  reference_path: null        # ไฟล์งานอ้างอิง (.jsonl/.parquet/.csv) แบบ offline — null = ดึงจาก OpenAlex API แล้ว cache ใน state_dir
  openalex:
    base_url: https://api.openalex.org
    mailto: ""                # อีเมลติดต่อ (ส่งเป็นพารามิเตอร์ mailto)
    api_key_env: OPENALEX_API_KEY   # ไม่บังคับ — ชื่อ env var ของ API key (การดึงหน้าแรกแบบ sample ไม่ต้องใช้ key)
    country_code: TH          # งานที่มีผู้แต่งสังกัดประเทศนี้
    per_subfield: 100         # จำนวนงานตัวอย่างต่อ subfield (สูงสุด 100 = 1 request)
    seed: 42
    timeout: 30
    max_retries: 3
  k: 20                       # kNN: เพื่อนบ้านที่ใช้โหวต subfield
  max_articles_per_topic: 200 # บทความที่ใกล้ centroid ที่สุดที่ใช้โหวตต่อหัวข้อ
  min_vote_share: 0.5         # โหวตชนะ < 50% → cross_field
  holdout_frac: 0.2           # สัดส่วนงานอ้างอิงที่กันไว้วัดความแม่น kNN

```

4d. Emerging keywords:
Before
```yaml
forecast:
```
insert
```yaml
# ---------- Emerging keywords (ระดับคำสำคัญ — Carley/Porter) ----------
keywords:
  enabled: true
  min_docs_recent: 7          # อย่างน้อย 7 บทความในช่วง R
  max_doc_share: 0.15         # คำที่อยู่ใน > 15% ของบทความ = คำทั่วไป ตัดทิ้ง
  novelty_min_ratio: 2.0      # ใหม่: share ใน R ≥ 2 เท่าของช่วง B
  min_active_years: 3         # ต่อเนื่อง: ปรากฏ ≥ 3 ปีในช่วง W
  min_orgs: 3                 # ≥ 3 สถาบันในช่วง R
  min_journals: 3             # ≥ 3 วารสารในช่วง R (ไม่ผ่าน = journal_driven)
  max_new_journal_share: 0.5  # บทความจากวารสารที่เพิ่งเข้าระบบใน R ต้อง < 50%
  min_growth_lo: 0.0          # โตจริง: CI ล่างของอัตราโต share > ค่านี้
  max_terms: 50               # จำนวนคำสูงสุดที่ส่งออก

```

4e. Stable layout:
After
```yaml
  max_edges_per_node: 4
```
insert
```yaml
  stable: true                # วางแผนที่ต่อจากรอบก่อน (หัวข้อเดิมอยู่ที่เดิม)
  anchor: 0.9                 # 1 = หัวข้อเดิมอยู่ตำแหน่งเดิมทุกประการ, 0 = ตาม UMAP รอบนี้ (หลังจัดแนวแล้ว)
  init_neighbors: 3           # หัวข้อใหม่วางตามหัวข้อเดิมที่คล้ายที่สุด 3 หัวข้อ
  galaxy: true                # พิกัดบทความรอบหัวข้อ (work/09_galaxy)
```

4f. Export v2, validation, bake-off:
After
```yaml
  include_forecast_in_json: true
```
insert
```yaml
  v2: true                    # เขียน data contract v2 → output/data/<release>/ (+ atlas_data.json 1.1 เหมือนเดิม)
  repr_articles: 12           # บทความตัวแทนต่อหัวข้อ (ชื่อเรื่อง + ลิงก์ ThaiJO — ไม่เผยแพร่บทคัดย่อ)
  max_topic_journals: 10
  max_topic_orgs: 10
  max_neighbors: 6

# ---------- atlas validate: เทียบกับรอบก่อน ----------
validation:
  max_topic_count_change: 0.25  # จำนวนหัวข้อเปลี่ยน > 25% → warning
  min_kept_ids: 0.9           # ID หัวข้อรอบก่อนที่ยังอยู่ < 90% → warning
  max_status_change_frac: 0.3 # หัวข้อเดิมที่เปลี่ยนสถานะ > 30% → warning
  size_swing_ratio: 2.0       # ขนาดหัวข้อเปลี่ยน ≥ 2 เท่า (ขึ้นหรือลง) → warning
  size_swing_min_articles: 50 # ...เฉพาะหัวข้อที่มี ≥ 50 บทความ
  max_article_drop: 0.02      # บทความทั้งหมดลดลง > 2% → error

# ---------- atlas bakeoff: เทียบ embedding/clustering ด้วยตัวเลข ----------
bakeoff:
  sample: 5000                # จำนวนบทความตัวอย่าง
  k: 10                       # kNN สำหรับวัดความแม่น
  holdout_frac: 0.2
  seeds: [1, 2, 3]            # วัดความนิ่ง (ARI) ข้าม seed
  algorithms: [hdbscan, hdbscan_fast, leiden]   # hdbscan_fast ต้อง --extra fast, leiden ต้อง --extra leiden
  npmi_top_n: 10
  embedding_candidates: []    # เช่น - {name: bge-m3-api, provider: api, model: BAAI/bge-m3, base_url: https://…/v1}
                              #      - {name: 3-large, provider: api, model: text-embedding-3-large, dimensions: 1024}
                              #      (api ใช้ runner ของ P0 — แยก store ต่อโมเดลด้วย store_id อัตโนมัติ)
```

- [ ] **Step 5: Create `pipeline/atlas/state.py`**

```python
"""Per-release persistent state under state_dir/releases/.

work_dir is regenerable; state_dir keeps what the NEXT quarter needs:

  releases/index.json            ordered list of releases written so far
  releases/<release>/topics/     stable topic ids, article assignments, lineage (cluster step)
  releases/<release>/layout.parquet   topic positions (layout step)

A step re-run for the same release overwrites only that release's folder and always
reads the *previous* release, so re-running any step is idempotent.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

RELEASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def release_from_date(d: date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def current_release(cfg: dict) -> str:
    rel = cfg["pipeline"].get("release") or release_from_date(date.today())
    if not RELEASE_RE.match(rel):
        raise ValueError(f"invalid release name {rel!r}")
    return rel


def _index_path(cfg: dict) -> Path:
    return Path(cfg["pipeline"]["state_dir"]) / "releases" / "index.json"


def known_releases(cfg: dict) -> list[str]:
    p = _index_path(cfg)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def previous_release(cfg: dict) -> str | None:
    """The release written before the current one (None on the first run)."""
    cur, rels = current_release(cfg), known_releases(cfg)
    if cur in rels:
        i = rels.index(cur)
        return rels[i - 1] if i > 0 else None
    return rels[-1] if rels else None


def release_dir(cfg: dict, release: str | None = None, create: bool = False) -> Path:
    """state_dir/releases/<release>; create=True also registers the release in index.json."""
    rel = release or current_release(cfg)
    d = Path(cfg["pipeline"]["state_dir"]) / "releases" / rel
    if create:
        d.mkdir(parents=True, exist_ok=True)
        rels = known_releases(cfg)
        if rel not in rels:
            rels.append(rel)
            _index_path(cfg).write_text(json.dumps(rels), encoding="utf-8")
    return d
```

- [ ] **Step 6: Append the offline guard to `pipeline/tests/conftest.py`**

```python


@pytest.fixture(autouse=True, scope="session")
def _offline():
    """No test touches the network: OpenAlex calls raise OpenAlexUnavailable → taxonomy falls back.

    Session scope, so it is already active while module-scoped fixtures run the pipeline.
    """
    mp = pytest.MonkeyPatch()
    mp.setenv("ATLAS_OFFLINE", "1")
    yield
    mp.undo()
```

(Session scope matters: a function-scoped fixture is not yet active when a module-scoped fixture runs the pipeline — in the prototype that leaked real OpenAlex requests.)

- [ ] **Step 7: Run tests**

Run: `uv run ruff check . && uv run pytest -q`
Expected: ruff clean; all tests pass (P0 suite + 5 new).

- [ ] **Step 8: Commit**

```bash
git add pipeline/atlas/config.py pipeline/config.example.yaml pipeline/atlas/state.py pipeline/tests/test_state.py pipeline/tests/test_config.py pipeline/tests/conftest.py
git commit -m "feat(pipeline): P1 config sections, per-release state helpers, offline test guard

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 2: Checkpoint fingerprints, PCA sample key, fast HDBSCAN backend, table-driven PUA test

Pipeline hygiene items deferred from the P0 final review. `fast_hdbscan` 0.3.2 (pure Python + numba, sklearn-style `HDBSCAN(min_cluster_size, min_samples).fit_predict`) gave ARI 1.0 against sklearn and was ~24× faster on 20K×10 after its first-call JIT (~10 s) — sklearn is projected at 1–2 h for 500K.

**Files:**
- Create: `pipeline/atlas/checkpoints.py`, `pipeline/tests/test_checkpoints.py`
- Modify: `pipeline/atlas/cluster.py`, `pipeline/atlas/embed.py`, `pipeline/atlas/config.py`, `pipeline/config.example.yaml`, `pipeline/tests/test_embed.py`, `pipeline/tests/test_thai.py`, `pipeline/tests/test_cluster.py`, `pipeline/pyproject.toml` + `uv.lock` + `requirements.txt`

**Interfaces:**
- Consumes: P0 `embed()`, `cluster()`, `reduce_embeddings(emb, ccfg, seed)`, `hdbscan_labels(red, fine)`.
- Produces: `atlas.checkpoints.CheckpointMismatch`, `docs_fingerprint(article_ids) -> str` (16 hex), `load_aligned(work) -> (02_docs DataFrame, 03_embeddings ndarray)`; `03_meta.json` gains `docs_fingerprint`; `hdbscan_labels(red, fine, backend: str = "sklearn")` (`"fast"` uses fast_hdbscan); config `clustering.hdbscan_backend` (`sklearn|fast`), `clustering.pca_fit_sample`. Every later step that reads embeddings uses `load_aligned`.

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_checkpoints.py`:

```python
import json

import numpy as np
import pandas as pd
import pytest

from atlas.checkpoints import CheckpointMismatch, docs_fingerprint, load_aligned
from atlas.cluster import cluster
from atlas.embed import embed
from atlas.io_utils import read_table, write_table


def _docs(work, n=12):
    texts = [f"การศึกษาเรื่องที่ {i} about rice farming {i % 3}" for i in range(n)]
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(n)], "doc_text": texts}), work / "02_docs.parquet")


def test_embed_records_a_fingerprint_that_load_aligned_checks(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "lite"                       # the P0 default became "local"
    cfg["embedding"]["lite"].update(dim=4, min_df=1)
    work = tmp_path / "work"
    _docs(work)
    embed(cfg)
    meta = json.loads((work / "03_meta.json").read_text(encoding="utf-8"))
    assert meta["docs_fingerprint"] == docs_fingerprint([f"a{i}" for i in range(12)])
    df, emb = load_aligned(work)
    assert len(df) == len(emb) == 12
    write_table(read_table(work / "02_docs.parquet").iloc[::-1], work / "02_docs.parquet")   # same rows, new order
    with pytest.raises(CheckpointMismatch, match="different 02_docs"):
        load_aligned(work)


def test_row_count_mismatch_stops_the_cluster_step(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    _docs(work, n=12)
    np.save(work / "03_embeddings.npy", np.zeros((11, 4), dtype=np.float32))
    with pytest.raises(CheckpointMismatch, match="re-run the embed step"):
        cluster(cfg)
```

In `pipeline/tests/test_thai.py`:
Replace
```python
from atlas.thai import clean_text, fold_thai, has_pua, norm_key, repair_glyphs, thai_ratio, tokenize
```
with
```python
import unicodedata

import pytest

from atlas.thai import THAI_PUA, clean_text, fold_thai, has_pua, norm_key, repair_glyphs, thai_ratio, tokenize
```
and append
```python


@pytest.mark.parametrize("pua", sorted(THAI_PUA))
def test_every_pua_glyph_maps_to_its_standard_code_point(pua):
    out = repair_glyphs(chr(pua))
    assert out == unicodedata.normalize("NFC", chr(THAI_PUA[pua])) and not has_pua(out)
```

In `pipeline/tests/test_cluster.py`:
Replace
```python
import numpy as np
import pandas as pd

from atlas.cluster import assign_outliers, cluster, coarse_groups, merge_similar, relabel_by_size
```
with
```python
import numpy as np
import pandas as pd
import pytest

from atlas.cluster import (
    assign_outliers,
    cluster,
    coarse_groups,
    hdbscan_labels,
    merge_similar,
    reduce_embeddings,
    relabel_by_size,
)
from atlas.config import load_config
```
(the fix wave's all-noise tests import `pytest` locally inside a function — leave those as they are) and append
```python


def _has_fast_hdbscan() -> bool:
    import importlib.util

    return importlib.util.find_spec("fast_hdbscan") is not None


@pytest.mark.skipif(not _has_fast_hdbscan(), reason="optional extra: uv sync --extra fast")
def test_fast_hdbscan_backend_matches_sklearn():
    from sklearn.metrics import adjusted_rand_score

    X, _ = blobs(n_per=80)
    fine = {"hdbscan_min_cluster_size": 20, "hdbscan_min_samples": 5}
    assert adjusted_rand_score(hdbscan_labels(X, fine, "sklearn"), hdbscan_labels(X, fine, "fast")) > 0.95


def test_pca_fit_sample_is_configurable():
    ccfg = load_config(None)["clustering"]
    ccfg.update(pca_dims=8, pca_fit_sample=100)
    ccfg["fine"].update(umap_n_components=2)
    X, _ = blobs(n_per=60)                 # 300 × 32 > pca_dims → PCA fitted on a 100-row sample, then UMAP
    assert reduce_embeddings(X, ccfg, seed=0).shape == (300, 2)
```

In `pipeline/tests/test_embed.py` (03_meta.json gains `docs_fingerprint`; the P0 Task 19 keys stay exactly as they are):
Replace
```python
    assert meta == {"model_id": "fake|1", "store_id": "fake|1", "n": 10, "dim": 16, "n_retries": 0,
                    "n_truncated": 0}
```
with
```python
    assert len(meta.pop("docs_fingerprint")) == 16
    assert meta == {"model_id": "fake|1", "store_id": "fake|1", "n": 10, "dim": 16, "n_retries": 0,
                    "n_truncated": 0}
```

In `pipeline/tests/test_cluster.py`, the fix wave's all-noise helper monkeypatches `hdbscan_labels` with a two-argument lambda; `cluster()` now passes the backend too:
Replace
```python
    monkeypatch.setattr(C, "hdbscan_labels", lambda red, fine: np.full(len(red), -1))
```
with
```python
    monkeypatch.setattr(C, "hdbscan_labels", lambda red, fine, backend="sklearn": np.full(len(red), -1))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_checkpoints.py tests/test_thai.py tests/test_cluster.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.checkpoints'` (collection errors).

- [ ] **Step 3: Create `pipeline/atlas/checkpoints.py`**

```python
"""Checkpoint integrity — a step that reads 03_embeddings.npy must get the vectors of THIS 02_docs.

embed writes docs_fingerprint (hash of the article_id order) into 03_meta.json; load_aligned()
re-checks the row count and the fingerprint and fails with a clear message instead of silently
pairing vectors with the wrong articles (e.g. after re-running preprocess without embed).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table


class CheckpointMismatch(RuntimeError):
    """work_dir checkpoints were written by different runs — re-run the named step."""


def docs_fingerprint(article_ids) -> str:
    h = hashlib.sha256()
    for a in article_ids:
        h.update(str(a).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:16]


def load_aligned(work: str | Path) -> tuple[pd.DataFrame, np.ndarray]:
    """(02_docs, 03_embeddings) after checking that they belong together."""
    work = Path(work)
    df = read_table(work / "02_docs.parquet")
    emb = np.load(work / "03_embeddings.npy")
    if len(emb) != len(df):
        raise CheckpointMismatch(f"03_embeddings.npy has {len(emb):,} rows but 02_docs has {len(df):,} "
                                 "— re-run the embed step")
    meta = work / "03_meta.json"
    if meta.exists():
        fp = json.loads(meta.read_text(encoding="utf-8")).get("docs_fingerprint")
        if fp and fp != docs_fingerprint(df["article_id"]):
            raise CheckpointMismatch("03_embeddings.npy was built for a different 02_docs — re-run the embed step")
    return df, emb
```

- [ ] **Step 4: Edit `pipeline/atlas/embed.py`** — P0 Task 19 routes the `api` and `local` providers through `atlas.embed_runner.run_embedding` and merges `store_id`, `n_retries`, `n_truncated` into `03_meta.json` via `**meta`; the fix wave added the `lite_max_docs` warning. Keep all of that — you only add `docs_fingerprint`.

Replace
```python
from atlas.embed_api import ApiEmbedder, api_store_id
```
with
```python
from atlas.checkpoints import docs_fingerprint
from atlas.embed_api import ApiEmbedder, api_store_id
```
Replace
```python
    texts = read_table(work / "02_docs.parquet")["doc_text"].tolist()
```
with
```python
    docs = read_table(work / "02_docs.parquet")
    texts = docs["doc_text"].tolist()
```
Replace
```python
    (work / "03_meta.json").write_text(json.dumps({"model_id": model_id, "n": int(arr.shape[0]),
                                                   "dim": int(arr.shape[1]), **meta}), encoding="utf-8")
```
with
```python
    (work / "03_meta.json").write_text(json.dumps({"model_id": model_id, "n": int(arr.shape[0]),
                                                   "dim": int(arr.shape[1]), **meta,
                                                   "docs_fingerprint": docs_fingerprint(docs["article_id"])}),
                                       encoding="utf-8")
```

- [ ] **Step 5: Edit `pipeline/atlas/cluster.py`**

5a. Imports:
Replace
```python
from atlas.ctfidf import topic_keywords, topic_terms
from atlas.io_utils import read_table, write_table
```
with
```python
from atlas.checkpoints import load_aligned
from atlas.ctfidf import topic_keywords, topic_terms
from atlas.io_utils import write_table
```
5b. PCA sample size from config:
Replace
```python
fit(emb[_sample(n, 100_000, seed)])
```
with
```python
fit(emb[_sample(n, int(ccfg["pca_fit_sample"]), seed)])
```
5c. Optional fast backend — replace the head of `hdbscan_labels` (its sklearn body stays; the backend switch goes before the sklearn import):
Replace
```python
def hdbscan_labels(red: np.ndarray, fine: dict) -> np.ndarray:
```
with
```python
def hdbscan_labels(red: np.ndarray, fine: dict, backend: str = "sklearn") -> np.ndarray:
    if backend == "fast":
        import fast_hdbscan  # optional extra: uv sync --extra fast

        n = len(red)
        mcs = max(2, min(int(fine["hdbscan_min_cluster_size"]), max(2, n // 2)))
        ms = max(1, min(int(fine["hdbscan_min_samples"]), mcs))
        return np.asarray(fast_hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=ms).fit_predict(red), dtype=int)
```
5d. Aligned checkpoints and the backend in `cluster()` (the fix wave's all-noise `ValueError` a few lines below stays as it is):
Replace
```python
    df = read_table(work / "02_docs.parquet")
    emb = np.load(work / "03_embeddings.npy")
```
with
```python
    df, emb = load_aligned(work)
```
Replace
```python
    raw = hdbscan_labels(reduce_embeddings(emb, ccfg, seed), ccfg["fine"])
```
with
```python
    raw = hdbscan_labels(reduce_embeddings(emb, ccfg, seed), ccfg["fine"], ccfg["hdbscan_backend"])
```
>>>END


- [ ] **Step 6: Config keys**

After
```python
    algorithm: Literal["hdbscan", "leiden"] = "hdbscan"
```
insert
```python
    hdbscan_backend: Literal["sklearn", "fast"] = "sklearn"
```
After
```python
    pca_dims: int = 128
```
insert
```python
    pca_fit_sample: int = Field(100_000, ge=100)
```
After
```yaml
  algorithm: hdbscan          # hdbscan (UMAP→HDBSCAN) | leiden (Leiden บน kNN graph — ต้อง uv sync --extra leiden)
```
insert
```yaml
  hdbscan_backend: sklearn    # sklearn | fast (fast_hdbscan เร็วกว่ามากที่ 500K — ต้อง uv sync --extra fast)
```
After
```yaml
  pca_dims: 128               # ลดมิติด้วย PCA ก่อน UMAP เมื่อ embedding ใหญ่กว่านี้
```
insert
```yaml
  pca_fit_sample: 100000      # จำนวนบทความตัวอย่างที่ใช้ fit PCA
```

- [ ] **Step 7: Optional dependency**

Run (from `pipeline/`): `uv add --optional fast "fast_hdbscan>=0.3"`, then `uv sync --extra fast` and `uv export --no-hashes --no-dev --format requirements-txt > requirements.txt`.
Expected: `pyproject.toml` gains `fast = ["fast_hdbscan>=0.3"]` under `[project.optional-dependencies]`; `uv.lock` updated.

- [ ] **Step 8: Run tests**

Run: `uv run ruff check . && uv run pytest -q`
Expected: all pass (27 parametrized PUA cases, 2 checkpoint tests, 2 cluster tests; the fast-backend test is skipped when the extra is not installed).

- [ ] **Step 9: Commit**

```bash
git add pipeline/atlas/checkpoints.py pipeline/atlas/cluster.py pipeline/atlas/embed.py pipeline/atlas/config.py pipeline/config.example.yaml pipeline/tests pipeline/pyproject.toml pipeline/uv.lock pipeline/requirements.txt
git commit -m "feat(pipeline): checkpoint fingerprints, configurable PCA sample, optional fast HDBSCAN backend

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 3: LLM core — OpenAI-compatible adapter on `api_http`, prompts from `prompts/*.md`, LLM runner on the P0 job plumbing (cache · journal · lock · budget · stop · status), `atlas llm`

All LLM work in P1 is topic-level (labels, merge checks, narratives, executive brief — no article-level calls) and goes through one adapter and one runner. The adapter speaks `POST {base_url}/chat/completions` only (OpenRouter, Typhoon, DeepInfra, vLLM/LiteLLM gateways, OpenAI/Gemini/Claude behind a gateway); there is no vendor SDK. It is built on P0 Task 19's HTTP core exactly as `embed_api` is (`post_json` + `call_with_retry` + `RetryPolicy` + `explain_permanent`), so the LLM retries server failures like the embedding runner and stops at once on a wrong key/model/URL/quota. The runner reuses P0's job plumbing (`jobs.RunLock` OS lock, `StopFlag`, `ProgressFile`, `RunStopped`, `spawn_background`) and `atlas status` lists the LLM job next to the embedding stores — no second lock or status implementation. Its cache is also its journal: one JSON line is appended per finished call, so closing the window loses only the calls in flight and re-runs never pay twice.

**Files:**
- Create: `pipeline/atlas/prompts.py`, `pipeline/atlas/llm.py`, `pipeline/atlas/llm_runner.py`, `pipeline/tests/test_llm.py`
- Modify: `pipeline/atlas/config.py`, `pipeline/config.example.yaml`, `pipeline/atlas/cli.py` (`_run_guarded` gains `tag`/`resume`, `run` passes them, `render_status` adds the LLM lines, new `llm` / `llm-stop`), `pipeline/atlas/jobs.py` (one line of `format_job_status`)

**Interfaces:**
- Consumes (P0 Task 19, merged at `0426434`):
  - `atlas.api_http`: `ApiConfigError`, `HttpPermanentError(status, body, headers)` (`.status/.body/.location`), `MalformedResponse(message, kind=…)` (a `TransientError`), `TooLargeError`, `TransientGaveUp`, `Cancelled`, `Transport` = `(url, headers, body: bytes, timeout) -> (status, headers, body)`, `EventHandler`, `urllib_transport`, `validate_base_url(url)`, `post_json(transport, url, payload, *, headers, timeout)`, `RetryPolicy(initial, cap, max_retries=None, sleep=None, rand=random.random)` (`.cancel()`), `call_with_retry(send, policy, on_event)` (emits `("retry", {attempt, delay, status, error})`), `explain_permanent(status, body, *, key_env, base_url, model, location)`.
  - `atlas.jobs`: `LOCK`, `PROGRESS`, `STOP`, `LOG`, `RunLock(path, *, stale_seconds, heartbeat)` (`.acquire()` → `LockHeld`, `.release()`, context manager), `StopFlag(path)` (`.request() / .is_set() / .clear() / .clear_if_older(epoch)`), `ProgressFile(path, min_interval)` (`.write(data, force)`), `RunStopped(message, abandoned=0)`, `now_iso()`, `process_started_epoch()`, `os_lock_held(dir)`, `spawn_background(args, log, cwd)`; `find_jobs` / `job_status` / `format_job_status(info, extra)` through `cli.render_status`.
  - `atlas.cli`: `EXIT_CONFIG`, `EXIT_LOCKED`, `_run_guarded`, `_cfg_arg`, `_tail`, `render_status`.
- Produces:
  - `atlas.prompts`: `DEFAULT_PROMPTS_DIR`, `load_prompt(name, prompts_dir=None) -> str` (the fenced block under `## Prompt (master)`; CRLF-safe), `prompt_version(template) -> str` (12 hex; hashes the template only, so editing a prompt file's notes never re-pays), `placeholders(template) -> set[str]`, `render_prompt(template, **values) -> str` (`KeyError` for a missing value; one pass, values never re-scanned).
  - `atlas.llm`: `LlmConfigError(api_http.ApiConfigError)`, `extract_json(text) -> dict`, `Reply(text, prompt_tokens, completion_tokens, seconds)`, `OpenAICompatLLM(base_url, model, temperature, max_output_tokens, *, api_key, api_key_env, json_mode, timeout, policy, transport, on_event)` with `.model_id`, `.chat(messages) -> Reply`, `.cancel()`, `OpenAICompatLLM.for_task(cfg, task, transport=None, sleep=None, max_retries=-1)`. A transient give-up surfaces as `api_http.TransientGaveUp` (no LLM-specific transient class).
  - `atlas.llm_runner`: `JOBS: dict[str, str]` (task → `"module:function"`, filled by Tasks 6, 7, 14), `LlmItem(key, prompt, fallback, check=None)`, `LlmJob(task, schema, prompt_version, items)`, `LlmResult(output, source ∈ {llm, cache, fallback}, repaired, key)`, `LlmRunner(cfg, job, llm=None)` (`.run()`, `.dry_run()`, `.key_for(prompt)`), `run_job(cfg, job, llm=None) -> (results by item key, stats)` — stats = `{task, model, items, from_cache, generated, repaired, fallback, cost_usd}`; raises `LlmConfigError`, `jobs.LockHeld`, `jobs.RunStopped` (stop.flag / Ctrl-C / budget). Helpers `llm_dir(cfg)`, `build_job`, `dry_run_all(cfg, tasks=None)`, `request_stop(cfg) -> Path`, `status_extra(info) -> list[str]`, `check_endpoints(cfg, transport=None, sleep=None)`.
  - State: `state_dir/llm_cache/<task>.jsonl` (cache + journal; a line = `{key, item, task, model, prompt_version, release, output|null, cost_usd, repaired, at}`; `output: null` lines only record spend), and the P0 job files in the same folder: `.lock`, `run.lock`, `progress.json` (`kind: "llm"`, `job_id: "llm:<task>"`, `unit: "items"`, `total/cached/this_run/remaining`, `generated/repaired/fallback`, `retries`, `cost_usd`, `release_spend_usd`, `budget_usd`, `stop_reason`), `stop.flag`, `run.log`.
  - Config `llm.{prompts_dir, budget_usd, max_repairs, max_regenerations, lock_stale_seconds, endpoints.<name>.{base_url, api_key_env (ATLAS_LLM_API_KEY), json_mode, concurrency, request_timeout, max_retries, backoff_initial, backoff_max, price_per_mtok_in, price_per_mtok_out}, tasks.{label, merge, narrative, brief}.{endpoint, model, temperature, max_output_tokens}}`.
  - CLI: `atlas llm -c CFG [--check] [--dry-run] [--task T]… [--background]` (exit codes as `atlas embed`: 0 ok · 2 config/endpoint error · 3 another LLM job holds the lock · 130 stopped by `llm-stop` / Ctrl-C / budget — the same command continues), `atlas llm-stop -c CFG`; `atlas status` shows the LLM job (`[llm] llm:<task>` + task/model, new/repaired/fallback, cost). `atlas run` messages are tagged `[run]` and name `atlas run` as the resume command (P0 printed `[embed]` / `atlas embed` for every stop).

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_llm.py` (fake `api_http` transport, injected sleep — no network):

````python
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError, field_validator

from atlas.config import load_config
from atlas.jobs import LOCK, LockHeld, RunLock, RunStopped
from atlas.llm import LlmConfigError, OpenAICompatLLM, extract_json
from atlas.llm_runner import LlmItem, LlmJob, LlmRunner, check_endpoints, llm_dir, request_stop, run_job
from atlas.prompts import load_prompt, placeholders, prompt_version, render_prompt

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- prompts
def test_every_master_prompt_loads_and_label_placeholders_are_known():
    for p in sorted((REPO / "prompts").glob("*.md")):
        assert load_prompt(p.stem, REPO / "prompts")
    assert placeholders(load_prompt("topic_label.th", REPO / "prompts")) == {"keywords", "terms", "titles"}


def test_render_inserts_values_verbatim_and_requires_every_placeholder():
    t = load_prompt("topic_label.th")
    out = render_prompt(t, keywords="ข้าว; rice", terms="ชาวนา {x}", titles="- การปลูกข้าว")
    assert "ชาวนา {x}" in out and "{keywords}" not in out
    with pytest.raises(KeyError, match="titles"):
        render_prompt(t, keywords="a", terms="b")


def test_crlf_prompt_file_loads_identically_and_version_hashes_the_template_only(tmp_path):
    text = (REPO / "prompts" / "topic_label.th.md").read_text(encoding="utf-8")
    (tmp_path / "topic_label.th.md").write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    t = load_prompt("topic_label.th", tmp_path)
    assert t == load_prompt("topic_label.th", REPO / "prompts")
    (tmp_path / "topic_label.th.md").write_text("# new notes\n\n" + text, encoding="utf-8")
    assert prompt_version(load_prompt("topic_label.th", tmp_path)) == prompt_version(t)
    assert len(prompt_version(t)) == 12 and prompt_version(t + " ") != prompt_version(t)


def test_extract_json_tolerates_fences_and_rejects_garbage():
    assert extract_json('Sure:\n```json\n{"a": 1}\n```') == {"a": 1}
    for bad in ("no json here", "[1, 2]"):
        with pytest.raises(ValueError):
            extract_json(bad)


# ---------------------------------------------------------------- adapter (fake api_http transport, no network)
def ok(text: str, usage=(100, 20)):
    body = {"choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1]}}
    return 200, {}, json.dumps(body, ensure_ascii=False).encode("utf-8")


class FakeServer:
    """api_http Transport: (url, headers, body, timeout) → (status, headers, body); scripted replies."""

    def __init__(self, *replies, default=None):
        self.replies, self.default, self.requests = list(replies), default, []

    def __call__(self, url, headers, body, timeout):
        self.requests.append({"url": url, "headers": headers, "payload": json.loads(body)})
        r = self.replies.pop(0) if self.replies else self.default
        if isinstance(r, Exception):
            raise r
        return r(self.requests[-1]["payload"]) if callable(r) else r


def _cfg(make_cfg, tmp_path, **endpoint):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q4"
    cfg["llm"]["endpoints"]["default"].update(base_url="https://llm.example/v1", concurrency=1, **endpoint)
    for t in cfg["llm"]["tasks"].values():
        t["model"] = "test-model"
    return cfg


def _llm(cfg, server, task="label", sleeps=None):
    return OpenAICompatLLM.for_task(cfg, task, transport=server,
                                    sleep=(sleeps.append if sleeps is not None else lambda s: None))


def test_adapter_sends_an_openai_compatible_request(make_cfg, tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_LLM_API_KEY", "sk-test")
    cfg = _cfg(make_cfg, tmp_path)
    server = FakeServer(ok('{"name": "ข้าว"}'), ok('{"name": "ข้าว"}'))
    reply = _llm(cfg, server).chat([{"role": "user", "content": "ตั้งชื่อ"}])
    req = server.requests[0]
    assert req["url"] == "https://llm.example/v1/chat/completions"
    assert req["headers"]["Authorization"] == "Bearer sk-test"
    p = req["payload"]
    assert (p["model"], p["messages"][0]["content"], p["max_tokens"]) == ("test-model", "ตั้งชื่อ", 600)
    assert p["response_format"] == {"type": "json_object"} and reply.prompt_tokens == 100
    cfg["llm"]["endpoints"]["default"]["json_mode"] = False
    _llm(cfg, server).chat([{"role": "user", "content": "x"}])
    assert "response_format" not in server.requests[1]["payload"]


def test_transient_errors_retry_with_retry_after(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    sleeps = []
    server = FakeServer((503, {}, b"busy"), (429, {"Retry-After": "7"}, b"slow down"), ConnectionResetError("reset"),
                        (200, {}, b'{"error": {"message": "upstream timeout"}}'), ok('{"name": "ok"}'))
    assert _llm(cfg, server, sleeps=sleeps).chat([{"role": "user", "content": "x"}]).text == '{"name": "ok"}'
    assert len(server.requests) == 5 and 7.0 in sleeps


def test_permanent_error_raises_at_once_and_names_the_key_variable(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    server = FakeServer((401, {}, b'{"error": "invalid api key"}'))
    with pytest.raises(LlmConfigError, match="ATLAS_LLM_API_KEY"):
        _llm(cfg, server).chat([{"role": "user", "content": "x"}])
    assert len(server.requests) == 1


# ---------------------------------------------------------------- runner
class Out(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("blank name")
        return v.strip()


def _job(keys, check=None):
    return LlmJob("label", Out, "v1", [LlmItem(k, f"name item {k}", {"name": f"fallback {k}"}, check) for k in keys])


def _by_item(script: dict):
    """Reply chosen by the item named in the first message; the turn number is len(messages)."""
    def reply(payload):
        item = payload["messages"][0]["content"].split("item ")[1].split()[0]
        texts = script[item]
        turn = len(payload["messages"]) // 2
        return ok(texts[min(turn, len(texts) - 1)])
    return reply


def test_runner_caches_repairs_and_falls_back(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    script = {"a": ['{"name": "A"}'], "b": ["not json", '{"name": "B"}'], "c": ['{"name": " "}']}
    server = FakeServer(default=_by_item(script))
    res, stats = run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, server))
    assert {k: (r.output["name"], r.source) for k, r in res.items()} == {
        "a": ("A", "llm"), "b": ("B", "llm"), "c": ("fallback c", "fallback")}
    assert (stats["generated"], stats["repaired"], stats["fallback"]) == (2, 1, 1)
    assert len(server.requests) == 1 + 2 + 3                 # c: first try + max_repairs (2)
    repair_turn = server.requests[2]["payload"]["messages"]
    assert [m["role"] for m in repair_turn] == ["user", "assistant", "user"] and "JSON" in repair_turn[2]["content"]
    again = FakeServer(default=_by_item({**script, "c": ['{"name": "C"}']}))
    res, stats = run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, again))
    assert len(again.requests) == 1 and stats["from_cache"] == 2 and res["c"].output == {"name": "C"}
    lines = (llm_dir(cfg) / "label.jsonl").read_text(encoding="utf-8").splitlines()
    assert sum(json.loads(x)["output"] is not None for x in lines) == 3


def test_failed_content_check_regenerates_once_then_falls_back(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    seen = {"good": 0}

    def reply(payload):
        item = payload["messages"][0]["content"].split("item ")[1].split()[0]
        if item == "good":
            seen["good"] += 1
            return ok('{"name": "invented 99"}' if seen["good"] == 1 else '{"name": "grounded"}')
        return ok('{"name": "invented 99"}')

    def check(out):
        return "number 99 is not in the facts" if "99" in out["name"] else None

    server = FakeServer(default=reply)
    res, stats = run_job(cfg, _job(["good", "bad"], check), llm=_llm(cfg, server))
    assert res["good"].output == {"name": "grounded"} and res["bad"].source == "fallback"
    regen = [r for r in server.requests if "rejected" in r["payload"]["messages"][0]["content"]]
    assert len(regen) == 2 and len(server.requests) == 4


def test_transient_give_up_falls_back_and_is_not_cached(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path, max_retries=1)
    res, stats = run_job(cfg, _job(["a"]), llm=_llm(cfg, FakeServer(default=(502, {}, b"bad gateway"))))
    assert res["a"].source == "fallback" and stats["fallback"] == 1
    res, _ = run_job(cfg, _job(["a"]), llm=_llm(cfg, FakeServer(default=ok('{"name": "A"}'))))
    assert res["a"].output == {"name": "A"}                   # asked again, not served from the cache


def test_budget_stops_cleanly_and_a_rerun_continues(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path, price_per_mtok_in=1.0, price_per_mtok_out=1.0)
    cfg["llm"]["budget_usd"] = 0.0012                         # one call costs 120 tokens ≈ 0.00012 USD
    keys = [f"k{i}" for i in range(12)]
    server = FakeServer(default=lambda p: ok('{"name": "n"}'))
    with pytest.raises(RunStopped, match="budget"):
        run_job(cfg, _job(keys), llm=_llm(cfg, server))
    done = len(server.requests)
    prog = json.loads((llm_dir(cfg) / "progress.json").read_text(encoding="utf-8"))
    assert 0 < done < 12 and (prog["status"], prog["stop_reason"], prog["kind"]) == ("stopped", "budget", "llm")
    cfg["llm"]["budget_usd"] = None
    more = FakeServer(default=lambda p: ok('{"name": "n"}'))
    res, stats = run_job(cfg, _job(keys), llm=_llm(cfg, more))
    assert stats["from_cache"] == done and len(more.requests) == 12 - done and len(res) == 12


def test_stop_flag_ends_the_job_after_the_calls_in_flight(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)

    def reply(payload):
        request_stop(cfg)                                     # operator runs `atlas llm-stop` meanwhile
        return ok('{"name": "n"}')

    server = FakeServer(default=reply)
    with pytest.raises(RunStopped, match="stop.flag"):
        run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, server))
    assert len(server.requests) == 1 and not (llm_dir(cfg) / "stop.flag").exists()
    res, stats = run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, FakeServer(default=ok('{"name": "n"}'))))
    assert stats["from_cache"] == 1 and stats["generated"] == 2


def test_permanent_error_stops_the_job_and_keeps_finished_items(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    server = FakeServer(ok('{"name": "A"}'), (404, {}, b"model not found"))
    with pytest.raises(LlmConfigError, match="404"):
        run_job(cfg, _job(["a", "b", "c"]), llm=_llm(cfg, server))
    prog = json.loads((llm_dir(cfg) / "progress.json").read_text(encoding="utf-8"))
    assert prog["status"] == "failed" and "404" in prog["last_error"] and len(server.requests) == 2
    res, stats = run_job(cfg, _job(["a"]), llm=_llm(cfg, FakeServer()))
    assert res["a"].source == "cache"


def test_second_job_is_refused_while_the_lock_is_held(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    with RunLock(llm_dir(cfg) / LOCK):                        # another LLM job holds the OS lock
        with pytest.raises(LockHeld):
            run_job(cfg, _job(["a"]), llm=_llm(cfg, FakeServer(default=ok('{"name": "n"}'))))


def test_cached_items_need_no_endpoint_and_status_and_dry_run_report(make_cfg, tmp_path):
    from atlas.cli import render_status

    cfg = _cfg(make_cfg, tmp_path, price_per_mtok_in=0.5, price_per_mtok_out=2.0)
    run_job(cfg, _job(["a", "b"]), llm=_llm(cfg, FakeServer(default=ok('{"name": "n"}'))))
    cfg["llm"]["endpoints"]["default"]["base_url"] = ""               # nothing left to pay for → no client needed
    res, stats = run_job(cfg, _job(["a", "b"]))
    assert stats["from_cache"] == 2 and {r.source for r in res.values()} == {"cache"}
    text = render_status(cfg)                                          # the P0 `atlas status` lists the LLM job
    assert "llm:label" in text and "done" in text and "2 / 2 items" in text and "test-model" in text
    dry = LlmRunner(cfg, _job(["a", "b", "c"])).dry_run()
    assert (dry["cached"], dry["to_call"]) == (2, 1) and dry["est_cost_usd"] > 0


def test_check_endpoints_reports_json_and_thai_round_trip(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path)
    cfg["llm"]["tasks"]["brief"]["model"] = "other-model"
    server = FakeServer(ok('{"ok": true, "word": "ภาษาไทย"}'), (401, {}, b"bad key"))
    rows = check_endpoints(cfg, transport=server, sleep=lambda s: None)
    assert [(r["model"], r["json_ok"], r["thai_ok"]) for r in rows] == [("test-model", True, True),
                                                                        ("other-model", False, False)]
    assert rows[0]["tasks"] == "label, merge, narrative" and "LlmConfigError" in rows[1]["error"]


def test_llm_config_defaults_and_errors(make_cfg, tmp_path):
    cfg = load_config(None)
    assert cfg["llm"]["endpoints"]["default"]["api_key_env"] == "ATLAS_LLM_API_KEY"
    assert set(cfg["llm"]["tasks"]) == {"label", "merge", "narrative", "brief"}
    with pytest.raises(LlmConfigError, match="llm.tasks.label.model"):
        OpenAICompatLLM.for_task(make_cfg(tmp_path), "label")
    priced = _cfg(make_cfg, tmp_path)
    priced["llm"]["budget_usd"] = 5.0
    with pytest.raises(LlmConfigError, match="price_per_mtok"):
        LlmRunner(priced, _job(["a"]))
    p = tmp_path / "c.yaml"
    p.write_text("llm:\n  tasks:\n    label:\n      endpoint: nowhere\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="nowhere"):
        load_config(p)
````

Append the CLI checks to the same file:

```python


def test_cli_check_without_models_exits_2():
    from typer.testing import CliRunner

    from atlas.cli import app

    r = CliRunner().invoke(app, ["llm", "--check"])
    assert r.exit_code == 2 and "nothing to check" in r.output


def test_cli_llm_stop_writes_the_flag(tmp_path):
    from typer.testing import CliRunner

    from atlas.cli import app

    p = tmp_path / "c.yaml"
    p.write_text(f"pipeline:\n  state_dir: {(tmp_path / 'state').as_posix()}\n", encoding="utf-8")
    r = CliRunner().invoke(app, ["llm-stop", "-c", str(p)])
    assert r.exit_code == 0 and (tmp_path / "state" / "llm_cache" / "stop.flag").exists()


def test_cli_llm_background_reports_a_child_that_fails_at_once(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from atlas.cli import app

    monkeypatch.setenv("ATLAS_BACKGROUND_CHECK_S", "60")
    p = tmp_path / "c.yaml"
    p.write_text(f"pipeline:\n  state_dir: {(tmp_path / 'state').as_posix()}\n"
                 f"  work_dir: {(tmp_path / 'work').as_posix()}\n", encoding="utf-8")
    r = CliRunner().invoke(app, ["llm", "-c", str(p), "--background"])
    assert r.exit_code == 1 and "04_topic_info" in r.output           # the tail of run.log is shown
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_llm.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.llm'`.

- [ ] **Step 3: Create `pipeline/atlas/prompts.py`**

````python
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
````

- [ ] **Step 4: Create `pipeline/atlas/llm.py`**

````python
"""LLM access — one OpenAI-compatible adapter: POST {base_url}/chat/completions.

Works with OpenRouter, Typhoon, DeepInfra, Together, an organisation's vLLM / LiteLLM gateway, and
OpenAI / Gemini / Claude models behind such a gateway. HTTP, error classification, backoff and the retry
loop are the P0 core in atlas.api_http (shared with atlas.embed_api), so the LLM behaves like the embedding
runner: transient failures (408/409/425/429/5xx, network, a 2xx without `choices`) retry with capped
full-jitter backoff and Retry-After — without limit unless max_retries is set, then api_http.TransientGaveUp —
while permanent ones (3xx, 401/402/403/404, other 4xx, 429 out of quota) and "prompt too large" raise
LlmConfigError at once with the fix in the message. `response_format: {"type": "json_object"}` is sent only
when the endpoint says json_mode: true; replies are always parsed by extract_json and validated by the
caller's pydantic schema (atlas.llm_runner).

config:  llm.endpoints.<name> = {base_url, api_key_env, json_mode, concurrency, request_timeout,
                                 max_retries, backoff_initial, backoff_max, price_per_mtok_in/out}
         llm.tasks.<task>     = {endpoint, model, temperature, max_output_tokens}
"""
from __future__ import annotations

import json
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from atlas.api_http import (
    ApiConfigError,
    EventHandler,
    HttpPermanentError,
    MalformedResponse,
    RetryPolicy,
    TooLargeError,
    Transport,
    call_with_retry,
    explain_permanent,
    post_json,
    urllib_transport,
    validate_base_url,
)

MALFORMED_REPEAT = 3        # the same malformed 2xx answer this often in a row = not transient (cf. embed_api)


class LlmConfigError(ApiConfigError):
    """Wrong endpoint / key / model / quota, or a prompt the model cannot take — retrying will not help."""


class _PersistentMalformed(Exception):
    """The server gave the same malformed 2xx answer MALFORMED_REPEAT times in a row."""


def extract_json(text: str) -> dict:
    """Parse the JSON object in a reply that may carry prose or ```json fences around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("reply JSON is not an object")
    return data


@dataclass
class Reply:
    text: str
    prompt_tokens: int          # 0 when the server reports no usage
    completion_tokens: int
    seconds: float


class OpenAICompatLLM:
    """`.chat(messages) -> Reply`. `on_event(kind, info)` (kind "retry") may be set later — the runner
    subscribes to it; `cancel()` makes a worker in a backoff wait raise api_http.Cancelled."""

    def __init__(self, base_url: str, model: str, temperature: float, max_output_tokens: int, *,
                 api_key: str = "", api_key_env: str = "", json_mode: bool = False, timeout: float = 120.0,
                 policy: RetryPolicy | None = None, transport: Transport | None = None,
                 on_event: EventHandler | None = None):
        self.base_url = str(base_url).rstrip("/")
        self.url = self.base_url + "/chat/completions"
        try:
            validate_base_url(self.url)
        except ApiConfigError as e:
            raise LlmConfigError(str(e)) from None
        self.model, self.temperature, self.max_output_tokens = model, temperature, max_output_tokens
        self.model_id = model                    # part of every LLM cache key
        self.json_mode, self.timeout, self.api_key_env = json_mode, timeout, api_key_env
        self.__headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.policy = policy or RetryPolicy(2.0, 300.0, None)
        self.transport = transport or urllib_transport
        self.on_event = on_event

    @classmethod
    def for_task(cls, cfg: dict, task: str, transport: Transport | None = None,
                 sleep: Callable[[float], Any] | None = None, max_retries: int | None = -1) -> OpenAICompatLLM:
        """The client of llm.tasks.<task>. max_retries=-1 → the endpoint's setting (a check passes a small one)."""
        tcfg = cfg["llm"]["tasks"][task]
        ecfg = cfg["llm"]["endpoints"][tcfg["endpoint"]]
        if not ecfg["base_url"] or not tcfg["model"]:
            raise LlmConfigError(f"set llm.endpoints.{tcfg['endpoint']}.base_url and llm.tasks.{task}.model "
                                 f"(or switch the step that needs the LLM off)")
        retries = ecfg["max_retries"] if max_retries == -1 else max_retries
        policy = RetryPolicy(float(ecfg["backoff_initial"]), float(ecfg["backoff_max"]), retries, sleep=sleep,
                             rand=random.random)
        return cls(ecfg["base_url"], tcfg["model"], float(tcfg["temperature"]), int(tcfg["max_output_tokens"]),
                   api_key=os.environ.get(ecfg["api_key_env"], "").strip(), api_key_env=ecfg["api_key_env"],
                   json_mode=bool(ecfg["json_mode"]), timeout=float(ecfg["request_timeout"]), policy=policy,
                   transport=transport)

    def cancel(self) -> None:
        self.policy.cancel()

    def _emit(self, kind: str, info: dict) -> None:
        if self.on_event:
            self.on_event(kind, info)

    def chat(self, messages: list[dict]) -> Reply:
        payload: dict = {"model": self.model, "messages": messages, "temperature": self.temperature,
                         "max_tokens": self.max_output_tokens}
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        seen = {"kind": None, "n": 0}

        def attempt() -> dict:
            try:
                data = post_json(self.transport, self.url, payload, headers=self.__headers, timeout=self.timeout)
                if not (isinstance(data, dict) and data.get("choices")):    # gateways wrap upstream errors in a 200
                    raise MalformedResponse(f"response without choices: {json.dumps(data)[:200]}", kind="no-choices")
                return data
            except MalformedResponse as e:
                seen["n"] = seen["n"] + 1 if e.kind == seen["kind"] else 1
                seen["kind"] = e.kind
                if seen["n"] >= MALFORMED_REPEAT:
                    raise _PersistentMalformed(str(e)) from None
                raise

        t0 = time.monotonic()
        try:
            data = call_with_retry(attempt, self.policy, self._emit)
        except HttpPermanentError as e:
            raise LlmConfigError(explain_permanent(e.status, e.body, key_env=self.api_key_env or "the API key env var",
                                                   base_url=self.base_url, model=self.model,
                                                   location=e.location)) from None
        except TooLargeError as e:
            raise LlmConfigError(f"{self.url} → {e} — the prompt is too long for {self.model}; use a model with a "
                                 "larger context or fewer representative titles") from None
        except _PersistentMalformed as e:
            raise LlmConfigError(f"{self.url} answered {MALFORMED_REPEAT} times without a usable reply ({e}) — "
                                 f"check base_url ({self.base_url}) and model ({self.model})") from None
        except LlmConfigError:
            raise
        except ApiConfigError as e:                               # TLS / bad URL found while sending
            raise LlmConfigError(str(e)) from None
        message = (data["choices"][0] or {}).get("message") or {}
        text = message.get("content") or ""                       # empty → the caller's JSON check asks for a repair
        usage = data.get("usage") or {}
        return Reply(text, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0),
                     time.monotonic() - t0)
````

- [ ] **Step 5: Create `pipeline/atlas/llm_runner.py`**

```python
"""LLM job runner — every topic-level LLM call (labels, merge checks, narratives, brief) goes through here.

  cache = journal  state_dir/llm_cache/<task>.jsonl — one JSON line appended and flushed per finished call,
                   keyed by sha256(model + prompt version + rendered prompt). Re-runs and the next quarter never
                   pay twice; a killed process loses only the calls in flight.
  structure        reply → extract_json → the job's pydantic schema; invalid → up to llm.max_repairs repair
                   turns; a failed content check (e.g. narrative grounding) → up to llm.max_regenerations fresh
                   calls; still failing → the item's fallback (never cached). Transient errors outlasting an
                   endpoint's max_retries (only when it is set) → the fallback too; the next run asks again.
  stopping         permanent endpoint errors (key / model / URL / quota) raise LlmConfigError at once (CLI exit
                   2). `atlas llm-stop` (stop.flag), Ctrl-C and llm.budget_usd (per release, all tasks) end the job
                   after the calls in flight and raise jobs.RunStopped: the step writes nothing, the CLI exits
                   130, and the same command continues (finished calls come from the cache, free).
  P0 plumbing      atlas.jobs exactly as the embedding runner uses it: one LLM job at a time (RunLock = OS lock
                   on state_dir/llm_cache/.lock), StopFlag, and a ProgressFile heartbeat (progress.json, kind
                   "llm") that `atlas status` lists next to the embedding stores.

Jobs register in JOBS ("task" → "module:function" returning an LlmJob for the current work_dir) so
`atlas llm --dry-run` can estimate every task without running it.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, CancelledError, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from atlas.api_http import Cancelled, TransientGaveUp
from atlas.jobs import (
    LOCK,
    PROGRESS,
    STOP,
    ProgressFile,
    RunLock,
    RunStopped,
    StopFlag,
    now_iso,
    process_started_epoch,
)
from atlas.llm import LlmConfigError, OpenAICompatLLM, extract_json
from atlas.state import current_release

JOBS: dict[str, str] = {}
PROGRESS_EVERY_S = 5.0

REPAIR = ("The reply above does not match the required JSON format ({error}). "
          "Reply again with ONLY the corrected JSON object, nothing else.")
REGENERATE = ("Your previous answer was rejected: {error}. Use only the facts, numbers and names given above; "
              "do not add any other number or topic name.")


@dataclass
class LlmItem:
    key: str                                              # e.g. "T000123" — names the item in logs and results
    prompt: str
    fallback: dict
    check: Callable[[dict], str | None] | None = None    # extra content check → error text or None


@dataclass
class LlmJob:
    task: str                                             # a key of llm.tasks
    schema: type[BaseModel]
    prompt_version: str
    items: list[LlmItem]


@dataclass
class LlmResult:
    output: dict
    source: str                                           # llm | cache | fallback
    repaired: int = 0
    key: str = ""                                         # cache key (empty for a fallback)


def llm_dir(cfg: dict) -> Path:
    return Path(cfg["pipeline"]["state_dir"]) / "llm_cache"


def _read_jsonl(path: Path) -> list[dict]:
    out = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue                                  # a line cut by a crash is skipped
    return out


class LlmRunner:
    def __init__(self, cfg: dict, job: LlmJob, llm=None):
        lc = cfg["llm"]
        self.cfg, self.job, self.llm = cfg, job, llm
        self.tcfg = lc["tasks"][job.task]
        self.ecfg = lc["endpoints"][self.tcfg["endpoint"]]
        self.model_id = llm.model_id if llm is not None else self.tcfg["model"]
        self.budget = lc["budget_usd"]
        self.priced = self.ecfg["price_per_mtok_in"] is not None and self.ecfg["price_per_mtok_out"] is not None
        if self.budget is not None and not self.priced:
            raise LlmConfigError(f"llm.budget_usd needs price_per_mtok_in/out on llm.endpoints.{self.tcfg['endpoint']}")
        self.max_repairs, self.max_regen = int(lc["max_repairs"]), int(lc["max_regenerations"])
        self.dir = llm_dir(cfg)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.dir / f"{job.task}.jsonl"
        self.release = current_release(cfg)
        self._mutex = threading.Lock()
        records = _read_jsonl(self.cache_path)
        self.cache = {r["key"]: r for r in records if r.get("output") is not None}
        self.spent = sum(float(r.get("cost_usd", 0.0)) for p in self.dir.glob("*.jsonl")
                         for r in (records if p == self.cache_path else _read_jsonl(p))
                         if r.get("release") == self.release)
        self.stats = {"task": job.task, "model": self.model_id, "items": len(job.items), "from_cache": 0,
                      "generated": 0, "repaired": 0, "fallback": 0, "cost_usd": 0.0}
        self.stopping: str | None = None                  # "stop.flag" | "Ctrl-C" | "budget" | "error"
        self.retries, self.last_error, self.last_error_at = 0, None, None
        self.backoff_until = 0.0
        self.started_at = now_iso()

    # ------------------------------------------------------------------ cache and money
    def key_for(self, prompt: str) -> str:
        return hashlib.sha256(f"{self.model_id}\n{self.job.prompt_version}\n{prompt}".encode()).hexdigest()[:16]

    def _append(self, rec: dict) -> None:
        with self._mutex, open(self.cache_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if rec.get("output") is not None:
                self.cache[rec["key"]] = rec

    def _price(self, tokens_in: float, tokens_out: float) -> float:
        if not self.priced:
            return 0.0
        return (tokens_in * float(self.ecfg["price_per_mtok_in"])
                + tokens_out * float(self.ecfg["price_per_mtok_out"])) / 1e6

    def estimate(self, prompt: str) -> float:
        """Upper bound for one call: ~1 token per character (Thai) + the full output allowance."""
        return self._price(len(prompt), int(self.tcfg["max_output_tokens"]))

    # ------------------------------------------------------------------ one item (worker thread)
    def _one(self, llm, k: str, item: LlmItem) -> LlmResult:
        messages = [{"role": "user", "content": item.prompt}]
        repairs = regens = 0
        cost = 0.0
        result = None
        try:
            while result is None:
                reply = llm.chat(messages)
                cost += (self._price(reply.prompt_tokens, reply.completion_tokens) if reply.prompt_tokens
                         else self._price(sum(len(m["content"]) for m in messages), len(reply.text)))
                try:
                    data = self.job.schema.model_validate(extract_json(reply.text)).model_dump()
                except ValueError as e:                         # bad JSON or pydantic ValidationError
                    if repairs >= self.max_repairs:
                        result = LlmResult(item.fallback, "fallback", repairs)
                        break
                    repairs += 1
                    messages = messages + [{"role": "assistant", "content": reply.text},
                                           {"role": "user", "content": REPAIR.format(error=str(e)[:300])}]
                    continue
                error = item.check(data) if item.check else None
                if error:
                    if regens >= self.max_regen:
                        print(f"[llm:{self.job.task}] {item.key}: {error} — fallback")
                        result = LlmResult(item.fallback, "fallback", repairs)
                        break
                    regens += 1
                    messages = [{"role": "user", "content": item.prompt + "\n\n" + REGENERATE.format(error=error)}]
                    continue
                result = LlmResult(data, "llm", repairs, k)
        finally:
            with self._mutex:
                self.spent += cost
                self.stats["cost_usd"] += cost
        self._append({"key": k, "item": item.key, "task": self.job.task, "model": self.model_id,
                      "prompt_version": self.job.prompt_version, "release": self.release,
                      "output": result.output if result.source == "llm" else None,
                      "cost_usd": round(cost, 6), "repaired": repairs, "at": now_iso()})
        return result

    def on_event(self, kind: str, info: dict) -> None:   # from worker threads (OpenAICompatLLM retries)
        if kind == "retry":
            with self._mutex:
                self.retries += 1
                self.backoff_until = max(self.backoff_until, time.monotonic() + float(info.get("delay") or 0))
                self.last_error, self.last_error_at = info.get("error"), now_iso()

    # ------------------------------------------------------------------ heartbeat for `atlas status`
    def _snapshot(self, status: str) -> dict:
        s = self.stats
        done = s["from_cache"] + s["generated"] + s["fallback"]
        if status == "running" and time.monotonic() < self.backoff_until:
            status = "backing_off"
        return {"kind": "llm", "unit": "items", "job_id": f"llm:{self.job.task}", "task": self.job.task,
                "model": self.model_id, "status": status, "pid": os.getpid(), "total": s["items"],
                "cached": s["from_cache"], "this_run": s["generated"] + s["fallback"], "remaining": s["items"] - done,
                "generated": s["generated"], "repaired": s["repaired"], "fallback": s["fallback"],
                "retries": self.retries, "truncated": 0, "cost_usd": round(s["cost_usd"], 4),
                "release": self.release, "release_spend_usd": round(self.spent, 4), "budget_usd": self.budget,
                "stop_reason": self.stopping if status == "stopped" else None,
                "last_error": self.last_error, "last_error_at": self.last_error_at,
                "started_at": self.started_at, "updated_at": now_iso()}

    # ------------------------------------------------------------------ the job
    def run(self) -> tuple[dict[str, LlmResult], dict]:
        results: dict[str, LlmResult] = {}
        todo: list[tuple[str, LlmItem]] = []
        for it in self.job.items:
            k = self.key_for(it.prompt)
            if k in self.cache:
                results[it.key] = LlmResult(self.cache[k]["output"], "cache", 0, k)
            else:
                todo.append((k, it))
        self.stats["from_cache"] = len(results)
        if todo:
            lock = RunLock(self.dir / LOCK, stale_seconds=float(self.cfg["llm"]["lock_stale_seconds"]),
                           heartbeat=self.dir / PROGRESS)
            lock.acquire()                                    # jobs.LockHeld when another LLM job runs
            try:
                self._run_todo(todo, results)
            finally:
                lock.release()
        self.stats["cost_usd"] = round(self.stats["cost_usd"], 6)
        return results, self.stats

    def _run_todo(self, todo: list[tuple[str, LlmItem]], results: dict[str, LlmResult]) -> None:
        llm = self.llm or OpenAICompatLLM.for_task(self.cfg, self.job.task)
        hooked = hasattr(llm, "on_event")
        previous = llm.on_event if hooked else None
        if hooked:
            llm.on_event = self.on_event
        stop_flag = StopFlag(self.dir / STOP)
        stop_flag.clear_if_older(process_started_epoch())   # a flag left by an earlier run; a newer one is honoured
        pf = ProgressFile(self.dir / PROGRESS, min_interval=PROGRESS_EVERY_S)
        pf.write(self._snapshot("running"), force=True)
        n = max(1, int(self.ecfg["concurrency"]))
        pending = iter(todo)
        nxt = next(pending, None)
        in_flight: dict[Future, tuple[str, LlmItem, float]] = {}
        reserved = 0.0                                        # budget held by calls in flight (upper bounds)
        failure: Exception | None = None
        ex = ThreadPoolExecutor(max_workers=n, thread_name_prefix="llm")

        def begin_stop(why: str) -> None:
            if self.stopping is None:
                self.stopping = why
                for f in in_flight:
                    f.cancel()                                # queued calls never start (not paid)
                cancel = getattr(llm, "cancel", None)
                if cancel:
                    cancel()                                  # a worker in a backoff wait gives up
                if why not in ("error", "budget"):
                    print(f"[llm:{self.job.task}] stopping ({why}): waiting for the calls in flight")

        try:
            while True:
                if self.stopping is None and stop_flag.is_set():
                    begin_stop("stop.flag")
                while self.stopping is None and nxt is not None and len(in_flight) < n:
                    k, it = nxt
                    est = self.estimate(it.prompt)
                    if self.budget is not None and self.spent + reserved + est > float(self.budget):
                        if not in_flight:                     # nothing will free budget: stop here
                            begin_stop("budget")
                        break                                 # else wait: real costs are below the estimates
                    in_flight[ex.submit(self._one, llm, k, it)] = (k, it, est)
                    reserved += est
                    nxt = next(pending, None)
                if not in_flight:
                    break
                try:
                    done, _ = wait(list(in_flight), timeout=0.5, return_when=FIRST_COMPLETED)
                except KeyboardInterrupt:
                    begin_stop("Ctrl-C")
                    continue
                for fut in done:
                    k, it, est = in_flight.pop(fut)
                    reserved -= est
                    try:
                        res = fut.result()
                    except LlmConfigError as e:
                        failure = failure or e
                        begin_stop("error")
                        continue
                    except TransientGaveUp as e:              # only when max_retries is set
                        print(f"[llm:{self.job.task}] {it.key}: {e} — fallback (asked again next run)")
                        res = LlmResult(it.fallback, "fallback")
                    except (Cancelled, CancelledError):       # stopped mid-backoff / never started: asked next run
                        continue
                    except Exception as e:  # noqa: BLE001 — a bug: keep what was paid for, then re-raise it
                        failure = failure or e
                        begin_stop("error")
                        continue
                    results[it.key] = res
                    self.stats["generated" if res.source == "llm" else "fallback"] += 1
                    self.stats["repaired"] += int(res.source == "llm" and res.repaired > 0)
                pf.write(self._snapshot("running"))
        finally:
            ex.shutdown(wait=True, cancel_futures=True)
            if hooked:
                llm.on_event = previous
        if failure is not None:
            self.last_error, self.last_error_at = f"{type(failure).__name__}: {failure}", now_iso()
            pf.write(self._snapshot("failed"), force=True)
            raise failure
        if self.stopping is not None:
            pf.write(self._snapshot("stopped"), force=True)
            stop_flag.clear()
            left = len(todo) - self.stats["generated"] - self.stats["fallback"]
            why = (f"budget llm.budget_usd = {self.budget} USD reached ({round(self.spent, 4)} USD spent in "
                   f"{self.release}) — raise it" if self.stopping == "budget" else f"{self.stopping}")
            raise RunStopped(f"LLM task {self.job.task}: {why}; {left} of {len(todo)} items not done — run the same "
                             f"command again to continue (finished calls are cached, nothing is paid twice)")
        stop_flag.clear()                                     # served (or moot): never carried to the next run
        pf.write(self._snapshot("done"), force=True)

    def dry_run(self) -> dict:
        todo = [it for it in self.job.items if self.key_for(it.prompt) not in self.cache]
        chars = sum(len(it.prompt) for it in todo)
        out_tokens = len(todo) * int(self.tcfg["max_output_tokens"])
        return {"task": self.job.task, "model": self.model_id, "items": len(self.job.items),
                "cached": len(self.job.items) - len(todo), "to_call": len(todo), "est_input_tokens": chars,
                "max_output_tokens": out_tokens,
                "est_cost_usd": round(self._price(chars, out_tokens), 4) if self.priced else None,
                "release_spend_usd": round(self.spent, 4), "budget_usd": self.budget}


def run_job(cfg: dict, job: LlmJob, llm=None) -> tuple[dict[str, LlmResult], dict]:
    """Results for every item (cache, LLM or fallback) + stats for the step's meta file.
    Raises LlmConfigError (endpoint/config), jobs.LockHeld (another LLM job) or jobs.RunStopped (stop/budget)."""
    return LlmRunner(cfg, job, llm).run()


# ---------------------------------------------------------------------- CLI helpers
def build_job(cfg: dict, task: str) -> LlmJob:
    module, fn = JOBS[task].split(":")
    return getattr(importlib.import_module(module), fn)(cfg)


def dry_run_all(cfg: dict, tasks: list[str] | None = None) -> list[dict]:
    rows = []
    for task in tasks or list(JOBS):
        try:
            rows.append(LlmRunner(cfg, build_job(cfg, task)).dry_run())
        except FileNotFoundError as e:
            rows.append({"task": task, "skipped": f"missing checkpoint {Path(str(e.filename or e)).name} — "
                                                  "run the pipeline up to that step first"})
    return rows


def request_stop(cfg: dict) -> Path:
    flag = StopFlag(llm_dir(cfg) / STOP)
    flag.request()
    return flag.path


def status_extra(info: dict) -> list[str]:
    """LLM lines added under the generic jobs.format_job_status block of `atlas status`."""
    spend = f"{info.get('release_spend_usd', 0)} USD in {info.get('release', '?')}"
    if info.get("budget_usd") is not None:
        spend += f" (budget {info['budget_usd']})"
    lines = [f"  task / model          : {info.get('task')} · {info.get('model')}",
             f"  llm                   : new {int(info.get('generated') or 0):,} · repaired "
             f"{int(info.get('repaired') or 0):,} · fallback {int(info.get('fallback') or 0):,}",
             f"  cost                  : {info.get('cost_usd', 0)} USD this run · {spend}"]
    if info.get("stop_reason"):
        lines.append(f"  stopped by            : {info['stop_reason']} — run `atlas llm` again to continue")
    return lines


def check_endpoints(cfg: dict, transport=None, sleep=None) -> list[dict]:
    """One tiny JSON request per distinct (endpoint, model) used by llm.tasks: reachable? JSON? Thai intact?"""
    word, out, seen = "ภาษาไทย", [], set()
    prompt = f'Reply with ONLY this JSON object, unchanged: {{"ok": true, "word": "{word}"}}'
    for task, tcfg in cfg["llm"]["tasks"].items():
        pair = (tcfg["endpoint"], tcfg["model"])
        if not tcfg["model"] or pair in seen:
            continue
        seen.add(pair)
        row = {"endpoint": pair[0], "model": pair[1], "tasks": task, "seconds": None, "json_ok": False,
               "thai_ok": False, "error": ""}
        try:
            llm = OpenAICompatLLM.for_task(cfg, task, transport=transport, sleep=sleep, max_retries=2)
            reply = llm.chat([{"role": "user", "content": prompt}])
            data = extract_json(reply.text)
            row.update(seconds=round(reply.seconds, 2), json_ok=True, thai_ok=data.get("word") == word)
        except Exception as e:  # noqa: BLE001 — reported to the operator, not raised
            row["error"] = f"{type(e).__name__}: {e}"
        out.append(row)
    for row in out:
        row["tasks"] = ", ".join(t for t, c in cfg["llm"]["tasks"].items()
                                 if (c["endpoint"], c["model"]) == (row["endpoint"], row["model"]))
    return out
```

- [ ] **Step 6: Config** — in `pipeline/atlas/config.py` (`model_validator` is already imported since P0 Task 19):

Before
```python
class AtlasConfig(_Strict):
```
insert
```python
class LlmEndpointCfg(_Strict):
    base_url: str = ""                # e.g. https://openrouter.ai/api/v1 — empty = LLM not configured
    api_key_env: str = "ATLAS_LLM_API_KEY"
    json_mode: bool = True
    concurrency: int = Field(4, ge=1)
    request_timeout: float = Field(120.0, gt=0.0)
    max_retries: int | None = Field(None, ge=0)       # None = retry transient errors without limit
    backoff_initial: float = Field(2.0, gt=0.0)
    backoff_max: float = Field(300.0, gt=0.0)
    price_per_mtok_in: float | None = Field(None, ge=0.0)
    price_per_mtok_out: float | None = Field(None, ge=0.0)

    @model_validator(mode="after")
    def _backoff_order(self) -> LlmEndpointCfg:
        if self.backoff_max < self.backoff_initial:
            raise ValueError("llm.endpoints.<name>.backoff_max must be >= backoff_initial")
        return self


class LlmTaskCfg(_Strict):
    endpoint: str = "default"
    model: str = ""
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(600, ge=16)


class LlmTasksCfg(_Strict):
    label: LlmTaskCfg = Field(default_factory=lambda: LlmTaskCfg(temperature=0.2, max_output_tokens=600))
    merge: LlmTaskCfg = Field(default_factory=lambda: LlmTaskCfg(temperature=0.0, max_output_tokens=300))
    narrative: LlmTaskCfg = Field(default_factory=lambda: LlmTaskCfg(temperature=0.3, max_output_tokens=900))
    brief: LlmTaskCfg = Field(default_factory=lambda: LlmTaskCfg(temperature=0.3, max_output_tokens=1200))


class LlmCfg(_Strict):
    prompts_dir: str | None = None    # None = the repo's prompts/ folder
    budget_usd: float | None = Field(None, ge=0.0)
    max_repairs: int = Field(2, ge=0)
    max_regenerations: int = Field(1, ge=0)
    lock_stale_seconds: float = Field(300.0, gt=0.0)
    endpoints: dict[str, LlmEndpointCfg] = Field(default_factory=lambda: {"default": LlmEndpointCfg()})
    tasks: LlmTasksCfg = Field(default_factory=LlmTasksCfg)

    @model_validator(mode="after")
    def _known_endpoints(self):
        for name in LlmTasksCfg.model_fields:
            ep = getattr(self.tasks, name).endpoint
            if ep not in self.endpoints:
                raise ValueError(f"llm.tasks.{name}.endpoint {ep!r} is not defined in llm.endpoints")
        return self


```
After
```python
    labeling: LabelingCfg = Field(default_factory=LabelingCfg)
```
insert
```python
    llm: LlmCfg = Field(default_factory=LlmCfg)
```
Replace
```python
    if cfg["taxonomy"]["reference_path"]:
```
with
```python
    if cfg["llm"]["prompts_dir"]:
        cfg["llm"]["prompts_dir"] = _resolve(cfg["llm"]["prompts_dir"], base)
    if cfg["taxonomy"]["reference_path"]:
```

In `pipeline/config.example.yaml`:
Before
```yaml
# ---------- หัวข้อที่มี ID ถาวรข้ามรอบ (T000123) ----------
```
insert
```yaml
# ---------- LLM (ทุกงานผ่าน API แบบ OpenAI-compatible: POST {base_url}/chat/completions) ----------
llm:
  prompts_dir: null           # null = โฟลเดอร์ prompts/ ของ repo (ไฟล์ .md เป็นต้นฉบับเดียวของ prompt)
  budget_usd: null            # งบต่อรอบข้อมูล (USD) รวมทุกงาน — เกินงบ = หยุดอย่างสะอาด; เพิ่มงบแล้วรันซ้ำ = ทำต่อ (ต้องใส่ราคา)
  max_repairs: 2              # คำตอบไม่ใช่ JSON ตาม schema → ขอให้แก้ได้กี่ครั้ง
  max_regenerations: 1        # ข้อความไม่ผ่านการตรวจตัวเลข/ชื่อหัวข้อ → ให้เขียนใหม่ได้กี่ครั้ง (แล้วใช้ประโยคแม่แบบ)
  lock_stale_seconds: 300     # ไม่มี heartbeat นานเกินนี้ → atlas status แสดง hung (lock ของ process ที่ยังอยู่ไม่ถูกยึด)
  endpoints:
    default:
      base_url: ""            # เช่น https://openrouter.ai/api/v1 · https://api.opentyphoon.ai/v1 · http://localhost:8000/v1 (vLLM) — ว่าง = ยังไม่ตั้งค่า LLM
      api_key_env: ATLAS_LLM_API_KEY   # ชื่อ env var ที่เก็บ key (ห้ามใส่ key ในไฟล์) — ใช้ key เดียวกับ embedding ได้
      json_mode: true         # ส่ง response_format json_object (ปิดถ้า server ไม่รองรับ — โค้ดตรวจ JSON เองเสมอ)
      concurrency: 4
      request_timeout: 120
      max_retries: null       # null = server ล่ม/429 ลองใหม่ไม่จำกัด (backoff); key/model/URL/โควตาผิด = หยุดทันที (exit 2); ตั้งค่า = ครบแล้วหัวข้อนั้นใช้ fallback
      backoff_initial: 2
      backoff_max: 300
      price_per_mtok_in: null # USD ต่อ 1 ล้าน token ขาเข้า (ดูราคาของผู้ให้บริการ) — จำเป็นเมื่อตั้ง budget_usd
      price_per_mtok_out: null
  tasks:                      # model ว่าง = งานนั้นยังไม่ได้ตั้งค่า
    label:                    # ตั้งชื่อหัวข้อ (TH/EN)
      endpoint: default
      model: ""
      temperature: 0.2
      max_output_tokens: 600
    merge:                    # ตรวจคู่หัวข้อที่อาจซ้ำ (ข้อเสนอให้บรรณาธิการ — ไม่รวมอัตโนมัติ)
      endpoint: default
      model: ""
      temperature: 0.0
      max_output_tokens: 300
    narrative:                # คำอธิบายหัวข้อ emerging/hot/declining จากตัวเลขของ pipeline
      endpoint: default
      model: ""
      temperature: 0.3
      max_output_tokens: 900
    brief:                    # บทสรุปผู้บริหาร
      endpoint: default
      model: ""
      temperature: 0.3
      max_output_tokens: 1200

```

- [ ] **Step 7: CLI and status** — in `pipeline/atlas/cli.py`:

7a. `_run_guarded` (P0 Task 19) learns a message tag and the resume command; every P0 message, exit code and the abandon path stay as they are (defaults `tag="embed"`, `resume="embed"` keep `atlas embed` byte-identical):

Replace the whole top-level function `_run_guarded` with
```python
def _run_guarded(cfg: dict, steps: list[str] | None, config: Path | None, ensure_docs: bool = False,
                 tag: str = "embed", resume: str = "embed") -> int:
    """Run pipeline steps; map the long-run outcomes to exit codes (0 ok, 1 failed, 2 config, 3 locked, 130 stopped).
    `tag` prefixes the messages ([embed] / [llm] / [run]); `resume` names the command that continues a stopped run.

    After a second Ctrl-C abandoned in-flight requests (the exception carries `abandoned`), EVERY outcome
    exits the process at once (os._exit, after flushing) instead of waiting up to request_timeout for the
    abandoned worker threads — keeping that outcome's exit code."""
    from atlas.api_http import ApiConfigError, TransientGaveUp
    from atlas.embed_runner import StoreSaveFailed
    from atlas.jobs import LockHeld, LockUnsupported, RunStopped
    from atlas.pipeline import run

    def done(code: int, e: BaseException) -> int:
        if getattr(e, "abandoned", 0):
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(code)
        return code

    try:
        if ensure_docs:
            _ensure_docs(cfg)
        run(cfg, steps)
    except StoreSaveFailed as e:
        typer.echo(f"[{tag}] \N{THAI CHARACTER BO BAIMAI}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA UE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER NGO NGU} store \N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO} — \N{THAI CHARACTER PHO PHUNG}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMALAI}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER NO NU} journal.bin \N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER BO BAIMAI}; \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER SARA U} (\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER THANTHAKHAT}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER MO MA} / \N{THAI CHARACTER SARA O}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER SARA UEE}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER PO PLA}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER DO DEK} "
                   f"index.parquet \N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NGO NGU}) \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER NGO NGU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA I}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER SARA II}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER NGO NGU} / could not save into the store: {e}\n"
                   f"  run the same command again: uv run atlas {resume} -c {_cfg_arg(config)}", err=True)
        return done(EXIT_FAILED, e)
    except LockUnsupported as e:
        typer.echo(f"[{tag}] ERROR: {e}", err=True)
        return done(EXIT_CONFIG, e)
    except ApiConfigError as e:
        typer.echo(f"[{tag}] ERROR — \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI THO} config \N{THAI CHARACTER SARA AE}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER MAI THO}\N{THAI CHARACTER WO WAEN}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA AI MAIMUAN}\N{THAI CHARACTER HO HIP}\N{THAI CHARACTER MO MA}\N{THAI CHARACTER MAI EK} / fix the config and rerun:\n  {e}", err=True)
        return done(EXIT_CONFIG, e)
    except LockHeld as e:
        typer.echo(f"[{tag}] {e}\n  \N{THAI CHARACTER DO DEK}\N{THAI CHARACTER SARA UU}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER THO THUNG}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA A} / status: uv run atlas status -c {_cfg_arg(config)}", err=True)
        return done(EXIT_LOCKED, e)
    except (RunStopped, KeyboardInterrupt) as e:
        typer.echo(f"[{tag}] \N{THAI CHARACTER HO HIP}\N{THAI CHARACTER YO YAK}\N{THAI CHARACTER SARA U}\N{THAI CHARACTER DO DEK}\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG}\N{THAI CHARACTER NO NU}\N{THAI CHARACTER SARA E}\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER RO RUA}\N{THAI CHARACTER MAITAIKHU}\N{THAI CHARACTER CHO CHAN} / stopped before completion{': ' + str(e) if str(e) else ''}\n"
                   f"  \N{THAI CHARACTER THO THAHAN}\N{THAI CHARACTER SARA AM}\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER MAI EK}\N{THAI CHARACTER O ANG} / resume: uv run atlas {resume} -c {_cfg_arg(config)}", err=True)
        return done(EXIT_STOPPED, e)
    except TransientGaveUp as e:
        typer.echo(f"[{tag}] ERROR: {e}\n  (max_retries is set in embedding.api / llm.endpoints; null = retry forever)", err=True)
        return done(EXIT_FAILED, e)
    except BaseException as e:                       # unexpected: the usual traceback, but never wait for
        if getattr(e, "abandoned", 0):               # abandoned worker threads
            import traceback

            traceback.print_exc()
            return done(EXIT_FAILED, e)
        raise
    return 0
```

7b. `atlas run` names itself when a run stops (an LLM or embedding stop inside `atlas run` is resumed by `atlas run`):

Replace
```python
    raise typer.Exit(_run_guarded(load_config(config), step or None, config))
```
with
```python
    raise typer.Exit(_run_guarded(load_config(config), step or None, config, tag="run", resume="run"))
```

7c. `atlas status` — the P0 `render_status` already lists every folder under `state_dir` that holds a `progress.json`, so the LLM job (`state_dir/llm_cache/`) appears by itself; give it its own stale threshold and the LLM lines:

Replace
```python
    for job in jobs:
        info = job_status(job, _lock_stale(cfg))
        extra: list[str] = []
        if info.get("kind") == "embedding":
```
with
```python
    for job in jobs:
        llm_job = job.name == "llm_cache"
        info = job_status(job, float(cfg["llm"]["lock_stale_seconds"]) if llm_job else _lock_stale(cfg))
        extra: list[str] = []
        if info.get("kind") == "llm":
            from atlas.llm_runner import status_extra

            extra = status_extra(info)
        elif info.get("kind") == "embedding":
```

and in `pipeline/atlas/jobs.py`, `format_job_status` reads the LLM's `this_run` counter (embedding progress keeps `embedded`):

Replace
```python
this run {int(info.get('embedded') or 0):,}
```
with
```python
this run {int(info.get('this_run', info.get('embedded')) or 0):,}
```

7d. The LLM commands — append to `pipeline/atlas/cli.py`:

```python


# ---------- LLM work: atlas llm / llm-stop (progress: `atlas status`)
@app.command("llm")
def llm_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    check: bool = typer.Option(False, "--check", help="one tiny request per endpoint/model: reachable, JSON, Thai"),
    dry_run: bool = typer.Option(False, "--dry-run", help="estimate calls, tokens and cost — no network"),
    task: list[str] = typer.Option(None, "--task", "-t", help="limit --dry-run to these tasks"),
    background: bool = typer.Option(False, "--background", help="run detached from this window (you may close it); "
                                                                "log in state_dir/llm_cache/run.log"),
) -> None:
    """LLM work (labels, merge checks, narratives, brief). Without flags: run the label and narrate steps.

    Exit codes (as `atlas embed`): 0 done, 2 endpoint/config error, 3 another LLM job runs, 130 stopped
    (`atlas llm-stop`, Ctrl-C or llm.budget_usd) — run the same command again to continue.
    """
    from atlas.config import load_config
    from atlas.llm_runner import check_endpoints, dry_run_all
    from atlas.pipeline import STEPS

    cfg = load_config(config)
    if check:
        rows = check_endpoints(cfg)
        if not rows:
            typer.echo("no llm.tasks.<task>.model is set — nothing to check")
            raise typer.Exit(EXIT_CONFIG)
        for r in rows:
            state = "OK  " if r["json_ok"] and r["thai_ok"] else "FAIL"
            typer.echo(f"{state} {r['endpoint']} · {r['model']} ({r['tasks']}): json={r['json_ok']} "
                       f"thai={r['thai_ok']} {r['seconds']}s {r['error']}")
        raise typer.Exit(0 if all(r["json_ok"] and r["thai_ok"] for r in rows) else EXIT_CONFIG)
    if dry_run:
        rows = dry_run_all(cfg, task or None)
        if not rows:
            typer.echo("no LLM tasks are registered yet")
        for r in rows:
            if "skipped" in r:
                typer.echo(f"{r['task']:<10} skipped — {r['skipped']}")
                continue
            cost = "unknown (set price_per_mtok_in/out)" if r["est_cost_usd"] is None else f"≤ {r['est_cost_usd']} USD"
            typer.echo(f"{r['task']:<10} {r['model'] or '(no model)'}: {r['items']} items, {r['cached']} cached, "
                       f"{r['to_call']} to call · ~{r['est_input_tokens']:,} input tokens, ≤ {r['max_output_tokens']:,} "
                       f"output · cost {cost} · spent this release {r['release_spend_usd']} USD"
                       + (f" of {r['budget_usd']}" if r["budget_usd"] is not None else ""))
        return
    if background:
        raise typer.Exit(_llm_background(cfg, config))
    code = _run_guarded(cfg, [s for s in ("label", "narrate") if s in STEPS], config, tag="llm", resume="llm")
    if code == 0:
        typer.echo(f"[llm] done — publish with: uv run atlas run -c {_cfg_arg(config)} --step export")
    raise typer.Exit(code)


def _llm_background(cfg: dict, config: Path | None) -> int:
    """`atlas llm` in a detached process (P0 spawn_background); a child that dies at once is reported."""
    import time

    from atlas.jobs import LOG, os_lock_held, spawn_background
    from atlas.llm_runner import llm_dir

    d, c = llm_dir(cfg), _cfg_arg(config)
    d.mkdir(parents=True, exist_ok=True)
    if os_lock_held(d):
        typer.echo(f"[llm] another LLM job is running — status: uv run atlas status -c {c}", err=True)
        return EXIT_LOCKED
    args = ["-m", "atlas", "llm"] + (["-c", str(Path(config).resolve())] if config else [])
    spawned = spawn_background(args, d / LOG, cwd=Path.cwd())
    deadline = time.monotonic() + float(os.environ.get("ATLAS_BACKGROUND_CHECK_S", "3"))
    while time.monotonic() < deadline:
        code = spawned.proc.poll()
        if code is not None:
            typer.echo(f"[llm] background run ended at once — exit code {code}; last lines of {d / LOG}:\n"
                       f"{_tail(d / LOG)}", err=code != 0)
            return code
        time.sleep(0.1)
    typer.echo(f"[llm] running in the background: PID {spawned.pid} — you may close this window")
    if spawned.warning:
        typer.echo(f"[llm] WARNING: {spawned.warning}", err=True)
    typer.echo(f"  log    : {d / LOG}\n  status : uv run atlas status -c {c}\n  stop   : uv run atlas llm-stop -c {c}")
    return 0


@app.command("llm-stop")
def llm_stop_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
) -> None:
    """Ask the LLM job to stop after the calls in flight (run `atlas llm` again to continue)."""
    from atlas.config import load_config
    from atlas.jobs import os_lock_held
    from atlas.llm_runner import llm_dir, request_stop

    cfg = load_config(config)
    flag = request_stop(cfg)
    if os_lock_held(llm_dir(cfg)):
        typer.echo(f"[llm-stop] stop requested ({flag}): the LLM job finishes the calls in flight, saves and exits")
    else:
        typer.echo(f"[llm-stop] stop requested ({flag}); no LLM job is running now — a pipeline that is still at an "
                   f"earlier step stops when its LLM step starts")
    typer.echo(f"  status: uv run atlas status -c {_cfg_arg(config)}")
```

- [ ] **Step 8: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_llm.py -q && uv run pytest -q`
Expected: all pass (20 new tests; P0's `test_jobs.py` and `test_embed_cli.py` unchanged and green).

- [ ] **Step 9: Commit**

```bash
git add pipeline/atlas/prompts.py pipeline/atlas/llm.py pipeline/atlas/llm_runner.py pipeline/atlas/config.py pipeline/config.example.yaml pipeline/atlas/cli.py pipeline/atlas/jobs.py pipeline/tests/test_llm.py
git commit -m "feat(llm): OpenAI-compatible adapter on api_http, prompts from prompts/*.md, LLM runner on the P0 job plumbing (cache/journal, budget, stop, status)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Stable topic IDs + lineage (fit yearly / assign quarterly)

Measured on the 20K synthetic corpus: Q1 fit (106 raw → 29 topics), Q2 = Q1 + 2,000 late articles in `auto` mode → assign, 0 of 1,992 new articles unassigned, kept 100 %; Q3 forced refit on Q2 (108 raw clusters, lite vectors re-fitted) → all 29 matched as `continue`, ARI 1.0 on shared articles.

**Files:**
- Create: `pipeline/atlas/lineage.py`, `pipeline/tests/test_lineage.py`
- Modify: `pipeline/atlas/cluster.py`, `pipeline/tests/test_cluster.py` (one assertion)

**Interfaces:**
- Consumes: `atlas.state` (Task 1), `load_aligned`, `hdbscan_labels(red, fine, backend)` (Task 2); P0 `reduce_embeddings`, `merge_similar`, `assign_outliers`, `relabel_by_size`, `centroids`, `coarse_groups`, `topic_terms`, `topic_keywords`.
- Produces:
  - `atlas.lineage`: `EVENTS = ("new","continue","split","merge","retired")`, `EVENT_COLUMNS = ["event","topic_id","parents"]` (`parents` = `"3;7"`), `topic_code(tid) -> "T%06d"`, `member_centroids(article_ids, emb, assignments) -> {topic_id: unit vector}`, `match_topics(prev, cur, old_vec, new_vec, next_id, containment, min_shared) -> ({tmp id: stable id}, events DataFrame, next_id)`, `kept_fraction(prev_ids, cur_ids) -> float`, `assign_to_previous(article_ids, emb, prev_assign, min_sim) -> (labels, n_new, n_new_unassigned)`, `load_topic_state(cfg, release) -> {"assignments","registry","model"} | None`, `save_topic_state(cfg, release, assignments, registry, events, model) -> Path`, `update_registry(prev_registry, active_ids, events, release) -> DataFrame[topic_id, born, status, last_seen]`.
  - `atlas.cluster`: `fit_labels(emb, ccfg, seed) -> (labels, n_raw)`, `stable_labels(cfg, article_ids, emb, prev, model_id) -> (labels, events, model, message)`, `cluster(cfg)` now writes **stable integer ids** (first fit: 1..k by size), plus `work/04_lineage` (`event, topic_id, parents`) and `work/04_topics_meta.json` (`release, previous_release, mode, kept_fraction, n_topics, events{…}`); state `state/releases/<release>/topics/{assignments.parquet (article_id, topic_id), registry.parquet, lineage.parquet, model.json {embedding_model, fitted_release, releases_since_fit, next_id, mode}}`.

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_lineage.py`:

```python
import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.cluster import cluster
from atlas.io_utils import read_table, write_table
from atlas.lineage import assign_to_previous, kept_fraction, match_topics, topic_code, update_registry


def _assign(spec: dict[int, int], start: int = 0) -> pd.DataFrame:
    """{topic: n_articles} → article_id/topic_id rows with consecutive ids a{start}…"""
    rows, i = [], start
    for t, n in spec.items():
        for _ in range(n):
            rows.append({"article_id": f"a{i}", "topic_id": t})
            i += 1
    return pd.DataFrame(rows)


def _events(ev: pd.DataFrame) -> dict[int, tuple[str, str]]:
    return {int(r.topic_id): (r.event, r.parents) for r in ev.itertuples()}


def test_continue_new_and_retired():
    prev = _assign({1: 20, 2: 20, 3: 20})
    cur = prev.copy()
    cur["topic_id"] = cur["topic_id"].map({1: 0, 2: 1, 3: -1})          # topic 3's articles now unassigned
    cur = pd.concat([cur, _assign({2: 15}, start=100)])                  # a brand-new cluster of new articles
    mapping, ev, nxt = match_topics(prev, cur, {}, {}, next_id=4, containment=0.5, min_shared=5)
    assert mapping == {0: 1, 1: 2, 2: 4} and nxt == 5
    assert _events(ev) == {1: ("continue", ""), 2: ("continue", ""), 4: ("new", ""), 3: ("retired", "")}


def test_split_keeps_id_for_the_larger_child():
    prev = _assign({7: 40})
    cur = prev.copy()
    cur["topic_id"] = [0] * 25 + [1] * 15
    mapping, ev, _ = match_topics(prev, cur, {}, {}, next_id=8, containment=0.5, min_shared=5)
    assert mapping == {0: 7, 1: 8}
    assert _events(ev) == {7: ("split", "7"), 8: ("split", "7")}


def test_merge_takes_the_id_of_the_main_source():
    prev = _assign({1: 30, 2: 20})
    cur = prev.assign(topic_id=0)
    mapping, ev, _ = match_topics(prev, cur, {}, {}, next_id=3, containment=0.5, min_shared=5)
    assert mapping == {0: 1}
    assert _events(ev) == {1: ("merge", "1;2")}
    reg = update_registry(pd.DataFrame({"topic_id": [1, 2], "born": "2026Q1", "status": "active",
                                        "last_seen": "2026Q1"}), [1], ev, "2026Q2")
    assert reg.set_index("topic_id")["status"].to_dict() == {1: "active", 2: "merged"}
    assert reg.set_index("topic_id").loc[1, "born"] == "2026Q1"


def test_cosine_breaks_ties_between_equal_overlaps():
    prev = _assign({1: 10, 2: 10})
    cur = prev.assign(topic_id=0)                                         # equal overlap 10 vs 10
    e = np.eye(3)
    mapping, _, _ = match_topics(prev, cur, {1: e[0], 2: e[1]}, {0: e[1]}, 3, 0.5, 5)
    assert mapping == {0: 2}                                              # topic 2 points the same way


def test_tiny_overlap_is_not_an_edge():
    prev = _assign({1: 50})
    cur = pd.concat([prev.iloc[:3].assign(topic_id=0), _assign({0: 30}, start=100)])
    mapping, ev, _ = match_topics(prev, cur, {}, {}, 2, 0.5, 5)           # 3 shared < min_shared 5
    assert mapping == {0: 2} and set(ev["event"]) == {"new", "retired"}


def test_assign_mode_keeps_old_and_places_new_articles():
    emb = np.array([[1, 0], [1, 0.1], [0, 1], [0.1, 1], [0.95, 0.05], [-1, 0]], dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    ids = pd.Series([f"a{i}" for i in range(6)])
    prev = pd.DataFrame({"article_id": ["a0", "a1", "a2", "a3"], "topic_id": [5, 5, 9, 9]})
    labels, n_new, n_lost = assign_to_previous(ids, emb, prev, min_sim=0.35)
    assert labels.tolist() == [5, 5, 9, 9, 5, -1] and (n_new, n_lost) == (2, 1)


def test_codes_and_kept_fraction():
    assert topic_code(123) == "T000123"
    assert kept_fraction({1, 2, 3, 4}, {1, 2, 3, 9}) == 0.75 and kept_fraction(set(), {1}) == 1.0


def _blob_work(cfg, n_per=60, k=4, extra=0, seed=0):
    rng = np.random.default_rng(seed)
    X = np.vstack([np.eye(16)[c] + rng.normal(0, 0.05, (n_per, 16)) for c in range(k)]
                  + ([np.eye(16)[0] + rng.normal(0, 0.05, (extra, 16))] if extra else []))
    X = (X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32)
    n = len(X)
    work = Path(cfg["pipeline"]["work_dir"])
    write_table(pd.DataFrame({"article_id": [f"a{i}" for i in range(n)], "doc_text": ["ข้าว เกษตรกร"] * n,
                              "keywords_th": ["ข้าว"] * n, "keywords_en": [""] * n}), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", X)
    (work / "03_meta.json").write_text(json.dumps({"model_id": "fake|1", "n": n, "dim": 16}), encoding="utf-8")


def _cfg(make_cfg, tmp_path, release, mode="auto"):
    cfg = make_cfg(tmp_path)
    cfg["clustering"].update(reducer="pca", n_groups=2)
    cfg["clustering"]["fine"].update(hdbscan_min_cluster_size=20, hdbscan_min_samples=5)
    cfg["pipeline"]["release"] = release
    cfg["topics"]["mode"] = mode
    return cfg


def test_cluster_step_keeps_ids_across_releases(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path, "2026Q1")
    _blob_work(cfg)
    first = cluster(cfg)
    work = tmp_path / "work"
    ids1 = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    assert ids1 == [1, 2, 3, 4] and set(read_table(work / "04_lineage.parquet")["event"]) == {"new"}

    cfg = _cfg(make_cfg, tmp_path, "2026Q2")                                     # auto → assign
    _blob_work(cfg, extra=10)
    second = cluster(cfg)
    meta = json.loads((work / "04_topics_meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "assign" and meta["kept_fraction"] == 1.0 and meta["previous_release"] == "2026Q1"
    assert (second[:len(first)] == first).all() and set(second[len(first):]) == {first[0]}

    cfg = _cfg(make_cfg, tmp_path, "2026Q3", mode="fit")                         # forced refit → matched
    _blob_work(cfg, extra=10, seed=1)
    cluster(cfg)
    meta = json.loads((work / "04_topics_meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "fit" and meta["kept_fraction"] == 1.0 and meta["events"]["continue"] == 4

    again = cluster(cfg)                                                          # same release re-run: idempotent
    assert json.loads((work / "04_topics_meta.json").read_text(encoding="utf-8")) == meta
    assert (tmp_path / "state" / "releases" / "2026Q3" / "topics" / "assignments.parquet").exists()
    assert len(set(again.tolist())) == 4


def test_embedding_model_change_forces_refit(make_cfg, tmp_path):
    cfg = _cfg(make_cfg, tmp_path, "2026Q1")
    _blob_work(cfg)
    cluster(cfg)
    cfg = _cfg(make_cfg, tmp_path, "2026Q2")
    _blob_work(cfg)
    (tmp_path / "work" / "03_meta.json").write_text(json.dumps({"model_id": "other|2", "n": 240, "dim": 16}),
                                                   encoding="utf-8")
    cluster(cfg)
    meta = json.loads((tmp_path / "work" / "04_topics_meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "fit" and meta["kept_fraction"] == 1.0
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_lineage.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.lineage'`.

- [ ] **Step 3: Create `pipeline/atlas/lineage.py`**

```python
"""Stable topic IDs across releases + lineage events.

Topic ids are stable integers N, published as "T%06d" (T000123). A release either
  assigns  — keeps last release's topics; articles seen before keep their topic, new
             articles join the nearest topic centroid (cosine ≥ outlier_min_similarity)
  fits     — clusters from scratch, then matches new clusters to last release's topics
             through the articles they share.

Matching (fit): M[o, n] = articles shared by old topic o and new cluster n.
  c_old = M / |o ∩ current docs|   (how much of o went into n)
  c_new = M / |n ∩ previous docs|  (how much of n came from o)
  edge o–n  ⇔  M ≥ match_min_shared and (c_old ≥ θ or c_new ≥ θ), θ = match_containment
Inside each connected component, pairs are taken greedily by (shared articles, centroid
cosine, smaller old id) so each old id is inherited at most once. Events per new topic:
  merge (≥ 2 old sources) · split (its source has ≥ 2 heirs) · continue · new (no edge);
old topics with no edge are retired. Centroid cosine is computed in the CURRENT embedding
space (old topic = mean of its articles' current vectors), so it works even when the
embedding space changes between runs (lite provider).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.state import release_dir

EVENTS = ("new", "continue", "split", "merge", "retired")
EVENT_COLUMNS = ["event", "topic_id", "parents"]


def topic_code(tid: int) -> str:
    return f"T{int(tid):06d}"


def _unit(v: np.ndarray) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-9)


def member_centroids(article_ids: pd.Series, emb: np.ndarray, assignments: pd.DataFrame) -> dict[int, np.ndarray]:
    """Unit centroid (current space) of every topic in `assignments` from its articles present now."""
    pos = pd.Series(np.arange(len(article_ids)), index=article_ids.to_numpy())
    a = assignments[(assignments["topic_id"] >= 0) & assignments["article_id"].isin(pos.index)]
    out: dict[int, np.ndarray] = {}
    for tid, g in a.groupby("topic_id"):
        out[int(tid)] = _unit(emb[pos.loc[g["article_id"]].to_numpy()].mean(axis=0))
    return out


def match_topics(prev: pd.DataFrame, cur: pd.DataFrame, old_vec: dict[int, np.ndarray],
                 new_vec: dict[int, np.ndarray], next_id: int, containment: float,
                 min_shared: int) -> tuple[dict[int, int], pd.DataFrame, int]:
    """prev: article_id, topic_id (stable, last release) · cur: article_id, topic_id (temporary, this fit).

    Returns ({temporary id → stable id}, events [event, topic_id, parents], next free id).
    """
    prev = prev[prev["topic_id"] >= 0]
    cur_all = cur
    cur = cur[cur["topic_id"] >= 0]
    new_ids = sorted(int(t) for t in cur["topic_id"].unique())
    old_ids = sorted(int(t) for t in prev["topic_id"].unique())
    shared = prev.merge(cur, on="article_id", suffixes=("_old", "_new"))
    M = shared.groupby(["topic_id_old", "topic_id_new"]).size()
    old_size = prev[prev["article_id"].isin(set(cur_all["article_id"]))].groupby("topic_id").size()
    new_size = cur[cur["article_id"].isin(set(prev["article_id"]))].groupby("topic_id").size()

    edges: dict[tuple[int, int], int] = {}
    for (o, n), m in M.items():
        c_old = m / max(int(old_size.get(o, 0)), 1)
        c_new = m / max(int(new_size.get(n, 0)), 1)
        if m >= min_shared and (c_old >= containment or c_new >= containment):
            edges[(int(o), int(n))] = int(m)
    sources: dict[int, set[int]] = {n: set() for n in new_ids}
    heirs: dict[int, set[int]] = {o: set() for o in old_ids}
    for o, n in edges:
        sources[n].add(o)
        heirs[o].add(n)

    def cos(o: int, n: int) -> float:
        if o in old_vec and n in new_vec:
            return float(old_vec[o] @ new_vec[n])
        return -1.0

    mapping: dict[int, int] = {}
    used: set[int] = set()
    for (o, n), _m in sorted(edges.items(), key=lambda kv: (-kv[1], -cos(*kv[0]), kv[0][0], kv[0][1])):
        if o not in used and n not in mapping:
            mapping[n] = o
            used.add(o)
    rows = []
    for n in new_ids:
        if n not in mapping:
            mapping[n], next_id = next_id, next_id + 1
        src = sorted(sources[n])
        if len(src) >= 2:
            rows.append(("merge", mapping[n], src))
        elif len(src) == 1 and len(heirs[src[0]]) >= 2:
            rows.append(("split", mapping[n], src))
        elif len(src) == 1 and mapping[n] == src[0]:
            rows.append(("continue", mapping[n], []))
        elif len(src) == 1:                  # its source's id went to a larger partner (many-to-many)
            rows.append(("split", mapping[n], src))
        else:
            rows.append(("new", mapping[n], []))
    for o in old_ids:
        if not heirs[o]:
            rows.append(("retired", o, []))
    events = pd.DataFrame([{"event": e, "topic_id": t, "parents": ";".join(map(str, p))} for e, t, p in rows],
                          columns=EVENT_COLUMNS)
    return mapping, events, next_id


def kept_fraction(prev_ids: set[int], cur_ids: set[int]) -> float:
    """Share of last release's topic ids that still exist."""
    return len(prev_ids & cur_ids) / len(prev_ids) if prev_ids else 1.0


def assign_to_previous(article_ids: pd.Series, emb: np.ndarray, prev_assign: pd.DataFrame,
                       min_sim: float) -> tuple[np.ndarray, int, int]:
    """Assign mode. Returns (labels aligned with article_ids, n_new_articles, n_new_unassigned)."""
    known = dict(zip(prev_assign["article_id"], prev_assign["topic_id"].astype(int)))
    labels = np.array([known.get(a, -2) for a in article_ids], dtype=int)      # −2 = never seen
    vecs = member_centroids(article_ids, emb, prev_assign)
    is_new = labels == -2
    todo = np.where(labels < 0)[0]                                            # new + previously unassigned
    if len(todo) and vecs:
        ids = np.array(sorted(vecs))
        C = np.stack([vecs[t] for t in ids])
        sim = emb[todo] @ C.T
        labels[todo] = np.where(sim.max(axis=1) >= min_sim, ids[sim.argmax(axis=1)], -1)
    labels[labels == -2] = -1
    return labels, int(is_new.sum()), int((is_new & (labels < 0)).sum())


# ------------------------------------------------------------------ persistent state
def _topics_dir(cfg: dict, release: str) -> Path:
    return release_dir(cfg, release) / "topics"


def load_topic_state(cfg: dict, release: str | None) -> dict | None:
    """{"assignments", "registry", "model"} of a release, or None when it has no topic state."""
    if not release:
        return None
    d = _topics_dir(cfg, release)
    if not (d / "model.json").exists():
        return None
    return {"assignments": read_table(d / "assignments.parquet"),
            "registry": read_table(d / "registry.parquet"),
            "model": json.loads((d / "model.json").read_text(encoding="utf-8"))}


def save_topic_state(cfg: dict, release: str, assignments: pd.DataFrame, registry: pd.DataFrame,
                     events: pd.DataFrame, model: dict) -> Path:
    release_dir(cfg, release, create=True)
    d = _topics_dir(cfg, release)
    d.mkdir(parents=True, exist_ok=True)
    write_table(assignments.reset_index(drop=True), d / "assignments.parquet")
    write_table(registry.reset_index(drop=True), d / "registry.parquet")
    write_table(events.reset_index(drop=True), d / "lineage.parquet")
    (d / "model.json").write_text(json.dumps(model, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def update_registry(prev_registry: pd.DataFrame | None, active_ids: list[int], events: pd.DataFrame,
                    release: str) -> pd.DataFrame:
    """topic_id, born, status (active | retired | merged), last_seen — one row per id ever issued."""
    cols = ["topic_id", "born", "status", "last_seen"]
    reg = prev_registry.copy() if prev_registry is not None else pd.DataFrame(columns=cols)
    reg = reg.set_index("topic_id") if len(reg) else pd.DataFrame(columns=cols[1:])
    merged_away = {int(p) for ps in events.loc[events["event"] == "merge", "parents"] for p in str(ps).split(";") if p}
    for tid in reg.index:
        if int(tid) not in active_ids and reg.loc[tid, "status"] == "active":
            reg.loc[tid, "status"] = "merged" if int(tid) in merged_away else "retired"
    for tid in active_ids:
        born = reg.loc[tid, "born"] if tid in reg.index else release
        reg.loc[tid, ["born", "status", "last_seen"]] = [born, "active", release]
    out = reg.reset_index().rename(columns={"index": "topic_id"})
    out["topic_id"] = out["topic_id"].astype(int)
    return out[cols].sort_values("topic_id").reset_index(drop=True)
```

- [ ] **Step 4: Edit `pipeline/atlas/cluster.py`**

4a. Extend the module docstring:
Replace
```python
  → per topic: c-TF-IDF words, author keywords, coherence (mean cosine to centroid)
"""
```
with
```python
  → per topic: c-TF-IDF words, author keywords, coherence (mean cosine to centroid)

Stable ids (atlas/lineage.py): topics.mode auto|fit|assign — assign keeps last release's
topics, fit re-clusters and matches clusters to last release's ids; state per release in
state_dir/releases/<release>/topics/. Extra outputs: 04_lineage, 04_topics_meta.json.
"""
```
4b. Imports (Task 2 left `from atlas.io_utils import write_table`):
Replace
```python
from atlas.io_utils import write_table
```
with
```python
from atlas.io_utils import write_table
from atlas.lineage import (
    EVENT_COLUMNS,
    EVENTS,
    assign_to_previous,
    kept_fraction,
    load_topic_state,
    match_topics,
    member_centroids,
    save_topic_state,
    update_registry,
)
from atlas.state import current_release, previous_release
```
4c. The fit/assign logic and the new `cluster()`. `fit_labels` holds exactly the lines the current `cluster()` runs between `raw = hdbscan_labels(…)` and `relabel_by_size(…)`, including the fix wave's all-noise rule (a corpus of ≥ 2 × `hdbscan_min_cluster_size` documents that HDBSCAN calls all noise is an error — only a tiny corpus becomes one topic), so it still fails before any checkpoint is written.

Replace everything from the line starting `def cluster(cfg: dict) -> np.ndarray:` to the end of the file with
```python
def fit_labels(emb: np.ndarray, ccfg: dict, seed: int) -> tuple[np.ndarray, int]:
    """Cluster from scratch → (labels 0..k−1 by size, −1 = unassigned; raw cluster count)."""
    raw = hdbscan_labels(reduce_embeddings(emb, ccfg, seed), ccfg["fine"], ccfg["hdbscan_backend"])
    n_raw = len(set(raw.tolist()) - {-1})
    labels = merge_similar(raw, emb, float(ccfg["merge_similarity"]))
    labels = assign_outliers(labels, emb, float(ccfg["outlier_min_similarity"]))
    if (labels < 0).all():
        mcs = int(ccfg["fine"]["hdbscan_min_cluster_size"])
        if len(labels) >= 2 * mcs:
            raise ValueError(
                f"HDBSCAN found no clusters in {len(labels):,} documents (everything is noise). Lower "
                f"clustering.fine.hdbscan_min_cluster_size (now {mcs}) / hdbscan_min_samples, or check the "
                f"embeddings (embedding.provider, 03_meta.json) before publishing anything")
        labels = np.zeros(len(labels), dtype=int)      # tiny corpus (< 2 × min_cluster_size): one topic
    return relabel_by_size(labels), n_raw


def _embedding_model_id(work: Path) -> str:
    meta = work / "03_meta.json"
    return json.loads(meta.read_text(encoding="utf-8"))["model_id"] if meta.exists() else ""


def _active_ids(registry: pd.DataFrame) -> set[int]:
    return set(registry.loc[registry["status"] == "active", "topic_id"].astype(int))


def stable_labels(cfg: dict, article_ids: pd.Series, emb: np.ndarray, prev: dict | None,
                  model_id: str) -> tuple[np.ndarray, pd.DataFrame, dict, str]:
    """→ (labels with stable ids, lineage events, model.json for this release, log message)."""
    ccfg, tcfg, seed = cfg["clustering"], cfg["topics"], int(cfg["pipeline"]["seed"])
    min_sim = float(ccfg["outlier_min_similarity"])
    mode, reason = tcfg["mode"], "configured"
    if prev is None:
        mode, reason = "fit", "no previous release"
    elif mode == "auto":
        pm = prev["model"]
        if pm.get("embedding_model") != model_id:
            mode, reason = "fit", "embedding model changed"
        elif int(pm.get("releases_since_fit", 0)) + 1 >= int(tcfg["refit_every_releases"]):
            mode, reason = "fit", "scheduled refit"
        else:
            mode, reason = "assign", "auto"
    if mode == "assign":
        labels, n_new, n_lost = assign_to_previous(article_ids, emb, prev["assignments"], min_sim)
        if tcfg["mode"] == "auto" and n_new and n_lost / n_new > float(tcfg["refit_max_unassigned"]):
            mode, reason = "fit", f"{n_lost / n_new:.0%} of new articles fit no topic"
        else:
            cur = sorted(set(labels.tolist()) - {-1})
            events = pd.DataFrame([{"event": "continue", "topic_id": t, "parents": ""} for t in cur]
                                  + [{"event": "retired", "topic_id": t, "parents": ""}
                                     for t in sorted(_active_ids(prev["registry"]) - set(cur))],
                                  columns=EVENT_COLUMNS)
            model = {**prev["model"], "releases_since_fit": int(prev["model"].get("releases_since_fit", 0)) + 1,
                     "mode": "assign"}
            return labels, events, model, f"assign ({reason}): {n_new:,} new articles, {n_lost:,} without a topic"
    tmp, n_raw = fit_labels(emb, ccfg, seed)
    cur_df = pd.DataFrame({"article_id": article_ids.to_numpy(), "topic_id": tmp})
    if prev is None:
        mapping = {t: t + 1 for t in sorted(set(tmp.tolist()) - {-1})}
        events = pd.DataFrame([{"event": "new", "topic_id": s, "parents": ""} for s in mapping.values()],
                              columns=EVENT_COLUMNS)
        next_id = max(mapping.values(), default=0) + 1
    else:
        pa = prev["assignments"]
        old_vec = member_centroids(article_ids, emb, pa)
        new_vec = member_centroids(article_ids, emb, cur_df)
        mapping, events, next_id = match_topics(pa, cur_df, old_vec, new_vec, int(prev["model"]["next_id"]),
                                                float(tcfg["match_containment"]), int(tcfg["match_min_shared"]))
    labels = np.array([mapping.get(int(t), -1) for t in tmp], dtype=int)
    model = {"embedding_model": model_id, "fitted_release": current_release(cfg), "releases_since_fit": 0,
             "next_id": int(next_id), "mode": "fit"}
    return labels, events, model, f"fit ({reason}): {n_raw} raw clusters → {len(mapping)} topics"


def cluster(cfg: dict) -> np.ndarray:
    work = Path(cfg["pipeline"]["work_dir"])
    df, emb = load_aligned(work)
    ccfg, seed = cfg["clustering"], int(cfg["pipeline"]["seed"])
    release, prev_release = current_release(cfg), previous_release(cfg)
    prev = load_topic_state(cfg, prev_release)

    labels, events, model, msg = stable_labels(cfg, df["article_id"], emb, prev, _embedding_model_id(work))
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
    fine = pd.DataFrame({"article_id": df["article_id"], "fine_topic": labels})
    write_table(fine, work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"article_id": df["article_id"],
                              "coarse_topic": [group_of.get(int(x), -1) for x in labels]}),
                work / "04_coarse_topics.parquet")
    write_table(info, work / "04_topic_info.parquet")
    write_table(events, work / "04_lineage.parquet")
    np.save(work / "04_centroids.npy", C)
    (work / "04_centroid_ids.json").write_text(json.dumps(ids), encoding="utf-8")

    kept = kept_fraction(set() if prev is None else _active_ids(prev["registry"]), set(ids))
    (work / "04_topics_meta.json").write_text(json.dumps({
        "release": release, "previous_release": prev_release, "mode": model["mode"],
        "kept_fraction": round(kept, 4), "n_topics": len(ids),
        "events": {e: int((events["event"] == e).sum()) for e in EVENTS},
    }), encoding="utf-8")
    registry = update_registry(None if prev is None else prev["registry"], ids, events, release)
    save_topic_state(cfg, release, fine.rename(columns={"fine_topic": "topic_id"}), registry, events, model)
    print(f"[cluster] {msg}; {len(ids)} topics, {len(set(groups.tolist()))} groups, "
          f"unassigned {(labels < 0).mean():.1%}, ids kept {kept:.0%}")
    return labels
```

4d. Topic ids now start at 1 (largest first). The one P0 test that names topic 0 — the fix wave's tiny all-noise corpus — expects the first stable id, in `pipeline/tests/test_cluster.py`:
Replace
```python
    assert set(labels.tolist()) == {0}
```
with
```python
    assert set(labels.tolist()) == {1}                                            # first stable id
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_lineage.py tests/test_cluster.py tests/test_pipeline_small.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/lineage.py pipeline/atlas/cluster.py pipeline/tests/test_lineage.py pipeline/tests/test_cluster.py
git commit -m "feat(topics): stable topic ids T000123 + lineage (continue/split/merge/new/retired), fit yearly / assign quarterly

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 5: Leiden on a kNN graph (optional `clustering.algorithm: leiden`)

`igraph` 1.0.0 ships `cp39-abi3` wheels for Windows, macOS and Linux, and has Leiden built in (`Graph.community_leiden(objective_function="modularity", weights=…, resolution=…, n_iterations=…)`; `leidenalg` is not needed). igraph draws randomness from Python's `random` module, so `random.seed(seed)` makes it reproducible.

**Files:**
- Create: `pipeline/atlas/graph_cluster.py`, `pipeline/tests/test_graph_cluster.py`
- Modify: `pipeline/atlas/cluster.py` (`fit_labels`), `pipeline/pyproject.toml` + lock

**Interfaces:**
- Consumes: `fit_labels` (Task 4), config `clustering.algorithm`, `clustering.leiden.*` (Task 1).
- Produces: `atlas.graph_cluster.has_igraph() -> bool`, `knn_edges(emb, k, chunk=2048) -> (edges[m,2] with i<j, weights[m])`, `leiden_labels(emb, lcfg, seed) -> labels` (communities < `min_cluster_size` → −1).

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_graph_cluster.py`:

```python
import numpy as np
import pytest

from atlas.cluster import fit_labels
from atlas.config import load_config
from atlas.graph_cluster import has_igraph, knn_edges

CCFG = load_config(None)["clustering"]


def _blobs(k=5, n_per=60, seed=0):
    rng = np.random.default_rng(seed)
    X = np.vstack([np.eye(32)[c] + rng.normal(0, 0.05, (n_per, 32)) for c in range(k)])
    return (X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32), np.repeat(np.arange(k), n_per)


def test_knn_edges_are_undirected_unique_and_without_self_loops():
    X, _ = _blobs(k=2, n_per=10)
    edges, w = knn_edges(X, k=3)
    assert (edges[:, 0] < edges[:, 1]).all()
    assert len({tuple(e) for e in edges.tolist()}) == len(edges)
    assert len(w) == len(edges) and (w >= 0).all()


@pytest.mark.skipif(not has_igraph(), reason="optional extra: uv sync --extra leiden")
def test_leiden_recovers_blobs_and_is_reproducible():
    from sklearn.metrics import adjusted_rand_score

    X, y = _blobs()
    ccfg = {**CCFG, "algorithm": "leiden", "leiden": {**CCFG["leiden"], "k": 10, "min_cluster_size": 20}}
    a, n_raw = fit_labels(X, ccfg, seed=1)
    b, _ = fit_labels(X, ccfg, seed=1)
    assert n_raw >= 5 and adjusted_rand_score(y, a) > 0.95 and (a == b).all()


@pytest.mark.skipif(not has_igraph(), reason="optional extra: uv sync --extra leiden")
def test_leiden_small_communities_become_unassigned():
    from atlas.graph_cluster import leiden_labels

    X, _ = _blobs(k=3, n_per=30)
    labels = leiden_labels(X, {**CCFG["leiden"], "k": 8, "min_cluster_size": 1000}, seed=0)
    assert (labels == -1).all()
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_graph_cluster.py -q` → FAIL: `ModuleNotFoundError: No module named 'atlas.graph_cluster'`.

- [ ] **Step 3: Create `pipeline/atlas/graph_cluster.py`**

```python
"""Leiden community detection on a kNN graph of the embeddings (the CWTS/OpenAlex style alternative
to UMAP→HDBSCAN). Optional dependency: `uv sync --extra leiden` (python-igraph; wheels for Windows,
macOS and Linux). igraph's built-in Leiden is used (no separate leidenalg package).

Graph: each article links to its k most similar articles (cosine), weight = cosine; the graph is
made undirected (an edge kept once, maximum weight). Modularity Leiden with `resolution`;
communities smaller than min_cluster_size become −1 (unassigned), like HDBSCAN noise. Python's
`random` module drives igraph's RNG, so seeding it makes runs reproducible.
"""
from __future__ import annotations

import random

import numpy as np


def has_igraph() -> bool:
    try:
        import igraph  # noqa: F401
    except ImportError:
        return False
    return True


def knn_edges(emb: np.ndarray, k: int, chunk: int = 2048) -> tuple[np.ndarray, np.ndarray]:
    """→ (edges [m, 2] with i < j, weights [m]) of the symmetrised kNN graph."""
    n = len(emb)
    k = max(1, min(k, n - 1))
    src, dst, w = [], [], []
    for s in range(0, n, chunk):
        sim = emb[s:s + chunk] @ emb.T
        rows = np.arange(s, min(s + chunk, n))
        sim[np.arange(len(rows)), rows] = -np.inf                     # no self loops
        idx = np.argpartition(-sim, k - 1, axis=1)[:, :k]
        src.append(np.repeat(rows, k))
        dst.append(idx.ravel())
        w.append(np.take_along_axis(sim, idx, axis=1).ravel())
    a, b, wt = np.concatenate(src), np.concatenate(dst), np.concatenate(w)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    key = lo.astype(np.int64) * n + hi
    order = np.lexsort((-wt, key))                                    # per pair, keep the largest weight
    key, lo, hi, wt = key[order], lo[order], hi[order], wt[order]
    first = np.r_[True, key[1:] != key[:-1]]
    return np.stack([lo[first], hi[first]], axis=1), np.maximum(wt[first], 0.0)


def leiden_labels(emb: np.ndarray, lcfg: dict, seed: int) -> np.ndarray:
    import igraph as ig  # optional dependency

    if len(emb) < 3:
        return np.zeros(len(emb), dtype=int)
    edges, weights = knn_edges(emb, int(lcfg["k"]))
    g = ig.Graph(n=len(emb), edges=edges.tolist(), directed=False)
    random.seed(seed)
    part = g.community_leiden(objective_function="modularity", weights=weights.tolist(),
                              resolution=float(lcfg["resolution"]), n_iterations=int(lcfg["n_iterations"]))
    labels = np.asarray(part.membership, dtype=int)
    sizes = np.bincount(labels)
    labels[sizes[labels] < int(lcfg["min_cluster_size"])] = -1
    return labels
```

- [ ] **Step 4: Edit `fit_labels` in `pipeline/atlas/cluster.py`**

Replace
```python
    """Cluster from scratch → (labels 0..k−1 by size, −1 = unassigned; raw cluster count)."""
    raw = hdbscan_labels(reduce_embeddings(emb, ccfg, seed), ccfg["fine"], ccfg["hdbscan_backend"])
```
with
```python
    """Cluster from scratch → (labels 0..k−1 by size, −1 = unassigned; raw cluster count)."""
    if ccfg["algorithm"] == "leiden":
        from atlas.graph_cluster import leiden_labels  # optional extra: uv sync --extra leiden

        raw = leiden_labels(emb, ccfg["leiden"], seed)
    else:
        raw = hdbscan_labels(reduce_embeddings(emb, ccfg, seed), ccfg["fine"], ccfg["hdbscan_backend"])
```

- [ ] **Step 5: Optional dependency** — `uv add --optional leiden "igraph>=1.0"`, `uv sync --extra leiden`, regenerate `requirements.txt`.

- [ ] **Step 6: Run tests** — `uv run ruff check . && uv run pytest -q` → all pass (3 Leiden tests pass with the extra, 2 skip without it).

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/graph_cluster.py pipeline/atlas/cluster.py pipeline/tests/test_graph_cluster.py pipeline/pyproject.toml pipeline/uv.lock pipeline/requirements.txt
git commit -m "feat(cluster): optional Leiden on a kNN graph (igraph) as clustering.algorithm

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

<!-- APPEND -->

### Task 6: Label v2 — labeling through the LLM runner, prompt from `prompts/topic_label.th.md`, editor overrides by stable topic id

The embedded `PROMPT_TEMPLATE` copy in `label.py` is removed; the prompt file is the only copy. Labels now carry `label_source` (`llm` | `keywords` | `override`). Editors fix names in a CSV keyed by the stable topic id (`T000123`, Task 4), and the fix wins every quarter. The P0 `state/label_cache.parquet` is not read any more: its key had no prompt version, so the first P1 run labels every topic once more through the new cache (`state/llm_cache/label.jsonl`); delete the old file after that run.

**Files:**
- Modify: `pipeline/atlas/label.py` (full replacement), `pipeline/tests/test_label.py` (full replacement — the P0 OpenAI-client fakes go away), `pipeline/atlas/llm_runner.py` (`JOBS`), `pipeline/atlas/config.py`, `pipeline/config.example.yaml`, `prompts/topic_label.th.md` (header notes only — the template is unchanged), `.gitignore`

**Interfaces:**
- Consumes: `run_job`, `LlmItem`, `LlmJob`, `JOBS` (Task 3); `load_prompt`, `render_prompt`, `prompt_version`; `topic_code` (Task 4); `load_aligned` (Task 2).
- Produces:
  - `atlas.label`: `PROMPT_NAME`, `LabelOut` (pydantic: `name_th`, `name_en` non-blank, `description`, `keywords: list[str]`), `representative_indices` (unchanged), `topic_titles(cfg, n=None) -> {topic_id: [titles]}` (MMR around the centroid; reused by Tasks 7 and 14), `label_job(cfg) -> LlmJob` (item key = `T%06d`), `load_overrides(path) -> DataFrame[topic_id:int, name_th, name_en, description, reviewer, reviewed_at, note]`, `label(cfg, llm=None) -> DataFrame`.
  - `work/05_labels` gains `label_source`; `cache_key` = the LLM cache key, or `"fallback"` (so P0's manifest count `n_labels_fallback` keeps working); `work/05_labels_meta.json` = `{provider, model_id, topics, from_cache, generated, repaired, fallback, overrides, unknown_overrides, cost_usd}`; an LLM stop (`atlas llm-stop`, Ctrl-C, budget) raises `jobs.RunStopped` out of the step, so no half-labelled `05_labels` is ever written.
  - Config: `labeling.provider ∈ {llm, off}` (`api` and YAML `false` accepted as aliases), `labeling.overrides_path` (default `None`; the example config points at `./registry/label_overrides.csv`, resolved against the config file's folder). `labeling.api.*` is removed (its settings live in `llm.endpoints` / `llm.tasks.label`).
  - Overrides CSV (UTF-8, BOM allowed — Excel): `topic_id,name_th,name_en,description,reviewer,reviewed_at,note`; empty cells keep the generated value.

- [ ] **Step 1: Write the failing tests** — replace `pipeline/tests/test_label.py` with:

```python
import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.label import label, label_job, load_overrides, representative_indices
from atlas.llm import Reply


class FakeLLM:
    """Stands in for OpenAICompatLLM: .model_id + .chat(messages) -> Reply; reply_fn(prompt, n) → text."""

    model_id = "fake-model"

    def __init__(self, reply_fn=None):
        self.calls = 0
        self.reply_fn = reply_fn or (lambda prompt, n: json.dumps(
            {"name_th": f"หัวข้อ {n}", "name_en": f"Topic {n}", "description": "d", "keywords": ["a", "b"]},
            ensure_ascii=False))

    def chat(self, messages):
        self.calls += 1
        return Reply(self.reply_fn(messages[0]["content"], self.calls), 0, 0, 0.0)


VALID = json.dumps({"name_th": "ข้าวไทย", "name_en": "Thai rice", "description": "d", "keywords": ["ข้าว", "rice"]},
                   ensure_ascii=False)


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


def _llm_cfg(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["labeling"]["provider"] = "llm"
    cfg["pipeline"]["release"] = "2026Q4"
    return cfg


def _meta(cfg):
    return json.loads((Path(cfg["pipeline"]["work_dir"]) / "05_labels_meta.json").read_text(encoding="utf-8"))


def test_representative_indices_central_then_diverse():
    c = np.array([1.0, 0.0, 0.0])
    m = np.array([[1, 0, 0], [0.999, 0.045, 0], [0.9, 0, 0.436]], dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    # λ=0.3 favours diversity: the near-duplicate of the first pick (row 1) loses to row 2
    assert representative_indices(m, c, 2, lam=0.3) == [0, 2]


def test_fallback_labels_use_author_keywords(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    _workdir(cfg, {1: ["ก", "ข"]})
    info = read_table(f"{cfg['pipeline']['work_dir']}/04_topic_info.parquet")
    info["top_keywords"] = "ผู้สูงอายุ; การดูแลระยะยาว; older adults"
    write_table(info, f"{cfg['pipeline']['work_dir']}/04_topic_info.parquet")
    out = label(cfg)
    assert out.loc[0, "name_th"] == "ผู้สูงอายุ / การดูแลระยะยาว"
    assert out.loc[0, "name_en"] == "older adults" and out.loc[0, "label_source"] == "keywords"


def test_prompt_comes_from_the_prompt_file_with_titles(make_cfg, tmp_path):
    cfg = _llm_cfg(make_cfg, tmp_path)
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"]})
    job = label_job(cfg)
    assert job.task == "label" and [it.key for it in job.items] == ["T000001"]
    p = job.items[0].prompt
    assert "- เรื่องข้าว 1" in p and "{titles}" not in p and "c-TF-IDF" in p


def test_llm_labels_cached_by_prompt_content(make_cfg, tmp_path):
    cfg = _llm_cfg(make_cfg, tmp_path)
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 2: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})
    first = FakeLLM()
    out = label(cfg, llm=first)
    assert first.calls == 2 and (out["label_source"] == "llm").all() and (out["cache_key"] != "fallback").all()
    second = FakeLLM()
    label(cfg, llm=second)
    assert second.calls == 0                                   # nothing changed → all from the LLM cache
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 2: ["หัวข้อใหม่ทั้งหมด 1", "หัวข้อใหม่ทั้งหมด 2"]})
    third = FakeLLM()
    out = label(cfg, llm=third)
    assert third.calls == 1                                    # only the topic whose members changed
    assert set(out["topic_id"]) == {1, 2} and _meta(cfg)["from_cache"] == 1


def test_invalid_replies_fall_back_and_are_retried_next_run(make_cfg, tmp_path):
    cfg = _llm_cfg(make_cfg, tmp_path)
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 2: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})
    blank = json.dumps({"name_th": " ", "name_en": "", "description": "d", "keywords": []})
    llm = FakeLLM(lambda p, n: blank if "เบาหวาน" in p else VALID)
    out = label(cfg, llm=llm).set_index("topic_id")
    assert llm.calls == 1 + 3                                  # topic 2: first try + 2 repair turns
    assert out.loc[1, "label_source"] == "llm" and out.loc[2, "cache_key"] == "fallback"
    assert out.loc[2, "label_source"] == "keywords" and out.loc[2, "name_en"] == "rice"
    assert _meta(cfg)["fallback"] == 1
    rerun = FakeLLM(lambda p, n: VALID)
    out = label(cfg, llm=rerun)
    assert rerun.calls == 1 and (out["cache_key"] != "fallback").all()


def test_editor_overrides_win_and_unknown_ids_are_reported(make_cfg, tmp_path):
    cfg = _llm_cfg(make_cfg, tmp_path)
    _workdir(cfg, {1: ["เรื่องข้าว 1", "เรื่องข้าว 2"], 2: ["เรื่องเบาหวาน 1", "เรื่องเบาหวาน 2"]})
    path = tmp_path / "registry" / "label_overrides.csv"
    path.parent.mkdir()
    path.write_text("topic_id,name_th,name_en,description,reviewer,reviewed_at,note\n"
                    "T000002,เบาหวานในผู้สูงอายุ,,,บก. ก,2026-10-01,\nT000099,หายไปแล้ว,Gone,,,,\n",
                    encoding="utf-8-sig")                     # Excel saves CSV with a BOM
    cfg["labeling"]["overrides_path"] = str(path)
    assert load_overrides(path)["topic_id"].tolist() == [2, 99]
    out = label(cfg, llm=FakeLLM(lambda p, n: VALID)).set_index("topic_id")
    assert out.loc[2, "name_th"] == "เบาหวานในผู้สูงอายุ" and out.loc[2, "name_en"] == "Thai rice"
    assert out.loc[2, "label_source"] == "override" and out.loc[1, "label_source"] == "llm"
    meta = _meta(cfg)
    assert meta["overrides"] == 1 and meta["unknown_overrides"] == ["T000099"]
    cfg["labeling"]["provider"] = "off"                        # overrides apply without an LLM too
    assert label(cfg).set_index("topic_id").loc[2, "name_th"] == "เบาหวานในผู้สูงอายุ"


def test_yaml_provider_aliases(tmp_path):
    from atlas.config import load_config

    p = tmp_path / "c.yaml"
    p.write_text("labeling:\n  provider: off\n", encoding="utf-8")       # bare off = YAML false
    assert load_config(p)["labeling"]["provider"] == "off"
    p.write_text("labeling:\n  provider: api\n  overrides_path: registry/o.csv\n", encoding="utf-8")  # P0 name
    cfg = load_config(p)
    assert cfg["labeling"]["provider"] == "llm"
    assert Path(cfg["labeling"]["overrides_path"]) == (tmp_path / "registry" / "o.csv").resolve()
    assert load_config(None)["labeling"]["overrides_path"] is None    # tests never read a real overrides file
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_label.py -q`
Expected: FAIL — `ImportError: cannot import name 'label_job' from 'atlas.label'`.

- [ ] **Step 3: Replace `pipeline/atlas/label.py`** (the P0 behaviours kept: MMR titles, blank names rejected, failed topics not cached and retried next run, keyword fallback)

```python
"""Topic labeling (topic-level LLM task "label").

labeling.provider = llm: author keywords + c-TF-IDF words + representative titles (nearest to the
centroid, diversified with MMR) → prompts/topic_label.th.md → the LLM runner (atlas/llm_runner.py:
cache keyed by model + prompt version + prompt, JSON repairs, keyword fallback, budget, stop).
labeling.provider = off: names from the topic's most distinctive author keywords (TH and EN).
Either way the editors' file labeling.overrides_path (CSV keyed by the stable topic id T000123)
wins, so corrections stick across quarters.

Outputs: work/05_labels (level, topic_id, name_th, name_en, description, keywords, cache_key,
label_source ∈ llm | keywords | override) and work/05_labels_meta.json (counts + LLM spend).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel, field_validator

from atlas.checkpoints import load_aligned
from atlas.io_utils import read_table, write_table
from atlas.lineage import topic_code
from atlas.llm_runner import LlmItem, LlmJob, run_job
from atlas.prompts import load_prompt, prompt_version, render_prompt
from atlas.thai import thai_ratio

PROMPT_NAME = "topic_label.th"
LABEL_COLUMNS = ["level", "topic_id", "name_th", "name_en", "description", "keywords", "cache_key", "label_source"]
OVERRIDE_COLUMNS = ["topic_id", "name_th", "name_en", "description", "reviewer", "reviewed_at", "note"]


class LabelOut(BaseModel):
    name_th: str
    name_en: str
    description: str = ""
    keywords: list[str] = []

    @field_validator("name_th", "name_en")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name_th and name_en must not be blank")
        return v.strip()


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


def topic_titles(cfg: dict, n: int | None = None) -> dict[int, list[str]]:
    """{topic_id: representative titles (MMR around the centroid)} — shared by label, merge, narrative, review."""
    work, lcfg = Path(cfg["pipeline"]["work_dir"]), cfg["labeling"]
    df, emb = load_aligned(work)
    labels = (df[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id", how="left")
              ["fine_topic"].fillna(-1).astype(int).to_numpy())
    C = np.load(work / "04_centroids.npy")
    ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    n = int(lcfg["n_repr_docs"]) if n is None else n
    out = {}
    for i, tid in enumerate(ids):
        members = np.where(labels == tid)[0]
        if len(members) == 0 or n == 0:
            out[int(tid)] = []
            continue
        idx = representative_indices(emb[members], C[i], n, float(lcfg["mmr_lambda"]))
        out[int(tid)] = df["title"].iloc[members[idx]].fillna("").astype(str).tolist()
    return out


def _fallback(top_keywords: str, top_terms: str, tid: int) -> dict:
    kws = [k for k in str(top_keywords).split("; ") if k]
    terms = [t for t in str(top_terms).split("; ") if t]
    th = [k for k in kws if thai_ratio(k) > 0.5][:2] or [t for t in terms if thai_ratio(t) > 0.5][:3]
    en = [k for k in kws if thai_ratio(k) <= 0.5][:2] or [t for t in terms if thai_ratio(t) <= 0.5][:3]
    return {"name_th": " / ".join(th) or f"หัวข้อ {tid}", "name_en": " / ".join(en) or f"Topic {tid}",
            "description": "", "keywords": kws[:6]}


def label_job(cfg: dict) -> LlmJob:
    """One LLM item per topic (registered in llm_runner.JOBS for `atlas llm --dry-run`)."""
    work = Path(cfg["pipeline"]["work_dir"])
    info = read_table(work / "04_topic_info.parquet")
    template = load_prompt(PROMPT_NAME, cfg["llm"]["prompts_dir"])
    titles = topic_titles(cfg)
    items = []
    for r in info.itertuples():
        tid = int(r.topic_id)
        prompt = render_prompt(template, keywords=r.top_keywords, terms=r.top_terms,
                               titles="\n".join(f"- {t}" for t in titles.get(tid, [])))
        items.append(LlmItem(topic_code(tid), prompt, _fallback(r.top_keywords, r.top_terms, tid)))
    return LlmJob("label", LabelOut, prompt_version(template), items)


def load_overrides(path: str | Path | None) -> pd.DataFrame:
    """Editors' corrections (CSV, UTF-8 with or without BOM): topic_id (T000123 or 123), name_th, name_en, …"""
    if not path or not Path(path).exists():
        return pd.DataFrame(columns=OVERRIDE_COLUMNS)
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    missing = {"topic_id", "name_th", "name_en"} - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    for c in OVERRIDE_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df["topic_id"] = df["topic_id"].str.strip().str.lstrip("Tt").astype(int)
    return df[OVERRIDE_COLUMNS].drop_duplicates("topic_id", keep="last")


def label(cfg: dict, llm=None) -> pd.DataFrame:
    """llm: an object with .model_id and .chat(messages) (tests); None → the configured endpoint, if needed."""
    work = Path(cfg["pipeline"]["work_dir"])
    info = read_table(work / "04_topic_info.parquet")
    provider = cfg["labeling"]["provider"]
    rows, stats = [], {"from_cache": 0, "generated": 0, "repaired": 0, "fallback": 0, "cost_usd": 0.0, "model": ""}
    if provider == "llm":
        job = label_job(cfg)
        results, stats = run_job(cfg, job, llm)
        for r in info.itertuples():
            code = topic_code(int(r.topic_id))
            res = results[code]
            out = res.output
            kws = out.get("keywords", [])
            rows.append({"level": "fine", "topic_id": int(r.topic_id), "name_th": out["name_th"],
                         "name_en": out["name_en"], "description": out.get("description", ""),
                         "keywords": "; ".join(kws) if isinstance(kws, list) else str(kws),
                         "cache_key": res.key or "fallback",
                         "label_source": "llm" if res.source != "fallback" else "keywords"})
    else:
        for r in info.itertuples():
            fb = _fallback(r.top_keywords, r.top_terms, int(r.topic_id))
            rows.append({"level": "fine", "topic_id": int(r.topic_id), **fb, "keywords": "; ".join(fb["keywords"]),
                         "cache_key": "fallback", "label_source": "keywords"})
    out = pd.DataFrame(rows, columns=LABEL_COLUMNS)

    ov = load_overrides(cfg["labeling"]["overrides_path"])
    known = set(out["topic_id"])
    unknown = sorted(topic_code(t) for t in set(ov["topic_id"]) - known)
    applied = 0
    for o in ov[ov["topic_id"].isin(known)].itertuples():
        i = out.index[out["topic_id"] == o.topic_id][0]
        changed = False
        for col in ("name_th", "name_en", "description"):
            if str(getattr(o, col)).strip():
                out.loc[i, col] = str(getattr(o, col)).strip()
                changed = True
        if changed:
            out.loc[i, "label_source"] = "override"
            applied += 1
    if unknown:
        print(f"[label] WARNING: {len(unknown)} overrides name topics that no longer exist: {', '.join(unknown[:10])}")
    write_table(out, work / "05_labels.parquet")
    meta = {"provider": provider, "model_id": stats["model"], "topics": len(out),
            "from_cache": stats["from_cache"], "generated": stats["generated"], "repaired": stats["repaired"],
            "fallback": int((out["cache_key"] == "fallback").sum()) if provider == "llm" else 0,
            "overrides": applied, "unknown_overrides": unknown, "cost_usd": stats["cost_usd"]}
    (work / "05_labels_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[label] {len(out)} topics: {meta['generated']} new, {meta['from_cache']} cached, "
          f"{meta['fallback']} keyword fallback, {applied} editor overrides")
    return out
```

- [ ] **Step 4: Register the job** in `pipeline/atlas/llm_runner.py`:

Replace
```python
JOBS: dict[str, str] = {}
```
with
```python
JOBS: dict[str, str] = {"label": "atlas.label:label_job"}
```

- [ ] **Step 5: Config** — in `pipeline/atlas/config.py`:

Replace
```python
from pydantic import BaseModel, ConfigDict, Field, model_validator
```
with
```python
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
```
Replace
```python
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
```
with
```python
class LabelingCfg(_Strict):
    provider: Literal["llm", "off"] = "off"
    overrides_path: str | None = None     # editors' CSV keyed by T000123; the example config sets ./registry/…
    n_repr_docs: int = 8
    mmr_lambda: float = Field(0.7, ge=0.0, le=1.0)

    @field_validator("provider", mode="before")
    @classmethod
    def _provider_alias(cls, v):
        if v is False:                    # YAML reads a bare `off` as boolean false
            return "off"
        return "llm" if v == "api" else v     # P0 name
```
Replace
```python
    if cfg["llm"]["prompts_dir"]:
```
with
```python
    if cfg["labeling"]["overrides_path"]:
        cfg["labeling"]["overrides_path"] = _resolve(cfg["labeling"]["overrides_path"], base)
    if cfg["llm"]["prompts_dir"]:
```

In `pipeline/config.example.yaml`:
Replace
```yaml
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
```
with
```yaml
labeling:
  provider: "off"             # llm | "off" (ต้องใส่เครื่องหมายคำพูด — YAML อ่าน off เปล่า ๆ เป็น false) — llm = ตั้งชื่อด้วย llm.tasks.label; off = จากคำสำคัญของผู้เขียน + c-TF-IDF
  overrides_path: ./registry/label_overrides.csv   # ชื่อที่บรรณาธิการแก้ (topic_id แบบ T000123) — ชนะชื่อจาก LLM ทุกรอบ; ไม่มีไฟล์ = ไม่มีการแก้
  n_repr_docs: 8              # บทความตัวแทน (ใกล้ centroid + กระจายด้วย MMR)
```

- [ ] **Step 6: Prompt file notes** — the template block stays byte-identical; only the notes change (`prompt_version` hashes the template, so this costs nothing):

Replace
```markdown
> **สถานะ: ใช้งานจริง** — สำเนาฝังอยู่ใน `pipeline/atlas/label.py` (ตัวแปร `PROMPT_TEMPLATE`)
> แก้ไฟล์นี้แล้วต้อง sync กลับเข้าโค้ดด้วย (และในทางกลับกัน) — การเปลี่ยน prompt เปลี่ยน `cache_key` (hash ของ model + prompt) → label ทุก topic จะถูกสร้างใหม่ในรอบถัดไป (จ่ายค่า API อีกครั้ง)
```
with
```markdown
> **สถานะ: ใช้งานจริง — ไฟล์นี้คือต้นฉบับเดียว** `pipeline/atlas/label.py` อ่าน block ใต้ "Prompt (master)" ตอนรัน (ไม่มีสำเนาในโค้ด)
> แก้ข้อความใน block = `prompt_version` เปลี่ยน → ทุก topic ถูกตั้งชื่อใหม่ในรอบถัดไป (จ่ายค่า API อีกครั้ง); แก้หมายเหตุนอก block ไม่มีผลต่อ cache
```
Replace
```markdown
- cache key = sha256(model + prompt) (ตัดเหลือ 16 hex) เก็บใน `state/label_cache.parquet` — เปลี่ยน prompt หรือ model หรือ members ของ topic → label ถูกสร้างใหม่เฉพาะ topic นั้น
- ผลที่คาด: **JSON เท่านั้น** ตาม schema — โค้ด parse ด้วย `json.loads` + ตัด markdown fence ออก
```
with
```markdown
- cache key = sha256(model + prompt_version + prompt ที่เติมค่าแล้ว) (16 hex) เก็บใน `state/llm_cache/label.jsonl` — เปลี่ยน template หรือ model หรือ members ของ topic → label ถูกสร้างใหม่เฉพาะ topic นั้น
- ผลที่คาด: **JSON เท่านั้น** ตาม schema — โค้ดตัด markdown fence แล้วตรวจด้วย pydantic (`LabelOut`); ผิดรูปแบบ → ขอให้แก้ ≤ `llm.max_repairs` ครั้ง → ไม่ได้ก็ใช้ชื่อจากคำสำคัญ (ไม่ cache — รอบหน้าลองใหม่)
- ชื่อที่บรรณาธิการแก้ใน `labeling.overrides_path` (topic_id แบบ T000123) ชนะผลของ prompt นี้เสมอ
```

- [ ] **Step 7: Keep the editors' file out of the public repo** — append to `.gitignore`:

```text
# editors' label corrections (real topic names) — back up with pipeline/state/, never commit
pipeline/registry/
```

- [ ] **Step 8: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_label.py tests/test_llm.py -q && uv run pytest -q`
Expected: all pass. (`tests/test_export.py` builds its own 05_labels without `label_source`; P0 export does not read the column.)

- [ ] **Step 9: Commit** — the prompt's location of truth changed; say so (CLAUDE.md rule):

```bash
git add pipeline/atlas/label.py pipeline/atlas/llm_runner.py pipeline/atlas/config.py pipeline/config.example.yaml pipeline/tests/test_label.py prompts/topic_label.th.md .gitignore
git commit -m "feat(label): labels through the LLM runner, editor overrides by stable topic id

Prompt text now lives only in prompts/topic_label.th.md (template unchanged; the copy in label.py is gone).
The P0 label cache is superseded by state/llm_cache/label.jsonl (one-time relabel).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 7: Merge suggestions (LLM task `merge`) + `atlas review export|import` (editors' 50-topic spot check)

Near-duplicate topics are flagged, never merged automatically (a merge changes stable ids; a wrong one distorts the map). Each quarter an editor gets a CSV of 50 topics — every keyword-fallback label and every possible duplicate first, then a seeded random draw — and the corrected names flow into the overrides file of Task 6.

**Files:**
- Create: `pipeline/atlas/review.py`, `pipeline/tests/test_review.py`
- Modify: `prompts/topic_merge.th.md` (rewritten for fine-topic pairs, JSON output), `pipeline/atlas/label.py` (call `suggest_merges`), `pipeline/atlas/llm_runner.py` (`JOBS`), `pipeline/atlas/config.py`, `pipeline/config.example.yaml`, `pipeline/atlas/cli.py`

**Interfaces:**
- Consumes: `topic_titles`, `load_overrides`, `OVERRIDE_COLUMNS` (Task 6); `run_job`/`LlmJob` (Task 3); `topic_code`; `current_release`.
- Produces:
  - `atlas.review`: `MergeOut` (`same_topic: bool`, `reason: str`), `merge_candidates(cfg) -> [(topic_a, topic_b, cosine)]`, `merge_job(cfg) -> LlmJob` (item key `"T000001|T000002"`), `suggest_merges(cfg, llm=None) -> DataFrame` → `work/05_merge_suggestions` (`topic_a, topic_b, similarity, same_topic (True/False/None), reason, source ∈ {llm, fallback, similarity}`), `export_review(cfg, out=None, n=None) -> Path`, `import_review(cfg, path) -> {applied, reviewed, overrides_total, path}`.
  - Review CSV columns: `topic_id, name_th, name_en, label_source, size, status, keywords, sample_titles, possible_duplicate, why_in_sample (fallback|duplicate|random), ok, name_th_fixed, name_en_fixed, reviewer, note` — UTF-8 with BOM (Excel shows Thai), default path `output/review/<release>_label_review.csv`.
  - Config: `labeling.merge.{enabled, min_similarity, max_pairs}`, `review.{sample_size, n_titles}`. The LLM is asked only when `labeling.provider: llm` and `llm.tasks.merge.model` is set; otherwise the pairs are listed by similarity.
  - CLI: `atlas review export -c CFG [--out PATH] [--n N]`, `atlas review import FILE -c CFG`.

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_review.py`:

```python
import json
from pathlib import Path

import numpy as np
import pandas as pd
from typer.testing import CliRunner

from atlas.cli import app
from atlas.io_utils import read_table, write_table
from atlas.label import label
from atlas.llm import Reply
from atlas.review import export_review, import_review, merge_candidates, suggest_merges


class FakeLLM:
    model_id = "fake-merge"

    def __init__(self, text):
        self.text, self.prompts = text, []

    def chat(self, messages):
        self.prompts.append(messages[0]["content"])
        return Reply(self.text, 0, 0, 0.0)


def _work(cfg, n_topics=6, per=4):
    """Topics 1 and 2 point the same way (near-duplicates); the others are orthogonal."""
    work = Path(cfg["pipeline"]["work_dir"])
    rng = np.random.default_rng(0)
    rows, emb, labels = [], [], []
    for t in range(1, n_topics + 1):
        axis = 0 if t in (1, 2) else t
        for i in range(per):
            v = np.eye(16)[axis] + rng.normal(0, 0.01, 16)
            emb.append(v / np.linalg.norm(v))
            rows.append({"article_id": f"a{len(rows)}", "title": f"เรื่องที่ {t}-{i}", "doc_text": "x"})
            labels.append(t)
    emb, labels = np.array(emb, dtype=np.float32), np.array(labels)
    ids = list(range(1, n_topics + 1))
    C = np.stack([emb[labels == t].mean(0) for t in ids])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", emb)
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows], "fine_topic": labels}),
                work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"level": "fine", "topic_id": ids, "size": per, "top_terms": "ข้าว; rice",
                              "top_keywords": [f"คำ{t}; word{t}" for t in ids], "coarse_topic": 0, "coherence": 0.9}),
                work / "04_topic_info.parquet")
    np.save(work / "04_centroids.npy", C)
    (work / "04_centroid_ids.json").write_text(json.dumps(ids), encoding="utf-8")
    return work


def test_near_duplicate_pairs_go_to_the_llm_and_nothing_is_merged(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q4"
    work = _work(cfg)
    label(cfg)                                                    # provider off → keyword names
    assert [(a, b) for a, b, _ in merge_candidates(cfg)] == [(1, 2)]
    sugg = read_table(work / "05_merge_suggestions.parquet")      # the label step wrote similarity-only rows
    assert sugg["source"].tolist() == ["similarity"] and sugg["same_topic"].isna().all()
    fake = FakeLLM('{"same_topic": true, "reason": "คำถามวิจัยเดียวกัน"}')
    out = suggest_merges(cfg, llm=fake)
    assert out[["topic_a", "topic_b", "same_topic", "source"]].values.tolist() == [[1, 2, True, "llm"]]
    assert "คำ1; word1" in fake.prompts[0] and "เรื่องที่ 2-" in fake.prompts[0]
    assert sorted(read_table(work / "05_labels.parquet")["topic_id"]) == [1, 2, 3, 4, 5, 6]


def test_review_export_samples_flagged_topics_first_and_import_writes_overrides(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q4"
    cfg["review"]["sample_size"] = 4
    cfg["labeling"]["overrides_path"] = str(tmp_path / "registry" / "label_overrides.csv")
    _work(cfg)
    label(cfg)
    path = export_review(cfg)
    assert path.name == "2026Q4_label_review.csv" and path.read_bytes()[:3] == b"\xef\xbb\xbf"   # BOM for Excel
    rev = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    assert len(rev) == 4 and {"T000001", "T000002"} <= set(rev["topic_id"])
    assert rev.set_index("topic_id").loc["T000001", "possible_duplicate"].startswith("T000002")
    assert export_review(cfg).read_bytes() == path.read_bytes()                       # reproducible sample
    code = rev.loc[rev["why_in_sample"] == "random", "topic_id"].iloc[0]
    rev.loc[rev["topic_id"] == code, ["name_th_fixed", "reviewer"]] = ["ชื่อที่แก้แล้ว", "บก. ข"]
    rev.to_csv(path, index=False, encoding="utf-8-sig")
    r = import_review(cfg, path)
    assert (r["applied"], r["overrides_total"]) == (1, 1)
    out = label(cfg).set_index("topic_id")
    tid = int(code[1:])
    assert out.loc[tid, "name_th"] == "ชื่อที่แก้แล้ว" and out.loc[tid, "label_source"] == "override"
    rev2 = pd.read_csv(export_review(cfg), dtype=str, encoding="utf-8-sig")
    assert code not in set(rev2["topic_id"])                      # already fixed → not drawn again


def test_review_cli_export(make_cfg, tmp_path):
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(f"pipeline:\n  work_dir: {(tmp_path / 'work').as_posix()}\n"
                        f"  output_dir: {(tmp_path / 'out').as_posix()}\n  release: 2026Q4\n", encoding="utf-8")
    cfg = make_cfg(tmp_path)
    _work(cfg)
    label(cfg)
    r = CliRunner().invoke(app, ["review", "export", "-c", str(cfg_path)])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "out" / "review" / "2026Q4_label_review.csv").exists()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_review.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.review'`.

- [ ] **Step 3: Rewrite `prompts/topic_merge.th.md`** (P0's version was a never-implemented coarse-group design; this is the pair check the code uses):

````markdown
# Prompt: ตรวจคู่หัวข้อที่อาจซ้ำกัน (topic merge check)

> **สถานะ: ใช้งานจริง — ไฟล์นี้คือต้นฉบับเดียว** `pipeline/atlas/review.py` อ่าน block ใต้ "Prompt (master)" ตอนรัน (งาน LLM `merge`)
> แก้ข้อความใน block = `prompt_version` เปลี่ยน → คู่หัวข้อถูกถามใหม่ในรอบถัดไป; แก้หมายเหตุนอก block ไม่มีผลต่อ cache

## บริบทการใช้

- คู่หัวข้อ (fine topic) ที่ centroid ใกล้กันมาก (cosine ≥ `labeling.merge.min_similarity`, ไม่เกิน `labeling.merge.max_pairs` คู่) ถูกส่งมาทีละคู่ — 1 call ต่อคู่
- inputs: `{name_a}`/`{name_b}` = ชื่อไทย (อังกฤษ), `{keywords_a}`/`{keywords_b}` = คำสำคัญของผู้เขียน (คั่นด้วย "; "), `{titles_a}`/`{titles_b}` = ชื่อบทความตัวแทน (บรรทัดละ 1 เรื่อง)
- ผลเป็น **ข้อเสนอ** เท่านั้น → `work/05_merge_suggestions` → คอลัมน์ `possible_duplicate` ใน `atlas review export` — **ไม่รวมอัตโนมัติ** (ID หัวข้อถาวรจะเปลี่ยน และการรวมผิดทำให้แผนที่เพี้ยนทั้งใบ)
- ตรวจด้วย pydantic (`MergeOut`: `same_topic` bool, `reason` str); ผิดรูปแบบ → ขอให้แก้ ≤ `llm.max_repairs` ครั้ง → ไม่ได้ก็แสดงเป็น "ไม่ทราบ" ให้คนดู

## Prompt (master)

```
คุณคือบรรณาธิการวารสารวิชาการไทย ระบบจัดกลุ่มอัตโนมัติพบว่าหัวข้อวิจัยสองหัวข้อนี้มีเนื้อหาใกล้กันมาก
ช่วยตัดสินว่าเป็น "หัวข้อเดียวกัน" (ควรรวม) หรือ "คนละหัวข้อ" (ควรแยกไว้)

หัวข้อ A: {name_a}
คำสำคัญ: {keywords_a}
ตัวอย่างชื่อบทความ:
{titles_a}

หัวข้อ B: {name_b}
คำสำคัญ: {keywords_b}
ตัวอย่างชื่อบทความ:
{titles_b}

เกณฑ์:
- "หัวข้อเดียวกัน" เมื่อคำถามวิจัยและกลุ่มผู้อ่านเหมือนกันเกือบทั้งหมด ต่างกันแค่คำเรียกหรือมุมมองเล็กน้อย
- ถ้าต่างสาขา ต่างกลุ่มประชากร หรือต่างวิธีวิจัยอย่างมีนัย ให้ตอบว่าคนละหัวข้อ แม้ใช้คำคล้ายกัน

ตอบกลับเป็น JSON เท่านั้น ห้ามมีข้อความอื่น:
{
  "same_topic": true,
  "reason": "เหตุผล 1 บรรทัด"
}
```

## หมายเหตุ

- บรรณาธิการเห็นด้วยว่าซ้ำ → แก้ชื่อให้ชัดผ่าน `labeling.overrides_path` ได้ทันที หรือรอ refit รายปี (`topics.refit_every_releases`) โดยลด `clustering.merge_similarity`
- ค่าใช้จ่ายต่ำ: ปกติ < 30 คู่ต่อรอบ
````

- [ ] **Step 4: Create `pipeline/atlas/review.py`**

```python
"""Editorial review: merge suggestions (LLM task "merge") and the quarterly label spot check.

Merge suggestions — topic pairs whose centroids are nearly identical (cosine ≥
labeling.merge.min_similarity, most similar first, at most labeling.merge.max_pairs) are shown to
the LLM with names, keywords and representative titles (prompts/topic_merge.th.md) → {same_topic,
reason}. Nothing is merged automatically: a merge changes stable ids and a wrong one distorts the
whole map. Without an LLM (labeling.provider off, or no llm.tasks.merge.model) the pairs are listed
by similarity only. Output: work/05_merge_suggestions.

`atlas review export` → output/review/<release>_label_review.csv (UTF-8 with BOM so Excel shows Thai):
a reproducible sample of review.sample_size topics — every keyword-fallback label and every possible
duplicate first, then a seeded random draw of the rest (topics an editor already fixed are skipped) —
with empty columns for the editor. `atlas review import FILE` upserts the corrected names into
labeling.overrides_path, which the label step applies every quarter.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel

from atlas.io_utils import read_table, write_table
from atlas.label import OVERRIDE_COLUMNS, load_overrides, topic_titles
from atlas.lineage import topic_code
from atlas.llm_runner import LlmItem, LlmJob, run_job
from atlas.prompts import load_prompt, prompt_version, render_prompt
from atlas.state import current_release

PROMPT_NAME = "topic_merge.th"
MERGE_COLUMNS = ["topic_a", "topic_b", "similarity", "same_topic", "reason", "source"]
REVIEW_COLUMNS = ["topic_id", "name_th", "name_en", "label_source", "size", "status", "keywords", "sample_titles",
                  "possible_duplicate", "why_in_sample", "ok", "name_th_fixed", "name_en_fixed", "reviewer", "note"]


class MergeOut(BaseModel):
    same_topic: bool
    reason: str = ""


def merge_candidates(cfg: dict) -> list[tuple[int, int, float]]:
    """(topic a, topic b, centroid cosine) for the most similar pairs above labeling.merge.min_similarity."""
    work, mcfg = Path(cfg["pipeline"]["work_dir"]), cfg["labeling"]["merge"]
    C = np.load(work / "04_centroids.npy")
    ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    S = C @ C.T
    iu = np.triu_indices(len(ids), k=1)
    sims = S[iu]
    keep = np.where(sims >= float(mcfg["min_similarity"]))[0]
    keep = keep[np.argsort(-sims[keep], kind="stable")][: int(mcfg["max_pairs"])]
    return [(int(ids[iu[0][k]]), int(ids[iu[1][k]]), round(float(sims[k]), 4)) for k in keep]


def _uses_llm(cfg: dict) -> bool:
    return cfg["labeling"]["provider"] == "llm" and bool(cfg["llm"]["tasks"]["merge"]["model"])


def merge_job(cfg: dict) -> LlmJob:
    work = Path(cfg["pipeline"]["work_dir"])
    labels = read_table(work / "05_labels.parquet").set_index("topic_id")
    info = read_table(work / "04_topic_info.parquet").set_index("topic_id")
    template = load_prompt(PROMPT_NAME, cfg["llm"]["prompts_dir"])
    pairs = merge_candidates(cfg)
    titles = topic_titles(cfg, int(cfg["review"]["n_titles"])) if pairs else {}
    items = []
    for a, b, _ in pairs:
        side = {}
        for tag, t in (("a", a), ("b", b)):
            side[f"name_{tag}"] = f"{labels.loc[t, 'name_th']} ({labels.loc[t, 'name_en']})"
            side[f"keywords_{tag}"] = info.loc[t, "top_keywords"]
            side[f"titles_{tag}"] = "\n".join(f"- {x}" for x in titles.get(t, []))
        items.append(LlmItem(f"{topic_code(a)}|{topic_code(b)}", render_prompt(template, **side),
                             {"same_topic": None, "reason": ""}))
    return LlmJob("merge", MergeOut, prompt_version(template), items)


def suggest_merges(cfg: dict, llm=None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    pairs = merge_candidates(cfg) if cfg["labeling"]["merge"]["enabled"] else []
    rows = [{"topic_a": a, "topic_b": b, "similarity": s, "same_topic": None, "reason": "", "source": "similarity"}
            for a, b, s in pairs]
    stats = None
    if pairs and (llm is not None or _uses_llm(cfg)):
        results, stats = run_job(cfg, merge_job(cfg), llm)
        for r in rows:
            res = results[f"{topic_code(r['topic_a'])}|{topic_code(r['topic_b'])}"]
            r.update(same_topic=res.output["same_topic"], reason=res.output["reason"],
                     source="fallback" if res.source == "fallback" else "llm")
    elif pairs:
        print("[label] merge suggestions by similarity only (set labeling.provider: llm and llm.tasks.merge.model "
              "for an LLM opinion)")
    out = pd.DataFrame(rows, columns=MERGE_COLUMNS)
    out["same_topic"] = out["same_topic"].astype(object)
    write_table(out, work / "05_merge_suggestions.parquet")
    (work / "05_merge_meta.json").write_text(json.dumps({"llm": stats}, ensure_ascii=False), encoding="utf-8")
    flagged = sum(1 for v in out["same_topic"] if v is None or bool(v))     # unknown counts as "look at it"
    print(f"[label] {len(out)} near-duplicate topic pairs, {flagged} to review")
    return out


# ---------------------------------------------------------------------- review export / import
def export_review(cfg: dict, out: str | Path | None = None, n: int | None = None) -> Path:
    work = Path(cfg["pipeline"]["work_dir"])
    labels = read_table(work / "05_labels.parquet")
    info = read_table(work / "04_topic_info.parquet")[["topic_id", "size", "top_keywords"]]
    df = labels.merge(info, on="topic_id", how="left")
    em_path = work / "07_emerging.parquet"
    status = read_table(em_path).set_index("topic_id")["status"].to_dict() if em_path.exists() else {}
    names = df.set_index("topic_id")["name_th"].to_dict()
    dup: dict[int, str] = {}
    mpath = work / "05_merge_suggestions.parquet"
    if mpath.exists():
        for m in read_table(mpath).itertuples():
            if pd.notna(m.same_topic) and not bool(m.same_topic):     # the LLM said: different topics
                continue
            dup.setdefault(int(m.topic_a), f"{topic_code(m.topic_b)} {names.get(int(m.topic_b), '')}")
            dup.setdefault(int(m.topic_b), f"{topic_code(m.topic_a)} {names.get(int(m.topic_a), '')}")
    n = int(n or cfg["review"]["sample_size"])
    why: dict[int, str] = {}
    if cfg["labeling"]["provider"] == "llm":
        for t in df.loc[df["label_source"] == "keywords", "topic_id"]:
            why[int(t)] = "fallback"
    for t in dup:
        why.setdefault(t, "duplicate")
    rest = df.loc[~df["topic_id"].isin(list(why)) & (df["label_source"] != "override"), "topic_id"].astype(int)
    rng = np.random.default_rng(int(cfg["pipeline"]["seed"]))
    k = max(0, n - len(why))
    for t in rng.permutation(rest.to_numpy())[:k]:
        why[int(t)] = "random"
    chosen = df[df["topic_id"].isin(list(why))].sort_values("topic_id")
    titles = topic_titles(cfg, int(cfg["review"]["n_titles"]))
    rows = [{"topic_id": topic_code(r.topic_id), "name_th": r.name_th, "name_en": r.name_en,
             "label_source": r.label_source, "size": int(r.size), "status": status.get(int(r.topic_id), ""),
             "keywords": r.top_keywords, "sample_titles": " | ".join(titles.get(int(r.topic_id), [])),
             "possible_duplicate": dup.get(int(r.topic_id), ""), "why_in_sample": why[int(r.topic_id)],
             "ok": "", "name_th_fixed": "", "name_en_fixed": "", "reviewer": "", "note": ""}
            for r in chosen.itertuples()]
    path = Path(out) if out else (Path(cfg["pipeline"]["output_dir"]) / "review"
                                  / f"{current_release(cfg)}_label_review.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=REVIEW_COLUMNS).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def import_review(cfg: dict, path: str | Path) -> dict:
    target = cfg["labeling"]["overrides_path"]
    if not target:
        raise ValueError("set labeling.overrides_path in the config (e.g. ./registry/label_overrides.csv)")
    rev = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    fixed = rev[(rev["name_th_fixed"].str.strip() != "") | (rev["name_en_fixed"].str.strip() != "")]
    ov = load_overrides(target)
    today = date.today().isoformat()
    new = pd.DataFrame([{"topic_id": int(r.topic_id.strip().lstrip("Tt")), "name_th": r.name_th_fixed.strip(),
                         "name_en": r.name_en_fixed.strip(), "description": "", "reviewer": r.reviewer.strip(),
                         "reviewed_at": today, "note": r.note.strip()} for r in fixed.itertuples()],
                       columns=OVERRIDE_COLUMNS)
    merged = pd.concat([ov[~ov["topic_id"].isin(new["topic_id"])], new], ignore_index=True).sort_values("topic_id")
    merged["topic_id"] = merged["topic_id"].map(topic_code)
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(target, index=False, encoding="utf-8-sig")
    return {"applied": len(new), "reviewed": len(rev), "overrides_total": len(merged), "path": str(target)}
```

- [ ] **Step 5: Run merge suggestions at the end of the label step** — in `pipeline/atlas/label.py`:

Replace
```python
          f"{meta['fallback']} keyword fallback, {applied} editor overrides")
    return out
```
with
```python
          f"{meta['fallback']} keyword fallback, {applied} editor overrides")
    if cfg["labeling"]["merge"]["enabled"]:
        from atlas.review import suggest_merges  # local import: atlas.review imports this module

        suggest_merges(cfg)
    return out
```
and register the job in `pipeline/atlas/llm_runner.py`:
Replace
```python
JOBS: dict[str, str] = {"label": "atlas.label:label_job"}
```
with
```python
JOBS: dict[str, str] = {"label": "atlas.label:label_job", "merge": "atlas.review:merge_job"}
```

- [ ] **Step 6: Config** — in `pipeline/atlas/config.py`:

Before
```python
class LabelingCfg(_Strict):
```
insert
```python
class MergeCfg(_Strict):
    enabled: bool = True
    min_similarity: float = Field(0.85, gt=0.0, le=1.0)
    max_pairs: int = Field(30, ge=0)


```
After
```python
    overrides_path: str | None = None     # editors' CSV keyed by T000123; the example config sets ./registry/…
```
insert
```python
    merge: MergeCfg = Field(default_factory=MergeCfg)
```
Before
```python
class AtlasConfig(_Strict):
```
insert
```python
class ReviewCfg(_Strict):
    sample_size: int = Field(50, ge=1)
    n_titles: int = Field(5, ge=1)


```
After
```python
    llm: LlmCfg = Field(default_factory=LlmCfg)
```
insert
```python
    review: ReviewCfg = Field(default_factory=ReviewCfg)
```

In `pipeline/config.example.yaml`:
After
```yaml
  mmr_lambda: 0.7
```
insert
```yaml
  merge:                      # คู่หัวข้อที่อาจซ้ำ → ข้อเสนอให้บรรณาธิการ (ไม่รวมอัตโนมัติ)
    enabled: true
    min_similarity: 0.85      # centroid cosine ≥ ค่านี้ = ผู้สมัคร
    max_pairs: 30             # ส่งให้ LLM ตัดสินไม่เกินกี่คู่ (คู่ที่ใกล้ที่สุดก่อน; ใช้ llm.tasks.merge)

# ---------- คนตรวจ: atlas review export → CSV ให้บรรณาธิการสุ่มตรวจชื่อหัวข้อ ----------
review:
  sample_size: 50             # หัวข้อต่อรอบ (ชื่อจาก fallback + คู่ที่อาจซ้ำมาก่อน แล้วสุ่มที่เหลือแบบทำซ้ำได้)
  n_titles: 5                 # ตัวอย่างชื่อบทความต่อหัวข้อในไฟล์ตรวจ
```

- [ ] **Step 7: CLI** — append to `pipeline/atlas/cli.py`:

```python


review_app = typer.Typer(help="Editors' spot check of topic names (export a CSV, import the corrections).",
                         no_args_is_help=True)
app.add_typer(review_app, name="review")


@review_app.command("export")
def review_export_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    out: Path = typer.Option(None, help="CSV path (default: output/review/<release>_label_review.csv)"),
    n: int = typer.Option(None, help="number of topics (default: review.sample_size)"),
) -> None:
    """Write the review CSV: keyword-fallback names and possible duplicates first, then a seeded sample."""
    from atlas.config import load_config
    from atlas.review import export_review

    typer.echo(f"wrote {export_review(load_config(config), out, n)}")


@review_app.command("import")
def review_import_cmd(
    file: Path = typer.Argument(..., help="the filled-in review CSV"),
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
) -> None:
    """Copy corrected names (name_th_fixed / name_en_fixed) into labeling.overrides_path."""
    from atlas.config import load_config
    from atlas.review import import_review

    r = import_review(load_config(config), file)
    typer.echo(f"{r['applied']} corrections from {r['reviewed']} reviewed topics → {r['path']} "
               f"({r['overrides_total']} overrides in total; they apply from the next label step)")
```

- [ ] **Step 8: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_review.py tests/test_label.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 9: Commit** (prompt rewritten — say so):

```bash
git add pipeline/atlas/review.py pipeline/tests/test_review.py prompts/topic_merge.th.md pipeline/atlas/label.py pipeline/atlas/llm_runner.py pipeline/atlas/config.py pipeline/config.example.yaml pipeline/atlas/cli.py
git commit -m "feat(review): near-duplicate topic suggestions (LLM merge check, never auto-merged) + atlas review export/import

prompts/topic_merge.th.md rewritten for fine-topic pairs with JSON output (read at run time by atlas/review.py).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 8: `embed_texts` on the P0 runner + OpenAlex reference works (fields → subfields → sampled Thai works)

P1 adds no embedding client of its own: texts outside the corpus (reference works now, bake-off samples in Task 19) go through the same `get_embedder` + `runner_cfg` + `run_embedding` + `EmbeddingStore` as the embed step (P0 Task 19), one store per `store_id` — so they get the same lock, journal, resume and `atlas status` line. OpenAlex is read with first-page requests only (no API key needed), at most 10 requests/s, and cached in `state_dir/openalex/` so later runs never re-fetch. Request shapes were verified against api.openalex.org on 2026-10-18 and recorded as fixtures; tests never touch the network.

**Files:**
- Modify: `pipeline/atlas/embed.py`, `pipeline/tests/test_embed.py` (append)
- Create: `pipeline/atlas/openalex.py`, `pipeline/tests/test_openalex.py`, `pipeline/tests/fixtures/openalex/{fields,subfields_17,subfields_33,works_1702,works_3304,works_3315}.json`

**Interfaces:**
- Consumes (P0 Task 19, in `atlas.embed` at `0426434`): `get_embedder(cfg)` (api → `embed_api.ApiEmbedder`, local → `LocalEmbedder`; `.model_id` = store id), `store_root(cfg)`, `runner_cfg(cfg)`, `_normalize`, and `atlas.embed_runner.run_embedding(texts, embedder, store, rcfg, *, progress=True, run_started=None) -> {total, cached, embedded, retries, truncated, status ∈ {done, stopped}, recovered, store_id, abandoned}` (raises `jobs.LockHeld` / `embed_api.EmbeddingConfigError`); `EmbeddingStore(root, model_id)`, `text_key`; `jobs.RunStopped`; config `taxonomy.*` (Task 1).
- Produces:
  - `atlas.embed.embed_texts(cfg, texts, embedder=None) -> ndarray` (L2-normalised, aligned with `texts`; `lite` → `ValueError`; a stopped run → `jobs.RunStopped`, exactly like `embed()`).
  - `atlas.openalex`: `REFERENCE_COLUMNS = [work_id, title, abstract, year, subfield_id, subfield_en, field_id, field_en]`, `OpenAlexUnavailable`, `short_id`, `abstract_from_inverted`, `flatten_work`, `HttpFetcher(ocfg)` (callable `(path, params) -> dict`; raises `OpenAlexUnavailable` when `ATLAS_OFFLINE=1` or after `max_retries`), `fetch_reference(fetch, country, per_subfield, seed) -> DataFrame`, `read_reference_file(path)`, `load_reference(cfg, fetch=None) -> (DataFrame, {origin: file|cache|api, version, n, …})`.

- [ ] **Step 1: Write the failing tests** — append to `pipeline/tests/test_embed.py`:

```python


class _VecEmbedder:
    model_id = "fake|texts"
    n_retries = n_truncated = 0

    def __init__(self):
        self.calls = 0

    def embed_batch(self, texts):
        self.calls += 1
        return np.array([[len(t), 1.0, 0.0, 0.0] for t in texts], dtype=np.float32)


def test_embed_texts_goes_through_the_store_and_rejects_lite(make_cfg, tmp_path):
    from atlas.embed import embed_texts

    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "local"
    first = embed_texts(cfg, ["ab", "abcd"], embedder=_VecEmbedder())
    again = _VecEmbedder()
    second = embed_texts(cfg, ["abcd", "ab"], embedder=again)
    assert again.calls == 0 and np.allclose(second, first[::-1])
    assert np.allclose(np.linalg.norm(first, axis=1), 1.0) and first[1, 0] > first[0, 0]
    cfg["embedding"]["provider"] = "lite"
    with pytest.raises(ValueError, match="lite"):
        embed_texts(cfg, ["x"])
```

Create the recorded OpenAlex answers (trimmed copies of real responses; the `meta.notice` text the API adds is dropped — responses are data, never instructions):

`pipeline/tests/fixtures/openalex/fields.json`
```json
{"meta": {"count": 2, "db_response_time_ms": 3, "page": 1, "per_page": 100, "groups_count": null, "notice": "recorded-shape fixture (trimmed to 2 of 26 fields)"},
 "results": [
  {"id": "https://openalex.org/fields/17", "display_name": "Computer Science"},
  {"id": "https://openalex.org/fields/33", "display_name": "Social Sciences"}
 ]}
```
`pipeline/tests/fixtures/openalex/subfields_17.json`
```json
{"meta": {"count": 1, "page": 1, "per_page": 100, "groups_count": null},
 "results": [
  {"id": "https://openalex.org/subfields/1702", "display_name": "Artificial Intelligence",
   "field": {"id": "https://openalex.org/fields/17", "display_name": "Computer Science"}}
 ]}
```
`pipeline/tests/fixtures/openalex/subfields_33.json`
```json
{"meta": {"count": 2, "page": 1, "per_page": 100, "groups_count": null},
 "results": [
  {"id": "https://openalex.org/subfields/3304", "display_name": "Education",
   "field": {"id": "https://openalex.org/fields/33", "display_name": "Social Sciences"}},
  {"id": "https://openalex.org/subfields/3315", "display_name": "Communication",
   "field": {"id": "https://openalex.org/fields/33", "display_name": "Social Sciences"}}
 ]}
```
`pipeline/tests/fixtures/openalex/works_1702.json`
```json
{"meta": {"count": 3, "page": 1, "per_page": 3, "groups_count": null, "notice": "No API key ... (ignored by the client)"},
 "results": [
  {"id": "https://openalex.org/W4399292033", "title": "Introducing CASUX: A Standardized Scale for Measuring the User Experience of Artificial Intelligence Based Conversational Agents",
   "publication_year": 2024,
   "primary_topic": {"id": "https://openalex.org/T12128", "display_name": "AI in Service Interactions", "score": 0.9028,
     "subfield": {"id": "https://openalex.org/subfields/1702", "display_name": "Artificial Intelligence"},
     "field": {"id": "https://openalex.org/fields/17", "display_name": "Computer Science"},
     "domain": {"id": "https://openalex.org/domains/3", "display_name": "Physical Sciences"}},
   "abstract_inverted_index": {"Conversational": [0], "agents": [1], "are": [2], "growing": [3], "in": [4], "education": [5]}},
  {"id": "https://openalex.org/W1000000002", "title": "Large language models for Thai question answering",
   "publication_year": 2025,
   "primary_topic": {"id": "https://openalex.org/T10181", "display_name": "Natural Language Processing Techniques", "score": 0.99,
     "subfield": {"id": "https://openalex.org/subfields/1702", "display_name": "Artificial Intelligence"},
     "field": {"id": "https://openalex.org/fields/17", "display_name": "Computer Science"},
     "domain": {"id": "https://openalex.org/domains/3", "display_name": "Physical Sciences"}},
   "abstract_inverted_index": {"We": [0], "fine-tune": [1], "a": [2, 5], "language": [3], "model": [4], "Thai": [6], "corpus": [7]}},
  {"id": "https://openalex.org/W1000000003", "title": "A work whose topic is unknown",
   "publication_year": 2023, "primary_topic": null, "abstract_inverted_index": null}
 ]}
```
`pipeline/tests/fixtures/openalex/works_3304.json`
```json
{"meta": {"count": 2, "page": 1, "per_page": 2, "groups_count": null},
 "results": [
  {"id": "https://openalex.org/W1000000011", "title": "Mathematics learning achievement of Thai secondary students",
   "publication_year": 2021,
   "primary_topic": {"id": "https://openalex.org/T11000", "display_name": "Mathematics Education", "score": 0.95,
     "subfield": {"id": "https://openalex.org/subfields/3304", "display_name": "Education"},
     "field": {"id": "https://openalex.org/fields/33", "display_name": "Social Sciences"},
     "domain": {"id": "https://openalex.org/domains/2", "display_name": "Social Sciences"}},
   "abstract_inverted_index": {"Students": [0], "solved": [1], "problems": [2], "with": [3], "skill": [4], "exercises": [5]}},
  {"id": "https://openalex.org/W1000000012", "title": "Teacher training in rural schools",
   "publication_year": 2019,
   "primary_topic": {"id": "https://openalex.org/T11001", "display_name": "Teacher Education", "score": 0.9,
     "subfield": {"id": "https://openalex.org/subfields/3304", "display_name": "Education"},
     "field": {"id": "https://openalex.org/fields/33", "display_name": "Social Sciences"},
     "domain": {"id": "https://openalex.org/domains/2", "display_name": "Social Sciences"}},
   "abstract_inverted_index": {"Rural": [0], "teachers": [1], "need": [2], "training": [3]}}
 ]}
```
`pipeline/tests/fixtures/openalex/works_3315.json`
```json
{"meta": {"count": 1, "page": 1, "per_page": 1, "groups_count": null},
 "results": [
  {"id": "https://openalex.org/W1000000021", "title": "Newspaper reading among Thai university students",
   "publication_year": 2016,
   "primary_topic": {"id": "https://openalex.org/T12000", "display_name": "Media and Journalism", "score": 0.93,
     "subfield": {"id": "https://openalex.org/subfields/3315", "display_name": "Communication"},
     "field": {"id": "https://openalex.org/fields/33", "display_name": "Social Sciences"},
     "domain": {"id": "https://openalex.org/domains/2", "display_name": "Social Sciences"}},
   "abstract_inverted_index": {"Print": [0], "media": [1], "readership": [2], "declines": [3]}}
 ]}
```

Create `pipeline/tests/test_openalex.py`:

```python
import json
import re

import pytest

from atlas.openalex import (
    HttpFetcher,
    OpenAlexUnavailable,
    abstract_from_inverted,
    fetch_reference,
    flatten_work,
    load_reference,
    read_reference_file,
    short_id,
)
from tests.conftest import FIXTURES

OA = FIXTURES / "openalex"


class RecordedFetch:
    """Serves tests/fixtures/openalex/*.json by endpoint + filter; records every call."""

    def __init__(self):
        self.calls = []

    def __call__(self, path: str, params: dict) -> dict:
        self.calls.append((path, dict(params)))
        if path == "/fields":
            name = "fields"
        elif path == "/subfields":
            name = "subfields_" + re.search(r"field\.id:(\d+)", params["filter"]).group(1)
        else:
            name = "works_" + re.search(r"primary_topic\.subfield\.id:(\d+)", params["filter"]).group(1)
        return json.loads((OA / f"{name}.json").read_text(encoding="utf-8"))


def test_helpers():
    assert short_id("https://openalex.org/subfields/1702") == "1702" and short_id(None) == ""
    assert abstract_from_inverted({"b": [1], "a": [0, 2]}) == "a b a" and abstract_from_inverted(None) == ""
    assert flatten_work({"id": "W1", "primary_topic": None}) is None


def test_fetch_reference_walks_fields_subfields_and_samples_works():
    fetch = RecordedFetch()
    df = fetch_reference(fetch, "TH", per_subfield=100, seed=42)
    assert sorted(df["subfield_id"].unique()) == ["1702", "3304", "3315"]
    assert len(df) == 5                                    # the work without a primary topic is dropped
    row = df.set_index("work_id").loc["W1000000002"]
    assert (row["field_id"], row["field_en"]) == ("17", "Computer Science")
    assert row["abstract"] == "We fine-tune a language model a Thai corpus"
    works = [p for path, p in fetch.calls if path == "/works"]
    assert len(works) == 3 and all(p["sample"] == 100 and p["seed"] == 42 and p["per_page"] == 100 for p in works)
    assert all("authorships.institutions.country_code:TH" in p["filter"] and "has_abstract:true" in p["filter"]
               for p in works)


def test_load_reference_caches_in_state_dir(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    df, meta = load_reference(cfg, RecordedFetch())
    assert meta["origin"] == "api" and meta["version"].startswith("openalex@") and len(df) == 5

    def boom(path, params):
        raise AssertionError("must not fetch again")

    df2, meta2 = load_reference(cfg, boom)
    assert meta2["origin"] == "cache" and df2["work_id"].tolist() == df["work_id"].tolist()


def test_reference_file_overrides_the_api(make_cfg, tmp_path):
    works = json.loads((OA / "works_3304.json").read_text(encoding="utf-8"))["results"]
    p = tmp_path / "ref.jsonl"
    p.write_text("\n".join(json.dumps(w) for w in works), encoding="utf-8")
    cfg = make_cfg(tmp_path)
    cfg["taxonomy"]["reference_path"] = str(p)
    df, meta = load_reference(cfg, None)
    assert meta == {"origin": "file", "version": "file:ref.jsonl", "n": 2}
    csv = tmp_path / "ref.csv"
    df.to_csv(csv, index=False)
    assert read_reference_file(csv)["subfield_id"].tolist() == ["3304", "3304"]


def test_offline_flag_blocks_the_network(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    with pytest.raises(OpenAlexUnavailable, match="ATLAS_OFFLINE"):
        load_reference(cfg)                                 # conftest sets ATLAS_OFFLINE=1


def test_http_fetcher_builds_polite_urls(monkeypatch, make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    ocfg = {**cfg["taxonomy"]["openalex"], "mailto": "atlas@example.org"}
    monkeypatch.delenv("ATLAS_OFFLINE")
    monkeypatch.setenv("OPENALEX_API_KEY", "k123")
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"results": []}'

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        return Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert HttpFetcher(ocfg)("/works", {"filter": "a:1,b:2", "per_page": 5}) == {"results": []}
    assert seen["url"] == ("https://api.openalex.org/works?filter=a:1,b:2&per_page=5"
                           "&mailto=atlas%40example.org&api_key=k123")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_embed.py tests/test_openalex.py -q`
Expected: FAIL — `ImportError: cannot import name 'embed_texts'` and `ModuleNotFoundError: No module named 'atlas.openalex'`.

- [ ] **Step 3: Add `embed_texts` to `pipeline/atlas/embed.py`** — next to `embed()`, built only from the P0 Task 19 helpers already in this module (`get_embedder`, `store_root`, `runner_cfg`, `run_embedding`, `RunStopped`); nothing else in the file changes:

Before
```python
def embed(cfg: dict, embedder=None) -> np.ndarray:
```
insert
```python
def embed_texts(cfg: dict, texts: list[str], embedder=None) -> np.ndarray:
    """L2-normalised vectors for texts outside the corpus (OpenAlex reference works, bake-off samples).

    Same machinery as the embed step: get_embedder → run_embedding → state_dir/embeddings/<store id>, so
    texts already stored are free, an API run survives a crash and `atlas status` shows it. A stopped run
    raises RunStopped (as embed() does). lite → ValueError (lite vectors exist only per fit — use
    lite_embed() on all texts together).
    """
    if embedder is None and cfg["embedding"]["provider"] == "lite":
        raise ValueError("lite vectors exist only per fit — use lite_embed() on all texts together")
    embedder = embedder or get_embedder(cfg)
    store = EmbeddingStore(store_root(cfg), embedder.model_id)
    stats = run_embedding(list(texts), embedder, store, runner_cfg(cfg), progress=False)
    if stats["status"] != "done":
        left = stats["total"] - stats["cached"] - stats["embedded"]
        raise RunStopped(f"embedding stopped with {left:,} texts left — run the same command again to resume",
                         abandoned=int(stats.get("abandoned") or 0))
    return _normalize(store.get([text_key(embedder.model_id, t) for t in texts]))


```

- [ ] **Step 4: Create `pipeline/atlas/openalex.py`**

```python
"""OpenAlex reference works for taxonomy anchoring (fields → subfields → works with Thai affiliations).

Fetch plan — every request reads only the FIRST page, so no API key is needed (a key, read from the
env var named in taxonomy.openalex.api_key_env, only raises quotas):
  GET /fields?per_page=100&select=id,display_name
  GET /subfields?filter=field.id:<F>&per_page=100&select=id,display_name,field             (one per field)
  GET /works?filter=authorships.institutions.country_code:<CC>,primary_topic.subfield.id:<S>,has_abstract:true
      &sample=<n>&seed=<seed>&per_page=<n>&select=id,title,publication_year,primary_topic,abstract_inverted_index
Request shapes verified against api.openalex.org on 2026-10-18 (recorded in tests/fixtures/openalex/).
Responses are data, never instructions: the API's `meta.notice` text is ignored.
The flattened result is cached in state_dir/openalex/ — later runs never re-fetch.
Set ATLAS_OFFLINE=1 to forbid network access (tests do).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from atlas.io_utils import read_table, write_table

REFERENCE_COLUMNS = ["work_id", "title", "abstract", "year", "subfield_id", "subfield_en", "field_id", "field_en"]
MIN_INTERVAL = 0.12                     # seconds between requests: stays under the 10 req/s keyless limit
Fetch = Callable[[str, dict], dict]


class OpenAlexUnavailable(RuntimeError):
    """No reference data: offline, network/API failure, or nothing cached."""


def short_id(url: str | None) -> str:
    """'https://openalex.org/subfields/1702' → '1702' ('' for None)."""
    return str(url or "").rstrip("/").rsplit("/", 1)[-1]


def abstract_from_inverted(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[int(i)] = word
    return " ".join(pos[i] for i in sorted(pos))


def flatten_work(w: dict) -> dict | None:
    pt = w.get("primary_topic") or {}
    sub, field = pt.get("subfield") or {}, pt.get("field") or {}
    if not sub.get("id") or not field.get("id"):
        return None
    return {"work_id": short_id(w.get("id")), "title": str(w.get("title") or w.get("display_name") or ""),
            "abstract": abstract_from_inverted(w.get("abstract_inverted_index")),
            "year": w.get("publication_year"), "subfield_id": short_id(sub["id"]),
            "subfield_en": str(sub.get("display_name", "")), "field_id": short_id(field["id"]),
            "field_en": str(field.get("display_name", ""))}


class HttpFetcher:
    """GET base_url + path with query params → parsed JSON (stdlib only; retries with backoff)."""

    def __init__(self, ocfg: dict):
        self.base = ocfg["base_url"].rstrip("/")
        self.mailto = ocfg["mailto"]
        self.api_key = os.environ.get(ocfg["api_key_env"], "")
        self.timeout, self.max_retries = float(ocfg["timeout"]), int(ocfg["max_retries"])
        self._last = 0.0

    def __call__(self, path: str, params: dict) -> dict:
        if os.environ.get("ATLAS_OFFLINE") == "1":
            raise OpenAlexUnavailable("ATLAS_OFFLINE=1 — network access disabled")
        q = dict(params)
        if self.mailto:
            q["mailto"] = self.mailto
        if self.api_key:
            q["api_key"] = self.api_key
        url = f"{self.base}{path}?{urllib.parse.urlencode(q, safe=':,|*')}"
        delay = 2.0
        for attempt in range(self.max_retries):
            time.sleep(max(0.0, MIN_INTERVAL - (time.monotonic() - self._last)))
            self._last = time.monotonic()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "tci-research-atlas"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                if attempt == self.max_retries - 1:
                    raise OpenAlexUnavailable(f"OpenAlex request failed: {e}") from e
                time.sleep(delay)
                delay *= 2
        raise OpenAlexUnavailable("unreachable")


def fetch_reference(fetch: Fetch, country: str, per_subfield: int, seed: int) -> pd.DataFrame:
    fields = fetch("/fields", {"per_page": 100, "select": "id,display_name"})["results"]
    subfields = []
    for f in fields:
        res = fetch("/subfields", {"filter": f"field.id:{short_id(f['id'])}", "per_page": 100,
                                   "select": "id,display_name,field"})["results"]
        subfields += [short_id(s["id"]) for s in res]
    rows = []
    for sid in tqdm(subfields, desc="openalex", disable=len(subfields) < 20):
        res = fetch("/works", {
            "filter": f"authorships.institutions.country_code:{country},primary_topic.subfield.id:{sid},has_abstract:true",
            "sample": per_subfield, "seed": seed, "per_page": per_subfield,
            "select": "id,title,publication_year,primary_topic,abstract_inverted_index"})["results"]
        rows += [r for r in (flatten_work(w) for w in res) if r]
    return pd.DataFrame(rows, columns=REFERENCE_COLUMNS).drop_duplicates("work_id").reset_index(drop=True)


def read_reference_file(path: str | Path) -> pd.DataFrame:
    """.jsonl of OpenAlex work objects, or a flat .parquet/.csv with REFERENCE_COLUMNS."""
    p = Path(path)
    if p.suffix in (".jsonl", ".ndjson"):
        works = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        df = pd.DataFrame([r for r in (flatten_work(w) for w in works) if r], columns=REFERENCE_COLUMNS)
    elif p.suffix == ".csv":
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
    else:
        df = read_table(p)
    missing = set(REFERENCE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{p}: reference file lacks columns {sorted(missing)}")
    return df[REFERENCE_COLUMNS].astype({"subfield_id": str, "field_id": str})


def load_reference(cfg: dict, fetch: Fetch | None = None) -> tuple[pd.DataFrame, dict]:
    """Reference works + provenance; raises OpenAlexUnavailable when there is no way to get them."""
    tcfg, ocfg = cfg["taxonomy"], cfg["taxonomy"]["openalex"]
    if tcfg["reference_path"]:
        df = read_reference_file(tcfg["reference_path"])
        return df, {"origin": "file", "version": f"file:{Path(tcfg['reference_path']).name}", "n": len(df)}
    cache_dir = Path(cfg["pipeline"]["state_dir"]) / "openalex"
    stem = f"reference_{ocfg['country_code']}_{ocfg['per_subfield']}_{ocfg['seed']}"
    meta_path = cache_dir / f"{stem}.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return read_table(cache_dir / f"{stem}.parquet"), {**meta, "origin": "cache"}
    df = fetch_reference(fetch or HttpFetcher(ocfg), ocfg["country_code"], int(ocfg["per_subfield"]),
                         int(ocfg["seed"]))
    if df.empty:
        raise OpenAlexUnavailable("OpenAlex returned no reference works")
    fetched = datetime.now(UTC).strftime("%Y-%m-%d")
    meta = {"origin": "api", "version": f"openalex@{fetched}", "n": len(df), "fetched_at": fetched}
    write_table(df, cache_dir / f"{stem}.parquet")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return df, meta
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_embed.py tests/test_openalex.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/embed.py pipeline/atlas/openalex.py pipeline/tests/test_embed.py pipeline/tests/test_openalex.py pipeline/tests/fixtures/openalex
git commit -m "feat(taxonomy): embed_texts on the P0 runner; OpenAlex reference works (first-page sampling, cached, offline-safe)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 9: Taxonomy — topics → OpenAlex subfields by kNN vote; OpenAlex fields become the map groups

Each topic's articles nearest its centroid (≤ `max_articles_per_topic`) take the similarity-weighted vote of their k nearest reference works; the plurality subfield wins, `cross_field` when its share is below `min_vote_share`. Fields (26, with Thai names) replace the P0 agglomerative groups, which stay as the fallback whenever OpenAlex is unavailable — the pipeline never stops for it. On the 20K synthetic corpus every planted topic landed in its planted subfield; held-out field accuracy of the kNN rule on the reference set itself is published as a quality number.

**Files:**
- Create: `pipeline/atlas/taxonomy.py`, `pipeline/tests/test_taxonomy.py`
- Modify: `pipeline/atlas/synth.py` (append `SUBFIELDS`, `reference_works`), `pipeline/atlas/export.py` (v1.1 group names), `pipeline/atlas/layout.py` (group of each topic), `pipeline/atlas/pipeline.py` (step `taxonomy` after `cluster`)

**Interfaces:**
- Consumes: `load_reference`, `OpenAlexUnavailable`, `Fetch` (Task 8); `embed_texts` (Task 8), `lite_embed`; `load_aligned` (Task 2).
- Produces:
  - `atlas.taxonomy`: `TAXONOMY_COLUMNS = [topic_id, group_id, group_en, group_th, subfield_id, subfield_en, vote_share, cross_field, source]`, `FIELD_TH` (field id → Thai name), `knn_vote(query, ref, ref_labels, k) -> (pred, conf)`, `holdout_accuracy(...)`, `topic_votes(...)`, `load_topic_groups(work) -> DataFrame` (10_taxonomy, or the P0 coarse groups when the step has not run), `taxonomy(cfg, fetch=None) -> DataFrame` → `work/10_taxonomy` + `work/10_taxonomy_meta.json` (`source, version, reference_origin, n_reference, k, holdout_accuracy_subfield, holdout_accuracy_field, n_cross_field` or `source: agglomerative, reason`).
  - `atlas.synth`: `SUBFIELDS` (planted topic key → `(subfield id, name, field id, field name)`), `reference_works(n_per_topic=40, seed=11) -> [OpenAlex-shaped work dicts]`.
  - `export.build_atlas(..., definition_version, group_names=None)`: `group_names = {group id: (th, en)}`.
  - Pipeline `STEPS`: `… cluster, taxonomy, label, …`.

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_taxonomy.py`:

```python
import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.export import build_atlas
from atlas.io_utils import read_table, write_table
from atlas.synth import SUBFIELDS, TOPICS, reference_works
from atlas.taxonomy import FIELD_TH, knn_vote, load_topic_groups, taxonomy

KEYS = ["genai_edu", "math_learning", "print_media"]


def test_knn_vote_weights_by_similarity():
    ref = np.eye(3, dtype=np.float32)
    labels = np.array(["a", "b", "b"])
    q = np.array([[0.9, 0.1, 0.0]], dtype=np.float32)
    pred, conf = knn_vote(q / np.linalg.norm(q), ref, labels, k=3)
    assert pred.tolist() == ["a"] and 0.5 < conf[0] < 1.0


def _corpus(cfg, n_per=40):
    """Three planted topics, docs written from the synthetic topic vocabularies, topic ids 1..3."""
    rng = np.random.default_rng(0)
    by_key = {t[0]: t for t in TOPICS}
    rows, labels = [], []
    for tid, key in enumerate(KEYS, start=1):
        _, _, th, en = by_key[key]
        for i in range(n_per):
            words = list(rng.choice(en, 4, replace=False)) + list(rng.choice(th, 2, replace=False))
            rows.append({"article_id": f"{key}{i}", "doc_text": " . ".join(words)})
            labels.append(tid)
    work = Path(cfg["pipeline"]["work_dir"])
    n = len(rows)
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": [r["article_id"] for r in rows], "fine_topic": labels}),
                work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"topic_id": [1, 2, 3], "size": n_per, "coarse_topic": [0, 0, 1]}),
                work / "04_topic_info.parquet")
    np.save(work / "03_embeddings.npy", np.random.default_rng(1).normal(size=(n, 8)).astype(np.float32))
    (work / "04_centroid_ids.json").write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    ref = Path(cfg["pipeline"]["work_dir"]).parent / "ref.jsonl"
    ref.write_text("\n".join(json.dumps(w) for w in reference_works(n_per_topic=20)), encoding="utf-8")
    return ref


def test_topics_are_anchored_to_openalex_subfields(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "lite"            # lite vectors are fitted jointly with the reference
    cfg["taxonomy"]["reference_path"] = str(_corpus(cfg))
    out = taxonomy(cfg).set_index("topic_id")
    for tid, key in enumerate(KEYS, start=1):
        sid, _, fid, fname = SUBFIELDS[key]
        assert (out.loc[tid, "subfield_id"], out.loc[tid, "group_id"]) == (sid, int(fid))
        assert out.loc[tid, "group_th"] == FIELD_TH[fid] and out.loc[tid, "group_en"] == fname
    assert not out["cross_field"].any() and set(out["source"]) == {"openalex"}
    meta = json.loads((tmp_path / "work" / "10_taxonomy_meta.json").read_text(encoding="utf-8"))
    assert meta["source"] == "openalex" and meta["n_reference"] == 320 and meta["holdout_accuracy_field"] >= 0.9
    assert load_topic_groups(tmp_path / "work").set_index("topic_id")["group_id"].to_dict() == {1: 17, 2: 33, 3: 33}


def test_mixed_topic_is_flagged_cross_field(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "lite"            # lite vectors are fitted jointly with the reference
    cfg["taxonomy"]["reference_path"] = str(_corpus(cfg))
    fine = read_table(tmp_path / "work" / "04_fine_topics.parquet")
    num = fine["article_id"].str.extract(r"(\d+)$")[0].astype(int)
    key = fine["article_id"].str.replace(r"\d+$", "", regex=True)
    fine["fine_topic"] = 3
    fine.loc[(key == "math_learning") & (num >= 20), "fine_topic"] = 2
    fine.loc[((key != "print_media") & (num < 20)) | ((key == "print_media") & (num < 15)), "fine_topic"] = 1
    write_table(fine, tmp_path / "work" / "04_fine_topics.parquet")     # topic 1 = 20 AI + 20 maths + 15 print
    out = taxonomy(cfg).set_index("topic_id")
    assert bool(out.loc[1, "cross_field"]) and out.loc[1, "vote_share"] < 0.5 + 1e-9


def test_no_reference_falls_back_to_agglomerative_groups(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["embedding"]["provider"] = "lite"            # lite vectors are fitted jointly with the reference
    _corpus(cfg)                                       # reference_path unset + ATLAS_OFFLINE=1 → no OpenAlex
    out = taxonomy(cfg)
    assert set(out["source"]) == {"agglomerative"} and out["group_id"].tolist() == [0, 0, 1]
    meta = json.loads((tmp_path / "work" / "10_taxonomy_meta.json").read_text(encoding="utf-8"))
    assert meta["source"] == "agglomerative" and "ATLAS_OFFLINE" in meta["reason"]
    cfg["taxonomy"]["source"] = "off"
    assert set(taxonomy(cfg)["source"]) == {"agglomerative"}


def test_api_provider_embeds_reference_through_the_store(make_cfg, tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    cfg["taxonomy"]["reference_path"] = str(_corpus(cfg))
    cfg["embedding"]["provider"] = "api"
    seen = {}

    def fake_embed_texts(cfg_, texts):
        seen["n"] = len(texts)
        return np.random.default_rng(2).normal(size=(len(texts), 8)).astype(np.float32)

    monkeypatch.setattr("atlas.taxonomy.embed_texts", fake_embed_texts)
    taxonomy(cfg)
    assert seen["n"] == 320


def test_v11_export_uses_field_names_for_groups():
    info = pd.DataFrame({"topic_id": [1, 2], "size": [30, 10], "top_terms": "a", "top_keywords": "a",
                         "coarse_topic": [33, 33], "coherence": 0.9})
    labels = pd.DataFrame({"level": "fine", "topic_id": [1, 2], "name_th": ["หนึ่ง", "สอง"], "name_en": ["One", "Two"],
                           "description": "", "keywords": "", "cache_key": "x"})
    layout = pd.DataFrame([{"kind": "group", "id": 33, "x": 1.0, "y": 1.0, "r": 5.0, "parent": -1},
                           {"kind": "topic", "id": 1, "x": 1.0, "y": 1.0, "r": 3.0, "parent": 33},
                           {"kind": "topic", "id": 2, "x": 2.0, "y": 2.0, "r": 2.0, "parent": 33}])
    em = pd.DataFrame({"topic_id": [1, 2], "status": "STABLE", "emerging_score": 50.0, "cagr_recent": 0.0,
                       "burst_years": "", "share_growth": 0.0, "share_growth_lo": 0.0, "share_growth_hi": 0.0,
                       "n_journals_R": 3, "n_orgs_R": 3, "journal_driven": False, "orgs_unverified": False})
    atlas = build_atlas(info, labels, layout, pd.DataFrame(columns=["s", "t", "w"]), em, pd.DataFrame(),
                        {"last_complete_year": 2024}, 40, True, 3,
                        group_names={33: ("สังคมศาสตร์", "Social Sciences")})
    assert atlas["groups"][0]["th"] == "สังคมศาสตร์" and atlas["groups"][0]["id"] == "g33"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_taxonomy.py -q`
Expected: FAIL — `ImportError: cannot import name 'SUBFIELDS' from 'atlas.synth'`.

- [ ] **Step 3: Append the synthetic reference set to `pipeline/atlas/synth.py`** (uses the module's existing `TOPICS`, `_sentence_en` and `np`):

```python


# OpenAlex subfield (= Scopus ASJC code) and field of each planted topic — for the synthetic reference set
SUBFIELDS = {
    "genai_edu": ("1702", "Artificial Intelligence", "17", "Computer Science"),
    "buddhist_media": ("1212", "Religious studies", "12", "Arts and Humanities"),
    "elderly_care": ("2717", "Geriatrics and Gerontology", "27", "Medicine"),
    "print_media": ("3315", "Communication", "33", "Social Sciences"),
    "tourism": ("1409", "Tourism, Leisure and Hospitality Management", "14", "Business, Management and Accounting"),
    "rice_farming": ("1102", "Agronomy and Crop Science", "11", "Agricultural and Biological Sciences"),
    "sme_ecommerce": ("1406", "Marketing", "14", "Business, Management and Accounting"),
    "nursing_edu": ("2902", "Advanced and Specialized Nursing", "29", "Nursing"),
    "diabetes": ("2712", "Endocrinology, Diabetes and Metabolism", "27", "Medicine"),
    "local_gov": ("3321", "Public Administration", "33", "Social Sciences"),
    "math_learning": ("3304", "Education", "33", "Social Sciences"),
    "water_quality": ("2312", "Water Science and Technology", "23", "Environmental Science"),
    "herbal_medicine": ("3003", "Pharmaceutical Science", "30", "Pharmacology, Toxicology and Pharmaceutics"),
    "hrm": ("1407", "Organizational Behavior and Human Resource Management", "14",
            "Business, Management and Accounting"),
    "thai_literature": ("1208", "Literature and Literary Theory", "12", "Arts and Humanities"),
    "energy": ("2105", "Renewable Energy, Sustainability and the Environment", "21", "Energy"),
}


def reference_works(n_per_topic: int = 40, seed: int = 11) -> list[dict]:
    """OpenAlex-shaped work objects (English title + inverted-index abstract) for every planted topic."""
    rng = np.random.default_rng(seed)
    works = []
    for key, _role, _th, en in TOPICS:
        sid, sname, fid, fname = SUBFIELDS[key]
        for j in range(n_per_topic):
            a, b = rng.choice(en, 2, replace=False)
            pen = rng.permutation(en)
            text = " ".join(_sentence_en(rng, pen[i], pen[i + 1]) for i in (0, 2, 4))
            inv: dict[str, list[int]] = {}
            for pos, word in enumerate(text.split()):
                inv.setdefault(word, []).append(pos)
            works.append({
                "id": f"https://openalex.org/W9{sid}{j:04d}", "title": f"{str(a).capitalize()} and {b} in Thailand",
                "publication_year": int(rng.integers(2015, 2025)),
                "primary_topic": {"id": "https://openalex.org/T0", "display_name": sname,
                                  "subfield": {"id": f"https://openalex.org/subfields/{sid}", "display_name": sname},
                                  "field": {"id": f"https://openalex.org/fields/{fid}", "display_name": fname},
                                  "domain": {"id": "https://openalex.org/domains/0", "display_name": "synthetic"}},
                "abstract_inverted_index": inv,
            })
    return works
```

- [ ] **Step 4: Create `pipeline/atlas/taxonomy.py`**

```python
"""Taxonomy anchoring: every fine topic → an OpenAlex subfield (→ field = its group on the map).

Reference set: works with Thai-affiliated authors from OpenAlex (atlas.openalex), embedded with the
SAME embedding model as the corpus (api/local: through the persistent store; lite: fitted jointly on
corpus + reference texts, because lite vectors only exist per fit). For each topic, its articles
closest to the centroid (≤ max_articles_per_topic) each take the similarity-weighted vote of their k
nearest reference works; the topic's subfield is the plurality of those article votes, vote_share is
the plurality's share and cross_field = vote_share < min_vote_share. Groups = OpenAlex fields.
Held-out accuracy of the same kNN rule on the reference set itself is recorded as a quality number.

Never hard-fails: taxonomy.source=off, offline, API errors or an empty reference set fall back to the
P0 agglomerative groups (04_topic_info.coarse_topic) with source="agglomerative".
Outputs: work/10_taxonomy, work/10_taxonomy_meta.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import load_aligned
from atlas.embed import embed_texts, lite_embed
from atlas.io_utils import read_table, write_table
from atlas.openalex import Fetch, OpenAlexUnavailable, load_reference

TAXONOMY_COLUMNS = ["topic_id", "group_id", "group_en", "group_th", "subfield_id", "subfield_en",
                    "vote_share", "cross_field", "source"]
# OpenAlex's 26 fields (ids = Scopus ASJC two-digit codes) with Thai names for the map legend
FIELD_TH = {
    "11": "เกษตรศาสตร์และชีววิทยา", "12": "ศิลปศาสตร์และมนุษยศาสตร์", "13": "ชีวเคมี พันธุศาสตร์ และอณูชีววิทยา",
    "14": "ธุรกิจ การจัดการ และการบัญชี", "15": "วิศวกรรมเคมี", "16": "เคมี", "17": "วิทยาการคอมพิวเตอร์",
    "18": "วิทยาการตัดสินใจ", "19": "วิทยาศาสตร์โลกและดาวเคราะห์", "20": "เศรษฐศาสตร์ เศรษฐมิติ และการเงิน",
    "21": "พลังงาน", "22": "วิศวกรรมศาสตร์", "23": "วิทยาศาสตร์สิ่งแวดล้อม", "24": "ภูมิคุ้มกันวิทยาและจุลชีววิทยา",
    "25": "วัสดุศาสตร์", "26": "คณิตศาสตร์", "27": "แพทยศาสตร์", "28": "ประสาทวิทยาศาสตร์", "29": "พยาบาลศาสตร์",
    "30": "เภสัชวิทยา พิษวิทยา และเภสัชศาสตร์", "31": "ฟิสิกส์และดาราศาสตร์", "32": "จิตวิทยา", "33": "สังคมศาสตร์",
    "34": "สัตวแพทยศาสตร์", "35": "ทันตแพทยศาสตร์", "36": "วิชาชีพด้านสุขภาพ",
}


def knn_vote(query: np.ndarray, ref: np.ndarray, ref_labels: np.ndarray, k: int,
             chunk: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """Similarity-weighted kNN vote → (label per query row, winning weight share). Rows are unit vectors."""
    k = max(1, min(k, len(ref)))
    classes, codes = np.unique(ref_labels, return_inverse=True)
    pred = np.empty(len(query), dtype=classes.dtype)
    conf = np.empty(len(query))
    for s in range(0, len(query), chunk):
        sim = query[s:s + chunk] @ ref.T
        idx = np.argpartition(-sim, k - 1, axis=1)[:, :k]
        w = np.maximum(np.take_along_axis(sim, idx, axis=1), 0.0) + 1e-6
        votes = np.zeros((len(idx), len(classes)))
        np.add.at(votes, (np.repeat(np.arange(len(idx)), k), codes[idx].ravel()), w.ravel())
        best = votes.argmax(axis=1)
        pred[s:s + chunk] = classes[best]
        conf[s:s + chunk] = votes[np.arange(len(idx)), best] / votes.sum(axis=1)
    return pred, conf


def holdout_accuracy(ref_emb: np.ndarray, labels: np.ndarray, k: int, frac: float, seed: int) -> float | None:
    """kNN accuracy on a random held-out part of the reference set (None when a side would be empty)."""
    rng = np.random.default_rng(seed)
    test = rng.random(len(labels)) < frac
    if test.sum() == 0 or (~test).sum() == 0:
        return None
    pred, _ = knn_vote(ref_emb[test], ref_emb[~test], labels[~test], k)
    return round(float((pred == labels[test]).mean()), 4)


def topic_votes(labels: np.ndarray, emb: np.ndarray, ids: list[int], C: np.ndarray, ref_emb: np.ndarray,
                ref_sub: np.ndarray, k: int, max_articles: int) -> pd.DataFrame:
    rows = []
    for i, tid in enumerate(ids):
        members = np.where(labels == tid)[0]
        if len(members) > max_articles:
            members = members[np.argsort(-(emb[members] @ C[i]), kind="stable")[:max_articles]]
        pred, _ = knn_vote(emb[members], ref_emb, ref_sub, k)
        vc = pd.Series(pred).value_counts()
        top = vc[vc == vc.iloc[0]].index
        winner = sorted(str(t) for t in top)[0]                 # deterministic tie-break
        rows.append({"topic_id": tid, "subfield_id": winner, "vote_share": float(vc.iloc[0] / len(pred)),
                     "n_voted": int(len(pred))})
    return pd.DataFrame(rows)


def load_topic_groups(work: str | Path) -> pd.DataFrame:
    """topic_id, group_id (int), group_en, group_th — from 10_taxonomy, else the P0 coarse groups."""
    work = Path(work)
    try:
        t = read_table(work / "10_taxonomy.parquet")
        return t[["topic_id", "group_id", "group_en", "group_th"]].astype({"group_id": int})
    except FileNotFoundError:
        info = read_table(work / "04_topic_info.parquet")
        return pd.DataFrame({"topic_id": info["topic_id"], "group_id": info["coarse_topic"].astype(int),
                             "group_en": "", "group_th": ""})


def _fallback(info: pd.DataFrame, reason: str) -> tuple[pd.DataFrame, dict]:
    out = pd.DataFrame({"topic_id": info["topic_id"], "group_id": info["coarse_topic"].astype(int),
                        "group_en": "", "group_th": "", "subfield_id": "", "subfield_en": "",
                        "vote_share": np.nan, "cross_field": False, "source": "agglomerative"},
                       columns=TAXONOMY_COLUMNS)
    return out, {"source": "agglomerative", "version": None, "reason": reason}


def taxonomy(cfg: dict, fetch: Fetch | None = None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    tcfg, seed = cfg["taxonomy"], int(cfg["pipeline"]["seed"])
    info = read_table(work / "04_topic_info.parquet")
    try:
        if tcfg["source"] == "off":
            raise OpenAlexUnavailable("taxonomy.source is off")
        ref, ref_meta = load_reference(cfg, fetch)
        if ref.empty:
            raise OpenAlexUnavailable("empty reference set")
    except (OpenAlexUnavailable, OSError, ValueError) as e:
        out, meta = _fallback(info, str(e))
        print(f"[taxonomy] WARNING: OpenAlex taxonomy unavailable ({e}) → agglomerative groups")
    else:
        docs, emb = load_aligned(work)
        ref_text = (ref["title"].fillna("") + " . " + ref["abstract"].fillna("")).str.slice(
            0, int(cfg["embedding"]["max_chars_per_doc"])).tolist()
        if cfg["embedding"]["provider"] == "lite":
            joint = lite_embed(docs["doc_text"].tolist() + ref_text, cfg["embedding"]["lite"], seed)
            joint /= np.maximum(np.linalg.norm(joint, axis=1, keepdims=True), 1e-9)
            emb, ref_emb = joint[:len(docs)], joint[len(docs):]
        else:
            ref_emb = embed_texts(cfg, ref_text)
        labels = (docs[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id",
                                             how="left")["fine_topic"].fillna(-1).astype(int).to_numpy())
        ids = [int(t) for t in json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))]
        C = np.stack([emb[labels == t].mean(axis=0) for t in ids]) if ids else np.zeros((0, emb.shape[1]))
        C /= np.maximum(np.linalg.norm(C, axis=1, keepdims=True), 1e-9)
        sub = ref["subfield_id"].astype(str).to_numpy()
        votes = topic_votes(labels, emb, ids, C, ref_emb, sub, int(tcfg["k"]), int(tcfg["max_articles_per_topic"]))
        names = ref.drop_duplicates("subfield_id").set_index("subfield_id")
        out = votes.assign(
            subfield_en=votes["subfield_id"].map(names["subfield_en"]),
            group_id=votes["subfield_id"].map(names["field_id"]).astype(int),
            group_en=votes["subfield_id"].map(names["field_en"]),
            cross_field=votes["vote_share"] < float(tcfg["min_vote_share"]),
            source="openalex")
        out["group_th"] = out["group_id"].astype(str).map(FIELD_TH).fillna(out["group_en"])
        out = out[TAXONOMY_COLUMNS]
        k, frac = int(tcfg["k"]), float(tcfg["holdout_frac"])
        meta = {"source": "openalex", "version": ref_meta["version"], "reference_origin": ref_meta["origin"],
                "n_reference": int(len(ref)), "k": k,
                "holdout_accuracy_subfield": holdout_accuracy(ref_emb, sub, k, frac, seed),
                "holdout_accuracy_field": holdout_accuracy(ref_emb, ref["field_id"].astype(str).to_numpy(), k,
                                                           frac, seed),
                "n_cross_field": int(out["cross_field"].sum())}
        print(f"[taxonomy] {len(out)} topics → {out['group_id'].nunique()} OpenAlex fields "
              f"({meta['n_cross_field']} cross-field); held-out subfield accuracy "
              f"{meta['holdout_accuracy_subfield']} on {len(ref):,} reference works")
    write_table(out, work / "10_taxonomy.parquet")
    (work / "10_taxonomy_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return out
```

- [ ] **Step 5: Use the field names in the v1.1 export** — `pipeline/atlas/export.py` (anchors checked against `0426434`; the fix wave's pre-v3 `orgs_unverified` guard, LOW_DATA forecast gating and manifest keys in this file stay as they are):

Replace
```python
from atlas.io_utils import read_table
```
with
```python
from atlas.io_utils import read_table
from atlas.taxonomy import load_topic_groups
```
Replace
```python
                em: pd.DataFrame, fc: pd.DataFrame, meta: dict, n_articles: int, include_forecast: bool,
                definition_version: int) -> dict:
```
with
```python
                em: pd.DataFrame, fc: pd.DataFrame, meta: dict, n_articles: int, include_forecast: bool,
                definition_version: int, group_names: dict[int, tuple[str, str]] | None = None) -> dict:
    """group_names: {group id: (th, en)} (OpenAlex field names); unnamed groups take their largest topic's label."""
```
Replace
```python
        groups.append({"id": f"g{cid}",
                       "th": labels["name_th"].get(big, f"{_GROUP_TH}{cid}"),
                       "en": labels["name_en"].get(big, f"Group {cid}"),
```
with
```python
        th, en = (group_names or {}).get(cid, ("", ""))
        groups.append({"id": f"g{cid}",
                       "th": th or labels["name_th"].get(big, f"{_GROUP_TH}{cid}"),
                       "en": en or labels["name_en"].get(big, f"Group {cid}"),
```
Replace
```python
    outdir.mkdir(parents=True, exist_ok=True)
    info = read_table(work / "04_topic_info.parquet")
```
with
```python
    outdir.mkdir(parents=True, exist_ok=True)
    groups = load_topic_groups(work)                 # OpenAlex fields when the taxonomy step ran
    info = (read_table(work / "04_topic_info.parquet").drop(columns="coarse_topic")
            .merge(groups[["topic_id", "group_id"]].rename(columns={"group_id": "coarse_topic"}), on="topic_id"))
    group_names = {int(r.group_id): (str(r.group_th), str(r.group_en))
                   for r in groups.drop_duplicates("group_id").itertuples()}
```
Replace
```python
                        definition_version=int(cfg["emerging"]["definition_version"]))
```
with
```python
                        definition_version=int(cfg["emerging"]["definition_version"]), group_names=group_names)
```

- [ ] **Step 6: Group of each topic on the P0 map** — `pipeline/atlas/layout.py` (Task 13 rewrites this module; until then the hubs follow the taxonomy):

Replace
```python
from .io_utils import read_table, write_table
```
with
```python
from .io_utils import read_table, write_table
from .taxonomy import load_topic_groups
```
Replace
```python
    info = read_table(work / "04_topic_info.parquet").set_index("topic_id")
```
with
```python
    info = read_table(work / "04_topic_info.parquet").set_index("topic_id")
    group_of = load_topic_groups(work).set_index("topic_id")["group_id"].to_dict()
```
Replace
```python
            "parent": int(info.loc[tid, "coarse_topic"]),
```
with
```python
            "parent": int(group_of.get(tid, info.loc[tid, "coarse_topic"])),
```

- [ ] **Step 7: Register the step** — `pipeline/atlas/pipeline.py`:

Replace
```python
STEPS = ["ingest", "preprocess", "embed", "cluster", "label", "series", "emerging", "forecast", "layout", "export"]
```
with
```python
STEPS = ["ingest", "preprocess", "embed", "cluster", "taxonomy", "label", "series", "emerging", "forecast", "layout",
         "export"]
```
After
```python
    "cluster": ("atlas.cluster", "cluster"),
```
insert
```python
    "taxonomy": ("atlas.taxonomy", "taxonomy"),
```

- [ ] **Step 8: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_taxonomy.py -q && uv run pytest -q`
Expected: all pass. The P0 pipeline tests now also run `taxonomy`; offline it falls back to agglomerative groups (same output as before).

- [ ] **Step 9: Commit**

```bash
git add pipeline/atlas/taxonomy.py pipeline/atlas/synth.py pipeline/atlas/export.py pipeline/atlas/layout.py pipeline/atlas/pipeline.py pipeline/tests/test_taxonomy.py
git commit -m "feat(taxonomy): topics anchored to OpenAlex subfields (kNN vote, cross_field); fields are the map groups, agglomerative fallback

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 10: Partial-year tables for the nowcast (Emerging definition unchanged — `definition_version` 3)

**User decision (2026-10-19): Emerging stays at `definition_version` 3.** The journal-completeness rule proposed for v4 is not shipped: `last_complete_year` is still decided by the v3 rule exactly as merged (`min_year_complete`, else `min(last data year, as_of_year − 1)` trimmed by the backfill guard — the "median" method), and there is no `emerging.completeness` config, no EMERGING_SPEC change, no version bump and no schema/type regeneration in this task.

What ships is the nowcast input only. Years after the cutoff are already excluded from trends (`trimmed_years`); their articles are now also counted into two tables that Forecast v2 (Task 11) uses for the current-year nowcast. The tables are computed **after** the cutoff from the same rows and never feed back into it, so every v3 number (statuses, `last_complete_year`, `trimmed_years`, `totals`) is unchanged — the P0 test `test_series_backfill_guard_and_tables` keeps passing untouched.

**Files:**
- Modify: `pipeline/atlas/topics_time.py`, `pipeline/tests/test_series.py` (append)

**Interfaces:**
- Consumes: v3 `as_of_year(ecfg)`, `last_complete_year(totals, ecfg)` (unchanged).
- Produces:
  - `publication_months(docs) -> DataFrame[year, month, count]` (only `published` dates that agree with the article year; Buddhist-Era dates converted; 1970/lost dates drop out).
  - New checkpoints `work/06_months` (year, month, count) and `work/06_partial_year` (topic_id, year, count for years after the cutoff); `06_meta.json` keeps the v3 keys (`last_complete_year`, `as_of_year`, `trimmed_years`, `years`, `totals`) and gains `partial_totals` (`{year: articles}` after the cutoff) and `completeness` = `{"method": "configured"}` when `min_year_complete` is set, else `{"method": "median"}` (the v3 backfill guard) — published as `data_quality.completeness_method` by Task 16.

- [ ] **Step 1: Write the failing test** — append to `pipeline/tests/test_series.py`:

```python


# ---- P1: partial-year tables for the nowcast (definition v3 unchanged)
def test_publication_months_and_partial_year(make_cfg, tmp_path):
    from atlas.topics_time import publication_months

    docs = pd.DataFrame({"year": [2024, 2024, 2025, 2016, 2014],
                         "published": ["2024-03-02", "2024-11-30", "2025-02-01", "2559-07-01", "1970-01-01"]})
    m = publication_months(docs.astype({"year": "Int64"}))
    assert sorted(map(tuple, m[["year", "month"]].to_numpy().tolist())) == [(2016, 7), (2024, 3), (2024, 11), (2025, 2)]
    cfg = make_cfg(tmp_path)
    cfg["emerging"]["as_of_year"] = 2026
    work = tmp_path / "work"
    rows, topics = [], []
    for y in range(2019, 2025):
        n = 2 if y == 2024 else 10
        for i in range(n):
            rows.append({"article_id": f"{y}-{i}", "year": y, "journal_name": "jA", "published": f"{y}-0{i % 9 + 1}-01"})
            topics.append({"article_id": f"{y}-{i}", "fine_topic": 0})
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    write_table(pd.DataFrame(topics), work / "04_fine_topics.parquet")
    build_series(cfg)
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    assert meta["last_complete_year"] == 2023 and meta["trimmed_years"] == [2024]       # the v3 rule, unchanged
    assert meta["partial_totals"] == {"2024": 2} and meta["completeness"] == {"method": "median"}
    assert read_table(work / "06_partial_year.parquet").to_dict("records") == [{"topic_id": 0, "year": 2024, "count": 2}]
    assert read_table(work / "06_months.parquet")["count"].sum() == 52
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_series.py -q`
Expected: FAIL — `ImportError: cannot import name 'publication_months'`.

- [ ] **Step 3: Edit `pipeline/atlas/topics_time.py`** (anchors checked against `0426434`)

3a. Docstring:
Replace
```python
"""Yearly series per topic + journal/institution tables for Emerging v3, with backfill guard.

corpus_total counts ALL dated articles (assigned or not) — it is the share denominator.
Outputs: 06_series, 06_topic_journal_year, 06_topic_org_year, 06_journal_first_year, 06_meta.json
"""
```
with
```python
"""Yearly series per topic + journal/institution tables for Emerging v3, with backfill guard.

corpus_total counts ALL dated articles (assigned or not) — it is the share denominator.
Years after last_complete_year (v3 rule, unchanged) are kept for the Forecast v2 nowcast only:
06_partial_year (topic counts) and 06_months (articles per publication month, dates that agree with the
article year). They are computed after the cutoff and never feed back into it.
Outputs: 06_series, 06_topic_journal_year, 06_topic_org_year, 06_journal_first_year, 06_months,
06_partial_year, 06_meta.json
"""
```

3b. `publication_months`, right before `build_series`:
Before
```python
def build_series(cfg: dict) -> pd.DataFrame:
```
insert
```python
def publication_months(docs: pd.DataFrame) -> pd.DataFrame:
    """year, month, count from `published` dates that agree with the article year (1970/lost dates drop out)."""
    if "published" not in docs.columns:
        return pd.DataFrame(columns=["year", "month", "count"])
    m = docs["published"].fillna("").astype(str).str.extract(r"^(\d{4})-(\d{2})")
    y = pd.to_numeric(m[0], errors="coerce")
    y = y.where(y <= 2400, y - 543)                               # Buddhist Era dates
    mon = pd.to_numeric(m[1], errors="coerce")
    ok = (y == docs["year"]) & mon.between(1, 12)
    out = pd.DataFrame({"year": docs.loc[ok, "year"].astype(int), "month": mon[ok].astype(int)})
    return out.groupby(["year", "month"]).size().rename("count").reset_index()


```

3c. Inputs of `build_series` and the rows after the cutoff (the cutoff call itself is the v3 one, on the same totals):
Replace
```python
    docs = read_table(work / "02_docs.parquet")[["article_id", "year", "journal_name"]]
```
with
```python
    docs = read_table(work / "02_docs.parquet")
    docs = docs[[c for c in ("article_id", "year", "journal_name", "published") if c in docs.columns]]
```
Replace
```python
    totals = d.groupby("year").size()
    cutoff = last_complete_year(totals, cfg["emerging"])
    trimmed = [int(y) for y in totals.index if y > cutoff]     # forward-dated / incomplete years: kept in the
    d, totals = d[d["year"] <= cutoff], totals[totals.index <= cutoff]   # corpus, excluded from trends
```
with
```python
    all_totals = d.groupby("year").size()
    cutoff = last_complete_year(all_totals, cfg["emerging"])    # definition v3, unchanged
    how = {"method": "configured" if cfg["emerging"].get("min_year_complete") is not None else "median"}
    trimmed = [int(y) for y in all_totals.index if y > cutoff]  # forward-dated / incomplete years: kept in the
    later = d[(d["year"] > cutoff) & (d["fine_topic"] >= 0)]     # corpus, excluded from trends, used for nowcast
    partial = (later.groupby(["fine_topic", "year"]).size().rename("count").reset_index()
               .rename(columns={"fine_topic": "topic_id"}))
    d, totals = d[d["year"] <= cutoff], all_totals[all_totals.index <= cutoff]
```

3d. Outputs:
Replace
```python
    write_table(jfirst, work / "06_journal_first_year.parquet")
    (work / "06_meta.json").write_text(json.dumps({
        "last_complete_year": int(cutoff),
        "as_of_year": as_of_year(cfg["emerging"]),
        "trimmed_years": trimmed,
        "years": [int(y) for y in totals.index],
        "totals": {str(int(y)): int(c) for y, c in totals.items()},
    }), encoding="utf-8")
```
with
```python
    write_table(jfirst, work / "06_journal_first_year.parquet")
    dated = docs[docs["year"].notna()].assign(year=lambda x: x["year"].astype(int))
    write_table(publication_months(dated), work / "06_months.parquet")
    write_table(partial, work / "06_partial_year.parquet")
    (work / "06_meta.json").write_text(json.dumps({
        "last_complete_year": int(cutoff),
        "as_of_year": as_of_year(cfg["emerging"]),
        "trimmed_years": trimmed,
        "years": [int(y) for y in totals.index],
        "totals": {str(int(y)): int(c) for y, c in totals.items()},
        "partial_totals": {str(int(y)): int(c) for y, c in all_totals.items() if y > cutoff},
        "completeness": how,
    }), encoding="utf-8")
```

- [ ] **Step 4: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_series.py tests/test_emerging.py -q && uv run pytest -q`
Expected: all pass; the P0 series/emerging tests are untouched (same cutoff, same statuses, `definition_version` 3 everywhere).

- [ ] **Step 5: Commit**

```bash
git add pipeline/atlas/topics_time.py pipeline/tests/test_series.py
git commit -m "feat(series): partial-year and publication-month tables for the nowcast (Emerging definition v3 unchanged)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Forecast v2 — share × total, naive/drift/NB GLM/damped ETS, rolling-origin CV, honest skill gate, conformal 80/95 % intervals, nowcast

`count = share × N̂`: the corpus total is forecast once (best of `total_models` by rolling-origin MAE) and every topic's share by each model, so topic numbers stay consistent with the total. Model choice uses all CV origins; **skill and MASE are scored honestly** — at each origin the model picked from earlier origins only is evaluated — and a forecast is shown only when the chosen model is not naive, skill > `min_skill` and the published (rounded) MASE < `max_mase`. Intervals are split-conformal on NB2-scaled errors of the published model across all topics (normal quantiles below `min_calibration` scores). The partial year after `last_complete_year` gets a nowcast: year-to-date ÷ the share of a year's articles usually published by that month.

Measured: on the 20K synthetic corpus pooled 80 % coverage over 3 cut-offs 0.79–0.81; on 4 simulated NB panels 0.735–0.80 (a single cut-off is 56 points on the synthetic corpus — too noisy for the 70–90 % acceptance band, hence `rolling_coverage`). `statsforecast` is not used (its 2.1 pins `pandas<3`).

**Files:**
- Modify: `pipeline/atlas/forecast.py` (full replacement), `pipeline/tests/test_forecast.py` (full replacement), `pipeline/atlas/config.py`, `pipeline/config.example.yaml`

**Interfaces:**
- Consumes: `06_series` (topic_id, year, count), `06_meta.json` (`last_complete_year`, `totals`, `partial_totals`), `06_months`, `06_partial_year` (Task 10), `07_emerging.status` (LOW_DATA topics are skipped — they get no trend claim either). The full replacement keeps both fix-wave guarantees of the old module (`0d37cf7`): no forecast for LOW_DATA topics, and a model whose backtest predictions are not finite never wins (no finite naive baseline → no forecast) — each keeps a test in the new file; the v1.1 export's own LOW_DATA gate in `build_atlas` stays as it is.
- Produces:
  - `atlas.forecast`: `FORECAST_COLUMNS` (`topic_id, model, backtest_mae, backtest_mape, mase, skill_vs_naive, show, hist_years, hist_counts, fc_years, fc_mean, fc_lo, fc_hi, fc_lo80, fc_hi80, fc_lo95, fc_hi95, nowcast_year, nowcast_month, nowcast_ytd, nowcast_mean`; JSON-string lists as in P0, `fc_lo/fc_hi` = the 95 % bounds so the v1.1 export keeps working), `holt_damped`, `total_forecast`, `nb_trend`, `share_forecast`, `predict_counts`, `dispersion`, `nb_sigma`, `origins`, `choose_total_model`, `backtest_topic`, `honest_records`, `conformal_factors`, `month_fraction`, `forecast_all(series, totals, last_year, fcfg, horizon=None) -> (rows, meta)`, `holdout_coverage`, `rolling_coverage(series, totals, last_year, fcfg, n_cuts=3)`, `forecast(cfg)` → `work/08_forecasts`, `work/08_forecast_meta.json` (`total_model, total_years, total_mean, conformal{h:{level:q}}, n_calibration, nowcast{year, as_of_month, fraction, ytd, mean} | null`).
  - Config `forecast.{horizon, min_history_years, models ⊆ [naive, drift, nb_glm, ets_damped], total_models ⊆ [naive, drift, ets_damped], cv_origins ≥ 3, min_train_years, min_skill, max_mase, min_calibration, nowcast.{enabled, min_months, profile_years, as_of}}` (`backtest_years` is gone).

- [ ] **Step 1: Write the failing tests** — replace `pipeline/tests/test_forecast.py` with:

```python
import json

import numpy as np
import pandas as pd
import pytest

from atlas.config import load_config
from atlas.forecast import (
    FORECAST_COLUMNS,
    conformal_factors,
    forecast,
    forecast_all,
    month_fraction,
    origins,
    rolling_coverage,
    total_forecast,
)
from atlas.io_utils import read_table, write_table

FCFG = load_config(None)["forecast"]          # tests lock the shipped defaults
YEARS = list(range(2012, 2025))


def _panel(topics: dict[int, list[float]], totals: list[float]):
    rows = [{"topic_id": t, "year": y, "count": int(c)} for t, cs in topics.items() for y, c in zip(YEARS, cs)]
    return pd.DataFrame(rows), pd.Series(dict(zip(YEARS, totals)))


def test_steady_share_trend_is_skilful_and_shown():
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(N[i] * 0.02 * 1.08 ** i) for i in range(13)]}, N)
    rows, meta = forecast_all(s, tot, 2024, FCFG)
    r = rows.iloc[0]
    assert r["model"] != "naive" and r["show"] and r["mase"] < 1 and r["skill_vs_naive"] > 0
    mean, lo80, hi80 = (json.loads(r[k]) for k in ("fc_mean", "fc_lo80", "fc_hi80"))
    lo95, hi95 = json.loads(r["fc_lo95"]), json.loads(r["fc_hi95"])
    assert json.loads(r["fc_years"]) == [2025, 2026] and mean[1] > mean[0] > s["count"].iloc[-1]
    assert all(a <= b <= c <= d for a, b, c, d in zip(lo95, lo80, hi80, hi95))
    assert meta["total_model"] in FCFG["total_models"]


def test_unpredictable_series_is_not_shown():
    rng = np.random.default_rng(3)
    s, tot = _panel({1: list(rng.choice([20, 200], 13))}, [10_000] * 13)
    r = forecast_all(s, tot, 2024, FCFG)[0].iloc[0]
    assert not r["show"]


def test_history_is_raw_and_starts_at_the_first_article():
    cnt = [0, 0, 10, 12, 500, 14, 15, 16, 18, 19, 20, 22, 23]
    r = forecast_all(*_panel({1: cnt}, [5000] * 13), 2024, FCFG)[0].iloc[0]
    assert json.loads(r["hist_years"])[0] == 2014 and 500 in json.loads(r["hist_counts"])


def test_too_short_history_is_skipped():
    s, tot = _panel({1: [0] * 9 + [1, 2, 3, 4]}, [100] * 13)
    assert forecast_all(s, tot, 2024, FCFG)[0].empty


def test_origins_and_total_models():
    assert origins(13, 4, 4) == [8, 9, 10, 11]
    assert origins(6, 4, 4) == [3, 4]
    assert list(total_forecast("drift", np.array([100.0, 110, 120]), 2)) == [130.0, 140.0]
    assert list(total_forecast("naive", np.array([5.0, 7]), 2)) == [7.0, 7.0]


def test_conformal_factor_is_the_finite_sample_quantile():
    q = conformal_factors({1: list(np.arange(1, 21) / 10)}, min_calibration=20)    # scores 0.1 … 2.0
    assert q[1][0.8] == pytest.approx(1.7)                                         # ⌈21·0.8⌉ = 17th smallest
    assert q[1][0.95] == pytest.approx(2.0)
    assert conformal_factors({1: [0.5] * 5}, min_calibration=20)[1][0.95] == pytest.approx(1.959964, rel=1e-5)


def _simulated_panel(seed: int, n_topics: int = 80):
    rng = np.random.default_rng(seed)
    N = np.round(5000 * 1.05 ** np.arange(13))
    topics = {}
    for t in range(n_topics):
        base, b, alpha = rng.uniform(0.002, 0.03), rng.uniform(-0.12, 0.15), rng.uniform(0.0, 0.05)
        mu = N * base * np.exp(b * np.arange(13))
        lam = rng.gamma(1 / alpha, mu * alpha) if alpha > 0 else mu
        topics[t] = list(rng.poisson(lam))
    return _panel(topics, list(N))


def test_80pct_intervals_cover_70_to_90pct_of_held_out_counts():
    s, tot = _simulated_panel(seed=0)
    cov = rolling_coverage(s, tot, 2024, FCFG, n_cuts=3)
    assert cov["n"] == 480                                  # 80 topics × 2 horizons × 3 cut-offs
    assert 0.70 <= cov["coverage80"] <= 0.90 and cov["coverage95"] >= 0.85
    assert cov["n_shown"] > 0 and cov["max_mase_shown"] < 1.0


def test_month_fraction():
    months = pd.DataFrame({"year": [2023] * 12, "month": range(1, 13), "count": [10] * 12})
    assert month_fraction(months, [2023], 3) == pytest.approx(0.25)
    assert month_fraction(months, [2020], 3) == 0.0


def test_forecast_step_writes_v2_columns_and_nowcast(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(n * 0.05) for n in N], 2: [round(n * 0.02 * 1.1 ** i) for i, n in enumerate(N)]}, N)
    s["corpus_total"] = s["year"].map(tot)
    write_table(s, work / "06_series.parquet")
    (work / "06_meta.json").write_text(json.dumps({
        "last_complete_year": 2024, "years": YEARS, "totals": {str(y): int(n) for y, n in tot.items()},
        "partial_totals": {"2025": 400}}), encoding="utf-8")
    months = pd.DataFrame([{"year": y, "month": m, "count": 10} for y in range(2022, 2026) for m in range(1, 13)
                           if y < 2025 or m <= 4])
    write_table(months, work / "06_months.parquet")
    write_table(pd.DataFrame({"topic_id": [1, 2], "year": 2025, "count": [30, 20]}), work / "06_partial_year.parquet")
    out = forecast(cfg)
    assert list(out.columns) == FORECAST_COLUMNS and len(out) == 2
    assert (out["nowcast_year"] == 2025).all() and (out["nowcast_month"] == 4).all()
    assert out.set_index("topic_id")["nowcast_mean"].to_dict() == {1: 90.0, 2: 60.0}       # ytd ÷ (4/12)
    meta = json.loads((work / "08_forecast_meta.json").read_text(encoding="utf-8"))
    assert meta["nowcast"] == {"year": 2025, "as_of_month": 4, "fraction": 0.3333, "ytd": 400, "mean": 1200.0}
    assert read_table(work / "08_forecasts.parquet")["show"].dtype == bool


def test_low_data_topics_get_no_forecast(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(n * 0.05) for n in N], 2: [round(n * 0.03) for n in N]}, N)
    write_table(s, work / "06_series.parquet")
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024, "years": YEARS,
                                                   "totals": {str(y): int(n) for y, n in tot.items()}}),
                                       encoding="utf-8")
    write_table(pd.DataFrame({"topic_id": [1, 2], "status": ["STABLE", "LOW_DATA"]}), work / "07_emerging.parquet")
    assert forecast(cfg)["topic_id"].tolist() == [1]           # no trend claim → no forecast either


def test_non_finite_predictions_never_win_and_no_finite_baseline_means_no_forecast(monkeypatch):
    import atlas.forecast as F  # the fix wave guard (0d37cf7), kept by Forecast v2

    real = F.predict_counts
    N = [1000 * 1.05 ** i for i in range(13)]
    s, tot = _panel({1: [round(N[i] * 0.02 * 1.08 ** i) for i in range(13)]}, N)

    def nan_for(bad):
        return lambda m, c, n, n_future: np.full(len(n_future), np.nan) if m in bad else real(m, c, n, n_future)

    monkeypatch.setattr(F, "predict_counts", nan_for({"drift", "nb_glm"}))
    r = forecast_all(s, tot, 2024, FCFG)[0].iloc[0]
    assert r["model"] not in ("drift", "nb_glm") and np.isfinite(r["backtest_mae"])
    monkeypatch.setattr(F, "predict_counts", nan_for({"naive"}))
    assert forecast_all(s, tot, 2024, FCFG)[0].empty            # no finite baseline → no skill → no forecast
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_forecast.py -q`
Expected: FAIL — `ImportError: cannot import name 'conformal_factors' from 'atlas.forecast'`.

- [ ] **Step 3: Config** — `pipeline/atlas/config.py`:

Replace
```python
class ForecastCfg(_Strict):
    horizon: int = 2
    min_history_years: int = 6
    models: list[Literal["naive", "linear", "poisson"]] = Field(
        default_factory=lambda: ["naive", "linear", "poisson"])
    backtest_years: int = 3
    min_skill: float = 0.0
```
with
```python
class NowcastCfg(_Strict):
    enabled: bool = True
    min_months: int = Field(3, ge=1, le=12)
    profile_years: int = Field(3, ge=1)
    as_of: str | None = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class ForecastCfg(_Strict):
    horizon: int = Field(2, ge=1)
    min_history_years: int = Field(6, ge=3)
    models: list[Literal["naive", "drift", "nb_glm", "ets_damped"]] = Field(
        default_factory=lambda: ["naive", "drift", "nb_glm", "ets_damped"])
    total_models: list[Literal["naive", "drift", "ets_damped"]] = Field(
        default_factory=lambda: ["naive", "drift", "ets_damped"])
    cv_origins: int = Field(4, ge=3)
    min_train_years: int = Field(4, ge=3)
    min_skill: float = 0.0
    max_mase: float = Field(1.0, gt=0.0)
    min_calibration: int = Field(20, ge=1)
    nowcast: NowcastCfg = Field(default_factory=NowcastCfg)
```
`pipeline/config.example.yaml`:
Replace
```yaml
forecast:
  horizon: 2
  min_history_years: 6
  models: [naive, linear, poisson]
  backtest_years: 3
  min_skill: 0.0              # แสดงตัวเลขเฉพาะเมื่อ skill เทียบ naive > ค่านี้ (ไม่งั้น "แนวโน้มไม่แน่นอน")
```
with
```yaml
# ---------- Forecast v2 — share × ยอดรวม corpus ----------
forecast:
  horizon: 2                  # พยากรณ์ล่วงหน้า 2 ปี
  min_history_years: 6        # หัวข้อที่มีประวัติน้อยกว่านี้ไม่พยากรณ์
  models: [naive, drift, nb_glm, ets_damped]   # naive = "เท่าปีล่าสุด" (baseline); ที่เหลือพยากรณ์ share × ยอดรวม
  total_models: [naive, drift, ets_damped]     # โมเดลพยากรณ์ยอดรวมทั้ง corpus
  cv_origins: 4               # rolling-origin backtest จาก 4 จุดตั้งต้น (≥ 3)
  min_train_years: 4          # จุดตั้งต้นต้องมีข้อมูลฝึกอย่างน้อยเท่านี้
  min_skill: 0.0              # แสดงตัวเลขเฉพาะเมื่อ skill เทียบ naive > ค่านี้ (ไม่งั้น "แนวโน้มไม่แน่นอน")
  max_mase: 1.0               # ... และ MASE < ค่านี้
  min_calibration: 20         # ค่าคลาดเคลื่อนจาก backtest อย่างน้อยเท่านี้ต่อ horizon จึงใช้ conformal (ไม่งั้นใช้ normal)
  nowcast:                    # ประมาณยอดทั้งปีของปีที่ยังไม่ครบ จากยอดสะสมตามเดือนตีพิมพ์
    enabled: true
    min_months: 3             # ต้องมีข้อมูลอย่างน้อย 3 เดือนแรกของปี
    profile_years: 3          # สัดส่วนรายเดือนจาก 3 ปีที่สมบูรณ์ล่าสุด
    as_of: null               # "YYYY-MM" — null = เดือนล่าสุดที่พบในปีนั้น
```

- [ ] **Step 4: Replace `pipeline/atlas/forecast.py`** (read the current file first: the fix wave's LOW_DATA exclusion and non-finite-MAE filter are subsumed — LOW_DATA is skipped in `forecast()`, and every model's backtest is exception-safe and finite-only in `backtest_topic`)

```python
"""Forecast v2 — share × corpus total, rolling-origin CV, MASE, conformal intervals, skill gate, nowcast.

count_t = share_t × N_t. The corpus total N is forecast once (best of forecast.total_models by
rolling-origin MAE); each topic's share is forecast by every model and the count forecast is
share forecast × N forecast — so topic numbers stay consistent with the corpus total.

Models (forecast.models):
  naive       ĉ = c_T                                   — the baseline ("same as last year")
  drift       share_T + h·(share_T − share_1)/(T − 1)   × N̂
  nb_glm      NB2 GLM  log E[c_t] = log N_t + a + b·t    × N̂   (α by moments, offset = corpus size)
  ets_damped  damped-trend Holt (statsmodels) on share  × N̂

Rolling-origin CV: origins o = T−cv_origins … T−1, horizons h ≤ horizon with o + h ≤ T; an origin
trains on years ≤ o only (≥ min_train_years) — including the N̂ it uses. The published model is the one
with the lowest MAE pooled over every (o, h). Skill is scored honestly, without reusing the data that
picked the model: at each origin after the first, the model chosen from EARLIER origins is evaluated
(honest_records). MASE = that MAE / mean|c_t − c_{t−1}| over the history; skill = 1 − MAE / MAE(naive).
Shown only when best ≠ naive, skill > min_skill and MASE < max_mase ("แนวโน้มไม่แน่นอน" otherwise).

Intervals 80/95%: NB2 scale σ(μ) = sqrt(μ + α·μ²) with the topic's α; split-conformal factor
q_h = the ⌈(n+1)·level⌉-th smallest |c − ĉ| / σ over ALL topics' CV errors at horizon h; interval
ĉ ± q_h·σ floored at 0. Fewer than min_calibration scores → normal quantiles (1.2816 / 1.9600).

Nowcast: partial year Y = last_complete_year + 1. full-year estimate = ytd / f(m), f(m) = share of
a year's articles published by month m in the last profile_years complete years.
Outputs: work/08_forecasts, work/08_forecast_meta.json
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

FORECAST_COLUMNS = ["topic_id", "model", "backtest_mae", "backtest_mape", "mase", "skill_vs_naive", "show",
                    "hist_years", "hist_counts", "fc_years", "fc_mean", "fc_lo", "fc_hi",
                    "fc_lo80", "fc_hi80", "fc_lo95", "fc_hi95",
                    "nowcast_year", "nowcast_month", "nowcast_ytd", "nowcast_mean"]
LEVELS = (0.8, 0.95)
SHARE_MODELS = ("drift", "nb_glm", "ets_damped")


# ------------------------------------------------------------------ models
def holt_damped(y: np.ndarray, h: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    scale = float(np.abs(y).max()) or 1.0
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(y / scale, trend="add", damped_trend=True,
                                   initialization_method="estimated").fit()
        out = np.asarray(fit.forecast(h), dtype=float) * scale
    if not np.isfinite(out).all():
        raise ValueError("ETS produced non-finite values")
    return out


def total_forecast(model: str, N: np.ndarray, h: int) -> np.ndarray:
    N = np.asarray(N, dtype=float)
    if model == "naive":
        out = np.repeat(N[-1], h)
    elif model == "drift":
        out = N[-1] + np.arange(1, h + 1) * (N[-1] - N[0]) / max(len(N) - 1, 1)
    elif model == "ets_damped":
        out = holt_damped(N, h)
    else:
        raise ValueError(model)
    return np.maximum(out, 1.0)


def nb_trend(c: np.ndarray, N: np.ndarray) -> tuple[float, float, float, float]:
    """log E[c_t] = log N_t + a + b·(t − t̄) → (a, b, alpha, t̄) with NB2 alpha by moments."""
    import statsmodels.api as sm

    t = np.arange(len(c), dtype=float)
    tm = float(t.mean())
    X = sm.add_constant(t - tm, has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pois = sm.GLM(c, X, family=sm.families.Poisson(), offset=np.log(N)).fit()
        mu = np.asarray(pois.fittedvalues, dtype=float)
        dof = max(len(c) - 2, 1)
        alpha = float(np.clip(np.sum(((c - mu) ** 2 - mu) / np.maximum(mu, 1e-9) ** 2) / dof, 1e-6, 10.0))
        nb = sm.GLM(c, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=np.log(N)).fit()
    a, b = (float(v) for v in nb.params)
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError("NB GLM did not converge")
    return a, b, alpha, tm


def share_forecast(model: str, c: np.ndarray, N: np.ndarray, h: int) -> np.ndarray:
    s = c / N
    steps = np.arange(1, h + 1)
    if model == "drift":
        out = s[-1] + steps * (s[-1] - s[0]) / max(len(s) - 1, 1)
    elif model == "nb_glm":
        a, b, _, tm = nb_trend(c, N)
        out = np.exp(a + b * (len(c) - 1 + steps - tm))
    elif model == "ets_damped":
        out = holt_damped(s, h)
    else:
        raise ValueError(model)
    return np.clip(out, 0.0, 1.0)


def predict_counts(model: str, c: np.ndarray, N: np.ndarray, N_future: np.ndarray) -> np.ndarray:
    if model == "naive":
        return np.repeat(float(c[-1]), len(N_future))
    return share_forecast(model, c, N, len(N_future)) * N_future


def dispersion(c: np.ndarray, N: np.ndarray) -> float:
    """NB2 alpha of a topic (0 = Poisson); falls back to 0.1 when the trend model cannot be fitted."""
    try:
        return nb_trend(c, N)[2]
    except Exception:  # noqa: BLE001
        return 0.1


def nb_sigma(mu: np.ndarray, alpha: float) -> np.ndarray:
    mu = np.maximum(np.asarray(mu, dtype=float), 0.0)
    return np.sqrt(mu + alpha * mu ** 2) + 0.5          # +0.5: a count interval is never narrower than ±½


# ------------------------------------------------------------------ backtest
def origins(n_years: int, cv_origins: int, min_train: int) -> list[int]:
    """Index of the last training year for each rolling origin (needs ≥ min_train training years)."""
    return [o for o in range(n_years - 1 - cv_origins, n_years - 1) if o + 1 >= min_train]


def choose_total_model(N: np.ndarray, models: list[str], horizon: int, cv_origins: int, min_train: int) -> str:
    errs: dict[str, list[float]] = {m: [] for m in models}
    for o in origins(len(N), cv_origins, min_train):
        h = min(horizon, len(N) - 1 - o)
        for m in models:
            try:
                errs[m] += list(np.abs(N[o + 1:o + 1 + h] - total_forecast(m, N[:o + 1], h)))
            except Exception:  # noqa: BLE001
                errs[m].append(math.inf)
    mae = {m: float(np.mean(e)) if e else math.inf for m, e in errs.items()}
    return min(models, key=lambda m: (mae[m], models.index(m)))


def backtest_topic(c: np.ndarray, N: np.ndarray, models: list[str], n_hat: dict[int, np.ndarray], offset: int,
                   horizon: int, cv_origins: int, min_train: int) -> dict[str, list[tuple[int, int, float, float, float]]]:
    """model → [(origin, h, actual, predicted, sigma)] over all rolling origins; models that fail anywhere are dropped.

    c, N start at the topic's first year = index `offset` of the corpus years; n_hat[i] is the corpus-total
    forecast made with corpus years [0..i] only (no look-ahead).
    """
    out: dict[str, list] = {m: [] for m in models}
    failed: set[str] = set()
    for o in origins(len(c), cv_origins, min_train):
        h = min(horizon, len(c) - 1 - o)
        N_hat = n_hat[offset + o][:h]
        alpha = dispersion(c[:o + 1], N[:o + 1])
        for m in models:
            if m in failed:
                continue
            try:
                p = np.maximum(predict_counts(m, c[:o + 1], N[:o + 1], N_hat), 0.0)
            except Exception:  # noqa: BLE001 — a model that cannot fit this origin is out for the topic
                failed.add(m)
                continue
            if not np.isfinite(p).all():                 # NaN/inf predictions never enter the MAE
                failed.add(m)
                continue
            sig = nb_sigma(p, alpha)
            out[m] += [(o, k + 1, float(c[o + 1 + k]), float(p[k]), float(sig[k])) for k in range(h)]
    return {m: v for m, v in out.items() if m not in failed and v}


def _mae(recs) -> float:
    return float(np.mean([abs(a - p) for _, _, a, p, _ in recs])) if recs else math.inf


def honest_records(bt: dict[str, list], models: list[str]) -> tuple[list, list]:
    """Errors of the model that would have been CHOSEN at each origin using only earlier origins.

    Model choice and skill scoring must not share data: at origin k the model with the lowest MAE over
    origins < k is "selected", and its error at k is what skill and MASE use.
    The first origin only seeds the choice. → (selected-model records, naive records) on the same points.
    (Interval calibration keeps using the published model's own CV errors — see conformal_factors.)
    """
    oks = sorted({r[0] for v in bt.values() for r in v})
    chosen, naive = [], []
    for o in oks[1:]:
        prior = {m: _mae([r for r in v if r[0] < o]) for m, v in bt.items()}
        sel = min(prior, key=lambda m: (prior[m], models.index(m)))
        chosen += [r for r in bt[sel] if r[0] == o]
        naive += [r for r in bt["naive"] if r[0] == o]
    return chosen, naive


def conformal_factors(scores: dict[int, list[float]], min_calibration: int) -> dict[int, dict[float, float]]:
    """horizon → {level: factor} from pooled normalised CV errors (split conformal)."""
    out: dict[int, dict[float, float]] = {}
    for h, s in scores.items():
        s = np.sort(np.asarray(s, dtype=float))
        out[h] = {}
        for lv in LEVELS:
            if len(s) < min_calibration:
                out[h][lv] = NormalDist().inv_cdf(0.5 + lv / 2)
            else:
                k = min(math.ceil((len(s) + 1) * lv), len(s)) - 1
                out[h][lv] = float(s[k])
    return out


# ------------------------------------------------------------------ nowcast
def month_fraction(months: pd.DataFrame, years: list[int], as_of: int) -> float:
    """Share of the articles of `years` published in months ≤ as_of (months: year, month, count)."""
    sub = months[months["year"].isin(years)]
    total = float(sub["count"].sum())
    return float(sub.loc[sub["month"] <= as_of, "count"].sum()) / total if total else 0.0


# ------------------------------------------------------------------ all topics
def forecast_all(series: pd.DataFrame, totals: pd.Series, last_year: int, fcfg: dict,
                 horizon: int | None = None) -> tuple[pd.DataFrame, dict]:
    """series: topic_id, year, count (years ≤ last_year) · totals: corpus articles by year (index = year)."""
    H = int(horizon or fcfg["horizon"])
    cvo, mtr = int(fcfg["cv_origins"]), int(fcfg["min_train_years"])
    years = [y for y in sorted(int(y) for y in totals.index) if y <= last_year]
    N = totals.reindex(years).to_numpy(dtype=float)
    models = list(dict.fromkeys(["naive", *fcfg["models"]]))
    total_model = choose_total_model(N, list(fcfg["total_models"]), H, cvo, mtr)
    n_hat = {i: total_forecast(total_model, N[:i + 1], H) for i in range(max(0, len(N) - 1 - cvo), len(N) - 1)}
    N_future = total_forecast(total_model, N, H)
    fut_years = list(range(last_year + 1, last_year + 1 + H))

    fits, scores = [], {h: [] for h in range(1, H + 1)}
    for tid, g in series[series["year"] <= last_year].groupby("topic_id"):
        cnt = g.set_index("year")["count"].reindex(years, fill_value=0).to_numpy(dtype=float)
        first = int(np.argmax(cnt > 0)) if cnt.any() else len(cnt)
        c, Nt = cnt[first:], N[first:]                      # history starts at the topic's first article
        if len(c) < int(fcfg["min_history_years"]) or c.sum() == 0:
            continue
        bt = backtest_topic(c, Nt, models, n_hat, first, H, cvo, mtr)
        if "naive" not in bt:
            continue
        mae = {m: _mae(v) for m, v in bt.items()}
        best = min(mae, key=lambda m: (mae[m], models.index(m)))       # final model: all origins; naive wins ties
        chosen, naive = honest_records(bt, models)
        if not chosen:                                   # a single origin cannot score a selection honestly
            continue
        mae_sel, mae_naive = _mae(chosen), _mae(naive)
        mape = float(np.mean([abs(a - p) / max(a, 1.0) for _, _, a, p, _ in chosen]) * 100)
        scale = float(np.mean(np.abs(np.diff(c)))) if len(c) > 1 else 0.0
        mase = round(mae_sel / scale, 3) if scale > 0 else math.nan       # gate on the value we publish
        skill = 1 - mae_sel / mae_naive if mae_naive > 0 else 0.0
        for _, h, a, p, s in bt[best]:                  # interval calibration: the published model's CV errors
            scores[h].append(abs(a - p) / s)
        fits.append({"topic_id": int(tid), "best": best, "c": c, "N": Nt, "years": years[first:],
                     "mae": mae_sel, "mape": mape, "mase": mase, "skill": skill})

    q = conformal_factors(scores, int(fcfg["min_calibration"]))
    rows = []
    for f in fits:
        mean = np.maximum(predict_counts(f["best"], f["c"], f["N"], N_future), 0.0)
        sig = nb_sigma(mean, dispersion(f["c"], f["N"]))
        show = bool(f["best"] != "naive" and f["skill"] > float(fcfg["min_skill"])
                    and math.isfinite(f["mase"]) and f["mase"] < float(fcfg["max_mase"]))
        lo = {lv: [round(max(float(mean[i] - q[i + 1][lv] * sig[i]), 0.0), 1) for i in range(H)] for lv in LEVELS}
        hi = {lv: [round(float(mean[i] + q[i + 1][lv] * sig[i]), 1) for i in range(H)] for lv in LEVELS}
        rows.append({
            "topic_id": f["topic_id"], "model": f["best"],
            "backtest_mae": round(f["mae"], 2), "backtest_mape": round(f["mape"], 2),
            "mase": f["mase"] if math.isfinite(f["mase"]) else None,
            "skill_vs_naive": round(f["skill"], 3), "show": show,
            "hist_years": json.dumps([int(y) for y in f["years"]]),
            "hist_counts": json.dumps([int(v) for v in f["c"]]),
            "fc_years": json.dumps(fut_years), "fc_mean": json.dumps([round(float(v), 1) for v in mean]),
            "fc_lo": json.dumps(lo[0.95]), "fc_hi": json.dumps(hi[0.95]),
            "fc_lo80": json.dumps(lo[0.8]), "fc_hi80": json.dumps(hi[0.8]),
            "fc_lo95": json.dumps(lo[0.95]), "fc_hi95": json.dumps(hi[0.95]),
        })
    meta = {"total_model": total_model, "total_years": fut_years,
            "total_mean": [round(float(v), 1) for v in N_future],
            "conformal": {str(h): {str(lv): round(v, 4) for lv, v in d.items()} for h, d in q.items()},
            "n_calibration": {str(h): len(s) for h, s in scores.items()}}
    return pd.DataFrame(rows, columns=[c for c in FORECAST_COLUMNS if not c.startswith("nowcast")]), meta


def holdout_coverage(series: pd.DataFrame, totals: pd.Series, last_year: int, fcfg: dict, holdout: int = 2) -> dict:
    """Honest check: forecast from last_year − holdout with everything (incl. calibration) fitted on the
    truncated data, then compare the 80/95% intervals and MASE with the held-out actual counts."""
    cut = last_year - holdout
    rows, _ = forecast_all(series[series["year"] <= cut], totals[totals.index <= cut], cut, fcfg, horizon=holdout)
    actual = series.set_index(["topic_id", "year"])["count"]
    hit80 = hit95 = n = 0
    for r in rows.itertuples():
        for i, y in enumerate(json.loads(r.fc_years)):
            a = float(actual.get((r.topic_id, y), 0))
            hit80 += json.loads(r.fc_lo80)[i] <= a <= json.loads(r.fc_hi80)[i]
            hit95 += json.loads(r.fc_lo95)[i] <= a <= json.loads(r.fc_hi95)[i]
            n += 1
    shown = rows[rows["show"]]
    return {"n": n, "coverage80": hit80 / n if n else math.nan, "coverage95": hit95 / n if n else math.nan,
            "n_shown": int(len(shown)), "max_mase_shown": float(shown["mase"].max()) if len(shown) else math.nan}


def rolling_coverage(series: pd.DataFrame, totals: pd.Series, last_year: int, fcfg: dict, n_cuts: int = 3) -> dict:
    """holdout_coverage at the published horizon from n_cuts successive cut-off years, pooled.

    One cut-off gives few points (topics × horizon); pooling several makes the coverage estimate steady.
    """
    H = int(fcfg["horizon"])
    res = [holdout_coverage(series[series["year"] <= end], totals[totals.index <= end], end, fcfg, holdout=H)
           for end in range(last_year, last_year - n_cuts, -1)]
    n = sum(r["n"] for r in res)
    shown = [r["max_mase_shown"] for r in res if r["n_shown"]]
    return {"n": n, "cuts": n_cuts,
            "coverage80": sum(r["coverage80"] * r["n"] for r in res if r["n"]) / n if n else math.nan,
            "coverage95": sum(r["coverage95"] * r["n"] for r in res if r["n"]) / n if n else math.nan,
            "n_shown": sum(r["n_shown"] for r in res), "max_mase_shown": max(shown) if shown else math.nan}


def forecast(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    f = cfg["forecast"]
    series = read_table(work / "06_series.parquet")
    em_path = work / "07_emerging.parquet"
    if em_path.exists():                       # LOW_DATA topics get no forecast (they get no trend claim either)
        em = read_table(em_path)
        series = series[~series["topic_id"].isin(set(em.loc[em["status"] == "LOW_DATA", "topic_id"]))]
    meta6 = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    last = int(meta6["last_complete_year"])
    totals = pd.Series({int(y): int(n) for y, n in meta6["totals"].items()}).sort_index()
    if len(series) and len(totals) >= int(f["min_history_years"]):
        out, meta = forecast_all(series, totals, last, f)
    else:
        out, meta = pd.DataFrame(columns=FORECAST_COLUMNS[:17]), {"total_model": None}
    out = out.reindex(columns=FORECAST_COLUMNS)
    meta["nowcast"] = None
    nc = f["nowcast"]
    months_path, partial_path = work / "06_months.parquet", work / "06_partial_year.parquet"
    if nc["enabled"] and months_path.exists() and partial_path.exists():
        months, partial = read_table(months_path), read_table(partial_path)
        year = last + 1
        in_year = months[months["year"] == year]
        as_of = int(nc["as_of"][5:7]) if nc["as_of"] else (int(in_year["month"].max()) if len(in_year) else 0)
        prof_years = list(range(last - int(nc["profile_years"]) + 1, last + 1))
        frac = month_fraction(months, prof_years, as_of) if as_of else 0.0
        if as_of >= int(nc["min_months"]) and frac > 0:
            ytd = partial[partial["year"] == year].set_index("topic_id")["count"]
            total_ytd = int(meta6.get("partial_totals", {}).get(str(year), int(ytd.sum())))
            meta["nowcast"] = {"year": year, "as_of_month": as_of, "fraction": round(frac, 4),
                               "ytd": total_ytd, "mean": round(total_ytd / frac, 1)}
            out["nowcast_year"], out["nowcast_month"] = year, as_of
            out["nowcast_ytd"] = out["topic_id"].map(ytd).fillna(0).astype(int)
            out["nowcast_mean"] = (out["nowcast_ytd"] / frac).round(1)
    write_table(out, work / "08_forecasts.parquet")
    (work / "08_forecast_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    shown = int(out["show"].astype(bool).sum()) if len(out) else 0
    print(f"[forecast] {len(out)} topics forecast, {shown} skilful enough to show; total model {meta['total_model']}")
    return out
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_forecast.py -q && uv run pytest -q`
Expected: all pass (the coverage test takes ~20 s). `tests/test_export.py` builds its own forecast frames with the P0 columns, which the v1.1 export still reads.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/forecast.py pipeline/tests/test_forecast.py pipeline/atlas/config.py pipeline/config.example.yaml
git commit -m "feat(forecast): v2 — share × total, NB GLM / damped ETS / drift vs naive, rolling-origin CV, honest skill gate, conformal 80/95 intervals, nowcast

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 12: Emerging keywords (term level, independent of clustering)

Carley/Newman/Porter/Garner-style emergence for author keywords (TH + EN folded by `norm_key`): novel (share ratio R/B ≥ 2, B smoothed by half an article; generic terms in > 15 % of documents dropped), persistent (≥ 3 of the W years), communal (≥ 3 institutions, ≥ 3 journals, < 50 % from journals new in R), growing (lower CI bound of the share growth — the same v3 `share_growth` as topics — > 0), ≥ 7 documents in R. Terms absent from B get `no_baseline: true` (their ratio only reflects the smoothing; published as null). On the 20K synthetic corpus all 12 planted generative-AI terms came out emerging and all 12 Buddhism-online terms journal-driven.

**Files:**
- Create: `pipeline/atlas/keywords.py`, `pipeline/tests/test_keywords.py`
- Modify: `pipeline/atlas/pipeline.py` (step `keywords` after `emerging`)

**Interfaces:**
- Consumes: v3 `emerging.share_growth(counts, totals, years, ci_level, max_abs_log_growth)`, `thai.norm_key`; `02_docs` (keywords_th/en, journal_name, year), `01_authors` (org_key), `06_meta.json`, `06_journal_first_year`, `04_fine_topics`; config `keywords.*` (Task 1), `emerging.{recent_window, baseline_window, trend_window, ci_level, max_abs_log_growth}`.
- Produces: `KEYWORD_COLUMNS = [term, key, count_recent, count_baseline, share_ratio, no_baseline, growth, growth_lo, growth_hi, n_active_years, n_orgs_R, n_journals_R, new_journal_share, journal_driven, topic_id, emerging]`, `keyword_rows(docs)`, `emerging_keywords(kw, totals, last_year, ecfg, kcfg, orgs, jfirst, topics=None)`, `keywords(cfg)` → `work/07_keywords` (candidates, emerging first; `topic_id` = the topic most of the term's R articles belong to, −1 if none).

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_keywords.py`:

```python
import json

import pandas as pd

from atlas.config import load_config
from atlas.io_utils import read_table, write_table
from atlas.keywords import KEYWORD_COLUMNS, emerging_keywords, keyword_rows, keywords

CFG = load_config(None)
YEARS = list(range(2015, 2025))              # last complete 2024 → R 2022–24, B 2017–21, W 2020–24
OLD_J = ["jA", "jB", "jC", "jD"]


def _docs():
    """filler docs + planted terms: rising (4 journals, 5 orgs), rising-but-one-new-journal, generic, flat."""
    rows, authors, n = [], [], 0

    def add(year, journal, kw_en, org):
        nonlocal n
        rows.append({"article_id": f"a{n}", "year": year, "journal_name": journal, "keywords_th": "",
                     "keywords_en": kw_en})
        authors.append({"article_id": f"a{n}", "org_key": org})
        n += 1

    rising = {2017: 1, 2019: 1, 2020: 2, 2021: 3, 2022: 8, 2023: 16, 2024: 30}
    for y in YEARS:
        for i in range(200):
            add(y, OLD_J[i % 4], "survey; filler", f"org{i % 6}")
        for i in range(rising.get(y, 0)):
            add(y, OLD_J[i % 4], "ChatGPT; survey", f"org{i % 5}")
            add(y, "jNew" if y >= 2022 else OLD_J[i % 4], "Buddhism online", f"org{i % 5}")
        for i in range(10):
            add(y, OLD_J[i % 4], "Steady Topic", f"org{i % 5}")
        for i in range({2022: 3, 2023: 4, 2024: 5}.get(y, 0)):
            add(y, OLD_J[i % 4], "LLM agents", f"org{i % 2}")      # new in R (no baseline), only 2 orgs
    return pd.DataFrame(rows).astype({"year": "Int64"}), pd.DataFrame(authors)


def test_keyword_rows_fold_case_spacing_and_duplicates():
    docs = pd.DataFrame({"article_id": ["a"], "year": [2020], "journal_name": ["j"],
                         "keywords_th": ["การศึกษา; การศึกษา "], "keywords_en": ["ChatGPT; chat gpt; x"]})
    kw = keyword_rows(docs)
    assert sorted(kw["key"]) == ["chatgpt", "การศึกษา"]          # 1-char key dropped, "chat gpt" = "ChatGPT"


def test_emerging_requires_novelty_persistence_breadth_and_growth():
    docs, authors = _docs()
    kw = keyword_rows(docs)
    totals = docs.groupby("year").size()
    totals.index = totals.index.astype(int)
    jfirst = docs.groupby("journal_name")["year"].min().rename("first_year").reset_index().rename(
        columns={"journal_name": "journal"})
    raw = emerging_keywords(kw, totals, 2024, CFG["emerging"], CFG["keywords"], authors, jfirst)
    assert list(raw.columns) == KEYWORD_COLUMNS
    out = raw.set_index("key")
    assert bool(out.loc["chatgpt", "emerging"]) and out.loc["chatgpt", "term"] == "ChatGPT"
    assert bool(out.loc["buddhismonline", "journal_driven"]) and not bool(out.loc["buddhismonline", "emerging"])
    assert "survey" not in out.index                                # in > 15% of documents → generic
    assert "steadytopic" not in out.index                           # no novelty (share ratio ≈ 1)
    assert out.index[0] == "chatgpt"                                # emerging terms sort first
    assert bool(out.loc["llmagents", "no_baseline"]) and not bool(out.loc["chatgpt", "no_baseline"])
    assert not bool(out.loc["llmagents", "emerging"])               # 2 institutions < min_orgs


def test_keywords_step_and_disabled_switch(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    docs, authors = _docs()
    write_table(docs, work / "02_docs.parquet")
    write_table(authors, work / "01_authors.parquet")
    write_table(pd.DataFrame({"article_id": docs["article_id"], "fine_topic": 1}), work / "04_fine_topics.parquet")
    totals = docs.groupby("year").size()
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024,
                                                   "totals": {str(int(y)): int(n) for y, n in totals.items()}}),
                                       encoding="utf-8")
    write_table(docs.groupby("journal_name")["year"].min().astype(int).rename("first_year").reset_index()
                .rename(columns={"journal_name": "journal"}), work / "06_journal_first_year.parquet")
    out = keywords(cfg)
    assert out.set_index("key").loc["chatgpt", "topic_id"] == 1
    assert len(read_table(work / "07_keywords.parquet")) == len(out)
    cfg["keywords"]["enabled"] = False
    assert keywords(cfg).empty and read_table(work / "07_keywords.parquet").empty
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_keywords.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.keywords'`.

- [ ] **Step 3: Create `pipeline/atlas/keywords.py`**

```python
"""Emerging keywords — term-level emergence, independent of clustering (Carley, Newman, Porter & Garner 2018).

Terms = author keywords (TH + EN), grouped by norm_key (case, spacing and lost tone marks fold together);
counts are documents per year. Windows R / B / W are the Emerging windows (emerging.*). A term is
emerging when it is
  novel       share_R / share_B ≥ novelty_min_ratio (B smoothed by half an article) and it is not a
              generic term (in ≤ max_doc_share of all documents)
  persistent  present in ≥ min_active_years of the W years
  communal    ≥ min_orgs institutions in R, and not journal-driven (≥ min_journals journals in R and
              < max_new_journal_share of its R documents from journals that entered in R)
  growing     lower CI bound of its share growth (emerging.share_growth, same as topics) > min_growth_lo
  big enough  ≥ min_docs_recent documents in R
no_baseline marks terms absent from B: their share_ratio only reflects the smoothing (published as null).
Output: work/07_keywords (candidates, emerging first).
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.emerging import share_growth
from atlas.io_utils import read_table, write_table
from atlas.thai import norm_key

KEYWORD_COLUMNS = ["term", "key", "count_recent", "count_baseline", "share_ratio", "no_baseline", "growth", "growth_lo",
                   "growth_hi", "n_active_years", "n_orgs_R", "n_journals_R", "new_journal_share",
                   "journal_driven", "topic_id", "emerging"]


def keyword_rows(docs: pd.DataFrame) -> pd.DataFrame:
    """One row per (article, keyword key): article_id, year, journal, key, term."""
    rows = []
    for aid, year, journal, th, en in zip(docs["article_id"], docs["year"], docs["journal_name"],
                                          docs["keywords_th"].fillna("").astype(str),
                                          docs["keywords_en"].fillna("").astype(str)):
        if pd.isna(year):
            continue
        seen = set()
        for term in (t.strip() for t in f"{th};{en}".split(";")):
            key = norm_key(term)
            if len(key) >= 2 and key not in seen:
                seen.add(key)
                rows.append((aid, int(year), journal, key, term))
    return pd.DataFrame(rows, columns=["article_id", "year", "journal", "key", "term"])


def emerging_keywords(kw: pd.DataFrame, totals: pd.Series, last_year: int, ecfg: dict, kcfg: dict,
                      orgs: pd.DataFrame, jfirst: pd.DataFrame, topics: pd.DataFrame | None = None) -> pd.DataFrame:
    """kw: keyword_rows() · totals: dated articles per year · orgs: article_id, org_key · jfirst: journal, first_year."""
    wR, wB, wW = int(ecfg["recent_window"]), int(ecfg["baseline_window"]), int(ecfg["trend_window"])
    R = list(range(last_year - wR + 1, last_year + 1))
    B = list(range(last_year - wR - wB + 1, last_year - wR + 1))
    W = list(range(last_year - wW + 1, last_year + 1))
    ci, max_log = float(ecfg["ci_level"]), float(ecfg["max_abs_log_growth"])
    kw = kw[kw["year"] <= last_year]
    n_docs = float(totals[totals.index <= last_year].sum())
    N_R, N_B = float(totals.reindex(R, fill_value=0).sum()), float(totals.reindex(B, fill_value=0).sum())
    if kw.empty or N_R == 0:
        return pd.DataFrame(columns=KEYWORD_COLUMNS)

    by_year = kw.groupby(["key", "year"]).size().unstack(fill_value=0)
    cnt_R = by_year.reindex(columns=R, fill_value=0).sum(axis=1)
    cnt_B = by_year.reindex(columns=B, fill_value=0).sum(axis=1)
    doc_share = by_year.sum(axis=1) / max(n_docs, 1.0)
    eps_B = 0.5 / max(N_B, 1.0)
    ratio = (cnt_R / N_R + eps_B) / (cnt_B / max(N_B, 1.0) + eps_B)
    active = (by_year.reindex(columns=W, fill_value=0) > 0).sum(axis=1)
    cand = ((cnt_R >= int(kcfg["min_docs_recent"])) & (doc_share <= float(kcfg["max_doc_share"]))
            & (ratio >= float(kcfg["novelty_min_ratio"])) & (active >= int(kcfg["min_active_years"])))
    keys = cand[cand].index
    if not len(keys):
        return pd.DataFrame(columns=KEYWORD_COLUMNS)

    kR = kw[kw["key"].isin(keys) & kw["year"].isin(R)]
    new_j = set(jfirst.loc[jfirst["first_year"] >= R[0], "journal"])
    org_R = kR[["key", "article_id"]].merge(orgs[orgs["org_key"].astype(str) != ""], on="article_id")
    n_orgs = org_R.groupby("key")["org_key"].nunique()
    n_j = kR.groupby("key")["journal"].nunique()
    new_share = kR.assign(new=kR["journal"].isin(new_j)).groupby("key")["new"].mean()
    display = kw[kw["key"].isin(keys)].groupby("key")["term"].agg(lambda s: Counter(s).most_common(1)[0][0])
    topic_of: dict[str, int] = {}
    if topics is not None and len(topics):
        tk = kR.merge(topics, on="article_id")
        tk = tk[tk["fine_topic"] >= 0]
        topic_of = tk.groupby("key")["fine_topic"].agg(lambda s: int(s.value_counts().index[0])).to_dict()
    tot_W = totals.reindex(W, fill_value=0).to_numpy(dtype=float)

    rows = []
    for key in keys:
        counts_W = by_year.loc[key].reindex(W, fill_value=0).to_numpy(dtype=float)
        g, lo, hi = share_growth(counts_W, tot_W, np.array(W), ci, max_log)
        nj, no, ns = int(n_j.get(key, 0)), int(n_orgs.get(key, 0)), float(new_share.get(key, 0.0))
        driven = nj < int(kcfg["min_journals"]) or ns >= float(kcfg["max_new_journal_share"])
        emerging = (bool(math.isfinite(lo) and lo > float(kcfg["min_growth_lo"]))
                    and no >= int(kcfg["min_orgs"]) and not driven)
        rows.append({"term": display[key], "key": key, "count_recent": int(cnt_R[key]),
                     "count_baseline": int(cnt_B[key]), "share_ratio": float(ratio[key]),
                     "no_baseline": bool(cnt_B[key] == 0),
                     "growth": g, "growth_lo": lo, "growth_hi": hi, "n_active_years": int(active[key]),
                     "n_orgs_R": no, "n_journals_R": nj, "new_journal_share": ns, "journal_driven": driven,
                     "topic_id": topic_of.get(key, -1), "emerging": emerging})
    out = pd.DataFrame(rows, columns=KEYWORD_COLUMNS)
    out["_lo"] = out["growth_lo"].fillna(-math.inf)
    out = out.sort_values(["emerging", "_lo", "count_recent", "key"], ascending=[False, False, False, True])
    return out.drop(columns="_lo").reset_index(drop=True)


def keywords(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    if not cfg["keywords"]["enabled"]:
        out = pd.DataFrame(columns=KEYWORD_COLUMNS)
        write_table(out, work / "07_keywords.parquet")
        return out
    docs = read_table(work / "02_docs.parquet")
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    totals = pd.Series({int(y): int(n) for y, n in meta["totals"].items()}).sort_index()
    try:
        orgs = read_table(work / "01_authors.parquet")[["article_id", "org_key"]]
    except FileNotFoundError:
        orgs = pd.DataFrame(columns=["article_id", "org_key"])
    out = emerging_keywords(keyword_rows(docs), totals, int(meta["last_complete_year"]), cfg["emerging"],
                            cfg["keywords"], orgs.drop_duplicates(), read_table(work / "06_journal_first_year.parquet"),
                            read_table(work / "04_fine_topics.parquet"))
    write_table(out, work / "07_keywords.parquet")
    print(f"[keywords] {len(out)} candidate terms, {int(out['emerging'].sum()) if len(out) else 0} emerging")
    return out
```

- [ ] **Step 4: Register the step** — `pipeline/atlas/pipeline.py`:

Replace
```python
STEPS = ["ingest", "preprocess", "embed", "cluster", "taxonomy", "label", "series", "emerging", "forecast", "layout",
         "export"]
```
with
```python
STEPS = ["ingest", "preprocess", "embed", "cluster", "taxonomy", "label", "series", "emerging", "keywords",
         "forecast", "layout", "export"]
```
After
```python
    "emerging": ("atlas.emerging", "emerging"),
```
insert
```python
    "keywords": ("atlas.keywords", "keywords"),
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_keywords.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/keywords.py pipeline/atlas/pipeline.py pipeline/tests/test_keywords.py
git commit -m "feat(keywords): emerging keywords — novelty, persistence, community breadth, CI growth, no-baseline flag

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 13: Stable map layout across releases + article galaxy

Readers learn where topics sit; a map that reshuffles every quarter destroys that. UMAP starts from last release's positions, the result is aligned back by a similarity Procrustes fit on the continuing topics, and continuing topics are anchored (`anchor` 0.9) to where they were; new topics take their nearest neighbours' shift. Measured on the synthetic two-release run: initialisation alone left a median shift of ~168 px, init + Procrustes + anchor brought it to ~30 px. The galaxy places every assigned article deterministically inside its topic's circle (for the Cartographic `/atlas` view of P1b).

**Files:**
- Modify: `pipeline/atlas/layout.py` (full replacement — keeps the P0 outputs `09_layout`, `09_edges` and the taxonomy group hubs of Task 9)
- Create: `pipeline/tests/test_layout.py`

**Interfaces:**
- Consumes: `04_centroids.npy`, `04_centroid_ids.json`, `04_topic_info`, `04_fine_topics`, `load_aligned` (Task 2), `load_topic_groups` (Task 9), `previous_release`, `release_dir` (Task 1); config `layout.{umap_2d_neighbors, umap_2d_min_dist, view_w, view_h, edge_similarity_threshold, max_edges_per_node, stable, anchor, init_neighbors, galaxy}`.
- Produces: `procrustes_fit(A, B) -> (s, R, t)`, `init_positions(...)`, `topic_positions(ids, C, lcfg, seed, prev_xy) -> (xy, info)`, `galaxy_coords(member_emb, centroid, cx, cy, r) -> (gx, gy)`, `layout(cfg)` → `work/09_layout` (kind, id, x, y, r, parent), `work/09_edges` (s, t, w), `work/09_galaxy` (article_id, topic_id, gx, gy), `state_dir/releases/<release>/layout.parquet` (topic_id, x, y).

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_layout.py`:

```python
import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import read_table, write_table
from atlas.layout import galaxy_coords, layout, procrustes_fit


def test_procrustes_recovers_rotation_scale_and_shift():
    rng = np.random.default_rng(0)
    A = rng.normal(size=(12, 2))
    th = 0.7
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    B = 3.0 * A @ R + np.array([100.0, 50.0])
    s, R2, t = procrustes_fit(A, B)
    assert np.allclose(s * A @ R2 + t, B, atol=1e-6)


def test_galaxy_is_deterministic_and_inside_the_topic_circle():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(50, 8))
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    c = X.mean(axis=0) / np.linalg.norm(X.mean(axis=0))
    gx, gy = galaxy_coords(X, c, 500.0, 300.0, 40.0)
    gx2, gy2 = galaxy_coords(X.copy(), c, 500.0, 300.0, 40.0)
    assert np.array_equal(gx, gx2) and np.array_equal(gy, gy2)
    assert (np.hypot(gx - 500, gy - 300) <= 40.0).all()
    closest = int(np.argmax(X @ c))                       # the most central article sits nearest the centre
    assert np.hypot(gx[closest] - 500, gy[closest] - 300) == np.hypot(gx - 500, gy - 300).min()
    assert galaxy_coords(X[:1], c, 1.0, 2.0, 5.0) == (np.array([1.0]), np.array([2.0]))


def _work(cfg, k: int, seed: int = 0):
    """k topics (ids 1..k) of 30 articles around distinct directions in 32-D."""
    rng = np.random.default_rng(seed)
    dirs = np.random.default_rng(42).normal(size=(k, 32))
    X = np.vstack([d + rng.normal(0, 0.3, (30, 32)) for d in dirs])
    X = (X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32)
    labels = np.repeat(np.arange(1, k + 1), 30)
    C = np.stack([X[labels == t].mean(axis=0) for t in range(1, k + 1)])
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    work = Path(cfg["pipeline"]["work_dir"])
    ids = [f"a{i}" for i in range(len(X))]
    write_table(pd.DataFrame({"article_id": ids}), work / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": ids, "fine_topic": labels}), work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"topic_id": range(1, k + 1), "size": 30, "coarse_topic": [t % 3 for t in range(k)]}),
                work / "04_topic_info.parquet")
    np.save(work / "03_embeddings.npy", X)
    np.save(work / "04_centroids.npy", C.astype(np.float32))
    (work / "04_centroid_ids.json").write_text(json.dumps(list(range(1, k + 1))), encoding="utf-8")


def _positions(tmp_path) -> dict[int, tuple[float, float]]:
    lay = read_table(tmp_path / "work" / "09_layout.parquet")
    return {int(r.id): (r.x, r.y) for r in lay[lay["kind"] == "topic"].itertuples()}


def test_layout_is_stable_across_releases_and_writes_galaxy(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q1"
    _work(cfg, k=12)
    layout(cfg)
    p1 = _positions(tmp_path)
    galaxy = read_table(tmp_path / "work" / "09_galaxy.parquet")
    assert len(galaxy) == 360 and set(galaxy["topic_id"]) == set(range(1, 13))
    assert (tmp_path / "state" / "releases" / "2026Q1" / "layout.parquet").exists()

    cfg["pipeline"]["release"] = "2026Q2"
    _work(cfg, k=13, seed=1)                                   # one new topic, every article re-sampled
    layout(cfg)
    p2 = _positions(tmp_path)
    moved = np.array([np.hypot(p2[t][0] - p1[t][0], p2[t][1] - p1[t][1]) for t in p1])
    assert np.median(moved) < 0.05 * cfg["layout"]["view_w"]
    W, H = cfg["layout"]["view_w"], cfg["layout"]["view_h"]
    assert all(90 <= x <= W - 90 and 90 <= y <= H - 90 for x, y in p2.values())


def test_layout_without_previous_release_fills_the_view(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["pipeline"]["release"] = "2026Q1"
    cfg["layout"]["galaxy"] = False
    _work(cfg, k=6)
    layout(cfg)
    xs = [x for x, _ in _positions(tmp_path).values()]
    assert min(xs) == 90.0 and max(xs) == cfg["layout"]["view_w"] - 90.0
    assert not (tmp_path / "work" / "09_galaxy.parquet").exists()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_layout.py -q`
Expected: FAIL — `ImportError: cannot import name 'procrustes_fit' from 'atlas.layout'`.

- [ ] **Step 3: Replace `pipeline/atlas/layout.py`**

```python
"""2D layout of topics for the atlas map (+ article "galaxy"), stable across releases.

Positions: UMAP 2D on topic centroids (near = semantically similar). With layout.stable and a layout
from the previous release (state_dir/releases/<prev>/layout.parquet):
  1. UMAP starts from the previous positions (new topics: mean of their `init_neighbors` most similar
     continuing topics);
  2. the result is aligned to the previous positions by a similarity Procrustes fit on the continuing
     topics (no rotation, flip or zoom between quarters);
  3. continuing topics end at anchor·previous + (1 − anchor)·aligned; a new topic gets the mean shift of
     its nearest continuing neighbours, so it lands next to them on the anchored map.
Without a previous layout (first release, or < 3 continuing topics): min-max scaling into the view box.
Group hubs sit at the size-weighted mean of their topics. Edges = centroid cosine ≥ threshold.

Galaxy: every assigned article is placed inside its topic's circle — angle from the topic's first two
principal components (sign-fixed), radius from the rank of its distance to the centroid (uniform disc).
Same inputs → same coordinates.

Outputs: work/09_layout (kind, id, x, y, r, parent), work/09_edges (s, t, w), work/09_galaxy
(article_id, topic_id, gx, gy); state_dir/releases/<release>/layout.parquet (topic_id, x, y).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import load_aligned
from atlas.io_utils import read_table, write_table
from atlas.state import previous_release, release_dir
from atlas.taxonomy import load_topic_groups

MARGIN = 90.0


def procrustes_fit(A: np.ndarray, B: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Similarity transform (scale s, orthogonal R, shift t) with s·A·R + t ≈ B (least squares)."""
    ma, mb = A.mean(axis=0), B.mean(axis=0)
    A0, B0 = A - ma, B - mb
    U, S, Vt = np.linalg.svd(A0.T @ B0)
    R = U @ Vt
    s = float(S.sum() / max((A0 ** 2).sum(), 1e-12))
    return s, R, mb - s * ma @ R


def _minmax_to_view(pos: np.ndarray, W: float, H: float) -> np.ndarray:
    out = pos.astype(float).copy()
    for ax, size in ((0, W), (1, H)):
        lo, hi = out[:, ax].min(), out[:, ax].max()
        out[:, ax] = MARGIN + (out[:, ax] - lo) / max(hi - lo, 1e-6) * (size - 2 * MARGIN)
    return out


def init_positions(ids: list[int], C: np.ndarray, prev_xy: dict[int, tuple[float, float]],
                   k: int) -> np.ndarray | None:
    """UMAP init (~10-unit scale): previous positions for continuing topics, neighbour mean for new ones."""
    keep = [i for i, t in enumerate(ids) if t in prev_xy]
    if len(keep) < 3:
        return None
    P = np.array([prev_xy[ids[i]] for i in keep], dtype=float)
    lo, span = P.min(axis=0), np.maximum(np.ptp(P, axis=0), 1e-6)
    init = np.zeros((len(ids), 2))
    init[keep] = 10.0 * (P - lo) / span
    sims = C @ C[keep].T
    for i in range(len(ids)):
        if ids[i] not in prev_xy:
            nn = np.argsort(-sims[i])[:k]
            init[i] = init[np.array(keep)[nn]].mean(axis=0)
    jitter = np.random.default_rng(0).normal(0, 1e-3, init.shape)        # UMAP needs distinct starting points
    return (init + jitter).astype(np.float32)


def topic_positions(ids: list[int], C: np.ndarray, lcfg: dict, seed: int,
                    prev_xy: dict[int, tuple[float, float]]) -> np.ndarray:
    W, H = float(lcfg["view_w"]), float(lcfg["view_h"])
    init = init_positions(ids, C, prev_xy, int(lcfg["init_neighbors"])) if lcfg["stable"] and prev_xy else None
    if len(ids) >= 4:
        import umap

        pos = umap.UMAP(n_components=2, n_neighbors=min(int(lcfg["umap_2d_neighbors"]), len(ids) - 1),
                        min_dist=float(lcfg["umap_2d_min_dist"]), metric="cosine", random_state=seed,
                        init=init if init is not None else "spectral").fit_transform(C)
    else:
        ang = np.linspace(0, 2 * np.pi, len(ids), endpoint=False)
        pos = np.stack([np.cos(ang), np.sin(ang)], axis=1)
    keep = [i for i, t in enumerate(ids) if t in prev_xy]
    if init is None or len(keep) < 3:
        return _minmax_to_view(pos, W, H)
    P = np.array([prev_xy[ids[i]] for i in keep], dtype=float)
    s, R, t = procrustes_fit(pos[keep], P)
    aligned = s * pos @ R + t
    a = float(lcfg["anchor"])
    out = aligned.copy()
    out[keep] = a * P + (1 - a) * aligned[keep]             # continuing topics stay (almost) where they were
    shift = out[keep] - aligned[keep]
    sims = C @ C[keep].T
    for i in range(len(ids)):                                # a new topic moves with its nearest old neighbours
        if ids[i] not in prev_xy:
            out[i] = aligned[i] + shift[np.argsort(-sims[i])[:int(lcfg["init_neighbors"])]].mean(axis=0)
    out[:, 0] = np.clip(out[:, 0], MARGIN, W - MARGIN)
    out[:, 1] = np.clip(out[:, 1], MARGIN, H - MARGIN)
    return out


def galaxy_coords(member_emb: np.ndarray, centroid: np.ndarray, cx: float, cy: float,
                  radius: float) -> tuple[np.ndarray, np.ndarray]:
    n = len(member_emb)
    if n == 1:
        return np.array([cx]), np.array([cy])
    X = member_emb - member_emb.mean(axis=0)
    _, _, Vt = np.linalg.svd(X, full_matrices=False)
    comps = Vt[:2].copy()
    for c in comps:                                       # sign convention → deterministic orientation
        if c[np.argmax(np.abs(c))] < 0:
            c *= -1
    P = X @ comps.T
    if P.shape[1] == 1:
        P = np.hstack([P, np.zeros((n, 1))])
    angle = np.arctan2(P[:, 1], P[:, 0])
    dist = 1.0 - member_emb @ centroid
    rank = np.argsort(np.argsort(dist, kind="stable"), kind="stable")
    rr = 0.95 * radius * np.sqrt((rank + 0.5) / n)
    return cx + rr * np.cos(angle), cy + rr * np.sin(angle)


def layout(cfg: dict) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    lcfg = cfg["layout"]
    seed = int(cfg["pipeline"]["seed"])
    C = np.load(work / "04_centroids.npy")
    ids = [int(t) for t in json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))]
    info = read_table(work / "04_topic_info.parquet").set_index("topic_id")
    group_of = load_topic_groups(work).set_index("topic_id")["group_id"].to_dict()

    prev_rel = previous_release(cfg)
    prev_xy: dict[int, tuple[float, float]] = {}
    if prev_rel and (release_dir(cfg, prev_rel) / "layout.parquet").exists():
        p = read_table(release_dir(cfg, prev_rel) / "layout.parquet")
        prev_xy = {int(r.topic_id): (float(r.x), float(r.y)) for r in p.itertuples()}
    pos = topic_positions(ids, C, lcfg, seed, prev_xy)

    size = info.loc[ids, "size"].to_numpy(dtype=float)
    r = 8 + (np.sqrt(size) / np.sqrt(size).max()) * 42          # fine topic radius 8–50
    fine_df = pd.DataFrame([{"kind": "topic", "id": tid, "x": round(float(pos[i, 0]), 1),
                             "y": round(float(pos[i, 1]), 1), "r": round(float(r[i]), 1),
                             "parent": int(group_of.get(tid, info.loc[tid, "coarse_topic"]))}
                            for i, tid in enumerate(ids)])
    hub_rows = []
    for gid, grp in fine_df.groupby("parent"):
        sizes = info.loc[grp["id"], "size"].to_numpy(dtype=float)
        hub_rows.append({"kind": "group", "id": int(gid), "x": round(float(np.average(grp["x"], weights=sizes)), 1),
                         "y": round(float(np.average(grp["y"], weights=sizes)), 1), "r": 0.0, "parent": -1,
                         "_size": sizes.sum()})
    hubs = pd.DataFrame(hub_rows)
    hr = np.sqrt(hubs["_size"].to_numpy(dtype=float))
    hubs["r"] = np.round(20 + (hr / hr.max()) * 70, 1)             # group hub radius 20–90
    out = pd.concat([hubs.drop(columns=["_size"]), fine_df], ignore_index=True)

    thr, maxe = float(lcfg["edge_similarity_threshold"]), int(lcfg["max_edges_per_node"])
    sim = C @ C.T
    np.fill_diagonal(sim, -1)
    edges = []
    for i, tid in enumerate(ids):
        kept = 0
        for j in np.argsort(-sim[i]):
            if sim[i, j] < thr or kept >= maxe:
                break
            if tid < ids[j]:                                          # undirected, write once
                edges.append({"s": tid, "t": ids[j], "w": round(float(sim[i, j]), 3)})
                kept += 1

    if lcfg["galaxy"]:
        docs, emb = load_aligned(work)
        fine = docs[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id", how="left")
        labels = fine["fine_topic"].fillna(-1).astype(int).to_numpy()
        parts = []
        for i, tid in enumerate(ids):
            members = np.where(labels == tid)[0]
            if len(members):
                gx, gy = galaxy_coords(emb[members], C[i], float(pos[i, 0]), float(pos[i, 1]), float(r[i]))
                parts.append(pd.DataFrame({"article_id": fine["article_id"].to_numpy()[members], "topic_id": tid,
                                           "gx": np.round(gx, 2), "gy": np.round(gy, 2)}))
        galaxy = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
            columns=["article_id", "topic_id", "gx", "gy"])
        write_table(galaxy, work / "09_galaxy.parquet")

    write_table(pd.DataFrame(edges, columns=["s", "t", "w"]), work / "09_edges.parquet")
    write_table(out, work / "09_layout.parquet")
    write_table(fine_df[["id", "x", "y"]].rename(columns={"id": "topic_id"}),
                release_dir(cfg, create=True) / "layout.parquet")
    moved = ""
    if prev_xy:
        cont = [i for i, t in enumerate(ids) if t in prev_xy]
        if cont:
            d = np.hypot(*(pos[cont] - np.array([prev_xy[ids[i]] for i in cont])).T)
            moved = f", continuing topics moved {np.median(d):.0f}px (median)"
    print(f"[layout] {len(hubs)} hubs, {len(fine_df)} topics, {len(edges)} similarity edges{moved}")
    return out
```

- [ ] **Step 4: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_layout.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pipeline/atlas/layout.py pipeline/tests/test_layout.py
git commit -m "feat(layout): map stays put across releases (UMAP init + Procrustes + anchoring) + deterministic article galaxy

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 14: Grounded narratives (top EMERGING / HOT / DECLINING) + executive brief — numbers only from the pipeline, checked after generation

Executives read the sentences, not the tables, so the sentences must never carry a number the pipeline did not compute. The prompt gets a facts block (names, status, shares B→R, growth with its CI, articles/journals/institutions, the forecast only when it passed the skill gate); the reply is checked — every number must be one of the facts (rounded to 0–1 decimals allowed, Thai digits converted), no other topic may be named — then regenerated once with the reason, and replaced by a template sentence built from the same facts if it still fails. With `narrative.provider: template` (the default) no LLM is called and the templates are published. A topic with no baseline is described as "new — no baseline", never as a multiple.

**Files:**
- Create: `pipeline/atlas/narrative.py`, `pipeline/tests/test_narrative.py`, `prompts/topic_narrative.th.md` (replaces the never-used P0 `prompts/emerging_narrative.th.md`), `prompts/executive_brief.th.md`
- Modify: `pipeline/atlas/llm_runner.py` (`JOBS`), `pipeline/atlas/pipeline.py` (step `narrate` after `forecast`), `pipeline/atlas/config.py`, `pipeline/config.example.yaml`

**Interfaces:**
- Consumes: `05_labels`, `07_emerging` (status, emerging_score, count_recent, share_baseline, share_recent, share_ratio, share_growth[_lo/_hi], n_journals_R, n_orgs_R), `08_forecasts` (show, fc_years, fc_mean, fc_lo80, fc_hi80), `06_meta.json`; `topic_titles` (Task 6); `run_job`, `LlmItem.check` (Task 3).
- Produces:
  - `atlas.narrative`: `STATUS_TH`, `NarrativeOut` (th, en), `BriefOut` (headline_th, headline_en, bullets_th, bullets_en — leading list markers stripped), `numbers_in(text)`, `grounding_error(texts, facts, names) -> str | None`, `topic_facts(...)`, `template_narrative(...)`, `selected_topics(cfg, em)`, `narrative_job(cfg)`, `brief_facts(...)`, `template_brief(...)`, `brief_job(cfg)`, `narrate(cfg, llm=None)`.
  - `work/11_narratives` (`topic_id, status, th, en, source ∈ {llm, template}`), `work/11_brief.json` = `{brief: {headline_th, headline_en, bullets_th, bullets_en, source} | null, llm: {narrative?: stats, brief?: stats}}`.
  - Config `narrative.{provider ∈ {llm, template}, statuses, top_n, n_titles, brief}`; pipeline `STEPS = [… keywords, forecast, narrate, layout, export]`; `JOBS` = label, merge, narrative, brief.

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_narrative.py`:

```python
import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import write_table
from atlas.llm import Reply
from atlas.llm_runner import JOBS
from atlas.narrative import grounding_error, narrate, narrative_job
from atlas.pipeline import STEPS

NAMES = {1: ("การเรียนรู้ด้วย AI", "AI-assisted learning"), 2: ("สื่อสิ่งพิมพ์", "Print media"),
         3: ("การปลูกข้าว", "Rice farming"), 4: ("โมเดลภาษาขนาดใหญ่", "Large language models")}


def _work(cfg):
    """Topic 1 EMERGING, 2 DECLINING, 3 STABLE, 4 EMERGING with no baseline; data to 2024."""
    work = Path(cfg["pipeline"]["work_dir"])
    rng = np.random.default_rng(0)
    rows, fine = [], []
    for t in NAMES:
        for i in range(3):
            rows.append({"article_id": f"a{t}{i}", "title": f"บทความ {NAMES[t][1]} {i}", "doc_text": "x"})
            fine.append({"article_id": f"a{t}{i}", "fine_topic": t})
    emb = rng.normal(size=(len(rows), 8)).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", emb)
    write_table(pd.DataFrame(fine), work / "04_fine_topics.parquet")
    np.save(work / "04_centroids.npy", np.stack([emb[i * 3:i * 3 + 3].mean(0) for i in range(4)]))
    (work / "04_centroid_ids.json").write_text(json.dumps(list(NAMES)), encoding="utf-8")
    write_table(pd.DataFrame([{"level": "fine", "topic_id": t, "name_th": th, "name_en": en, "description": "",
                               "keywords": f"{en}; {th}", "cache_key": "x", "label_source": "llm"}
                              for t, (th, en) in NAMES.items()]), work / "05_labels.parquet")
    em = pd.DataFrame({
        "topic_id": [1, 2, 3, 4], "status": ["EMERGING", "DECLINING", "STABLE", "EMERGING"],
        "emerging_score": [80.0, 20.0, 50.0, 70.0], "count_recent": [240, 90, 300, 60],
        "share_baseline": [0.004, 0.02, 0.03, 0.0], "share_recent": [0.012, 0.008, 0.03, 0.004],
        "share_ratio": [3.0, 0.4, 1.0, 4e8], "share_growth": [0.35, -0.2, 0.0, 0.9],
        "share_growth_lo": [0.2, -0.3, -0.05, 0.4], "share_growth_hi": [0.5, -0.1, 0.05, 1.5],
        "n_journals_R": [12, 5, 20, 6], "n_orgs_R": [30, 8, 40, 9]})
    write_table(em, work / "07_emerging.parquet")
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024, "trimmed_years": [2025],
                                                   "totals": {str(y): 1000 for y in range(2015, 2025)}}),
                                       encoding="utf-8")
    write_table(pd.DataFrame([{"topic_id": 1, "show": True, "fc_years": "[2025, 2026]", "fc_mean": "[120.0, 130.0]",
                               "fc_lo80": "[100.0, 105.0]", "fc_hi80": "[140.0, 155.0]"}]),
                work / "08_forecasts.parquet")
    return work


def test_grounding_accepts_rounding_thai_digits_and_rejects_inventions():
    facts = "- สัดส่วน: 1.23% → 4.56% (3.7 เท่า)\n- บทความ 1,234 เรื่อง ช่วง 2022–2024 (3 ปี)"
    assert grounding_error(["สัดส่วนเพิ่มจาก 1.2% เป็น 4.6% ใน ๓ ปี", "1,234 articles in 2022–2024"], facts, []) is None
    assert "99" in grounding_error(["เพิ่มขึ้น 99%"], facts, [])
    assert "Rice farming" in grounding_error(["unlike Rice farming"], facts, ["Rice farming", "AI"])
    assert grounding_error(["about AI"], facts, ["AI"]) is None          # names under 4 characters are not checked


def test_templates_without_an_llm(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = _work(cfg)
    df = narrate(cfg)
    assert df["topic_id"].tolist() == [1, 4, 2] and set(df["source"]) == {"template"}   # EMERGING, then DECLINING
    by = df.set_index("topic_id")
    assert "ไม่มีบทความในช่วง" in by.loc[4, "th"] and "1.20%" in by.loc[1, "th"]
    brief = json.loads((work / "11_brief.json").read_text(encoding="utf-8"))["brief"]
    assert brief["source"] == "template" and "2024" in brief["headline_th"]
    item = {it.key: it for it in narrative_job(cfg).items}["T000004"]
    base = [ln for ln in item.prompt.splitlines() if ln.startswith("- ช่วงฐาน")][0]
    assert "ไม่มีฐานเปรียบเทียบ" in base and "เท่า" not in base


class FakeWriter:
    model_id = "fake-writer"

    def __init__(self):
        self.prompts = []

    def chat(self, messages):
        p = messages[0]["content"]
        self.prompts.append(p)
        if "headline_th" in p:
            out = {"headline_th": "หัวข้อการเรียนรู้ด้วย AI เติบโตเร็วที่สุดถึงปี 2024", "headline_en": "AI-assisted learning leads",
                   "bullets_th": ["1. มีหัวข้อกำลังเกิดใหม่ 2 หัวข้อ"], "bullets_en": ["- 2 emerging topics"]}
        elif "Print media" in p:
            out = {"th": "ลดลง 99% ต่อปี", "en": "down 99% a year"}                  # invented number
        elif "Large language models" in p:
            out = {"th": "โมเดลภาษาขนาดใหญ่เป็นหัวข้อใหม่ที่ไม่มีฐานเปรียบเทียบ", "en": "A new topic with no baseline"}
        else:
            out = {"th": "การเรียนรู้ด้วย AI โต 35% ต่อปี (ช่วงเชื่อมั่น 90%: 20% ถึง 50%)",
                   "en": "AI-assisted learning grows 35% a year (90% CI 20% to 50%)"}
        return Reply(json.dumps(out, ensure_ascii=False), 0, 0, 0.0)


def test_llm_narratives_are_grounded_or_replaced(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = _work(cfg)
    writer = FakeWriter()
    by = narrate(cfg, llm=writer).set_index("topic_id")
    assert by.loc[1, "source"] == "llm" and "35%" in by.loc[1, "th"]
    assert by.loc[4, "source"] == "llm"
    assert by.loc[2, "source"] == "template" and "99" not in by.loc[2, "th"]          # rejected twice → template
    assert sum("Print media" in p and "headline_th" not in p for p in writer.prompts) == 2   # first try + 1 regeneration
    assert any("rejected: numbers not in the facts: 99" in p for p in writer.prompts)
    saved = json.loads((work / "11_brief.json").read_text(encoding="utf-8"))
    assert saved["brief"]["source"] == "llm" and saved["brief"]["bullets_th"] == ["มีหัวข้อกำลังเกิดใหม่ 2 หัวข้อ"]
    assert set(saved["llm"]) == {"narrative", "brief"} and saved["llm"]["narrative"]["fallback"] == 1


def test_step_and_jobs_are_registered():
    assert STEPS.index("forecast") < STEPS.index("narrate") < STEPS.index("export")
    assert set(JOBS) == {"label", "merge", "narrative", "brief"}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_narrative.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.narrative'`.

- [ ] **Step 3: Prompts** — the never-used P0 draft `prompts/emerging_narrative.th.md` (prose output, Thai only) becomes `prompts/topic_narrative.th.md` (JSON in both languages, grounding rules stated). `git mv` it and overwrite the content, or equivalently:

Delete `prompts/emerging_narrative.th.md` (`git rm prompts/emerging_narrative.th.md`).

Create `prompts/topic_narrative.th.md`:

````markdown
# Prompt: คำอธิบายหัวข้อจากตัวเลขของ pipeline (topic narrative)

> **สถานะ: ใช้งานจริง — ไฟล์นี้คือต้นฉบับเดียว** `pipeline/atlas/narrative.py` อ่าน block ใต้ "Prompt (master)" ตอนรัน (งาน LLM `narrative`)
> แก้ข้อความใน block = `prompt_version` เปลี่ยน → คำอธิบายถูกเขียนใหม่ในรอบถัดไป; แก้หมายเหตุนอก block ไม่มีผลต่อ cache
> (เดิมชื่อ `emerging_narrative.th.md` — ออกแบบไว้ใน P0 แต่ยังไม่เคยใช้)

## บริบทการใช้

- เรียกต่อหัวข้อ เฉพาะ `narrative.top_n` หัวข้อแรกของแต่ละสถานะใน `narrative.statuses` (EMERGING / WATCH / HOT เรียงตาม emerging_score, DECLINING เรียงตามอัตราลดลง)
- inputs: `{facts}` = ข้อเท็จจริงจาก pipeline (ชื่อ สถานะ สัดส่วนช่วงฐาน→ช่วงล่าสุด อัตราเปลี่ยนพร้อมช่วงเชื่อมั่น จำนวนบทความ/วารสาร/สถาบัน พยากรณ์เมื่อผ่านเกณฑ์ skill) · `{titles}` = ชื่อบทความตัวแทน (บรรทัดละ 1 เรื่อง)
- **ตรวจหลังได้คำตอบ** (`narrative.grounding_error`): ตัวเลขทุกตัวต้องอยู่ใน `{facts}` (ปัดเศษ 0–1 ตำแหน่งได้, เลขไทยแปลงก่อนตรวจ) และห้ามมีชื่อหัวข้ออื่น → ไม่ผ่าน = ให้เขียนใหม่ `llm.max_regenerations` ครั้งพร้อมบอกเหตุผล → ไม่ผ่านอีก = ใช้ประโยคแม่แบบจากตัวเลขชุดเดียวกัน (`source: template`)
- ผลลัพธ์ → `work/11_narratives` → `topics/<id>.json → narrative` (เว็บแสดงพร้อมป้าย "สรุปอัตโนมัติจากตัวเลขของระบบ")
- หัวข้อใหม่ที่ไม่มีบทความในช่วงฐาน: facts เขียนว่า "ไม่มีฐานเปรียบเทียบ" และไม่มีจำนวนเท่า — prompt สั่งไม่ให้เขียนเป็นจำนวนเท่า

## Prompt (master)

```
คุณคือนักวิเคราะห์นโยบายวิจัย เขียนคำอธิบายสั้นของหัวข้อวิจัยหนึ่งหัวข้อสำหรับผู้บริหารและบรรณาธิการวารสาร

ข้อเท็จจริงจากระบบ (ใช้ได้เฉพาะข้อมูลนี้):
{facts}

ตัวอย่างชื่อบทความในหัวข้อนี้:
{titles}

เขียน 2–3 ประโยค เป็นภาษาไทยและภาษาอังกฤษที่ความหมายตรงกัน โดย:
1. บอกว่าหัวข้อนี้เกี่ยวกับอะไร (จากชื่อ คำสำคัญ และตัวอย่างบทความ)
2. บอกทิศทางจากตัวเลข เลือก 1–2 ตัวเลขที่สำคัญที่สุด ถ้าบอกอัตราเปลี่ยนต่อปี ให้บอกช่วงเชื่อมั่นด้วย
3. ถ้าข้อเท็จจริงบอกว่าไม่มีฐานเปรียบเทียบ ให้บอกตรง ๆ ว่าเป็นหัวข้อใหม่ที่ไม่มีฐานเปรียบเทียบ ห้ามเขียนเป็นจำนวนเท่า

กติกา:
- ตัวเลขทุกตัวต้องมาจากข้อเท็จจริงข้างต้น (ปัดเศษได้) ห้ามคำนวณตัวเลขใหม่ ห้ามแปลงปีเป็น พ.ศ.
- ห้ามเอ่ยชื่อหัวข้ออื่น ห้ามเดาสาเหตุที่ข้อมูลไม่ได้บอก ห้ามใช้คำฟุ่มเฟือย เช่น "น่าสนใจ" "สำคัญมาก"

ตอบกลับเป็น JSON เท่านั้น ห้ามมีข้อความอื่น:
{
  "th": "คำอธิบายภาษาไทย",
  "en": "The same explanation in English"
}
```
````

Create `prompts/executive_brief.th.md`:

````markdown
# Prompt: บทสรุปผู้บริหาร (executive brief)

> **สถานะ: ใช้งานจริง — ไฟล์นี้คือต้นฉบับเดียว** `pipeline/atlas/narrative.py` อ่าน block ใต้ "Prompt (master)" ตอนรัน (งาน LLM `brief`)
> แก้ข้อความใน block = `prompt_version` เปลี่ยน → บทสรุปถูกเขียนใหม่ในรอบถัดไป; แก้หมายเหตุนอก block ไม่มีผลต่อ cache

## บริบทการใช้

- เรียก 1 ครั้งต่อรอบข้อมูล — ผลคือ headline ของหน้า Overview (ประโยคแบบบทบรรณาธิการเหนือ forest plot) และ bullet สั้นสำหรับ PDF brief
- inputs: `{facts}` = ช่วงปีที่วิเคราะห์ (และปีที่ยังไม่ครบ), จำนวนบทความ/หัวข้อ, จำนวนหัวข้อตามสถานะ, 3 หัวข้อแรกของ EMERGING / HOT / DECLINING พร้อมจำนวนบทความและอัตราเปลี่ยนพร้อมช่วงเชื่อมั่น
- **ตรวจหลังได้คำตอบ** เหมือน topic narrative: ตัวเลขทุกตัวต้องอยู่ใน `{facts}`, ชื่อหัวข้อต้องเป็นชื่อที่อยู่ใน `{facts}` เท่านั้น; เลขลำดับหน้า bullet ถูกตัดก่อนตรวจ → ไม่ผ่าน = เขียนใหม่ → ไม่ผ่านอีก = แม่แบบ (`source: template`)
- ผลลัพธ์ → `work/11_brief.json` → `overview.json → brief`

## Prompt (master)

```
คุณคือนักวิเคราะห์นโยบายวิจัย เขียนบทสรุปผู้บริหารของแผนที่งานวิจัยไทยรอบนี้

ข้อเท็จจริงจากระบบ (ใช้ได้เฉพาะข้อมูลนี้):
{facts}

เขียนเป็นภาษาไทยและภาษาอังกฤษที่ความหมายตรงกัน:
- headline: ประโยคเดียวที่สรุปสิ่งสำคัญที่สุดของรอบนี้
- bullets: 3–5 ข้อ ข้อละประโยคเดียว (หัวข้อกำลังเกิดใหม่ หัวข้อกำลังร้อน หัวข้อกำลังลดลง และข้อจำกัดของข้อมูลถ้ามี)

กติกา:
- ตัวเลขทุกตัวต้องมาจากข้อเท็จจริงข้างต้น (ปัดเศษได้) ห้ามคำนวณตัวเลขใหม่ ห้ามแปลงปีเป็น พ.ศ.
- ถ้าบอกอัตราเปลี่ยนต่อปี ให้บอกช่วงเชื่อมั่นด้วย
- เอ่ยชื่อหัวข้อได้เฉพาะชื่อที่อยู่ในข้อเท็จจริง ห้ามเดาสาเหตุ ห้ามใช้คำฟุ่มเฟือย ไม่ต้องใส่เลขลำดับหน้าข้อ

ตอบกลับเป็น JSON เท่านั้น ห้ามมีข้อความอื่น:
{
  "headline_th": "ประโยคสรุปภาษาไทย",
  "headline_en": "The headline in English",
  "bullets_th": ["ข้อที่หนึ่ง", "ข้อที่สอง", "ข้อที่สาม"],
  "bullets_en": ["First point", "Second point", "Third point"]
}
```
````

- [ ] **Step 4: Create `pipeline/atlas/narrative.py`**

```python
"""Grounded narratives (LLM tasks "narrative" and "brief") — every number comes from the pipeline.

Topic narratives: the top narrative.top_n topics of each status in narrative.statuses (EMERGING, WATCH
and HOT by emerging_score, DECLINING by the steepest share decline) get 2–3 sentences in Thai and
English (prompts/topic_narrative.th.md). Executive brief: a headline and 3–5 bullets for the whole
release (prompts/executive_brief.th.md) — the Overview page's headline sentence.
The prompt carries a facts block built from 05_labels, 07_emerging, 08_forecasts and 06_meta, and the
reply is checked before it is accepted:
  numbers  every number in the text (Thai digits converted, thousands separators removed, sign ignored)
           must equal a number of the facts block — exactly, or rounded to 0 or 1 decimal;
  names    no topic name may appear unless it is in the facts block.
A failed check → one regeneration that names the problem (llm.max_regenerations); still failing →
a template sentence built from the same facts (source "template"). narrative.provider: template never
calls the LLM. Outputs: work/11_narratives (topic_id, status, th, en, source), work/11_brief.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from atlas.io_utils import read_table, write_table
from atlas.label import topic_titles
from atlas.lineage import topic_code
from atlas.llm_runner import LlmItem, LlmJob, run_job
from atlas.prompts import load_prompt, prompt_version, render_prompt

TOPIC_PROMPT, BRIEF_PROMPT = "topic_narrative.th", "executive_brief.th"
NARRATIVE_COLUMNS = ["topic_id", "status", "th", "en", "source"]
STATUS_TH = {"EMERGING": "กำลังเกิดใหม่", "WATCH": "จับตา", "HOT": "กำลังร้อน", "DECLINING": "กำลังลดลง",
             "STABLE": "คงที่", "LOW_DATA": "ข้อมูลน้อย"}
_THAI_DIGITS = str.maketrans("".join(chr(0x0E50 + d) for d in range(10)), "0123456789")   # Thai digits 0-9
_NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


class NarrativeOut(BaseModel):
    th: str
    en: str

    @field_validator("th", "en")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("th and en must not be blank")
        return v.strip()


class BriefOut(BaseModel):
    headline_th: str
    headline_en: str
    bullets_th: list[str] = Field(min_length=1, max_length=6)
    bullets_en: list[str] = Field(min_length=1, max_length=6)

    @field_validator("bullets_th", "bullets_en")
    @classmethod
    def _strip_markers(cls, v: list[str]) -> list[str]:
        """'1. text' / '- text' → 'text' (list numbers are not facts)."""
        return [b for b in (re.sub(r"^\s*(?:\d+[.)]|[-•*])\s+", "", str(x)).strip() for x in v) if b]


# ---------------------------------------------------------------------- grounding check
def numbers_in(text: str) -> list[float]:
    return [float(m.replace(",", "")) for m in _NUMBER.findall(str(text).translate(_THAI_DIGITS))]


def _grounded(x: float, allowed: set[float]) -> bool:
    return any(x == a or x == round(a) or x == round(a, 1) for a in allowed)


def grounding_error(texts: list[str], facts: str, names: list[str]) -> str | None:
    """Why the texts are not grounded in `facts`, or None. names: every topic name of the release."""
    allowed = set(numbers_in(facts))
    bad = sorted({n for t in texts for n in numbers_in(t) if not _grounded(n, allowed)})
    if bad:
        return "numbers not in the facts: " + ", ".join(f"{n:g}" for n in bad[:5])
    joined = "\n".join(texts)
    foreign = [n for n in names if len(n) >= 4 and n not in facts and n in joined]
    if foreign:
        return "names topics that are not in the facts: " + ", ".join(foreign[:3])
    return None


# ---------------------------------------------------------------------- facts
def _pct(v: float, nd: int = 2) -> str:
    return f"{v * 100:.{nd}f}"


def _windows(cfg: dict, last: int) -> tuple[str, str]:
    """('2017–2021 (5 ปี)', '2022–2024 (3 ปี)') — window lengths are facts too ("in the last 3 years")."""
    e = cfg["emerging"]
    r, b = int(e["recent_window"]), int(e["baseline_window"])
    return f"{last - r - b + 1}–{last - r} ({b} ปี)", f"{last - r + 1}–{last} ({r} ปี)"


def topic_facts(cfg: dict, lab, em, fc, last: int) -> str:
    B, R = _windows(cfg, last)
    ci = round(float(cfg["emerging"]["ci_level"]) * 100)
    lines = [f"- ชื่อ: {lab.name_th} ({lab.name_en})",
             f"- สถานะ: {STATUS_TH[em.status]} ({em.status})",
             f"- คำสำคัญ: {lab.keywords}"]
    if str(lab.description).strip():
        lines.append(f"- คำอธิบาย: {lab.description}")
    if float(em.share_baseline) == 0:
        lines.append(f"- ช่วงฐาน {B}: ไม่มีบทความ (หัวข้อใหม่ — ไม่มีฐานเปรียบเทียบ) | ช่วงล่าสุด {R}: "
                     f"{_pct(em.share_recent)}% ของบทความทั้งหมด")
    else:
        lines.append(f"- สัดส่วนของบทความทั้งหมด: ช่วงฐาน {B} = {_pct(em.share_baseline)}% → ช่วงล่าสุด {R} = "
                     f"{_pct(em.share_recent)}% ({em.share_ratio:.1f} เท่า)")
    if pd.notna(em.share_growth):
        lines.append(f"- อัตราเปลี่ยนของสัดส่วนต่อปี: {_pct(em.share_growth, 1)}% (ช่วงเชื่อมั่น {ci}%: "
                     f"{_pct(em.share_growth_lo, 1)}% ถึง {_pct(em.share_growth_hi, 1)}%)")
    lines.append(f"- บทความช่วง {R}: {int(em.count_recent):,} เรื่อง จาก {int(em.n_journals_R)} วารสาร "
                 f"{int(em.n_orgs_R)} สถาบัน")
    if fc is not None and bool(fc.show):
        years, mean, lo, hi = (json.loads(fc[k]) for k in ("fc_years", "fc_mean", "fc_lo80", "fc_hi80"))
        lines.append(f"- พยากรณ์ปี {years[0]}: {mean[0]:.0f} เรื่อง (ช่วง 80%: {lo[0]:.0f}–{hi[0]:.0f})")
    return "\n".join(lines)


def template_narrative(cfg: dict, lab, em, last: int) -> dict:
    B, R = _windows(cfg, last)
    n = int(em.count_recent)
    if float(em.share_baseline) == 0:
        return {"th": f"{lab.name_th}: หัวข้อใหม่ที่ไม่มีบทความในช่วง {B} — ช่วง {R} มี {n:,} เรื่อง "
                      f"({_pct(em.share_recent)}% ของบทความทั้งหมด)",
                "en": f"{lab.name_en}: a new topic with no articles in {B}; {n:,} articles in {R} "
                      f"({_pct(em.share_recent)}% of all articles)."}
    up = float(em.share_recent) >= float(em.share_baseline)
    return {"th": f"{lab.name_th}: สัดส่วนบทความ{'เพิ่มขึ้น' if up else 'ลดลง'}จาก {_pct(em.share_baseline)}% "
                  f"ในช่วง {B} เป็น {_pct(em.share_recent)}% ในช่วง {R} ({n:,} เรื่อง)",
            "en": f"{lab.name_en}: share of articles {'rose' if up else 'fell'} from {_pct(em.share_baseline)}% "
                  f"in {B} to {_pct(em.share_recent)}% in {R} ({n:,} articles)."}


def _inputs(cfg: dict):
    work = Path(cfg["pipeline"]["work_dir"])
    labels = read_table(work / "05_labels.parquet").drop_duplicates("topic_id").set_index("topic_id")
    em = read_table(work / "07_emerging.parquet").set_index("topic_id")
    fpath = work / "08_forecasts.parquet"
    fc = read_table(fpath).set_index("topic_id") if fpath.exists() else pd.DataFrame()
    last = int(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["last_complete_year"])
    return labels, em, fc, last


def selected_topics(cfg: dict, em: pd.DataFrame) -> list[int]:
    ncfg, out = cfg["narrative"], []
    for status in ncfg["statuses"]:
        g = em[em["status"] == status]
        g = g.sort_values("share_growth") if status == "DECLINING" else g.sort_values("emerging_score",
                                                                                         ascending=False)
        out += [int(t) for t in g.index[: int(ncfg["top_n"])]]
    return out


def _names(labels: pd.DataFrame) -> list[str]:
    return [str(n) for c in ("name_th", "name_en") for n in labels[c] if str(n).strip()]


def narrative_job(cfg: dict) -> LlmJob:
    labels, em, fc, last = _inputs(cfg)
    template = load_prompt(TOPIC_PROMPT, cfg["llm"]["prompts_dir"])
    tids = selected_topics(cfg, em)
    titles = topic_titles(cfg, int(cfg["narrative"]["n_titles"])) if tids else {}
    names = _names(labels)
    items = []
    for tid in tids:
        lab, e = labels.loc[tid], em.loc[tid]
        f = fc.loc[tid] if len(fc) and tid in fc.index else None
        facts = topic_facts(cfg, lab, e, f, last)
        tl = "\n".join(f"- {t}" for t in titles.get(tid, []))
        items.append(LlmItem(topic_code(tid), render_prompt(template, facts=facts, titles=tl),
                             template_narrative(cfg, lab, e, last),
                             _checker(facts + "\n" + tl, names, ("th", "en"))))
    return LlmJob("narrative", NarrativeOut, prompt_version(template), items)


def _checker(facts: str, names: list[str], fields: tuple[str, ...]):
    def check(out: dict) -> str | None:
        texts = [t for f in fields for t in (out[f] if isinstance(out[f], list) else [out[f]])]
        return grounding_error(texts, facts, names)
    return check


def brief_facts(cfg: dict, labels: pd.DataFrame, em: pd.DataFrame, last: int) -> str:
    work = Path(cfg["pipeline"]["work_dir"])
    meta = json.loads((work / "06_meta.json").read_text(encoding="utf-8"))
    years = sorted(int(y) for y in meta["totals"])
    counts = em["status"].value_counts()
    ci = round(float(cfg["emerging"]["ci_level"]) * 100)
    lines = [f"- ช่วงข้อมูลที่ใช้วิเคราะห์: {years[0]}–{last}"
             + (f" (ปีที่ยังไม่ครบและไม่นำมาวิเคราะห์: {', '.join(map(str, meta.get('trimmed_years', [])))})"
                if meta.get("trimmed_years") else ""),
             f"- บทความในช่วงนี้: {sum(meta['totals'].values()):,} เรื่อง · หัวข้อวิจัย {len(em)} หัวข้อ",
             "- จำนวนหัวข้อตามสถานะ: " + ", ".join(f"{STATUS_TH[s]} ({s}) {int(counts.get(s, 0))}" for s in STATUS_TH)]
    _, R = _windows(cfg, last)
    for status in ("EMERGING", "HOT", "DECLINING"):
        g = em[em["status"] == status]
        g = g.sort_values("share_growth") if status == "DECLINING" else g.sort_values("emerging_score",
                                                                                         ascending=False)
        for tid, e in g.head(3).iterrows():
            lab = labels.loc[tid]
            lines.append(f"- {STATUS_TH[status]}: {lab.name_th} ({lab.name_en}) — {int(e.count_recent):,} เรื่องใน {R}, "
                         f"สัดส่วนเปลี่ยน {_pct(e.share_growth, 1)}%/ปี (ช่วงเชื่อมั่น {ci}%: "
                         f"{_pct(e.share_growth_lo, 1)}% ถึง {_pct(e.share_growth_hi, 1)}%)")
    return "\n".join(lines)


def template_brief(cfg: dict, em: pd.DataFrame, last: int, total: int) -> dict:
    c = em["status"].value_counts()
    e, h, d = (int(c.get(s, 0)) for s in ("EMERGING", "HOT", "DECLINING"))
    return {"headline_th": f"ข้อมูลถึงปี {last}: {total:,} บทความ {len(em)} หัวข้อ — กำลังเกิดใหม่ {e} หัวข้อ, "
                           f"กำลังร้อน {h} หัวข้อ, กำลังลดลง {d} หัวข้อ",
            "headline_en": f"Data to {last}: {total:,} articles in {len(em)} topics — {e} emerging, {h} hot, "
                           f"{d} declining",
            "bullets_th": [f"{STATUS_TH[s]} ({s}): {int(c.get(s, 0))} หัวข้อ" for s in STATUS_TH],
            "bullets_en": [f"{s}: {int(c.get(s, 0))} topics" for s in STATUS_TH]}


def brief_job(cfg: dict) -> LlmJob:
    labels, em, _, last = _inputs(cfg)
    work = Path(cfg["pipeline"]["work_dir"])
    total = sum(json.loads((work / "06_meta.json").read_text(encoding="utf-8"))["totals"].values())
    template = load_prompt(BRIEF_PROMPT, cfg["llm"]["prompts_dir"])
    facts = brief_facts(cfg, labels, em, last)
    item = LlmItem("brief", render_prompt(template, facts=facts), template_brief(cfg, em, last, total),
                   _checker(facts, _names(labels), ("headline_th", "headline_en", "bullets_th", "bullets_en")))
    return LlmJob("brief", BriefOut, prompt_version(template), [item])


def _use_llm(cfg: dict, task: str, llm) -> bool:
    return llm is not None or (cfg["narrative"]["provider"] == "llm" and bool(cfg["llm"]["tasks"][task]["model"]))


def narrate(cfg: dict, llm=None) -> pd.DataFrame:
    work = Path(cfg["pipeline"]["work_dir"])
    labels, em, _, last = _inputs(cfg)
    stats = {}
    job = narrative_job(cfg)
    if job.items and _use_llm(cfg, "narrative", llm):
        results, stats["narrative"] = run_job(cfg, job, llm)
        outs = {k: (r.output, "template" if r.source == "fallback" else "llm") for k, r in results.items()}
    else:
        outs = {it.key: (it.fallback, "template") for it in job.items}
    rows = []
    for it in job.items:
        tid = int(it.key[1:])
        out, src = outs[it.key]
        rows.append({"topic_id": tid, "status": str(em.loc[tid, "status"]), "th": out["th"], "en": out["en"],
                     "source": src})
    df = pd.DataFrame(rows, columns=NARRATIVE_COLUMNS)
    write_table(df, work / "11_narratives.parquet")
    brief = None
    if cfg["narrative"]["brief"] and len(em):
        bjob = brief_job(cfg)
        if _use_llm(cfg, "brief", llm):
            res, stats["brief"] = run_job(cfg, bjob, llm)
            r = res["brief"]
            brief = {**r.output, "source": "template" if r.source == "fallback" else "llm"}
        else:
            brief = {**bjob.items[0].fallback, "source": "template"}
    (work / "11_brief.json").write_text(json.dumps({"brief": brief, "llm": stats}, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    n_llm = int((df["source"] == "llm").sum())
    print(f"[narrate] {len(df)} topic narratives ({n_llm} LLM, {len(df) - n_llm} template); "
          f"brief: {brief['source'] if brief else 'off'}")
    return df
```

- [ ] **Step 5: Register the jobs and the step**

Replace
```python
JOBS: dict[str, str] = {"label": "atlas.label:label_job", "merge": "atlas.review:merge_job"}
```
with
```python
JOBS: dict[str, str] = {"label": "atlas.label:label_job", "merge": "atlas.review:merge_job",
                        "narrative": "atlas.narrative:narrative_job", "brief": "atlas.narrative:brief_job"}
```
Replace
```python
         "forecast", "layout", "export"]
```
with
```python
         "forecast", "narrate", "layout", "export"]
```
After
```python
    "forecast": ("atlas.forecast", "forecast"),
```
insert
```python
    "narrate": ("atlas.narrative", "narrate"),
```

- [ ] **Step 6: Config** — `pipeline/atlas/config.py`:

Before
```python
class AtlasConfig(_Strict):
```
insert
```python
class NarrativeCfg(_Strict):
    provider: Literal["llm", "template"] = "template"
    statuses: list[Literal["EMERGING", "WATCH", "HOT", "DECLINING"]] = Field(
        default_factory=lambda: ["EMERGING", "HOT", "DECLINING"])
    top_n: int = Field(10, ge=0)
    n_titles: int = Field(5, ge=0)
    brief: bool = True


```
After
```python
    review: ReviewCfg = Field(default_factory=ReviewCfg)
```
insert
```python
    narrative: NarrativeCfg = Field(default_factory=NarrativeCfg)
```
`pipeline/config.example.yaml` (after the `review:` block):
After
```yaml
  n_titles: 5                 # ตัวอย่างชื่อบทความต่อหัวข้อในไฟล์ตรวจ
```
insert
```yaml

# ---------- คำอธิบายหัวข้อ + บทสรุปผู้บริหาร (ตัวเลขมาจาก pipeline เท่านั้น — ตรวจซ้ำหลัง LLM ตอบ) ----------
narrative:
  provider: template          # llm (llm.tasks.narrative / brief) | template (ประโยคแม่แบบจากตัวเลข ไม่เรียก LLM)
  statuses: [EMERGING, HOT, DECLINING]   # สถานะที่ได้คำอธิบาย
  top_n: 10                   # ต่อสถานะ (EMERGING/HOT ตาม emerging_score, DECLINING ตามอัตราลดลง)
  n_titles: 5                 # ชื่อบทความตัวแทนที่ส่งให้ LLM
  brief: true                 # บทสรุปผู้บริหาร (headline ของหน้า Overview)
```

- [ ] **Step 7: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_narrative.py tests/test_llm.py -q && uv run pytest -q`
Expected: all pass (the P0 pipeline tests now run `narrate` with templates).

- [ ] **Step 8: Commit** (prompt files changed — say so):

```bash
git add pipeline/atlas/narrative.py pipeline/tests/test_narrative.py prompts/topic_narrative.th.md prompts/executive_brief.th.md pipeline/atlas/llm_runner.py pipeline/atlas/pipeline.py pipeline/atlas/config.py pipeline/config.example.yaml
git commit -m "feat(narrative): grounded topic narratives + executive brief (numbers and names checked, template fallback)

prompts/emerging_narrative.th.md → prompts/topic_narrative.th.md (JSON TH/EN, grounding rules); new prompts/executive_brief.th.md.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 15: Data contract v2 — models for every published file (overview, taxonomy, topics, topic detail, series, edges, keywords, latest) + LLM accounting

P0 locked `Manifest` and `TopicsFile`; P1 adds the other files and the fields the analytics now produce: taxonomy (subfield, cross_field, vote), nowcast, label source, narrative and brief, `no_baseline` (`share_ratio: null`), `low_data_reason`, and in the manifest the interval level `ci_level` (the bounds keep the level-agnostic names `*_lo/*_hi`), the v3 fields (`as_of_year`, `trimmed_years`, `n_orgs_unverified`, `ingest_errors`, `embedding_provider`) and the label/LLM accounting. Strict JSON (`allow_inf_nan=False`) everywhere; colours are token keys `cat-01…cat-12`.

**Files:**
- Modify: `pipeline/atlas/schema/contract.py` (full replacement — unchanged upstream since `8ae68fc`, verified at `0426434`), `web/src/data/contract.schema.json` + `web/src/data/contract.ts` (regenerated)
- Create: `pipeline/tests/test_contract_v2.py`

**Interfaces:**
- Consumes: nothing new.
- Produces (all in `atlas.schema.contract`): `TOPIC_ID`, `GROUP_ID` (`F<field id>` or `G<nn>` fallback), `COLOR_TOKEN`; models `FileEntry`, `LlmTaskStats{task, model, items, from_cache, generated, repaired, fallback, cost_usd}`, `LabelStats{provider, llm, keywords, overrides}`, `Manifest` (+ `ci_level, as_of_year, trimmed_years, embedding_provider, n_orgs_unverified, ingest_errors, labels, llm`; `definition_version` default 3 — unchanged, user decision 2026-10-19), `TopicMetrics` (+ `no_baseline`, `share_ratio: float | None`, `low_data_reason ∈ {few_articles, not_estimable} | None`), `TopicForecast`, `TopicLineage`, `TopicNowcast{year, as_of_month, ytd, mean}`, `Topic` (+ `label_source, subfield, subfield_en, cross_field, taxonomy_vote, nowcast`), `TopicsFile`, `GroupInfo`, `SubfieldInfo`, `TaxonomyFile`, `YearCount`, `Kpis`, `DataQuality`, `Brief{headline_th, headline_en, bullets_th, bullets_en, source}`, `Overview` (+ `brief`), `SeriesFile` (aligned-lengths validator), `Edge`, `EdgesFile`, `RepresentativeArticle`, `CountItem`, `Narrative{th, en, source}`, `TopicDetail` (+ `narrative`), `EmergingKeyword` (+ `no_baseline`, `share_ratio: float | None`), `KeywordsFile`, `Latest{release, path, schema_version, generated_at}`; `FILE_MODELS`, `model_for(path)`, `contract_json_schema()` (properties: manifest, overview, taxonomy, topics, topic_detail, series, edges, keywords, latest), `write_json_schema(path)`.

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_contract_v2.py`:

```python
import pytest
from pydantic import ValidationError

from atlas.schema.contract import (
    FILE_MODELS,
    GroupInfo,
    SeriesFile,
    TopicDetail,
    TopicNowcast,
    contract_json_schema,
    model_for,
)


def test_every_published_file_has_a_model_and_a_schema_entry():
    props = contract_json_schema()["properties"]
    assert set(props) == {"manifest", "overview", "taxonomy", "topics", "topic_detail", "series", "edges",
                          "keywords", "latest"}
    assert model_for("topics/T000001.json") is TopicDetail and model_for("overview.json") is FILE_MODELS["overview.json"]
    assert model_for("unknown.json") is None


def test_series_must_be_aligned_and_ids_patterned():
    SeriesFile(years=[2023, 2024], corpus_total=[10, 12], topics={"T000001": [1, 2]})
    with pytest.raises(ValidationError, match="one value per year"):
        SeriesFile(years=[2023, 2024], corpus_total=[10, 12], topics={"T000001": [1]})
    with pytest.raises(ValidationError):
        TopicDetail(id="T1", articles=[])


def test_nan_and_hex_colours_are_rejected():
    with pytest.raises(ValidationError):
        TopicNowcast(year=2025, as_of_month=4, ytd=3, mean=float("nan"))
    with pytest.raises(ValidationError):
        GroupInfo(id="F33", th="ก", en="A", color="#FF5F1F", size=1, n_topics=1, x=0, y=0, r=1)
    GroupInfo(id="F33", th="ก", en="A", color="cat-01", size=1, n_topics=1, x=0, y=0, r=1)


def _metrics(**over):
    m = dict(count_recent=40, share_recent=0.01, share_baseline=0.0, share_ratio=None, no_baseline=True,
             share_growth=None, share_growth_lo=None, share_growth_hi=None, acceleration=0.0, burst_frac=0.0,
             novelty=0.0, n_journals_R=3, n_orgs_R=3, new_journal_share=0.0, journal_hhi=0.1, journal_driven=False,
             low_data_reason="not_estimable")
    return {**m, **over}


def test_no_baseline_topics_carry_a_null_ratio_and_a_low_data_reason():
    from atlas.schema.contract import TopicMetrics

    assert TopicMetrics(**_metrics()).share_ratio is None
    with pytest.raises(ValidationError):
        TopicMetrics(**_metrics(low_data_reason="other"))


def test_manifest_carries_the_interval_level_and_llm_accounting():
    from atlas.schema.contract import LabelStats, LlmTaskStats, Manifest

    m = Manifest(release="2026Q4", generated_at="2026-10-18T00:00:00Z", pipeline_version="abc", config_hash="0" * 16,
                 embedding_model="api|bge-m3|None", ci_level=0.9, trimmed_years=[2026],
                 labels=LabelStats(provider="llm", llm=10, keywords=1, overrides=2),
                 llm=[LlmTaskStats(task="label", model="m", items=11, from_cache=5, generated=5, repaired=1,
                                   fallback=1, cost_usd=0.02)])
    assert m.definition_version == 3 and m.llm[0].fallback == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_contract_v2.py -q`
Expected: FAIL — `ImportError: cannot import name 'FILE_MODELS'`.

- [ ] **Step 3: Replace `pipeline/atlas/schema/contract.py`**

```python
"""Data contract v2 — the JSON files of one release (output/data/<release>/) that web v2 reads.

Pydantic models are the source of truth → JSON Schema (`atlas schema`) → TypeScript
(`npm run gen:types` in web/). CI fails when either generated file drifts.
Files: manifest.json, overview.json, taxonomy.json, topics.json, topics/<id>.json, series.json,
edges.json, keywords.json; output/data/latest.json points at the newest release.
Strict JSON: NaN/Infinity are validation errors. Colours are design-token keys (cat-01…), never hex.
Uncertainty bounds keep level-agnostic names (share_growth_lo/_hi); the level is manifest.ci_level.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2.0.0"
Status = Literal["EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA"]
TOPIC_ID = r"^T\d{6}$"
GROUP_ID = r"^[FG]\d{2}$"                 # F = OpenAlex field id, G = agglomerative fallback group
COLOR_TOKEN = r"^cat-\d{2}$"              # colours are design-token keys, never hex


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)   # strict JSON: NaN/Infinity are errors


class FileEntry(_Model):
    path: str
    bytes: int
    sha256: str


class LlmTaskStats(_Model):
    task: str
    model: str
    items: int
    from_cache: int
    generated: int
    repaired: int
    fallback: int
    cost_usd: float


class LabelStats(_Model):
    provider: Literal["llm", "off"]
    llm: int = Field(description="topics named by the LLM (incl. cached names)")
    keywords: int = Field(description="topics named from author keywords (provider off or LLM fallback)")
    overrides: int = Field(description="topics whose name an editor corrected (labeling.overrides_path)")


class Manifest(_Model):
    schema_version: str = SCHEMA_VERSION
    release: str = Field(description="release tag, e.g. 2026Q4")
    generated_at: str
    pipeline_version: str
    config_hash: str
    definition_version: int = 3
    ci_level: float = Field(0.9, description="level of every *_lo/*_hi interval in this release")
    as_of_year: int | None = None
    trimmed_years: list[int] = Field(default_factory=list, description="years after last_complete_year")
    embedding_provider: str = ""
    embedding_model: str
    taxonomy_version: str | None = None
    modules: list[str] = Field(default_factory=list)
    files: list[FileEntry] = Field(default_factory=list)
    previous_release: str | None = None
    n_orgs_unverified: int = 0
    ingest_errors: int = 0
    labels: LabelStats | None = None
    llm: list[LlmTaskStats] = Field(default_factory=list)


class TopicMetrics(_Model):
    count_recent: int
    share_recent: float
    share_baseline: float
    share_ratio: float | None = Field(description="null when no_baseline")
    no_baseline: bool = Field(False, description="no articles in the baseline window — show 'new — no baseline'")
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
    orgs_unverified: bool = False      # v3: institution breadth rule skipped (affiliation coverage too low)
    low_data_reason: Literal["few_articles", "not_estimable"] | None = None


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


class TopicNowcast(_Model):
    year: int
    as_of_month: int = Field(ge=1, le=12)
    ytd: int
    mean: float


class Topic(_Model):
    id: str = Field(pattern=TOPIC_ID)
    group: str
    th: str
    en: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    label_source: Literal["llm", "keywords", "override"] = "keywords"
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
    subfield: str | None = None               # OpenAlex subfield id, e.g. "3304"
    subfield_en: str = ""
    cross_field: bool = False                 # subfield vote < taxonomy.min_vote_share
    taxonomy_vote: float | None = None
    nowcast: TopicNowcast | None = None


class TopicsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    topics: list[Topic]


class GroupInfo(_Model):
    id: str = Field(pattern=GROUP_ID)
    th: str
    en: str
    color: str = Field(pattern=COLOR_TOKEN)
    size: int
    n_topics: int
    x: float
    y: float
    r: float


class SubfieldInfo(_Model):
    id: str
    en: str
    group: str = Field(pattern=GROUP_ID)
    n_topics: int
    size: int


class TaxonomyFile(_Model):
    schema_version: str = SCHEMA_VERSION
    source: Literal["openalex", "agglomerative"]
    version: str | None = None
    holdout_accuracy_subfield: float | None = None
    holdout_accuracy_field: float | None = None
    groups: list[GroupInfo]
    subfields: list[SubfieldInfo] = Field(default_factory=list)


class YearCount(_Model):
    year: int
    articles: float


class Kpis(_Model):
    articles: int
    assigned_articles: int
    topics: int
    groups: int
    journals: int
    institutions: int
    pct_abstract_en: float
    pct_doi: float
    pct_keywords: float


class DataQuality(_Model):
    year_missing: int
    unassigned_articles: int
    completeness_method: str                       # median (v3 backfill guard) | configured (min_year_complete)
    text_quality: dict[str, int] = Field(default_factory=dict)


class Brief(_Model):
    headline_th: str
    headline_en: str
    bullets_th: list[str] = Field(default_factory=list)
    bullets_en: list[str] = Field(default_factory=list)
    source: Literal["llm", "template"]


class Overview(_Model):
    schema_version: str = SCHEMA_VERSION
    release: str
    previous_release: str | None = None
    generated_at: str
    definition_version: int = 3
    last_complete_year: int
    kpis: Kpis
    status_counts: dict[str, int]
    corpus_by_year: list[YearCount]
    corpus_forecast: list[YearCount] = Field(default_factory=list)
    nowcast: TopicNowcast | None = None
    lineage_events: dict[str, int] = Field(default_factory=dict)
    retired_topics: list[str] = Field(default_factory=list)
    data_quality: DataQuality
    brief: Brief | None = None


class SeriesFile(_Model):
    schema_version: str = SCHEMA_VERSION
    years: list[int]
    corpus_total: list[int]
    topics: dict[str, list[int]]

    @model_validator(mode="after")
    def _aligned(self):
        n = len(self.years)
        if len(self.corpus_total) != n or any(len(v) != n for v in self.topics.values()):
            raise ValueError("every series must have one value per year")
        return self


class Edge(_Model):
    s: str = Field(pattern=TOPIC_ID)
    t: str = Field(pattern=TOPIC_ID)
    w: float


class EdgesFile(_Model):
    schema_version: str = SCHEMA_VERSION
    edges: list[Edge]


class RepresentativeArticle(_Model):
    article_id: str
    title: str
    title_en: str = ""
    year: int | None = None
    journal: str = ""
    url: str = ""
    doi: str = ""
    gx: float | None = None
    gy: float | None = None


class CountItem(_Model):
    key: str
    count: int


class Narrative(_Model):
    th: str
    en: str
    source: Literal["llm", "template"]


class TopicDetail(_Model):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(pattern=TOPIC_ID)
    articles: list[RepresentativeArticle]
    journals: list[CountItem] = Field(default_factory=list)
    institutions: list[CountItem] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    neighbors: list[str] = Field(default_factory=list)
    narrative: Narrative | None = None


class EmergingKeyword(_Model):
    term: str
    count_recent: int
    share_ratio: float | None = Field(description="null when no_baseline")
    no_baseline: bool = False
    growth: float | None
    growth_lo: float | None
    n_active_years: int
    n_orgs_R: int
    n_journals_R: int
    journal_driven: bool
    emerging: bool
    topic: str | None = None


class KeywordsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    keywords: list[EmergingKeyword]


class Latest(_Model):
    release: str
    path: str
    schema_version: str = SCHEMA_VERSION
    generated_at: str


# published file → model (validate + export use the same table); topics/<id>.json → TopicDetail
FILE_MODELS: dict[str, type[_Model]] = {
    "manifest.json": Manifest, "overview.json": Overview, "taxonomy.json": TaxonomyFile,
    "topics.json": TopicsFile, "series.json": SeriesFile, "edges.json": EdgesFile, "keywords.json": KeywordsFile,
}


def model_for(path: str) -> type[_Model] | None:
    if path.startswith("topics/") and path.endswith(".json"):
        return TopicDetail
    return FILE_MODELS.get(path)


def contract_json_schema() -> dict:
    from pydantic.json_schema import models_json_schema

    files = {"manifest": Manifest, "overview": Overview, "taxonomy": TaxonomyFile, "topics": TopicsFile,
             "topic_detail": TopicDetail, "series": SeriesFile, "edges": EdgesFile, "keywords": KeywordsFile,
             "latest": Latest}
    _, top = models_json_schema([(m, "validation") for m in files.values()], ref_template="#/definitions/{model}")
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "AtlasContract",
        "type": "object",
        "properties": {k: {"$ref": f"#/definitions/{m.__name__}"} for k, m in files.items()},
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

- [ ] **Step 4: Regenerate the schema and the TypeScript types**

Run (from `pipeline/`): `uv run atlas schema` then (from `web/`): `npm run gen:types`
Expected: both files change; `uv run pytest tests/test_schema.py -q` passes (drift check), `npm run build` in `web/` still compiles (the current web does not import the new types).

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/schema/contract.py pipeline/tests/test_contract_v2.py web/src/data/contract.schema.json web/src/data/contract.ts
git commit -m "feat(contract): data contract v2 for every published file (+ no_baseline, low_data_reason, ci_level, narrative, brief, LLM accounting)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 16: Export v2 — `output/data/<release>/` + sha256 manifest + `output/data/latest.json` (v1.1 `atlas_data.json` kept)

**Files:**
- Create: `pipeline/atlas/export_v2.py`, `pipeline/tests/test_release.py`
- Modify: `pipeline/atlas/export.py` (call `write_release` at the end when `export.v2`)

**Interfaces:**
- Consumes: every checkpoint of the run — `02_docs` + `03_embeddings` via `load_aligned`, `01_authors`, `01_ingest_errors` (P0 fix wave; optional), `03_meta.json`, `04_topic_info`, `04_fine_topics`, `04_centroids*`, `04_lineage`, `05_labels` (+ `label_source`), `05_labels_meta.json`, `05_merge_meta.json`, `06_series`, `06_meta.json`, `07_emerging`, `07_keywords`, `08_forecasts`, `08_forecast_meta.json`, `09_layout`, `09_edges`, `09_galaxy`, `10_taxonomy` (+ meta), `11_narratives`, `11_brief.json`; state `releases/<release>/topics/registry.parquet`; contract models (Task 15).
- Produces: `atlas.export_v2`: `config_hash(cfg) -> str` (16 hex; result-changing settings only), `group_code(gid, source) -> "F33" | "G03"`, `build_release(cfg) -> {published path: model}`, `write_release(cfg) -> Path` (replaces `output/data/<release>/` completely on a re-run; writes `latest.json` = `{release, path: "<release>/manifest.json", schema_version, generated_at}`). Topic metrics: `no_baseline` + `share_ratio: null` when `share_baseline == 0`; `low_data_reason` = `few_articles` (count_recent < `min_articles_recent`) or `not_estimable`. Manifest: `ci_level`, `definition_version` (config), `as_of_year`, `trimmed_years`, `embedding_provider`, `n_orgs_unverified`, `ingest_errors`, `labels`, `llm` (label · merge · narrative · brief stats of this run).

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_release.py` (a module fixture runs the whole pipeline twice, as releases 2026Q1 and 2026Q2, on the 11 real ThaiJO fixture files; Tasks 17–18 append to this file):

```python
"""Contract v2 export (→ validate → publish) on the 11 real ThaiJO files, as two releases."""
import hashlib
import json
import shutil

import pytest

from atlas.config import load_config
from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run
from atlas.schema.contract import Manifest, model_for
from tests.conftest import FIXTURES


@pytest.fixture(scope="module")
def two_releases(tmp_path_factory):
    root = tmp_path_factory.mktemp("rel")
    for rel in ("2026Q1", "2026Q2"):
        cfg = load_config(None)
        cfg["pipeline"].update(work_dir=str(root / "work"), output_dir=str(root / "out"),
                               state_dir=str(root / "state"), release=rel)
        cfg["input"].update(path=str(FIXTURES / "thaijo_md"), workers=1)
        cfg["embedding"]["provider"] = "lite"
        cfg["clustering"]["reducer"] = "pca"
        run(cfg, STEPS)
    return root, cfg


def test_release_files_match_the_contract_and_link_back_to_thaijo(two_releases):
    root, _ = two_releases
    data = root / "out" / "data"
    assert json.loads((data / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q2"
    man = Manifest.model_validate_json((data / "2026Q2" / "manifest.json").read_text(encoding="utf-8"))
    assert man.previous_release == "2026Q1" and {f.path for f in man.files} >= {
        "overview.json", "taxonomy.json", "topics.json", "series.json", "edges.json", "keywords.json"}
    for f in man.files:
        raw = (data / "2026Q2" / f.path).read_bytes()
        assert len(raw) == f.bytes and hashlib.sha256(raw).hexdigest() == f.sha256
        model_for(f.path).model_validate_json(raw)
    topics = json.loads((data / "2026Q2" / "topics.json").read_text(encoding="utf-8"))["topics"]
    assert all(t["status"] == "LOW_DATA" and t["id"].startswith("T") for t in topics)
    assert topics[0]["lineage"]["born"] == "2026Q1" and topics[0]["lineage"]["event"] == "continue"
    assert all(t["metrics"]["low_data_reason"] in ("few_articles", "not_estimable") for t in topics)
    assert man.definition_version == 3 and man.ci_level == 0.9 and man.embedding_provider == "lite"
    assert man.labels.provider == "off" and man.labels.keywords == len(topics) and man.llm == []
    ov = json.loads((data / "2026Q2" / "overview.json").read_text(encoding="utf-8"))
    assert ov["brief"]["source"] == "template" and ov["definition_version"] == 3
    detail = json.loads((data / "2026Q2" / f"topics/{topics[0]['id']}.json").read_text(encoding="utf-8"))
    assert detail["articles"][0]["url"].startswith("https://so02.tci-thaijo.org/")
    blob = "".join(p.read_text(encoding="utf-8") for p in (data / "2026Q2").rglob("*.json"))
    docs = read_table(root / "work" / "02_docs.parquet")
    snippets = [a[:40] for a in list(docs["abstract_th"]) + list(docs["abstract_en"]) if len(a) >= 40]
    assert snippets and not any(s in blob for s in snippets)     # abstracts are never published
    tax = json.loads((data / "2026Q2" / "taxonomy.json").read_text(encoding="utf-8"))
    assert tax["source"] == "agglomerative" and all(g["color"].startswith("cat-") for g in tax["groups"])


def _copy(two_releases, tmp_path):
    root, cfg = two_releases
    dst = tmp_path / "data"
    shutil.copytree(root / "out" / "data", dst)
    return dst, cfg
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_release.py -q`
Expected: FAIL — `FileNotFoundError` for `out/data/latest.json` (nothing writes contract v2 yet).

- [ ] **Step 3: Create `pipeline/atlas/export_v2.py`**

```python
"""Export data contract v2 → output_dir/data/<release>/ (+ output_dir/data/latest.json).

Every file is built as a pydantic model from atlas/schema/contract.py (validation happens on
construction; NaN/Infinity are rejected) and written as compact strict JSON. manifest.json lists
every other file with its byte size and sha256, the interval level (ci_level), the v3 data-quality
fields and the label/LLM accounting. Representative articles carry titles and links back to ThaiJO
only — abstracts are never published (journal copyright). Institutions are counted at organisation
level; no person is ranked (PDPA). A topic or keyword with no baseline articles is published with
share_ratio null and no_baseline true (the web says "new — no baseline").
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.checkpoints import load_aligned
from atlas.export import _git_hash, fine_labels
from atlas.io_utils import read_table
from atlas.label import representative_indices
from atlas.lineage import topic_code
from atlas.schema import contract as C
from atlas.state import current_release, previous_release, release_dir
from atlas.taxonomy import load_topic_groups

N_COLOR_TOKENS = 12


def _f(v, nd: int = 4) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def _json_list(s) -> list:
    return json.loads(s) if isinstance(s, str) and s else []


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _optional(path: Path) -> pd.DataFrame | None:
    try:
        return read_table(path)
    except FileNotFoundError:
        return None


def config_hash(cfg: dict) -> str:
    """Hash of every setting that can change results (paths and the release name excluded)."""
    body = {k: v for k, v in cfg.items() if k != "pipeline"}
    body["pipeline"] = {k: v for k, v in cfg["pipeline"].items() if k in ("seed",)}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def group_code(gid: int, source: str) -> str:
    return f"{'F' if source == 'openalex' else 'G'}{int(gid):02d}"


def _metrics(e: pd.Series, min_recent: int) -> C.TopicMetrics:
    no_base = float(e["share_baseline"]) == 0.0
    reason = None
    if str(e["status"]) == "LOW_DATA":
        reason = "few_articles" if int(e["count_recent"]) < min_recent else "not_estimable"
    return C.TopicMetrics(
        count_recent=int(e["count_recent"]), share_recent=_f(e["share_recent"], 6) or 0.0,
        share_baseline=_f(e["share_baseline"], 6) or 0.0,
        share_ratio=None if no_base else (_f(e["share_ratio"]) or 0.0), no_baseline=no_base,
        share_growth=_f(e["share_growth"]), share_growth_lo=_f(e["share_growth_lo"]),
        share_growth_hi=_f(e["share_growth_hi"]), acceleration=_f(e["acceleration"]) or 0.0,
        burst_frac=_f(e["burst_frac"]) or 0.0,
        burst_years=[int(y) for y in str(e["burst_years"] or "").split(",") if y.strip()],
        novelty=_f(e["novelty"]) or 0.0, coherence=_f(e["coherence"]), n_journals_R=int(e["n_journals_R"]),
        n_orgs_R=int(e["n_orgs_R"]), new_journal_share=_f(e["new_journal_share"]) or 0.0,
        journal_hhi=_f(e["journal_hhi"]) or 0.0, journal_driven=bool(e["journal_driven"]),
        orgs_unverified=bool(e.get("orgs_unverified", False)), low_data_reason=reason)


def _forecast(f: pd.Series) -> C.TopicForecast:
    show = bool(f["show"]) if pd.notna(f["show"]) else False
    lists = {k: [float(v) for v in _json_list(f[c])] if show else []
             for k, c in (("mean", "fc_mean"), ("lo80", "fc_lo80"), ("hi80", "fc_hi80"),
                          ("lo95", "fc_lo95"), ("hi95", "fc_hi95"))}
    return C.TopicForecast(model=str(f["model"]), mase=_f(f["mase"], 3), skill_vs_naive=_f(f["skill_vs_naive"], 3) or 0.0,
                           show=show, years=[int(y) for y in _json_list(f["fc_years"])] if show else [], **lists)


def build_release(cfg: dict) -> dict[str, C._Model]:
    """{published relative path: model} for one release (nothing is written)."""
    work = Path(cfg["pipeline"]["work_dir"])
    ecfg = cfg["export"]
    release, prev = current_release(cfg), previous_release(cfg)
    now = datetime.now(UTC).isoformat()
    docs, emb = load_aligned(work)
    info = read_table(work / "04_topic_info.parquet")
    labels = fine_labels(read_table(work / "05_labels.parquet")).set_index("topic_id")
    em = read_table(work / "07_emerging.parquet").set_index("topic_id")
    fc = read_table(work / "08_forecasts.parquet").set_index("topic_id")
    lay = read_table(work / "09_layout.parquet")
    edges = read_table(work / "09_edges.parquet")
    fine = docs[["article_id"]].merge(read_table(work / "04_fine_topics.parquet"), on="article_id", how="left")
    labels_arr = fine["fine_topic"].fillna(-1).astype(int).to_numpy()
    meta6 = _read_json(work / "06_meta.json")
    fmeta = _read_json(work / "08_forecast_meta.json")
    taxmeta = _read_json(work / "10_taxonomy_meta.json")
    tax = _optional(work / "10_taxonomy.parquet")
    source = "openalex" if tax is not None and len(tax) and (tax["source"] == "openalex").all() else "agglomerative"
    groups = load_topic_groups(work).set_index("topic_id")
    lineage = _optional(work / "04_lineage.parquet")
    lin = lineage.set_index("topic_id") if lineage is not None and len(lineage) else pd.DataFrame()
    reg_path = release_dir(cfg, release) / "topics" / "registry.parquet"
    born = read_table(reg_path).set_index("topic_id")["born"].to_dict() if reg_path.exists() else {}
    galaxy = _optional(work / "09_galaxy.parquet")
    gxy = galaxy.set_index("article_id")[["gx", "gy"]] if galaxy is not None and len(galaxy) else None
    try:
        authors = read_table(work / "01_authors.parquet")[["article_id", "org_key"]]
    except FileNotFoundError:
        authors = pd.DataFrame(columns=["article_id", "org_key"])
    orgs = authors[authors["org_key"].astype(str) != ""].drop_duplicates()

    pos = lay[lay["kind"] == "topic"].set_index("id")
    hubs = lay[lay["kind"] == "group"].set_index("id")
    ids = [int(t) for t in info["topic_id"]]
    size_of = info.set_index("topic_id")["size"].to_dict()
    tax_i = tax.set_index("topic_id") if tax is not None and source == "openalex" else None
    code = {t: topic_code(t) for t in ids}
    cent_ids = json.loads((work / "04_centroid_ids.json").read_text(encoding="utf-8"))
    cents = dict(zip(cent_ids, np.load(work / "04_centroids.npy")))

    min_recent = int(cfg["emerging"]["min_articles_recent"])
    narr = _optional(work / "11_narratives.parquet")
    narratives = ({int(r.topic_id): C.Narrative(th=str(r.th), en=str(r.en), source=str(r.source))
                   for r in narr.itertuples()} if narr is not None else {})
    brief = _read_json(work / "11_brief.json")

    # ---- topics.json
    topics = []
    for t in ids:
        e, g = em.loc[t] if t in em.index else None, groups.loc[t]
        f = fc.loc[t] if t in fc.index else None
        lb = labels.loc[t] if t in labels.index else None
        ev = lin.loc[t] if len(lin) and t in lin.index else None
        event = str(ev["event"]) if ev is not None and ev["event"] in ("new", "continue", "split", "merge") else "new"
        parents = [topic_code(int(p)) for p in str(ev["parents"] if ev is not None else "").split(";") if p]
        tx = tax_i.loc[t] if tax_i is not None and t in tax_i.index else None
        nowcast = None
        if f is not None and "nowcast_mean" in f and pd.notna(f["nowcast_mean"]):
            nowcast = C.TopicNowcast(year=int(f["nowcast_year"]), as_of_month=int(f["nowcast_month"]),
                                     ytd=int(f["nowcast_ytd"]), mean=float(f["nowcast_mean"]))
        topics.append(C.Topic(
            id=code[t], group=group_code(g["group_id"], source),
            th=str(lb["name_th"]) if lb is not None else code[t], en=str(lb["name_en"]) if lb is not None else code[t],
            description=str(lb["description"] or "") if lb is not None else "",
            keywords=[k for k in str(lb["keywords"] or "").split("; ") if k] if lb is not None else [],
            label_source=str(lb.get("label_source", "keywords")) if lb is not None else "keywords",
            size=int(size_of[t]),
            x=float(pos.loc[t, "x"]), y=float(pos.loc[t, "y"]), r=float(pos.loc[t, "r"]),
            status=str(e["status"]) if e is not None else "LOW_DATA",
            score=(_f(e["emerging_score"], 1) or 0.0) if e is not None else 0.0,
            metrics=_metrics(e, min_recent) if e is not None else C.TopicMetrics(
                count_recent=0, share_recent=0.0, share_baseline=0.0, share_ratio=None, share_growth=None,
                share_growth_lo=None, share_growth_hi=None, acceleration=0.0, burst_frac=0.0, novelty=0.0,
                n_journals_R=0, n_orgs_R=0, new_journal_share=0.0, journal_hhi=0.0, journal_driven=False,
                low_data_reason="few_articles"),
            forecast=_forecast(f) if f is not None else None,
            lineage=C.TopicLineage(born=born.get(t), event=event, parents=parents),
            subfield=str(tx["subfield_id"]) if tx is not None else None,
            subfield_en=str(tx["subfield_en"]) if tx is not None else "",
            cross_field=bool(tx["cross_field"]) if tx is not None else False,
            taxonomy_vote=_f(tx["vote_share"]) if tx is not None else None,
            nowcast=nowcast))
    files: dict[str, C._Model] = {"topics.json": C.TopicsFile(topics=topics)}

    # ---- topics/<id>.json
    titles = docs.set_index("article_id")
    for t in ids:
        members = np.where(labels_arr == t)[0]
        idx = representative_indices(emb[members], cents[t], int(ecfg["repr_articles"]),
                                     float(cfg["labeling"]["mmr_lambda"])) if len(members) else []
        arts = []
        for aid in docs["article_id"].to_numpy()[members[idx]] if len(members) else []:
            row = titles.loc[aid]
            year = row.get("year")
            arts.append(C.RepresentativeArticle(
                article_id=str(aid), title=str(row.get("title", "") or ""), title_en=str(row.get("title_en", "") or ""),
                year=int(year) if pd.notna(year) else None, journal=str(row.get("journal_name", "") or ""),
                url=str(row.get("url", "") or ""), doi=str(row.get("doi", "") or ""),
                gx=_f(gxy.loc[aid, "gx"], 2) if gxy is not None and aid in gxy.index else None,
                gy=_f(gxy.loc[aid, "gy"], 2) if gxy is not None and aid in gxy.index else None))
        member_ids = docs["article_id"].to_numpy()[members]
        jc = titles.loc[member_ids, "journal_name"].value_counts().head(int(ecfg["max_topic_journals"]))
        oc = (orgs[orgs["article_id"].isin(set(member_ids))]["org_key"].value_counts()
              .head(int(ecfg["max_topic_orgs"])))
        nb = pd.concat([edges[edges["s"] == t].rename(columns={"t": "o"})[["o", "w"]],
                        edges[edges["t"] == t].rename(columns={"s": "o"})[["o", "w"]]])
        nb = nb.sort_values(["w", "o"], ascending=[False, True]).head(int(ecfg["max_neighbors"]))
        lb = labels.loc[t] if t in labels.index else None
        files[f"topics/{code[t]}.json"] = C.TopicDetail(
            id=code[t], articles=arts,
            journals=[C.CountItem(key=str(k), count=int(v)) for k, v in jc.items()],
            institutions=[C.CountItem(key=str(k), count=int(v)) for k, v in oc.items()],
            keywords=[k for k in str(lb["keywords"] or "").split("; ") if k] if lb is not None else [],
            neighbors=[code[int(o)] for o in nb["o"] if int(o) in code], narrative=narratives.get(t))

    # ---- taxonomy.json (groups = map hubs)
    gsize = info.assign(g=info["topic_id"].map(groups["group_id"])).groupby("g")["size"].agg(["sum", "count"])
    order = gsize.sort_values("sum", ascending=False).index.tolist()
    names = groups.drop_duplicates("group_id").set_index("group_id")
    group_rows = []
    for rank, gid in enumerate(order):
        th, en = str(names.loc[gid, "group_th"] or ""), str(names.loc[gid, "group_en"] or "")
        if not th or not en:                      # agglomerative fallback: name of its largest topic
            big = int(info[info["topic_id"].map(groups["group_id"]) == gid].sort_values("size").iloc[-1]["topic_id"])
            th = th or (str(labels.loc[big, "name_th"]) if big in labels.index else code[big])
            en = en or (str(labels.loc[big, "name_en"]) if big in labels.index else code[big])
        h = hubs.loc[gid] if gid in hubs.index else None
        group_rows.append(C.GroupInfo(id=group_code(gid, source), th=th, en=en,
                                      color=f"cat-{rank % N_COLOR_TOKENS + 1:02d}", size=int(gsize.loc[gid, "sum"]),
                                      n_topics=int(gsize.loc[gid, "count"]), x=float(h["x"]) if h is not None else 0.0,
                                      y=float(h["y"]) if h is not None else 0.0, r=float(h["r"]) if h is not None else 0.0))
    subfields = []
    if source == "openalex":
        tx = tax.merge(info[["topic_id", "size"]], on="topic_id")
        for sid, g in tx.groupby("subfield_id"):
            subfields.append(C.SubfieldInfo(id=str(sid), en=str(g["subfield_en"].iloc[0]),
                                            group=group_code(int(g["group_id"].iloc[0]), source),
                                            n_topics=int(len(g)), size=int(g["size"].sum())))
    files["taxonomy.json"] = C.TaxonomyFile(
        source=source, version=taxmeta.get("version"),
        holdout_accuracy_subfield=_f(taxmeta.get("holdout_accuracy_subfield")),
        holdout_accuracy_field=_f(taxmeta.get("holdout_accuracy_field")), groups=group_rows, subfields=subfields)

    # ---- series.json + edges.json + keywords.json
    s = read_table(work / "06_series.parquet")
    years = [int(y) for y in meta6.get("years", [])]
    files["series.json"] = C.SeriesFile(
        years=years, corpus_total=[int(meta6["totals"][str(y)]) for y in years],
        topics={code[int(t)]: g.set_index("year")["count"].reindex(years, fill_value=0).astype(int).tolist()
                for t, g in s.groupby("topic_id") if int(t) in code})
    files["edges.json"] = C.EdgesFile(edges=[C.Edge(s=code[int(r.s)], t=code[int(r.t)], w=float(r.w))
                                             for r in edges.itertuples() if int(r.s) in code and int(r.t) in code])
    kw = _optional(work / "07_keywords.parquet")
    if kw is not None:
        files["keywords.json"] = C.KeywordsFile(keywords=[
            C.EmergingKeyword(term=str(r.term), count_recent=int(r.count_recent),
                              share_ratio=None if bool(r.no_baseline) else (_f(r.share_ratio) or 0.0),
                              no_baseline=bool(r.no_baseline),
                              growth=_f(r.growth), growth_lo=_f(r.growth_lo), n_active_years=int(r.n_active_years),
                              n_orgs_R=int(r.n_orgs_R), n_journals_R=int(r.n_journals_R),
                              journal_driven=bool(r.journal_driven), emerging=bool(r.emerging),
                              topic=code.get(int(r.topic_id)))
            for r in kw.head(int(cfg["keywords"]["max_terms"])).itertuples()])

    # ---- overview.json
    nonempty = {c: docs[c].fillna("").astype(str).str.len() > 0 for c in ("abstract_en", "doi") if c in docs}
    kw_any = (docs.get("keywords_th", pd.Series("", index=docs.index)).fillna("").astype(str)
              + docs.get("keywords_en", pd.Series("", index=docs.index)).fillna("").astype(str)).str.len() > 0
    tq = pd.Series([f for v in docs.get("text_quality", pd.Series(dtype=str)).fillna("") for f in str(v).split("; ") if f])
    comp = meta6.get("completeness", {})
    nc = fmeta.get("nowcast")
    events = (lineage["event"].value_counts().to_dict() if lineage is not None else {})
    files["overview.json"] = C.Overview(
        release=release, previous_release=prev, generated_at=now, last_complete_year=int(meta6["last_complete_year"]),
        definition_version=int(cfg["emerging"]["definition_version"]),
        brief=C.Brief(**brief["brief"]) if brief.get("brief") else None,
        kpis=C.Kpis(articles=len(docs), assigned_articles=int((labels_arr >= 0).sum()), topics=len(ids),
                    groups=len(group_rows), journals=int(docs["journal_name"].nunique()),
                    institutions=int(orgs["org_key"].nunique()),
                    pct_abstract_en=round(100 * float(nonempty["abstract_en"].mean()), 1) if "abstract_en" in nonempty else 0.0,
                    pct_doi=round(100 * float(nonempty["doi"].mean()), 1) if "doi" in nonempty else 0.0,
                    pct_keywords=round(100 * float(kw_any.mean()), 1) if len(docs) else 0.0),
        status_counts={str(k): int(v) for k, v in em["status"].value_counts().items()},
        corpus_by_year=[C.YearCount(year=y, articles=int(meta6["totals"][str(y)])) for y in years],
        corpus_forecast=[C.YearCount(year=int(y), articles=float(m))
                         for y, m in zip(fmeta.get("total_years", []), fmeta.get("total_mean", []))],
        nowcast=C.TopicNowcast(year=nc["year"], as_of_month=nc["as_of_month"], ytd=nc["ytd"], mean=nc["mean"]) if nc else None,
        lineage_events={str(k): int(v) for k, v in events.items()},
        retired_topics=[topic_code(int(r.topic_id)) for r in (lineage.itertuples() if lineage is not None else [])
                        if r.event == "retired"],
        data_quality=C.DataQuality(year_missing=int(docs["year"].isna().sum()),
                                   unassigned_articles=int((labels_arr < 0).sum()),
                                   completeness_method=str(comp.get("method", "median")),
                                   text_quality={str(k): int(v) for k, v in tq.value_counts().items()}))
    emb_meta = _read_json(work / "03_meta.json")
    modules = ["overview", "taxonomy", "topics", "topic_detail", "series", "edges"] + (["keywords"] if kw is not None else [])
    errs = _optional(work / "01_ingest_errors.parquet")
    files["manifest.json"] = C.Manifest(
        release=release, generated_at=now, pipeline_version=_git_hash(), config_hash=config_hash(cfg),
        definition_version=int(cfg["emerging"]["definition_version"]), ci_level=float(cfg["emerging"]["ci_level"]),
        as_of_year=meta6.get("as_of_year"), trimmed_years=[int(y) for y in meta6.get("trimmed_years", [])],
        embedding_provider=str(cfg["embedding"]["provider"]), embedding_model=str(emb_meta.get("model_id", "")),
        taxonomy_version=taxmeta.get("version"), modules=modules, previous_release=prev,
        n_orgs_unverified=int(em["orgs_unverified"].astype(bool).sum()) if "orgs_unverified" in em else 0,
        ingest_errors=len(errs) if errs is not None else 0,
        labels=_label_stats(cfg, labels), llm=_llm_stats(work, brief))
    return files


def _label_stats(cfg: dict, labels: pd.DataFrame) -> C.LabelStats:
    src = labels["label_source"] if "label_source" in labels else pd.Series("keywords", index=labels.index)
    return C.LabelStats(provider=cfg["labeling"]["provider"], llm=int((src == "llm").sum()),
                        keywords=int((src == "keywords").sum()), overrides=int((src == "override").sum()))


def _llm_stats(work: Path, brief: dict) -> list[C.LlmTaskStats]:
    """Per LLM task of this run: items, cache hits, new calls, repairs, fallbacks and spend."""
    found = []
    lab = _read_json(work / "05_labels_meta.json")
    if lab.get("provider") == "llm":
        found.append({**lab, "task": "label", "model": lab.get("model_id", ""), "items": lab.get("topics", 0)})
    merge = _read_json(work / "05_merge_meta.json").get("llm")
    found += [merge] if merge else []
    found += list((brief.get("llm") or {}).values())
    keys = ("from_cache", "generated", "repaired", "fallback")
    return [C.LlmTaskStats(task=s["task"], model=str(s.get("model", "")), items=int(s.get("items", 0)),
                           **{k: int(s.get(k, 0)) for k in keys}, cost_usd=round(float(s.get("cost_usd", 0.0)), 4))
            for s in found]


def _dump(model: C._Model) -> bytes:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def write_release(cfg: dict) -> Path:
    files = build_release(cfg)
    release = current_release(cfg)
    root = Path(cfg["pipeline"]["output_dir"]) / "data"
    out = root / release
    if out.exists():
        shutil.rmtree(out)                         # a re-run of the same release replaces it completely
    entries = []
    for rel, model in sorted(files.items()):
        if rel == "manifest.json":
            continue
        data = _dump(model)
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        entries.append(C.FileEntry(path=rel, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    manifest = files["manifest.json"].model_copy(update={"files": entries})
    (out / "manifest.json").write_bytes(_dump(C.Manifest.model_validate(manifest.model_dump())))
    latest = C.Latest(release=release, path=f"{release}/manifest.json", generated_at=manifest.generated_at)
    (root / "latest.json").write_bytes(_dump(latest))
    print(f"[export] contract v2 → {out} ({len(entries)} files + manifest)")
    return out
```

- [ ] **Step 4: Call it from the export step** — end of `export()` in `pipeline/atlas/export.py` (the v1.1 `atlas_data.json`, CSVs and manifest are unchanged — the current web keeps working until web v2 ships):

Replace
```python
    print(f"[export] -> {outdir / 'atlas_data.json'} (+ csv, manifest); centroids -> {prev}")
    return atlas
```
with
```python
    print(f"[export] -> {outdir / 'atlas_data.json'} (+ csv, manifest); centroids -> {prev}")
    if cfg["export"].get("v2", False):
        from atlas.export_v2 import write_release

        write_release(cfg)
    return atlas
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_release.py -q && uv run pytest -q`
Expected: all pass (the fixture takes ~40 s: two full runs with PCA).

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/export_v2.py pipeline/atlas/export.py pipeline/tests/test_release.py
git commit -m "feat(export): data contract v2 release folder with sha256 manifest and latest.json (atlas_data.json 1.1 kept)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 17: `atlas validate` — integrity, schema, coherence, diff vs the previous release, LLM fallbacks (exit 0 / 1 / 2)

**Files:**
- Create: `pipeline/atlas/validate.py`
- Modify: `pipeline/atlas/cli.py` (append `validate`), `pipeline/tests/test_release.py` (append)

**Interfaces:**
- Consumes: a release folder written by Task 16; contract models (`Manifest`, `model_for`); config `validation.*` (Task 1).
- Produces: `atlas.validate`: `Report(release_dir, previous_dir, errors, warnings, stats)` with `.exit_code` (0 clean · 1 warnings · 2 errors), `validate_release(release_dir, previous_dir, vcfg) -> Report` (previous = `manifest.previous_release` next to it when not given; unreadable previous → warning, diff skipped), `render_report(rep) -> str`; CLI `atlas validate [-c CFG] [--release R] [--dir PATH] [--previous PATH]`.
  - Checks: integrity (manifest parses; listed files exist with size + sha256; unlisted JSON → warning; required files present) · schema (every file against its model) · coherence (unique ids; one `topics/<id>.json` each; series/edges name known topics; groups exist in taxonomy; KPI topic count) · diff (topic count change, ids kept, status flips, size swings → warnings; corpus shrink → error) · LLM (keyword-fallback names, narrative/brief fallbacks → warnings).

- [ ] **Step 1: Write the failing tests** — append to `pipeline/tests/test_release.py`:

```python


def test_validate_clean_release_and_diff_against_previous(two_releases):
    from atlas.validate import validate_release

    root, cfg = two_releases
    rep = validate_release(root / "out" / "data" / "2026Q2", None, cfg["validation"])
    assert rep.exit_code == 0, rep.errors + rep.warnings
    assert rep.previous_dir is not None and rep.stats["kept_ids"] == 1.0 and rep.stats["topics"] >= 1


def test_tampered_or_extra_files_are_reported(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    (data / "2026Q2" / "edges.json").write_text('{"edges": []}', encoding="utf-8")
    (data / "2026Q2" / "notes.json").write_text("{}", encoding="utf-8")
    rep = validate_release(data / "2026Q2", None, cfg["validation"])
    assert rep.exit_code == 2
    assert any("edges.json: size/sha256" in e for e in rep.errors)
    assert any("notes.json: on disk but not in the manifest" in w for w in rep.warnings)


def test_diff_flags_lost_ids_and_a_shrinking_corpus(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    prev = data / "2026Q1"
    t = json.loads((prev / "topics.json").read_text(encoding="utf-8"))
    t["topics"] += [{**t["topics"][0], "id": f"T9{i:05d}"} for i in range(3)]      # ids that vanished
    (prev / "topics.json").write_text(json.dumps(t), encoding="utf-8")
    ov = json.loads((prev / "overview.json").read_text(encoding="utf-8"))
    ov["kpis"]["articles"] = 100
    (prev / "overview.json").write_text(json.dumps(ov), encoding="utf-8")
    rep = validate_release(data / "2026Q2", prev, cfg["validation"])
    assert rep.exit_code == 2
    assert any("remain" in w for w in rep.warnings) and any("corpus shrank" in e for e in rep.errors)


def test_missing_previous_release_only_warns(two_releases, tmp_path):
    from atlas.validate import validate_release

    root, cfg = two_releases
    rep = validate_release(root / "out" / "data" / "2026Q2", tmp_path / "no-such-release", cfg["validation"])
    assert rep.exit_code == 1 and any("diff skipped" in w for w in rep.warnings)


def test_cli_validate_exit_codes(two_releases, tmp_path):
    from typer.testing import CliRunner

    from atlas.cli import app

    root, _ = two_releases
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(f"pipeline:\n  output_dir: '{(root / 'out').as_posix()}'\n  release: 2026Q2\n",
                        encoding="utf-8")
    res = CliRunner().invoke(app, ["validate", "--config", str(cfg_file)])
    assert res.exit_code == 0 and "atlas validate: OK" in res.stdout
    res = CliRunner().invoke(app, ["validate", "--dir", str(tmp_path / "empty")])
    assert res.exit_code == 2 and "manifest.json is missing" in res.stdout


def test_llm_fallbacks_are_reported(two_releases, tmp_path):
    from atlas.validate import validate_release

    data, cfg = _copy(two_releases, tmp_path)
    path = data / "2026Q2" / "manifest.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    m["labels"] = {"provider": "llm", "llm": 2, "keywords": 1, "overrides": 0}
    m["llm"] = [{"task": "narrative", "model": "m", "items": 4, "from_cache": 0, "generated": 3, "repaired": 0,
                 "fallback": 1, "cost_usd": 0.01}]
    path.write_text(json.dumps(m), encoding="utf-8")              # the manifest does not hash itself
    rep = validate_release(data / "2026Q2", None, cfg["validation"])
    assert rep.exit_code == 1
    assert any("fell back to keywords" in w for w in rep.warnings)
    assert any("narrative: 1 of 4" in w for w in rep.warnings)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_release.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.validate'`.

- [ ] **Step 3: Create `pipeline/atlas/validate.py`**

```python
"""`atlas validate` — check one release folder before it is published.

1. integrity  manifest.json parses; every listed file exists with the listed size and sha256;
              JSON files on disk that the manifest does not list → warning
2. schema     every file validates against its pydantic model (atlas/schema/contract.py)
3. coherence  unique topic ids; one topics/<id>.json per topic; series and edges only name known
              topics; every topic's group exists in taxonomy.json; KPI topic count matches
4. diff       against the previous release folder (manifest.previous_release next to this one, or
              --previous): topic count change, share of last release's ids kept, status changes of
              continuing topics, large size swings, a shrinking corpus (thresholds: validation.*)
5. LLM        topic names that fell back to keywords and narrative/brief items that fell back to a
              template (invalid replies, or transient errors past max_retries) → warning: re-run `atlas llm` before publishing
Exit code: 0 = clean, 1 = warnings only, 2 = errors.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from atlas.schema.contract import SCHEMA_VERSION, Manifest, model_for


@dataclass
class Report:
    release_dir: str
    previous_dir: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return 2 if self.errors else 1 if self.warnings else 0


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _check_files(root: Path, rep: Report) -> dict[str, object]:
    """Integrity + schema. Returns {relative path: validated model} for files that passed."""
    try:
        manifest = Manifest.model_validate(_load(root / "manifest.json"))
    except FileNotFoundError:
        rep.errors.append("manifest.json is missing")
        return {}
    except (ValidationError, json.JSONDecodeError) as e:
        rep.errors.append(f"manifest.json is invalid: {e}")
        return {}
    if manifest.schema_version.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        rep.errors.append(f"schema major version {manifest.schema_version} ≠ pipeline {SCHEMA_VERSION}")
    models: dict[str, object] = {"manifest.json": manifest}
    listed = {f.path for f in manifest.files}
    for entry in manifest.files:
        p = root / entry.path
        if not p.exists():
            rep.errors.append(f"{entry.path}: listed in the manifest but missing")
            continue
        data = p.read_bytes()
        if len(data) != entry.bytes or hashlib.sha256(data).hexdigest() != entry.sha256:
            rep.errors.append(f"{entry.path}: size/sha256 differs from the manifest (file changed after export?)")
            continue
        model = model_for(entry.path)
        if model is None:
            rep.warnings.append(f"{entry.path}: no contract model — not schema-checked")
            continue
        try:
            models[entry.path] = model.model_validate(json.loads(data.decode("utf-8")))
        except (ValidationError, json.JSONDecodeError, UnicodeDecodeError) as e:
            rep.errors.append(f"{entry.path}: does not match the contract: {str(e).splitlines()[0]}")
    for p in sorted(root.rglob("*.json")):
        rel = p.relative_to(root).as_posix()
        if rel != "manifest.json" and rel not in listed:
            rep.warnings.append(f"{rel}: on disk but not in the manifest")
    for required in ("overview.json", "taxonomy.json", "topics.json", "series.json", "edges.json"):
        if required not in listed:
            rep.errors.append(f"{required}: required file not in the manifest")
    return models


def _check_coherence(models: dict, rep: Report) -> None:
    topics = models.get("topics.json")
    if topics is None:
        return
    ids = [t.id for t in topics.topics]
    known = set(ids)
    if len(known) != len(ids):
        rep.errors.append("topics.json: duplicate topic ids")
    missing = [i for i in ids if f"topics/{i}.json" not in models]
    if missing:
        rep.errors.append(f"{len(missing)} topics have no valid topics/<id>.json (e.g. {missing[0]})")
    if (s := models.get("series.json")) is not None and set(s.topics) != known:
        rep.errors.append("series.json: topic ids differ from topics.json")
    if (e := models.get("edges.json")) is not None and any(x.s not in known or x.t not in known for x in e.edges):
        rep.errors.append("edges.json: an edge names an unknown topic")
    if (tx := models.get("taxonomy.json")) is not None:
        groups = {g.id for g in tx.groups}
        bad = sorted({t.group for t in topics.topics} - groups)
        if bad:
            rep.errors.append(f"taxonomy.json: missing groups {bad[:5]}")
    if (ov := models.get("overview.json")) is not None and ov.kpis.topics != len(ids):
        rep.errors.append(f"overview.json: kpis.topics={ov.kpis.topics} but topics.json has {len(ids)}")
    rep.stats.update(topics=len(ids), articles=ov.kpis.articles if ov is not None else None,
                     statuses=ov.status_counts if ov is not None else {})


def _diff(models: dict, prev_root: Path, vcfg: dict, rep: Report) -> None:
    try:
        prev_topics = {t["id"]: t for t in _load(prev_root / "topics.json")["topics"]}
        prev_overview = _load(prev_root / "overview.json")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        rep.warnings.append(f"previous release at {prev_root} is unreadable ({e}) — diff skipped")
        return
    cur = {t.id: t for t in models["topics.json"].topics}
    n0, n1 = len(prev_topics), len(cur)
    change = abs(n1 - n0) / n0 if n0 else 0.0
    kept = len(set(prev_topics) & set(cur)) / n0 if n0 else 1.0
    common = sorted(set(prev_topics) & set(cur))
    flips = [i for i in common if prev_topics[i]["status"] != cur[i].status]
    flip_frac = len(flips) / len(common) if common else 0.0
    rep.stats.update(previous_topics=n0, topic_count_change=round(change, 4), kept_ids=round(kept, 4),
                     status_changes=len(flips))
    if change > float(vcfg["max_topic_count_change"]):
        rep.warnings.append(f"topic count {n0} → {n1} ({change:.0%} change)")
    if kept < float(vcfg["min_kept_ids"]):
        rep.warnings.append(f"only {kept:.0%} of the previous release's topic ids remain")
    if flip_frac > float(vcfg["max_status_change_frac"]):
        rep.warnings.append(f"{len(flips)} of {len(common)} continuing topics changed status ({flip_frac:.0%})")
    swing, floor = float(vcfg["size_swing_ratio"]), int(vcfg["size_swing_min_articles"])
    swings = [f"{i} {prev_topics[i]['size']}→{cur[i].size}" for i in common
              if max(prev_topics[i]["size"], cur[i].size) >= floor
              and max(prev_topics[i]["size"], cur[i].size) >= swing * max(min(prev_topics[i]["size"], cur[i].size), 1)]
    if swings:
        rep.warnings.append(f"{len(swings)} topics changed size ≥ {swing:g}×: " + ", ".join(swings[:10]))
    a0, a1 = int(prev_overview["kpis"]["articles"]), models["overview.json"].kpis.articles
    if a0 and (a0 - a1) / a0 > float(vcfg["max_article_drop"]):
        rep.errors.append(f"corpus shrank from {a0:,} to {a1:,} articles")


def _check_llm(manifest: Manifest | None, rep: Report) -> None:
    if manifest is None:
        return
    lab = manifest.labels
    if lab is not None and lab.provider == "llm" and lab.keywords:
        rep.warnings.append(f"{lab.keywords} topic names fell back to keywords (invalid replies, or transient errors past max_retries) "
                            "— run `atlas llm` again, then export")
    for s in manifest.llm:
        if s.task != "label" and s.fallback:
            rep.warnings.append(f"LLM {s.task}: {s.fallback} of {s.items} items use their fallback")


def validate_release(release_dir: str | Path, previous_dir: str | Path | None, vcfg: dict) -> Report:
    root = Path(release_dir)
    rep = Report(release_dir=str(root))
    models = _check_files(root, rep)
    _check_coherence(models, rep)
    manifest = models.get("manifest.json")
    _check_llm(manifest, rep)
    if previous_dir is None and manifest is not None and manifest.previous_release:
        cand = root.parent / manifest.previous_release
        previous_dir = cand if cand.exists() else None
    if previous_dir is not None and "topics.json" in models and "overview.json" in models:
        rep.previous_dir = str(previous_dir)
        _diff(models, Path(previous_dir), vcfg, rep)
    return rep


def render_report(rep: Report) -> str:
    status = {0: "OK", 1: "WARNINGS", 2: "ERRORS"}[rep.exit_code]
    lines = [f"atlas validate: {status} — {rep.release_dir}"]
    if rep.previous_dir:
        lines.append(f"  compared with {rep.previous_dir}")
    lines += [f"  stat  {k}: {v}" for k, v in rep.stats.items()]
    lines += [f"  ERROR {e}" for e in rep.errors] + [f"  WARN  {w}" for w in rep.warnings]
    return "\n".join(lines)
```

- [ ] **Step 4: CLI** — append to `pipeline/atlas/cli.py`:

```python


@app.command("validate")
def validate_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    release: str = typer.Option(None, help="release to check (default: pipeline.release / current quarter)"),
    release_dir: Path = typer.Option(None, "--dir", help="check this folder instead of output/data/<release>"),
    previous: Path = typer.Option(None, help="previous release folder (default: manifest.previous_release)"),
) -> None:
    """Validate a data-contract v2 release (schema + integrity + diff vs the previous release).

    Exit code 0 = clean, 1 = warnings, 2 = errors.
    """
    from atlas.config import load_config
    from atlas.state import current_release
    from atlas.validate import render_report, validate_release

    cfg = load_config(config)
    root = release_dir or Path(cfg["pipeline"]["output_dir"]) / "data" / (release or current_release(cfg))
    rep = validate_release(root, previous, cfg["validation"])
    typer.echo(render_report(rep))
    raise typer.Exit(rep.exit_code)
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_release.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/validate.py pipeline/atlas/cli.py pipeline/tests/test_release.py
git commit -m "feat(release): atlas validate — integrity, schema, coherence, diff vs previous release, LLM fallbacks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 18: `atlas publish --site` — data folder + `latest.json` + single-file offline HTML (Python only), optional tarball

Delivery is a static site that any host can serve (the web reads `data/latest.json` relative to its `BASE_URL` at run time and makes no API calls): a quarterly update is *copy the new data folder + latest.json* — no web rebuild, no Node on the operator's machine. The single-file edition is made by injecting the release into the prebuilt `offline-template.html` that the web build ships (P1b), with plain Python string replacement. The P0-planned tarball for a GitHub Release stays available behind `--tarball`; the `gh` command is printed, never run.

**Files:**
- Create: `pipeline/atlas/publish.py`
- Modify: `pipeline/atlas/cli.py` (append `publish`), `pipeline/tests/test_release.py` (append)

**Interfaces:**
- Consumes: `validate_release`, `render_report` (Task 17); `Latest` (Task 15); a release folder (Task 16).
- Produces: `atlas.publish`: `PublishRefused`, `package_release(release_dir, out_dir) -> (tar.gz, .sha256)`, `release_notes(release_dir) -> str`, `offline_bundle(release_dir, latest) -> {latest, files: {path: JSON}}`, `inject_offline(template_html, bundle) -> str` (fills `<script type="application/json" id="atlas-data">…</script>`; `</` escaped as `<\/`; `ValueError` without the tag), `publish_site(release_dir, site) -> {site_data, latest, offline_html | None}`, `publish(cfg, release=None, allow_warnings=False, site=None, tarball=False) -> dict`; CLI `atlas publish -c CFG [--release R] [--site DIR] [--tarball] [--allow-warnings]` (exit 2 when refused or when neither target is given).
  - Site layout (the contract with web v2, P1b): `<site>/data/<release>/…` (older releases kept), `<site>/data/latest.json` = `{release, path: "<release>/manifest.json", schema_version, generated_at}`, `<site>/atlas-offline.html` (bundle = `{latest, files}` — the web's DataSource reads the embedded bundle when the tag is non-empty, else fetches `data/latest.json`).

- [ ] **Step 1: Write the failing tests** — append to `pipeline/tests/test_release.py`:

```python


TEMPLATE = ('<!doctype html><html><head><title>Atlas</title></head><body><div id="root"></div>'
            '<script type="application/json" id="atlas-data">null</script><script src="assets/app.js"></script>'
            '</body></html>')


def test_publish_to_the_site_writes_data_latest_and_the_offline_html(two_releases, tmp_path):
    import re

    from atlas.publish import publish

    root, cfg = two_releases
    site = tmp_path / "site"
    site.mkdir()
    (site / "offline-template.html").write_text(TEMPLATE, encoding="utf-8")
    for rel in ("2026Q1", "2026Q2"):                                   # two quarters, published in order
        r = publish({**cfg, "pipeline": {**cfg["pipeline"], "release": rel}}, site=site)
    latest = json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))
    assert latest["release"] == "2026Q2" and (site / "data" / latest["path"]).exists()
    assert (site / "data" / "2026Q1" / "manifest.json").exists()      # older quarters stay for comparison
    html = (site / "atlas-offline.html").read_text(encoding="utf-8")
    bundle = json.loads(re.search(r'id="atlas-data">(.*?)</script>', html, re.S).group(1))
    assert bundle["latest"]["release"] == "2026Q2" and "topics.json" in bundle["files"]
    assert any(k.startswith("topics/T") for k in bundle["files"]) and '<script src="assets/app.js">' in html
    assert r["offline_html"].endswith("atlas-offline.html") and "tarball" not in r


def test_offline_injection_escapes_script_ends_and_needs_the_data_tag():
    from atlas.publish import inject_offline

    html = inject_offline(TEMPLATE, {"x": "</script><b>"})
    assert html.count("</script>") == 2 and "<\\/script><b>" in html
    with pytest.raises(ValueError, match="atlas-data"):
        inject_offline("<html></html>", {})


def test_site_without_a_template_still_gets_the_data(two_releases, tmp_path, capsys):
    from atlas.publish import publish

    root, cfg = two_releases
    r = publish({**cfg, "pipeline": {**cfg["pipeline"], "release": "2026Q2"}}, site=tmp_path / "bare")
    assert r["offline_html"] is None and (tmp_path / "bare" / "data" / "latest.json").exists()
    assert "offline-template.html not found" in capsys.readouterr().out


def test_package_is_reproducible_and_broken_releases_are_refused(two_releases, tmp_path):
    import tarfile

    from atlas.publish import PublishRefused, package_release, publish

    root, cfg = two_releases
    rel = root / "out" / "data" / "2026Q2"
    a = package_release(rel, tmp_path / "a")
    b = package_release(rel, tmp_path / "b")
    assert a[1].read_text().split()[0] == b[1].read_text().split()[0]
    with tarfile.open(a[0]) as tar:
        names = tar.getnames()
    assert "2026Q2/manifest.json" in names and all(n.startswith("2026Q2/") for n in names)
    data, cfg2 = _copy(two_releases, tmp_path)
    (data / "2026Q2" / "topics.json").write_text("{}", encoding="utf-8")
    cfg2 = {**cfg2, "pipeline": {**cfg2["pipeline"], "output_dir": str(tmp_path), "release": "2026Q2"}}
    with pytest.raises(PublishRefused):
        publish(cfg2, site=tmp_path / "site")
    assert not (tmp_path / "site").exists()                         # nothing reaches the site when refused


def test_cli_publish_needs_a_target_and_never_runs_gh(two_releases, tmp_path, monkeypatch):
    import subprocess

    from typer.testing import CliRunner

    from atlas.cli import app

    def no_subprocess(*a, **k):
        raise AssertionError("publish must not start processes")

    monkeypatch.setattr(subprocess, "run", no_subprocess)
    monkeypatch.setattr(subprocess, "Popen", no_subprocess)
    root, _ = two_releases
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(f"pipeline:\n  output_dir: '{(root / 'out').as_posix()}'\n  release: 2026Q2\n",
                        encoding="utf-8")
    assert CliRunner().invoke(app, ["publish", "--config", str(cfg_file)]).exit_code == 2
    res = CliRunner().invoke(app, ["publish", "--config", str(cfg_file), "--tarball", "--site", str(tmp_path / "s")])
    assert res.exit_code == 0 and "gh release create data-2026Q2" in res.stdout and "latest.json" in res.stdout
    notes = (root / "out" / "releases" / "atlas-data-2026Q2.notes.md").read_text(encoding="utf-8")
    assert notes.startswith("# TCI Research Atlas — data 2026Q2") and "LOW_DATA" in notes
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_release.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.publish'`.

- [ ] **Step 3: Create `pipeline/atlas/publish.py`**

```python
"""`atlas publish` — put a validated release on the static site (and, optionally, package it).

Validates first (refuses on errors, and on warnings unless allow_warnings). Then, with a site folder
(the web build output — any static host, opened from a sub-path):
  <site>/data/<release>/…        the contract v2 files, copied (a re-publish replaces that folder)
  <site>/data/latest.json        {release, path: "<release>/manifest.json", …} — the web reads it at run
                                 time relative to its BASE_URL; publishing a quarter = copying data, no rebuild
  <site>/atlas-offline.html      the single-file edition: the web build's offline-template.html with the
                                 release injected into <script type="application/json" id="atlas-data">
                                 by plain string replacement (Python only — no Node on the operator's machine)
Older releases already in <site>/data/ stay (the web can compare quarters).
With tarball=True also output/releases/atlas-data-<release>.tar.gz (deterministic: sorted members,
mtime 0, uid/gid 0, no gzip timestamp) + .sha256 + .notes.md, and the `gh release create` command is
printed for a human — never run.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import shutil
import tarfile
from pathlib import Path

from atlas.schema.contract import Latest
from atlas.state import current_release
from atlas.validate import render_report, validate_release

OFFLINE_TEMPLATE, OFFLINE_HTML = "offline-template.html", "atlas-offline.html"
_DATA_TAG = re.compile(r'(<script type="application/json" id="atlas-data">)(.*?)(</script>)', re.S)


class PublishRefused(RuntimeError):
    pass


def package_release(release_dir: str | Path, out_dir: str | Path) -> tuple[Path, Path]:
    root = Path(release_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tar_path = out / f"atlas-data-{root.name}.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for p in sorted(x for x in root.rglob("*") if x.is_file()):
            data = p.read_bytes()
            info = tarfile.TarInfo(f"{root.name}/{p.relative_to(root).as_posix()}")
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    with open(tar_path, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
        gz.write(buf.getvalue())
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    sha_path = tar_path.with_name(tar_path.name + ".sha256")
    sha_path.write_text(f"{digest}  {tar_path.name}\n", encoding="utf-8")
    return tar_path, sha_path


def release_notes(release_dir: str | Path) -> str:
    root = Path(release_dir)
    ov = json.loads((root / "overview.json").read_text(encoding="utf-8"))
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    k = ov["kpis"]
    lines = [f"# TCI Research Atlas — data {ov['release']}", "",
             f"- {k['articles']:,} articles · {k['topics']:,} topics · {k['groups']} groups · "
             f"{k['journals']:,} journals · {k['institutions']:,} institutions",
             f"- data through {ov['last_complete_year']} · schema {man['schema_version']} · "
             f"definition v{ov['definition_version']} · intervals {round(man.get('ci_level', 0.9) * 100)}% · "
             f"embedding `{man['embedding_model']}`",
             f"- previous release: {ov.get('previous_release') or '—'}", "", "## Status", ""]
    lines += [f"- {s}: {n}" for s, n in sorted(ov["status_counts"].items())]
    if ov.get("lineage_events"):
        lines += ["", "## Topic lineage", ""] + [f"- {e}: {n}" for e, n in sorted(ov["lineage_events"].items())]
    lines += ["", f"Files: {len(man['files']) + 1} (sha256 per file in manifest.json). Licence: CC BY 4.0.", ""]
    return "\n".join(lines)


def offline_bundle(release_dir: str | Path, latest: dict) -> dict:
    """{latest, files: {relative path: parsed JSON}} — what atlas-offline.html carries."""
    root = Path(release_dir)
    files = {p.relative_to(root).as_posix(): json.loads(p.read_text(encoding="utf-8"))
             for p in sorted(root.rglob("*.json"))}
    return {"latest": latest, "files": files}


def inject_offline(template_html: str, bundle: dict) -> str:
    """Put the bundle into the data <script> of the template; '</' is escaped so the JSON cannot end it."""
    payload = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    out, n = _DATA_TAG.subn(lambda m: m.group(1) + payload + m.group(3), template_html, count=1)
    if n != 1:
        raise ValueError(f'{OFFLINE_TEMPLATE} has no <script type="application/json" id="atlas-data"> element')
    return out


def publish_site(release_dir: Path, site: Path) -> dict:
    release = release_dir.name
    dst = site / "data" / release
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(release_dir, dst)
    man = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    latest = Latest(release=release, path=f"{release}/manifest.json", generated_at=man["generated_at"])
    latest_json = latest.model_dump(mode="json")
    (site / "data" / "latest.json").write_text(json.dumps(latest_json, ensure_ascii=False), encoding="utf-8")
    offline = None
    template = site / OFFLINE_TEMPLATE
    if template.exists():
        html = inject_offline(template.read_text(encoding="utf-8"), offline_bundle(release_dir, latest_json))
        offline = site / OFFLINE_HTML
        offline.write_text(html, encoding="utf-8")
    else:
        print(f"[publish] WARNING: {template} not found — build the web first (npm run build); "
              "the single-file offline edition was skipped")
    return {"site_data": str(dst), "latest": str(site / "data" / "latest.json"),
            "offline_html": str(offline) if offline else None}


def publish(cfg: dict, release: str | None = None, allow_warnings: bool = False, site: str | Path | None = None,
            tarball: bool = False) -> dict:
    release = release or current_release(cfg)
    rel_dir = Path(cfg["pipeline"]["output_dir"]) / "data" / release
    rep = validate_release(rel_dir, None, cfg["validation"])
    print(render_report(rep))
    if rep.exit_code == 2 or (rep.exit_code == 1 and not allow_warnings):
        raise PublishRefused(f"validation exit code {rep.exit_code} — fix the release (or pass --allow-warnings)")
    result: dict = {"release": release, "validation": rep.exit_code}
    if site is not None:
        result.update(publish_site(rel_dir, Path(site)))
    if tarball:
        out = Path(cfg["pipeline"]["output_dir"]) / "releases"
        tar_path, sha_path = package_release(rel_dir, out)
        notes = out / f"atlas-data-{release}.notes.md"
        notes.write_text(release_notes(rel_dir), encoding="utf-8")
        result.update(tarball=str(tar_path), sha256=str(sha_path), notes=str(notes),
                      gh_command=(f'gh release create data-{release} "{tar_path}" "{sha_path}" '
                                  f'--title "Atlas data {release}" --notes-file "{notes}"'))
    return result
```

- [ ] **Step 4: CLI** — append to `pipeline/atlas/cli.py`:

```python


@app.command("publish")
def publish_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    release: str = typer.Option(None, help="release to publish (default: pipeline.release / current quarter)"),
    site: Path = typer.Option(None, "--site", help="the static web folder: writes data/<release>/, "
                              "data/latest.json and atlas-offline.html"),
    tarball: bool = typer.Option(False, "--tarball", help="also package a reproducible tar.gz + notes "
                                 "for a GitHub Release (printed command, never uploaded)"),
    allow_warnings: bool = typer.Option(False, "--allow-warnings", help="publish even when validation warns"),
) -> None:
    """Validate a release, then put it on the static site and/or package it. Never uploads anything.

    Exit code 0 = published, 2 = refused (validation) or nothing to do.
    """
    from atlas.config import load_config
    from atlas.publish import PublishRefused, publish

    if site is None and not tarball:
        typer.echo("nothing to do: pass --site <web folder> and/or --tarball", err=True)
        raise typer.Exit(2)
    try:
        r = publish(load_config(config), release, allow_warnings, site, tarball)
    except PublishRefused as e:
        typer.echo(f"refused: {e}", err=True)
        raise typer.Exit(2) from e
    if site is not None:
        typer.echo(f"site data: {r['site_data']}\nlatest:    {r['latest']}\n"
                   f"offline:   {r['offline_html'] or 'skipped (no offline-template.html in the site folder)'}")
    if tarball:
        typer.echo(f"tarball: {r['tarball']}\nsha256:  {r['sha256']}\nnotes:   {r['notes']}")
        typer.echo(f"upload it yourself (needs the owner's go-ahead):\n  {r['gh_command']}")
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_release.py -q && uv run pytest -q`
Expected: all pass; no test starts a process or touches the network.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/publish.py pipeline/atlas/cli.py pipeline/tests/test_release.py
git commit -m "feat(release): atlas publish --site — data/<release> + latest.json + offline single-file HTML via Python; optional reproducible tarball (gh command printed, never run)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 19: `atlas bakeoff` — choose the embedding model and the clustering algorithm by numbers

Embedding candidates are scored on our own Thai works (journal kNN accuracy; OpenAlex subfield kNN accuracy on the Thai reference works; neighbour purity against the planted truth on the synthetic corpus). API candidates go through `embed_texts` → the P0 runner, one store per `store_id`, so a sample is paid for once and the winner's vectors are reused by the real run. Clustering candidates (`hdbscan`, `hdbscan_fast`, `leiden`) run with several seeds on the same vectors: ARI stability, agreement with the first algorithm (`ari_vs_first` — sklearn vs fast_hdbscan should be ≈ 1), purity, NPMI coherence. Measured on the 20K synthetic corpus: Leiden 0.3 s/run vs UMAP→HDBSCAN 19 s/run, both purity 1.0.

**Files:**
- Create: `pipeline/atlas/bakeoff.py`, `pipeline/tests/test_bakeoff.py`
- Modify: `pipeline/atlas/cli.py` (append `bakeoff`)

**Interfaces:**
- Consumes: `embed_texts`, `lite_embed` (Task 8), `fit_labels` (Tasks 4–5) with `clustering.hdbscan_backend` (Task 2), `knn_vote` (Task 9), `topic_terms`, `tokenize`, `load_reference` (Task 8), `load_aligned` (Task 2); config `bakeoff.*` (Task 1).
- Produces: `atlas.bakeoff`: `knn_accuracy`, `neighbor_purity`, `purity`, `ari_stability`, `npmi_coherence`, `embedding_bakeoff(texts, journals, candidates, k, holdout_frac, seed, truth=None, reference=None) -> DataFrame[candidate, dim, journal_knn_acc, subfield_knn_acc, truth_purity, seconds, error]`, `clustering_bakeoff(emb, texts, ccfg, algorithms, seeds, truth=None, npmi_top_n=10) -> DataFrame[algorithm, n_topics, unassigned, ari_stability, ari_vs_first, purity, npmi, seconds_per_run, error]`, `render_report(emb_df, clu_df, meta) -> Markdown`, `candidate_fn(cfg, cand)`, `run_bakeoff(cfg, kind, truth_path=None) -> Markdown`; CLI `atlas bakeoff -c CFG [--kind embedding|clustering|all] [--truth CSV] [--out MD]`. A missing optional extra or a broken candidate becomes an `error` row, never a crash.

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_bakeoff.py`:

```python
import math

import numpy as np
import pandas as pd
import pytest

from atlas.bakeoff import (
    ari_stability,
    clustering_bakeoff,
    embedding_bakeoff,
    knn_accuracy,
    neighbor_purity,
    npmi_coherence,
    purity,
    render_report,
    run_bakeoff,
)
from atlas.config import load_config
from atlas.io_utils import write_table

WORDS = {0: "ข้าว เกษตรกร ผลผลิต rice farmer yield", 1: "เบาหวาน อินซูลิน ผู้ป่วย diabetes insulin patient",
         2: "ท่องเที่ยว โฮมสเตย์ ชุมชน tourism homestay community"}


def _blobs(k=3, n_per=40, seed=0, noise=0.05):
    rng = np.random.default_rng(seed)
    X = np.vstack([np.eye(16)[c] + rng.normal(0, noise, (n_per, 16)) for c in range(k)])
    return (X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32), np.repeat(np.arange(k), n_per)


def test_metric_values_on_known_inputs():
    X, y = _blobs()
    assert knn_accuracy(X, y, 5, 0.3, 0) == 1.0 and neighbor_purity(X, y, 5) == 1.0
    assert purity(np.array([0, 0, 1, 1, -1]), ["a", "b", "c", "c", "a"]) == pytest.approx(0.75)
    assert ari_stability([np.array([0, 0, 1, 1]), np.array([1, 1, 0, 0])]) == pytest.approx(1.0)
    docs = [{"a", "b"}] * 50 + [{"c", "d"}] * 50
    assert npmi_coherence({0: ["a", "b"]}, docs, 10) == pytest.approx(1.0)
    assert npmi_coherence({0: ["a", "c"]}, docs, 10) == pytest.approx(-1.0)
    assert math.isnan(npmi_coherence({0: ["zzz"]}, docs, 10))


def test_embedding_bakeoff_ranks_a_real_signal_above_noise():
    texts = [f"{WORDS[t]} เอกสาร {i}" for i in range(60) for t in (0, 1, 2)]
    journals = [f"j{t}" for i in range(60) for t in (0, 1, 2)]
    truth = [t for i in range(60) for t in (0, 1, 2)]
    from atlas.embed import lite_embed

    lite = {"dim": 16, "ngram_min": 2, "ngram_max": 4, "max_features": 5000, "min_df": 1}
    cands = {"lite": lambda t: lite_embed(t, lite, 0),
             "noise": lambda t: np.random.default_rng(0).normal(size=(len(t), 16)),
             "broken": lambda t: (_ for _ in ()).throw(RuntimeError("no key"))}
    ref = ([WORDS[0]] * 10 + [WORDS[1]] * 10, ["1102"] * 10 + ["2712"] * 10)
    df = embedding_bakeoff(texts, journals, cands, k=5, holdout_frac=0.3, seed=1, truth=truth, reference=ref)
    r = df.set_index("candidate")
    assert r.loc["lite", "journal_knn_acc"] > 0.95 > r.loc["noise", "journal_knn_acc"]
    assert r.loc["lite", "subfield_knn_acc"] == 1.0 and r.loc["lite", "truth_purity"] > 0.95
    assert "no key" in r.loc["broken", "error"]


def test_clustering_bakeoff_and_report():
    X, y = _blobs(k=3, n_per=60)
    texts = [WORDS[int(t)] for t in y]
    ccfg = load_config(None)["clustering"]
    ccfg.update(reducer="pca")
    ccfg["fine"].update(hdbscan_min_cluster_size=20, hdbscan_min_samples=5)
    ccfg["leiden"].update(k=10, min_cluster_size=20)
    df = clustering_bakeoff(X, texts, ccfg, ["hdbscan", "hdbscan_fast", "leiden"], [1, 2], truth=y, npmi_top_n=5)
    h = df.set_index("algorithm").loc["hdbscan"]
    assert h["n_topics"] == 3 and h["ari_stability"] == 1.0 and h["purity"] == 1.0 and h["npmi"] > 0.5
    assert h["ari_vs_first"] == 1.0
    assert set(df["algorithm"]) == {"hdbscan", "hdbscan_fast", "leiden"}   # optional ones may be error rows
    fast = df.set_index("algorithm").loc["hdbscan_fast"]
    assert fast["error"] or fast["ari_vs_first"] > 0.95                   # same partition as sklearn
    md = render_report(None, df, {"sample": len(X)})
    assert md.startswith("# Bake-off report") and "| hdbscan |" in md and "Best stable clustering" in md


def test_run_bakeoff_from_a_work_dir(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["bakeoff"].update(sample=120, seeds=[1, 2], algorithms=["hdbscan"])
    cfg["clustering"].update(reducer="pca")
    cfg["clustering"]["fine"].update(hdbscan_min_cluster_size=15, hdbscan_min_samples=5)
    X, y = _blobs(k=3, n_per=50)
    work = tmp_path / "work"
    ids = [f"a{i}" for i in range(len(y))]
    write_table(pd.DataFrame({"article_id": ids, "doc_text": [WORDS[int(t)] for t in y],
                              "journal_name": [f"j{t}" for t in y]}), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", X)
    truth = tmp_path / "truth.csv"
    pd.DataFrame({"article_id": ids, "topic": y}).to_csv(truth, index=False)
    md = run_bakeoff(cfg, "all", truth)
    assert "## Embedding models" in md and "lite (configured)" in md and "| hdbscan |" in md
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_bakeoff.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'atlas.bakeoff'`.

- [ ] **Step 3: Create `pipeline/atlas/bakeoff.py`**

```python
"""Bake-offs — pick the embedding model and the clustering algorithm by numbers, not belief.

Embedding candidates (bakeoff.embedding_candidates) are scored on our own Thai works:
  journal_knn_acc    kNN (k) accuracy of predicting an article's journal from held-out neighbours
  subfield_knn_acc   kNN accuracy of the OpenAlex subfield on held-out Thai reference works (if available)
  truth_purity       mean share of each article's k nearest neighbours with the same planted topic
                     (synthetic corpus only — needs a truth CSV: article_id, topic)
Clustering algorithms (bakeoff.algorithms: hdbscan = UMAP→HDBSCAN→merge with sklearn, hdbscan_fast = the
same with fast_hdbscan, leiden = Leiden on a kNN graph) are run with every seed in bakeoff.seeds on the
same embeddings:
  ari_stability      mean pairwise adjusted Rand index between seeds (1 = identical partitions)
  ari_vs_first       ARI of the first run against the first algorithm's first run (do two backends agree?)
  purity             mean majority-topic share per cluster against the truth (synthetic only)
  npmi               mean NPMI coherence of each cluster's top c-TF-IDF terms over document co-occurrence
API candidates embed through the P0 runner (atlas.embed.embed_texts) into one store per store_id, so a
bake-off sample is paid for once and a winning model's vectors are reused by the real run.
The report is Markdown; nothing here changes the pipeline's configuration.
"""
from __future__ import annotations

import copy
import importlib.util
import itertools
import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.ctfidf import topic_terms
from atlas.taxonomy import knn_vote
from atlas.thai import tokenize

EmbedFn = Callable[[list[str]], np.ndarray]


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _unit(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float32)
    return X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)


# ------------------------------------------------------------------ metrics
def knn_accuracy(X: np.ndarray, y, k: int, holdout_frac: float, seed: int) -> float:
    y = np.asarray(y).astype(str)
    test = np.random.default_rng(seed).random(len(y)) < holdout_frac
    if not test.any() or test.all():
        return math.nan
    pred, _ = knn_vote(X[test], X[~test], y[~test], k)
    return float((pred == y[test]).mean())


def neighbor_purity(X: np.ndarray, y, k: int) -> float:
    y = np.asarray(y).astype(str)
    sim = X @ X.T
    np.fill_diagonal(sim, -np.inf)
    k = max(1, min(k, len(y) - 1))
    idx = np.argpartition(-sim, k - 1, axis=1)[:, :k]
    return float((y[idx] == y[:, None]).mean())


def purity(labels: np.ndarray, truth) -> float:
    """Mean over clusters (unassigned −1 excluded) of the majority truth label's share."""
    df = pd.DataFrame({"c": labels, "t": np.asarray(truth)})
    df = df[df["c"] >= 0]
    if df.empty:
        return math.nan
    return float(df.groupby("c")["t"].agg(lambda s: s.value_counts().iloc[0] / len(s)).mean())


def ari_stability(runs: list[np.ndarray]) -> float:
    from sklearn.metrics import adjusted_rand_score

    pairs = list(itertools.combinations(runs, 2))
    return float(np.mean([adjusted_rand_score(a, b) for a, b in pairs])) if pairs else math.nan


def npmi_coherence(top_terms: dict[int, list[str]], doc_tokens: list[set[str]], top_n: int) -> float:
    n = len(doc_tokens)
    if not n:
        return math.nan
    df: dict[str, set[int]] = {}
    wanted = {t for terms in top_terms.values() for t in terms[:top_n]}
    for i, toks in enumerate(doc_tokens):
        for t in toks & wanted:
            df.setdefault(t, set()).add(i)
    scores = []
    for terms in top_terms.values():
        ts = [t for t in terms[:top_n] if t in df]
        vals = []
        for a, b in itertools.combinations(ts, 2):
            joint = len(df[a] & df[b])
            if joint == 0:
                vals.append(-1.0)
                continue
            pj, pa, pb = joint / n, len(df[a]) / n, len(df[b]) / n
            vals.append(1.0 if pj == 1.0 else math.log(pj / (pa * pb)) / -math.log(pj))
        if vals:
            scores.append(float(np.mean(vals)))
    return float(np.mean(scores)) if scores else math.nan


# ------------------------------------------------------------------ embedding bake-off
def embedding_bakeoff(texts: list[str], journals, candidates: dict[str, EmbedFn], k: int, holdout_frac: float,
                      seed: int, truth=None, reference: tuple[list[str], list[str]] | None = None) -> pd.DataFrame:
    """Each candidate embeds corpus texts (+ reference texts, in one call) → one row of metrics."""
    rows = []
    ref_texts, ref_sub = reference if reference else ([], [])
    for name, fn in candidates.items():
        t0 = time.time()
        try:
            X = _unit(fn(list(texts) + list(ref_texts)))
        except Exception as e:  # noqa: BLE001 — a broken candidate is reported, not fatal
            rows.append({"candidate": name, "error": f"{type(e).__name__}: {e}"})
            continue
        D, R = X[:len(texts)], X[len(texts):]
        rows.append({
            "candidate": name, "dim": int(X.shape[1]),
            "journal_knn_acc": round(knn_accuracy(D, journals, k, holdout_frac, seed), 4),
            "subfield_knn_acc": round(knn_accuracy(R, ref_sub, k, holdout_frac, seed), 4) if len(R) else math.nan,
            "truth_purity": round(neighbor_purity(D, truth, k), 4) if truth is not None else math.nan,
            "seconds": round(time.time() - t0, 1), "error": ""})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ clustering bake-off
def clustering_bakeoff(emb: np.ndarray, texts: list[str], ccfg: dict, algorithms: list[str], seeds: list[int],
                       truth=None, npmi_top_n: int = 10) -> pd.DataFrame:
    from sklearn.metrics import adjusted_rand_score

    from atlas.cluster import fit_labels

    doc_tokens = [set(tokenize(t)) for t in texts]
    rows, reference = [], None
    for algo in algorithms:
        if algo == "leiden" and not _has_module("igraph"):
            rows.append({"algorithm": algo, "error": "igraph not installed (uv sync --extra leiden)"})
            continue
        if algo == "hdbscan_fast" and not _has_module("fast_hdbscan"):
            rows.append({"algorithm": algo, "error": "fast_hdbscan not installed (uv sync --extra fast)"})
            continue
        cfg_a = copy.deepcopy(ccfg)
        cfg_a["algorithm"] = "leiden" if algo == "leiden" else "hdbscan"
        cfg_a["hdbscan_backend"] = "fast" if algo == "hdbscan_fast" else "sklearn"
        runs, secs = [], []
        for s in seeds:
            t0 = time.time()
            runs.append(fit_labels(emb, cfg_a, s)[0])
            secs.append(time.time() - t0)
        first = runs[0]
        reference = first if reference is None else reference
        ids = sorted(set(first.tolist()) - {-1})
        terms = topic_terms({t: [texts[i] for i in np.where(first == t)[0]] for t in ids}, npmi_top_n,
                            int(ccfg["ctfidf_max_docs_per_topic"]), seeds[0])
        rows.append({
            "algorithm": algo, "n_topics": int(np.median([len(set(r.tolist()) - {-1}) for r in runs])),
            "unassigned": round(float(np.mean([(r < 0).mean() for r in runs])), 4),
            "ari_stability": round(ari_stability(runs), 4),
            "ari_vs_first": round(float(adjusted_rand_score(reference, first)), 4),
            "purity": round(purity(first, truth), 4) if truth is not None else math.nan,
            "npmi": round(npmi_coherence(terms, doc_tokens, npmi_top_n), 4),
            "seconds_per_run": round(float(np.mean(secs)), 1), "error": ""})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ report
def _table(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty:
        return ["(not run)"]
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if (isinstance(v, float) and math.isnan(v)) else str(v) for v in r) + " |")
    return out


def render_report(emb_df: pd.DataFrame | None, clu_df: pd.DataFrame | None, meta: dict) -> str:
    lines = ["# Bake-off report", "", *[f"- {k}: {v}" for k, v in meta.items()], "",
             "## Embedding models", "", *_table(emb_df), "", "## Clustering", "", *_table(clu_df), ""]
    if emb_df is not None and "journal_knn_acc" in emb_df and emb_df["journal_knn_acc"].notna().any():
        best = emb_df.sort_values("journal_knn_acc", ascending=False).iloc[0]
        lines.append(f"Best embedding by journal kNN accuracy: **{best['candidate']}** ({best['journal_knn_acc']})")
    if clu_df is not None and "ari_stability" in clu_df and clu_df["ari_stability"].notna().any():
        ok = clu_df[clu_df["ari_stability"] >= 0.8]
        key = "purity" if ok["purity"].notna().any() else "npmi"
        if len(ok):
            best = ok.sort_values(key, ascending=False).iloc[0]
            lines.append(f"Best stable clustering (ARI ≥ 0.8) by {key}: **{best['algorithm']}** ({best[key]})")
        else:
            lines.append("No clustering algorithm reached ARI stability ≥ 0.8.")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ CLI glue
def candidate_fn(cfg: dict, cand: dict) -> EmbedFn:
    """Embedding function for one bakeoff.embedding_candidates entry (api/local go through the store)."""
    from atlas.embed import embed_texts, lite_embed

    if cand["provider"] == "lite":
        return lambda texts: lite_embed(texts, cfg["embedding"]["lite"], int(cfg["pipeline"]["seed"]))
    c2 = copy.deepcopy(cfg)
    c2["embedding"]["provider"] = cand["provider"]
    block = c2["embedding"][cand["provider"]]
    if cand["model"]:
        block["model"] = cand["model"]
    if cand["provider"] == "api":
        if cand["base_url"]:
            block["base_url"] = cand["base_url"]
        block["dimensions"] = cand["dimensions"]          # None = not sent (bge-m3) — never inherit the default 1024
        block["store_id"] = cand.get("store_id")          # None → the runner's "api|<model>|<dimensions>"
    return lambda texts: embed_texts(c2, texts)


def run_bakeoff(cfg: dict, kind: str, truth_path: str | Path | None = None) -> str:
    from atlas.checkpoints import load_aligned

    work = Path(cfg["pipeline"]["work_dir"])
    bcfg, seed = cfg["bakeoff"], int(cfg["pipeline"]["seed"])
    docs, all_emb = load_aligned(work)
    rng = np.random.default_rng(seed)
    pick = np.sort(rng.choice(len(docs), min(int(bcfg["sample"]), len(docs)), replace=False))
    sample = docs.iloc[pick].reset_index(drop=True)
    truth = None
    if truth_path:
        t = pd.read_csv(truth_path).set_index("article_id")["topic"]
        truth = sample["article_id"].map(t).fillna("?").astype(str).to_numpy()
    texts = sample["doc_text"].tolist()
    emb_df = clu_df = None
    meta = {"work_dir": str(work), "sample": len(sample), "k": bcfg["k"], "seeds": bcfg["seeds"]}
    if kind in ("embedding", "all"):
        cands = {c["name"]: candidate_fn(cfg, c) for c in bcfg["embedding_candidates"]} or {
            "lite (configured)": candidate_fn(cfg, {"provider": "lite"})}
        reference = None
        try:
            from atlas.openalex import load_reference

            ref, _ = load_reference(cfg)
            reference = ((ref["title"] + " . " + ref["abstract"]).tolist(), ref["subfield_id"].astype(str).tolist())
        except Exception as e:  # noqa: BLE001 — subfield accuracy is optional
            meta["subfield_reference"] = f"unavailable ({type(e).__name__})"
        emb_df = embedding_bakeoff(texts, sample["journal_name"].astype(str).to_numpy(), cands, int(bcfg["k"]),
                                   float(bcfg["holdout_frac"]), seed, truth, reference)
    if kind in ("clustering", "all"):
        emb = all_emb[pick]
        clu_df = clustering_bakeoff(emb, texts, cfg["clustering"], list(bcfg["algorithms"]),
                                    [int(s) for s in bcfg["seeds"]], truth, int(bcfg["npmi_top_n"]))
    return render_report(emb_df, clu_df, meta)
```

- [ ] **Step 4: CLI** — append to `pipeline/atlas/cli.py`:

```python


@app.command("bakeoff")
def bakeoff_cmd(
    config: Path = typer.Option(None, "--config", "-c", help="config.yaml (built-in defaults if omitted)"),
    kind: str = typer.Option("all", help="embedding | clustering | all"),
    truth: Path = typer.Option(None, help="CSV with article_id,topic (synthetic corpus _truth.csv)"),
    out: Path = typer.Option(None, help="write the Markdown report here"),
) -> None:
    """Compare embedding models and clustering algorithms on the current work_dir (Markdown report)."""
    from atlas.bakeoff import run_bakeoff
    from atlas.config import load_config

    if kind not in ("embedding", "clustering", "all"):
        raise typer.BadParameter("kind must be embedding, clustering or all")
    md = run_bakeoff(load_config(config), kind, truth)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
    typer.echo(md)
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_bakeoff.py -q && uv run pytest -q`
Expected: all pass (with `--extra leiden --extra fast` installed the optional rows are real numbers; without them they are error rows).

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/bakeoff.py pipeline/atlas/cli.py pipeline/tests/test_bakeoff.py
git commit -m "feat(bakeoff): embedding and clustering bake-offs (kNN accuracy, purity, ARI stability, NPMI) with a Markdown report

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 20: Streaming ingest — parse the corpus in batches straight into tables (on top of the fix wave's per-file errors and error ceiling)

At 250K–500K files the P0 reader holds every parsed record (with its reference list) as Python dicts before building tables — several GB on a laptop. The batched reader parses `input.batch_files` files at a time with the fix wave's per-file wrapper (`_parse_file_safe`: a file that cannot be read or parsed becomes a `{path, error: "Type: message"}` row, `decode_replaced` is flagged by `_parse_file`), turns each batch into DataFrames immediately and concatenates at the end; the one corpus-level pass (an article without a year takes the median year of its issue) moves to the article table, so batch boundaries cannot change the result. Everything after parsing in `ingest()` is the fix wave's code, unchanged: one `01_ingest_errors` writer, then `check_error_ceiling` (`input.max_error_ratio`; all files failing is always an error), dedup with the one-sided DOI rule, the warning lines. `read_thaijo_corpus` stays for `atlas profile`.

**Files:**
- Modify: `pipeline/atlas/ingest.py`, `pipeline/atlas/config.py`, `pipeline/config.example.yaml`, `pipeline/tests/test_ingest.py` (append)

**Interfaces:**
- Consumes (fix wave, at `0426434`): `_parse_file_safe(path) -> (record | None, error | None)`, `POOL_MIN_FILES`, `ERROR_COLUMNS`, `check_error_ceiling(n_files, errors, max_ratio, errors_path)`, `records_to_tables`; P0 `ARTICLE_COLUMNS`/`AUTHOR_COLUMNS`/`REFERENCE_COLUMNS`.
- Produces: `ingest.fill_years_from_issue_df(articles) -> DataFrame`, `ingest.read_thaijo_tables(root, pattern="**/*.md", workers=1, batch_files=20_000) -> (articles, authors, references, errors)` (each file gives one article or one error, so `n_files = len(articles) + len(errors)` exactly as before); `ingest()` uses it for `thaijo_md` input; config `input.batch_files`.

- [ ] **Step 1: Write the failing tests** — append to `pipeline/tests/test_ingest.py` (the fix wave's tests already cover a parser exception, an unreadable path in the process pool, `decode_replaced` and the error ceiling through `ingest()`, which now runs the batched reader — they are the regression suite for this task):

```python


def test_batched_parsing_gives_the_p0_tables_and_errors(thaijo_dir, tmp_path):
    from atlas.ingest import read_thaijo_corpus, read_thaijo_tables, records_to_tables

    src = tmp_path / "in"
    shutil.copytree(thaijo_dir, src)
    (src / "zz_bad.md").mkdir()                                # matches the glob, cannot be read as a file
    small = read_thaijo_tables(src, batch_files=3)
    whole = read_thaijo_tables(src, batch_files=10_000)
    for a, b in zip(small[:3], whole[:3]):
        pd.testing.assert_frame_equal(a, b, check_dtype=False)     # concat may widen string → object
    recs, errors = read_thaijo_corpus(src)                     # the P0 reader (atlas profile) agrees
    for a, b in zip(whole[:3], records_to_tables(recs)):
        pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True), check_dtype=False)
    assert len(small[0]) == 11 and small[3] == whole[3] == errors and errors[0]["path"].endswith("zz_bad.md")


def test_issue_year_fill_runs_on_the_whole_article_table():
    from atlas.ingest import fill_years_from_issue_df

    df = pd.DataFrame({"issue_url": ["i1", "i1", "i1", "i2", ""], "year": [2020, None, 2021, None, None],
                       "year_source": ["meta", "", "meta", "", ""]})
    out = fill_years_from_issue_df(df)
    assert out["year"].tolist()[:3] == [2020, 2020, 2021] and out.loc[1, "year_source"] == "issue_median"
    assert pd.isna(out.loc[3, "year"]) and pd.isna(out.loc[4, "year"])     # no dated sibling / no issue
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_ingest.py -q`
Expected: FAIL — `ImportError: cannot import name 'read_thaijo_tables'`.

- [ ] **Step 3: Batched reader** — in `pipeline/atlas/ingest.py`, after `records_to_tables` (it reuses the fix wave's `_parse_file_safe` and `POOL_MIN_FILES`; nothing above this point changes):

Before
```python
# ------------------------------------------------------------------ table input
```
insert
```python
def fill_years_from_issue_df(articles: pd.DataFrame) -> pd.DataFrame:
    """Corpus-level pass on the article table: a missing year takes the median year of its issue
    (same rule as sources.thaijo_md.fill_years_from_issue, independent of how the corpus was batched)."""
    y = pd.to_numeric(articles["year"], errors="coerce")
    issue = articles["issue_url"].fillna("").astype(str)
    has = y.notna() & (issue != "")
    med = y[has].groupby(issue[has]).median()
    fill = y.isna() & issue.isin(med.index)
    out = articles.copy()
    out["year"] = y.astype("Int64")
    out.loc[fill, "year"] = issue[fill].map(med).astype(int).to_numpy()
    out.loc[fill, "year_source"] = "issue_median"
    return out


def _parse_batch(files: list[str], workers: int) -> tuple[list[dict], list[dict]]:
    """One batch through the fix wave's per-file wrapper (records, {path, error} rows)."""
    if workers > 1 and len(files) > POOL_MIN_FILES:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            out = list(ex.map(_parse_file_safe, files, chunksize=max(1, min(256, len(files) // workers))))
    else:
        out = [_parse_file_safe(f) for f in files]
    return [r for r, _ in out if r is not None], [e for _, e in out if e is not None]


def read_thaijo_tables(root: str | Path, pattern: str = "**/*.md", workers: int = 1,
                       batch_files: int = 20_000) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict]]:
    """Parse the corpus batch by batch straight into tables → (articles, authors, references, errors).
    Same files, records and errors as read_thaijo_corpus, without holding every record in memory."""
    files = sorted(str(p) for p in Path(root).glob(pattern) if not p.name.startswith("_"))
    parts, errors = [], []
    for i in tqdm(range(0, len(files), batch_files), desc="parse batches", disable=len(files) <= batch_files):
        recs, errs = _parse_batch(files[i:i + batch_files], workers)
        parts.append(records_to_tables(recs))
        errors += errs
        del recs
    if not parts:
        parts = [records_to_tables([])]
    arts, auths, refs = (pd.concat([p[k] for p in parts], ignore_index=True) for k in range(3))
    return fill_years_from_issue_df(arts), auths, refs, errors


```

- [ ] **Step 4: Use it in the step** — only the reading lines of `ingest()` change; `n_files`, the single `01_ingest_errors` writer, `check_error_ceiling` and the warnings below stay as the fix wave wrote them:

Replace
```python
        recs, errors = read_thaijo_corpus(icfg["path"], icfg["glob"], int(icfg["workers"]))
        n_files = len(recs) + len(errors)
        articles, authors, refs = records_to_tables(recs)
```
with
```python
        articles, authors, refs, errors = read_thaijo_tables(icfg["path"], icfg["glob"], int(icfg["workers"]),
                                                             int(icfg["batch_files"]))
        n_files = len(articles) + len(errors)            # one article or one error per file
```

- [ ] **Step 5: Config**

After
```python
    workers: int = Field(4, ge=1)
```
insert
```python
    batch_files: int = Field(20_000, ge=1)
```
After
```yaml
  workers: 4                  # จำนวน process ตอน parse (ใช้เมื่อไฟล์ > 2,000)
```
insert
```yaml
  batch_files: 20000          # parse ทีละกี่ไฟล์แล้วแปลงเป็นตารางทันที (คุม RAM ที่ 500K ไฟล์)
```

- [ ] **Step 6: Run tests**

Run: `uv run ruff check . && uv run pytest tests/test_ingest.py tests/test_thaijo_md.py tests/test_profile.py -q && uv run pytest -q`
Expected: all pass (the fix wave's F11 and error-ceiling tests included).

- [ ] **Step 7: Commit**

```bash
git add pipeline/atlas/ingest.py pipeline/atlas/config.py pipeline/config.example.yaml pipeline/tests/test_ingest.py
git commit -m "feat(ingest): batched parsing straight into tables (bounded memory at 500K files) on the per-file error path; issue-year fill on the article table

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 21: P1 acceptance — two synthetic quarters end to end (slow) + `synth id_offset` + CI extras

The acceptance run generates the 20K synthetic corpus (Q1), adds 2K late-arriving articles (Q2) and **re-clusters Q2 from scratch** (`topics.mode: fit` — the hard case for stable ids), then checks every P1 verification item of the spec. Prototype numbers (Windows, ~6 min): ids kept 100 %, ARI 1.0, taxonomy 100 %, planted EMERGING / WATCH / HOT / DECLINING recovered, `chatgpt` emerging and `buddhism` journal-driven, median map shift 30 px, release validates with 0 warnings, pooled 80 % coverage 0.79–0.81.

**Files:**
- Modify: `pipeline/atlas/synth.py` (`generate(..., id_offset=0)`), `pipeline/tests/test_synth.py` (append), `.github/workflows/ci.yml`
- Create: `pipeline/tests/test_e2e_p1.py`

**Interfaces:**
- Consumes: everything in Tasks 1–20; `configs/ci.yaml` (lite embeddings, `labeling.provider: off`, `narrative.provider` default `template` — CI never calls an LLM or OpenAlex).
- Produces: `synth.generate(out_dir, n, seed, id_offset=0)` (article ids and DOIs start at `id_offset`, so a late batch never collides); the slow test `test_p1_two_quarters_on_the_synthetic_corpus`; CI installs the `leiden` and `fast` extras so their tests run.

- [ ] **Step 1: Write the failing tests** — create `pipeline/tests/test_e2e_p1.py`:

```python
"""P1 acceptance (slow): two synthetic "quarters" through the whole pipeline.

Q1 = 20K-article synthetic corpus; Q2 = Q1 + 2K late-arriving articles, re-clustered from scratch
(topics.mode: fit — the hard case for stable ids). Checks the spec's P1 verification items:
stable ids (≥ 90% kept, ARI ≥ 0.8), forecast 80% intervals cover 70–90% in an honest hold-out,
shown forecasts have MASE < 1, taxonomy and emerging keywords recover what was planted, the map
stays put, narratives exist for the planted signals, and the contract v2 release validates (diffs
cleanly against Q1) and lands on a static site with latest.json and the offline HTML.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import adjusted_rand_score

from atlas.config import load_config
from atlas.forecast import rolling_coverage
from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run
from atlas.publish import publish
from atlas.synth import SUBFIELDS, generate, reference_works
from atlas.validate import validate_release

PIPELINE = Path(__file__).resolve().parent.parent


def _cfg(root: Path, release: str, corpus: Path, ref: Path, mode: str) -> dict:
    cfg = load_config(PIPELINE / "configs" / "ci.yaml")
    cfg["pipeline"].update(work_dir=str(root / f"work_{release}"), output_dir=str(root / "out"),
                           state_dir=str(root / "state"), release=release)
    cfg["input"]["path"] = str(corpus)
    cfg["taxonomy"]["reference_path"] = str(ref)
    cfg["topics"]["mode"] = mode
    return cfg


@pytest.mark.slow
def test_p1_two_quarters_on_the_synthetic_corpus(tmp_path):
    corpus = tmp_path / "corpus"
    generate(corpus / "base", n=20_000, seed=7)
    ref = tmp_path / "reference.jsonl"
    ref.write_text("\n".join(json.dumps(w) for w in reference_works()), encoding="utf-8")
    run(_cfg(tmp_path, "2026Q1", corpus / "base", ref, "auto"), STEPS)
    generate(corpus / "extra", n=2_000, seed=8, id_offset=1_000_000)
    cfg2 = _cfg(tmp_path, "2026Q2", corpus, ref, "fit")
    run(cfg2, STEPS)
    w1, w2 = tmp_path / "work_2026Q1", tmp_path / "work_2026Q2"

    # stable topic ids across a full refit
    meta = json.loads((w2 / "04_topics_meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "fit" and meta["kept_fraction"] >= 0.9
    both = read_table(w1 / "04_fine_topics.parquet").merge(read_table(w2 / "04_fine_topics.parquet"),
                                                         on="article_id", suffixes=("_1", "_2"))
    assert adjusted_rand_score(both["fine_topic_1"], both["fine_topic_2"]) >= 0.8

    # forecast: honest hold-out backtest (2-year horizon from 3 successive cut-off years, pooled)
    series = read_table(w2 / "06_series.parquet")
    m6 = json.loads((w2 / "06_meta.json").read_text(encoding="utf-8"))
    totals = pd.Series({int(y): int(n) for y, n in m6["totals"].items()}).sort_index()
    cov = rolling_coverage(series, totals, int(m6["last_complete_year"]), cfg2["forecast"], n_cuts=3)
    assert 0.70 <= cov["coverage80"] <= 0.90, cov
    fc = read_table(w2 / "08_forecasts.parquet")
    assert fc["show"].any() and (fc.loc[fc["show"], "mase"] < 1).all()

    # taxonomy + planted signals
    truth = pd.concat([pd.read_csv(corpus / "base" / "_truth.csv"), pd.read_csv(corpus / "extra" / "_truth.csv")])
    tt = read_table(w2 / "04_fine_topics.parquet").merge(truth, on="article_id")
    dominant = tt[tt["fine_topic"] >= 0].groupby("fine_topic")["topic"].agg(lambda s: s.value_counts().index[0])
    tax = read_table(w2 / "10_taxonomy.parquet").set_index("topic_id")
    hits = [tax.loc[t, "subfield_id"] == SUBFIELDS[k][0] for t, k in dominant.items()]
    assert np.mean(hits) >= 0.9
    em = read_table(w2 / "07_emerging.parquet").set_index("topic_id")
    role_topic = tt[tt["fine_topic"] >= 0].groupby("role")["fine_topic"].agg(lambda s: s.value_counts().index[0])
    assert em.loc[role_topic["emerging"], "status"] == "EMERGING"
    assert em.loc[role_topic["confound"], "status"] == "WATCH"
    assert em.loc[role_topic["hot"], "status"] == "HOT" and em.loc[role_topic["declining"], "status"] == "DECLINING"
    kw = read_table(w2 / "07_keywords.parquet").set_index("key")
    assert bool(kw.loc["chatgpt", "emerging"]) and bool(kw.loc["buddhism", "journal_driven"])

    # the map stays put
    def topic_xy(work):
        lay = read_table(work / "09_layout.parquet")
        return lay[lay["kind"] == "topic"].set_index("id")[["x", "y"]]

    p1, p2 = topic_xy(w1), topic_xy(w2)
    common = p1.index.intersection(p2.index)
    moved = np.hypot(*(p2.loc[common].to_numpy() - p1.loc[common].to_numpy()).T)
    assert np.median(moved) < 0.05 * cfg2["layout"]["view_w"]

    # narratives (template provider — no LLM in CI) for the planted signals
    narr = read_table(w2 / "11_narratives.parquet").set_index("topic_id")
    assert role_topic["emerging"] in narr.index and narr.loc[role_topic["declining"], "source"] == "template"
    assert json.loads((w2 / "11_brief.json").read_text(encoding="utf-8"))["brief"]["source"] == "template"

    # contract v2 release validates, diffs cleanly against Q1 and lands on a static site
    rep = validate_release(tmp_path / "out" / "data" / "2026Q2", None, cfg2["validation"])
    assert not rep.errors, rep.errors
    assert rep.stats["kept_ids"] >= 0.9 and rep.previous_dir is not None
    site = tmp_path / "site"
    site.mkdir()
    (site / "offline-template.html").write_text('<script type="application/json" id="atlas-data"></script>',
                                                encoding="utf-8")
    r = publish(cfg2, site=site, allow_warnings=True, tarball=True)
    assert json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q2"
    assert Path(r["offline_html"]).stat().st_size > 100_000 and Path(r["tarball"]).stat().st_size > 0
```

and append to `pipeline/tests/test_synth.py`:

```python


def test_id_offset_makes_a_disjoint_late_batch_with_unique_dois(tmp_path):
    from atlas.ingest import read_thaijo_tables

    base = generate(tmp_path / "base", n=600, seed=3)
    extra = generate(tmp_path / "extra", n=200, seed=8, id_offset=1_000_000)
    assert not set(base["article_id"]) & set(extra["article_id"])
    arts = read_thaijo_tables(tmp_path)[0].drop_duplicates("article_id")
    dois = arts.loc[arts["doi"] != "", "doi"]
    assert dois.is_unique                      # DOI dedup in ingest must never merge two synthetic articles
    assert len(arts) == len(base) + len(extra)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_synth.py -q`
Expected: FAIL — `TypeError: generate() got an unexpected keyword argument 'id_offset'`.

- [ ] **Step 3: `id_offset` in `pipeline/atlas/synth.py`**

Replace
```python
def generate(out_dir: str | Path, n: int = 20_000, seed: int = 7) -> pd.DataFrame:
```
with
```python
def generate(out_dir: str | Path, n: int = 20_000, seed: int = 7, id_offset: int = 0) -> pd.DataFrame:
```
Replace
```python
    truth, idx = [], 0
```
with
```python
    truth, idx = [], id_offset
```

- [ ] **Step 4: CI** — `.github/workflows/ci.yml` (both pipeline jobs install the optional extras; the slow job runs P0's and P1's acceptance tests):

Replace
```yaml
      - run: uv sync --locked
      - run: uv run ruff check .
```
with
```yaml
      - run: uv sync --locked --extra leiden --extra fast
      - run: uv run ruff check .
```
Replace
```yaml
    timeout-minutes: 30
```
with
```yaml
    timeout-minutes: 45
```
Replace
```yaml
      - run: uv sync --locked
      - name: synthetic corpus recovers planted EMERGING / WATCH / HOT / DECLINING
        run: uv run pytest -m slow -q
```
with
```yaml
      - run: uv sync --locked --extra leiden --extra fast
      - name: synthetic corpus — P0 planted signals + P1 two-quarter acceptance
        run: uv run pytest -m slow -q
```

- [ ] **Step 5: Run tests**

Run: `uv run ruff check . && uv run pytest -q && uv run pytest -m slow -q`
Expected: all pass; the slow suite takes ~12 min (P0 e2e ~5 min, P1 e2e ~6 min, the 11-file UMAP regression ~30 s). If an acceptance threshold fails, do **not** loosen it or change the synthetic generator: report the printed numbers to the controller.

- [ ] **Step 6: Commit**

```bash
git add pipeline/atlas/synth.py pipeline/tests/test_synth.py pipeline/tests/test_e2e_p1.py .github/workflows/ci.yml
git commit -m "test(p1): two-quarter synthetic acceptance (stable ids, coverage, taxonomy, keywords, map, narratives, release → site); CI installs leiden + fast

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---


### Task 22: Docs sync — architecture, data spec, operations (LLM, review, publish), roadmap, CLAUDE.md, READMEs

Docs are part of the definition of done (CLAUDE.md §8 sends every future contributor to them first). Every anchor below was checked against `0426434` (P0 Task 19's §1A embedding runbook and env-var lines, the fix wave's v3 wording) plus Tasks 1–21; P0's own sections stay as they are. P1's LLM key is `ATLAS_LLM_API_KEY` (Task 3) — P0's labeling key `ATLAS_API_KEY` goes away with the P0 label API (Task 6), so every line naming it is rewritten here. Emerging stays at definition v3 (user decision 2026-10-19), so no `definition_version` line changes.

**Files:**
- Modify: `docs/ARCHITECTURE.md`, `docs/DATA_SPEC.md`, `docs/OPERATIONS.md`, `docs/ROADMAP.md`, `CLAUDE.md`, `pipeline/README.md`, `README.md`

**Interfaces:** documentation only — every command, file and key named here exists after Tasks 1–21.

- [ ] **Step 1: `docs/ARCHITECTURE.md` — the v2 data flow**

Replace the body of the section `## 2. การไหลของข้อมูล (data flow)` (everything up to the next heading of the same or a higher level; keep the heading) with
````markdown

```
corpus/*.md (ThaiJO scrape)            ← ตรวจก่อนด้วย: atlas profile
        │
        ▼
[ingest]     parse .md ทีละชุด (input.batch_files) → ตารางทันที · ปี: Published→DOI→median issue · dedup
        │  → work/01_articles · 01_authors (+org_key) · 01_references · 01_ingest_errors (ไฟล์ที่อ่านไม่ได้)
        ▼
[preprocess] doc_text = title + keywords + abstract (≤ 6000 ตัวอักษร)                      → work/02_docs
        ▼
[embed]      api (runner ของ P0: retry ไม่จำกัด, journal, resume — `atlas embed`) | local (BGE-M3) | lite (CI)
             เวกเตอร์ถาวรใน state/embeddings/<store_id>     → work/03_embeddings.npy + 03_meta.json (docs_fingerprint)
        ▼
[cluster]    fit (UMAP→HDBSCAN | Leiden) หรือ assign เข้าหัวข้อรอบก่อน (topics.mode) → ID ถาวร T000123 + lineage
        │  → work/04_* · state/releases/<release>/topics/{assignments,registry,lineage}
        ▼
[taxonomy]   kNN vote กับงานอ้างอิงไทยใน OpenAlex → subfield → field = กลุ่มบนแผนที่ (fallback: agglomerative)
        │  → work/10_taxonomy (+ meta: ความแม่นยำ held-out)
        ▼
[label]      LLM runner (cache/journal state/llm_cache, งบ, หยุด/ทำต่อ, lock/status ของ P0) หรือ off → ชื่อที่บรรณาธิการแก้ชนะเสมอ
        │  + คู่หัวข้อที่อาจซ้ำ (ข้อเสนอ ไม่รวมเอง)  → work/05_labels · 05_labels_meta.json · 05_merge_suggestions
        ▼
[series]     topic × ปี + ปีสมบูรณ์ล่าสุด (กฎ v3: backfill guard) + ตารางปีหลังจากนั้น (ใช้ทำ nowcast เท่านั้น)
        │  → work/06_series · 06_months · 06_partial_year · 06_meta.json · ตารางวารสาร/สถาบัน
        ▼
[emerging]   Emerging v3 (docs/EMERGING_SPEC.md)                                          → work/07_emerging
[keywords]   emerging keywords ระดับคำ (Carley/Porter)                                    → work/07_keywords
        ▼
[forecast]   share × ยอดรวม: naive / drift / NB GLM / damped ETS · rolling-origin CV · skill gate · conformal 80/95 · nowcast
        │  → work/08_forecasts · 08_forecast_meta.json
        ▼
[narrate]    คำอธิบายหัวข้อ + บทสรุปผู้บริหาร (ตัวเลขจาก pipeline เท่านั้น ตรวจซ้ำ; ไม่ผ่าน = ประโยคแม่แบบ)
        │  → work/11_narratives · 11_brief.json
        ▼
[layout]     แผนที่นิ่งข้ามรอบ (UMAP เริ่มจากรอบก่อน + Procrustes + anchor) + galaxy บทความ → work/09_*
        ▼
[export]     output/atlas_data.json (schema 1.1 — เว็บปัจจุบัน) + output/data/<release>/ (contract v2) + latest.json
        ▼
atlas validate  →  atlas publish --site <โฟลเดอร์เว็บ>  →  data/<release>/ + data/latest.json + atlas-offline.html
เว็บ v2 อ่าน data/latest.json แบบ path สัมพัทธ์จาก BASE_URL — ไม่เรียก API ตอน runtime; อัปเดตรายไตรมาส = คัดลอกโฟลเดอร์ data
```

- งาน LLM ทั้งหมดเป็นระดับหัวข้อ (ชื่อ คู่ซ้ำ คำอธิบาย บทสรุป) ผ่าน adapter เดียวแบบ OpenAI-compatible (`atlas/llm.py`) บนแกน HTTP ร่วมกับ embedding (`atlas/api_http.py`) — ไม่มี SDK ของผู้ให้บริการรายใด
- ข้อมูลที่ต้องอยู่ข้ามรอบอยู่ใน `state_dir` เท่านั้น: embeddings, llm_cache, releases/<release>/ (ID หัวข้อ, ตำแหน่งบนแผนที่), openalex/
- รันซ้ำ step ใดของรอบเดิม = ผลเหมือนเดิม (อ่านรอบ *ก่อน* เสมอ เขียนทับเฉพาะโฟลเดอร์ของรอบนี้)

````

- [ ] **Step 2: `docs/DATA_SPEC.md` — new checkpoints, state and contract v2**

Replace
```markdown
| `05_labels` | label | level, topic_id, name_th, name_en, description, keywords, cache_key (`cache_key` = sha256(model + prompt) 16 ตัวแรก; `"fallback"` เมื่อ `label.provider: "off"`) |
```
with
```markdown
| `05_labels` | label | level, topic_id, name_th, name_en, description, keywords, cache_key (key ของ LLM cache หรือ `"fallback"`), label_source (`llm` \| `keywords` \| `override`) |
| `05_labels_meta.json` | label | provider, model_id, topics, from_cache, generated, repaired, fallback, overrides, unknown_overrides, cost_usd |
| `05_merge_suggestions`, `05_merge_meta.json` | label | topic_a, topic_b, similarity, same_topic (True/False/None), reason, source · สถิติ LLM งาน merge |
```
After
```markdown
| `09_layout`, `09_edges` | layout | id, kind, x, y, r, parent · s, t, w |
```
insert
```markdown
| `04_lineage`, `04_topics_meta.json` | cluster | event (new/continue/split/merge/retired), topic_id, parents · release, previous_release, mode (fit/assign), kept_fraction, events |
| `06_months`, `06_partial_year` | series | year, month, count (วันที่ตีพิมพ์ที่ตรงกับปี) · topic_id, year, count ของปีหลัง last_complete_year (ใช้ทำ nowcast) |
| `06_meta.json` (เพิ่ม) | series | partial_totals (ยอดบทความของปีหลัง last_complete_year), completeness {method: median (backfill guard v3) \| configured} |
| `07_keywords` | keywords | term, key, count_recent, count_baseline, share_ratio, no_baseline, growth(_lo/_hi), n_active_years, n_orgs_R, n_journals_R, new_journal_share, journal_driven, topic_id, emerging |
| `08_forecasts` (v2), `08_forecast_meta.json` | forecast | + fc_lo80/hi80/lo95/hi95, nowcast_* · total_model, conformal, n_calibration, nowcast |
| `09_galaxy` | layout | article_id, topic_id, gx, gy |
| `10_taxonomy`, `10_taxonomy_meta.json` | taxonomy | topic_id, group_id, group_en/th, subfield_id/en, vote_share, cross_field, source · version, holdout accuracy |
| `11_narratives`, `11_brief.json` | narrate | topic_id, status, th, en, source (llm\|template) · {brief, llm} |
```
Replace
```markdown
| `state/label_cache.parquet` | label | cache_key → ชื่อหัวข้อ |
```
with
```markdown
| `state/llm_cache/<task>.jsonl` | label, narrate | cache + journal ของทุก call LLM: key = sha256(model + prompt_version + prompt) · output (null = บันทึกค่าใช้จ่ายของ call ที่ใช้ fallback) · cost_usd · release |
| `state/llm_cache/progress.json`, `.lock`, `run.lock`, `stop.flag`, `run.log` | label, narrate | ไฟล์งานแบบเดียวกับ embedding store (P0 `atlas.jobs`): สถานะ (`atlas status`, kind `llm`), OS lock กันรันซ้อน (+ ข้อมูล PID), คำขอหยุด (`atlas llm-stop`), log ของ `atlas llm --background` |
| `state/releases/index.json`, `state/releases/<release>/topics/`, `…/layout.parquet` | cluster, layout | ลำดับรอบ · assignments, registry (born/status/last_seen), lineage, model.json · ตำแหน่งหัวข้อ |
| `state/openalex/reference_*.parquet` + `.json` | taxonomy | งานอ้างอิง OpenAlex ที่ดึงแล้ว (ไม่ดึงซ้ำ) |
| `pipeline/registry/label_overrides.csv` (นอก state; ไม่เข้า git) | label | ชื่อที่บรรณาธิการแก้: topic_id (T000123), name_th, name_en, description, reviewer, reviewed_at, note |
```
Replace the body of the section `## 6. Data contract v2 (P1)` (everything up to the next heading of the same or a higher level; keep the heading) with
```markdown

`pipeline/atlas/schema/contract.py` → `web/src/data/contract.schema.json` → `web/src/data/contract.ts`
สร้างด้วย `uv run atlas schema` และ `npm run gen:types` (CI ตรวจ drift ทั้งสองขั้น)

รอบข้อมูลหนึ่งรอบ = `output/data/<release>/` (เช่น `2026Q4/`) — JSON แบบ strict (ไม่มี NaN/Infinity), สีเป็น token `cat-01…cat-12` ไม่ใช่ hex, ไม่มีบทคัดย่อและไม่มีข้อมูลระดับบุคคล

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `manifest.json` | `Manifest` | release, previous_release, definition_version, **ci_level** (ระดับของช่วง `*_lo/*_hi` ทุกตัว), as_of_year, trimmed_years, embedding_provider/model, taxonomy_version, n_orgs_unverified, ingest_errors, labels {provider, llm, keywords, overrides}, llm [{task, model, items, from_cache, generated, repaired, fallback, cost_usd}], files [{path, bytes, sha256}] |
| `overview.json` | `Overview` | KPI, จำนวนตามสถานะ, ยอดรายปี + พยากรณ์ยอดรวม, nowcast, lineage events, retired topics, data_quality (completeness), **brief** (headline + bullets, source llm/template) |
| `taxonomy.json` | `TaxonomyFile` | source (openalex/agglomerative), groups (F33 / G03, ชื่อ TH/EN, สี token, ตำแหน่ง hub), subfields |
| `topics.json` | `TopicsFile` | หัวข้อ: id T000123, group, ชื่อ, label_source, ขนาด, ตำแหน่ง, status, score, metrics, forecast, lineage, subfield, cross_field, nowcast |
| `topics/<id>.json` | `TopicDetail` | บทความตัวแทน (ชื่อเรื่อง + ลิงก์ ThaiJO + พิกัด galaxy), วารสาร/สถาบันหลัก, คำสำคัญ, เพื่อนบ้าน, **narrative** |
| `series.json`, `edges.json`, `keywords.json` | `SeriesFile`, `EdgesFile`, `KeywordsFile` | ยอดรายปีต่อหัวข้อ · เส้นเชื่อม · emerging keywords |
| `output/data/latest.json` | `Latest` | {release, path: "<release>/manifest.json", schema_version, generated_at} |

- `metrics.share_ratio` เป็น **null** และ `no_baseline: true` เมื่อไม่มีบทความในช่วงฐาน (เว็บแสดง "ใหม่ — ไม่มีฐานเปรียบเทียบ") — เช่นเดียวกับ keyword
- `metrics.low_data_reason`: `few_articles` (count_recent < `min_articles_recent`) หรือ `not_estimable` (ประมาณอัตราโตไม่ได้) เมื่อ status = LOW_DATA
- `atlas validate` ตรวจ integrity (sha256) · schema · ความสอดคล้อง · diff กับรอบก่อน · fallback ของ LLM; `atlas publish --site <dir>` วาง `data/<release>/` + `data/latest.json` + `atlas-offline.html` (ข้อมูลฝังใน `<script type="application/json" id="atlas-data">` ของ `offline-template.html` ที่ web build สร้าง)

```

- [ ] **Step 3: `docs/OPERATIONS.md` — runbook steps and new sections**

After
```markdown
(`python -m atlas.pipeline` ยังใช้ได้เป็น alias ของ `atlas run` แต่เอกสารนี้ใช้ `atlas` CLI)
```
insert
```markdown

ถ้าใช้ LLM (`labeling.provider: llm` / `narrative.provider: llm`): ก่อนรันจริง `uv run atlas llm -c config.yaml --check` (ปลายทางตอบ JSON + ภาษาไทยไม่เพี้ยน) และ `--dry-run` (จำนวน call, token, ค่าใช้จ่ายโดยประมาณ, งบที่เหลือ) — ดูหัวข้อ 6
หลังรัน: `uv run atlas validate -c config.yaml` ต้องได้ exit 0 (1 = มีคำเตือน อ่านก่อนเผยแพร่, 2 = ห้ามเผยแพร่)
```
Replace the body of the section `### ขั้น 3 — นำเข้าเว็บ` (everything up to the next heading of the same or a higher level; keep the heading) with
````markdown

```bash
cd pipeline
uv run atlas validate -c config.yaml                         # 0 = ผ่าน
uv run atlas publish  -c config.yaml --site ../web/dist      # วาง data/<release>/ + data/latest.json + atlas-offline.html
```

- เว็บ v2 อ่าน `data/latest.json` ตอนเปิดหน้า → **ไม่ต้อง build เว็บใหม่ทุกไตรมาส** แค่คัดลอกโฟลเดอร์ `data/` ใหม่ขึ้น host (รอบเก่ายังอยู่ใน `data/` ให้เทียบได้)
- `atlas-offline.html` = เว็บทั้งหน้าในไฟล์เดียว (ส่งอีเมล/เปิดโดยไม่ต่อเน็ตได้) — สร้างด้วย Python จาก `offline-template.html` ของ web build; ถ้าโฟลเดอร์เว็บยังไม่มีไฟล์นี้ publish จะเตือนแล้วข้ามไป
- ต้องการไฟล์แนบ GitHub Release ด้วย: เติม `--tarball` (ได้ tar.gz ที่ทำซ้ำได้ + sha256 + release notes และคำสั่ง `gh release create` ให้คนรันเอง — โปรแกรมไม่อัปโหลดเอง)
- เว็บปัจจุบัน (schema 1.1) ยังใช้ `bash scripts/import_atlas.sh` ได้จนกว่าเว็บ v2 จะขึ้น

````
````markdown

## 6. LLM ผ่าน API (ชื่อหัวข้อ · คู่ที่อาจซ้ำ · คำอธิบาย · บทสรุปผู้บริหาร)

ทุกงานใช้ปลายทางแบบ OpenAI-compatible (`POST {base_url}/chat/completions`) เช่น OpenRouter, Typhoon, DeepInfra หรือ vLLM/LiteLLM ขององค์กร — ตั้งใน `config.yaml → llm.endpoints` และเลือกโมเดลต่องานใน `llm.tasks.{label, merge, narrative, brief}`

```powershell
$env:ATLAS_LLM_API_KEY = "sk-..."        # หรือ setx ATLAS_LLM_API_KEY "sk-..." แล้วเปิดหน้าต่างใหม่ (bash: export ...)
uv run atlas llm -c config.yaml --check  # 1 คำขอเล็กต่อโมเดล: ตอบได้ไหม, เป็น JSON ไหม, ภาษาไทยครบไหม
uv run atlas llm -c config.yaml --dry-run   # ต่องาน: กี่ call, มีใน cache กี่ตัว, token ขาเข้า, ค่าใช้จ่ายสูงสุด, งบที่ใช้ไปในรอบนี้
uv run atlas llm -c config.yaml          # รัน step label + narrate (หรือรวมอยู่ใน atlas run อยู่แล้ว); --background = รันเบื้องหลัง ปิดหน้าต่างได้
uv run atlas status -c config.yaml       # ความคืบหน้า embedding + LLM
uv run atlas llm-stop -c config.yaml     # หยุดหลัง call ที่กำลังทำเสร็จ (exit 130) — รันคำสั่งเดิม = ทำต่อ
```

- **cache = journal**: ทุก call ที่เสร็จถูกบันทึกทันทีใน `state/llm_cache/<task>.jsonl` → ปิดหน้าต่าง/ไฟดับ/รันซ้ำ = จ่ายเฉพาะที่ยังไม่เสร็จ; รอบถัดไปจ่ายเฉพาะหัวข้อที่เนื้อหาเปลี่ยน
- **งบ**: `llm.budget_usd` ต่อรอบข้อมูล รวมทุกงาน (ต้องใส่ `price_per_mtok_in/out` ของปลายทาง) — call ถัดไปอาจเกินงบ = หยุดอย่างสะอาด (exit 130, step นั้นไม่เขียนผลครึ่ง ๆ กลาง ๆ); เพิ่มงบแล้วรันคำสั่งเดิม = ทำต่อจาก cache
- **server ล่ม/429**: ลองใหม่เองไม่จำกัด (backoff + Retry-After; ตั้ง `max_retries` = ครบแล้วหัวข้อนั้นใช้ fallback และถูกถามใหม่รอบหน้า) · **key/model/URL/โควตาผิด**: หยุดทันที exit 2 พร้อมบอกสิ่งที่ต้องแก้ · มีงาน LLM อื่นรันอยู่: exit 3 (ดู `atlas status`; lock เป็น OS lock แบบเดียวกับ embedding — process ตาย = ปล่อยเอง)
- JSON ผิดรูปแบบ → ขอให้แก้ ≤ 2 ครั้ง → fallback; คำอธิบายที่มีตัวเลข/ชื่อหัวข้อที่ไม่อยู่ในข้อมูล → เขียนใหม่ 1 ครั้ง → ประโยคแม่แบบ — จำนวน fallback ทุกงานอยู่ใน `manifest.json → llm` และ `atlas validate` เตือนก่อนเผยแพร่
- ครั้งแรกที่ใช้ P1: label cache ของ P0 (`state/label_cache.parquet`) ไม่ถูกใช้แล้ว → ทุกหัวข้อถูกตั้งชื่อใหม่ 1 ครั้ง แล้วลบไฟล์เก่าได้

## 7. คนตรวจชื่อหัวข้อ (ทุกรอบ ~50 หัวข้อ)

```bash
uv run atlas review export -c config.yaml         # → output/review/<release>_label_review.csv (เปิดใน Excel ได้ทันที)
#   บรรณาธิการกรอก name_th_fixed / name_en_fixed / reviewer / note ในแถวที่ต้องแก้
uv run atlas review import output/review/2026Q4_label_review.csv -c config.yaml   # → labeling.overrides_path
uv run atlas run -c config.yaml -s label -s narrate -s export                      # ใช้ชื่อใหม่ทันที
```

- ตัวอย่างที่ส่งตรวจ: ชื่อที่ LLM ทำไม่ได้ (ใช้คำสำคัญแทน) + คู่หัวข้อที่อาจซ้ำ มาก่อน แล้วสุ่มที่เหลือแบบทำซ้ำได้ (หัวข้อที่แก้แล้วไม่ถูกสุ่มซ้ำ)
- ไฟล์ overrides ผูกกับ ID ถาวร (T000123) → ชื่อที่แก้ชนะชื่อจาก LLM ทุกไตรมาส; ID ที่ถูกรวม/เลิกใช้ถูกแจ้งเตือนตอน label
- `pipeline/registry/` ไม่เข้า git (เป็นชื่อหัวข้อจากข้อมูลจริง) — สำรองไว้พร้อม `pipeline/state/`
- คู่ที่อาจซ้ำไม่ถูกรวมอัตโนมัติ: ถ้าเห็นด้วยว่าซ้ำ ให้ตั้งชื่อให้ชัดผ่าน overrides หรือรอ refit รายปีโดยลด `clustering.merge_similarity`

## 8. เลือกโมเดล embedding / อัลกอริทึมจัดกลุ่มด้วยตัวเลข (bake-off)

```bash
uv run atlas bakeoff -c config.yaml --kind all --out ../logs/bakeoff.md                 # ใช้ work_dir ปัจจุบัน
uv run atlas bakeoff -c configs/ci.yaml --truth .ci/synth/_truth.csv --out bakeoff.md   # corpus สังเคราะห์ (มีคำตอบ)
```

ใส่ผู้สมัครใน `bakeoff.embedding_candidates` (api ใช้ runner เดียวกับ embed — แยก store ต่อโมเดล จ่ายครั้งเดียว) — เลือก embedding ด้วย journal/subfield kNN accuracy และเลือกอัลกอริทึมที่ ARI stability ≥ 0.8 แล้วดู purity/NPMI
````

- [ ] **Step 4: `docs/ROADMAP.md`**

Before
```markdown
## งานแนะนำลำดับถัดไป (เรียงตาม value/effort)
```
insert
```markdown
## P1a — core analytics v2 (เสร็จ)

ID หัวข้อถาวร + lineage · กลุ่มตาม OpenAlex fields · Forecast v2 (share × ยอดรวม, conformal 80/95, nowcast ของปีที่ยังไม่ครบ) · emerging keywords · แผนที่นิ่งข้ามรอบ + galaxy · LLM ทุกงานผ่าน API (runner + งบ + review/overrides) · คำอธิบายและบทสรุปที่ตรวจตัวเลข · contract v2 + `atlas validate` + `atlas publish --site` · bake-off · ingest แบบเป็นชุด

ถัดไป: **P1b** เว็บ v2 (DESIGN.md + tokens แบบ hybrid ก่อน, แล้ว Overview / Atlas / Topic / Emerging) และ **P1c** หน้าเสริม + ช่องทางเผยแพร่ (PDF brief, Pages) — ดูแผน `docs/superpowers/plans/2026-10-19-p1a-core-analytics.md` ท้ายเอกสาร

```

- [ ] **Step 5: `CLAUDE.md`**

5a. §3 feature table:
After
```markdown
| + | Live dashboard (โหลด JSON runtime, fallback bundle) | `web/src/lib/loader.ts` | ✅ พร้อมใช้ |
```
insert
```markdown
| P1 | ID หัวข้อถาวร + lineage, OpenAlex taxonomy, Forecast v2, emerging keywords, แผนที่นิ่ง | `pipeline/atlas/{lineage,taxonomy,forecast,keywords,layout}.py` | ✅ pipeline (เว็บ v2 = P1b) |
| P1 | LLM ผ่าน API (label · merge · narrative · brief) + review/overrides | `pipeline/atlas/{llm,llm_runner,label,review,narrative}.py` | ✅ |
| P1 | Contract v2 release + validate + publish --site (+ offline HTML) | `pipeline/atlas/{export_v2,validate,publish}.py` | ✅ |
```
5b. §4 commands:
After
```markdown
uv run pytest -q && uv run pytest -m slow -q
```
insert
```markdown
uv run atlas llm -c config.yaml --check | --dry-run      # ปลายทาง LLM / ประมาณ token+ค่าใช้จ่าย; ไม่ใส่ flag = รัน label + narrate
uv run atlas review export -c config.yaml                # CSV ให้บรรณาธิการตรวจชื่อ → atlas review import <csv>
uv run atlas validate -c config.yaml                     # exit 0/1/2
uv run atlas publish -c config.yaml --site ../web/dist   # data/<release>/ + data/latest.json + atlas-offline.html
uv run atlas bakeoff -c config.yaml --kind all           # เทียบ embedding/clustering
```
Replace
```markdown
(key อยู่ใน env var เท่านั้น: `ATLAS_EMBED_API_KEY` สำหรับ embedding แบบ API, `ATLAS_API_KEY` สำหรับ labeling แบบ API — ขั้นตอน embed ครั้งใหญ่ดู `docs/OPERATIONS.md` §1A)
```
with
```markdown
(key อยู่ใน env var เท่านั้น: `ATLAS_EMBED_API_KEY` สำหรับ embedding แบบ API, `ATLAS_LLM_API_KEY` สำหรับ LLM (ชื่อหัวข้อ · คู่ซ้ำ · คำอธิบาย · บทสรุป) — ใช้ key เดียวกันได้; embed ครั้งใหญ่ดู `docs/OPERATIONS.md` §1A, LLM ดู §6)
```
5c. §5 contract (the v1.1 line keeps `meta.definition_version = 3`):
After
```markdown
- data contract v2 อยู่ที่ `pipeline/atlas/schema/contract.py` → ต้องสร้างใหม่พร้อมกัน: `uv run atlas schema` แล้ว `npm run gen:types` (ใน `web/`) — CI ตรวจ drift ทั้งสองขั้น
```
insert
```markdown
- contract v2 ถูกเขียนจริงแล้ว (P1): `output/data/<release>/*.json` + `output/data/latest.json` (รายละเอียดใน `docs/DATA_SPEC.md` §6) — ช่วงเชื่อมั่นใช้ชื่อ `*_lo/*_hi` เสมอ ระดับอยู่ใน `manifest.ci_level`; `share_ratio` เป็น null เมื่อ `no_baseline`
- เว็บ v2 (P1b) อ่าน `data/latest.json` แบบ path สัมพัทธ์จาก `BASE_URL` (ไม่เรียก API ตอน runtime) หรือข้อมูลที่ฝังใน `atlas-offline.html`
```
5d. §6 rules:
Replace
```markdown
- **DON'T** ใส่ API key ลงไฟล์ใด ๆ — ใช้ env var เสมอ (`ATLAS_EMBED_API_KEY` embedding, `ATLAS_API_KEY` labeling; ชื่ออยู่ใน `api_key_env` ของ config)
```
with
```markdown
- **DON'T** ใส่ API key ลงไฟล์ใด ๆ — ใช้ env var เสมอ (`ATLAS_EMBED_API_KEY` embedding, `ATLAS_LLM_API_KEY` LLM, `OPENALEX_API_KEY` ถ้ามี; ชื่ออยู่ใน `api_key_env` ของ config)
- **DO** เรียก LLM ผ่าน `atlas.llm_runner.run_job` เท่านั้น (cache, งบ, หยุด/ต่อ, repair, fallback; lock/progress/stop ใช้ `atlas.jobs` ของ P0 ตัวเดียวกับ embedding) — งาน LLM เป็นระดับหัวข้อ ไม่เรียกต่อบทความ
- **DO** ตัวเลขในข้อความที่ LLM เขียนต้องมาจาก pipeline และผ่าน `narrative.grounding_error` — ห้ามเผยแพร่ข้อความ LLM ที่ไม่ได้ตรวจ
```
Replace the body of the section `### LLM prompts` (everything up to the next heading of the same or a higher level; keep the heading) with
```markdown

- Prompts อยู่ใน `prompts/*.md` เท่านั้น (block ใต้ "Prompt (master)") — โค้ดอ่านไฟล์ตอนรัน ไม่มีสำเนาในโค้ด; แก้ prompt = แก้ไฟล์เดียวแล้วบอกใน commit
- cache key = sha256(model + `prompt_version` + prompt ที่เติมค่าแล้ว)[:16] ใน `state_dir/llm_cache/<task>.jsonl` — `prompt_version` คือ hash ของ template เท่านั้น (แก้หมายเหตุนอก block ไม่ทำให้จ่ายซ้ำ)
- ไฟล์: `topic_label.th` (label), `topic_merge.th` (merge), `topic_narrative.th` (narrative), `executive_brief.th` (brief)

```

- [ ] **Step 6: `pipeline/README.md` and `README.md`**

Before
```markdown
## สิ่งที่ตั้งใจไม่ทำ (และทำเพิ่มได้ภายหลัง)
```
insert
```markdown
## P1: steps, คำสั่ง และโมดูลที่เพิ่ม

Steps: `ingest → preprocess → embed → cluster → taxonomy → label → series → emerging → keywords → forecast → narrate → layout → export`

| โมดูล | หน้าที่ |
|---|---|
| `state.py`, `checkpoints.py` | ชื่อรอบ (YYYYQn) + state ต่อรอบ · ตรวจว่า 03_embeddings ตรงกับ 02_docs |
| `lineage.py` | ID หัวข้อถาวร T000123 + continue/split/merge/new/retired |
| `graph_cluster.py` | Leiden บน kNN graph (`--extra leiden`) |
| `openalex.py`, `taxonomy.py` | งานอ้างอิงไทยจาก OpenAlex → subfield/field ของแต่ละหัวข้อ |
| `keywords.py` | emerging keywords |
| `prompts.py`, `llm.py`, `llm_runner.py` | prompt จากไฟล์ · adapter OpenAI-compatible · runner (cache/งบ/หยุด/status) |
| `review.py`, `narrative.py` | คู่ที่อาจซ้ำ + ไฟล์ตรวจของบรรณาธิการ · คำอธิบายหัวข้อ + บทสรุปผู้บริหารที่ตรวจตัวเลข |
| `export_v2.py`, `validate.py`, `publish.py`, `bakeoff.py` | contract v2 · ตรวจรอบ · วางขึ้นเว็บ/offline/tarball · เทียบโมเดล |

คำสั่ง: `atlas llm` (`--check`, `--dry-run`), `atlas llm-stop`, `atlas review export|import`, `atlas validate`, `atlas publish --site [--tarball]`, `atlas bakeoff` — รายละเอียดใน `docs/OPERATIONS.md` §3, §6–§8

```
Before
```markdown
## ทีมที่พัฒนาต่อ
```
insert
```markdown
## P1 (analytics v2)

หัวข้อมี ID ถาวรข้ามไตรมาส, กลุ่มใหญ่ตาม OpenAlex fields, พยากรณ์พร้อมช่วง 80/95% และ nowcast ของปีที่ยังไม่ครบ, emerging keywords, คำอธิบายหัวข้อและบทสรุปผู้บริหารที่ตัวเลขทุกตัวมาจาก pipeline, และการเผยแพร่แบบ static (`atlas publish --site` → `data/latest.json` + ไฟล์ HTML เดี่ยวสำหรับ offline) — ดู `docs/OPERATIONS.md`

```

- [ ] **Step 7: Stale P0 lines** (the P0 labeling key `ATLAS_API_KEY` and the old label cache)

Replace
```markdown
(embedding store, label cache, centroids รอบก่อน)
```
with
```markdown
(embedding store, LLM cache, ID หัวข้อและตำแหน่งบนแผนที่ของแต่ละรอบ, งานอ้างอิง OpenAlex)
```
Replace
```markdown
- API key (env var เท่านั้น — ห้ามใส่ในไฟล์ใด ๆ): embedding แบบ api ใช้ `ATLAS_EMBED_API_KEY` (ดู §1A), LLM labeling แบบ api ใช้ `ATLAS_API_KEY` (ตั้งใน crontab env ถ้ารันอัตโนมัติ)
```
with
```markdown
- API key (env var เท่านั้น — ห้ามใส่ในไฟล์ใด ๆ): embedding แบบ api ใช้ `ATLAS_EMBED_API_KEY` (ดู §1A), LLM ใช้ `ATLAS_LLM_API_KEY` (ดู §6; ใช้ key เดียวกันได้) — ตั้งใน crontab env ถ้ารันอัตโนมัติ
```
Replace
```markdown
8. **Emerging narrative อัตโนมัติ** — ให้ LLM เขียนย่อหน้าสรุป "ทำไมหัวข้อนี้ emerging" จาก metric + ตัวอย่างบทความ (prompt พร้อมแล้วที่ `prompts/emerging_narrative.th.md`)
```
with
```markdown
8. ~~**Emerging narrative อัตโนมัติ**~~ — ✅ P1: step `narrate` (`prompts/topic_narrative.th.md` + บทสรุปผู้บริหาร) ตรวจตัวเลขทุกตัวก่อนเผยแพร่
```
Replace
```markdown
export ATLAS_EMBED_API_KEY=...             # ถ้าใช้ embedding แบบ API (labeling แบบ API: ATLAS_API_KEY)
```
with
```markdown
export ATLAS_EMBED_API_KEY=...             # ถ้าใช้ embedding แบบ API
export ATLAS_LLM_API_KEY=...               # ถ้าใช้ LLM (ชื่อหัวข้อ/คำอธิบาย/บทสรุป) — ใช้ key เดียวกันได้
```
Replace
```markdown
export ATLAS_API_KEY=...        # LLM labeling แบบ api
```
with
```markdown
export ATLAS_LLM_API_KEY=...    # LLM (ชื่อหัวข้อ · คำอธิบาย · บทสรุป) — PowerShell: $env:ATLAS_LLM_API_KEY="..."
```
Replace
```markdown
  label.py        LLM ตั้งชื่อ topic (cache_key = hash ของ model + prompt ใน state/label_cache) หรือ off
```
with
```markdown
  label.py        ตั้งชื่อ topic ผ่าน LLM runner (cache ใน state/llm_cache) หรือ off + ชื่อที่บรรณาธิการแก้
```

- [ ] **Step 8: Check**

Run: `grep -rn "label_cache\|ATLAS_API_KEY\|PROMPT_TEMPLATE\|emerging_narrative" docs CLAUDE.md README.md pipeline/README.md prompts` — every remaining hit must be historical (P0 plan/spec files under `docs/superpowers/`), the one-time migration note in OPERATIONS §6, or the "formerly" note in `prompts/topic_narrative.th.md`. Then `uv run ruff check . && uv run pytest -q` (docs-only change; nothing should move).

- [ ] **Step 9: Commit**

```bash
git add docs/ARCHITECTURE.md docs/DATA_SPEC.md docs/OPERATIONS.md docs/ROADMAP.md CLAUDE.md pipeline/README.md README.md
git commit -m "docs: P1 architecture, data spec (contract v2, LLM cache, release state), operations (LLM, review, publish, bake-off), roadmap

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

