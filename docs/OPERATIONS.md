# OPERATIONS — คู่มือปฏิบัติการรายไตรมาส

> สำหรับผู้ดูแลระบบ: รอบรันปกติทำ 4 ขั้น — รับไฟล์ → รัน pipeline → นำเข้าเว็บ → ตรวจหน้าเว็บ
> เวลารวมโดยประมาณ (corpus ~200K): API mode 30–60 นาที / local mode 2–4 ชั่วโมง

## 0. สิ่งที่ต้องมี (ครั้งแรกครั้งเดียว)

- เครื่องที่รัน pipeline: Python 3.11+ (ใช้ `uv`; dev/CI ใช้ 3.12), RAM ≥ 16 GB (local mode อยากได้ GPU)
- เครื่อง build เว็บ: Node.js 24 (ตรงกับ CI) (เครื่องเดียวกันก็ได้)
- API key (env var เท่านั้น — ห้ามใส่ในไฟล์ใด ๆ): embedding แบบ api ใช้ `ATLAS_EMBED_API_KEY` (ดู §1A), LLM labeling แบบ api ใช้ `ATLAS_API_KEY` (ตั้งใน crontab env ถ้ารันอัตโนมัติ)
- `pipeline/config.yaml` (คัดลอกจาก `config.example.yaml` แล้วแก้ `input.path`)

## 1. รอบรันรายไตรมาส (runbook)

### ขั้น 1 — รับและวางคลังบทความ

ได้โฟลเดอร์ไฟล์ .md จาก ThaiJO ชุดใหม่ (หนึ่งไฟล์ต่อบทความ) → วางนอก git (เช่น `../corpus`; ข้อมูลจริงห้ามเข้า repo)
→ แก้ `config.yaml: input.path` ชี้โฟลเดอร์นั้น

### ขั้น 2 — รัน pipeline

```bash
cd pipeline
uv sync --extra local                      # หรือ --extra api (ครั้งแรก/เมื่อ lock เปลี่ยน)
uv run atlas profile /path/to/corpus --md ../logs/profile.md   # อ่านรายงานคุณภาพคลังก่อนเสมอ
uv run atlas run --config config.yaml      # ทั้งสาย (หรือ bash ../scripts/quarterly_run.sh ซึ่ง profile ให้ด้วย)
```

(`python -m atlas.pipeline` ยังใช้ได้เป็น alias ของ `atlas run` แต่เอกสารนี้ใช้ `atlas` CLI)

สิ่งที่ต้องดูตอนจบ:
- `[export] -> output/atlas_data.json` ขึ้นโดยไม่มี error
- เปิด `output/manifest.json` ดู `counts.total_articles` ว่าเพิ่มขึ้นสมเหตุสมผลจากรอบก่อน และตรวจ `ingest_errors` (ควรเป็น 0), `embedding_provider` (ต้องเป็น `local` หรือ `api` — ห้ามเผยแพร่ผลจาก `lite`), `n_labels_fallback`, `trimmed_years` / `as_of_year` (ปีที่ไม่ถูกนับในแนวโน้ม), `n_orgs_unverified`
- เปิด `output/emerging.csv` sort ตาม `emerging_score` — ลองอ่าน top 10 ว่า "มีเหตุผล" ไหม (sanity check ด้วยความรู้โดเมน)

### ขั้น 3 — นำเข้าเว็บ

```bash
bash scripts/import_atlas.sh        # copy output/atlas_data.json → web/public/data/ แล้ว build
```

สคริปต์จะ: ตรวจว่า JSON มี `meta/groups/nodes` ครบ → คัดลอกเข้า `web/public/data/atlas_data.json` → `npm run build` → รายงานผล

### ขั้น 4 — ตรวจหน้าเว็บ + เผยแพร่

- เปิดเว็บ (preview): badge ต้องขึ้น **"● ข้อมูลสดจาก pipeline · ข้อมูลถึงปี YYYY"** (ปี = last_complete_year ใหม่)
- คลิก 1 หัวข้อ EMERGING → แผงขวาต้องมีชิปสถานะ + กราฟคาดการณ์
- ลองสลับภาษา EN ดูคร่าว ๆ
- กด **「publish」** บน Kimi (หรือ deploy static ตามช่องทางของหน่วยงาน)

### ขั้น 5 — เก็บรอบรัน

```bash
mkdir -p runs/2026Q4 && cp pipeline/output/* runs/2026Q4/
```

เก็บ `output/` ทุกรอบไว้ — ใช้ทำ "diff รอบรัน" ในอนาคต และย้อนดู manifest ว่ารอบนั้นใช้นิยามแบบไหน

## 1A. รัน embedding ครั้งใหญ่ผ่าน API (ลงทุนครั้งเดียว)

ใช้ตอน embed คลังทั้งหมด (250K–500K เรื่อง) ครั้งแรกด้วย BGE-M3 (หรือโมเดลอื่น) ผ่าน endpoint แบบ OpenAI-compatible (`POST {base_url}/embeddings`)
เวกเตอร์เก็บถาวรใน `state/embeddings/<store>/` — รอบไตรมาสถัดไปจ่ายเฉพาะบทความใหม่/ที่ข้อความเปลี่ยน

**1) ตั้ง key — env var เท่านั้น ห้ามใส่ใน config หรือไฟล์ใด ๆ**

```powershell
$env:ATLAS_EMBED_API_KEY = "..."        # PowerShell: เฉพาะหน้าต่างนี้ (รวม --background ที่สั่งจากหน้าต่างนี้)
setx ATLAS_EMBED_API_KEY "..."          # จำถาวร — แล้วเปิดหน้าต่างใหม่ (หน้าต่างเดิมยังไม่เห็นค่า)
```

```bash
export ATLAS_EMBED_API_KEY=...          # bash
```

server ในองค์กรที่ไม่ใช้ key: ไม่ต้องตั้ง (ระบบส่ง request โดยไม่มี `Authorization`; ถ้า server ต้องใช้ key จะตอบ 401 และระบบบอกชื่อ env var ที่ต้องตั้ง)

**2) config** (`config.yaml` — key อื่นใช้ค่าเริ่มต้นได้ ดูคำอธิบายครบใน `config.example.yaml`)

```yaml
embedding:
  provider: api
  api:
    base_url: http://my-server:8080/v1    # self-hosted TEI/vLLM/Infinity/Ollama; DeepInfra: https://api.deepinfra.com/v1/openai
    api_key_env: ATLAS_EMBED_API_KEY      # "ชื่อ" env var — ไม่ใช่ตัว key
    model: BAAI/bge-m3                    # ตรวจชื่อโมเดลกับผู้ให้บริการ (บางเจ้าใช้ bge-m3)
    dimensions: null                      # bge-m3 = 1024 เสมอ — อย่าส่ง dimensions
    store_id: null                        # null → "api|BAAI/bge-m3|None" (ไม่ผูก base_url)
    concurrency: 4                        # request พร้อมกัน (429 บ่อย → ลด หรือตั้ง requests_per_minute)
    max_retries: null                     # null = retry error ชั่วคราวไม่จำกัด
```

**3) ตรวจก่อนรันจริง**

```bash
uv run atlas embed -c config.yaml --check      # ยิง 1 request: model, มิติ, latency — key/URL/โมเดลผิดรู้ทันที (exit 2)
uv run atlas embed -c config.yaml --dry-run    # นับ เอกสาร / cached / ต้อง embed / ตัวอักษร / ~token / จำนวน request — ไม่ยิง API
```

(`--dry-run` และการรันจริงจะ ingest + preprocess ให้ก่อนถ้ายังไม่มี `work/02_docs`)

**4) รัน**

```bash
uv run atlas embed -c config.yaml                 # หน้าต่างนี้: แถบความคืบหน้า + retry / ตัดข้อความ / เหตุการณ์ล่าสุด
uv run atlas embed -c config.yaml --background    # เบื้องหลัง: พิมพ์ PID แล้วปิดหน้าต่างได้เลย; log อยู่ที่ <store>/run.log
```

- server ล่ม / 5xx / 429 / 408 / timeout / เน็ตหลุด / คำตอบผิดรูป → **รอแล้วลองใหม่ไม่จำกัด** (exponential backoff + jitter สูงสุด `backoff_max` = 5 นาที/ครั้ง, เคารพ `Retry-After`) — ไม่ต้องเฝ้า
- key ผิด (401/403), base_url หรือโมเดลผิด (404), request ไม่ถูกต้อง (400/422 อื่น) → **หยุดทันที** (exit 2) พร้อมบอกวิธีแก้ — ไม่วนเปล่า
- server บอกว่าใหญ่เกิน (413 หรือ 400/422 ที่พูดถึง token/length) → แบ่ง batch ครึ่งอัตโนมัติ; ข้อความเดี่ยวยาวเกิน → ตัดครึ่งซ้ำได้ถึง `min_text_chars` (นับใน `truncated`)

**5) ดูสถานะ** (เปิดอีกหน้าต่างได้ระหว่างรัน)

```bash
uv run atlas status -c config.yaml               # = atlas embed-status
```

แสดง: สถานะ (`running` / `backing_off` = รอ server / `stopped` / `interrupted` = process ตายกลางคัน / `done` / `failed`), PID ยังทำงานไหม, ความคืบหน้า, อัตรา, ETA, จำนวน retry/ตัดข้อความ, error ล่าสุด, จำนวนเวกเตอร์ใน store, journal ที่รอ recover — อ่านจาก `progress.json` (อัปเดตทุก ~5 วินาที)

**6) หยุด**

- หน้าต่างที่รันอยู่: **Ctrl-C ครั้งเดียว** = หยุดส่งงานใหม่ รอ request ที่ค้าง บันทึกทุกอย่าง (exit 130); กดซ้ำ = ไม่รอ request ที่ค้าง (ข้อความเหล่านั้นถูกส่งใหม่รอบหน้า)
- รันเบื้องหลัง: `uv run atlas embed-stop -c config.yaml` (สถานะเป็น `stopped`)
- ฉุกเฉิน — ปิดหน้าต่าง / `taskkill /F /PID <pid>` / ไฟดับ: เสียได้แค่ request ที่ยังไม่ตอบ (≤ 2 × `concurrency` batch) เพราะทุก batch ที่ได้ผลถูกเขียนลง `journal.bin` ทันที

**7) ทำต่อ = รันคำสั่งเดิมอีกครั้ง**

```bash
uv run atlas embed -c config.yaml
```

ระบบอ่าน `journal.bin` คืนเข้า store (`[embed] recovered N vectors from journal`), ยึด `run.lock` ที่ค้างจาก process ที่ตายแล้ว (PID ตาย หรือไม่มี heartbeat นานกว่า `lock_stale_seconds`) แล้ว embed เฉพาะที่ store ยังไม่มี — ไม่จ่ายซ้ำ
เสร็จแล้วรัน `uv run atlas run -c config.yaml` ตามปกติ — ขั้น embed จะขึ้น `0 to embed` และใช้เวกเตอร์จาก store

**8) ย้าย server / เปลี่ยนโมเดล**

- `store_id` ไม่ผูก `base_url`: ย้ายไป server ที่ให้บริการ **โมเดลเดียวกันด้วยการตั้งค่าเดียวกัน** (ไม่ quantize/ตัดข้อความ/normalize ต่างไป) → แก้แค่ `base_url` ใช้ store เดิมต่อได้
- server ใหม่ให้เวกเตอร์ต่างไป (โมเดล, quantization, มิติ) → ตั้ง `store_id` ใหม่ (เช่น `bge-m3-deepinfra`) = store ใหม่, embed ใหม่ทั้งคลัง — ห้ามผสมเวกเตอร์ต่างที่มาใน store เดียว
- ถ้ามิติไม่ตรง store เดิม ระบบหยุดเอง: `store เดิมเป็นมิติ X แต่ server ตอบ Y — ตั้ง store_id ใหม่`

**exit codes**: 0 เสร็จ · 1 ล้ม (เช่น ตั้ง `max_retries` แล้ว retry หมด) · 2 config/error ถาวร · 3 มีอีก process รัน store เดียวกันอยู่ · 130 ถูกหยุด (ทำต่อได้)

## 2. ตั้ง cron (ตัวเลือก — ยังต้องมีคนกดตรวจขั้น 3–4)

```cron
# 01:00 วันที่ 1 ของ เดือน 1,4,7,10
0 1 1 1,4,7,10 * cd /path/to/tci-research-atlas && bash scripts/quarterly_run.sh pipeline/config.yaml >> logs/quarterly.log 2>&1
```

## 3. Troubleshooting

| อาการ | สาเหตุที่พบบ่อย | วิธีแก้ |
|---|---|---|
| `atlas profile` ฟ้องไฟล์อ่านไม่ได้/ฟิลด์ว่างมาก | รูปแบบ .md จาก ThaiJO เปลี่ยน (หรือใช้ `input.format: table` แล้ว mapping คอลัมน์ผิด) | ดูรายงาน profile; ถ้าเป็นตาราง แก้ `input.columns` ใน config.yaml |
| embed ค้าง/ล่มกลางทาง/ปิดหน้าต่าง | API timeout, OOM, process ถูกฆ่า | รันคำสั่งเดิมได้เลย — ทุก batch ที่ได้ผลอยู่ใน `journal.bin` ทันที (เข้า store ทุก `checkpoint_every`) ทำต่อจากจุดเดิมโดยไม่จ่ายซ้ำ (§1A) |
| `atlas embed` exit 2 | key ไม่ได้ตั้ง/ผิด (401/403), `base_url`/`model` ผิด (404), request ไม่ถูกต้อง (400/422), มิติไม่ตรง store เดิม, ข้อความยาวเกินแม้ตัดถึง `min_text_chars` | อ่านข้อความ error (บอกวิธีแก้ทั้งไทย/อังกฤษ) → แก้ env var/config → `atlas embed --check` → รันใหม่ |
| `atlas embed` exit 3 `กำลังรันอยู่ (PID …)` | มีอีก process รัน store เดียวกันอยู่ | `atlas status` ดู PID/ความคืบหน้า; ถ้า process นั้นตายแล้ว lock ถูกยึดต่ออัตโนมัติ (PID ตาย หรือ heartbeat เก่ากว่า `lock_stale_seconds`) |
| `atlas embed` exit 130 | Ctrl-C หรือ `atlas embed-stop` | ปกติ — รันคำสั่งเดิมเพื่อทำต่อ |
| retry ไม่จบ / สถานะ `backing_off` นาน | server ปลายทางล่ม คิวเต็ม หรือติด rate limit | `atlas status` → `last error` (เช่น `HTTP 503`, `URLError: ... refused`) แล้วแก้ที่ server — runner ทำต่อเองเมื่อ server กลับมา; 429 บ่อย → ลด `concurrency` หรือตั้ง `requests_per_minute`; ไม่อยากรอไม่จำกัด → ตั้ง `max_retries` |
| สถานะ `interrupted` | process ตายกลางคัน (ปิดหน้าต่าง/ไฟดับ/taskkill) | รันคำสั่งเดิม — journal ถูก recover อัตโนมัติ |
| topic ออกมาใหญ่เกิน/เล็กเกิน | hdbscan_min_cluster_size ไม่เหมาะ | ปรับ `clustering.fine.hdbscan_min_cluster_size` (หรือ `clustering.n_groups` สำหรับกลุ่มใหญ่) แล้วรัน `uv run atlas run -c config.yaml -s cluster -s label -s series -s emerging -s forecast -s layout -s export` |
| ทุกหัวข้อขึ้น DECLINING | ปีล่าสุดข้อมูลยังไม่ครบ แต่ backfill guard ไม่ตัด (เช่น รันย้อนหลังด้วย `as_of_year` ผิด) | ดู log `[series] … looks incomplete` และ `meta.trimmed_years`; ตรวจ `emerging.as_of_year` (null = ปีปัจจุบัน) หรือตั้ง `emerging.min_year_complete` เอง |
| `meta.trimmed_years` มีหลายปี / `last_complete_year` ต่ำกว่าที่คิด | ปีที่กำลังดำเนินอยู่ไม่นับเสมอ, ฉบับลงวันที่ล่วงหน้า, หรือปีล่าสุดยอด < 60% ของ median 3 ปีก่อน (ตัดได้สูงสุด `backfill_max_trim` = 2 ปี) | ปกติ — ดูตาราง "Articles per year" ใน profile; ถ้าข้อมูลครบจริงแล้ว ตั้ง `emerging.min_year_complete` |
| log ขึ้น `[ingest] WARNING: N files could not be read or parsed` | ไฟล์เสีย/ถูกล็อก/สิทธิ์ไม่พอ, โฟลเดอร์ชื่อลงท้าย `.md`, หรือ layout ที่ parser ไม่รองรับ | ดู `work/01_ingest_errors` (path + error) หรือส่วน "Files with errors" ใน profile; แก้/ลบไฟล์แล้วรัน `-s ingest` ใหม่ — ไฟล์ที่มีไบต์เพี้ยนเล็กน้อยไม่ถูกข้าม แต่ได้ flag `decode_replaced` |
| log ขึ้น `[embed] WARNING: embedding.provider is 'lite'` | config ใช้ `lite` (สำหรับ CI) กับคลังจริง | เปลี่ยนเป็น `embedding.provider: local` (หรือ `api`) แล้วรันใหม่ — อย่าเผยแพร่ผลจาก lite |
| `ValueError: HDBSCAN found no clusters in N documents` | `hdbscan_min_cluster_size` ใหญ่เกินคลัง หรือ embedding ผิดปกติ (เช่น lite/โมเดลผิด) | ลด `clustering.fine.hdbscan_min_cluster_size` / `hdbscan_min_samples`; ตรวจ `work/03_meta.json` (model_id) — pipeline จะไม่รวมทุกอย่างเป็นหัวข้อเดียวเงียบ ๆ อีกแล้ว (ยกเว้นคลังจิ๋ว < 2 × min_cluster_size) |
| label เป็นภาษาอังกฤษหมด | โมเดลไม่ถนัดไทย | เปลี่ยน `labeling.api.model` (เช่น typhoon / gpt-4o / gemini-2.0-flash) — cache_key (hash ของ model + prompt) เปลี่ยน เฉพาะ label จะถูกสร้างใหม่ |
| หน้าเว็บยังเป็นข้อมูลเก่า | ลืม build ใหม่ หรือ browser cache | `import_atlas.sh` ต้องรันจนจบ (มี build ในตัว); hard-refresh |
| หน้าเว็บ badge ขึ้น "○ ข้อมูลตัวอย่าง" | JSON ไม่ถูกวาง/โหลดไม่ได้ | เช็ก `web/public/data/atlas_data.json` มีจริง และ deploy มีไฟล์นี้ด้วย |
| forecast ไม่มีบาง topic | ประวัติ < 6 ปี หรือไม่ผ่าน skill gate (ดีกว่า naive ไม่พอ) | เป็นเรื่องปกติ (`forecast.min_history_years`, `forecast.min_skill`); ใน JSON จะเป็น `forecast: null` + `forecast_uncertain` |
| หัวข้อเกือบทั้งหมดเป็น LOW_DATA | corpus เล็ก/ช่วงปีสั้น หรือ `min_articles_recent` สูงไป | ตรวจรายงาน profile; ปรับ `emerging.min_articles_recent` เฉพาะเมื่อมีเหตุผล (กระทบนิยาม ต้อง bump `definition_version`) |
| หัวข้อขึ้น WATCH เยอะ | วารสารเข้ามาอัปโหลดย้อนหลังเป็นชุด (journal-entry bias) | ดู profile หัวข้อ "วารสารที่อัปโหลดย้อนหลัง"; WATCH คือสัญญาณเตือน ไม่ใช่ข้อสรุป |
| `provider: off` ใน YAML ไม่ทำงานตามคาด | YAML อ่าน `off` เปล่า ๆ เป็น false | ใส่เครื่องหมายคำพูด: `provider: "off"` |
| Windows แสดงภาษาไทยเพี้ยนใน console | console เป็น cp1252 | ทั้ง `uv run atlas …` และ `python -m atlas.pipeline` ตั้ง stdout/stderr เป็น UTF-8 ให้แล้ว (รวมตอน redirect ลงไฟล์) |
| อยากปรับนิยาม emerging | — | แก้ `config.yaml → emerging:` + `docs/EMERGING_SPEC.md` + `tests/test_emerging.py` พร้อมกัน แล้วรัน `uv run atlas run -c config.yaml -s emerging -s forecast -s export` (ฟรี ไม่แตะ API) |

## 4. งบประมาณโดยประมาณต่อรอบ (corpus ~200K เรื่อง)

| รายการ | API mode | Local mode |
|---|---|---|
| Embedding รอบแรก | ~$10–20 | ฟรี (GPU 2–4 ชม.) |
| Embedding รอบต่อไป | เฉพาะบทความใหม่/ที่ข้อความเปลี่ยน (เวกเตอร์เดิมอยู่ใน `state/embeddings`) | ฟรี |
| LLM labeling | ~$1–3 (เฉพาะ topic ที่ยังไม่มีใน cache) | ฟรี (ถ้ารันเอง) |
| **รวม/ไตรมาส** | **~$15–25** | **~0** |

## 5. การย้อนกลับ (rollback)

- เว็บบน Kimi: ใช้ version card ย้อนกลับเวอร์ชันก่อนหน้าได้ทันที
- ข้อมูล: คัดลอก `atlas_data.json` จาก `runs/<ไตรมาสก่อน>/` กลับมาแล้ว `import_atlas.sh` ใหม่
