# ARCHITECTURE — สถาปัตยกรรมระบบ

## 1. หลักการออกแบบ

1. **แยกผลิตจากแสดงผลสมบูรณ์** — pipeline (Python, batch, หนัก) กับเว็บ (React, static, เบา) รู้จักกันผ่าน contract v2 (`data/<release>/` + `data/latest.json`; `atlas_data.json` คงไว้เพื่อความเข้ากันได้เท่านั้น) เปลี่ยนโค้ดฝั่งใดฝั่งหนึ่งได้อิสระ ตราบใดที่ data contract ไม่เปลี่ยน
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
[methods]    lexicon วิธีวิจัย TH/EN + ตัวอ่านขนาดตัวอย่าง → วิธีรายบทความ/หัวข้อ/ปี (+ บันทึก LLM ถ้าเปิด)  → work/12_methods_*
[journals]   ตัวตนวารสาร (+ registry/journals.csv) · D1–D5, D7 · อ่านแถวผู้แต่งที่นี่ที่เดียว เผยแพร่เฉพาะยอดรวม → work/13_journal*
[match]      ดัชนี trigram (fold เดียวกับ foldText ของเว็บ; ไม่มีข้อความบทความ)                          → work/14_match.json
        ▼
[institutions] สถาบัน (ตารางชื่อ → ROR → ชื่อตามที่เขียน), เครือข่ายความร่วมมือ, ประเทศคู่, จังหวัด, ข้อเสนอ R6 — อ่านแถวผู้แต่งเฉพาะสังกัด → work/15_*
[sdg]        หัวข้อ → SDG/BCG/แผน ววน./หมุดหมายแผนฯ 13 (centroid cosine หรือคำสำคัญ)                    → work/16_*
[benchmark]  ไทยเทียบโลกจาก OpenAlex (16 requests; offline = ข้ามพร้อมเหตุผล)                           → work/17_*
[gaps]       ช่องว่างงานวิจัย R5 + ความเสี่ยงกระจุกตัว E10                                              → work/18_*
        ▼
[references] แนวปฏิบัติการอ้างอิงรายวารสาร D7 + "ถูกอ้างใน TCI" R12 (DOI → ชื่อเรื่องตรงตัว; เผยแพร่เมื่อ coverage ถึงเกณฑ์) → work/19_*
[search]     ดัชนีค้นหาบทความแบบแบ่งไฟล์ R2 (ชื่อเรื่อง + คำสำคัญผู้แต่ง, pythainlp newmm) + จุดกาแล็กซี R8 (จาก 09_galaxy) → work/20_*
[kwtrends]   แนวโน้มคำสำคัญของผู้แต่งรายปี R7 + อภิธานศัพท์ไทย↔อังกฤษต่อหัวข้อ/ทั้งคลัง                → work/21_*
        ▼
[export]     output/atlas_data.json (schema 1.1 — เว็บ v2 ไม่อ่านแล้ว) + output/data/<release>/ (contract v2) + latest.json
        ▼
atlas validate  →  atlas publish --site <โฟลเดอร์เว็บ>  →  data/<release>/ + data/latest.json + atlas-offline.html
                                                           (+ data/feeds/*.xml เมื่อตั้ง publish.site_url)
เว็บ v2 อ่าน data/latest.json แบบ path สัมพัทธ์จาก BASE_URL — ไม่เรียก API ตอน runtime; อัปเดตรายไตรมาส = คัดลอกโฟลเดอร์ data
```

- **P4:** ลำดับ step `… gaps → references → search → kwtrends → export`; `export` (ผ่าน `atlas/export_research.py`) เขียน `references.json`, `search/{meta,vocab}.json` + `search/idx-<NNN>.json` + `search/docs-<NNN>.json`, `galaxy.json`, `kwtrends.json` และ `cited_in_tci` / `glossary` ในรายหัวข้อ (contract 2.3) — โมดูลที่ข้ามบอกเหตุผลใน `manifest.skipped_modules`; `search/` และ `galaxy.json` อยู่นอก HTML ออฟไลน์; ฟีด Atom ไม่ใช่ส่วนของรอบข้อมูล แต่ `atlas publish` (`atlas/feeds.py`) สร้างจากรอบที่อยู่บนเว็บ จึงต้องรู้ที่อยู่สาธารณะ (`publish.site_url`); ค้นหาในเบราว์เซอร์ใช้การตัดคำแบบยาวที่สุดก่อนกับ vocab ที่เผยแพร่ (ไม่มี pythainlp ฝั่งเว็บ) ตรึงด้วย `pipeline/tests/fixtures/search_parity.json`
- **P3:** ลำดับ step `match → institutions → sdg → benchmark → gaps → export`; แคช ROR อยู่ใน `state_dir/ror/` (ข้อมูลถาวร) และคำขอ OpenAlex ของ `benchmark` ใช้ `state_dir/openalex/` เดียวกับ taxonomy; `export` เขียน `institutions*.json`, `regions.json`, `sdg.json`, `global.json`, `gaps.json` และ `overview.executive` (contract 2.2); เว็บแสดงเป็น 6 หน้า lazy และเส้นขอบจังหวัดอยู่ใน chunk ของ `/regions`
- **P2:** `export` เขียน `state_dir/releases/<release>/snapshot.json` ทุกรอบ แล้วรอบถัดไปเทียบกับ snapshot นั้นเป็น `diff.json` (รอบก่อน P2 ใช้ `output/data/<prev>/`); `match.json` อยู่นอก HTML ออฟไลน์ และเว็บคำนวณ match ในเบราว์เซอร์ล้วน ๆ (`web/src/lib/matcher.ts` ตรึงด้วย `pipeline/tests/fixtures/match_parity.json`)
- งาน LLM ทั้งหมดเป็นระดับหัวข้อ (ชื่อ คู่ซ้ำ คำอธิบาย บทสรุป) ผ่าน adapter เดียวแบบ OpenAI-compatible (`atlas/llm.py`) บนแกน HTTP ร่วมกับ embedding (`atlas/api_http.py`) — ไม่มี SDK ของผู้ให้บริการรายใด
- รอบข้อมูลเลือกครั้งเดียวที่ `cluster` (`pipeline.release` หรือไตรมาสของวันที่รัน) แล้วบันทึกพร้อมเวลา snapshot ใน `work/04_topics_meta.json`; ทุกขั้นหลังจากนั้นและ validate/publish ใช้รอบที่บันทึกไว้ (`atlas.state.work_release` — config ที่ชี้รอบอื่นถูกปฏิเสธ) และใช้ snapshot เดียวกันสำหรับ as_of_year, nowcast และ generated_at
- ข้อมูลที่ต้องอยู่ข้ามรอบอยู่ใน `state_dir` เท่านั้น: embeddings, llm_cache, releases/<release>/ (ID หัวข้อ, ตำแหน่งบนแผนที่), openalex/
- รันซ้ำ step ใดของรอบเดิม = ผลเหมือนเดิม (อ่านรอบ *ก่อน* เสมอ เขียนทับเฉพาะโฟลเดอร์ของรอบนี้) — ความปลอดภัยของรอบ: ชื่อรอบถูกตรวจรูปแบบ, ID หัวข้อไม่ถูกใช้ซ้ำ, สั่งรันรอบเก่าขณะมีรอบใหม่กว่าอยู่แล้วจะถูกปฏิเสธ, ไม่มี state หัวข้อของรอบก่อนหน้า = error (ไม่เดา)

## 3. โครงสร้างเว็บ (web/)

เว็บ v2: `./data/latest.json` → `./data/<release>/*.json` (HttpSource) หรือข้อมูลฝังในไฟล์ออฟไลน์ (EmbeddedSource) → `loadRelease()` → render (HashRouter, ไม่มีข้อมูลสำรองฝังในเว็บ)

| ไฟล์ | หน้าที่ |
|---|---|
| `src/data/source.ts` + `src/data/release.ts` | แหล่งข้อมูล (Http \| Embedded) และ loader ที่ตรวจ schema major — แถบแจ้งเมื่อโหลดไม่ได้ |
| `src/data/contract.ts` (generated) + `types.ts` | ชนิดข้อมูลจาก `contract.schema.json` (`npm run gen:types`) |
| `src/pages/*Page.tsx` | overview · atlas · topics/:id · emerging · compare · data · about · brief + หน้า lazy ของ P2–P4 (journals … gaps, search · galaxy · keywords · references) |
| `src/embed/` | กราฟฝัง `/embed/topic/:id`, `/embed/emerging` (ไม่มีเมนู/ส่วนท้าย; chunk lazy) + ปุ่มคัดลอก `<iframe>` และลิงก์ฟีด |
| `src/lib/{searchTokens,searchClient,citation,galaxyGl}.ts` | ตัดคำค้น (ตรงกับ Python) · ค้นหาแบบโหลดเฉพาะ shard (doc shard ≤ 6 ต่อคำค้น) · RIS/BibTeX ไม่มีผู้แต่ง · WebGL2 (`gl.POINTS` draw call เดียว + กริดหาจุดใกล้สุด) |
| `src/charts/` | forest plot · portfolio matrix · trend · multi-line (ทุกกราฟมีแท็บตาราง) |
| `src/features/atlas/` | แผนที่ภูมิประเทศ (canvas + SVG overlay) + ดัชนีหัวข้อ |
| `src/strings/` | ข้อความ UI ไทย+อังกฤษ (`i18n.test.ts` ตรวจครบคู่) — หน้า lazy ใช้ไฟล์ strings ของตัวเองผ่าน `useStrings(dict)` เพื่อไม่ให้ข้อความเข้า entry chunk (งบ 180 KB gzip; หลัง P4 ≈ 171 KB เพราะ `/atlas` และ `/brief` เป็น lazy แล้ว) |
| `src/styles/tokens.css` | design tokens light/dark |

รายละเอียดคำสั่งและโครงสร้างโค้ด: `web/README.md`

### แผนที่ภูมิประเทศ

- พื้นที่แผนที่ 10 × 6 ช่อง (A–J, 1–6) วาดสีสาขาตามความหนาแน่น + เส้นชั้นความสูงบน canvas; หัวข้อที่มีสถานะเด่นเป็นสัญลักษณ์ SVG ที่โฟกัสได้ ส่วนหัวข้ออื่นเป็นจุดและค้นหาได้
- ป้ายชื่อทุกชนิดผ่านการวางแบบเลี่ยงการชน (`src/lib/labels.ts`, `placeCentered`); pan/zoom ด้วยลาก ปุ่ม และแป้นพิมพ์

## 4. Design tokens

ฐาน Civic modern: ฟอนต์ Sarabun (self-hosted), civic blue `#0f3557`, link `#1a5bb0`, focus yellow `#ffd43b`, ink `#0b0c0e` — ค่าทั้งหมดอยู่ที่ `DESIGN.md` และ `web/src/styles/tokens.css` (ตรวจ CVD + contrast ด้วย `palette.test.ts`); สถานะแสดงด้วยรูปทรง + สี + ชื่อเสมอ

## 5. ทำไมไม่มี backend

ข้อมูลเปลี่ยนปีละ 4 ครั้ง (รันรายไตรมาส) → ความสดของข้อมูลไม่ต้องการ real-time API
static hosting ถูกกว่า เสถียรกว่า และ publish ผ่าน Kimi/ที่อื่นได้ทันที
ค้นหาบทความทั้งคลัง (P4) ก็ไม่ต้องมี backend: ดัชนีเป็นไฟล์สถิตแบ่ง shard ที่เบราว์เซอร์โหลดเฉพาะส่วนที่ต้องใช้
ถ้าอนาคตต้องการ auth/per-user state หรือค้นหาบทคัดย่อ (full-text) ค่อยเพิ่ม backend (ดู ROADMAP.md §ทางเลือกอนาคต)

## 6. ข้อจำกัดที่รับรู้ไว้

- **forecast ระยะสั้น (2 ปี)** — ตั้งใจ: ข้อมูลบทความมี backfill lag, ทำนายยาวจะหลอกตัวเอง
- **สถานะใช้ช่วงเชื่อมั่น (v2)** — score ยังเป็น percentile ภายในรอบ เทียบข้ามรอบไม่ได้
- **layout นิ่งข้ามรอบ (P1)** — UMAP เริ่มจากตำแหน่งรอบก่อน + Procrustes + anchor ทำให้หัวข้อเดิมไม่ย้ายที่ ยกเว้นเมื่อ refit ทั้งก้อน (`topics.refit_every_releases`)
