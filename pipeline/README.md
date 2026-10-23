# TCI Research Atlas — Batch Pipeline

Pipeline สร้างรอบข้อมูล (release) ของ Research Atlas จากคลังบทความ TCI/ThaiJO:
**ingest → embedding (API หรือ local) → topic clustering 2 ชั้น → ID หัวข้อถาวร + taxonomy → ตั้งชื่อด้วย LLM →
Emerging Topic Analysis → Forecast → โมดูลบรรณาธิการ/ผู้บริหาร/นักวิจัย → export data contract v2 → validate → publish**

ทุกขั้นเป็น batch ที่ checkpoint ลง `work_dir` — พัง/หยุดกลางทางแล้วรันต่อได้ งานที่เสียเงิน (embedding, คำตอบ LLM) เก็บถาวรใน `state_dir` จึงไม่จ่ายซ้ำ

```
ingest → preprocess → embed → cluster → taxonomy → label → series → emerging → keywords → forecast → narrate
       → layout → methods → journals → match → institutions → sdg → benchmark → gaps → references → search
       → kwtrends → export
```

(ลำดับนี้คือ `atlas.pipeline.STEPS`; หลัง export ตามด้วย `atlas validate` และ `atlas publish` — `atlas quarterly` ทำทั้งหมดในคำสั่งเดียว)

---

## 1. Quick start

```bash
cd pipeline
uv sync --extra api                        # หรือ --extra local (BGE-M3 บน GPU); + --extra fast --extra leiden สำหรับคลังใหญ่
cp config.example.yaml config.yaml         # แก้ input.path → โฟลเดอร์คลัง (รูปแบบ 1.0), state_dir, embedding, LLM, publish.site_url
uv run atlas quarterly --corpus /path/to/corpus --release 2026Q4 --prepare   # ตรวจคลังก่อน (ไม่เสียเงิน)
uv run atlas quarterly --corpus /path/to/corpus --release 2026Q4             # ทั้งรอบ → ../runs/2026Q4/ + ../deploy/2026Q4/site/
uv run pytest -q                           # ทดสอบ (+ uv run pytest -m slow -q = e2e บนคลังสังเคราะห์)
```

ขั้นตอนรอบจริงแบบละเอียด (embedding ครั้งแรก, ตรวจผล, ตรวจชื่อหัวข้อ, ขึ้นเว็บ, backup, rollback): `../docs/OPERATIONS.md` §1 — README นี้ไม่ซ้ำเนื้อหานั้น

- Python ≥ 3.11 (dev/CI ใช้ 3.12) · ทางหลักคือ `uv sync`; `requirements.txt` เป็น export ของ `uv.lock` สำหรับติดตั้งแบบไม่ใช้ uv
- extras: `local` = `sentence-transformers` (BGE-M3) · `api` = `openai` (ไม่จำเป็นแล้ว — embedding และ LLM ใช้แกน HTTP ของ `atlas` เอง) · `fast` = `fast-hdbscan` (อัลกอริทึม `hdbscan_fast`) · `leiden` = `igraph` (Leiden บน kNN graph)
- ดีฟอลต์ `embedding.provider: local`; โหมด `lite` (TF-IDF+SVD) ไม่ต้องใช้ extra ใด ๆ — ใช้ใน CI/ทดสอบเท่านั้น (เกิน `embedding.lite_max_docs` เรื่องจะขึ้น WARNING และ `atlas quarterly`/`package_release.sh` ไม่ยอมแพ็กรอบที่ทำด้วย `lite` หรือ `fixture` ขึ้นเว็บจริง)
- **ข้อมูลจริงไม่เข้า git** — คลังบทความ, `output/`, `state/`, `registry/*.csv` (ยกเว้น `*.example.csv`), `../runs/`, `../deploy/` ถูก ignore; repo มีเฉพาะตัวอย่าง 11 ไฟล์ใน `tests/fixtures/thaijo_md/` และคลังสมมติใน `../docs/corpus/example/`

## 2. คลังบทความ (input)

| `input.format` | ข้อมูล | หมายเหตุ |
|---|---|---|
| `corpus_jsonl` | **คลังรูปแบบ 1.0 (แนะนำ)** — `articles/**/*.jsonl[.gz]` (`input.corpus_glob`) + `journals.csv` ในโฟลเดอร์เดียวกัน | สเปก: `../docs/corpus/README.md` · โมเดล pydantic `atlas/schema/corpus.py` (`tci-atlas-corpus/1.0`) → `../docs/corpus/corpus.schema.json` · ประเภทใน `input.exclude_article_types` ถูกตัดและนับในรายงาน |
| `thaijo_md` | โฟลเดอร์ไฟล์ .md จาก ThaiJO หนึ่งไฟล์ต่อบทความ (`input.glob`) | ค่าดีฟอลต์ของ `config.py` เมื่อไม่ระบุ (`config.example.yaml` ตั้ง `corpus_jsonl`) · รูปแบบและสิ่งที่ parser ซ่อมให้: `../docs/DATA_SPEC.md` §1 |
| `table` | ไฟล์ตารางไฟล์เดียว (csv/json/jsonl/parquet) | จับคู่คอลัมน์ที่ `input.columns` |

`atlas quarterly` และ `atlas profile` ดูรูปแบบจากโฟลเดอร์เอง (`articles/*.jsonl*` → `corpus_jsonl`, ไม่งั้น `.md`); `atlas run` ใช้ค่า `input.format` ใน config ตรง ๆ

**ไฟล์ประกอบ (companion files)** ที่ทีมข้อมูลส่งมาพร้อมคลัง (`atlas/companions.py`):

| ไฟล์ในโฟลเดอร์คลัง | ใช้แทนค่า config | เนื้อหา |
|---|---|---|
| `journals.csv` | `journals.registry_path` | 1 แถวต่อ `journal_key` (ชื่อ ISSN กลุ่ม TCI สาขา) — บังคับสำหรับ `corpus_jsonl` |
| `institutions_aliases.csv` | `institutions.aliases_path` | ชื่อสังกัดที่เขียนต่างกัน → สถาบันเดียว |
| `province_population.csv` | `institutions.population_path` | ประชากรรายจังหวัด → บทความต่อประชากร 100,000 คน |
| `ror.zip` | `institutions.ror_path` | ฐาน ROR (CC0) สำหรับจับคู่สถาบัน |

`atlas quarterly` ใช้ไฟล์เหล่านี้แทนค่าใน `config.yaml` ให้เอง — ถ้ารัน `atlas run` เองต้องตั้ง path ใน config (ตัวอย่างไฟล์: `registry/*.example.csv`)

ตรวจคลังก่อนรันเสมอ:

```bash
uv run atlas profile /path/to/corpus --md ../logs/profile.md [--out profile.json] [--workers 4] [--aliases-todo aliases_todo.csv]
uv run atlas corpus convert /path/to/md --out /path/to/new-corpus   # คลัง .md → รูปแบบ 1.0 (รหัสบทความเดิม, ตาราง ingest เดิม)
uv run atlas corpus schema                                          # เขียน ../docs/corpus/corpus.schema.json ใหม่หลังแก้ schema/corpus.py (CI ตรวจ drift)
```

`atlas profile` รายงานจำนวนไฟล์/บรรทัดที่อ่านไม่ได้ (พร้อม `ไฟล์:บรรทัด`), ช่วงปีและที่มาของปี, % ความครบของแต่ละช่อง, ปัญหาข้อความไทย, วารสารที่อัปโหลดย้อนหลัง และผลตรวจไฟล์ประกอบด้วย loader ตัวเดียวกับ pipeline; exit 1 เมื่อสัดส่วนที่อ่านไม่ได้เกิน `--max-error-ratio` (= `input.max_error_ratio`, ดีฟอลต์ 0.01) หรือไฟล์ประกอบต้องแก้ · `--aliases-todo` เขียนสังกัดที่พบบ่อยที่สุดซึ่งยังไม่มีแถวใน alias table (ระดับสถาบันเท่านั้น)
ทีมข้อมูลที่ไม่ได้ติดตั้ง pipeline ตรวจรูปแบบแบบเบาได้ด้วย `python ../docs/corpus/validate_jsonl.py <คลัง>` (ต้องมี `jsonschema`; ไม่ตรวจกติกาข้ามช่อง)

## 3. ตั้งค่า

```bash
cp config.example.yaml config.yaml          # key ที่ไม่รู้จักถูกปฏิเสธ (AtlasConfig, pydantic)
export ATLAS_EMBED_API_KEY=...              # embedding แบบ api (PowerShell: $env:ATLAS_EMBED_API_KEY="..." หรือ setx)
export ATLAS_LLM_API_KEY=...                # LLM — ใช้ key เดียวกันได้
export OPENALEX_API_KEY=...                 # ไม่บังคับ (taxonomy + ไทยเทียบโลก)
```

key อยู่ใน env var เท่านั้น — config เก็บแค่ "ชื่อ" env var (`api_key_env`)

**Embedding — โหมด API** (`embedding.provider: api`) รองรับทุก endpoint แบบ OpenAI-compatible (`POST {base_url}/embeddings`) —
รันครั้งใหญ่ด้วย `atlas embed` (retry ไม่จำกัดเมื่อ server ล่ม, หยุดทันทีเมื่อ config ผิด, resume ได้ — ดู `../docs/OPERATIONS.md` §1A).
ชื่อ base_url/model ด้านล่างเป็นตัวอย่าง ตรวจกับผู้ให้บริการก่อนใช้:

| ผู้ให้บริการ | base_url | model |
|---|---|---|
| BGE-M3 บน server ตัวเอง (HF TEI / vLLM / Infinity / Ollama) | `http://host:port/v1` | `BAAI/bge-m3` หรือ `bge-m3` (`dimensions: null`) |
| DeepInfra | `https://api.deepinfra.com/v1/openai` | `BAAI/bge-m3` (`dimensions: null`) |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `BAAI/bge-m3` (`dimensions: null`) |
| OpenAI | `https://api.openai.com/v1` | `text-embedding-3-large` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `text-embedding-004` |
| OpenRouter | `https://openrouter.ai/api/v1` | เช่น `openai/text-embedding-3-large` |

**Embedding — โหมด Local** (`embedding.provider: local`) ดีฟอลต์ `BAAI/bge-m3` (multilingual, ไทยดี) บน GPU ตัวเอง — ฟรีแต่ช้ากว่า

**LLM** (`labeling.provider: llm`, `narrative.provider: llm`, `methods.provider: llm` — ปลายทางที่ `llm.endpoints`/`llm.tasks`, งบสูงสุด `llm.budget_usd`; narrative ดีฟอลต์ `template`) หรือ `"off"` (ต้องใส่เครื่องหมายคำพูด — YAML อ่าน `off` เปล่า ๆ เป็น false): ชื่อหัวข้อจะมาจากคำสำคัญของผู้เขียน + c-TF-IDF · prompt อยู่ที่ `../prompts/*.md` เท่านั้น

**เผยแพร่:** `publish.site_url` = ที่อยู่สาธารณะของเว็บ (ใช้เขียนฟีด Atom และ `atlas quarterly` ส่งเป็น `ATLAS_SITE_URL` ตอน build เว็บสำหรับ canonical/Open Graph/sitemap); `publish.keep_full_releases` = จำนวนรอบที่เก็บครบบนเว็บ (รอบเก่ากว่าถูกลดเหลือไฟล์หลัก)

ค่าทุกตัวพร้อมคำอธิบายอยู่ใน `config.example.yaml`; ที่มาของแต่ละโมดูลและวิธีตั้งเกณฑ์: `../docs/OPERATIONS.md` §6–§22

## 4. คำสั่ง (`uv run atlas <cmd> --help` ดูตัวเลือกทั้งหมด)

```bash
# รอบไตรมาส
uv run atlas quarterly [-c config.yaml] [--corpus <คลัง>] [-r 2026Q4] [--prepare] [--yes] [--strict] [--build-web] \
                       [--runs-dir ../runs] [--deploy-dir ../deploy] [--site ../web/dist]

# ทีละขั้น
uv run atlas profile <คลัง> --md <report.md>                               # ตรวจคลัง (exit 1 = ต้องแก้)
uv run atlas run -c config.yaml                                             # ทุก step
uv run atlas run -c config.yaml -s emerging -s forecast -s export           # เฉพาะบาง step (-s ซ้ำได้ ตามลำดับที่ให้)
uv run atlas embed -c config.yaml --check | --dry-run                       # ยิง 1 request ตรวจ key/URL/มิติ | นับงาน/ตัวอักษร/~token ไม่ยิง API
uv run atlas embed -c config.yaml [--background] [--concurrency N]          # embed ครั้งใหญ่ (resume = รันคำสั่งเดิมซ้ำ; exit 0/2/3/130)
uv run atlas status -c config.yaml                                          # สถานะงานยาวทั้ง embedding และ LLM (alias: embed-status)
uv run atlas embed-stop -c config.yaml                                      # หยุดอย่างสุภาพ
uv run atlas llm -c config.yaml --check | --dry-run [-t <task>]             # ตรวจปลายทาง | ประมาณ call/token/ค่าใช้จ่าย ไม่ใช้เน็ต
uv run atlas llm -c config.yaml [--background]                              # รัน step label, methods (เมื่อ methods.provider: llm), narrate
uv run atlas llm-stop -c config.yaml
uv run atlas review export -c config.yaml [--out x.csv] [--n 50]            # CSV ให้บรรณาธิการตรวจชื่อหัวข้อ
uv run atlas review import <filled.csv> -c config.yaml                      # ชื่อที่แก้ → labeling.overrides_path
uv run atlas validate -c config.yaml [--release R] [--dir D] [--previous P] # exit 0 = ผ่าน, 1 = คำเตือน, 2 = error
uv run atlas publish -c config.yaml --site ../web/dist [--tarball] [--allow-warnings] [--set-latest]

# เครื่องมือ
uv run atlas sdg-scores -c config.yaml                                      # ช่วยตั้ง sdg.min_similarity (อ่านอย่างเดียว)
uv run atlas bakeoff -c config.yaml --kind embedding|clustering|all [--truth _truth.csv] [--out report.md]
uv run atlas synth --out .ci/synth --n 20000 [--seed 7]                     # คลังสังเคราะห์ (.md) พร้อม _truth.csv
uv run atlas schema                                                         # ../web/src/data/contract.schema.json → แล้ว npm run gen:types ใน web/
uv run atlas corpus schema | corpus convert <md> --out <dir>
uv run atlas version
```

(`python -m atlas.pipeline --steps …` ยังใช้ได้เป็น alias ของ `atlas run`; `scripts/run_all.sh [config.yaml]` = `atlas run`)

### `atlas quarterly`

ลำดับใน `atlas/quarterly.py` — แต่ละขั้นเป็น process `atlas` แยกที่มี exit code ของตัวเอง รันซ้ำคำสั่งเดิม = ทำต่อจากจุดที่หยุด:

1. **config** → `runs/<รอบ>/config.yaml` (config.yaml + คลัง รูปแบบที่ตรวจพบ ไฟล์ประกอบ และชื่อรอบ)
2. **corpus** → `runs/<รอบ>/corpus_manifest.json` (ไฟล์ ขนาด sha256)
3. **profile** → `runs/<รอบ>/profile.md` (+ `aliases_todo.csv`) — หยุดถ้าเกิน `input.max_error_ratio` · `--prepare` หยุดตรงนี้
4. **embed** (เฉพาะ `provider: api`) dry-run แล้ว `atlas embed`
5. **llm** (เมื่อเปิดงาน LLM) แสดง `atlas llm --dry-run` แล้วถามยืนยันก่อนจ่าย (`--yes` ข้าม)
6. **run** → `pipeline.log` · 7. **validate** → `validate.txt` (exit 2 หยุด; exit 1 ไปต่อ เว้นแต่ `--strict`)
8. **web** — `npm ci && npm run build` เมื่อยังไม่มี `web/dist` หรือใส่ `--build-web`
9. **publish** `--site web/dist` · 10. **deploy** → `deploy/<รอบ>/site/` + `deploy/atlas-site-<รอบ>.zip` + `deploy/atlas-data-<รอบ>.zip` (ปฏิเสธรอบ `fixture`/`lite`)
11. **summary** → `runs/<รอบ>/summary.md` (ตัวเลข เวลาแต่ละขั้น คำเตือน และสิ่งที่ต้องอัปโหลด)

ไม่ใส่ `--release` = ไตรมาสของวันนี้ เว้นแต่ `work_dir` มีรอบที่เริ่มแล้วยังไม่จบ (ยังไม่มี `summary.md`) — รอบนั้นถูกทำต่อ
ใช้จาก root ได้ด้วย `bash scripts/quarterly_run.sh …` หรือดับเบิลคลิก `scripts\quarterly_run.cmd` บน Windows

## 5. ผลลัพธ์และโฟลเดอร์

| ที่ | อะไร |
|---|---|
| `output/data/<release>/*.json` + `output/data/latest.json` | **data contract v2** ที่เว็บอ่าน (`SCHEMA_VERSION = "2.5.0"`, `definition_version = 3`) — schema เต็ม `../docs/DATA_SPEC.md` |
| `output/atlas_data.json` + `topics.csv` · `emerging.csv` · `forecasts.csv` · `manifest.json` | schema 1.1 รุ่นเก่า + CSV สำหรับนักวิเคราะห์ (เว็บ v2 ไม่อ่าน `atlas_data.json` แล้ว) |
| `output/review/` · `output/releases/` | CSV ตรวจชื่อหัวข้อ · `atlas-data-<release>.tar.gz` + notes จาก `publish --tarball` |
| `work/` | checkpoint ของทุก step — ลบได้เสมอ |
| `state/` | ข้อมูลถาวรข้ามรอบ: embedding store, `llm_cache/`, ID หัวข้อ (assignments, registry, lineage) และตำแหน่งแผนที่ใน `state/releases/<release>/`, งานอ้างอิง OpenAlex — **ห้ามลบ ควร backup** |
| `../runs/<release>/` · `../deploy/` | บันทึกรอบและชุดพร้อมอัปโหลดจาก `atlas quarterly` |

`atlas publish --site <dir>` ตรวจรอบอีกครั้งแล้วเขียน `data/<release>/`, `data/latest.json`, `atlas-offline.html` (จาก `offline-template.html` ของ web build, ไม่รวม `export.offline_exclude` และไม่เกิน `export.offline_max_mb`) และ `data/feeds/` เมื่อตั้ง `publish.site_url` · คัดลอกรอบก่อนหน้าตามสาย `previous_release` กลับมาให้ (เว็บเทียบ Δ ได้แม้ `npm run build` ล้าง `dist/`) · ไม่ย้าย `latest.json` ไปรอบที่เก่ากว่าบน site เว้นแต่ `--set-latest` · ไม่อัปโหลดอะไรเลย

## 6. ความเป็นส่วนตัว (PDPA)

- ชื่อผู้แต่งถูกอ่านเพื่อหาสังกัดเท่านั้น; ไฟล์ที่เผยแพร่มีแต่ตัวเลขรวม (หัวข้อ วารสาร สถาบัน จังหวัด) — ไม่มีชื่อบุคคล บทคัดย่อ หรือข้อความรายการอ้างอิง (`match.json` เก็บแค่น้ำหนัก trigram; ดัชนีค้นหาสร้างจากชื่อเรื่อง + คำสำคัญเท่านั้น)
- สถาบันที่มีบทความน้อยกว่า `institutions.min_articles` นับในยอดรวมแต่ไม่ถูกแสดงเป็นรายการ
- **ด่านตรวจใน `atlas validate` / `atlas publish`** (`atlas/privacy.py`): สแกนทุกไฟล์ของรอบจริงหาอีเมล, ORCID iD และชื่อหน่วยงานที่มีชื่อเต็มของผู้แต่งในคลังปนอยู่ — พบ = error (exit 2) และ publish ปฏิเสธ; ชื่อหน่วยงานที่คนตรวจแล้วว่าไม่ใช่ชื่อบุคคลใส่ใน `validation.privacy_allow` · ข้อความ error อ้างไฟล์และชื่อหน่วยงาน ไม่พิมพ์ชื่อผู้แต่ง

## 7. ตั้งเวลารัน

```bash
# crontab: 01:00 วันที่ 1 ของเดือน 1,4,7,10 (--yes = ไม่ถามก่อนจ่ายค่า LLM; งบยังคุมด้วย llm.budget_usd)
0 1 1 1,4,7,10 * cd /path/to/tci-research-atlas && bash scripts/quarterly_run.sh --yes >> logs/cron.log 2>&1
```

คนยังต้องตรวจผลก่อนอัปโหลด (`../docs/OPERATIONS.md` §1.4 และ §2)

---

## นิยาม "Emerging" ของ TCI v3

implement ใน `atlas/emerging.py` (`definition_version = 3`) และปรับ threshold ได้ทั้งหมดใน `config.yaml → emerging:`
หน้าต่างเวลา: R = `recent_window` ปีล่าสุดที่ข้อมูลสมบูรณ์ (ดีฟอลต์ 3), B = `baseline_window` ปีก่อนหน้า R (ดีฟอลต์ 5); ปีที่กำลังดำเนินอยู่ (`as_of_year`) ไม่นับเสมอ และ backfill guard ตัดปีล่าสุดที่ยอดต่ำกว่า 60% ของ median 3 ปีก่อนหน้า (ได้สูงสุด 2 ปี) — ปีที่ถูกตัดอยู่ใน `meta.trimmed_years`

| สถานะ | ความหมาย (ดีฟอลต์) |
|---|---|
| **LOW_DATA** ข้อมูลน้อย | count_R < 30 หรือประมาณ share_growth ไม่ได้ — ไม่ฟันธง |
| **EMERGING** กำลังเกิดใหม่ | หัวข้อเล็ก **และ** ขอบล่างของช่วงเชื่อมั่นการโต ≥ +10%/ปี **และ** share_ratio ≥ 1.8 **และ** ความกว้าง (≥ 3 วารสาร, ≥ 3 สถาบัน, วารสารใหม่ < 50%) ผ่าน |
| **WATCH** จับตา | โตตามเกณฑ์ EMERGING แต่ความกว้างไม่ผ่าน (สัญญาณ journal-entry bias) |
| **HOT** กำลังมาแรง | หัวข้อใหญ่ (share_R ≥ quantile 0.75) **และ** ขอบล่างของช่วงเชื่อมั่นการโต > 0 |
| **DECLINING** ลดลง | ขอบบนของช่วงเชื่อมั่นการโต < 0 **และ** share_ratio ≤ 0.8 |
| **STABLE** คงที่ | อื่น ๆ |

สถานะตรวจตามลำดับข้างต้น (ข้อแรกที่เข้าคือคำตอบ) · Emerging Score 0–100 เป็น percentile ภายในรอบ ใช้จัดอันดับเท่านั้น เทียบข้ามรอบไม่ได้
v3: share_growth ที่ประมาณไม่ได้ (เช่น บทความทั้งหมดอยู่ปีเดียว) = NaN → LOW_DATA · ช่วงเชื่อมั่น (`ci_level` 0.90) ใช้ Student-t เมื่อข้อมูล overdispersed · `orgs_unverified` บอกหัวข้อที่ข้ามเกณฑ์สถาบัน (ข้อมูลสังกัดไม่พอ)
ชื่อสถานะที่เผยแพร่มาจาก `narrative.STATUS_TH/STATUS_EN` · สเปกเต็มพร้อมสูตรและเหตุผลเชิงวิธีวิจัย: `../docs/EMERGING_SPEC.md`

แก้นิยาม = แก้ `../docs/EMERGING_SPEC.md` + `config.example.yaml` + `tests/test_emerging.py` + `../web/src/lib/definition.ts` พร้อมกัน และเพิ่ม `definition_version`

### Forecast

- Forecast v2 = share ของหัวข้อ × ยอดรวมของคลัง; โมเดล `naive`, `drift`, `nb_glm`, `ets_damped` (ยอดรวมใช้ `forecast.total_models`) เลือกต่อ topic ด้วย rolling-origin CV (MAE, MASE, skill เทียบ naive); โมเดลยอดรวมแยกตามจุดตั้งต้นของแต่ละ fold (ไม่มองข้อมูลอนาคต)
- ทำนายล่วงหน้า `forecast.horizon` = 2 ปี พร้อมช่วง 80/95 แบบ conformal ที่คาลิเบรตจากเรคคอร์ด backtest ซื่อสัตย์ของโมเดลที่เลือก (`forecast.sigma_floor`, `dispersion_fallback`, `alpha_min/alpha_max`, `min_calibration`)
- nowcast: เฉพาะปีปฏิทินที่กำลังดำเนินอยู่ (`forecast.nowcast.*`, `min_month_share` = 0.02)
- gate: ส่งออก forecast เฉพาะเมื่อ skill เทียบ naive > `forecast.min_skill`, MASE ≤ `forecast.max_mase` และมีจุด backtest ซื่อสัตย์ ≥ `forecast.min_honest_points` (3) ไม่เช่นนั้น `forecast: null` และ `forecast_uncertain: true`; topic ที่มีประวัติ < `forecast.min_history_years` (6) จะไม่ทำนาย
- emerging keywords: `keywords.*` (`smoothing_articles`, `min_key_length` …); layout: `layout.*` (`stable`, `anchor`, `galaxy`, `margin`)

---

## โครงสร้างโค้ด

```
atlas/
  cli.py            typer CLI (ทุกคำสั่งในหัวข้อ 4)
  quarterly.py      atlas quarterly (รอบเดียวจบ: runs/ + deploy/)
  config.py         AtlasConfig (pydantic) — key ที่ไม่รู้จักถูกปฏิเสธ
  pipeline.py       orchestrator (STEPS)
  sources/          corpus_jsonl.py (คลังรูปแบบ 1.0) · thaijo_md.py (ThaiJO Markdown)
  schema/           contract.py (data contract v2 → JSON Schema) · corpus.py (คลังรูปแบบ 1.0)
  corpus_convert.py atlas corpus convert   companions.py  ตรวจไฟล์ประกอบ   profile.py  รายงานคุณภาพคลัง   synth.py  คลังสังเคราะห์
  thai.py           ซ่อมข้อความไทย (PUA, สระอำ), แยก TH/EN
  ingest.py         อ่าน+normalize+dedup (article_id → DOI → ชื่อเรื่อง+ปี; พ.ศ. → ค.ศ.)
  preprocess.py     ประกอบ doc_text
  embed.py          api | local | lite → embed_runner.py (batch, concurrency, journal, lock, stop, progress)
                    + embed_store.py (เก็บถาวรใน state/) + embed_api.py (OpenAI-compatible /embeddings)
  api_http.py       แกน HTTP + retry ที่ embedding และ LLM ใช้ร่วมกัน
  jobs.py           งานยาว: run.lock, stop.flag, progress.json, รันเบื้องหลัง, atlas status
  cluster.py        PCA → UMAP → HDBSCAN → merge ซ้ำ → outlier → กลุ่มใหญ่; ctfidf.py · graph_cluster.py (Leiden)
  lineage.py        ID หัวข้อถาวร T000123 + continue/split/merge/new/retired (ID ไม่ถูกใช้ซ้ำ) · state.py, checkpoints.py
  openalex.py, taxonomy.py   subfield/field ของ OpenAlex ต่อหัวข้อ (งบหมด = กลุ่ม agglomerative)
  prompts.py, llm.py, llm_runner.py   prompt จากไฟล์ · adapter OpenAI-compatible · runner (cache/งบ/หยุด/repair/fallback)
  label.py, review.py, narrative.py   ชื่อหัวข้อ + overrides · ไฟล์ตรวจของบรรณาธิการ · คำอธิบาย/บทสรุปที่ตรวจตัวเลข (grounding_error) และภาษา (jargon_in)
  topics_time.py    yearly series + backfill guard
  emerging.py       นิยาม Emerging v3 + Kleinberg burst + novelty   keywords.py  emerging keywords
  forecast.py       naive/drift/nb_glm/ets_damped + backtest + skill gate
  layout.py         แผนที่หัวข้อ (UMAP 2D นิ่งข้ามรอบ) + similarity edges + พิกัดกาแล็กซี
  P2  methods.py · journals.py · journal_metrics.py · journal_topics.py · registry.py · matcher.py · diff.py · export_editors.py
  P3  places.py · orgs.py · countries.py · institutions_ref.py · institutions.py · sdg.py · global_bench.py · gaps.py · export_exec.py
  P4  references.py · search_index.py · kwtrends.py · export_research.py · feeds.py
  export.py, export_v2.py   atlas_data.json 1.1 + CSV · data contract v2
  validate.py, privacy.py, publish.py   ตรวจรอบ (schema + ความถูกต้อง + เทียบรอบก่อน + PDPA) · วางขึ้นเว็บ/offline/tarball
  bakeoff.py        เทียบโมเดล embedding / อัลกอริทึมจัดกลุ่ม
  data/             th_provinces.csv (77 จังหวัด ISO 3166-2:TH) · frameworks.yaml (SDG/BCG/แผน ววน./แผนฯ 13)
configs/ci.yaml     config สำหรับ CI
registry/           *.example.csv (ไฟล์จริงของผู้ดูแล git-ignored)
tests/              pytest (test_emerging.py ล็อกนิยาม; test_e2e_synth.py = slow; fixtures/match_parity.json + search_parity.json ตรึงฝั่งเว็บ)
scripts/            run_all.sh · make_search_parity.py · write_match_parity.py
```

## สิ่งที่ยังไม่ทำ (ทำเพิ่มได้ภายหลัง)

- co-citation edges บนแผนที่หัวข้อ — ตอนนี้รายการอ้างอิงใช้ในโมดูล `references` (แนวปฏิบัติการอ้างอิงรายวารสาร + "ถูกอ้างใน TCI") เท่านั้น
- incremental clustering แบบ online — clustering รันใหม่ทั้งคลังทุกไตรมาส (embedding เป็น incremental อยู่แล้วผ่าน `state/`; ID หัวข้อต่อเนื่องด้วย `lineage.py`)
- ไอเดียอื่น: `../docs/ROADMAP.md`
