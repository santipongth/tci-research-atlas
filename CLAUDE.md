# CLAUDE.md — TCI Research Atlas

> ไฟล์นี้คือ "สมองกลาง" ของโปรเจกต์สำหรับ Claude Code — อ่านไฟล์นี้ก่อนทำอะไรทั้งสิ้น
> เอกสารเชิงลึกแยกอยู่ใน `docs/` — อ่านเฉพาะที่เกี่ยวกับงานที่กำลังทำ

## 1. โปรเจกต์นี้คืออะไร

**TCI Research Atlas** = แผนที่ภูมิทัศน์งานวิจัยไทย (discovery & insight tool) สำหรับ 3 กลุ่มผู้ใช้:

- **นักวิจัย** — หาช่องว่างงานวิจัย ดูหัวข้อที่กำลังโต
- **บรรณาธิการวารสาร** — เห็นภาพรวมสาขา วางแผนเชิงกลยุทธ์
- **ผู้บริหาร/นโยบาย** — dashboard ภาพรวมเพื่อการตัดสินใจระดับประเทศ

สถาปัตยกรรม: **batch pipeline (Python, รันทุก 3 เดือน)** → ส่งออก `atlas_data.json` → **เว็บ (React)** โหลด JSON นั้นมาแสดงเป็น live interactive dashboard โดยไม่ต้องแก้โค้ดเว็บ

## 2. โครงสร้าง repo

```
tci-research-atlas/
├── CLAUDE.md               ← ไฟล์นี้
├── README.md               ← ภาพรวมสำหรับทีม (ภาษาไทย)
├── docs/
│   ├── ARCHITECTURE.md     ← การออกแบบระบบ + การไหลของข้อมูล
│   ├── DATA_SPEC.md        ← สเปก input (TCI metadata) และ output (atlas_data.json)
│   ├── EMERGING_SPEC.md    ← นิยาม "emerging" ของ TCI ฉบับเต็ม + สูตรคะแนน
│   ├── ROADMAP.md          ← ฟีเจอร์ทั้ง 5 phase + ของที่ควรทำต่อ
│   └── OPERATIONS.md       ← วิธีรัน batch รายไตรมาส + import เข้าเว็บ + troubleshoot
├── pipeline/               ← Python batch pipeline (Phase 1,2,4,5)
│   ├── atlas/              ← โมดูล pipeline: ingest→preprocess→embed→cluster→label
│   │                         →series→emerging→forecast→layout→export
│   ├── config.example.yaml ← คัดลอกเป็น config.yaml แล้วแก้
│   ├── tests/              ← pytest (มี test_emerging.py ครอบคลุมนิยาม emerging)
│   ├── scripts/            ← validate_input.py, run_all.sh
│   └── requirements.txt
├── web/                    ← React + TypeScript + Vite + Tailwind (Phase 3)
│   ├── src/sections/       ← AtlasMap, EmergingThemes, GroupRanking, Insights, ...
│   ├── src/lib/loader.ts   ← โหลด /data/atlas_data.json → normalize → fallback ข้อมูล bundle
│   ├── src/data/atlas.ts   ← ข้อมูล bundle (71 สาขาจริง) + interfaces หลัก
│   └── public/data/atlas_data.example.json ← ตัวอย่างไฟล์จาก pipeline
├── prompts/                ← LLM prompts ทั้งหมด (ฉบับ master — sync กับโค้ด)
└── scripts/
    ├── quarterly_run.sh    ← สคริปต์รัน batch รายไตรมาส (เรียกจาก cron)
    └── import_atlas.sh     ← คัดลอกผล pipeline เข้า web/public/data/ + build
```

## 3. แผนฟีเจอร์ 5 Phase (สถานะปัจจุบัน)

| Phase | ฟีเจอร์ | ที่ตั้ง | สถานะ |
|---|---|---|---|
| 1 | Embedding (batch, API **หรือ** local model) | `pipeline/atlas/embed.py` | ✅ พร้อมใช้ |
| 2 | Topic Clustering 2 ชั้น (UMAP+HDBSCAN, c-TF-IDF) | `pipeline/atlas/cluster.py` | ✅ พร้อมใช้ |
| 3 | Atlas web (bubble map, drill-down, 2 ภาษา) | `web/` | ✅ พร้อมใช้ |
| 4 | Emerging Topic Analysis (นิยาม TCI + burst + score) | `pipeline/atlas/emerging.py` + `web/src/sections/EmergingThemes.tsx` | ✅ พร้อมใช้ |
| 5 | Research Trend Forecasting (OLS/Poisson, backtest) | `pipeline/atlas/forecast.py` + ForecastChart ในเว็บ | ✅ พร้อมใช้ |
| + | LLM labeling + merge duplicates | `pipeline/atlas/label.py` | ✅ พร้อมใช้ |
| + | Live dashboard (โหลด JSON runtime, fallback bundle) | `web/src/lib/loader.ts` | ✅ พร้อมใช้ |

สิ่งที่ยังไม่มี / ไอเดียต่อยอดอยู่ใน `docs/ROADMAP.md` (เช่น author network, journal view, compare mode, API backend)

## 4. คำสั่งที่ใช้บ่อย

### Pipeline (ทำงานใน `pipeline/`)

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml      # แล้วแก้ path/ค่าต่าง ๆ
export ATLAS_API_KEY=...                # ถ้าใช้ embedding/labeling แบบ API

python scripts/validate_input.py --config config.yaml   # เช็กไฟล์ input ก่อนเสมอ
python -m atlas.pipeline --config config.yaml           # รันทั้ง pipeline
python -m atlas.pipeline --config config.yaml --steps emerging forecast export  # รันบาง step
pytest tests/ -q                        # ทดสอบ
```

### Web (ทำงานใน `web/`)

```bash
npm install
npm run dev        # dev server
npm run build      # build → dist/
```

### รอบรันรายไตรมาส (จาก root)

```bash
bash scripts/quarterly_run.sh /path/to/tci_export.csv     # รัน pipeline ครบ + validate
bash scripts/import_atlas.sh                              # คัดลอก JSON เข้าเว็บ + build
```

รายละเอียดเชิงปฏิบัติการทั้งหมดอยู่ใน `docs/OPERATIONS.md`

## 5. Data contract สำคัญที่สุด: `atlas_data.json`

**นี่คือสัญญาระหว่าง pipeline กับเว็บ — ห้ามเปลี่ยนโดยไม่แก้ทั้งสองฝั่ง**

- ฝั่งผลิต: `pipeline/atlas/export.py` (schema เต็มใน `docs/DATA_SPEC.md`)
- ฝั่งบริโภค: `web/src/lib/loader.ts` — ฟังก์ชัน `normalize()` แปลง pipeline schema → web schema:
  - `nodeId` → `id`, `kind: "topic"` → `kind: "field"`, `nTopics` → `nFields`
  - `emerging_score` → `emergingScore`, `burst_years` → `burstYears`
  - `meta.total_topics` → `totalFields`, `meta.last_complete_year` → `lastCompleteYear`
- เว็บ fetch `/data/atlas_data.json` ตอน runtime (`cache: "no-cache"`) — ถ้าไม่มีไฟล์/โหลดไม่ได้ → ใช้ข้อมูล bundle ใน `src/data/atlas.ts` แทน (หน้าเว็บไม่มีวันขาว)
- **การอัปเดตข้อมูล = วางไฟล์ JSON ใหม่เท่านั้น ไม่ต้องแก้โค้ดเว็บ** (แต่ต้อง build ใหม่เพราะ public/ ถูกคัดลอกเข้า dist/)

## 6. กฎการพัฒนา (Do / Don't)

### Pipeline

- **DO** เพิ่ม step ใหม่โดยสร้างโมดูลใน `atlas/` ที่อ่าน checkpoint ของ step ก่อนจาก `work_dir` และเขียน checkpoint ของตัวเอง — pipeline ต้อง stop/resume ได้ทุกจุด
- **DO** ใช้ `io_utils.read_table/write_table` (รองรับ parquet→pickle fallback) อย่าเรียก `pd.read_parquet` ตรง ๆ
- **DO** เก็บค่าพารามิเตอร์ทุกตัวใน `config.yaml` — ห้าม hardcode threshold
- **DO** รัน `pytest tests/ -q` ก่อนส่งงาน — โดยเฉพาะถ้าแก้ `emerging.py` (นิยาม emerging มี unit test ล็อกไว้)
- **DON'T** แก้นิยาม EMERGING/HOT/DECLINING โดยไม่อัปเดต `docs/EMERGING_SPEC.md` + `config.example.yaml` + ทดสอบให้ตรงกัน
- **DON'T** ใส่ API key ลงไฟล์ใด ๆ — ใช้ env var (`ATLAS_API_KEY`) เสมอ

### Web

- **DO** อ่าน `web/src/data/atlas.ts` เพื่อดู interfaces หลัก (`AtlasNode`, `TopicForecast`, `TopicStatus`) ก่อนแก้ UI
- **DO** คง design tokens: bg `#f5f6f2`, ink `#161611`, accent `#FF5F1F`, panel ขาว radius 7px; fonts: IBM Plex Sans Thai (UI), IBM Plex Mono (ตัวเลข), Noto Serif Thai (display)
- **DO** รองรับ 2 ภาษาทุกสตริง — เพิ่ม key ใน `web/src/lib/i18n.ts` ทั้ง `th` และ `en`
- **DO** ทำให้ section ใหม่ "หดตัวเอง" (return null) เมื่อข้อมูลไม่มีฟิลด์นั้น — เหมือน `EmergingThemes.tsx` ที่ซ่อนตัวถ้าไม่มี status
- **DON'T** แก้ Tailwind เป็น dynamic class (เช่น `bg-[${color}]` จาก string ต่อกัน) — compile ไม่ผ่าน; ใช้ inline style แทนถ้าต้อง dynamic
- **DON'T** ใส่ข้อมูลจริงลง `public/data/atlas_data.json` ใน repo — repo เก็บเฉพาะ `atlas_data.example.json`; ไฟล์จริงวางตอน deploy

### LLM prompts

- Prompts ฉบับ master อยู่ใน `prompts/*.md` — โค้ดใน `pipeline/atlas/label.py` มีสำเนาฝังอยู่; **ถ้าแก้ prompt ให้แก้ทั้งสองที่และบอกใน commit**
- ทุก prompt มี `prompt_hash` caching — เปลี่ยน prompt = hash เปลี่ยน = label ถูกสร้างใหม่เฉพาะที่จำเป็น

## 7. บริบทภาษาไทยที่ต้องรู้

- ข้อมูล TCI เป็นไทย+อังกฤษปนกัน — embedding ต้อง multilingual (default: API `text-embedding-3-large` หรือ local `BAAI/bge-m3`)
- c-TF-IDF ใช้ `char_wb` n-gram 3–5 เพราะภาษาไทยไม่มีช่องว่างระหว่างคำ
- ปีในข้อมูลอาจเป็น พ.ศ. — `ingest.py` แปลงเป็น ค.ศ. แล้ว (ทุกอย่าง downstream เป็น ค.ศ.)
- UI ภาษาไทยห้ามใช้ italic (ภาษาไทยไม่มีตัวเอียงแท้)

## 8. เมื่อไม่แน่ใจ

1. ดู `docs/ARCHITECTURE.md` ก่อน — เข้าใจการไหลของข้อมูล
2. ดู `docs/DATA_SPEC.md` — schema ทุกไฟล์ checkpoint
3. ดู `docs/OPERATIONS.md` — ถ้าเป็นเรื่องรันงานจริง
4. ถามผู้ใช้ถ้าการตัดสินใจกระทบ "นิยาม" (เช่น เปลี่ยน threshold ของ emerging) เพราะผู้บริหารใช้ตัวเลขเหล่านี้สื่อสารต่อ
