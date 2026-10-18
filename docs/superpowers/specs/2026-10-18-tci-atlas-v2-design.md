# TCI Research Atlas v2 — แผนพัฒนาฉบับสมบูรณ์

> แผนนี้เป็นทั้ง design spec และ roadmap — หลังอนุมัติจะบันทึกเป็น `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md`
> แล้วแตกเป็น implementation plan ละเอียดทีละเฟส (เริ่ม P0) ด้วย writing-plans

## Context — ทำไมต้องทำ

โปรเจกต์มีโครงที่ดี (batch pipeline → JSON → static web) แต่ **ยังใช้กับข้อมูลจริงไม่ได้** และ **ยังไม่ใช่ dashboard ฉบับเต็ม**:

- corpus จริงเป็น Markdown จาก ThaiJO (>250,000 ไฟล์ ออกแบบเผื่อ 500K) แต่ ingest อ่านได้แค่ CSV/JSON/Parquet
- มีบั๊กที่ทำให้ผลผิดทั้งแผนที่: coarse clustering รัน HDBSCAN `min_cluster_size=1500` บน centroid หลักร้อยจุด → ทุกหัวข้อกลายเป็นกลุ่มเดียว; `pytest` เก็บเทสต์ไม่ได้ (ฟังก์ชันชื่อ `run_tests`); ไม่มีการแปลง พ.ศ.→ค.ศ. ตามที่ docs อ้าง
- เว็บยังเป็นหน้าเดียว ใช้ข้อมูล bundle "71 สาขา" ชุดเก่า ไม่มี search / URL state / dark mode / keyboard a11y

เป้าหมาย: **Atlas v2** — live dashboard สาธารณะ (GitHub Pages) + ไฟล์ HTML เดี่ยว offline + PDF สรุปผู้บริหาร
สำหรับ 3 กลุ่ม: **ผู้บริหาร · บรรณาธิการ · นักวิจัย** ทั้งในและต่างประเทศ (TH/EN เท่าเทียม) ภายใต้แบรนด์ TCI

## การตัดสินใจของผู้ใช้ (ยืนยันแล้ว)

| เรื่อง | ตัดสินใจ |
|---|---|
| ข้อมูล | มีคลัง .md ครบ >250K ไฟล์ (หลายวารสาร) — ระหว่างพัฒนาใช้ 11 ไฟล์จริง + synthetic corpus |
| ผลงาน | ทั้งเว็บ live + HTML เดี่ยว offline (+ PDF) |
| การเปิดเผย | สาธารณะ — ระดับหัวข้อ/วารสาร/สถาบัน, **ไม่จัดอันดับรายบุคคล** (PDPA) |
| Compute | ตั้งค่าได้ทั้ง API (OpenAI/Gemini/Claude) และ local GPU (BGE-M3) |
| ฟีเจอร์ | ทุกโมดูลที่เสนอ + ฟีเจอร์เพิ่มที่ผมคิดสำหรับทั้ง 3 กลุ่ม |
| ดีไซน์ | ออกแบบใหม่ทั้งหมด — mockup 3 ทิศทาง: Editorial / Cartographic / Civic modern |
| แบรนด์ | โครงการของ TCI (ได้รับอนุญาต) — ใช้ **wordmark ชั่วคราว** สลับเป็นโลโก้ทางการได้จุดเดียว |
| Hosting | GitHub Pages ฟรี + GitHub Actions, repo public, ส่งมอบทีละเฟส |

## ข้อค้นพบจากการอ่านโค้ด + corpus (ต้องแก้)

**Pipeline defects**
1. ingest ไม่รองรับ .md; ไม่แปลง พ.ศ.; dedup ใช้ md5 ชื่อเรื่อง (docs อ้าง rapidfuzz 0.95) — `pipeline/atlas/ingest.py`
2. coarse clustering ยุบเหลือกลุ่มเดียว — `pipeline/atlas/cluster.py:103-115`
3. `tests/test_emerging.py` ไม่มี `test_*` → pytest ไม่รันอะไร; ใช้ `/tmp` แบบ hardcode
4. emerging ไม่ตรง spec (spec คือ source of truth): γ คงที่ แทน γ·ln(n), `burst_scale=3.0` แทน s=2.0, `burst_intensity` เป็น log-likelihood gain (โตตามขนาด topic → score เอียงไปหาหัวข้อใหญ่) แทน "สัดส่วนปีที่ burst ในช่วง R" — `pipeline/atlas/emerging.py:63-104`
5. `embed.py` reuse checkpoint ถ้าจำนวนแถวเท่าเดิม (ได้ vector เก่าผิดเรื่อง); `label.py` cache ด้วย topic_id ของ HDBSCAN ซึ่งเปลี่ยนทุกรอบ → ชื่อหัวข้อสลับกันเงียบ ๆ; representative titles = abstract ยาวสุด ไม่ใช่ใกล้ centroid
6. `forecast.py` export history ที่ winsorize แล้ว (กราฟบิดเบือน), ไม่มี naive baseline
7. c-TF-IDF แบบ char_wb n-gram ให้คำเด่นเป็นเศษคำไทย
8. `cluster.py`/`layout.py` เขียน parquet ตรง (ผิดกฎ io_utils); ชื่อ checkpoint ใน docs ไม่ตรงโค้ด; `prev/` อยู่ใน `work_dir` ที่ docs บอกว่าลบได้; สคริปต์ bash ไม่เหมาะ Windows

**ความจริงของ corpus (.md จาก ThaiJO)**
- ส่วนหัว: `# title`, `**Journal:**` (แค่ OJS path เช่น `BECJournal` — ไม่มีชื่อเต็ม/ISSN/tier), `**Published:**`, `**Pages:**`, `**Article URL:**`, `**Issue URL:**`, `**Authors:**` (`ชื่อไทย [EN name] (สังกัดไทย (สังกัด EN))` + คำนำหน้าวิชาการปน), `**Keywords:**` (ไทย+อังกฤษปน บางทีถูกตัดกลางคำ)
- `## Abstract` = บทคัดย่อไทย + ชื่ออังกฤษ + บทคัดย่ออังกฤษ + `DOI:` ต่อกันในย่อหน้าเดียว (คั่นด้วยช่องว่าง ≥3)
- **2/11 ไฟล์ `Published: 1970-01-01`** → ต้องกู้ปีจาก DOI (`10.14456/becj.2014.xx`) → median ปีของ Issue เดียวกัน → null
- `## References` ขึ้นบรรทัดผิด, บางเรื่องมีแค่ "how-to-cite ตัวเอง", ปีเป็น พ.ศ., อ้างอิงไทยที่เขียนอังกฤษ → ห้ามตัดสิน "ไทย/สากล" จากตัวอักษร
- ข้อความบางไฟล์วรรณยุกต์หาย ("ความตองการ") / สัญลักษณ์สถิติหาย → ต้อง fold วรรณยุกต์ใน search + ติด flag `text_quality`
- article ID ของ OJS ไม่ unique ข้ามเซิร์ฟเวอร์ → ใช้ `so02:BECJournal:74136` จาก Article URL
- **ความเสี่ยงใหญ่สุด: journal-entry bias** — วารสารเข้าระบบ/อัปโหลดย้อนหลัง ทำให้หัวข้อดูเหมือน EMERGING → ต้องมี `journal_hhi` + flag `journal_driven`

## สถาปัตยกรรม v2

```
corpus/*.md ──► [atlas profile]  สำรวจคุณภาพข้อมูลทั้งคลังก่อนทุกอย่าง (ปี/วารสาร/ภาษา/refs coverage)
        │
        ▼
 ingest (ThaiJO md parser) → preprocess → embed (store แบบ incremental: article_id+text_sha+model_id)
        → taxonomy (กลุ่มบนสุด = OpenAlex 26 fields / 252 subfields — นิ่งข้ามรอบ + เทียบสากลได้)
        → topics (fit รายปี / assign รายไตรมาส + lineage: continue/split/merge/new/retired)
        → label (LLM provider: openai-compatible | anthropic | local; prompt โหลดจาก prompts/*.md)
        → series → emerging (ตรง spec + journal_hhi flag) → forecast (+naive, MASE, skill)
        → layout (นิ่งข้ามรอบ + galaxy: วางบทความรอบ topic)
        → enrich: journals · institutions(ROR+alias→จังหวัด) · methods · references · sdg/frameworks · global(OpenAlex)
        → narrative/brief (LLM grounded) → export (data contract v2, sharded) → validate → publish (GitHub Release)
        │
        ▼
 web v2 (React 19 + Vite + TS, HashRouter) ── DataSource: HttpSource (Pages) | EmbeddedSource (HTML เดี่ยว)
        └─ CI: lint/tsc/test → build Pages + build offline single-file + Playwright PDF brief
```

หลักการที่คงไว้: แยกผลิต/แสดงผล, resume ได้ทุก step, ตัวเลขทุกตัวมีนิยาม+เทสต์, ภาษาไทยเป็นพลเมืองชั้นหนึ่ง
หลักการใหม่: **persistent state แยกจาก work** (`state/` เก็บ embeddings, lineage, label cache, alias, layout เดิม),
**ข้อมูลจริงไม่เข้า git** (ออกเป็น GitHub Release asset), **CLI Python เดียวใช้ได้ทุก OS** (`atlas run|profile|synth|validate|publish`)

### การตัดสินใจทางเทคนิคหลัก
- **Taxonomy:** fine topic → OpenAlex subfield ด้วย kNN (k≈20) บน embedding ของงาน OpenAlex ที่มีผู้แต่งไทย (โมเดลเดียวกัน, cache ใน `state/`) — ไม่ match กับชื่อสั้น ๆ; vote <50% → flag `cross_field`; อนุญาต local split ใต้ parent เดียวกัน (เช่น พุทธศึกษา, รัฐประศาสนศาสตร์)
- **Scale 500K×1024 บนเครื่อง 16–32GB:** PCA→128 (fit บน sample 100K) → UMAP 10D fit ~150K แบบ stratified แล้ว transform ที่เหลือ → sklearn/fast_hdbscan (เลี่ยงปัญหา build `hdbscan` บน Windows); cuML เป็นทางเลือกผ่าน WSL2+NVIDIA
- **Stable IDs:** fit ใหม่ปีละครั้ง (หรือเมื่อ low-confidence เกินเกณฑ์) / ไตรมาสอื่น assign บทความใหม่เข้า centroid เดิม; ตอน refit จับคู่ด้วย contingency ของบทความร่วม (containment ≥0.5) + cosine เป็นตัวตัดสินเสมอ
- **Thai NLP:** pythainlp (newmm) สำหรับ c-TF-IDF + pre-segment ตอนสร้าง search index; ฝั่งเว็บใช้ `Intl.Segmenter('th')`; fold วรรณยุกต์ทั้ง index และ query
- **Search ที่ 500K บน Pages (1GB site / 100MB ต่อไฟล์):** index เฉพาะชื่อเรื่อง+คำสำคัญ (≈30–40MB แบ่ง ~512 shards) + รายการบทความต่อ topic; **ไม่เผยแพร่ abstract เต็ม** (ลิขสิทธิ์วารสาร) — ลิงก์กลับ ThaiJO; รวมไฟล์ < 20K
- **"Match my abstract" v1:** TF-IDF เทียบ term vector ของ topic ในเบราว์เซอร์ (ไม่โหลดโมเดล 100MB) — semantic model เป็นทางเลือกอนาคต
- **SDG:** 17 goals ด้วย kNN บนชุดข้อมูล OSDG (CC BY) + LLM ยืนยันระดับ topic; กรอบไทย (BCG, แผนด้าน ววน., หมุดหมายแผนฯ 13) เป็น YAML ที่ผู้ดูแลแก้ได้ ใช้ engine เดียวกัน
- **Institutions:** alias table ที่คัดเอง (สินทรัพย์หลัก — ราชภัฏ/ราชมงคล) + ROR dump (CC0) เป็นตัวเสริม → จังหวัด/ประเภท/ประเทศ; คำนำหน้าวิชาการ → สัดส่วนนักศึกษาเป็นผู้แต่ง
- **Journal registry:** `registry/journals.csv` (ชื่อเต็ม TH/EN, ISSN, TCI tier, สาขา TCI, สถาบันเจ้าของ) — จำเป็นสำหรับ journal view, tier filter, และกรองเฉพาะวารสาร TCI
- **Router:** HashRouter ทั้ง Pages และ offline (deep link ไม่ 404, เปิด `file://` ได้); `BASE_URL`-relative fetch (แก้บั๊ก `/data/...` absolute)
- **PDF:** สร้างใน web CI ด้วย Playwright print หน้า `/brief` (ฟอนต์ไทยฝัง) — เชื่อถือได้กว่า HTML สำหรับ LINE/อีเมล

### Data contract v2 (`data/<release>/` + `latest.json`)
- `manifest.json` — `schema_version` (semver), release, git sha, config hash, embedding_model, taxonomy_version, `modules[]`, `files[{path,bytes,sha256}]`, previous_release
- core: `overview.json`, `taxonomy.json`, `topics.json` (stable `id` เช่น `T000123`, subfield, th/en/description, keywords, size, x/y/r, status, metrics{…, burst_frac, journal_hhi, journal_driven}, score, lineage, sdg[], forecast{model, mase, skill_vs_naive, years, mean, lo, hi}), `series.json` (columnar, ค่าดิบ), `edges.json`
- per-topic: `topics/<id>.json` (บทความใกล้ centroid, วารสาร, สถาบัน, methods, narrative)
- modules: `journals.json`, `institutions.json`, `sdg.json`, `global.json`, `gaps.json`, `diff.json`, `brief.json`
- article-level: `articles/<shard>.json`, `search/*`, `galaxy/points.bin`
- สีเป็น **token key** ไม่ใช่ hex; offline subset = `offline_bundle.json`
- **Pydantic models = source of truth** → JSON Schema → TS types (json-schema-to-typescript); CI fail ถ้า generated ไม่ตรง; เว็บตรวจ major version ด้วย zod → แสดง banner แทนหน้าขาว; เพจซ่อนตัวเองตาม `manifest.modules`

## แคตตาล็อกฟีเจอร์ตามกลุ่มผู้ใช้ (เฟสที่ส่งมอบ)

### ผู้บริหาร / นโยบาย
| # | ฟีเจอร์ | เฟส |
|---|---|---|
| E1 | Executive overview: KPI (บทความ, หัวข้อ, วารสาร, สถาบัน, % ร่วมมือต่างประเทศ, % มีบทคัดย่ออังกฤษ) + Δ QoQ/YoY | P1→P3 |
| E2 | Portfolio matrix ขนาด×การเติบโต (Stars / Rising / Mature / Declining) | P1 |
| E3 | Emerging/Hot/Declining + **early warning** หัวข้อยุทธศาสตร์ที่ลดลงหลายไตรมาส | P1 |
| E4 | **PDF สรุปผู้บริหาร 1–2 หน้า** TH/EN — ทุกตัวเลขอ้างข้อมูลจริง | P1 (template) → P3 |
| E5 | "อะไรเปลี่ยนตั้งแต่ไตรมาสก่อน" (หัวข้อใหม่/เปลี่ยนสถานะ/movers) | P2 |
| E6 | **ความเหลื่อมล้ำเชิงพื้นที่**: แผนที่จังหวัดของผลผลิตวิจัย | P3 |
| E7 | ภูมิทัศน์สถาบัน + เครือข่ายความร่วมมือระหว่างสถาบัน/ต่างประเทศ | P3 |
| E8 | SDGs 17 เป้า + กรอบไทย (BCG / แผน ววน. / หมุดหมายแผนฯ 13): ครอบคลุม-ช่องว่าง | P3 |
| E9 | **ไทย vs โลก (OpenAlex)**: activity index, ช่องว่างการเติบโต, "โลกโตแรงแต่ไทยยังเล็ก" = โอกาสลงทุน | P3 |
| E10 | ความเสี่ยงการกระจุกตัว: หัวข้อที่พึ่งสถาบัน/วารสารเดียว | P3 |
| E11 | สัญญาณคุณภาพเชิงวิธีวิจัย ("methods monoculture" เช่น พึ่งแบบสอบถาม+สถิติพรรณนา) | P2→P3 |
| E12 | แผงความโปร่งใสข้อมูล: coverage, คุณภาพข้อมูล, journal-entry flags | P1 |

### บรรณาธิการวารสาร
| # | ฟีเจอร์ | เฟส |
|---|---|---|
| D1 | Journal profile: ขอบเขตบนแผนที่, สัดส่วนหัวข้อ, **scope drift** รายปี | P2 |
| D2 | **คะแนนความครบถ้วน metadata** (บทคัดย่ออังกฤษ, คำสำคัญ, DOI, รูปแบบอ้างอิง) สอดคล้องเกณฑ์ประเมิน TCI | P2 |
| D3 | **สัดส่วนผู้แต่งในสถาบันเจ้าของวารสาร** (in-house) + ความหลากหลายสถาบัน + ผู้แต่งต่างประเทศ | P2 |
| D4 | วารสารคู่เทียบ (topic mix ใกล้กัน) + benchmarking | P2 |
| D5 | หัวข้อ emerging ไปลงที่ไหน + **ตัวหาโอกาสฉบับพิเศษ** (emerging ที่ยังมีวารสารรองรับน้อย) | P2 |
| D6 | คลังผู้ทรงคุณวุฒิระดับสถาบัน (สถาบันที่แอคทีฟในหัวข้อ) | P3 |
| D7 | แนวปฏิบัติวิธีวิจัย/การอ้างอิงรายวารสาร | P2→P4 |

### นักวิจัย
| # | ฟีเจอร์ | เฟส |
|---|---|---|
| R1 | Topic page: แนวโน้ม+คาดการณ์, คำสำคัญ, บทความตัวแทน (ลิงก์ ThaiJO), หัวข้อใกล้เคียง, วารสาร, สถาบัน, SDG, วิธีวิจัย | P1 → เติมทุกเฟส |
| R2 | ค้นหาหัวข้อ TH/EN (P1) → ค้นหาบทความทั้งคลังแบบ sharded (P4) | P1/P4 |
| R3 | **วางบทคัดย่อของฉัน** → หัวข้อ/วารสาร/งานที่ใกล้ที่สุด | P2 |
| R4 | **ควรตีพิมพ์ที่ไหน** (journal × topic fit) | P2 |
| R5 | **ตัวหาช่องว่างงานวิจัย**: หัวข้อเพื่อนบ้านที่ยังไม่ค่อยมีใครเชื่อม, โตในโลกแต่เล็กในไทย, emerging ที่มีสถาบันทำน้อย | P3 |
| R6 | หาผู้ร่วมวิจัยระดับสถาบัน (สถาบันที่เสริมกัน) | P3 |
| R7 | Keyword trend explorer (เทียบ ≤5 คำข้ามปี) + อภิธานศัพท์ TH↔EN ต่อหัวข้อ | P4 |
| R8 | Galaxy view: บทความทุกเรื่องเป็นจุด (WebGL) | P4 |
| R9 | Export CSV ทุกรายการ (P1) + RIS/BibTeX (P4) + cite-this-atlas | P1/P4 |
| R10 | เปรียบเทียบ 2–4 หัวข้อซ้อนกราฟ | P1 |
| R11 | ติดตามอัปเดต: RSS/Atom ต่อรอบ/ต่อหัวข้อ | P4 |
| R12 | การอ้างอิงภายในคลัง TCI ("ถูกอ้างใน TCI") — **เฉพาะเมื่อ coverage ของ references พอ** | P4 |

### ทุกกลุ่ม + ผู้ใช้ต่างประเทศ
TH/EN เท่าเทียม + อภิธานศัพท์ + คู่มือ "อ่านกราฟนี้อย่างไร" · URL แชร์ได้ทุกสถานะ · WCAG 2.2 AA, dark mode, mobile ·
หน้า Method ภาษาง่าย + changelog นิยามต่อรอบ · Open data (CC BY 4.0) + static JSON API มีเวอร์ชัน + data dictionary ·
embed widget (iframe กราฟ, P4) · แบรนด์ TCI ผ่าน `web/src/brand/` + `web/public/brand/` (wordmark ชั่วคราว → โลโก้ทางการแก้จุดเดียว)

**ตัดออก:** shadcn ที่ไม่ใช้ ~40 ไฟล์, `kimi-plugin-inspect-react`, ข้อมูล bundle 71 สาขา, Prophet, ข้อความ hardcode "200,003 บทความ 71 สาขา" ใน `web/index.html`

## เฟสการส่งมอบ (vertical slices — ทุกเฟสใช้งานได้จริง + ออก release)

### P0 — Foundation & ตรวจความจริงของข้อมูล
- `git init` + GitHub public repo (ขออนุญาตก่อน push ทุกครั้ง), `.gitignore` (กัน corpus/state/output/data จริง)
- `pipeline/pyproject.toml` (uv), ruff, pydantic config, Typer CLI `atlas`
- **ThaiJO md parser** (ใหม่ `pipeline/atlas/sources/thaijo_md.py`): แยก TH/EN abstract (space-run + script ratio + ความยาว/จุด), ชื่ออังกฤษ, DOI, ผู้แต่ง/สังกัดซ้อนวงเล็บ/คำนำหน้า, keywords ไทย/อังกฤษ, references (ต่อบรรทัด, ตัด self-cite), ปี (Published → DOI → median issue → null), ID จาก URL
- **golden tests บน 11 ไฟล์จริง** + fuzz test (parser ไม่ throw)
- `atlas synth`: synthetic .md corpus (หลายพัน–20K) ฝังสัญญาณ: emerging, hot, declining, burst, **journal-entry confound**, สถาบัน, refs, methods
- `atlas profile`: รายงานคุณภาพทั้งคลัง (ปี/วารสาร/ภาษา/refs coverage/text_quality)
- แก้ defects 1–8 ทั้งหมด; `emerging.py` ให้ตรง spec; เขียนเทสต์ใหม่เป็น `test_*` ด้วย `tmp_path`
- embedding fallback แบบ CPU เบา (TF-IDF+SVD) ให้ CI รันได้ไม่ต้องมี GPU/API
- data contract v2 skeleton (pydantic → JSON Schema → TS) + GitHub Actions CI
- sync docs (ARCHITECTURE/DATA_SPEC/OPERATIONS/README) กับโค้ด

### P1 — Core analytics v2 + Web v2 MVP + release สาธารณะครั้งแรก
- Pipeline: taxonomy OpenAlex, topics fit/assign + lineage, label (LLM provider abstraction + prompts จากไฟล์), forecast + naive baseline, layout นิ่ง, export v2, `atlas validate` (schema + diff เทียบรอบก่อน), `atlas publish`
- **ดีไซน์ (ทำคู่ขนาน):** mood board หน้า Overview 3 ทิศทาง (Editorial / Cartographic / Civic) พร้อม wordmark TCI → ผู้ใช้เลือก 1 → `DESIGN.md` + tokens + Thai typography (ห้าม italic) + dataviz palette → อัปเดต CLAUDE.md §6
- Web v2: เคลียร์ของเก่า, app shell + HashRouter, DataSource (Http/Embedded), i18n, URL state, dark mode
  หน้า: `/overview` `/atlas` `/topics/:id` `/emerging` `/compare` `/data` `/about` (+ topic search, CSV export)
- Outputs: Pages deploy, **HTML เดี่ยว** (vite-plugin-singlefile, ≤~15MB, ฟอนต์ subset, ไม่มี network request), **PDF brief** (Playwright)

### P2 — Release บรรณาธิการ
journals module + registry, metadata completeness, in-house rate, peer journals, scope drift, special-issue finder,
methods lexicon (TH/EN + sample size regex; LLM ทางเลือก), quarter diff, "วางบทคัดย่อ" + "ควรตีพิมพ์ที่ไหน" → หน้า `/journals` `/journals/:id` `/methods` `/changes` `/match`

### P3 — Release ผู้บริหาร
institutions (alias+ROR→จังหวัด), เครือข่ายความร่วมมือ, แผนที่จังหวัด, SDG + กรอบไทย, OpenAlex global benchmark, gap finder, concentration risk, KPI เต็ม + brief ฉบับเต็ม → หน้า `/institutions` `/institutions/:id` `/regions` `/sdg` `/global` `/gaps`

### P4 — เครื่องมือเชิงลึกสำหรับนักวิจัย
ค้นหาบทความทั้งคลัง (sharded), galaxy view, keyword trend + glossary, RIS/BibTeX, RSS/Atom, embed widgets, reference analytics + internal citation (ถ้า coverage พอ)

## เรื่องที่ต้องให้ TCI ยืนยัน (กระทบ "นิยาม" ตาม CLAUDE.md §8)
- แก้โค้ด emerging ให้ตรง spec (γ·ln n, s=2.0, burst_frac) — ตัวเลข score จะเปลี่ยนจากเดิม
- เพิ่ม flag `journal_driven` (แสดงเตือนก่อน ไม่เปลี่ยนเกณฑ์จำแนก)
- threshold `share_R < 1.5%` ขึ้นกับความละเอียดของ topic → อาจต้องปรับเมื่อใช้ taxonomy ใหม่
- แหล่ง journal registry (ชื่อเต็ม/ISSN/tier) — TCI มีไฟล์ทางการหรือไม่
- ไฟล์โลโก้ + คู่มือแบรนด์ทางการ (ตอนนี้ใช้ wordmark ชั่วคราว)

## ไฟล์สำคัญที่จะแก้/สร้าง (ตัวอย่าง)
- แก้: `pipeline/atlas/{ingest,cluster,emerging,embed,label,forecast,layout,export,pipeline}.py`, `pipeline/config.example.yaml`, `pipeline/tests/test_emerging.py`, `web/src/lib/loader.ts`, `web/index.html`, `web/package.json`, `docs/*.md`, `CLAUDE.md`, `README.md`
- สร้าง: `pipeline/pyproject.toml`, `pipeline/atlas/cli.py`, `pipeline/atlas/sources/thaijo_md.py`, `pipeline/atlas/synth.py`, `pipeline/atlas/profile.py`, `pipeline/atlas/llm.py`, `pipeline/atlas/schema/` (pydantic contract), `pipeline/atlas/modules/{taxonomy,lineage,journals,institutions,methods,references,sdg,global_bench,narrative}.py`, `pipeline/registry/`, `pipeline/tests/fixtures/` (11 ไฟล์ + golden), `web/src/brand/`, `web/src/data/source.ts`, `web/src/routes/*`, `.github/workflows/{ci,deploy}.yml`, `DESIGN.md`
- reuse: `io_utils.read_table/write_table`, `emerging._cagr/_ols_slope/kleinberg_burst` (แก้ให้ตรง spec), `forecast` model functions, `layout` edge logic, `prompts/*.md` (narrative + merge ที่ออกแบบไว้แล้ว)

## Verification ("เสร็จ" หมายถึงผ่านทั้งหมด)
- **P0:** `uv run pytest -q` (golden 11 ไฟล์: ปี 1970→ปีจาก DOI, ชื่ออังกฤษ, DOI, สังกัดซ้อน, self-cite; emerging rules; fuzz) ·
  `uv run atlas synth --n 20000 && uv run atlas run --config configs/ci.yaml` (CPU, < 10 นาที) ต้องเจอ EMERGING ที่ฝังไว้ + flag journal confound ·
  `uv run atlas profile corpus/` รันกับ 11 ไฟล์จริงได้ · CI เขียว
- **P1:** stability test (snapshot T vs T+1 ไตรมาส synthetic: คง topic ID ≥90%, ARI ≥0.8) · taxonomy accuracy บน held-out · `atlas validate` ·
  `npm run lint && npx tsc -b && npm run build` · Playwright smoke ทุก route (ข้อมูลเต็ม/ว่าง) + axe 0 serious + Lighthouse budget ·
  เปิด HTML เดี่ยวผ่าน `file://` แล้วไม่มี network request · PDF ฟอนต์ไทยถูกต้อง · ตรวจหน้าเว็บจริงด้วย browser (ภาษา, dark mode, mobile)
- **P2+:** precision/coverage ต่อโมดูลบนชุด label มือ (สังกัด 500, วิธีวิจัย 200, SDG 300) · rollback drill ด้วย release tag

## ขั้นตอนหลังอนุมัติแผน
1. บันทึก memory: ผู้ใช้ต้องการฟีเจอร์ครบ 3 กลุ่ม (นักวิจัย/บรรณาธิการ/ผู้บริหาร) + แบรนด์ TCI, และการตัดสินใจข้างต้น
2. บันทึก spec นี้ลง `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md`
3. `git init` (ถาม GitHub username/ชื่อ repo ก่อนสร้าง remote + ก่อน push)
4. ใช้ writing-plans แตก **P0** เป็น implementation plan ละเอียด (TDD) → ดำเนินการด้วย subagent-driven-development → รายงานผล + ตรวจกับคุณก่อนเริ่ม P1
5. งาน UI ทุกครั้งใช้ impeccable (ตาม CLAUDE.md ส่วนตัว) + dataviz สำหรับกราฟ; ตรวจเอกสาร library ล่าสุดผ่าน context7
