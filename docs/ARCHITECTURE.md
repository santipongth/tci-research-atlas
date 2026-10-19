# ARCHITECTURE — สถาปัตยกรรมระบบ

## 1. หลักการออกแบบ

1. **แยกผลิตจากแสดงผลสมบูรณ์** — pipeline (Python, batch, หนัก) กับเว็บ (React, static, เบา) รู้จักกันผ่านไฟล์เดียว: `atlas_data.json` เปลี่ยนโค้ดฝั่งใดฝั่งหนึ่งได้อิสระ ตราบใดที่ data contract ไม่เปลี่ยน
2. **ไม่มี backend/database** — ลดภาระ infra ของทีมเป็นศูนย์; เว็บ static ใช้ได้ทุกที่ (Kimi publish, GitHub Pages, nginx)
3. **ทุกอย่าง resume ได้** — pipeline เขียน checkpoint หลังทุก step ลง `work_dir`; รันใหม่ = ข้าม step ที่ทำแล้ว (เลือกด้วย `--step/-s`)
4. **ตัวเลขต้องอธิบายได้** — ทุก metric ที่ขึ้นหน้าเว็บมีนิยามเขียนไว้ใน `EMERGING_SPEC.md` และทดสอบใน `tests/` เพราะผู้บริหารจะถือตัวเลขนี้ไปคุยต่อ
5. **ภาษาไทยเป็นพลเมืองชั้นหนึ่ง** — embedding multilingual, c-TF-IDF ตัดคำด้วย pythainlp + author keywords, UI สองภาษา, ปี ค.ศ. เป็นมาตรฐานกลาง (แปลงจาก พ.ศ. ที่ ingest)
6. **state แยกจาก work** — `work_dir` ลบได้เสมอ; `state_dir` เก็บสิ่งที่ต้องอยู่ข้ามรอบ (embedding store, LLM cache, ID หัวข้อและตำแหน่งบนแผนที่ของแต่ละรอบ, งานอ้างอิง OpenAlex)

## 2. การไหลของข้อมูล (data flow)

```
corpus/*.md (ThaiJO scrape)            ← ตรวจก่อนด้วย: atlas profile
        │
        ▼
[ingest]     parse .md ทีละชุด (input.batch_files) → ตารางทันที · ปี: Published→DOI→median issue · dedup
        │  → work/01_articles · 01_authors (+org_key) · 01_references · 01_ingest_errors (ไฟล์ที่อ่านไม่ได้)
        ▼
[preprocess] doc_text = title + keywords + abstract (≤ 6000 ตัวอักษร)                      → work/02_docs
        ▼
[embed]      api (runner ของ P0: retry ไม่จำกัด, journal, resume — `atlas embed`) | local (BGE-M3) | lite (CI)
             เวกเตอร์ถาวรใน state/embeddings/<store_id>     → work/03_embeddings.npy + 03_meta.json (docs_fingerprint)
        ▼
[cluster]    fit (UMAP→HDBSCAN | Leiden) หรือ assign เข้าหัวข้อรอบก่อน (topics.mode) → ID ถาวร T000123 + lineage
        │  → work/04_* · state/releases/<release>/topics/{assignments,registry,lineage}
        ▼
[taxonomy]   kNN vote กับงานอ้างอิงไทยใน OpenAlex → subfield → field = กลุ่มบนแผนที่
             (OpenAlex key เป็นทางเลือก; งบรายวันหมด (429) = หยุดสะอาด แล้วใช้กลุ่ม agglomerative พร้อมเหตุผล)
        │  → work/10_taxonomy (+ meta: ความแม่นยำ held-out)
        ▼
[label]      LLM runner (cache/journal state/llm_cache, งบ, หยุด/ทำต่อ, lock/status ของ P0) หรือ off → ชื่อที่บรรณาธิการแก้ชนะเสมอ
        │  + คู่หัวข้อที่อาจซ้ำ (ข้อเสนอ ไม่รวมเอง)  → work/05_labels · 05_labels_meta.json · 05_merge_suggestions
        ▼
[series]     topic × ปี + ปีสมบูรณ์ล่าสุด (กฎ v3: backfill guard) + ตารางปีหลังจากนั้น (ใช้ทำ nowcast เท่านั้น)
        │  → work/06_series · 06_months · 06_partial_year · 06_meta.json · ตารางวารสาร/สถาบัน
        ▼
[emerging]   Emerging v3 (docs/EMERGING_SPEC.md)                                          → work/07_emerging
[keywords]   emerging keywords ระดับคำ (Carley/Porter)                                    → work/07_keywords
        ▼
[forecast]   share × ยอดรวม (โมเดลยอดรวมแยกตามจุดตั้งต้นของแต่ละ fold — ไม่มองข้อมูลอนาคต):
             naive / drift / NB GLM / damped ETS · rolling-origin CV · skill gate · ช่วง 80/95 conformal
             คาลิเบรตจากเรคคอร์ด backtest ที่ "ซื่อสัตย์" ของโมเดลที่เลือก · แสดงเมื่อมีจุดซื่อสัตย์ ≥ forecast.min_honest_points
             nowcast เฉพาะปีปฏิทินที่กำลังดำเนินอยู่เท่านั้น
        │  → work/08_forecasts · 08_forecast_meta.json
        ▼
[narrate]    คำอธิบายหัวข้อ + บทสรุปผู้บริหาร (ตัวเลขจาก pipeline เท่านั้น ตรวจซ้ำ; เขียนใหม่ 1 ครั้ง ไม่ผ่าน = ประโยคแม่แบบ)
        │  → work/11_narratives · 11_brief.json
        ▼
[layout]     แผนที่นิ่งข้ามรอบ (UMAP เริ่มจากรอบก่อน + Procrustes + anchor) + galaxy บทความ → work/09_*
        ▼
[export]     output/atlas_data.json (schema 1.1 — เว็บปัจจุบัน) + output/data/<release>/ (contract v2) + latest.json
        ▼
atlas validate  →  atlas publish --site <โฟลเดอร์เว็บ>  →  data/<release>/ + data/latest.json + atlas-offline.html
เว็บ v2 อ่าน data/latest.json แบบ path สัมพัทธ์จาก BASE_URL — ไม่เรียก API ตอน runtime; อัปเดตรายไตรมาส = คัดลอกโฟลเดอร์ data
```

- งาน LLM ทั้งหมดเป็นระดับหัวข้อ (ชื่อ คู่ซ้ำ คำอธิบาย บทสรุป) ผ่าน adapter เดียวแบบ OpenAI-compatible (`atlas/llm.py`) บนแกน HTTP ร่วมกับ embedding (`atlas/api_http.py`) — ไม่มี SDK ของผู้ให้บริการรายใด
- ข้อมูลที่ต้องอยู่ข้ามรอบอยู่ใน `state_dir` เท่านั้น: embeddings, llm_cache, releases/<release>/ (ID หัวข้อ, ตำแหน่งบนแผนที่), openalex/
- รันซ้ำ step ใดของรอบเดิม = ผลเหมือนเดิม (อ่านรอบ *ก่อน* เสมอ เขียนทับเฉพาะโฟลเดอร์ของรอบนี้) — ความปลอดภัยของรอบ: ชื่อรอบถูกตรวจรูปแบบ, ID หัวข้อไม่ถูกใช้ซ้ำ, สั่งรันรอบเก่าขณะมีรอบใหม่กว่าอยู่แล้วจะถูกปฏิเสธ, ไม่มี state หัวข้อของรอบก่อนหน้า = error (ไม่เดา)

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
- **สถานะใช้ช่วงเชื่อมั่น (v2)** — score ยังเป็น percentile ภายในรอบ เทียบข้ามรอบไม่ได้
- **layout นิ่งข้ามรอบ (P1)** — UMAP เริ่มจากตำแหน่งรอบก่อน + Procrustes + anchor ทำให้หัวข้อเดิมไม่ย้ายที่ ยกเว้นเมื่อ refit ทั้งก้อน (`topics.refit_every_releases`)
