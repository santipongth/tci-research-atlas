# TCI Research Atlas — Batch Pipeline

Pipeline สำหรับสร้าง Research Atlas จาก metadata วารสาร TCI (ชื่อเรื่อง, ผู้แต่ง, คำสำคัญ, บทคัดย่อ ฯลฯ)
ครอบคลุม: **embedding (API หรือ local) → topic clustering 2 ชั้น → ตั้งชื่อ topic ด้วย LLM →
Emerging Topic Analysis → Trend Forecasting → export JSON เข้าหน้าเว็บ Atlas**

ทุกขั้นเป็น batch ที่ checkpoint อัตโนมัติ — กลางทางพัง/กดหยุด แล้วรันต่อได้โดยไม่เสียงบประมาณซ้ำ

```
┌─────────┐  ┌────────────┐  ┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐
│ ingest  │→ │ preprocess │→ │ embed  │→ │ cluster │→ │ label  │→ │ series │
│ CSV/JSON│  │ doc_text   │  │api│local│  │UMAP+HDB │  │  LLM   │  │ yearly │
└─────────┘  └────────────┘  └────────┘  └─────────┘  └────────┘  └───┬────┘
                                                                      ↓
┌─────────┐  ┌────────┐  ┌──────────┐                          ┌──────────┐
│ export  │← │ layout │← │ forecast │←─────────────────────────│ emerging │
│ JSON/CSV│  │ UMAP2D │  │linear/pois│                         │ TCI spec │
└─────────┘  └────────┘  └──────────┘                          └──────────┘
```

---

## 1. ติดตั้ง

```bash
cd tci-atlas-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# เลือกตามโหมด embedding:
pip install openai                          # โหมด api
pip install sentence-transformers torch     # โหมด local (BGE-M3)
```

## 2. เตรียมข้อมูล (metadata ขั้นต่ำที่ต้องมี)

ไฟล์ CSV/JSON/JSONL/Parquet หนึ่งแถวต่อบทความ คอลัมน์ที่จำเป็น:

| คอลัมน์ | บังคับ | หมายเหตุ |
|---|---|---|
| `id` | ✓ | รหัสบทความ unique |
| `title_th` / `title_en` | ✓ อย่างใดอย่างหนึ่ง | |
| `year` | ✓ | ปีที่พิมพ์ (พ.ศ./ค.ศ. ก็ได้ — แนะนำแปลงเป็น ค.ศ. ก่อน) |
| `abstract_th` / `abstract_en` | แนะนำ | ถ้าว่างเยอะ topic จะหยาบลง แต่ยังทำงานได้ด้วย title+keywords |
| `keywords_th` / `keywords_en` | แนะนำ | คั่นด้วย `;` |
| `authors`, `affiliations`, `journal`, `tci_tier`, `doi`, `url` | optional | ใช้ drill-down/segment ในเว็บ |

ตรวจไฟล์ก่อนรัน:

```bash
python scripts/validate_input.py --config config.yaml
```

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

**LLM labeling** (`labeling.provider: api`) — ใช้ endpoint เดียวกันได้ หรือ `off` ถ้าไม่มีงบ (จะใช้ c-TF-IDF terms เป็นชื่อ topic แทน)

## 4. รัน

```bash
python -m atlas.pipeline --config config.yaml                      # ทั้งสาย
python -m atlas.pipeline --config config.yaml --steps embed cluster # บางขั้น
python -m atlas.pipeline --steps emerging forecast export           # รันซ้ำเฉพาะท้ายสาย (ฟรี ไม่แตะ API)
```

ผลลัพธ์อยู่ใน `output/`: `atlas_data.json` (สำหรับเว็บ), `topics.csv`, `emerging.csv`, `forecasts.csv`, `manifest.json`

## 5. ตั้งเวลารัน (เช่น ทุกไตรมาส)

```bash
# crontab: 01:00 วันที่ 1 ของเดือน 1,4,7,10
0 1 1 1,4,7,10 * * cd /path/to/tci-atlas-pipeline && .venv/bin/python -m atlas.pipeline --config config.yaml >> logs/cron.log 2>&1
```

รอบใหม่จะใช้ centroids ของรอบก่อน (ที่ pipeline เก็บไว้ให้เองใน `work/prev/`) คำนวณ **novelty** — หัวข้อเกิดใหม่จริงจะมี novelty สูง

---

## นิยาม "Emerging" ของ TCI (ฉบับใช้งานจริง)

นิยามนี้ implement ใน `atlas/emerging.py` และปรับ threshold ได้ทั้งหมดใน `config.yaml → emerging:`

### หน้าต่างเวลา
- `R` = `recent_window` ปีล่าสุด**ที่ข้อมูลสมบูรณ์** (ดีฟอลต์ 3 ปี)
- `B` = `baseline_window` ปีก่อนหน้า R (ดีฟอลต์ 5 ปี)
- **backfill guard**: ถ้าปีล่าสุดมียอดบทความ < 60% ของค่ามัธยฐานรายปี (วารสารยังลงข้อมูลไม่ครบ) ปีนั้นจะถูกตัดจากหน้าต่างวิเคราะห์อัตโนมัติ

### มิติที่วัด (ต่อ topic)

| มิติ | สูตร/วิธี | ความหมาย |
|---|---|---|
| `share_R`, `share_B` | บทความ topic ÷ บทความทั้ง corpus ในช่วง R/B | ขนาดสัมพัทธ์ (กันปีที่ corpus โต) |
| `cagr_recent` | `((c_last+0.5)/(c_first+0.5))^(1/(n-1)) − 1` | อัตราโตต่อปีช่วง R |
| `share_ratio` | `share_R / share_B` | โตเร็วกว่า corpus กี่เท่า |
| `slope_share` | OLS slope ของ share เทียบปี (normalize ด้วย mean share) | ทิศทางระยะยาว B∪R |
| `acceleration` | `slope(count\|R) − slope(count\|B)` (normalize) | เร่งตัวหรือชะลอ |
| `burst_intensity` | Kleinberg 2-state (Poisson, ปรับตามขนาด corpus รายปี, γ=1.0) | มีช่วง "ระเบิด" หรือไม่ + ปีที่ระเบิด |
| `novelty` | `1 − max cosine sim` ของ centroid เทียบ topic รอบ pipeline ก่อน | หัวข้อเกิดใหม่จริง (0.5 ถ้าไม่มีรอบก่อน) |

### เกณฑ์จำแนกสถานะ

| สถานะ | เงื่อนไข (ค่าดีฟอลต์) |
|---|---|
| **EMERGING** | `share_R < 1.5%` **และ** `cagr_recent ≥ 25%/ปี` **และ** `share_ratio ≥ 1.8` **และ** มี ≥ 30 เรื่องในช่วง R |
| **HOT** | `share_R ≥ 1.5%` **และ** `slope_share > 0` |
| **DECLINING** | share ลดต่อเนื่อง ≥ 3 ปีท้าย |
| **STABLE** | อื่น ๆ |

เหตุผลของ threshold: เงื่อนไข `share_R < 1.5%` บังคับว่า "emerging ต้องยังเล็ก" (ถ้าใหญ่แล้วยังโต = HOT);
`min_articles_recent: 30` กัน noise จากหัวข้อจิ๋ว; `share_ratio` กันกรณี corpus ทั้งระบบโตเร็วจนทุกอย่างดูโต

### Emerging Score (0–100)

```
score = 100 × ( 0.35 × P(growth) + 0.25 × P(acceleration) + 0.20 × P(burst) + 0.20 × P(novelty) )
```

`P(·)` = percentile rank ภายในรอบรันนั้น (ทำให้ score เทียบกันได้ข้ามรอบ) — ใช้จัดอันดับหน้า "Emerging Themes" บนเว็บ

### Forecast

- โมเดล: `linear` (OLS), `poisson` (GLM), `prophet` (optional) — **เลือกโมเดลที่ดีสุดต่อ topic อัตโนมัติ**ด้วย backtest
  (train ถึง Y−3 → วัด MAPE 3 ปีสุดท้าย)
- ทำนายล่วงหน้า 2 ปี พร้อมช่วงความเชื่อมั่นจาก residual (±1.96σ) — present เป็น band ไม่ใช่เส้นเดียว
- กติกา: โมเดลไหน backtest แพ้ linear baseline จะไม่ถูกเลือก; topic ที่มีประวัติ < 6 ปีจะไม่ทำนาย

---

## การเชื่อมเข้าหน้าเว็บ Atlas

`output/atlas_data.json` มีโครง `{meta, groups, nodes, links}` — nodes แต่ละตัวมี
`x, y, r, color, th, en, articles, status, emerging_score, burst_years, forecast{...}`
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
  ingest.py       อ่าน+normalize+dedup (DOI → title hash, เก็บ record ที่ครบสุด)
  preprocess.py   ประกอบ doc_text = title + keywords + abstract
  embed.py        ApiEmbedder / LocalEmbedder + checkpoint ทุก 5,000 เรื่อง
  cluster.py      BERTopic 2 ชั้น (fine/coarse) + outlier → nearest centroid
  label.py        LLM ตั้งชื่อ topic (JSON schema, cache ตาม prompt_hash)
  topics_time.py  yearly series + backfill guard
  emerging.py     นิยาม Emerging ของ TCI + Kleinberg burst + novelty
  forecast.py     model selection ด้วย backtest MAPE
  layout.py       UMAP 2D บน centroid → ตำแหน่งบนแผนที่ + similarity edges
  export.py       atlas_data.json + CSVs + manifest
  pipeline.py     orchestrator CLI
tests/test_emerging.py   unit test นิยาม emerging (รัน: python3 tests/test_emerging.py)
scripts/validate_input.py  เช็คไฟล์ input ก่อนเสียงบ
data/synth.csv    ข้อมูลสังเคราะห์ตัวอย่างสำหรับทดลอง
```

## สิ่งที่ตั้งใจไม่ทำ (และทำเพิ่มได้ภายหลัง)

- co-citation edges — ต้องมี references ในข้อมูล; เพิ่มเป็น edge อีกชุดใน layout.py ได้
- author/affiliation network — metadata พร้อมอยู่แล้ว เพิ่ม aggregation step ได้
- incremental clustering แบบ online — ตอนนี้รันใหม่ทั้ง corpus ทุกไตรมาส (200K เรื่องทำได้สบาย)
