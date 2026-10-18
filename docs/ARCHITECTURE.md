# ARCHITECTURE — สถาปัตยกรรมระบบ

## 1. หลักการออกแบบ

1. **แยกผลิตจากแสดงผลสมบูรณ์** — pipeline (Python, batch, หนัก) กับเว็บ (React, static, เบา) รู้จักกันผ่านไฟล์เดียว: `atlas_data.json` เปลี่ยนโค้ดฝั่งใดฝั่งหนึ่งได้อิสระ ตราบใดที่ data contract ไม่เปลี่ยน
2. **ไม่มี backend/database** — ลดภาระ infra ของทีมเป็นศูนย์; เว็บ static ใช้ได้ทุกที่ (Kimi publish, GitHub Pages, nginx)
3. **ทุกอย่าง resume ได้** — pipeline เขียน checkpoint หลังทุก step ลง `work_dir`; รันใหม่ = ข้าม step ที่ทำแล้ว (เลือกด้วย `--steps`)
4. **ตัวเลขต้องอธิบายได้** — ทุก metric ที่ขึ้นหน้าเว็บมีนิยามเขียนไว้ใน `EMERGING_SPEC.md` และทดสอบใน `tests/` เพราะผู้บริหารจะถือตัวเลขนี้ไปคุยต่อ
5. **ภาษาไทยเป็นพลเมืองชั้นหนึ่ง** — embedding multilingual, c-TF-IDF แบบ char n-gram, UI สองภาษา, ปี ค.ศ. เป็นมาตรฐานกลาง (แปลงจาก พ.ศ. ที่ ingest)

## 2. การไหลของข้อมูล (data flow)

```
metadata TCI (csv/json/parquet)
        │
        ▼
[ingest]      อ่าน+map คอลัมน์, แปลง พ.ศ.→ค.ศ., dedup (title similarity ≥0.95 เก็บ record ที่ metadata ครบกว่า)
        │  → work/01_articles.parquet
        ▼
[preprocess]  ประกอบ doc ต่อเรื่อง (title+keywords+abstract, ≤6000 ตัวอักษร), ทำความสะอาด
        │  → work/02_docs.parquet
        ▼
[embed]       embedding ทุกเรื่อง (provider: api|local) + checkpoint ทุก 5,000 เรื่อง
        │  → work/03_embeddings.npy
        ▼
[cluster]     UMAP(10 มิติ) → HDBSCAN 2 ชั้น (coarse=กลุ่มใหญ่, fine=topic)
              outlier → assign เข้า centroid ใกล้สุด, c-TF-IDF (char_wb 3–5) หาคำเด่น
        │  → work/04_topics.parquet, 04_topic_info.parquet, 04_centroids.npy
        ▼
[label]       LLM ตั้งชื่อ topic (terms + representative titles → JSON ชื่อไทย/อังกฤษ/คำอธิบาย/keywords)
              cache ด้วย (topic, prompt_hash, model) — รันใหม่ไม่เสียเงินซ้ำ
        │  → work/05_labels.parquet
        ▼
[series]      ตารางจำนวนบทความ topic × ปี + last_complete_year (backfill guard:
              ตัดปีล่าสุดทิ้งถ้ายอด < 60% ของ median)
        │  → work/06_topic_year.parquet, 06_meta.json
        ▼
[emerging]    นิยาม TCI: share/CAGR/slope/streak + Kleinberg burst + novelty เทียบ centroid รอบก่อน
        │  → work/07_emerging.parquet
        ▼
[forecast]    OLS/Poisson ต่อ topic + เลือกโมเดลด้วย backtest MAPE (train ≤ Y−3)
        │  → work/08_forecasts.parquet
        ▼
[layout]      UMAP 2 มิติสำหรับแผนที่ + edges จาก cosine similarity ของ centroid
        │  → work/09_layout.parquet, 09_edges.parquet
        ▼
[export]      atlas_data.json (เว็บ) + topics.csv / emerging.csv / forecasts.csv (นักวิเคราะห์)
              + manifest.json + เก็บ centroids ไว้ให้รอบหน้าคำนวณ novelty
        │  → output/atlas_data.json
        ▼
เว็บ: fetch('/data/atlas_data.json') → loader.normalize() → render
      (fetch ไม่สำเร็จ → ใช้ข้อมูล bundle ใน src/data/atlas.ts)
```

## 3. โครงสร้างเว็บ (web/)

| ไฟล์ | หน้าที่ |
|---|---|
| `src/pages/Home.tsx` | ประกอบทุก section, เรียก `loadAtlas()`, state ภาษา (th/en), data freshness badge |
| `src/lib/loader.ts` | **หัวใจของ live dashboard** — fetch JSON, `normalize()` schema pipeline→web, fallback |
| `src/data/atlas.ts` | interfaces (`AtlasNode`, `TopicForecast`, `TopicStatus`) + ข้อมูล bundle 71 สาขาจริง |
| `src/lib/i18n.ts` | dictionary th/en ทุกสตริง + helpers (`fmt`, `pct`) |
| `src/sections/AtlasMap.tsx` | bubble map SVG (pan/zoom ด้วย viewBox transform), `STATUS_STYLE`, DetailPanel + ForecastChart |
| `src/sections/EmergingThemes.tsx` | รายการหัวข้อเรียงตาม emergingScore + filter chips ตามสถานะ (ซ่อนตัวเองถ้าไม่มีข้อมูล status) |
| `src/sections/GroupRanking.tsx` | ตารางอันดับกลุ่ม คลิกเพื่อไฮไลต์บนแผนที่ |
| `src/sections/Insights.tsx` | อินไซต์ที่คำนวณจากข้อมูล ณ รอบนั้น (บางอันหดตัวถ้าไม่มี entity ที่เกี่ยว) |
| `src/sections/StatsBand.tsx`, `Header.tsx`, `Methodology.tsx` | แถบสถิติ, แถบนำทาง, ส่วนอธิบายวิธี |

### รูปแบบ bubble map

- SVG เดียว viewBox 1680×1040, pan/zoom ด้วย state `{k, x, y}` แปลงเป็น `transform` ของ `<g>` ราก
- wheel zoom ผูก non-passive listener ผ่าน callback ref (React ผูก passive โดยดีฟอลต์ → preventDefault ไม่ได้)
- node = วงกลม ขนาด ∝ √(จำนวนบทความ), สี = กลุ่ม, จุดส้มเล็กมุมขวาบน = EMERGING
- label ใช้ `paint-order: stroke` (พื้นขาวรอบตัวอักษร) และพลิกขึ้นเหนือ node ถ้าใกล้ขอบล่าง
- ตัวเลขยักษ์จาง ๆ (ghost numeral) เป็น watermark กลางแผนที่

## 4. Design tokens (ห้ามดrifท์)

| token | ค่า | ใช้กับ |
|---|---|---|
| bg | `#f5f6f2` | พื้นหลังหน้า |
| ink | `#161611` | ตัวอักษรหลัก |
| accent | `#FF5F1F` | จุดเน้น, EMERGING, score bar |
| panel | `#ffffff` radius 7px | การ์ด/แผง |
| font UI | IBM Plex Sans Thai | ข้อความทั่วไป |
| font data | IBM Plex Mono | ตัวเลข, eyebrow, label เทคนิค |
| font display | Noto Serif Thai | หัวข้อใหญ่ |

สถานะสี: EMERGING `#FF5F1F` · HOT `#E5484D` · DECLINING `#697177` · STABLE `#30A46C`

## 5. ทำไมไม่มี backend

ข้อมูลเปลี่ยนปีละ 4 ครั้ง (รันรายไตรมาส) → ความสดของข้อมูลไม่ต้องการ real-time API
static hosting ถูกกว่า เสถียรกว่า และ publish ผ่าน Kimi/ที่อื่นได้ทันที
ถ้าอนาคตต้องการ search/auth/per-user state ค่อยเพิ่ม backend (ดู ROADMAP.md §ทางเลือกอนาคต)

## 6. ข้อจำกัดที่รับรู้ไว้

- **forecast ระยะสั้น (2 ปี)** — ตั้งใจ: ข้อมูลบทความมี backfill lag, ทำนายยาวจะหลอกตัวเอง
- **emerging score เป็น percentile ภายในรอบรัน** — เปรียบเทียบข้ามรอบรันไม่ได้ตรง ๆ (ออกแบบให้เช่นนั้น: ใช้จัดอันดับ "ตอนนี้อะไรน่าสนใจ")
- **layout เปลี่ยนทุกรอบรัน** — ตำแหน่งวงกลมคำนวณใหม่ทุกครั้ง; ถ้าต้องการแผนที่นิ่งข้ามรอบ ดู ROADMAP.md §map-stability
