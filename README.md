# TCI Research Atlas

**แผนที่ภูมิทัศน์งานวิจัยไทย** — เครื่องมือ discovery & insight จากบทความวารสารวิชาการไทย (TCI/ThaiJO)
สำหรับ **นักวิจัย** (หาช่องว่าง ดูหัวข้อกำลังโต) · **บรรณาธิการ** (เห็นภาพรวมสาขา) · **ผู้บริหาร** (dashboard เพื่อนโยบาย)

## ระบบประกอบด้วย 2 ส่วน

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  pipeline/  (Python batch)  │         │  web/  (React dashboard)     │
│  รันทุก 3 เดือน             │  JSON   │  โหลด /data/atlas_data.json  │
│                             │ ──────► │  ตอน runtime → ไม่ต้องแก้โค้ด │
│  metadata TCI               │         │  bubble map · emerging ·      │
│  → embed → cluster → label  │         │  forecast · insights          │
│  → emerging → forecast      │         │  (ถ้าไม่มี JSON ใช้ข้อมูล     │
│  → atlas_data.json          │         │   bundle 71 สาขาสำรอง)        │
└─────────────────────────────┘         └──────────────────────────────┘
```

- **ไม่มีฐานข้อมูล ไม่มี backend** — เว็บเป็น static site ที่อ่าน JSON ไฟล์เดียว
- **อัปเดตข้อมูล = วางไฟล์ `atlas_data.json` ใหม่ + build เว็บใหม่** เท่านั้น

## Quick start

```bash
# 1) Pipeline — ผลิต atlas_data.json จาก metadata TCI
cd pipeline
pip install -r requirements.txt
cp config.example.yaml config.yaml   # แก้ input.path และตั้งค่า embedding provider
export ATLAS_API_KEY=sk-...          # ถ้าใช้ API mode
python scripts/validate_input.py --config config.yaml
python -m atlas.pipeline --config config.yaml
# → ได้ pipeline/output/atlas_data.json

# 2) Web — นำ JSON เข้าเว็บแล้ว build
cd ..
bash scripts/import_atlas.sh         # copy JSON → web/public/data/ + npm run build
cd web && npm run dev                # ดูผลที่ localhost
```

รอบรันจริงรายไตรมาส: ดู `docs/OPERATIONS.md` · สเปกข้อมูล: `docs/DATA_SPEC.md` · นิยาม emerging: `docs/EMERGING_SPEC.md`

## นิยาม "Emerging" ของ TCI (ย่อ)

หน้าต่างเวลา: **R = 3 ปีล่าสุดที่สมบูรณ์**, **B = 5 ปีก่อนหน้า R** (ตัดปีที่ข้อมูลยัง backfill ไม่เสร็จออกอัตโนมัติ)

| สถานะ | เงื่อนไข |
|---|---|
| **EMERGING** กำลังเกิดใหม่ | share(R) < 1.5% **และ** CAGR(R) ≥ 25%/ปี **และ** share(R)/share(B) ≥ 1.8 **และ** มี ≥ 30 เรื่องในช่วง R |
| **HOT** กำลังร้อน | share(R) ≥ 1.5% **และ** slope ของ share > 0 |
| **DECLINING** กำลังลดลง | slope ของ share ติดลบต่อเนื่อง ≥ 3 ปี |
| **STABLE** คงที่ | ไม่เข้าเงื่อนไขข้างต้น |

**Emerging Score (0–100)** = `100 × (0.35·P(growth) + 0.25·P(acceleration) + 0.20·P(burst) + 0.20·P(novelty))`
โดย P() คือ percentile rank ภายในรอบรันนั้น — burst ใช้ Kleinberg 2-state (Viterbi, Poisson), novelty = 1 − max cosine similarity กับ centroid ของรอบก่อน

สเปกเต็มพร้อมเหตุผลเชิงวิธีวิจัย: `docs/EMERGING_SPEC.md`

## Forecasting

ทำนายจำนวนบทความรายปีของแต่ละหัวข้อล่วงหน้า 2 ปี ด้วย linear (OLS) / Poisson GLM — ระบบ **เลือกโมเดลที่ดีสุดต่อหัวข้ออัตโนมัติ** ด้วย backtest (train ≤ Y−3, วัด MAPE 3 ปีสุดท้าย) พร้อมช่วงความเชื่อมั่น ±1.96σ แสดงเป็นกราฟเส้นประในแผงรายละเอียดของเว็บ

## ทีมที่พัฒนาต่อ

เปิด repo นี้ใน **Claude Code** แล้วอ่าน `CLAUDE.md` — มีกฎการพัฒนา data contract และคำสั่งทั้งหมดครบถ้วน
