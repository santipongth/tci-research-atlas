# ARCHITECTURE — สถาปัตยกรรมระบบ

> เอกสารนี้อธิบายว่าข้อมูลไหลจากคลังบทความไปถึงหน้าเว็บอย่างไร · สเปกไฟล์ทุกตัวอยู่ใน `docs/DATA_SPEC.md` · วิธีรันงานจริงอยู่ใน `docs/OPERATIONS.md` · รูปแบบคลังสำหรับทีมข้อมูลอยู่ใน `docs/corpus/README.md`

## 1. หลักการออกแบบ

1. **แยกฝั่งผลิตกับฝั่งแสดงผลขาดจากกัน** — pipeline (Python, batch, งานหนัก) กับเว็บ (React, static, เบา) รู้จักกันผ่าน data contract v2 เท่านั้น (`data/<release>/*.json` + `data/latest.json`) แก้โค้ดฝั่งใดฝั่งหนึ่งได้อิสระตราบใดที่ contract ไม่เปลี่ยน (`atlas_data.json` schema 1.1 ยังถูกเขียนเพื่อความเข้ากันได้ แต่เว็บไม่อ่านแล้ว)
2. **ไม่มี backend และฐานข้อมูล** — เว็บเป็นไฟล์ static วางบน host ใดก็ได้ (GitHub Pages, nginx, host ของหน่วยงาน) ไม่เรียก API หรือ LLM ตอนเปิดหน้า ไม่โหลดอะไรจากเซิร์ฟเวอร์ภายนอก
3. **หยุดแล้วทำต่อได้ทุกจุด** — ทุก step เขียน checkpoint ลง `work_dir`; รันใหม่เฉพาะ step ที่ต้องการได้ (`-s/--step`); งานยาว (embedding, LLM) มี journal, lock, ปุ่มหยุด และทำต่อจากที่ค้างได้
4. **ตัวเลขต้องอธิบายได้** — ทุกตัวเลขบนเว็บมีนิยามใน `docs/EMERGING_SPEC.md` / `docs/DATA_SPEC.md` และมี test ล็อกไว้ เพราะผู้บริหารนำตัวเลขไปสื่อสารต่อ
5. **ภาษาไทยเป็นภาษาหลัก** — embedding หลายภาษา, c-TF-IDF ตัดคำด้วย pythainlp + คำสำคัญของผู้แต่ง, UI สองภาษา, ปี ค.ศ. เป็นมาตรฐานกลาง (แปลงจาก พ.ศ. ตอน ingest)
6. **แยก state ออกจาก work** — `work_dir` ลบทิ้งได้เสมอ; `state_dir` เก็บสิ่งที่ต้องอยู่ข้ามรอบและห้ามลบ (ดู §3)
7. **ไม่เผยแพร่ข้อมูลระบุตัวบุคคล (PDPA)** — ชื่อผู้แต่งถูกอ่านเพื่อหาสังกัดเท่านั้น เผยแพร่แค่ตัวเลขรวม ไม่มีบทคัดย่อในไฟล์ที่เผยแพร่ และมีด่านตรวจก่อนเผยแพร่ทุกรอบ (§5)

## 2. ภาพรวมทั้งระบบ

```
 ทีมข้อมูล TCI                      pipeline/ (Python)                           เว็บ (static)
 ─────────────                     ──────────────────                           ──────────────
 corpus/                           atlas quarterly (คำสั่งเดียวต่อรอบ)
   articles/*.jsonl(.gz) ──┐         profile → embed → llm → run (23 steps)
   journals.csv            ├──────▶            → validate → publish ──────────▶ web/dist/
   institutions_aliases.csv│                     │            │                   data/latest.json
   province_population.csv │          work_dir/ (checkpoint, ลบได้)               data/<release>/…
   ror.zip               ──┘          state_dir/ (ถาวร, ห้ามลบ)                    data/feeds/…  (ถ้าตั้ง site_url)
 (หรือโฟลเดอร์ .md จาก ThaiJO                                                     atlas-offline.html
  หรือไฟล์ตารางไฟล์เดียว)                                                              │
                                    runs/<release>/  ← บันทึกของรอบ                    ▼
                                    deploy/<release>/site/ + zip ← พร้อมอัปโหลด   host ใดก็ได้ / GitHub Pages
```

## 3. ข้อมูลเข้า

### 3.1 รูปแบบคลัง (`input.format`)

| รูปแบบ | ตัวอ่าน | ใช้เมื่อ |
|---|---|---|
| `corpus_jsonl` — **corpus format 1.0** (แนะนำ) | `atlas/sources/corpus_jsonl.py` ตาม model ใน `atlas/schema/corpus.py` (`tci-atlas-corpus/1.0`) | ทีมข้อมูลเตรียมไฟล์ JSON Lines หนึ่งบทความต่อบรรทัดใน `corpus/articles/*.jsonl` หรือ `.jsonl.gz` ชื่อฟิลด์ตาม Crossref/JATS/OpenAlex; คีย์ที่ไม่รู้จัก = error; บรรทัดที่อ่านไม่ได้เป็นแถว error (ไม่ crash ไม่ทิ้งเงียบ); ประเภทใน `input.exclude_article_types` (เช่น editorial) ถูกตัดและนับไว้ |
| `thaijo_md` | `atlas/sources/thaijo_md.py` | โฟลเดอร์ไฟล์ .md ที่ scrape จาก ThaiJO (ซ่อมอักษร PUA, ปีจาก Published → DOI → ปีของฉบับ) — ค่าดีฟอลต์ของโค้ดเมื่อไม่ระบุ format |
| `table` | `atlas/ingest.py` | ไฟล์ csv/json/jsonl/parquet ไฟล์เดียว จับคู่ชื่อคอลัมน์ด้วย `input.columns` |

- `atlas corpus schema` เขียน `docs/corpus/corpus.schema.json` จาก model; `atlas corpus convert` แปลงโฟลเดอร์ .md เป็น format 1.0 โดยคง article id เดิม (ประวัติหัวข้อและ embedding ที่จ่ายไปแล้วใช้ต่อได้)
- รหัสบทความต้องไม่เปลี่ยนข้ามไตรมาส: ใช้ id ที่ให้มา → URL ของ ThaiJO → DOI → hash ของวารสาร+ชื่อเรื่อง+ปี
- `atlas quarterly` และ `atlas profile` ตรวจรูปแบบจากโฟลเดอร์ให้เอง (`profile.detect_format`: มีไฟล์ `articles/*.jsonl*` = `corpus_jsonl`)

### 3.2 ไฟล์ที่มากับคลัง (companion files — `atlas/companions.py`)

| ไฟล์ | ใช้ทำอะไร | ถ้าไม่มี |
|---|---|---|
| `journals.csv` | ทะเบียนวารสารต่อ `journal_key` (ชื่อ, ISSN, tier, สาขา TCI) | **บังคับ** สำหรับ `corpus_jsonl` |
| `institutions_aliases.csv` | ชื่อสังกัดตามที่เขียน → สถาบันเดียว | ใช้ ROR และชื่อตามที่เขียน |
| `province_population.csv` | ประชากรรายจังหวัด → บทความต่อประชากร 100,000 คน | ไม่แสดงตัวเลขต่อประชากร |
| `ror.zip` | ROR data dump (CC0) สำหรับระบุตัวสถาบัน | ข้ามขั้น ROR |

วางไว้ข้าง `articles/` แล้ว `atlas quarterly` จะใช้ไฟล์เหล่านี้แทนค่าใน `config.yaml` ให้เอง · `atlas profile` ตรวจทุกไฟล์ด้วยตัวอ่านเดียวกับ pipeline (error ที่เห็นคือ error ที่รอบจริงจะเจอ) และเขียนรายการสังกัดที่พบบ่อยแต่ยังไม่มีในตาราง alias เป็น CSV ให้ทีมเติม (ระดับสถาบันเท่านั้น ไม่มีชื่อบุคคล) · ฉบับในเครื่องของผู้ดูแลอยู่ที่ `pipeline/registry/` (git-ignored; repo มีแต่ `*.example.csv`)

ข้อมูลอ้างอิงสาธารณะที่ commit ไว้: `pipeline/atlas/data/th_provinces.csv` (77 จังหวัด ISO 3166-2:TH) และ `frameworks.yaml` (SDG/BCG/แผน ววน./หมุดหมายแผนฯ 13 + คำสำคัญ)

## 4. Pipeline: ลำดับ step

ลำดับจริงอยู่ที่ `STEPS` ใน `pipeline/atlas/pipeline.py` (23 step) — `atlas run` รันทั้งหมดตามลำดับนี้ หรือเลือกบาง step ด้วย `-s`

```
[ingest]       atlas/ingest.py — อ่านคลังทีละชุด (input.batch_files) → ตาราง · ปี พ.ศ.→ค.ศ. · ตัดซ้ำ (id → DOI → ชื่อเรื่อง+ปี)
               ไฟล์/บรรทัดเสียเกิน input.max_error_ratio = หยุด
        │  → work/01_articles · 01_authors (+org_key) · 01_references · 01_ingest_errors
        ▼
[preprocess]   atlas/preprocess.py — doc_text = ชื่อเรื่อง + คำสำคัญ + บทคัดย่อ (≤ 6,000 ตัวอักษร)        → work/02_docs
        ▼
[embed]        atlas/embed.py — local (BGE-M3, ค่าดีฟอลต์) | api (OpenAI-compatible) | lite (CI/ทดสอบเท่านั้น)
               เวกเตอร์ถาวรใน state/embeddings/ (§6)                       → work/03_embeddings.npy + 03_meta.json
        ▼
[cluster]      atlas/cluster.py + lineage.py — fit (UMAP→HDBSCAN หรือ Leiden) หรือ assign เข้าหัวข้อรอบก่อน (topics.mode)
               → ID ถาวร T000123 + lineage (continue/merge/split/new/retired) · เลือกชื่อรอบ (release) ที่นี่ครั้งเดียว
        │  → work/04_* (04_topics_meta.json เก็บรอบ + เวลา snapshot) · state/releases/<release>/topics/
        ▼
[taxonomy]     atlas/taxonomy.py — kNN vote กับงานไทยใน OpenAlex → subfield → field = กลุ่มบนแผนที่
               (key เป็นทางเลือก; งบรายวันหมด/ออฟไลน์ = ใช้กลุ่ม agglomerative พร้อมเหตุผล)   → work/10_taxonomy*
        ▼
[label]        atlas/label.py — ชื่อหัวข้อ TH/EN ผ่าน LLM runner (หรือ off = ใช้คำสำคัญ) · ชื่อที่บรรณาธิการแก้ชนะเสมอ
               + คู่หัวข้อที่อาจซ้ำ (เป็นข้อเสนอ ไม่รวมเอง)                          → work/05_labels* · 05_merge_suggestions
        ▼
[series]       atlas/topics_time.py — หัวข้อ × ปี, ปีสมบูรณ์ล่าสุด (กฎ v3: backfill guard), เดือนของปีที่ยังไม่ครบ → work/06_*
        ▼
[emerging]     atlas/emerging.py — นิยาม v3 (ช่วงเชื่อมั่น + ตัวกรองความกว้าง, 6 สถานะ, burst, score)      → work/07_emerging
[keywords]     atlas/keywords.py — คำสำคัญที่กำลังโตระดับคำ                                          → work/07_keywords
        ▼
[forecast]     atlas/forecast.py — share × ยอดรวม · naive/drift/NB GLM/damped ETS · rolling-origin CV · skill gate
               · ช่วง 80/95 แบบ conformal · nowcast เฉพาะปีที่กำลังดำเนินอยู่              → work/08_forecasts*
        ▼
[narrate]      atlas/narrative.py — คำอธิบายหัวข้อ + บทสรุปผู้บริหาร (LLM ผ่าน runner; ตัวเลขต้องมาจาก pipeline:
               grounding_error + jargon_in ไม่ผ่าน = เขียนใหม่ 1 ครั้ง แล้วใช้ประโยคแม่แบบ)      → work/11_narratives · 11_brief.json
        ▼
[layout]       atlas/layout.py — แผนที่หัวข้อนิ่งข้ามรอบ (UMAP เริ่มจากตำแหน่งรอบก่อน + Procrustes + anchor)
               + กาแล็กซีบทความ                                   → work/09_layout · 09_edges · 09_galaxy · state/releases/<release>/layout.parquet
        ▼
[methods]      atlas/methods.py — วิธีวิจัย (lexicon TH/EN + ขนาดตัวอย่าง) รายบทความ/หัวข้อ/ปี (+ บันทึก LLM ถ้าเปิด) → work/12_*
[journals]     atlas/journals.py (+ journal_metrics, journal_topics, registry) — D1–D5, D7, สัดส่วนหัวข้อรายปี   → work/13_*
[match]        atlas/matcher.py — ดัชนี trigram สำหรับ "วางบทคัดย่อ" (เก็บแค่น้ำหนัก ไม่มีข้อความ)          → work/14_match.json
        ▼
[institutions] atlas/institutions.py (+ institutions_ref, places, orgs) — สถาบัน (alias → ประเทศ → ROR → ชื่อตามที่เขียน),
               เครือข่ายความร่วมมือ, ประเทศคู่, จังหวัด + หัวข้อเด่นรายจังหวัด, ข้อเสนอคู่ร่วมมือ         → work/15_*
[sdg]          atlas/sdg.py — หัวข้อ → SDG/BCG/แผน ววน./แผนฯ 13 (ดีฟอลต์ lexical; embedding หลังปรับเกณฑ์)   → work/16_*
[benchmark]    atlas/global_bench.py — ไทยเทียบโลกจาก OpenAlex (ออฟไลน์ = ข้ามพร้อมเหตุผล)                → work/17_*
[gaps]         atlas/gaps.py — ช่องว่างงานวิจัย R5 + ความเสี่ยงกระจุกตัว E10                              → work/18_*
        ▼
[references]   atlas/references.py — แนวปฏิบัติการอ้างอิงรายวารสาร D7 + "ถูกอ้างใน TCI" R12                 → work/19_*
[search]       atlas/search_index.py — ดัชนีค้นหาแบบแบ่ง shard (ชื่อเรื่อง + คำสำคัญผู้แต่ง) + จุดกาแล็กซี     → work/20_*
[kwtrends]     atlas/kwtrends.py — แนวโน้มคำสำคัญรายปี + อภิธานศัพท์ไทย↔อังกฤษ                           → work/21_*
        ▼
[export]       atlas/export.py → atlas_data.json (1.1) + export_v2.write_release → output/data/<release>/ (contract v2)
               ใช้ export_editors / export_exec / export_research สำหรับไฟล์เสริม และเขียน snapshot ของรอบไว้ทำ diff รอบหน้า
```

กฎที่ใช้กับทุก step:
- step ใหม่ = โมดูลใหม่ใน `atlas/` ที่อ่าน checkpoint ของ step ก่อนจาก `work_dir` แล้วเขียน checkpoint ของตัวเอง; อ่าน/เขียนตารางผ่าน `io_utils.read_table/write_table` (parquet → pickle fallback) และอ่านเฉพาะคอลัมน์ที่ต้องใช้จากตารางใหญ่
- รอบข้อมูล (release, รูป `YYYYQn`) เลือกครั้งเดียวที่ `cluster` แล้วทุก step หลังจากนั้นรวมถึง validate/publish ใช้รอบที่บันทึกไว้ (`atlas.state.work_release` — config ที่ชี้รอบอื่นถูกปฏิเสธ) และใช้เวลา snapshot เดียวกันสำหรับ as_of_year, nowcast และ generated_at (export ซ้ำได้ไฟล์เหมือนเดิมทุกไบต์)
- รันซ้ำ step ของรอบเดิม = ผลเหมือนเดิม (อ่านรอบ *ก่อน* เสมอ เขียนทับเฉพาะโฟลเดอร์ของรอบนี้) · ชื่อรอบผิดรูป, ID หัวข้อซ้ำ, สั่งรันรอบที่เก่ากว่ารอบที่มีอยู่ หรือไม่มี state หัวข้อของรอบก่อน = error (ไม่เดา)
- แถวผู้แต่งอ่านได้เฉพาะใน `journal_metrics`/`journals` (ตัวเลขรวม) และ `institutions_ref`/`institutions` (สังกัดเท่านั้น คอลัมน์ชื่อถูกทิ้งตอนอ่าน) — ด่าน privacy อ่านชื่อเพื่อตรวจอย่างเดียว (§5)

### work_dir กับ state_dir

| ที่ | เก็บอะไร | ลบได้ไหม |
|---|---|---|
| `work_dir` (`pipeline/work/`) | checkpoint `01_*` … `21_*` ของรอบที่กำลังทำ | ลบได้เสมอ (รันใหม่สร้างคืน) |
| `state_dir/embeddings/` | embedding store ต่อโมเดล | **ห้ามลบ** (เสียเงิน/เวลาฝังใหม่) |
| `state_dir/llm_cache/` | คำตอบ LLM ต่องาน (`<task>.jsonl`) + lock/progress ของงาน LLM | **ห้ามลบ** |
| `state_dir/releases/<release>/` | ID หัวข้อ + lineage (`topics/`), ตำแหน่งบนแผนที่ (`layout.parquet`), `snapshot.json` สำหรับ diff รอบหน้า; `releases/index.json` | **ห้ามลบ** |
| `state_dir/openalex/`, `state_dir/ror/` | แคชคำขอ OpenAlex (taxonomy + benchmark) และ ROR เฉพาะประเทศ | ลบได้แต่ต้องดึงใหม่ |
| `output/data/<release>/` + `latest.json` | รอบที่ export แล้ว (contract v2) | เก็บไว้ — publish ใช้กู้รอบก่อน |

## 5. ด่านก่อนเผยแพร่และการเผยแพร่

### 5.1 Data contract v2 (`pipeline/atlas/schema/contract.py`)

- ตอนนี้ `SCHEMA_VERSION = "2.5.0"` (เพิ่มอย่างเดียวทุกขั้น: 2.1 ไฟล์ของบรรณาธิการ · 2.2 ผู้บริหาร · 2.3 นักวิจัย · 2.4 สัดส่วนหัวข้อรายปีของวารสาร · 2.5 หัวข้อเด่นรายจังหวัด `ProvinceStat.topics` ใน `regions.json`); `definition_version` ของนิยามสถานะยังเป็น 3
- ไฟล์หลัก (ทุกรอบมี): `manifest.json`, `overview.json`, `taxonomy.json`, `topics.json`, `topics/<id>.json`, `series.json`, `edges.json` (+ `keywords.json` เมื่อ step keywords มีผล)
- ไฟล์เสริม (optional) ประกาศใน `manifest.modules`: `journals` (+ `journals/<id>.json`), `methods`, `diff`, `match`, `institutions` (+ `institutions/<id>.json`), `regions`, `sdg`, `global`, `gaps`, `references`, `search` (`search/meta.json`, `vocab.json`, `idx-<NNN>.json`, `docs-<NNN>.json`), `galaxy`, `kwtrends` — โมดูลที่ข้ามบอกเหตุผลใน `manifest.skipped_modules`
- แก้ contract = `uv run atlas schema` แล้ว `npm run gen:types` ใน `web/` (CI ตรวจ drift ทั้งสองขั้น) — สเปกเต็มอยู่ใน `docs/DATA_SPEC.md`

### 5.2 `atlas validate` (`atlas/validate.py`) — exit 0 = ผ่าน, 1 = มีคำเตือน, 2 = มี error

1. **integrity** — manifest อ่านได้, ทุกไฟล์มีอยู่จริงและขนาด/sha256 ตรง
2. **schema** — ทุกไฟล์ผ่าน pydantic model ของ contract
3. **coherence** — ID หัวข้อไม่ซ้ำ มีไฟล์รายหัวข้อครบ, การอ้างถึงหัวข้อ/วารสาร/สถาบันในไฟล์เสริมชี้ไปของที่มีอยู่จริง, กลุ่มมีใน taxonomy; ไฟล์ใหญ่เกิน `validation.max_file_bytes` = คำเตือน
4. **P4 cross-checks** (`_check_research`) — จำนวน doc shard ตรงกับ `n_docs`/`docs_per_shard`, ordinal เริ่มถูกที่, จำนวนแถวรวมตรง, หัวข้อในแถวบทความมีจริง, index shard ครบ, vocab ตรง `n_tokens` (vocab ใหญ่ = เตือนให้ตั้ง `search.min_df: 2`), จำนวนจุดกาแล็กซีเท่าจำนวนบทความในดัชนีค้นหา
5. **diff กับรอบก่อน** — จำนวนหัวข้อเปลี่ยนมาก, ID เดิมเหลือน้อย, สถานะเปลี่ยนมาก, คลังหดตัว (เกณฑ์ใน `validation.*`)
6. **LLM** — ชื่อหัวข้อ/ข้อความที่ตกไปใช้คำสำคัญหรือประโยคแม่แบบ = คำเตือนให้รัน `atlas llm` อีกครั้ง
7. **ด่าน PDPA** (`atlas/privacy.py` `scan_release`, เป็น error) — หาอีเมลและ ORCID ในทุกไฟล์ของรอบ (รวม search shard และฟีด) และหาชื่อเต็มของผู้แต่งในคลังที่ไปปนในชื่อสถาบัน/รายชื่อสถาบันของหัวข้อ/เจ้าของและผู้จัดพิมพ์วารสาร; ชื่อผู้แต่งอ่านจาก `work/01_authors` เพื่อตรวจเท่านั้น ข้อความ error อ้างไฟล์และชื่อหน่วยงาน ไม่อ้างชื่อบุคคล; ชื่อหน่วยงานที่คนตรวจแล้วว่าไม่ใช่ชื่อคนใส่ใน `validation.privacy_allow`

### 5.3 `atlas publish --site <เว็บที่ build แล้ว>` (`atlas/publish.py`)

publish รัน validate ก่อนเสมอ (error = ปฏิเสธ; คำเตือน = ปฏิเสธเว้นแต่อนุญาต) แล้วจัดโฟลเดอร์เว็บดังนี้

```
<site>/
├── index.html, assets/…            ← จาก npm run build (ไม่ต้อง build ใหม่ทุกไตรมาส)
├── data/latest.json                ← {release, path: "<release>/manifest.json", …, feeds?}
├── data/<release>/…                ← ไฟล์ contract v2 ของรอบนี้ (publish ซ้ำ = แทนทั้งโฟลเดอร์)
├── data/<รอบเก่า>/…                ← เก็บไว้ให้เว็บเทียบไตรมาส แต่ "ลดขนาด" แล้ว
├── data/feeds/releases.xml         ← ฟีด Atom (เฉพาะเมื่อตั้ง publish.site_url)
├── data/feeds/topics/<id>.xml
└── atlas-offline.html              ← ฉบับไฟล์เดียว เปิดได้โดยไม่ต่อเน็ต
```

- `latest.json` ย้ายเฉพาะเมื่อรอบที่ publish ใหม่สุดบนเว็บ (publish รอบเก่าซ้ำ = คงไว้พร้อมคำเตือน; `--set-latest` บังคับได้ เช่นตอน rollback)
- **ลดขนาดรอบเก่า** (`slim_old_releases`): รอบที่ใหม่สุด `publish.keep_full_releases` รอบ (ดีฟอลต์ 1) และรอบที่ `latest.json` ชี้อยู่เก็บครบ รอบที่เก่ากว่าเหลือแค่ `manifest`, `overview`, `topics`, `taxonomy`, `diff` และโฟลเดอร์ `topics/` (ฟีดลิงก์ถึง) — เว็บไม่โตหลายร้อย MB ทุกไตรมาส
- **กู้รอบก่อน** (`restore_previous`): รอบที่รอบนี้อ้างถึงต่อกันเป็นทอด (`manifest.previous_release`) แต่ไม่มีบนเว็บ (เช่นหลัง `npm run build` ล้าง `dist/data`) ถูกคัดลอกคืนจาก `output/data/`
- **HTML ออฟไลน์**: ใช้ `offline-template.html` ที่ได้จาก build แล้วฝังข้อมูลใน `<script type="application/json" id="atlas-data">` ด้วย Python ล้วน (เครื่องผู้รันไม่ต้องมี Node) · ไม่ใส่ `export.offline_exclude` (ดีฟอลต์ `match.json`) และไม่ใส่ `search/` กับ `galaxy.json` เสมอ · ไฟล์หลักใส่ครบ ไฟล์รายหัวข้อ → รายวารสาร → รายสถาบันใส่จนถึงงบ `export.offline_max_mb` (ดีฟอลต์ 60 MB) แล้วบอกว่าตัดอะไรออก (หน้าที่ไม่มีไฟล์อธิบายตัวเอง)
- **ฟีด Atom** (`atlas/feeds.py`): สร้างจากรอบที่อยู่บนเว็บเมื่อตั้ง `publish.site_url` แล้ว `latest.json.feeds = true` (ฉบับออฟไลน์ไม่มีฟีด)
- `--tarball` เขียน `output/releases/atlas-data-<release>.tar.gz` แบบ deterministic + `.sha256` + บันทึกรอบ และพิมพ์คำสั่ง `gh release create` ให้คนรันเอง (ไม่รันให้)

## 6. งานยาว: embedding และ LLM

- **โครงร่วม** (`atlas/jobs.py`): ทุกงานยาวมีโฟลเดอร์ใน `state_dir` ที่มี `.lock` (OS lock ที่ kernel ปล่อยเองเมื่อ process ตาย), `run.lock` (ข้อมูล pid/host), `progress.json` (heartbeat ที่ `atlas status` อ่าน), `stop.flag` (`atlas embed-stop` / `atlas llm-stop`) และ `run.log` ของโหมด `--background`
- **Embedding**: `atlas/embed_store.py` = store แบบเขียนต่อท้ายอย่างเดียว key = hash(model, ข้อความ) แยกโฟลเดอร์ตามโมเดล ข้อความที่ไม่เปลี่ยนไม่ถูกฝังซ้ำข้ามไตรมาส · `atlas/embed_runner.py` (`atlas embed`) retry ไม่จำกัดเมื่อปลายทางล่มชั่วคราว ทำต่อหลัง Ctrl-C/ไฟดับได้ · `embed_api.py` + `api_http.py` = แกน HTTP แบบ OpenAI-compatible (ไม่ใช้ SDK ของผู้ให้บริการรายใด) · key อยู่ใน env var `ATLAS_EMBED_API_KEY` เท่านั้น
- **LLM**: ทุกการเรียกผ่าน `atlas/llm_runner.py` `run_job` บน adapter `atlas/llm.py` (OpenAI-compatible, แกน HTTP เดียวกับ embedding) · cache = journal `state_dir/llm_cache/<task>.jsonl` key = sha256(model + `prompt_version` + prompt ที่เติมค่าแล้ว) · ตอบผิดรูปแบบ = repair, ไม่ผ่านการตรวจเนื้อหา = เขียนใหม่ แล้วจึง fallback (ไม่ cache) · หยุดด้วย `atlas llm-stop`, Ctrl-C หรืองบ `llm.budget_usd` แล้วทำต่อด้วยคำสั่งเดิม (ที่ตอบแล้วไม่เสียเงินซ้ำ) · งานเป็นระดับหัวข้อทั้งหมด: `label`, `merge`, `narrative`, `brief`, `methods` (prompt อยู่ใน `prompts/*.md` ไฟล์เดียว อ่านตอนรัน) · `atlas llm --dry-run` ประมาณ token และค่าใช้จ่าย · `atlas review export/import` ให้บรรณาธิการแก้ชื่อหัวข้อแล้วชื่อนั้นชนะเสมอ · key อยู่ใน `ATLAS_LLM_API_KEY`

## 7. รอบรายไตรมาสด้วยคำสั่งเดียว: `atlas quarterly` (`atlas/quarterly.py`)

`bash scripts/quarterly_run.sh [--corpus <โฟลเดอร์>] [--release YYYYQn]` (หรือ `quarterly_run.cmd` บน Windows) = `uv run atlas quarterly` — แต่ละขั้นเป็น process `atlas` แยกที่มี exit code ของตัวเอง; รอบที่ล้มกลางทาง = รันคำสั่งเดิมซ้ำแล้วทำต่อ

| ขั้น | ทำอะไร | ผล |
|---|---|---|
| 1 config | config.yaml + คลัง/รอบ/companion files ของรอบนี้ | `runs/<release>/config.yaml` |
| 2 corpus | รายการไฟล์ ขนาด sha256 ที่รอบนี้อ่าน | `runs/<release>/corpus_manifest.json` |
| 3 profile | ตรวจคลัง + companion files (หยุดเมื่อเสียเกิน `input.max_error_ratio`) | `runs/<release>/profile.md` |
| 4 embed | เฉพาะ provider `api`: ตัวเลข dry-run แล้ว `atlas embed` | store ใน `state_dir` |
| 5 llm | เมื่อเปิดงาน LLM: แสดง `--dry-run` และต้องยืนยัน (หรือ `--yes`) ก่อนจ่ายเงิน | cache ใน `state_dir` |
| 6 run | `atlas run` ทุก step | `runs/<release>/pipeline.log` |
| 7 validate | exit 2 = หยุด; exit 1 = ไปต่อ เว้นแต่ `--strict` | รายงาน validate |
| 8 web | build `web/dist` ถ้ายังไม่มี (หรือ `--build-web`) โดยส่ง `ATLAS_SITE_URL` = `publish.site_url` | `web/dist/` |
| 9 publish | `atlas publish --site web/dist` | ข้อมูลในเว็บ |
| 10 deploy | สำเนาเว็บทั้งก้อน + zip ทั้งเว็บ + zip เฉพาะข้อมูล (ปฏิเสธเว็บที่รอบล่าสุดเป็นข้อมูลตัวอย่าง) | `deploy/<release>/site/`, `deploy/atlas-site-<release>.zip`, `deploy/atlas-data-<release>.zip` |
| 11 summary | จำนวน เวลา และสิ่งที่ต้องอัปโหลดไปที่ไหน | `runs/<release>/summary.md` |

`--prepare` หยุดหลังตรวจคลัง (ก่อนการฝังครั้งใหญ่ครั้งแรก) · `scripts/import_atlas.sh` ยังใช้ได้สำหรับ build + publish อย่างเดียว

## 8. GitHub Pages (`.github/workflows/pages.yml`)

- รันเมื่อผู้ดูแลกดเองเท่านั้น (`workflow_dispatch`) — push ไม่มีวันแทนรอบที่ออนไลน์อยู่
- `data_release` ว่าง = เว็บสาธิตด้วยข้อมูลสังเคราะห์ (`npm run stage:demo`: ทุกหน้ามีป้ายข้อมูลตัวอย่าง และใส่ robots noindex)
- `data_release` = tag ของ GitHub Release ที่แนบ `atlas-site-data-<release>.zip` (สร้างด้วย `scripts/package_release.sh` หลัง `atlas publish --site web/dist`) = ขึ้นข้อมูลจริง; zip ที่เป็นข้อมูลตัวอย่าง (`embedding_provider` = fixture/lite) ถูกปฏิเสธ · ไม่มีข้อมูลจริงใน repo
- ขั้นตอน: `npm ci` → `npm test` → `npm run build` → วางข้อมูล → upload + deploy Pages
- CI ปกติ (`.github/workflows/ci.yml`): pipeline (ruff, pytest, schema drift, e2e สังเคราะห์) · web (type drift, fixtures, build, งบ bundle, Playwright smoke) · brief PDF

## 9. เว็บ (`web/`)

React 19 + Vite + TypeScript + Tailwind 4 · `HashRouter` · base `./` (เปิดจาก sub-path ใดก็ได้) · รายละเอียดคำสั่งและโครงโค้ดอยู่ใน `web/README.md`

### 9.1 การโหลดข้อมูล

```
HttpSource (src/data/source.ts)          EmbeddedSource (src/data/source.ts)
  fetch ./data/latest.json                 อ่าน {latest, files} จาก <script id="atlas-data">
  → ./data/<release>/<ไฟล์>                 ใน atlas-offline.html
            └──────────────┬──────────────┘
                           ▼
   loadRelease (src/data/release.ts): latest → manifest (ตรวจ schema major = 2 ด้วย zod)
   → ไฟล์หลักพร้อมกัน → overview.json ของรอบก่อน (สำหรับ Δ; ไม่มี/เสีย/ออฟไลน์ บอกต่างกัน)
   → ไฟล์เสริมและ topics/<id>.json โหลดเมื่อหน้าต้องใช้ (cache ในหน่วยความจำ)
```

- โหลดไม่ได้ / schema ผิด major / ไฟล์เสีย → แถบแจ้งเหตุผล (`DataError` 4 ชนิด: missing, network, parse, schema) — **ไม่มีข้อมูลสำรองฝังในเว็บ**
- ชื่อรอบใน `latest.json` ถูกตรวจรูปแบบ (ชี้ออกนอก `data/` ไม่ได้)
- หน้าที่ใช้ไฟล์เสริมเรนเดอร์ผ่าน `ModuleFile`: ไม่มีโมดูล = h1 + เหตุผล (จาก `manifest.skipped_modules` ถ้ามี) ไม่ใช่หน้าขาว
- ชนิดข้อมูลมาจาก `src/data/contract.ts` ที่ generate เท่านั้น ผ่าน `src/data/types.ts`

### 9.2 Routes (`src/App.tsx`)

| กลุ่ม | route | โหลด |
|---|---|---|
| หลัก | `/overview` (หน้าแรก; `/` ส่งต่อมาที่นี่), `/topics/:id`, `/emerging`, `/compare`, `/data`, `/about`, `*` (ไม่พบหน้า) | อยู่ใน entry chunk |
| สรุป/เรื่องเล่า | `/brief`, `/story`, `/atlas` | lazy |
| บรรณาธิการ (P2) | `/journals`, `/journals/:id`, `/methods`, `/changes`, `/match` | lazy |
| ผู้บริหาร (P3) | `/institutions`, `/institutions/:id`, `/regions`, `/province`, `/province/:code`, `/sdg`, `/global`, `/gaps`, `/ideas` | lazy |
| นักวิจัย (P4) | `/search`, `/galaxy`, `/keywords`, `/references` | lazy |
| กราฟฝัง | `/embed/topic/:id`, `/embed/emerging` (`/embed/*` อื่น = กราฟหัวข้อ) — นอก app shell ไม่มีเมนู/ส่วนท้าย | lazy |

เมนูจัดตามคำถามของผู้อ่าน (`src/components/Header.tsx`): ภาพรวม · สรุปผู้บริหาร · **อะไรกำลังมา** · **ใครทำเรื่องอะไร** · **ไทยอยู่ตรงไหน** · **หางานวิจัย** · ข้อมูลเปิด · อ่านตัวเลขอย่างไร

### 9.3 ความทนทานและขนาด

- **Error boundary 3 ชั้น** (`src/components/ErrorBoundary.tsx`): ครอบทั้งแอปใน `main.tsx` · ครอบพื้นที่หน้าใน `Layout` (หัวและเมนูยังอยู่; ล้างเองเมื่อเปลี่ยนหน้าหรือ query) · ครอบกราฟฝังด้วย `EmbedBoundary` · chunk หายหลัง deploy ใหม่ = reload ให้ 1 ครั้ง
- **งบ bundle**: entry ≤ 180 KB gzip (`npm run check:bundle` ตรวจงบและตรวจว่าทุก `lazy(() => import(…))` ใน `App.tsx` เป็น chunk แยก; ตอนนี้ ≈ 167 KB) · ข้อความของหน้า lazy อยู่ในไฟล์ `src/strings/<หน้า>.ts` ของตัวเอง (`useStrings`) · เส้นขอบจังหวัดอยู่ใน chunk ของหน้าแผนที่จังหวัดเท่านั้น
- **ข้อมูลขนาดจริง** (~1,500 หัวข้อ, ~2,000 วารสาร, ~10,000 สถาบัน, 500K บทความ): ตาราง/รายการมีเพดาน (`DataTable` `limit`, `ListMore`, `useCapped`) และบอกจำนวนที่ตรงกับที่แสดง; `/search` โหลด doc shard ≤ 6 ไฟล์ต่อคำค้น (LRU cache) และบอกเมื่อผลมาจากบางส่วน
- **SEO** (ปลั๊กอิน `atlasSeo` ใน `web/vite.config.ts`, ใช้ `ATLAS_SITE_URL`): canonical, Open Graph/Twitter card, schema.org WebSite + Organization + Dataset, `robots.txt`, `sitemap.xml` (มีแค่หน้าแรกเพราะ HashRouter) · `offline-template.html` และเว็บสาธิตเป็น noindex

### 9.4 โครงโค้ด

| ที่ | หน้าที่ |
|---|---|
| `src/data/` | `source.ts` · `release.ts` · `contract.ts` (generated) · `types.ts` |
| `src/pages/` | หน้าตาม §9.2 (+ ส่วนย่อยใน `overview/`, `topic/`, `about/`, `data/`) |
| `src/components/` | Figure · StatTile/StatGrid · DataTable · Term/InfoPop · HowNote · SourceLine · CsvButton · ModuleFile · ProvinceMap · ErrorBoundary ฯลฯ |
| `src/charts/` | กราฟ SVG เขียนเอง (forest, portfolio, trend, multi-line + ชุด infographic) — คณิตการจัดวางแบบ pure อยู่ใน `infographic.ts` / `execLayout.ts` / `editorLayout.ts` (มี test) |
| `src/features/atlas/` | แผนที่หัวข้อ (canvas ภูมิประเทศ + SVG overlay, กริดอ้างอิง 10 × 6 A–J/1–6) + ดัชนีค้นหาหัวข้อ (`Gazetteer`) |
| `src/lib/` | `searchTokens.ts` (ต้องตรง `pipeline/tests/fixtures/search_parity.json`) · `matcher.ts` (ต้องตรง `match_parity.json`; ข้อความที่วางไม่ออกจากเบราว์เซอร์) · `citation.ts` (RIS/BibTeX ไม่มีผู้แต่ง) · `galaxyGl.ts` (WebGL2) · `urlState.ts` (ตัวกรองอยู่ใน URL) ฯลฯ |
| `src/embed/` | กราฟฝัง + ปุ่มคัดลอก `<iframe>` + ลิงก์ฟีด (แสดงเมื่อ `latest.feeds === true`) |
| `src/strings/` | ข้อความไทย+อังกฤษทุกตัว (`i18n.test.ts` ตรวจครบคู่) |
| `src/styles/tokens.css` | design tokens (ธีมสว่างธีมเดียว) |
| `src/geo/thProvinces.ts` | เส้นขอบ 77 จังหวัด (Natural Earth) |
| `src/brand/`, `src/assets/brand/partners/` | โลโก้ TCI · NECTEC · สวทช. |

### 9.5 ระบบดีไซน์

กฎดีไซน์ทั้งหมดอยู่ใน `DESIGN.md` (ชนะ catalog ทั่วไปเสมอ) และค่า token อยู่ใน `web/src/styles/tokens.css` — โลกดีไซน์ "ข่าวข้อมูล" (data explainer): พื้นขาวธีมเดียว ไม่มีโหมดมืด, ฟอนต์ Sarabun (self-hosted), น้ำเงิน TCI `#283894`, ส้ม TCI `--accent-mark` เฉพาะจุดเน้นจุดเดียว, ข้อมูลประกอบเป็นเทา; สถานะแสดงด้วยรูปทรง + สี + ชื่อเสมอ (ตรวจ CVD + contrast ด้วย `palette.test.ts`); ข้อความ 2 ชั้นตาม "Copy voice" และ pipeline ใช้ชุดคำต้องห้ามเดียวกัน (`narrative.jargon_in`) · ทิศทางและข้อมูลผลิตภัณฑ์: `.impeccable/surfaces/web-src.md`, `PRODUCT.md`

## 10. ทำไมไม่มี backend

- ข้อมูลเปลี่ยนปีละ 4 ครั้ง ไม่ต้องการ API แบบ real-time
- static hosting ถูกกว่า เสถียรกว่า และย้าย host ได้ทันที (คัดลอกโฟลเดอร์)
- ค้นหาบทความทั้งคลังก็ไม่ต้องมี backend: ดัชนีเป็นไฟล์ static แบ่ง shard ที่เบราว์เซอร์โหลดเฉพาะส่วนที่ต้องใช้; "วางบทคัดย่อ" คำนวณในเบราว์เซอร์ล้วน
- ถ้าต้องการบัญชีผู้ใช้, การแจ้งเตือนส่วนตัว หรือค้นหาบทคัดย่อเต็ม ค่อยเพิ่ม backend (ดู `docs/ROADMAP.md`)

## 11. ข้อจำกัดที่รับรู้ไว้

- **คาดการณ์ระยะสั้น (2 ปี)** — ตั้งใจ: ข้อมูลบทความมี backfill lag ทำนายยาวจะหลอกตัวเอง
- **score เป็น percentile ภายในรอบ** — เทียบข้ามรอบไม่ได้ ใช้มิติดิบถ้าจะเทียบ
- **แผนที่นิ่งข้ามรอบ** — หัวข้อเดิมอยู่ที่เดิมด้วย UMAP เริ่มจากรอบก่อน + Procrustes + anchor แต่ตอน fit ใหม่ทั้งก้อน (`topics.refit_every_releases`, ดีฟอลต์ทุก 4 รอบ) หัวข้อแตก/รวมได้ และ lineage บอกว่าไปไหน
- **HashRouter** — ลิงก์ทุกหน้าใช้ได้และแชร์ได้ แต่ search engine เก็บได้เป็นหลักแค่หน้าแรก
- **HTML ออฟไลน์** ไม่มีค้นหา กาแล็กซี วางบทคัดย่อ และกราฟฝัง (ขนาดไฟล์) และอาจไม่มีไฟล์รายละเอียดบางส่วนเมื่อเกินงบ `offline_max_mb`
