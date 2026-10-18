# OPERATIONS — คู่มือปฏิบัติการรายไตรมาส

> สำหรับผู้ดูแลระบบ: รอบรันปกติทำ 4 ขั้น — รับไฟล์ → รัน pipeline → นำเข้าเว็บ → ตรวจหน้าเว็บ
> เวลารวมโดยประมาณ (corpus ~200K): API mode 30–60 นาที / local mode 2–4 ชั่วโมง

## 0. สิ่งที่ต้องมี (ครั้งแรกครั้งเดียว)

- เครื่องที่รัน pipeline: Python 3.11+ (ใช้ `uv`; dev/CI ใช้ 3.12), RAM ≥ 16 GB (local mode อยากได้ GPU)
- เครื่อง build เว็บ: Node.js 24 (ตรงกับ CI) (เครื่องเดียวกันก็ได้)
- API key ถ้าใช้โหมด api: ตั้ง `export ATLAS_API_KEY=...` (ใส่ใน `.env` หรือ crontab env)
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
- เปิด `output/manifest.json` ดู `counts.total_articles` ว่าเพิ่มขึ้นสมเหตุสมผลจากรอบก่อน
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

## 2. ตั้ง cron (ตัวเลือก — ยังต้องมีคนกดตรวจขั้น 3–4)

```cron
# 01:00 วันที่ 1 ของ เดือน 1,4,7,10
0 1 1 1,4,7,10 * cd /path/to/tci-research-atlas && bash scripts/quarterly_run.sh pipeline/config.yaml >> logs/quarterly.log 2>&1
```

## 3. Troubleshooting

| อาการ | สาเหตุที่พบบ่อย | วิธีแก้ |
|---|---|---|
| `atlas profile` ฟ้องไฟล์อ่านไม่ได้/ฟิลด์ว่างมาก | รูปแบบ .md จาก ThaiJO เปลี่ยน (หรือใช้ `input.format: table` แล้ว mapping คอลัมน์ผิด) | ดูรายงาน profile; ถ้าเป็นตาราง แก้ `input.columns` ใน config.yaml |
| embed ค้าง/ล่มกลางทาง | API timeout, OOM | รันใหม่ได้เลย — checkpoint ทุก 5,000 เรื่อง รันต่อจากจุดเดิม |
| topic ออกมาใหญ่เกิน/เล็กเกิน | hdbscan_min_cluster_size ไม่เหมาะ | ปรับ `clustering.fine.hdbscan_min_cluster_size` (หรือ `clustering.n_groups` สำหรับกลุ่มใหญ่) แล้วรัน `uv run atlas run -c config.yaml -s cluster -s label -s series -s emerging -s forecast -s layout -s export` |
| ทุกหัวข้อขึ้น DECLINING | ปีล่าสุดข้อมูลยังไม่ครบ แต่ backfill guard ไม่ตัด | ตั้ง `emerging.min_year_complete` เองใน config |
| label เป็นภาษาอังกฤษหมด | โมเดลไม่ถนัดไทย | เปลี่ยน `labeling.api.model` (เช่น typhoon / gpt-4o / gemini-2.0-flash) — cache_key (hash ของ model + prompt) เปลี่ยน เฉพาะ label จะถูกสร้างใหม่ |
| หน้าเว็บยังเป็นข้อมูลเก่า | ลืม build ใหม่ หรือ browser cache | `import_atlas.sh` ต้องรันจนจบ (มี build ในตัว); hard-refresh |
| หน้าเว็บ badge ขึ้น "○ ข้อมูลตัวอย่าง" | JSON ไม่ถูกวาง/โหลดไม่ได้ | เช็ก `web/public/data/atlas_data.json` มีจริง และ deploy มีไฟล์นี้ด้วย |
| forecast ไม่มีบาง topic | ประวัติ < 6 ปี หรือไม่ผ่าน skill gate (ดีกว่า naive ไม่พอ) | เป็นเรื่องปกติ (`forecast.min_history_years`, `forecast.min_skill`); ใน JSON จะเป็น `forecast: null` + `forecast_uncertain` |
| หัวข้อเกือบทั้งหมดเป็น LOW_DATA | corpus เล็ก/ช่วงปีสั้น หรือ `min_articles_recent` สูงไป | ตรวจรายงาน profile; ปรับ `emerging.min_articles_recent` เฉพาะเมื่อมีเหตุผล (กระทบนิยาม ต้อง bump `definition_version`) |
| หัวข้อขึ้น WATCH เยอะ | วารสารเข้ามาอัปโหลดย้อนหลังเป็นชุด (journal-entry bias) | ดู profile หัวข้อ "วารสารที่อัปโหลดย้อนหลัง"; WATCH คือสัญญาณเตือน ไม่ใช่ข้อสรุป |
| `provider: off` ใน YAML ไม่ทำงานตามคาด | YAML อ่าน `off` เปล่า ๆ เป็น false | ใส่เครื่องหมายคำพูด: `provider: "off"` |
| Windows แสดงภาษาไทยเพี้ยนใน console | console เป็น cp1252 | ใช้ `uv run atlas …` (ตั้ง UTF-8 ให้แล้ว) |
| อยากปรับนิยาม emerging | — | แก้ `config.yaml → emerging:` + `docs/EMERGING_SPEC.md` + `tests/test_emerging.py` พร้อมกัน แล้วรัน `uv run atlas run -c config.yaml -s emerging -s forecast -s export` (ฟรี ไม่แตะ API) |

## 4. งบประมาณโดยประมาณต่อรอบ (corpus ~200K เรื่อง)

| รายการ | API mode | Local mode |
|---|---|---|
| Embedding รอบแรก | ~$10–20 | ฟรี (GPU 2–4 ชม.) |
| Embedding รอบต่อไป | ~เท่าเดิม (รันทั้ง corpus ใหม่) | ฟรี |
| LLM labeling | ~$1–3 (เฉพาะ topic ที่ยังไม่มีใน cache) | ฟรี (ถ้ารันเอง) |
| **รวม/ไตรมาส** | **~$15–25** | **~0** |

## 5. การย้อนกลับ (rollback)

- เว็บบน Kimi: ใช้ version card ย้อนกลับเวอร์ชันก่อนหน้าได้ทันที
- ข้อมูล: คัดลอก `atlas_data.json` จาก `runs/<ไตรมาสก่อน>/` กลับมาแล้ว `import_atlas.sh` ใหม่
