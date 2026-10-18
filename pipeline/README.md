# TCI Research Atlas — Batch Pipeline

Pipeline สำหรับสร้าง Research Atlas จากคลังบทความ ThaiJO แบบ Markdown (ชื่อเรื่อง, ผู้แต่ง, คำสำคัญ, บทคัดย่อ, รายการอ้างอิง)
ครอบคลุม: **embedding (API หรือ local) → topic clustering 2 ชั้น → ตั้งชื่อ topic ด้วย LLM →
Emerging Topic Analysis → Trend Forecasting → export JSON เข้าหน้าเว็บ Atlas**

ทุกขั้นเป็น batch ที่ checkpoint อัตโนมัติ — กลางทางพัง/กดหยุด แล้วรันต่อได้โดยไม่เสียงบประมาณซ้ำ

```
┌─────────┐  ┌────────────┐  ┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐
│ ingest  │→ │ preprocess │→ │ embed  │→ │ cluster │→ │ label  │→ │ series │
│ ThaiJO md│  │ doc_text   │  │api│local│  │UMAP+HDB │  │  LLM   │  │ yearly │
└─────────┘  └────────────┘  └────────┘  └─────────┘  └────────┘  └───┬────┘
                                                                      ↓
┌─────────┐  ┌────────┐  ┌──────────┐                          ┌──────────┐
│ export  │← │ layout │← │ forecast │←─────────────────────────│ emerging │
│ JSON/CSV│  │ UMAP2D │  │ 3 models │                          │ TCI spec │
└─────────┘  └────────┘  └──────────┘                          └──────────┘
```

---

## 1. Quick start

```bash
cd pipeline
uv sync --extra local                      # หรือ --extra api
cp config.example.yaml config.yaml         # แก้ input.path → โฟลเดอร์ .md
uv run atlas profile /path/to/corpus --md ../logs/profile.md   # ขั้น 1: อ่านรายงานก่อนเสมอ
uv run atlas run --config config.yaml      # ขั้น 2: ทั้งสาย (หรือ bash ../scripts/quarterly_run.sh)
bash ../scripts/import_atlas.sh            # ขั้น 3: นำเข้าเว็บ + build
uv run pytest -q                           # ทดสอบ (เพิ่ม uv run pytest -m slow -q สำหรับ e2e ข้อมูลสังเคราะห์)
```

Python ≥ 3.11 (dev/CI ใช้ 3.12) · `--extra api` ติดตั้ง `openai`, `--extra local` ติดตั้ง `sentence-transformers` (BGE-M3) · ดีฟอลต์ `embedding.provider: local`; โหมด `lite` (TF-IDF+SVD) ไม่ต้องใช้ extra ใด ๆ — ใช้ใน CI/ทดสอบเท่านั้น (เกิน `embedding.lite_max_docs` เรื่องจะขึ้น WARNING)
**ข้อมูลจริงไม่เข้า git** — คลังบทความและ `atlas_data.json` ของจริงเก็บนอก repo (มีเฉพาะตัวอย่าง 11 ไฟล์ใน `tests/fixtures/thaijo_md/`)

## 2. เตรียมข้อมูล

ค่าดีฟอลต์ `input.format: thaijo_md` — โฟลเดอร์ไฟล์ .md จาก ThaiJO หนึ่งไฟล์ต่อบทความ (รูปแบบและสิ่งที่ pipeline ซ่อมให้ ดู `../docs/DATA_SPEC.md` §1)
ถ้ามีเป็นตาราง ตั้ง `input.format: table` (csv/json/jsonl/parquet) แล้วจับคู่คอลัมน์ที่ `input.columns`

ตรวจคลังก่อนรันเสมอ:

```bash
uv run atlas profile /path/to/corpus --md ../logs/profile.md [--out ../logs/profile.json] [--workers 4]
```

รายงานบอกจำนวนไฟล์ ช่วงปี (และแหล่งที่มาของปี) ฟิลด์ว่าง ปัญหาข้อความไทย และวารสารที่อัปโหลดย้อนหลัง

## 3. ตั้งค่า

```bash
cp config.example.yaml config.yaml
export ATLAS_API_KEY=sk-...     # ถ้าใช้โหมด api
```

จุดที่ต้องเลือกใน `config.yaml`:

**Embedding — โหมด API** (`embedding.provider: api`) รองรับทุก endpoint แบบ OpenAI-compatible:

| ผู้ให้บริการ | base_url | model |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `text-embedding-3-large` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `text-embedding-004` |
| OpenRouter | `https://openrouter.ai/api/v1` | เช่น `openai/text-embedding-3-large` |
| vLLM/Ollama ตัวเอง | `http://localhost:8000/v1` | ตามที่ deploy |

**Embedding — โหมด Local** (`embedding.provider: local`) ดีฟอลต์ `BAAI/bge-m3` (multilingual, ไทยดี) บน GPU ตัวเอง — ฟรี แต่ช้ากว่า; 200K เรื่อง ≈ 2–4 ชม. บน GPU เกรดกลาง

**LLM labeling** (`labeling.provider: api`) — ใช้ endpoint เดียวกันได้ หรือ `"off"` (ต้องใส่เครื่องหมายคำพูด — YAML อ่าน `off` เปล่า ๆ เป็น false) ถ้าไม่มีงบ: ชื่อหัวข้อจะมาจากคำสำคัญของผู้เขียน + c-TF-IDF

## 4. รัน

```bash
uv run atlas run --config config.yaml                                   # ทั้งสาย
uv run atlas run -c config.yaml -s embed -s cluster                     # บางขั้น (-s ซ้ำได้)
uv run atlas run -c config.yaml -s emerging -s forecast -s export       # รันซ้ำเฉพาะท้ายสาย (ฟรี ไม่แตะ API)
uv run atlas synth --out .ci/synth --n 20000                           # สร้างคลังสังเคราะห์สำหรับทดสอบ
uv run atlas schema                                                     # เขียน JSON Schema ของ data contract v2
```

(`python -m atlas.pipeline --steps …` ยังใช้ได้เป็น alias ของ `atlas run` แต่ควรใช้ `atlas` CLI)

ผลลัพธ์อยู่ใน `output/`: `atlas_data.json` (schema 1.1, สำหรับเว็บ), `topics.csv`, `emerging.csv`, `forecasts.csv`, `manifest.json`
ข้อมูลที่ต้องอยู่ข้ามรอบ (embedding store, label cache, centroid รอบก่อน) อยู่ใน `state/` (git-ignored, ห้ามลบ) ส่วน `work/` ลบได้เสมอ

## 5. ตั้งเวลารัน (เช่น ทุกไตรมาส)

```bash
# crontab: 01:00 วันที่ 1 ของเดือน 1,4,7,10
0 1 1 1,4,7,10 * cd /path/to/tci-research-atlas/pipeline && uv run atlas run --config config.yaml >> ../logs/cron.log 2>&1
# หรือใช้สคริปต์ที่ profile คลังก่อนแล้วรัน: bash /path/to/tci-research-atlas/scripts/quarterly_run.sh
```

export เก็บ centroids ของรอบนี้ไว้ใน `state/prev/` ให้รอบหน้า — **P0 ยังไม่ใช้** (novelty ตอนนี้ = สัดส่วนบทความของหัวข้อที่อยู่ในช่วง R + อายุของหัวข้อ ดู `../docs/EMERGING_SPEC.md` §3); P1 จะใช้ไฟล์นี้ทำ lineage ของหัวข้อข้ามรอบ

---

## นิยาม "Emerging" ของ TCI v3

implement ใน `atlas/emerging.py` (`definition_version = 3`) และปรับ threshold ได้ทั้งหมดใน `config.yaml → emerging:`
หน้าต่างเวลา: R = `recent_window` ปีล่าสุดที่ข้อมูลสมบูรณ์ (ดีฟอลต์ 3), B = `baseline_window` ปีก่อนหน้า R (ดีฟอลต์ 5); ปีที่กำลังดำเนินอยู่ (`as_of_year`) ไม่นับเสมอ และ backfill guard ตัดปีล่าสุดที่ยอดต่ำกว่า 60% ของ median 3 ปีก่อนหน้า (ได้สูงสุด 2 ปี) — ปีที่ถูกตัดอยู่ใน `meta.trimmed_years`

| สถานะ | ความหมาย (ดีฟอลต์) |
|---|---|
| **LOW_DATA** ข้อมูลน้อย | count_R < 30 หรือประมาณ share_growth ไม่ได้ — ไม่ฟันธง |
| **EMERGING** กำลังเกิดใหม่ | หัวข้อเล็ก **และ** ขอบล่างของช่วงเชื่อมั่นการโต ≥ +10%/ปี **และ** share_ratio ≥ 1.8 **และ** ความกว้าง (วารสาร/สถาบัน) ผ่าน |
| **WATCH** จับตา | โตตามเกณฑ์ EMERGING แต่ความกว้างไม่ผ่าน (สัญญาณ journal-entry bias) |
| **HOT** กำลังร้อน | หัวข้อใหญ่ **และ** ขอบล่างของช่วงเชื่อมั่นการโต > 0 |
| **DECLINING** กำลังลดลง | ขอบบนของช่วงเชื่อมั่นการโต < 0 **และ** share_ratio ≤ 0.8 |
| **STABLE** คงที่ | อื่น ๆ |

สถานะตรวจตามลำดับข้างต้น (ข้อแรกที่เข้าคือคำตอบ) · Emerging Score 0–100 เป็น percentile ภายในรอบ ใช้จัดอันดับเท่านั้น เทียบข้ามรอบไม่ได้
v3: share_growth ที่ประมาณไม่ได้ (เช่น บทความทั้งหมดอยู่ปีเดียว) = NaN → LOW_DATA · ช่วงเชื่อมั่นใช้ Student-t เมื่อข้อมูล overdispersed · `orgs_unverified` บอกหัวข้อที่ข้ามเกณฑ์สถาบัน (ข้อมูลสังกัดไม่พอ)
สเปกเต็มพร้อมสูตรและเหตุผลเชิงวิธีวิจัย: `docs/EMERGING_SPEC.md`

แก้นิยาม = แก้ `docs/EMERGING_SPEC.md` + `config.example.yaml` + `tests/test_emerging.py` พร้อมกัน และเพิ่ม `definition_version`

### Forecast

- โมเดล: `naive`, `linear` (OLS), `poisson` (GLM) — เลือกต่อ topic ด้วย backtest (MAE, MASE, skill เทียบ naive)
- ทำนายล่วงหน้า 2 ปี พร้อมช่วงความเชื่อมั่น
- skill gate: ส่งออก forecast ใน JSON เฉพาะเมื่อ skill เทียบ naive > `forecast.min_skill` ไม่เช่นนั้น `forecast: null` และ `forecast_uncertain: true`; topic ที่มีประวัติ < `forecast.min_history_years` (6) จะไม่ทำนาย

---

## การเชื่อมเข้าหน้าเว็บ Atlas

`output/atlas_data.json` มีโครง `{meta, groups, nodes, links}` — nodes แต่ละตัวมี
`x, y, r, color, th, en, articles, status, emerging_score, burst_years, share_growth(_lo/_hi), journal_driven, orgs_unverified, forecast{...}` (schema 1.1 — ดู `../docs/DATA_SPEC.md` §3)
หน้าเว็บที่ทำไว้สลับจากไฟล์ `src/data/atlas.ts` มาอ่าน JSON นี้ได้โดยเปลี่ยน data source จุดเดียว
(โครง field ตั้งใจออกแบบให้ตรงกัน)

## งบประมาณโดยประมาณ (corpus 200K เรื่อง)

| ขั้น | API | Local |
|---|---|---|
| Embedding รอบแรก | ~$10–20 (batch API) | ฟรี, 2–4 ชม. บน GPU |
| LLM labeling (~300–800 topics) | ~$1–3 | ฟรี (ถ้ารันโมเดลเอง) |
| รอบถัดไป (incremental) | เฉพาะบทความใหม่ | เฉพาะบทความใหม่ |

## โครงสร้างโค้ด

```
atlas/
  cli.py          typer CLI: run | profile | synth | schema
  config.py       AtlasConfig (pydantic) — key ที่ไม่รู้จักถูกปฏิเสธ
  sources/        thaijo_md.py — parser ไฟล์ ThaiJO Markdown
  schema/         contract.py — data contract v2 (สร้าง JSON Schema)
  thai.py         ซ่อมข้อความไทย (PUA, สระอำ), แยก TH/EN
  ingest.py       อ่าน+normalize+dedup (article_id → DOI → ชื่อเรื่อง+ปี)
  preprocess.py   ประกอบ doc_text = title + keywords + abstract
  embed.py        api | local | lite + embed_store.py (เก็บถาวรใน state/)
  cluster.py      PCA → UMAP → HDBSCAN (sklearn) → merge ซ้ำ → outlier → กลุ่มใหญ่ (agglomerative); ctfidf.py
  label.py        LLM ตั้งชื่อ topic (cache_key = hash ของ model + prompt ใน state/label_cache) หรือ off
  topics_time.py  yearly series + backfill guard
  emerging.py     นิยาม Emerging v3 + Kleinberg burst + novelty
  forecast.py     naive/linear/Poisson + backtest + skill gate
  layout.py       UMAP 2D บน centroid → ตำแหน่งบนแผนที่ + similarity edges
  export.py       atlas_data.json (1.1) + CSVs + manifest
  profile.py      รายงานคุณภาพคลัง   synth.py  คลังสังเคราะห์
  pipeline.py     orchestrator
configs/ci.yaml  config สำหรับ CI
tests/           pytest (test_emerging.py ล็อกนิยาม; test_e2e_synth.py = slow)
scripts/run_all.sh  ตัวช่วยรันทั้งสาย
```

## สิ่งที่ตั้งใจไม่ทำ (และทำเพิ่มได้ภายหลัง)

- co-citation edges — ต้องมี references ในข้อมูล; เพิ่มเป็น edge อีกชุดใน layout.py ได้
- author/affiliation network — metadata พร้อมอยู่แล้ว เพิ่ม aggregation step ได้
- incremental clustering แบบ online — ตอนนี้ clustering รันใหม่ทั้ง corpus ทุกไตรมาส (embedding เป็น incremental อยู่แล้วผ่าน `state/embeddings`)
