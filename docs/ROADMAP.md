# ROADMAP — แผนพัฒนาและไอเดียต่อยอด

> แผนหลักปัจจุบันอยู่ที่ `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md` (เฟส P0–P4)

## Phase ที่เสร็จแล้ว (baseline ปัจจุบัน)

| Phase | รายละเอียด | ไฟล์หลัก |
|---|---|---|
| **1 — Embedding (batch)** | รองรับ 2 โหมด: API (OpenAI-compatible: OpenAI/Gemini/OpenRouter/vLLM/Ollama) และ local (sentence-transformers, default BGE-M3); checkpoint ทุก 5,000 เรื่อง; resume ได้ | `pipeline/atlas/embed.py` |
| **2 — Topic Clustering** | 2 ชั้น: fine (~หลายร้อย topic) + coarse (กลุ่มใหญ่บนแผนที่); UMAP 10 มิติ + HDBSCAN; outlier → nearest centroid; c-TF-IDF ด้วย char_wb 3–5 gram (เหมาะกับไทย) | `pipeline/atlas/cluster.py` |
| **3 — Atlas web** | React bubble map (pan/zoom), drill-down, 2 ภาษา (ไทย/EN), insights ที่คำนวณจากข้อมูล, live loader + fallback | `web/` |
| **4 — Emerging Topic Analysis** | นิยาม TCI v2 (ดู EMERGING_SPEC.md: ช่วงเชื่อมั่น + ตัวกรองความกว้าง, 6 สถานะ), Kleinberg burst, novelty เทียบรอบก่อน, score 0–100, section "หัวข้อเกิดใหม่" บนเว็บ | `pipeline/atlas/emerging.py`, `web/src/sections/EmergingThemes.tsx` |
| **5 — Research Trend Forecasting** | naive/OLS/Poisson ต่อ topic, เลือกโมเดลด้วย backtest, แสดงเฉพาะที่ผ่าน skill gate (แม่นกว่า naive), กราฟในแผงรายละเอียด | `pipeline/atlas/forecast.py`, ForecastChart ใน AtlasMap.tsx |
| **+ LLM Labeling** | ตั้งชื่อ topic ไทย+อังกฤษ, cache ด้วย cache_key = hash ของ model + prompt (รันใหม่ไม่เสียเงินซ้ำ) | `pipeline/atlas/label.py`, `prompts/` |
| **+ ThaiJO Markdown ingest (P0)** | parse ไฟล์ .md จาก ThaiJO (ซ่อม PUA/สระอำ, ปีจาก Published→DOI→issue, ผู้แต่ง/สังกัด/อ้างอิง), `atlas profile` | `pipeline/atlas/sources/thaijo_md.py`, `pipeline/atlas/profile.py` |
| **+ Synthetic e2e (P0)** | คลังสังเคราะห์ 20K เรื่อง ฝังหัวข้อ EMERGING/WATCH/HOT/DECLINING แล้วตรวจว่ากู้คืนได้ | `pipeline/atlas/synth.py`, `pipeline/tests/test_e2e_synth.py` |
| **+ CI (P0)** | GitHub Actions: ruff + pytest + JSON Schema drift, e2e (`pytest -m slow`), web (type drift + build) | `.github/workflows/ci.yml` |
| **+ Live dashboard** | เว็บ fetch `/data/atlas_data.json` runtime — อัปเดตข้อมูลโดยไม่แก้โค้ด | `web/src/lib/loader.ts` |

## งานแนะนำลำดับถัดไป (เรียงตาม value/effort)

### 🟢 ทำได้เร็ว คุ้ม (1–3 วัน)

1. **Search box บนแผนที่** — ค้นหาหัวข้อ/คำสำคัญ (ไทย+อังกฤษ) แล้วไฮไลต์บนแผนที่
   - ทำที่ `web/` ล้วน (filter `data.nodes` ตาม `th/en/keywords`) ไม่ต้องแตะ pipeline
2. **Export รูป/ข้อมูลจากเว็บ** — ปุ่ม download PNG ของแผนที่ + CSV ของรายการ emerging
   - `svg → canvas → png` ฝั่ง client ล้วน
3. **Topic detail เจาะลึกขึ้น** — แสดง top journals, ตัวอย่างชื่อบทความล่าสุด (ต้องเพิ่มฟิลด์ใน export.py — มี metadata พร้อมอยู่แล้ว)
4. **โหมดเปรียบเทียบ 2 หัวข้อ** — overlay เส้นกราฟ 2 เส้นในแผง detail

### 🟡 ปานกลาง (1–2 สัปดาห์)

5. **Map stability ข้ามรอบรัน** — ตอนนี้ตำแหน่ง node เปลี่ยนทุกไตรมาส ผู้ใช้จำแผนที่เดิมไม่ได้
   - วิธี: init UMAP 2D ของรอบใหม่ด้วยตำแหน่งรอบก่อน (เฉพาะ topic ที่ match ได้ด้วย centroid similarity ≥ 0.7)
   - แตะ `pipeline/atlas/layout.py` + เก็บ layout เดิมใน `work/prev/`
6. **Journal view** — หน้า/โหมดแสดงวารสาร: วารสาร X มีบทความกระจายใน topic ไหนบ้าง (ใช้ `journal_name` ที่ ingest เก็บไว้)
   - เพิ่ม aggregation step ใน pipeline + หน้าใหม่ในเว็บ
7. **Diff รอบรัน ("อะไรเปลี่ยนตั้งแต่ไตรมาสก่อน")** — หัวข้อใหม่, หัวข้อที่เปลี่ยนสถานะ, mover ที่ score ขึ้นแรงสุด
   - ข้อมูล prev centroids มีอยู่แล้ว; เพิ่มการเก็บ snapshot status รอบก่อน + section เล็กในเว็บ
8. **Emerging narrative อัตโนมัติ** — ให้ LLM เขียนย่อหน้าสรุป "ทำไมหัวข้อนี้ emerging" จาก metric + ตัวอย่างบทความ (prompt พร้อมแล้วที่ `prompts/emerging_narrative.th.md`)

### 🔵 ใหญ่ ต้องวางแผน (เดือนขึ้นไป)

9. **Author / affiliation network** — metadata มี authors+affiliations อยู่แล้ว; ทำ co-authorship graph ต่อ topic (ใครคุยกับใครในเรื่องนี้)
10. **Co-citation edges** — ถ้า export TCI มี references จะได้ edge คุณภาพสูงกว่า semantic similarity
11. **API backend + auth** — ถ้าต้องการ saved views, alerts ("แจ้งเตือนเมื่อหัวข้อ X เข้าเกณฑ์ EMERGING"), หรือข้อมูลที่ห้าม public
    - แนวทาง Kimi platform: backend-building (Hono + tRPC + Drizzle + MySQL, Kimi login ในตัว)
12. **ลงทะเบียน incremental** — ตอนนี้รันทั้ง corpus ใหม่ทุกไตรมาส (200K เรื่องยังสบาย); ถ้าโตเป็นล้านเรื่องค่อยทำ online clustering

## แนวคิดเชิงนโยบายที่ข้อมูลพร้อมจะตอบ (เสนอผู้บริหารได้เลย)

- **ช่องว่างงานวิจัย** — คู่ topic ที่อยู่ใกล้กันเชิงความหมายแต่ไทยทำน้อยทั้งคู่ (หางยาวของแผนที่)
- **จับคู่งานวิจัยกับวารสาร** — บรรณาธิการเห็นว่าหัวข้อ emerging ไปลงวารสารไหน → ตัดสินใจเปิด section ใหม่
- **ภาพรวมระดับประเทศรายปี** — สถิติ share ของแต่ละกลุ่มเทียบปี = วัตถุดิบรายงานนโยบาย
- **Early warning** — topic ที่ DECLINING หลายไตรมาสติดในสาขาสำคัญของประเทศ

## สิ่งที่ตั้งใจไม่ทำ (และเหตุผล)

| ไม่ทำ | เพราะ |
|---|---|
| Real-time updates | ข้อมูล TCI เปลี่ยนช้า — รายไตรมาสเพียงพอ, static site เสถียรกว่า |
| Login/user accounts (ตอนนี้) | เป็นเครื่องมือสาธารณะ — เพิ่มภายหลังได้ถ้าต้องการ saved views |
| ทำนายยาว > 2 ปี | ข้อมูลมี backfill lag — ทำนายยาวจะสร้างความมั่นใจเทียม |
| Score เทียบข้ามรอบรัน | score เป็น percentile ภายในรอบโดยออกแบบ — ใช้มิติดิบถ้าจะเทียบข้ามรอบ |
