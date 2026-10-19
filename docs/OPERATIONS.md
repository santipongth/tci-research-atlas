# OPERATIONS — คู่มือปฏิบัติการรายไตรมาส

> สำหรับผู้ดูแลระบบ: รอบรันปกติทำ 4 ขั้น — รับไฟล์ → รัน pipeline → นำเข้าเว็บ → ตรวจหน้าเว็บ
> เวลารวมโดยประมาณ (corpus ~200K): API mode 30–60 นาที / local mode 2–4 ชั่วโมง

## 0. สิ่งที่ต้องมี (ครั้งแรกครั้งเดียว)

- เครื่องที่รัน pipeline: Python 3.11+ (ใช้ `uv`; dev/CI ใช้ 3.12), RAM ≥ 16 GB (local mode อยากได้ GPU)
- เครื่อง build เว็บ: Node.js 24 (ตรงกับ CI) (เครื่องเดียวกันก็ได้)
- API key (env var เท่านั้น — ห้ามใส่ในไฟล์ใด ๆ): embedding แบบ api ใช้ `ATLAS_EMBED_API_KEY` (ดู §1A), LLM ใช้ `ATLAS_LLM_API_KEY` (ดู §6; ใช้ key เดียวกันได้), OpenAlex ใช้ `OPENALEX_API_KEY` (ทางเลือก ดู §9) — ตั้งใน crontab env ถ้ารันอัตโนมัติ
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

ถ้าใช้ LLM (`labeling.provider: llm` / `narrative.provider: llm`): ก่อนรันจริง `uv run atlas llm -c config.yaml --check` (ปลายทางตอบ JSON + ภาษาไทยไม่เพี้ยน) และ `--dry-run` (จำนวน call, token, ค่าใช้จ่ายโดยประมาณ, งบที่เหลือ) — ดูหัวข้อ 6
หลังรัน: `uv run atlas validate -c config.yaml` ต้องได้ exit 0 (1 = มีคำเตือน อ่านก่อนเผยแพร่, 2 = ห้ามเผยแพร่)

สิ่งที่ต้องดูตอนจบ:
- `[export] -> output/atlas_data.json` ขึ้นโดยไม่มี error
- เปิด `output/manifest.json` ดู `counts.total_articles` ว่าเพิ่มขึ้นสมเหตุสมผลจากรอบก่อน และตรวจ `ingest_errors` (ควรเป็น 0), `embedding_provider` (ต้องเป็น `local` หรือ `api` — ห้ามเผยแพร่ผลจาก `lite`), `n_labels_fallback`, `trimmed_years` / `as_of_year` (ปีที่ไม่ถูกนับในแนวโน้ม), `n_orgs_unverified`
- เปิด `output/emerging.csv` sort ตาม `emerging_score` — ลองอ่าน top 10 ว่า "มีเหตุผล" ไหม (sanity check ด้วยความรู้โดเมน)

### ขั้น 3 — นำเข้าเว็บ

```bash
cd pipeline
uv run atlas validate -c config.yaml                         # 0 = ผ่าน
uv run atlas publish  -c config.yaml --site ../web/dist      # วาง data/<release>/ + data/latest.json + atlas-offline.html
```

- เว็บ v2 อ่าน `data/latest.json` ตอนเปิดหน้า → **ไม่ต้อง build เว็บใหม่ทุกไตรมาส** แค่คัดลอกโฟลเดอร์ `data/` ใหม่ขึ้น host (รอบเก่ายังอยู่ใน `data/` ให้เทียบได้)
- **รอบข้อมูลผูกกับ work_dir**: ขั้น `cluster` เลือกรอบ (`pipeline.release` หรือไตรมาสของวันที่รันเมื่อเป็น null) แล้วบันทึกรอบ + เวลา snapshot ไว้ใน `work/04_topics_meta.json`; ทุกขั้นหลังจากนั้น (label, narrate, layout, export) เขียนได้เฉพาะรอบนั้น — ถ้าแก้ `pipeline.release` เป็นรอบอื่นแล้วรันต่อ จะถูกปฏิเสธ (exit 2: "work_dir was clustered for 2026Q4 but pipeline.release is 2027Q1 — re-run from cluster, or set pipeline.release: 2026Q4") จึงไม่มีรอบผี/การเขียนทับรอบเก่า; ถ้า `pipeline.release: null` การรันต่อภายหลัง (แม้ข้ามไตรมาส) รวมถึง `atlas validate` / `atlas publish` จะใช้รอบที่บันทึกไว้ ไม่ใช่ไตรมาสของวันนี้ · `as_of_year` (เมื่อเป็น null), เพดานเดือนของ nowcast และ `generated_at` ใช้เวลา snapshot เดียวกัน — export รอบเดิมซ้ำได้ไฟล์เหมือนเดิมทุกไบต์
- **รอบก่อนหน้าตามมาด้วย**: publish คัดลอกรอบก่อนหน้าตามสาย `previous_release` (รอบก่อน → รอบก่อนนั้น …) ที่ site ยังไม่มี จาก `output/data/` ให้เอง (เช่น หลัง `npm run build` ล้าง `dist/data`) เพื่อให้เว็บแสดงการเปลี่ยนแปลง (Δ) ได้ — ไม่เขียนทับโฟลเดอร์รอบที่มีอยู่บน site แล้ว; ถ้าหารอบก่อนหน้าไม่พบทั้งในเครื่องและบน site จะเตือน (publish ต่อได้ แต่เว็บไม่มี Δ เทียบกับรอบนั้น)
- **`latest.json` ชี้รอบใหม่สุดเสมอ**: publish รอบที่เก่ากว่ารอบที่มีอยู่บน site (เช่น แก้แล้ว publish 2026Q3 ซ้ำหลัง 2026Q4) จะวางโฟลเดอร์ให้แต่ไม่ย้าย `latest.json`/`atlas-offline.html` (มีคำเตือน) — ต้องการย้ายจริงใช้ `--set-latest`; export ก็ไม่ย้าย `output/data/latest.json` ไปรอบที่เก่ากว่า
- **โฟลเดอร์รอบต้องคงชื่อเดิม**: `atlas validate` เป็น error เมื่อ `manifest.release` ไม่ตรงกับชื่อโฟลเดอร์ (ห้ามเปลี่ยนชื่อ/ก๊อปปี้เป็นชื่ออื่น) และเตือน (ข้าม diff) เมื่อไม่พบโฟลเดอร์ของรอบก่อนหน้าที่ manifest อ้างถึง; ชื่อรอบต้องเป็นรูป YYYYQn (เช่น `2026Q4`) — ชื่อแปลก ๆ อย่าง `../x` ถูกปฏิเสธ
- `atlas-offline.html` = เว็บทั้งหน้าในไฟล์เดียว (ส่งอีเมล/เปิดโดยไม่ต่อเน็ตได้) — สร้างด้วย Python จาก `offline-template.html` ของ web build; ถ้าโฟลเดอร์เว็บยังไม่มีไฟล์นี้ publish จะเตือนแล้วข้ามไป
- ต้องการไฟล์แนบ GitHub Release ด้วย: เติม `--tarball` (ได้ tar.gz ที่ทำซ้ำได้ + sha256 + release notes และคำสั่ง `gh release create` ให้คนรันเอง — โปรแกรมไม่อัปโหลดเอง)
- ทางลัด (จาก root): `bash scripts/import_atlas.sh` = `npm run build` ใน web แล้ว `atlas publish --site web/dist`

### ขั้น 4 — ตรวจหน้าเว็บ + เผยแพร่

- วางรอบใหม่ลงโฟลเดอร์เว็บด้วย `uv run atlas publish --site web/dist` (หรือ `bash scripts/import_atlas.sh`) แล้วเปิด preview (`npm run preview` ใน `web/`)
- หน้า `/overview` ต้องแสดงชื่อรอบใหม่ ข้อความ "ข้อมูลถึงปี YYYY" ตรงกับ `last_complete_year` และตัวเลข Δ เทียบรอบก่อน (ถ้าโฟลเดอร์รอบก่อนยังอยู่บน site; ถ้าไม่อยู่จะมีบรรทัด "ไม่พบข้อมูลรอบก่อนหน้า")
- เปิด `/emerging` → แท็บ EMERGING ต้องมีรายการ คลิก 1 หัวข้อ → หน้าหัวข้อต้องมีชิปสถานะ (สัญลักษณ์ + สี + ข้อความ) และกราฟแนวโน้มพร้อมตาราง
- สลับภาษา TH/EN และเปิดโหมดมืดดูคร่าว ๆ; ถ้าเป็นข้อมูลสังเคราะห์ ต้องเห็นป้าย "ข้อมูลตัวอย่าง" ทุกหน้า
- เผยแพร่ข้อมูลจริง: `uv run atlas publish --site web/dist` แล้ว deploy โฟลเดอร์ `web/dist` ขึ้น host ของหน่วยงาน (static host ใดก็ได้) — การ push ขึ้น GitHub **ไม่** deploy อะไรเอง
- workflow `.github/workflows/pages.yml` ใช้สำหรับ **เว็บสาธิต** เท่านั้น: ผู้ดูแลกดรันเอง (Actions → Pages → Run workflow) ระบบจะ build เว็บพร้อม **ข้อมูลตัวอย่าง (สังเคราะห์)** ที่มีป้าย "ข้อมูลตัวอย่าง" ทุกหน้าและตั้ง noindex — สคริปต์ `stage:demo` ปฏิเสธการเขียนทับโฟลเดอร์ที่มี release จริง

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
- key ผิด (401/403), base_url หรือโมเดลผิด (404), request ไม่ถูกต้อง (400/422 อื่น), **เครดิต/โควตาหมด** (402 หรือ 429 ที่บอก `insufficient_quota`/billing — แต่ 429 ที่พูดถึง rate limit ต่อนาที/วัน ยังรอแล้วลองใหม่), base_url ถูก **redirect** (3xx — ไม่ follow เพื่อไม่ส่ง key ไปที่อื่น; ระบบบอก URL ปลายทางให้ตั้งเป็น base_url) → **หยุดทันที** (exit 2) พร้อมบอกวิธีแก้ — ไม่วนเปล่า
- server ตอบผิดรูปแบบ **แบบเดิมซ้ำ 3 ครั้ง** สำหรับ batch เดียว → แบ่ง batch; ถ้าเหลือข้อความเดียวแล้วยังผิด → หยุด (exit 2) พร้อมบอกปัญหา (ไม่วนไม่รู้จบกับคำตอบเสียแบบเดิม)
- ส่ง key ผ่าน `http://` ไปเครื่องที่ไม่ใช่ localhost → ขึ้น WARNING หนึ่งครั้ง (ควรใช้ `https://` เว้นแต่เป็นเครือข่ายภายในที่เชื่อถือได้)
- `--background` เฝ้า process ลูก ~3 วินาที: ถ้าตายทันที (config ผิด, 401 ใน request แรก, มีอีกตัวรันอยู่) จะพิมพ์ exit code + ท้าย `run.log` และจบด้วย exit code นั้น — ไม่ใช่บอกว่า "รันแล้ว"
- server บอกว่าใหญ่เกิน (413 หรือ 400/422 ที่พูดถึง token/length) → แบ่ง batch ครึ่งอัตโนมัติ; ข้อความเดี่ยวยาวเกิน → ตัดครึ่งซ้ำได้ถึง `min_text_chars` (นับใน `truncated`)

**5) ดูสถานะ** (เปิดอีกหน้าต่างได้ระหว่างรัน)

```bash
uv run atlas status -c config.yaml               # = atlas embed-status
```

แสดง: สถานะ (`running` / `backing_off` = รอ server / `hung` = process ยังอยู่แต่ไม่มี heartbeat นานกว่า `lock_stale_seconds` / `stopped` / `interrupted` = process ตายกลางคัน / `done` / `failed`), PID ยังทำงานไหม (ตรวจเวลาเริ่ม process ด้วย จึงไม่สับสนเมื่อ Windows นำ PID เดิมไปใช้ใหม่), ความคืบหน้า, อัตรา, ETA, จำนวน retry/ตัดข้อความ, error ล่าสุด, จำนวนเวกเตอร์ใน store, journal ที่รอ, จำนวนข้อความที่ถูกตัดสะสม (`truncated.parquet`) — ระหว่างรัน ตัวเลขเหล่านี้มาจาก `progress.json` (อัปเดตทุก ~5 วินาที) **status ไม่เปิดไฟล์ store ของงานที่กำลังรัน** จึงสั่งดูถี่แค่ไหนก็ไม่ขวาง checkpoint บน Windows

**6) หยุด**

- หน้าต่างที่รันอยู่: **Ctrl-C ครั้งเดียว** = หยุดส่งงานใหม่ รอ request ที่ค้างให้ตอบ บันทึกทุกอย่าง แล้วออก (exit 130); **กดอีกครั้ง** = ไม่รอ request ที่ค้าง: บันทึกเฉพาะที่ได้ผลแล้วลง store แล้วออกทันที (exit 130 — ข้อความของ request ที่ทิ้งไป จะถูกส่งใหม่รอบหน้า) — บน Windows การกดสองครั้งติดกันเร็วมากอาจนับเป็นครั้งเดียว: ถ้ายังไม่ออก ให้รอสักครู่แล้วกดอีกครั้ง
- **หยุดด้วย Ctrl-C เท่านั้น อย่าใช้ Ctrl-Break**: Ctrl-Break ทำให้ `uv run` จบทันที (หน้าต่างกลับมาที่ prompt) ขณะที่ Python ยังหยุดงานต่ออยู่เบื้องหลัง — ดูสถานะด้วย `atlas status` แล้วรอให้ขึ้น `stopped` ก่อนรันใหม่
- รันเบื้องหลัง: `uv run atlas embed-stop -c config.yaml` (สถานะเป็น `stopped`) — สั่งได้แม้งานยังอยู่ช่วง ingest: จะหยุดทันทีที่ถึงขั้น embed (คำขอหยุดที่เก่ากว่าเวลาเริ่ม process ถูกทิ้งเอง)
- ฉุกเฉิน — ปิดหน้าต่าง / `taskkill /F /PID <pid>` / process crash: เสียได้แค่ request ที่ยังไม่ตอบ (≤ 2 × `concurrency` batch) เพราะทุก batch ที่ได้ผลถูกเขียนลง `journal.bin` ทันที
- **ไฟดับ / เครื่องดับกะทันหัน**: เสียเพิ่มได้อีก**ไม่เกินราว 10 วินาทีล่าสุด**ของผลที่อยู่ใน `journal.bin` (journal fsync ลงดิสก์อย่างช้าทุก 10 วินาที; ส่วนที่เข้า store แล้วถูก fsync ก่อนแทนที่ index เสมอ) — รันคำสั่งเดิมแล้วระบบจ่ายเฉพาะส่วนที่หายนั้นใหม่

**7) ทำต่อ = รันคำสั่งเดิมอีกครั้ง**

```bash
uv run atlas embed -c config.yaml
```

ระบบอ่าน `journal.bin` คืนเข้า store (`[embed] recovered N vectors from journal`) แล้ว embed เฉพาะที่ store ยังไม่มี — ไม่จ่ายซ้ำ. การกันรันซ้อนใช้ OS lock บนไฟล์ `<store>/.lock` ที่ process ถือไว้ตลอดการรัน: process ตาย (ปิดหน้าต่าง/taskkill/crash) → OS ปล่อย lock ทันที รันใหม่ได้เลยไม่ต้องรอ; process ที่ยังอยู่ (แม้ค้าง) **ไม่ถูกแย่ง lock เด็ดขาด** — `run.lock` เป็นแค่ข้อมูลให้ `atlas status` อ่าน
เสร็จแล้วรัน `uv run atlas run -c config.yaml` ตามปกติ — ขั้น embed จะขึ้น `0 to embed` และใช้เวกเตอร์จาก store

**8) ย้าย server / เปลี่ยนโมเดล**

- `store_id` ไม่ผูก `base_url`: ย้ายไป server ที่ให้บริการ **โมเดลเดียวกันด้วยการตั้งค่าเดียวกัน** (ไม่ quantize/ตัดข้อความ/normalize ต่างไป) → แก้แค่ `base_url` ใช้ store เดิมต่อได้
- server ใหม่ให้เวกเตอร์ต่างไป (โมเดล, quantization, มิติ) → ตั้ง `store_id` ใหม่ (เช่น `bge-m3-deepinfra`) = store ใหม่, embed ใหม่ทั้งคลัง — ห้ามผสมเวกเตอร์ต่างที่มาใน store เดียว
- ถ้ามิติไม่ตรง store เดิม ระบบหยุดเอง: `store เดิมเป็นมิติ X แต่ server ตอบ Y — ตั้ง store_id ใหม่`

**exit codes**: 0 เสร็จ · 1 ล้ม (เช่น ตั้ง `max_retries` แล้ว retry หมด; หรือบันทึกลง store ตอนจบไม่ได้ เช่น ดิสก์เต็ม หรือมีโปรแกรมเปิด `index.parquet` ค้าง — ผลอยู่ใน `journal.bin` ครบ รันคำสั่งเดิมอีกครั้ง) · 2 config/error ถาวร (key, URL, redirect, โมเดล, โควตาหมด, มิติไม่ตรง, ระบบไฟล์ล็อกไฟล์ไม่ได้) · 3 มี process อื่นถือ store นี้อยู่ (กำลังรัน หรือ hung) · 130 ถูกหยุด (ทำต่อได้)

## 2. ตั้ง cron (ตัวเลือก — ยังต้องมีคนกดตรวจขั้น 3–4)

```cron
# 01:00 วันที่ 1 ของ เดือน 1,4,7,10
0 1 1 1,4,7,10 * cd /path/to/tci-research-atlas && bash scripts/quarterly_run.sh pipeline/config.yaml >> logs/quarterly.log 2>&1
```

## 3. Troubleshooting

| อาการ | สาเหตุที่พบบ่อย | วิธีแก้ |
|---|---|---|
| `atlas profile` ฟ้องไฟล์อ่านไม่ได้/ฟิลด์ว่างมาก | รูปแบบ .md จาก ThaiJO เปลี่ยน (หรือใช้ `input.format: table` แล้ว mapping คอลัมน์ผิด) | ดูรายงาน profile; ถ้าเป็นตาราง แก้ `input.columns` ใน config.yaml |
| embed ค้าง/ล่มกลางทาง/ปิดหน้าต่าง | API timeout, OOM, process ถูกฆ่า | รันคำสั่งเดิมได้เลย — ทุก batch ที่ได้ผลอยู่ใน `journal.bin` ทันที (เข้า store ทุก `checkpoint_every`) ทำต่อจากจุดเดิมโดยไม่จ่ายซ้ำ; ไฟดับอาจเสียผล ~10 วินาทีล่าสุด (§1A) |
| `atlas embed` exit 2 | key ไม่ได้ตั้ง/ผิด (401/403), `base_url`/`model` ผิด (404), request ไม่ถูกต้อง (400/422), base_url ถูก redirect (3xx), เครดิต/โควตาหมด (402, 429 `insufficient_quota`/billing), server ตอบผิดรูปแบบเดิมซ้ำกับข้อความเดียว, มิติไม่ตรง store เดิม, ข้อความยาวเกินแม้ตัดถึง `min_text_chars`, `base_url` ผิดรูป (port/scheme) | อ่านข้อความ error (บอกวิธีแก้ทั้งไทย/อังกฤษ) → แก้ env var/config (redirect: ตั้ง base_url เป็น URL ปลายทางที่แสดง; โควตา: เติมเงินกับผู้ให้บริการ) → `atlas embed --check` → รันใหม่ |
| `atlas embed` exit 2 `this filesystem does not support file locking` | `state_dir` อยู่บน network share / ระบบไฟล์ที่ล็อกไฟล์ไม่ได้ (กันรันซ้อนไม่ได้) | ย้าย `pipeline.state_dir` ไปไว้บนดิสก์ในเครื่อง |
| `atlas embed` exit 1 `could not save into the store … kept in journal.bin` | ตอนจบบันทึกลง store ไม่ได้: ดิสก์เต็ม/I-O error หรือมีโปรแกรมอื่นเปิด `index.parquet` ค้างนานเกิน 1 นาที | แก้สาเหตุ (เพิ่มพื้นที่ดิสก์, ปิดโปรแกรมนั้น หรือยกเว้น `state/` จาก antivirus/backup) แล้วรันคำสั่งเดิม — journal ถูก replay ไม่จ่ายซ้ำ |
| `atlas embed` exit 3 `กำลังรันอยู่ (PID …)` หรือ `hung` | มี process อื่นถือ OS lock ของ store นี้อยู่ (lock หลุดเองทันทีเมื่อ process ตาย ไม่ต้องรอ) | `atlas status` ดู PID/ความคืบหน้า; ถ้าตั้งใจให้รันตัวเดียวก็รอให้จบ หรือ `atlas embed-stop`; ถ้าเป็น `hung` ดูหัวข้อถัดไป |
| สถานะ `hung` (process ยังอยู่แต่ไม่มี heartbeat นานกว่า `lock_stale_seconds`) | main thread ค้าง เช่น หน้าต่าง console ถูกคลิกค้าง (QuickEdit หยุดการพิมพ์), ดิสก์/แชร์ค้าง, เครื่อง sleep | กด Esc/Enter ในหน้าต่างนั้นถ้าเป็น QuickEdit; ถ้ายังไม่ขยับ `taskkill /F /PID <pid>` แล้วรันคำสั่งเดิม (journal recover ให้) — ระบบไม่แย่ง lock จาก process ที่ยังอยู่เอง |
| `atlas embed` exit 130 | Ctrl-C หรือ `atlas embed-stop` | ปกติ — รันคำสั่งเดิมเพื่อทำต่อ |
| กด Ctrl-Break แล้ว prompt กลับมาทันที แต่ `atlas status` ยังขึ้น running | Ctrl-Break ปิด `uv run` ทันที ขณะที่ Python ยังหยุดงานอยู่เบื้องหลัง | รอจน `atlas status` ขึ้น `stopped`/`interrupted` แล้วค่อยรันใหม่; ครั้งหน้าใช้ Ctrl-C |
| retry ไม่จบ / สถานะ `backing_off` นาน | server ปลายทางล่ม คิวเต็ม หรือติด rate limit | `atlas status` → `last error` (เช่น `HTTP 503`, `URLError: ... refused`) แล้วแก้ที่ server — runner ทำต่อเองเมื่อ server กลับมา; 429 บ่อย → ลด `concurrency` หรือตั้ง `requests_per_minute`; ไม่อยากรอไม่จำกัด → ตั้ง `max_retries` |
| log/status ขึ้น `checkpoint postponed N times — something holds index.parquet` | โปรแกรมอื่น (antivirus, backup, ตัวเปิดไฟล์) เปิด `index.parquet` ค้างไว้นาน | ไม่ต้องทำอะไร — ผลอยู่ใน `journal.bin` และเข้า store เมื่อไฟล์ว่าง (หลังเลื่อน 3 ครั้งติด ระบบจะไม่เขียน shard ซ้ำจนกว่าไฟล์จะว่างจริง); ถ้าเกิดบ่อย ให้ยกเว้นโฟลเดอร์ `state/` จากการสแกน |
| สถานะ `interrupted` | process ตายกลางคัน (ปิดหน้าต่าง/ไฟดับ/taskkill) | รันคำสั่งเดิม — journal ถูก recover อัตโนมัติ |
| topic ออกมาใหญ่เกิน/เล็กเกิน | hdbscan_min_cluster_size ไม่เหมาะ | ปรับ `clustering.fine.hdbscan_min_cluster_size` (หรือ `clustering.n_groups` สำหรับกลุ่มใหญ่) แล้วรัน `uv run atlas run -c config.yaml -s cluster -s label -s series -s emerging -s forecast -s layout -s export` |
| ทุกหัวข้อขึ้น DECLINING | ปีล่าสุดข้อมูลยังไม่ครบ แต่ backfill guard ไม่ตัด (เช่น รันย้อนหลังด้วย `as_of_year` ผิด) | ดู log `[series] … looks incomplete` และ `meta.trimmed_years`; ตรวจ `emerging.as_of_year` (null = ปีของ snapshot ตอน cluster) หรือตั้ง `emerging.min_year_complete` เอง |
| `meta.trimmed_years` มีหลายปี / `last_complete_year` ต่ำกว่าที่คิด | ปีที่กำลังดำเนินอยู่ไม่นับเสมอ, ฉบับลงวันที่ล่วงหน้า, หรือปีล่าสุดยอด < 60% ของ median 3 ปีก่อน (ตัดได้สูงสุด `backfill_max_trim` = 2 ปี) | ปกติ — ดูตาราง "Articles per year" ใน profile; ถ้าข้อมูลครบจริงแล้ว ตั้ง `emerging.min_year_complete` |
| `RuntimeError: N of M files failed to read/parse (ratio … > input.max_error_ratio …)` (หรือ "ไม่มีไฟล์ใด parse ได้") | สัดส่วนไฟล์ที่อ่าน/parse ไม่ได้เกินเพดาน `input.max_error_ratio` (default 0.01) — มักเป็น parser/layout เปลี่ยน ไม่ใช่ไฟล์เสียแค่ไม่กี่ไฟล์; ingest หยุดเพื่อไม่ให้เผยแพร่คลังที่ขาดหายเงียบ ๆ | เปิด `work/01_ingest_errors.parquet` (คอลัมน์ path + error; error 3 ชนิดแรกอยู่ในข้อความ) หรือรัน `atlas profile <โฟลเดอร์>` ดู "Files with errors" (มีบรรทัด ⚠ เมื่อเกินเพดาน) → แก้ไฟล์/parser แล้วรัน `-s ingest` ใหม่; ถ้ายอมรับการสูญเสียนี้จริง ให้ปรับ `input.max_error_ratio` ใน config.yaml โดยตั้งใจ (แล้วบันทึกเหตุผล) |
| `RuntimeError: 07_emerging … orgs_unverified` ตอน `-s export` | work_dir สร้างก่อน definition v3 (ตาราง emerging ไม่มี flag `orgs_unverified`) — export ไม่เดาค่าให้ เพราะจะทำให้ความกว้างที่ยังไม่ตรวจดูเหมือนตรวจแล้ว | รัน `uv run atlas run -c config.yaml -s emerging -s forecast -s export` |
| log ขึ้น `[ingest] WARNING: N files could not be read or parsed` | ไฟล์เสีย/ถูกล็อก/สิทธิ์ไม่พอ, โฟลเดอร์ชื่อลงท้าย `.md`, หรือ layout ที่ parser ไม่รองรับ | ดู `work/01_ingest_errors` (path + error) หรือส่วน "Files with errors" ใน profile; แก้/ลบไฟล์แล้วรัน `-s ingest` ใหม่ — ไฟล์ที่มีไบต์เพี้ยนเล็กน้อยไม่ถูกข้าม แต่ได้ flag `decode_replaced` |
| log ขึ้น `[embed] WARNING: embedding.provider is 'lite'` | config ใช้ `lite` (สำหรับ CI) กับคลังจริง | เปลี่ยนเป็น `embedding.provider: local` (หรือ `api`) แล้วรันใหม่ — อย่าเผยแพร่ผลจาก lite |
| `ValueError: HDBSCAN found no clusters in N documents` | `hdbscan_min_cluster_size` ใหญ่เกินคลัง หรือ embedding ผิดปกติ (เช่น lite/โมเดลผิด) | ลด `clustering.fine.hdbscan_min_cluster_size` / `hdbscan_min_samples`; ตรวจ `work/03_meta.json` (model_id) — pipeline จะไม่รวมทุกอย่างเป็นหัวข้อเดียวเงียบ ๆ อีกแล้ว (ยกเว้นคลังจิ๋ว < 2 × min_cluster_size) |
| label เป็นภาษาอังกฤษหมด | โมเดลไม่ถนัดไทย | เปลี่ยนโมเดลใน `llm.tasks.label.model` (เช่น typhoon / gpt-4o / gemini-2.0-flash) แล้ว `atlas llm --check` — cache key (model + prompt) เปลี่ยน เฉพาะ label จะถูกสร้างใหม่ |
| หน้าเว็บยังเป็นข้อมูลเก่า | latest.json ยังชี้รอบเก่า หรือ cache | ตรวจ `data/latest.json` บน host; hard-refresh (เว็บอ่านด้วย no-cache) |
| แถบ "ยังไม่มีชุดข้อมูล" / "รุ่นของข้อมูลไม่ตรง" | ไม่มี `data/latest.json` หรือ schema ไม่ใช่ 2.x | รัน `atlas publish --site` ใหม่ / อัปเดตเว็บให้ตรงรุ่น |
| forecast ไม่มีบาง topic | ประวัติ < 6 ปี, ไม่ผ่าน skill gate (ดีกว่า naive ไม่พอ) หรือมีจุด backtest ซื่อสัตย์น้อยกว่า `forecast.min_honest_points` | เป็นเรื่องปกติ (`forecast.min_history_years`, `forecast.min_skill`, `forecast.min_honest_points`); ใน contract v2 (`topics.json`) ประวัติสั้น/LOW_DATA = `forecast: null`, ไม่ผ่าน gate = `forecast.show: false` (ไม่มีเส้น — เว็บขึ้น "แนวโน้มไม่แน่นอน"); `forecast_uncertain` มีเฉพาะไฟล์เก่า `atlas_data.json` (v1.1) · forecast รายหัวข้อ (share × ยอดรวมที่พยากรณ์) **ไม่ได้ปรับให้ผลรวมเท่ายอดรวมของคลัง** — รวมทุกหัวข้อแล้วไม่จำเป็นต้องเท่า `corpus_forecast` |
| หัวข้อเกือบทั้งหมดเป็น LOW_DATA | corpus เล็ก/ช่วงปีสั้น หรือ `min_articles_recent` สูงไป | ตรวจรายงาน profile; ปรับ `emerging.min_articles_recent` เฉพาะเมื่อมีเหตุผล (กระทบนิยาม ต้อง bump `definition_version`) |
| หัวข้อขึ้น WATCH เยอะ | WATCH = โตตามเกณฑ์ EMERGING แต่**ไม่ผ่านเกณฑ์ความกว้าง**: วารสาร < `breadth.min_journals`, สถาบัน < `breadth.min_orgs` (เมื่อข้อมูลสังกัดพอ) หรือบทความจากวารสารที่เพิ่งเข้าระบบ ≥ `breadth.max_new_journal_share` — มักเกิดจากวารสารเข้ามาอัปโหลดย้อนหลังเป็นชุด (journal-entry bias); คำอธิบายหัวข้อ/บทสรุปบอกเหตุผลรายหัวข้อ (เช่น "มาจาก 2 วารสาร", "วารสารที่เพิ่งเข้าระบบ 60%") | ดู profile หัวข้อ "วารสารที่อัปโหลดย้อนหลัง"; WATCH คือสัญญาณเตือน ไม่ใช่ข้อสรุป |
| `atlas llm` exit 130 / ข้อความ budget | งบ `llm.budget_usd` หมด, Ctrl-C หรือ `atlas llm-stop` | ปกติ — เพิ่มงบแล้วรันคำสั่งเดิม ทำต่อจาก cache (§6) |
| `atlas llm` exit 2 | key/model/URL/โควตาผิด | อ่านข้อความ error → แก้ `ATLAS_LLM_API_KEY` / `llm.endpoints` → `atlas llm --check` |
| `atlas llm` exit 3 | มีงาน LLM อื่นรันอยู่ | `atlas status` ดู PID; รอ หรือ `atlas llm-stop` |
| กลุ่มบนแผนที่ไม่ใช่สาขา OpenAlex (`taxonomy.source: agglomerative`, รหัส `G…`) | OpenAlex ล่ม/งบรายวันหมด (429) หรือปิด `taxonomy.source` → ใช้กลุ่ม agglomerative ที่**ตั้งชื่อตามหัวข้อที่ใหญ่ที่สุดของกลุ่ม** พร้อมเหตุผลใน `10_taxonomy_meta.json` | ตั้ง `OPENALEX_API_KEY` หรือรอวันถัดไป แล้ว `atlas run -s taxonomy …` ต่อ (cache คงอยู่; §9) |
| กลุ่มชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" / "Unmapped group N" | `10_taxonomy` **เก่ากว่า** การ cluster ล่าสุด (เช่น รัน `-s cluster` ใหม่แต่ไม่ได้รัน `-s taxonomy`) — หัวข้อที่ taxonomy เดิมไม่รู้จักถูกใส่กลุ่มสำรองชื่อนี้ (ไม่ได้เกิดจาก OpenAlex ล่ม) | รัน `atlas run -c config.yaml -s taxonomy -s label -s layout -s export` |
| `[run] ERROR: work_dir was clustered for X but pipeline.release is Y` (exit 2) | แก้ `pipeline.release` หลังขั้น cluster แล้วรันขั้นหลัง ๆ ต่อ — ข้อมูลใน work_dir เป็นของรอบ X | ตั้ง `pipeline.release: X` (หรือ null) เพื่อรันรอบ X ต่อ หรือรันตั้งแต่ `-s cluster` ใหม่เพื่อทำรอบ Y (ไม่มีอะไรถูกเขียนตอนถูกปฏิเสธ) |
| `atlas run` ปฏิเสธรอบเก่า / ขึ้นว่าไม่มี state หัวข้อรอบก่อน | รันรอบที่เก่ากว่ารอบที่มีอยู่แล้ว หรือ `state/releases/` ของรอบก่อนหายไป | ใช้ชื่อรอบใหม่ที่ไม่เก่ากว่ารอบล่าสุด; กู้ `state/releases/<รอบก่อน>/` จากสำรอง — ID หัวข้อไม่ถูกใช้ซ้ำ ระบบไม่เดาแทน |
| `provider: off` ใน YAML ไม่ทำงานตามคาด | YAML อ่าน `off` เปล่า ๆ เป็น false | ใส่เครื่องหมายคำพูด: `provider: "off"` |
| Windows แสดงภาษาไทยเพี้ยนใน console | console เป็น cp1252 | ทั้ง `uv run atlas …` และ `python -m atlas.pipeline` ตั้ง stdout/stderr เป็น UTF-8 ให้แล้ว (รวมตอน redirect ลงไฟล์) |
| อยากปรับนิยาม emerging | — | แก้ `config.yaml → emerging:` + `docs/EMERGING_SPEC.md` + `tests/test_emerging.py` พร้อมกัน แล้วรัน `uv run atlas run -c config.yaml -s emerging -s forecast -s export` (ฟรี ไม่แตะ API) |

## 4. งบประมาณโดยประมาณต่อรอบ (corpus ~200K เรื่อง)

| รายการ | API mode | Local mode |
|---|---|---|
| Embedding รอบแรก | ~$10–20 | ฟรี (GPU 2–4 ชม.) |
| Embedding รอบต่อไป | เฉพาะบทความใหม่/ที่ข้อความเปลี่ยน (เวกเตอร์เดิมอยู่ใน `state/embeddings`) | ฟรี |
| LLM (ชื่อ · คู่ซ้ำ · คำอธิบาย · บทสรุป) | ~$1–3 (เฉพาะ topic ที่ยังไม่มีใน cache; คุมด้วย `llm.budget_usd`) | ฟรี (ถ้ารันเอง) |
| **รวม/ไตรมาส** | **~$15–25** | **~0** |

## 5. การย้อนกลับ (rollback)

- เว็บ: deploy commit ก่อนหน้าอีกครั้งผ่าน GitHub Pages (re-run workflow ของ commit เก่า) หรือวางโฟลเดอร์ `web/dist` เวอร์ชันเก่ากลับ
- ข้อมูล: แก้ `data/latest.json` ให้ชี้รอบก่อน (โฟลเดอร์รอบเก่ายังอยู่ใน data/) — ไม่ต้อง build ใหม่

## 6. LLM ผ่าน API (ชื่อหัวข้อ · คู่ที่อาจซ้ำ · คำอธิบาย · บทสรุปผู้บริหาร)

ทุกงานใช้ปลายทางแบบ OpenAI-compatible (`POST {base_url}/chat/completions`) เช่น OpenRouter, Typhoon, DeepInfra หรือ vLLM/LiteLLM ขององค์กร — ตั้งใน `config.yaml → llm.endpoints` และเลือกโมเดลต่องานใน `llm.tasks.{label, merge, narrative, brief}` · `narrative.provider` ดีฟอลต์ `template` (ประโยคแม่แบบ ไม่เรียก LLM) — ตั้งเป็น `llm` เมื่อพร้อม

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
- JSON ผิดรูปแบบ → ขอให้แก้ ≤ `llm.max_repairs` (2) ครั้ง → fallback
- **ตรวจคำอธิบาย (grounding)**: ข้อความถูกปฏิเสธและเขียนใหม่ 1 ครั้ง (`llm.max_regenerations`) แล้วใช้ประโยคแม่แบบ เมื่อมี (ก) ตัวเลขหลักที่ไม่อยู่ในข้อมูลของหัวข้อ (ข) คำบอกจำนวนเท่า — ตัวเลข ("5 เท่า", "3 times", "12-fold", "5x") หรือตัวอักษรไทย/อังกฤษ ("สามเท่า", "สิบสองเท่า", "ร้อยเท่า", "five times", "hundredfold", "tripled", "doubled") — ที่ไม่ตรงกับ**อัตราส่วน**ในข้อมูล (ค่า "(x เท่า)" = share_ratio ของหัวข้อ ตรงตัวหรือปัด 1 ตำแหน่ง) เลขความยาวช่วงปีหรือจำนวนบทความใช้อ้างเป็น "เท่า" ไม่ได้ (ค) คำบอกจำนวนเท่าใด ๆ ในหัวข้อที่ไม่มีช่วงฐานเปรียบเทียบ (`no_baseline`) (ง) คำบอกทิศทางผิดในประโยคอัตราโต (เช่น เขียน "ลดลง" ให้หัวข้อที่โต; ในบทสรุปผู้บริหาร ประโยคที่เอ่ยหลายหัวข้อตรวจเมื่อมีตัวเลขอัตรา 1 ตัวเท่านั้น) — จำนวน fallback ทุกงานอยู่ใน `manifest.json → llm` และ `atlas validate` เตือนก่อนเผยแพร่
- prompts อยู่ใน `prompts/topic_label.th.md`, `topic_merge.th.md`, `topic_narrative.th.md`, `executive_brief.th.md`
- **ชื่อหัวข้อข้ามไตรมาส**: หัวข้อที่ lineage เป็น `continue` และคำสำคัญผู้เขียน + คำเด่น c-TF-IDF ยังทับซ้อนกับชุดคำตอนตั้งชื่อ ≥ `labeling.reuse_min_jaccard` (Jaccard, ค่าเริ่ม 0.5) ใช้ชื่อเดิมของรอบก่อน (`label_source: reused`, ไม่เรียก LLM — นับใน `manifest.labels.reused`); หัวข้อใหม่/แยก/รวม และหัวข้อที่คำเปลี่ยนมากได้ชื่อใหม่; ชื่อจาก fallback คำสำคัญไม่ถูกเก็บต่อ (ถาม LLM ใหม่) และชื่อที่บรรณาธิการแก้ (overrides) ยังชนะเสมอ — ชื่อของแต่ละรอบเก็บไว้ที่ `state/releases/<release>/labels.parquet`
- **ค่าใช้จ่ายใน manifest**: `manifest.llm[].cost_usd` = ยอดรวมของรอบข้อมูลนั้นทั้งหมด (รวมทุกครั้งที่รัน จาก journal) · `this_run_cost_usd` = เฉพาะการรันครั้งล่าสุด
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

ใส่ผู้สมัครใน `bakeoff.embedding_candidates` (api ใช้ runner เดียวกับ embed — แยก store ต่อโมเดล จ่ายครั้งเดียว)

คอลัมน์ในรายงาน:
- embedding: `journal_knn_acc` = kNN ทายวารสารของบทความจากเพื่อนบ้านที่กันไว้ · `subfield_knn_acc` = kNN ทาย subfield OpenAlex บนงานอ้างอิงไทย (ว่างถ้าไม่มี reference) · `truth_purity` = สัดส่วนเพื่อนบ้านที่เป็นหัวข้อจริงเดียวกัน (เฉพาะ synthetic ที่มี `--truth`)
- clustering: `ari_stability` = ARI เฉลี่ยระหว่าง seed (1 = เหมือนกันทุกครั้ง; เกณฑ์ ≥ 0.8) · `ari_vs_first` = สองอัลกอริทึมเห็นตรงกันแค่ไหน · `npmi` = coherence ของคำเด่นของแต่ละหัวข้อ · `purity` = ความบริสุทธิ์เทียบเฉลย (synthetic เท่านั้น)

บรรทัด "best" ในรายงาน (embedding: จัดอันดับด้วยค่าเฉลี่ยของ `journal_knn_acc`, `subfield_knn_acc` และ `truth_purity` เท่าที่มีในรอบนั้น) เป็นจุดเริ่มต้น **ไม่ใช่คำตัดสิน** (advisory) — ผู้ปฏิบัติงานเป็นคนเลือก (เลือก embedding ด้วย journal/subfield accuracy; เลือกอัลกอริทึมที่ ARI stability ≥ 0.8 แล้วดู purity/NPMI) และการเปลี่ยนโมเดล embedding = store ใหม่ + embed ใหม่ทั้งคลัง (ค่าใช้จ่ายรอบแรกอีกครั้ง) รวมถึง fit หัวข้อใหม่ทั้งก้อน

## 9. OpenAlex สำหรับกลุ่มบนแผนที่ (taxonomy)

- key เป็น **ทางเลือก**: `OPENALEX_API_KEY` (ส่งเป็น `Authorization: Bearer` เท่านั้น ไม่อยู่ใน cache/log/ข้อความ error) — ไม่ตั้ง = โหมด keyless
- keyless: งบ ~$0.10/วัน, 10 req/s (เราจำกัดที่ 8 = `requests_per_second_keyless`) · มี key: ~$1/วัน, 30 req/s (เราจำกัดที่ 25 = `requests_per_second_keyed`) และดึงได้หลายหน้า (`max_pages_keyed`)
- งบรายวันหมด (HTTP 429) = หยุดอย่างสะอาด เก็บที่ดึงได้แล้วไว้ใน `state/openalex/` และ taxonomy ถอยไปใช้กลุ่ม agglomerative พร้อมบันทึกเหตุผล (แต่ละกลุ่มตั้งชื่อตามหัวข้อที่ใหญ่ที่สุดของกลุ่ม; ชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" เกิดเฉพาะเมื่อ `10_taxonomy` เก่ากว่าการ cluster) — ตั้ง key หรือรอวันถัดไปแล้วรัน `-s taxonomy` ซ้ำ ทำต่อจาก cache (ใช้ร่วมกันทั้งสองโหมด)
