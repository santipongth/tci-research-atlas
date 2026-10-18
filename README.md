# TCI Research Atlas

**แผนที่ภูมิทัศน์งานวิจัยไทย** — เครื่องมือ discovery & insight จากบทความวารสารวิชาการไทย (TCI/ThaiJO)
สำหรับ **นักวิจัย** (หาช่องว่าง ดูหัวข้อกำลังโต) · **บรรณาธิการ** (เห็นภาพรวมสาขา) · **ผู้บริหาร** (dashboard เพื่อนโยบาย)

## ระบบประกอบด้วย 2 ส่วน

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  pipeline/  (Python batch)  │         │  web/  (React dashboard)     │
│  รันทุก 3 เดือน             │  JSON   │  โหลด /data/atlas_data.json  │
│                             │ ──────► │  ตอน runtime → ไม่ต้องแก้โค้ด │
│  คลัง .md จาก ThaiJO        │         │  bubble map · emerging ·      │
│  → embed → cluster → label  │         │  forecast · insights          │
│  → emerging → forecast      │         │  (ถ้าไม่มี JSON ใช้ข้อมูล     │
│  → atlas_data.json          │         │   bundle 71 สาขาสำรอง)        │
└─────────────────────────────┘         └──────────────────────────────┘
```

- **ไม่มีฐานข้อมูล ไม่มี backend** — เว็บเป็น static site ที่อ่าน JSON ไฟล์เดียว
- **อัปเดตข้อมูล = วางไฟล์ `atlas_data.json` ใหม่ + build เว็บใหม่** เท่านั้น

## Quick start

```bash
cd pipeline
uv sync --extra local                      # หรือ --extra api
cp config.example.yaml config.yaml         # แก้ input.path → โฟลเดอร์ .md
export ATLAS_API_KEY=sk-...                # ถ้าใช้ embedding/labeling แบบ API
uv run atlas profile /path/to/corpus --md ../logs/profile.md   # ขั้น 1: อ่านรายงานก่อนเสมอ
uv run atlas run --config config.yaml      # ขั้น 2: ทั้งสาย (หรือ bash ../scripts/quarterly_run.sh)
bash ../scripts/import_atlas.sh            # ขั้น 3: นำเข้าเว็บ + build
uv run pytest -q                           # ทดสอบ pipeline
cd ../web && npm run dev                   # ดูผลที่ localhost
```

ข้อมูลจริง (คลังบทความ, `atlas_data.json` ของจริง) **ไม่เข้า git** — repo เก็บเฉพาะตัวอย่าง 11 ไฟล์ใน `pipeline/tests/fixtures/` และ `atlas_data.example.json`

รอบรันจริงรายไตรมาส: ดู `docs/OPERATIONS.md` · สเปกข้อมูล: `docs/DATA_SPEC.md` · นิยาม emerging: `docs/EMERGING_SPEC.md` · แผนหลัก v2: `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md`

## นิยาม "Emerging" ของ TCI v2 (ย่อ)

หน้าต่างเวลา: **R = 3 ปีล่าสุดที่สมบูรณ์**, **B = 5 ปีก่อนหน้า R** (ตัดปีที่ข้อมูลยัง backfill ไม่เสร็จออกอัตโนมัติ) · สถานะใช้ช่วงเชื่อมั่นของการเติบโต ไม่ใช่ค่าจุดเดียว

| สถานะ | ความหมาย (ดีฟอลต์) |
|---|---|
| **LOW_DATA** ข้อมูลน้อย | count_R < 30 หรือประมาณ share_growth ไม่ได้ — ไม่ฟันธง |
| **EMERGING** กำลังเกิดใหม่ | หัวข้อเล็ก **และ** ขอบล่างของช่วงเชื่อมั่นการโต ≥ +10%/ปี **และ** share_ratio ≥ 1.8 **และ** ความกว้าง (วารสาร/สถาบัน) ผ่าน |
| **WATCH** จับตา | โตตามเกณฑ์ EMERGING แต่ความกว้างไม่ผ่าน (สัญญาณ journal-entry bias) |
| **HOT** กำลังร้อน | หัวข้อใหญ่ **และ** ขอบล่างของช่วงเชื่อมั่นการโต > 0 |
| **DECLINING** กำลังลดลง | ขอบบนของช่วงเชื่อมั่นการโต < 0 **และ** share_ratio ≤ 0.8 |
| **STABLE** คงที่ | อื่น ๆ |

สถานะตรวจตามลำดับข้างต้น (ข้อแรกที่เข้าคือคำตอบ) · Emerging Score 0–100 เป็น percentile ภายในรอบ ใช้จัดอันดับเท่านั้น เทียบข้ามรอบไม่ได้
สเปกเต็มพร้อมสูตรและเหตุผลเชิงวิธีวิจัย: `docs/EMERGING_SPEC.md`

## Forecasting

ทำนายจำนวนบทความรายปีของแต่ละหัวข้อล่วงหน้า 2 ปี ด้วย naive / linear (OLS) / Poisson GLM — เลือกโมเดลต่อหัวข้อด้วย backtest และแสดงผล **เฉพาะหัวข้อที่ผ่าน skill gate** (แม่นกว่า naive); หัวข้อที่ไม่ผ่านจะไม่มีเส้นทำนายใน JSON (`forecast: null`, `forecast_uncertain: true`)

## ทีมที่พัฒนาต่อ

เปิด repo นี้ใน **Claude Code** แล้วอ่าน `CLAUDE.md` — มีกฎการพัฒนา data contract และคำสั่งทั้งหมดครบถ้วน
