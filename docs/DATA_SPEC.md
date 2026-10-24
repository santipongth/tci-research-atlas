# DATA_SPEC — สเปกข้อมูลเข้า/ออก

> สเปกนี้ตรงกับโค้ดใน `pipeline/atlas/` — ถ้าไม่ตรงกันถือเป็นบั๊กของเอกสารหรือโค้ด · นิยามสถานะ/emerging อยู่ที่ `docs/EMERGING_SPEC.md`
> สัญญากับเว็บคือ **contract v2** (§6–§11, `SCHEMA_VERSION = "2.5.0"`) — `atlas_data.json` (§3) เป็นไฟล์ legacy ที่เว็บไม่อ่านแล้ว

**สารบัญ**
| ส่วน | เรื่อง |
|---|---|
| §0 | ข้อมูลเข้าที่แนะนำ: คลังรูปแบบ 1.0 (JSON Lines) |
| §1 | ThaiJO Markdown · §1.1 ตาราง · §1.2 กฎของ ingest (ปี, ซ้ำ, เพดานไฟล์ผิด, `01_ingest_meta.json`) |
| §2 | §2.1 checkpoint ใน work_dir · §2.2 state_dir · §2.3 ไฟล์ที่ผู้ดูแลคัดเอง |
| §3–§5 | legacy: `atlas_data.json` 1.1 · การแปลงฝั่งเว็บ v1 (ลบแล้ว) · ไฟล์สำหรับนักวิเคราะห์ใน `output/` |
| §6 | contract v2: ไฟล์หลัก · §6.1 `manifest.modules` · §6.2 `atlas publish` (latest, ฟีด, offline, ลดขนาดรอบเก่า) · §6.3 `atlas validate` |
| §7–§11 | โมดูลที่เพิ่มทีละ minor: 2.1 บรรณาธิการ · 2.2 ผู้บริหาร · 2.3 นักวิจัย · 2.4 หัวข้อรายปีของวารสาร · 2.5 หัวข้อรายจังหวัด |
| §12 | กติกาความถูกต้องและความเป็นส่วนตัวที่ pipeline บังคับ (ชื่อสถาบัน, ด่าน PDPA, ด่านข้ามไฟล์ P4, journal_key/org_key) |

**ข้อตกลงที่ใช้ทั้งเอกสาร**
- ปีทุกค่าเป็น ค.ศ. · สัดส่วนเป็นเศษส่วน 0–1 (0.10 = 10%) ยกเว้น KPI ที่ชื่อขึ้นต้นด้วย `pct_` เป็นเปอร์เซ็นต์ · ช่วงเชื่อมั่นใช้ชื่อ `*_lo/*_hi` ระดับอยู่ใน `manifest.ci_level`
- L = `last_complete_year`; R / B / W = หน้าต่างของนิยาม emerging (`emerging.recent_window` / `baseline_window` / `trend_window`, ดีฟอลต์ 3 / 5 / 5 ปี — EMERGING_SPEC §2)
- โมดูลวารสาร วิธีวิจัย และสถาบันใช้หน้าต่างของตัวเอง = `journals.window_years` / `methods.window_years` / `institutions.window_years` ปีสมบูรณ์ล่าสุด (ดีฟอลต์ 5 ปีเท่ากับ W แต่เป็นคนละ key) — ในเอกสารนี้เรียกว่า "หน้าต่างของโมดูล"
- "ช่วงที่วิเคราะห์" (`atlas.checkpoints.analysed_window`) = ปีแรก … ปีสุดท้ายของ `06_meta.json → years` + `trimmed_years` (ใช้โดย references, search, galaxy, kwtrends-glossary)

## 0. Input ที่แนะนำ: คลังรูปแบบ 1.0 (`input.format: corpus_jsonl`)

- **รูปแบบ:** JSON Lines หนึ่งบรรทัดต่อบทความ (UTF-8) ในไฟล์ใต้ `input.path` ที่ตรง `input.corpus_glob` (ดีฟอลต์ `articles/**/*.jsonl*`) และลงท้าย `.jsonl`, `.jsonl.gz`, `.ndjson` หรือ `.ndjson.gz` (ไฟล์ที่ชื่อขึ้นต้นด้วย `_` ถูกข้าม; ไม่พบไฟล์เลย = `FileNotFoundError`) พร้อม `<คลัง>/journals.csv`
- **คู่มือสำหรับทีมข้อมูล:** `docs/corpus/README.md` · **ตัวอย่าง:** `docs/corpus/example/`
- **schema:** `CORPUS_SCHEMA = "tci-atlas-corpus/1.0"` — `docs/corpus/corpus.schema.json` สร้างจาก `pipeline/atlas/schema/corpus.py` ด้วย `atlas corpus schema` (test ตรวจ drift)
  - ทุกบรรทัดต้องมี `"schema": "tci-atlas-corpus/1.0"`, `journal_key` (ASCII ไม่มีช่องว่าง ≤ 200 ตัว) และ `title.th` หรือ `title.en`; key ที่ไม่รู้จัก = error (ข้อมูลอื่นใส่ใน `extra`)
  - ฟิลด์: `id`, `source` (thaijo/tci/other), `doi` (`10.xxxx/…`), `url`, `issue_url`, `journal_key`, `journal_title {th,en}`, `issn`, `eissn`, `volume`, `issue`, `pages {first,last}`, `published` (วันที่ ISO), `year`, `article_type` (research-article · review-article · academic-article · case-report · short-communication · book-review · editorial · erratum · other), `language` (ISO 639-1), `title`, `abstract`, `keywords {th[], en[]}`, `authors[]` (`position`, `name {th,en}`, `orcid`, `corresponding`, `role` ∈ lecturer · researcher · student-master · student-doctoral · student · other, `affiliations[] {name {th,en}, ror (https://ror.org/…), country (ISO 3166-1 alpha-2), province (หนึ่งใน 77 รหัส ISO 3166-2:TH)}`), `references[] {text, doi, year, translated}`, `funding[]`, `license`, `provenance`, `extra`
  - ปี > 2400 (พ.ศ.) ถูกปฏิเสธ (ต้องเขียน ค.ศ.); `year` > 2100 ถูกปฏิเสธ; `year` ต้องตรงกับปีของ `published` เมื่อมีทั้งคู่
- **ตัวอ่าน:** `atlas/sources/corpus_jsonl.py`
  - ตรวจทุกบรรทัดกับ model แล้วแปลงเป็น record แบบเดียวกับ `parse_markdown` ทุก step หลัง ingest จึงไม่ต้องแก้ (ไบต์ที่ถอดรหัสไม่ได้กลายเป็น U+FFFD และติด flag `decode_replaced`)
  - บรรทัดที่ไม่ใช่ JSON หรือไม่ผ่าน model บันทึกเป็นแถวของ `01_ingest_errors` ในรูป `path = "ไฟล์:บรรทัด"`; ไฟล์ .gz ที่อ่านไม่ได้ = 1 แถว error ทั้งไฟล์; เพดาน `input.max_error_ratio` คิดจาก "บรรทัด" (บทความ + error + บทความที่ถูกตัดตามประเภท)
  - `input.exclude_article_types` (ดีฟอลต์ `[editorial, erratum, book-review]`) ตัดประเภทที่ไม่ใช่ผลงานวิจัยออก และพิมพ์จำนวนต่อประเภท
  - ปี: `published` มีค่า → ปีของ `published` (`year_source = "published"`); ไม่มี → `year` (`"given"`); ไม่มีทั้งคู่ → ใช้ median ของฉบับ (§1.2); `issue_url` ว่างแต่มี volume/issue → สร้างคีย์ฉบับ `issue:<journal_key>:<volume>:<issue>`
  - `journal_name` = `journal_title.th` หรือ `.en` หรือส่วนท้ายของ `journal_key`; ผู้แต่งเรียงตาม `position` (ไม่มี = ลำดับในรายการ); `is_student` = role ขึ้นต้นด้วย student
- **รหัสบทความ** (ต้องไม่เปลี่ยนข้ามไตรมาส):
  1. ใช้ `id` ที่ทีมใส่มาก่อน
  2. ไม่มี → ถ้า `url` เป็น URL บทความ ThaiJO ใช้ `<server>:<journal path>:<เลข>` เช่น `so02:BECJournal:54875` (ตรงกับคลัง .md — ประวัติหัวข้อและ embedding store ใช้ต่อได้)
  3. ไม่มี URL → `doi:<doi ตัวพิมพ์เล็ก>`
  4. ไม่มี DOI → `tci:` + 16 hex แรกของ sha1(`journal_key|ชื่อเรื่องที่ normalize แล้ว (ไทย ถ้าไม่มีใช้อังกฤษ)|ปี`)
- **คอลัมน์เฉพาะคลัง 1.0 ใน checkpoint** (ทางอื่นเป็นค่าว่าง):
  - `01_articles`: `journal_key`, `article_type`, `language`, `issn`, `eissn`, `volume`, `issue`
  - `01_authors`: `orcid`, `ror`, `country`, `province` และ **หนึ่งแถวต่อผู้แต่งต่อสังกัด** (`affiliation_index` = สังกัดลำดับที่เท่าไรของผู้แต่ง; ผู้แต่งที่ไม่มีสังกัดมี 1 แถวว่าง)
  - `registry.journal_keys` ใช้ `journal_key` ที่ทีมใส่มาก่อน (ก่อนสร้างจากรหัสบทความ/ชื่อวารสาร)
  - `institutions_ref.Resolver` ใช้ `ror` / `country` / `province` เป็นค่าบอกใบ้ แต่ไม่ทับ alias ที่คัดเอง
- **`journals.csv`** = ทะเบียนวารสาร (คอลัมน์เดียวกับ `pipeline/registry/journals.example.csv`: `journal_key, name_th, name_en, issn, eissn, tci_tier, tci_field, publisher_org, url`) — pipeline อ่านผ่าน `journals.registry_path` (`config.example.yaml` ชี้ `../corpus/journals.csv`; `atlas quarterly` ใช้ไฟล์ที่ส่งมาพร้อมคลังแทนค่าใน config) · `atlas profile` ตรวจไฟล์ประกอบ (`journals.csv`, `institutions_aliases.csv`, `province_population.csv`, `ror.zip`) ด้วยตัวอ่านเดียวกับ pipeline
- **ย้ายคลังเดิม:** `atlas corpus convert <โฟลเดอร์ .md> --out <โฟลเดอร์>` → `articles/part-NNNN.jsonl.gz` + `journals.csv` (เมื่อยังไม่มี) ได้ตาราง ingest เท่าเดิม (test parity) และรหัสบทความเดิม

## 1. Input: ThaiJO Markdown (ค่าดีฟอลต์ของโค้ด `input.format: thaijo_md`)
(`config.example.yaml` ตั้ง `corpus_jsonl`; ไม่ใส่ `input.format` = `thaijo_md`)
หนึ่งไฟล์ .md ต่อบทความ ตรง `input.glob` (ดีฟอลต์ `**/*.md`; ไฟล์ที่ชื่อขึ้นต้นด้วย `_` ถูกข้าม; ตัวอย่างจริงใน `pipeline/tests/fixtures/thaijo_md/`) — อ่านแบบ `utf-8-sig` โดยไบต์ที่ไม่ใช่ UTF-8 กลายเป็น U+FFFD (บทความยังถูกเก็บ + flag `decode_replaced`); parse ทีละ `input.batch_files` (20,000) ไฟล์ ใช้ `input.workers` process เมื่อไฟล์ > 2,000

| ส่วน | รูปแบบ | ที่ pipeline ทำ |
|---|---|---|
| `# ชื่อเรื่อง` | ไทย, อังกฤษ, `TH [EN]` หรือ `EN (TH)` | แยก title_th / title_en (วงเล็บต้องเป็นอีกภาษาและยาว ≥ 15 ตัวอักษร — `(TQA)` ไม่ถูกแยก); ไม่มีชื่ออังกฤษ → ใช้ส่วนชื่ออังกฤษในบทคัดย่อ |
| `**Journal:**` | OJS path เช่น `BECJournal` | journal_name (ว่าง → OJS path จาก URL; ชื่อเต็ม/ISSN มาจากทะเบียนวารสาร) |
| `**Published:**` | YYYY-MM-DD; `1970-01-01` = วันที่หาย | ปี: Published (พ.ศ. → ค.ศ.) → ปีในรูป `.YYYY.` ของ DOI → median ของฉบับ (`issue_url`) → ว่าง · `year_source` = `published` \| `doi` \| `issue_median` \| `""` |
| `**Pages:**`, `**Issue URL:**` | ข้อความ / URL ของฉบับ | pages, issue_url (ใช้หา median ปีของฉบับ) |
| `**Article URL:**` | `https://<server>.tci-thaijo.org/index.php/<journal>/article/view/<id>` | article_id = `<server>:<journal>:<id>` เช่น `so02:BECJournal:54875` (ไม่มี URL → `file:` + 16 hex แรกของ sha1(`<ชื่อโฟลเดอร์>/<ชื่อไฟล์>`)) |
| `**Authors:**` | `- ชื่อ [EN name] (สังกัดไทย (สังกัด EN))` + คำนำหน้าวิชาการ | ชื่อ, สังกัด TH/EN, role (ตำแหน่งวิชาการ/นักศึกษาที่ตัดออกจากสังกัด), is_student, org_key |
| `**Keywords:**` | ไทย+อังกฤษคั่น `,` หรือ `;` | keywords_th / keywords_en (แยกตามสัดส่วนอักษรไทย) |
| `## Abstract` | บทคัดย่อไทย␣␣␣ชื่ออังกฤษ␣␣␣บทคัดย่ออังกฤษ␣␣␣DOI: … | แยกด้วยช่องว่าง ≥2 + สัดส่วนอักษร; ดึง DOI; ตัด label "Abstract" |
| `## References` | bullet ที่ถูกตัดบรรทัด | ต่อบรรทัด, ปีในวงเล็บแรก (พ.ศ.→ค.ศ.), lang (`th` \| `latin`), ตัด self-citation และส่วน "Translated Thai References" ออกจากการนับ (`n_references`) |

ปัญหาข้อความที่ซ่อมให้อัตโนมัติ (`atlas.thai.clean_text`): อักษรไทย Private-Use (U+F700–F71A) จาก PDF, `ํา`→`ำ`, ช่องว่างก่อนสระบน/ล่าง · flag ใน `text_quality` (คั่น `; `): `thai_pua_repaired`, `tone_marks_missing` (บทคัดย่อไทย ≥ 200 อักษรที่ไม้โท < 0.5%), `stat_symbols_missing` (เช่น `( = 3`), `decode_replaced`

### 1.1 Input แบบตาราง (`input.format: table`)
ไฟล์เดียว `.csv` / `.json` (list หรือ dict ที่มี list) / `.jsonl` / `.ndjson` / `.parquet` ที่ `input.path` — `input.columns` จับคู่ "ชื่อคอลัมน์มาตรฐาน: ชื่อคอลัมน์ในไฟล์" (ต้องมี `article_id`); `year_source = "table"`; ผู้แต่งและสังกัดเป็นข้อความคั่น `;` จับคู่ตามลำดับ (ผู้แต่งคนที่ i ↔ สังกัดที่ i, `affiliation_index` = 0); ไม่มีรายการอ้างอิง, `n_student_authors = 0`; วารสารระบุด้วย `name:<ชื่อที่ normalize แล้ว>`

### 1.2 กฎที่ ingest ทำให้ (`atlas/ingest.py`, ตามลำดับ)
1. **ปี** (`normalize_years`): ค่า > 2400 ถือเป็น พ.ศ. (− 543) แล้วตัดแถวที่ปี < `input.min_year` (1990) หรือ > `input.max_year` (null = ปีปัจจุบัน + 1) — บทความที่ไม่มีปีถูกเก็บไว้ (นับเป็น `year_missing`; ไม่เข้าอนุกรมเวลา)
2. **ชื่อเรื่อง:** ไม่มีทั้ง title_th และ title_en → ตัดทิ้ง
3. **ซ้ำ** (`input.dedup.enabled: true`): เรียงให้เรคคอร์ดที่ครบที่สุดมาก่อน (นับฟิลด์ที่ไม่ว่างใน title_th/en, abstract_th/en, keywords_th/en, doi, authors; เสมอกันเรียงตาม article_id) แล้วเก็บตัวแรกของแต่ละชุดซ้ำ:
   - article_id ซ้ำ → ซ้ำ (**ทำเสมอแม้ปิด dedup**)
   - DOI เดียวกัน (ตัวพิมพ์เล็ก ตัดช่องว่าง) **และ** ชื่อเรื่องไทย หรือชื่อเรื่องอังกฤษที่ normalize แล้ว (80 ตัวแรก) ตรงกันอย่างน้อยฝั่งหนึ่ง (ฝั่งที่ว่างไม่นับ) → ซ้ำ; DOI เดียวกันแต่ทั้งไทยและอังกฤษต่างกัน = metadata ผิด เก็บทุกเรื่องและนับเป็น `doi_title_conflicts` (พิมพ์เตือน)
   - ชื่อเรื่อง**ทั้งชื่อ**ที่ normalize แล้ว (`title` = ไทย ถ้าไม่มีใช้อังกฤษ) + ปี → ซ้ำ เว้นแต่ทั้งสองเรื่องมี DOI และ DOI ต่างกัน; ชื่อสั้น < 40 ตัวอักษร (เช่น "บทบรรณาธิการ") ต้องเป็นวารสาร (`journal_key`) เดียวกันด้วย
4. แถวผู้แต่งและรายการอ้างอิงเหลือเฉพาะของบทความที่เก็บ (ตัดซ้ำด้วย `(article_id, position, affiliation_index)` / `(article_id, position)`)
5. **เพดานไฟล์ผิด:** เขียน `01_ingest_errors` (path, error = `"ชนิด: ข้อความ"`; เขียนทุกรอบ อาจว่าง) **ก่อน** แล้วตรวจ: ไม่มีไฟล์/บรรทัดใด parse ได้ หรือสัดส่วน error > `input.max_error_ratio` (0.01) → `RuntimeError` และ**ไม่เขียน** `01_articles/01_authors/01_references` (รอบที่ถูกปฏิเสธจึงไม่ทิ้งคลังที่บางลงไว้ให้ step ถัดไป)
6. เขียน checkpoint + `01_ingest_meta.json` = `{records, articles, outside_year_range, no_title, duplicates, year_missing, files_with_errors}` และพิมพ์บรรทัดสรุปเดียวกัน

ตรวจคลังก่อนรัน: `uv run atlas profile <คลัง> --md ../logs/profile.md` (`--format auto|corpus_jsonl|thaijo_md`, `--out` JSON, `--aliases-todo` CSV ของสังกัดที่ยังไม่มี alias) — รายงานคุณภาพคลัง: จำนวนไฟล์/บรรทัด ที่อ่าน/parse ไม่ได้ ช่วงปี บทความลงวันที่ล่วงหน้า ยอดต่อปีเทียบปีก่อน ฟิลด์ว่าง วารสารที่อัปโหลดย้อนหลัง DOI ซ้ำแต่ชื่อเรื่องต่างกัน ไฟล์ประกอบ; exit 1 เมื่อต้องแก้ก่อนส่งมอบ

## 2. Checkpoints (work_dir — ลบได้) และ state (state_dir — ห้ามลบ)
ไฟล์ตารางใช้ `io_utils.write_table/read_table` (parquet ถ้ามี pyarrow, ไม่งั้น pickle) · checkpoint ของ P2–P4 (`12_*`–`21_*`) อยู่ใน §7–§9

### 2.1 work_dir

| ไฟล์ | step | คอลัมน์ / เนื้อหา |
|---|---|---|
| `01_articles` | ingest | article_id, source_path, url, issue_url, journal_name, published, year (Int64, ว่างได้), year_source, pages, doi, title_th/en, abstract_th/en, keywords_th/en (คั่น `; `), authors (ชื่อผู้แต่ง คั่น `; ` — อ่านใน step ที่ได้รับอนุญาตเท่านั้น), affiliations, n_authors, n_student_authors, n_references, has_references, self_citation_only, text_quality, journal_key, article_type, language, issn, eissn, volume, issue + คอลัมน์ช่วย title (ไทย ถ้าไม่มีใช้อังกฤษ), abstract, keywords |
| `01_authors` | ingest | article_id, position (ลำดับผู้แต่ง), affiliation_index, name, name_en, affiliation_th/en, role, is_student, org_key, orcid, ror, country, province — หนึ่งแถวต่อผู้แต่งต่อสังกัด |
| `01_ingest_errors` | ingest | path (ไฟล์ หรือ `ไฟล์:บรรทัด`), error (`"ชนิด: ข้อความ"`) — เขียนทุกรอบ อาจว่าง |
| `01_ingest_meta.json` | ingest | records, articles, outside_year_range, no_title, duplicates, year_missing, files_with_errors |
| `01_references` | ingest | article_id, position, text, year, lang (`th` \| `latin`), translated, self_citation |
| `02_docs` | preprocess | 01_articles + doc_text (`embedding.doc_fields` ต่อกัน ≤ `embedding.max_chars_per_doc`) — บทความที่ doc_text < 10 ตัวอักษรถูกตัด |
| `03_embeddings.npy`, `03_meta.json` | embed | matrix (แถวตรงกับ 02_docs, normalize แล้ว); meta: model_id (= store id; lite = `lite\|char<min>-<max>\|svd<dim>`), n, dim, docs_fingerprint (sha256 ของลำดับ article_id — `load_aligned` ปฏิเสธเวกเตอร์ของ 02_docs อื่น) + สำหรับ api/local: store_id, n_retries, n_truncated |
| `04_fine_topics` | cluster | article_id, fine_topic (−1 = ยังไม่จัดหมวด) |
| `04_coarse_topics` | cluster | article_id, coarse_topic (−1 = ยังไม่จัดหมวด) |
| `04_topic_info` | cluster | level (`fine`), topic_id, size, top_terms, top_keywords, coarse_topic, coherence (cosine เฉลี่ยกับ centroid) |
| `04_centroids.npy`, `04_centroid_ids.json` | cluster | centroid ต่อหัวข้อ |
| `04_lineage`, `04_topics_meta.json` | cluster | event (new/continue/split/merge/retired), topic_id, parents (`;`) · release (รอบที่ทุกขั้นหลัง cluster ต้องเขียน — `atlas.state.work_release`), previous_release, mode (fit/assign), snapshot_at (เวลาท้องถิ่น ISO 8601 พร้อม offset: ใช้กำหนด as_of_year, เพดานเดือน nowcast และ generated_at), kept_fraction, n_topics, events |
| `05_labels` | label | level, topic_id, name_th, name_en, description, keywords, cache_key (key ของ LLM cache หรือ `"fallback"`), label_source (`llm` \| `keywords` \| `override` \| `reused` = ชื่อของรอบก่อน: lineage `continue` และคำสำคัญ + คำเด่นยังทับซ้อนกับชุดคำตอนตั้งชื่อ ≥ `labeling.reuse_min_jaccard` — ไม่เรียก LLM) |
| `05_labels_meta.json` | label | provider, model_id, topics, from_cache, generated, repaired, fallback, reused, overrides, unknown_overrides, cost_usd (การรันครั้งนี้) |
| `05_merge_suggestions`, `05_merge_meta.json` | label | topic_a, topic_b, similarity, same_topic (True/False/None), reason, source · สถิติ LLM งาน merge |
| `06_series` | series | topic_id, year, count, count_with_org (บทความที่มี org_key ≥ 1), corpus_total (บทความที่มีปีทั้งหมดของปีนั้น รวมที่ยังไม่จัดหมวด), share — หนึ่งแถวต่อหัวข้อ × ทุกปีที่มีบทความ ≤ L (หัวข้อที่ไม่มีบทความในช่วงนั้นก็มีแถวศูนย์) |
| `06_topic_journal_year` · `06_topic_org_year` · `06_journal_first_year` | series | topic_id, journal (= `journal_key`), year, count · topic_id, org_key, year, count · journal, first_year (ปีแรกในบทความที่มีปีทั้งคลัง) — ใช้คำนวณความกว้าง (EMERGING_SPEC §3) |
| `06_months`, `06_partial_year` | series | year, month, count (วันที่ตีพิมพ์ที่ปีตรงกับปีบทความ) · topic_id, year, count ของปีหลัง L (ใช้ทำ nowcast) |
| `06_meta.json` | series | last_complete_year, n_articles (ทั้ง 02_docs = `kpis.articles`), as_of_year, snapshot_at (คัดลอกจาก 04_topics_meta), trimmed_years (ปีที่มีข้อมูลหลัง L), years, totals (บทความที่มีปีต่อปี ≤ L), partial_totals (ยอดของปีหลัง L), completeness {method: `median` (backfill guard v3) \| `configured`} |
| `07_emerging` | emerging | topic_id, count_recent, share_recent, share_baseline, share_ratio, share_growth(_lo/_hi), cagr_recent, acceleration, burst_frac, burst_years, novelty, coherence, n_journals_R, journal_hhi, new_journal_share, n_orgs_R, org_coverage_R, orgs_unverified, status, journal_driven, large_share_threshold, emerging_score, last_complete_year, definition_version — ดู EMERGING_SPEC §3 (คอลัมน์ครบแม้ไม่มีหัวข้อ) |
| `07_keywords` | keywords | term, key, count_recent, count_baseline, share_ratio, no_baseline, growth(_lo/_hi), n_active_years, n_orgs_R, n_journals_R, new_journal_share, journal_driven, topic_id, emerging (EMERGING_SPEC §8) |
| `08_forecasts`, `08_forecast_meta.json` | forecast | topic_id, model (`naive` \| `drift` \| `nb_glm` \| `ets_damped`), backtest_mae, backtest_mape, mase, skill_vs_naive, show, hist_years/hist_counts/fc_years/fc_mean (JSON), fc_lo/fc_hi (= 95%), fc_lo80/hi80/lo95/hi95, nowcast_year/month/ytd/mean · total_model, total_years, total_mean, conformal {h: {level: q}}, n_calibration, nowcast {year, as_of_month, fraction, ytd, mean} หรือ null — ช่วงคาลิเบรตจากเรคคอร์ด honest ของโมเดลที่เลือก; `show` = skill gate (EMERGING_SPEC §9); หัวข้อ LOW_DATA ไม่มีแถว; nowcast มีเฉพาะปีปฏิทินที่กำลังดำเนินอยู่ (= L + 1 = as_of_year) |
| `09_layout`, `09_edges`, `09_galaxy` | layout | kind (`group` \| `topic`), id, x, y, r, parent · s, t, w · article_id, topic_id, gx, gy (เมื่อ `layout.galaxy: true`) |
| `10_taxonomy`, `10_taxonomy_meta.json` | taxonomy | topic_id, group_id, group_en/th, subfield_id/en, vote_share, cross_field, source · version, holdout accuracy — เมื่อ fallback เป็น agglomerative: group_id = 1000 + coarse, code `G<n>`, ชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" / "Unmapped group N", meta มีเหตุผล (เช่น งบ OpenAlex รายวันหมด) |
| `11_narratives`, `11_brief.json` | narrate | topic_id, status, th, en, source (`llm` \| `template`) · {brief, llm} |

### 2.2 state_dir (ถาวรข้ามรอบ)

| ไฟล์ | step | เนื้อหา |
|---|---|---|
| `embeddings/<slug>-<hash>/` | embed | index.parquet + shard_NNNNN.npy (slug/hash จาก store id: `api\|<model>\|<dimensions>` หรือ `embedding.api.store_id` — ไม่รวม base_url; `local\|<model>\|<max_seq_length>`; hash = sha1 8 ตัวแรก) |
| `…/<store>/journal.bin` | embed | write-ahead log ของเวกเตอร์ที่ได้แล้วแต่ยังไม่เข้า store: header `ATJ1` + uint32 dim; record = sha1 key 40 ไบต์ ASCII + dim × float32 little-endian (flush ทุก batch, fsync ≤ ทุก 10 วินาที) — รันครั้งถัดไป replay เข้า store แล้วลบ (record ท้ายที่ขาด/เสียถูกข้าม) |
| `…/<store>/progress.json` | embed | สถานะงาน (เขียนแบบ atomic ทุก ~5 วินาที + ทุก flush/เปลี่ยนสถานะ): kind, store_id, status (`running`/`backing_off`/`stopped`/`done`/`failed`), pid, total, cached, embedded, remaining, rate_per_s, eta_s, retries, truncated, truncated_total, store_vectors, journal_pending, checkpoint_postponed, last_error, last_error_at, last_event, recovered, started_at, updated_at — อ่านด้วย `atlas status` (แสดง `interrupted` เมื่อ process ตาย, `hung` เมื่อยังอยู่แต่ heartbeat เก่ากว่า `lock_stale_seconds`); ระหว่างรัน status ใช้ store_vectors/journal_pending จากไฟล์นี้ ไม่เปิดไฟล์ store |
| `…/<store>/.lock` | embed | ไฟล์ว่าง ไม่ถูกลบ — process ที่รันถือ OS lock (msvcrt/fcntl) บนไฟล์นี้ตลอดการรัน = กันรันซ้อนจริง; OS ปล่อยเองเมื่อ process ตาย; `atlas status` ตัดสินว่างานยังรันอยู่จาก lock นี้ (ลองล็อกแบบไม่รอแล้วปล่อยทันที) |
| `…/<store>/run.lock` | embed | ข้อมูลเท่านั้น `{pid, host, started_at, pid_started}` (pid_started = เวลาเริ่ม process จาก OS กัน PID reuse) — `atlas status` ใช้บอกว่า process ยังอยู่ไหม; ลบเมื่อจบ (ค้างได้ ไม่มีผล) |
| `…/<store>/run.log` | embed `--background` | stdout+stderr ของการรันเบื้องหลัง (ต่อท้ายทุกครั้ง) |
| `…/<store>/stop.flag` | embed-stop | คำขอหยุด — runner หยุดสุภาพ (รอ request ที่ค้าง, flush) แล้วลบ; flag ที่เขียนก่อน process ที่รันเริ่ม = ค้างจากรอบก่อน ถูกลบทิ้ง, flag ที่ใหม่กว่า (เช่น สั่งตอนยัง ingest) ถูกทำตาม |
| `…/<store>/truncated.parquet` | embed | key, original_chars, used_chars, run_started_at — ข้อความที่ server รับไม่ได้จนต้องตัด (ต่อท้ายทุกรอบ, สะสม; `atlas status` แสดงจำนวนรวม) |
| `llm_cache/<task>.jsonl` | label, narrate, methods | cache + journal ของทุก call LLM: key = sha256(model + prompt_version + prompt)[:16] · output (null = บันทึกค่าใช้จ่ายของ call ที่ใช้ fallback) · cost_usd · release |
| `llm_cache/progress.json`, `.lock`, `run.lock`, `stop.flag`, `run.log` | label, narrate | ไฟล์งานแบบเดียวกับ embedding store (P0 `atlas.jobs`): สถานะ (`atlas status`, kind `llm`), OS lock กันรันซ้อน (+ ข้อมูล PID), คำขอหยุด (`atlas llm-stop`), log ของ `atlas llm --background` |
| `releases/index.json` | cluster | ลำดับรอบที่เขียนแล้ว (เก่า → ใหม่) — ใช้หา previous_release และตัดสินว่ารอบไหนใหม่สุด |
| `releases/<release>/topics/` | cluster | assignments, registry (born/status/last_seen), lineage, model.json (embedding_model, fitted_release, releases_since_fit, next_id, mode) |
| `releases/<release>/layout.parquet` | layout | ตำแหน่งหัวข้อ (topic_id, x, y) — แผนที่รอบถัดไปวางต่อจากนี้ |
| `releases/<release>/labels.parquet` | label | ชื่อหัวข้อจากเครื่อง (ก่อน overrides): topic_id, name_th/en, description, keywords, cache_key, origin (`llm` \| `keywords`), label_terms (ชุดคำที่ใช้ตั้งชื่อ — รอบถัดไปเทียบ Jaccard กับชุดนี้ จึงไม่ไหลทีละนิด) |
| `releases/<release>/snapshot.json` | export | สรุปย่อของรอบสำหรับ `diff.json` ของรอบถัดไป (§7) |
| `openalex/` (`reference_*.parquet` + `.json` และ request cache) | taxonomy, benchmark | งานอ้างอิง OpenAlex ที่ดึงแล้ว (ไม่ดึงซ้ำ; cache ใช้ร่วมกันทั้งโหมดมี key และไม่มี key) |
| `ror/<dump>.<country>.json` | institutions | แคชข้อมูล ROR เฉพาะประเทศ (สร้างจาก `institutions.ror_path` ครั้งแรกครั้งเดียว) |
| `prev/centroids.npy`, `prev/centroid_ids.json` | export (legacy) | สำเนา centroid ของรอบล่าสุด (ไฟล์ของ export 1.1) |

### 2.3 ไฟล์ที่ผู้ดูแลคัดเอง (`pipeline/registry/`, ไม่เข้า git — repo มีแต่ `*.example.csv`)

| ไฟล์ | อ่านโดย | เนื้อหา |
|---|---|---|
| `label_overrides.csv` (`labeling.overrides_path`) | label | ชื่อที่บรรณาธิการแก้: topic_id (T000123), name_th, name_en, description, reviewer, reviewed_at, note |
| `journals.csv` (`journals.registry_path`) | journals | ทะเบียนวารสาร (§0) |
| `institutions_aliases.csv` (`institutions.aliases_path`) | institutions | alias, inst_id, name_th, name_en, type, province, country, ror |
| `province_population.csv` (`institutions.population_path`) | institutions | code, population, year → บทความต่อประชากรแสนคน |

## 3. Legacy output: `atlas_data.json` (schema 1.1)

> **legacy — เว็บ v2 ไม่อ่านไฟล์นี้แล้ว** (อ่าน contract v2 ใน §6) · `atlas/export.py` ยังเขียน `output/atlas_data.json` ทุกครั้งที่รันขั้น export (เพื่อความเข้ากันได้กับเครื่องมือภายนอก) แล้วจึงเขียน contract v2 เมื่อ `export.v2: true`

```jsonc
{
  "meta": {
    "generated_at": "2026-10-18T...",   // snapshot_at ของขั้น cluster แปลงเป็น UTC (export ซ้ำได้ค่าเดิม)
    "pipeline_version": "git hash หรือ nogit",
    "schema_version": "1.1",
    "definition_version": 4,
    "last_complete_year": 2024,          // ปีสมบูรณ์สุดท้าย (หลัง backfill guard)
    "as_of_year": 2026,                  // จาก 06_meta.json (config emerging.as_of_year หรือปีของ snapshot)
    "trimmed_years": [2025, 2026],       // ปีที่มีข้อมูลหลัง last_complete_year (ไม่ใช้คำนวณแนวโน้ม)
    "total_articles": 200003,            // แถวใน 02_docs
    "assigned_articles": 198000,
    "unassigned_articles": 2003,
    "total_topics": 132,
    "total_groups": 14,
    "n_orgs_unverified": 3               // จำนวนหัวข้อที่ข้ามเกณฑ์สถาบัน (ทุกสถานะ)
  },
  "groups": [
    { "id": "g33", "th": "สังคมศาสตร์", "en": "Social Sciences", "color": "#E5484D",
      "articles": 52000, "rank": 1 }     // id = "g" + group_id ของ taxonomy (สาขา OpenAlex หรือ 1000+coarse); สี hex จาก PALETTE legacy; เรียงตาม articles desc
  ],
  "nodes": [
    // kind = "group" (จุดศูนย์กลางกลุ่ม)
    { "nodeId": "g33", "kind": "group", "id": "g33", "th": "...", "en": "...",
      "color": "#E5484D", "articles": 52000, "rank": 1,
      "x": 840.0, "y": 520.0, "r": 96.0, "nTopics": 12 },
    // kind = "topic"
    { "nodeId": "t17", "kind": "topic",
      "group": "g33",                   // id กลุ่มแม่
      "th": "การเฝ้าระวังฝุ่น PM2.5", "en": "PM2.5 monitoring",
      "description": "คำอธิบาย 1 บรรทัด",
      "keywords": "PM2.5; คุณภาพอากาศ; ...",   // คั่นด้วย ;
      "articles": 900, "color": "#E5484D",
      "x": 812.4, "y": 448.2, "r": 30.1,
      "status": "EMERGING",             // EMERGING | WATCH | HOT | DECLINING | STABLE | LOW_DATA
      "emerging_score": 92.5,           // 0–100 หรือ null
      "cagr_recent": 0.612,             // CAGR ช่วง R (ทศนิยม)
      "burst_years": "2022,2023",       // ปีที่ burst คั่นด้วย , หรือ ""
      "share_growth": 0.42, "share_growth_lo": 0.18, "share_growth_hi": 0.71,  // null = ประมาณไม่ได้
      "n_journals_R": 9, "n_orgs_R": 14,
      "journal_driven": false,
      "orgs_unverified": false,         // (v3): ข้อมูลสังกัดใน R ไม่พอ → ไม่ได้ตรวจเกณฑ์ "≥ 3 สถาบัน"
      "coherence": 0.31,                // จาก 04_topic_info
      "forecast_uncertain": false,
      "forecast": {                      // null ถ้าไม่ผ่าน skill gate, status = LOW_DATA หรือปิด export.include_forecast_in_json
        "model": "nb_glm",              // naive | drift | nb_glm | ets_damped
        "backtest_mape": 12.4,          // %
        "mase": 0.8, "skill_vs_naive": 0.2,
        "hist_years":  [2017, ..., 2024],
        "hist_counts": [  12, ...,  240],
        "fc_years":    [2025, 2026],
        "fc_mean":     [ 268,  295],
        "fc_lo":       [ 231,  244],    // ช่วง 95%
        "fc_hi":       [ 305,  346]
      }
    }
  ],
  "links": [
    { "s": "t17", "t": "t42", "w": 0.61 }   // edge ความคล้ายระหว่าง topic (09_edges)
  ]
}
```

### schema 1.1 additions (เทียบ 1.0)
ต่อ node แบบ topic เพิ่ม: `share_growth`, `share_growth_lo`, `share_growth_hi` (null = ประมาณไม่ได้), `n_journals_R`, `n_orgs_R`, `journal_driven`, `orgs_unverified` (v3, additive), `coherence`, `forecast_uncertain`
ต่อ `meta` เพิ่ม: `schema_version = "1.1"`, `definition_version = 4`, `assigned_articles`, `unassigned_articles`, และ (v3, additive) `as_of_year`, `trimmed_years`, `n_orgs_unverified`
`forecast` เป็น null เว้นแต่ผ่าน skill gate (`show` = true) และสถานะไม่ใช่ `LOW_DATA`; `forecast_uncertain` = true เมื่อมี forecast แต่ไม่ผ่าน gate หรือหัวข้อเป็น `LOW_DATA`
`07_emerging` ที่ไม่มีคอลัมน์ `orgs_unverified` (work_dir ก่อน v3) → export หยุดด้วย error (ไม่เดาค่า)

## 4. Legacy: การแปลงฝั่งเว็บ v1
เว็บ v1 (`web/src/lib/loader.ts` → `normalize`) แปลง snake_case ของ §3 เป็น camelCase — **ถูกลบไปพร้อมเว็บ v1 แล้ว** เว็บ v2 อ่านเฉพาะ contract v2 ผ่าน `web/src/data/source.ts` + `release.ts` และใช้ชนิดข้อมูลจาก `web/src/data/contract.ts` ที่ generate จาก schema โดยตรง (ไม่มีขั้นแปลงชื่อฟิลด์)

## 5. ไฟล์เสริมสำหรับนักวิเคราะห์ (`output/`)
เขียนโดย `atlas/export.py` ทุกรอบ export (CSV เมื่อ `export.formats` มี `csv`):

| ไฟล์ | เนื้อหา |
|---|---|
| `topics.csv` | `04_topic_info` + ชื่อ/คำอธิบาย/keywords จาก `05_labels` (id, ชื่อ, คำอธิบาย, keywords, size, กลุ่ม) |
| `emerging.csv` | `07_emerging` ทุกคอลัมน์ (เอาไป pivot/plot ต่อเองได้) |
| `forecasts.csv` | `08_forecasts` ทุกคอลัมน์ |
| `manifest.json` | (ของ export 1.1 — คนละไฟล์กับ `data/<release>/manifest.json`) pipeline_version, generated_at, schema_version `1.1`, `definition_version`, `ci_level`, `as_of_year`, `trimmed_years`, `n_orgs_unverified`, `embedding_provider`, `embedding_model_id` (จาก 03_meta.json), `n_labels_fallback` (หัวข้อที่ได้ชื่อจาก keyword แทน LLM), `ingest_errors` (จำนวนแถวใน 01_ingest_errors; null = ไม่มีบันทึก), `config_emerging` (config emerging ที่ใช้), `counts` (= meta), `artifacts` (ชื่อไฟล์ใน output/) — ใช้ย้อนดูว่ารอบนั้นคำนวณด้วยนิยาม/ข้อมูลแบบไหน |

## 6. Data contract v2 (P1)

`pipeline/atlas/schema/contract.py` (pydantic = source of truth) → `web/src/data/contract.schema.json` → `web/src/data/contract.ts`
สร้างด้วย `uv run atlas schema` และ `npm run gen:types` (CI ตรวจ drift ทั้งสองขั้น) · `SCHEMA_VERSION = "2.5.0"` — ทุกไฟล์มี `schema_version`; เว็บตรวจเฉพาะ **major = 2** (ต่างไป = แถบแจ้งเหตุผล) และ minor ที่เพิ่มขึ้นเป็นแบบเพิ่มอย่างเดียวเสมอ

| เวอร์ชัน | เพิ่มอะไร | ส่วน |
|---|---|---|
| 2.0 | manifest, overview, taxonomy, topics, topics/<id>, series, edges, keywords, latest | §6 |
| 2.1 | journals, journals/<id>, methods, diff, match; `CountItem.id` | §7 |
| 2.2 | institutions, institutions/<id>, regions, sdg, global, gaps; `Kpis.pct_international/pct_multi_institution/provinces`; `Overview.executive`; `Manifest.skipped_modules`; `Topic.sdg` | §8 |
| 2.3 | references, search/*, galaxy, kwtrends; `TopicDetail.cited_in_tci/glossary`; `Latest.feeds` | §9 |
| 2.4 | `JournalDetail.topic_years` | §10 |
| 2.5 | `ProvinceStat.topics` | §11 |

รอบข้อมูลหนึ่งรอบ = `output/data/<release>/` (เช่น `2026Q4/`) — JSON แบบ strict (ไม่มี NaN/Infinity; ทุก model `extra="forbid"`), เขียนแบบ compact UTF-8, สีเป็น token `cat-01…cat-12` ไม่ใช่ hex, รหัสหัวข้อ `T` + 6 หลัก, รหัสกลุ่ม `F<field>` (สาขา OpenAlex) หรือ `G<n>` (agglomerative/fallback), ไม่มีบทคัดย่อและไม่มีข้อมูลระดับบุคคล · export ซ้ำของรอบเดิมลบโฟลเดอร์แล้วเขียนใหม่ทั้งหมด

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `manifest.json` | `Manifest` | schema_version, release, generated_at, pipeline_version (git hash), config_hash (sha256[:16] ของ config ทุกส่วนยกเว้น path และชื่อรอบ — เก็บ `pipeline.seed`), definition_version, **ci_level** (ระดับของช่วง `*_lo/*_hi` ทุกตัว), as_of_year, trimmed_years, embedding_provider, embedding_model, taxonomy_version, **modules** (ตารางด้านล่าง), **skipped_modules** {โมดูล: เหตุผล}, files [{path, bytes, sha256}] (ทุกไฟล์ยกเว้น manifest เอง), previous_release, n_orgs_unverified, ingest_errors (null = ไม่มีบันทึก — ไม่ใช่ 0), labels {provider (`llm` \| `off`), llm, keywords, overrides, reused}, llm [{task, model, items, from_cache, generated, repaired, fallback, cost_usd = ยอดรวมของรอบข้อมูลนี้ทุกครั้งที่รัน (จาก journal), this_run_cost_usd = เฉพาะการรันล่าสุด}] |
| `overview.json` | `Overview` | release, previous_release, generated_at, definition_version, last_complete_year, **kpis** (`Kpis`: articles, assigned_articles, topics, groups, journals (นับ `journal_key`), institutions, pct_abstract_en, pct_doi, pct_keywords (เปอร์เซ็นต์ ทศนิยม 1 ตำแหน่ง) + P3), status_counts, corpus_by_year [{year, articles}] (= totals), corpus_forecast (พยากรณ์ยอดรวม), nowcast, lineage_events, retired_topics, data_quality {year_missing, unassigned_articles, completeness_method, text_quality {flag: จำนวน}}, **brief** (headline_th/en + bullets_th/en, source `llm` \| `template`), executive (§8) |
| `taxonomy.json` | `TaxonomyFile` | source (`openalex` \| `agglomerative`), version, holdout_accuracy_subfield/field, groups [{id, th, en, color, size, n_topics, x, y, r (ตำแหน่ง hub)}], subfields [{id, en, group, n_topics, size}] — สีผูกกับรหัสกลุ่ม ไม่ใช่ลำดับขนาด: สาขา OpenAlex ใช้ตารางคงที่ (`export_v2.FIELD_COLOR`; 12 สาขาที่พบบ่อยใน TCI ได้สีไม่ซ้ำกัน), กลุ่ม `G<n>` = `cat-(n mod 12 + 1)`; ถ้าสองกลุ่มในรอบเดียวกันได้สีเดียวกัน รหัสที่น้อยกว่าคงสีไว้ อีกกลุ่มเลื่อนไปสีว่างถัดไป (ตัดสินจากชุดรหัสเท่านั้น ไม่ใช่ขนาด) → กลุ่มเดิมสีเดิมทุกไตรมาส |
| `topics.json` | `TopicsFile` | `Topic`: id, group, th, en, description, keywords[], label_source (`llm` \| `keywords` \| `override` \| `reused`), size, x, y, r, status, score (emerging_score ทศนิยม 1 ตำแหน่ง), **metrics** (`TopicMetrics`: count_recent, share_recent, share_baseline, share_ratio, no_baseline, share_growth(_lo/_hi), acceleration, burst_frac, burst_years[], novelty, coherence, n_journals_R, n_orgs_R, new_journal_share, journal_hhi, journal_driven, orgs_unverified, low_data_reason), forecast (`TopicForecast`: model, mase, skill_vs_naive, show, years, mean, lo80, hi80, lo95, hi95 — อาร์เรย์ว่างเมื่อ `show` = false; ไม่มีแถว forecast = null), lineage {born, event, parents}, sdg (เลข SDG), subfield, subfield_en, cross_field, taxonomy_vote, nowcast {year, as_of_month, ytd, mean} |
| `topics/<id>.json` | `TopicDetail` | บทความตัวแทน `export.repr_articles` เรื่อง (MMR: article_id, title, title_en, year, journal, url ThaiJO, doi, gx/gy พิกัด galaxy), journals (`CountItem` ≤ `export.max_topic_journals`, นับตาม `journal_key`, `id` → `journals/<id>.json`), institutions (≤ `export.max_topic_orgs`; §12), keywords, neighbors (≤ `export.max_neighbors`), **narrative** {th, en, source} + P4 (§9) — สถาบันนับตาม `org_key` (พับวรรณยุกต์/ตัวพิมพ์เพื่อรวมคำสะกดต่างกัน) แต่ `institutions[].key` เป็น**ชื่อที่เขียนจริง**ที่พบบ่อยที่สุดของ key นั้น (ส่วนชื่อองค์กรของสังกัด เช่น "มหาวิทยาลัยเกษตรศาสตร์" / "Naresuan University" — ไม่ตัดวรรณยุกต์ ไม่แปลงตัวพิมพ์; ไม่มีชื่อคณะ/ตำแหน่ง); เมื่อมีโมดูลสถาบัน (P3) ใช้สถาบันแบบ canonical (รวมชื่อแปรผัน) และมี `id` → `institutions/<id>.json` |
| `series.json` | `SeriesFile` | years (= `06_meta.json → years`), corpus_total, topics {รหัส: ยอดรายปี} — ทุกอาร์เรย์ยาวเท่า years (validator ตรวจ) |
| `edges.json` | `EdgesFile` | edges [{s, t, w}] |
| `keywords.json` | `KeywordsFile` | `EmergingKeyword` ≤ `keywords.max_terms`: term, count_recent, share_ratio (null เมื่อ no_baseline), no_baseline, growth, growth_lo, n_active_years, n_orgs_R, n_journals_R, journal_driven, emerging, topic |
| `output/data/latest.json` | `Latest` | {release, path: "<release>/manifest.json", schema_version, generated_at, feeds (2.3)} — ชี้รอบใหม่สุดเท่านั้น (export/publish รอบเก่ากว่าไม่ย้าย; `atlas publish --set-latest` บังคับ) |

- `generated_at` ของทุกไฟล์ = `snapshot_at` (UTC) ของ work_dir จึง export ซ้ำได้ไฟล์เดิมทุกไบต์
- `metrics.share_ratio` เป็น **null** และ `no_baseline: true` เมื่อ `share_baseline` = 0 (เว็บแสดง "ใหม่ — ปี {B} ยังไม่มีงานเรื่องนี้") — เช่นเดียวกับ keyword
- `metrics.low_data_reason`: `few_articles` (count_recent < `emerging.min_articles_recent`) หรือ `not_estimable` (ประมาณอัตราโตไม่ได้) เมื่อ status = LOW_DATA (EMERGING_SPEC §6.1)
- กลุ่ม fallback (taxonomy.source = agglomerative): id 1000 + coarse, code `G<n>`, ชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" / "Unmapped group N"; กลุ่ม agglomerative ที่ไม่มีชื่อใช้ชื่อของหัวข้อที่ใหญ่ที่สุด

### 6.1 `manifest.modules`
ไฟล์ที่เว็บต้องมีเสมอ: `overview`, `taxonomy`, `topics`, `topic_detail`, `series`, `edges` (validate บังคับ overview/taxonomy/topics/series/edges ใน manifest); นอกนั้นเป็น optional — มีใน `modules` เมื่อไฟล์ถูกเขียน, ไม่มีพร้อมเหตุผลใน `skipped_modules` เมื่อ pipeline ข้ามโดยตั้งใจ, หรือไม่มีเลยเมื่อ step ไม่ได้รัน (หน้าเว็บอธิบายตัวเองผ่าน `ModuleFile`)

| module | ไฟล์ | เมื่อไหร่ |
|---|---|---|
| `keywords` | keywords.json | มี `07_keywords` |
| `journals`, `journal_detail` | journals.json, journals/<id>.json | ขั้น journals รันแล้ว |
| `institutions`, `institution_detail` | institutions.json, institutions/<id>.json | ขั้น institutions รัน (skipped: `institutions.enabled is false`) |
| `regions` · `sdg` · `global` · `gaps` | regions.json · sdg.json · global.json · gaps.json | ขั้นนั้นรัน (skipped: `institutions.enabled is false` / `sdg.enabled is false` / เหตุผลจาก `17_benchmark_meta.json` เช่น OpenAlex ใช้ไม่ได้) |
| `references` · `search` · `galaxy` · `kwtrends` | §9 | skipped พร้อมเหตุผลจาก meta ของ step |
| `methods` · `match` | methods.json · match.json | มี checkpoint `12_*` · `14_match.json` |
| `diff` | diff.json | มีรอบก่อนหน้าและหา snapshot ได้ (§7) |

### 6.2 `atlas publish` (`atlas/publish.py`)
1. **validate ก่อนเสมอ** (§6.3) — exit 2 ปฏิเสธเสมอ, exit 1 ปฏิเสธเว้นแต่ `--allow-warnings`
2. `--site <dir>` (เว็บที่ build แล้ว):
   - `<site>/data/<release>/` = สำเนาของ `output/data/<release>/` (publish ซ้ำแทนที่โฟลเดอร์นั้น)
   - รอบก่อนหน้าแบบลูกโซ่ (`previous_release` ของ `previous_release` …) ที่เว็บยังไม่มีถูกคัดลอกคืนจาก `output/data/` (ไม่แทนที่โฟลเดอร์ที่อยู่บนเว็บแล้ว; หาไม่พบ = เตือน)
   - `<site>/data/latest.json` ย้ายเฉพาะเมื่อรอบนี้ใหม่สุดบนเว็บ (ลำดับจาก `state/releases/index.json` ถ้ารู้ทุกชื่อ ไม่งั้นเรียงตามชื่อ) หรือ `--set-latest`; ไม่ย้าย = เตือน และ `atlas-offline.html` ไม่เปลี่ยน
   - **ลดขนาดรอบเก่า** (เฉพาะเมื่อ latest ย้าย): รอบที่เก่ากว่า `publish.keep_full_releases` (1) รอบใหม่สุด (เรียงตามชื่อ) เหลือเฉพาะ `manifest.json · overview.json · topics.json · taxonomy.json · diff.json` + โฟลเดอร์ `topics/` (ฟีดลิงก์ถึง); รอบที่เพิ่ง publish (ที่ latest ชี้) ไม่ถูกตัดเสมอ รวมตอนย้อนกลับด้วย `--set-latest`
   - **ฟีด Atom** เมื่อตั้ง `publish.site_url` (§9) → `latest.json.feeds = true`; ไม่ตั้ง = พิมพ์ว่าไม่มีฟีด
   - **`atlas-offline.html`** = `offline-template.html` ของ web build ที่ฝัง `{latest, files}` ใน `<script type="application/json" id="atlas-data">` (แทนข้อความด้วย Python; `</` และ `<!--` ถูก escape); `latest` ในไฟล์ไม่มี `feeds`; ไม่ใส่ไฟล์ใน `export.offline_exclude` (ดีฟอลต์ `[match.json, search, galaxy.json]`) และ `search`, `galaxy.json` ถูกตัดเสมอแม้ config เก่าไม่ระบุ; **งบขนาด** `export.offline_max_mb` (60) × 1,000,000 ไบต์ของ JSON: ไฟล์ระดับบนใส่ทั้งหมด แล้วใส่ไฟล์รายละเอียด `topics/` (ตามลำดับใน topics.json) → `journals/` → `institutions/` จนเต็ม (ที่เหลือพิมพ์จำนวน; หน้าที่ไม่มีไฟล์บอกผู้อ่านเอง); ไม่มี template = เตือนและข้าม
3. `--tarball` → `output/releases/atlas-data-<release>.tar.gz` (ทำซ้ำได้ไบต์เดิม: เรียงชื่อ, mtime 0, uid/gid 0, gzip ไม่มีเวลา) + `.sha256` + `.notes.md` และพิมพ์คำสั่ง `gh release create` ให้คนรันเอง

### 6.3 `atlas validate` (`atlas/validate.py`) — exit 0 สะอาด · 1 มีแต่คำเตือน · 2 มี error
1. **integrity:** manifest อ่านได้และ major ของ schema = 2; ทุกไฟล์ใน `files` มีอยู่ ขนาดและ sha256 ตรง (error); ไฟล์ JSON บนดิสก์ที่ manifest ไม่ระบุ = เตือน; ไฟล์ > `validation.max_file_bytes` (50 MB) = เตือน; ไฟล์หลัก (overview, taxonomy, topics, series, edges) ไม่อยู่ใน manifest = error
2. **schema:** ทุกไฟล์ผ่าน model ของตัวเอง (`contract.model_for`; ไฟล์ที่ไม่มี model = เตือน)
3. **ความสอดคล้อง:** รหัสหัวข้อไม่ซ้ำและมี `topics/<id>.json` ครบ; series/edges อ้างแต่หัวข้อที่มี; กลุ่มของทุกหัวข้ออยู่ใน taxonomy; `kpis.topics` = จำนวนหัวข้อ · P2: รหัสวารสารไม่ซ้ำ มีไฟล์ครบ, peers/ลิงก์วารสารของหัวข้อ/วารสารใน match ชี้วารสารที่มี, หัวข้อใน journals/methods/diff (รวม restructured, merged_into)/match เป็นหัวข้อของรอบนี้ และหัวข้อที่ retired ต้องไม่อยู่ใน topics.json · P3: รหัสสถาบันไม่ซ้ำ มีไฟล์ครบ, edges/partners/suggested/top ของจังหวัด/ลิงก์สถาบันของหัวข้อ/top ของ concentration ชี้สถาบันที่เผยแพร่, หัวข้อใน sdg/global/gaps มีอยู่, สาขาใน gaps อยู่ใน taxonomy · P4: `_check_research` (§12)
4. **ความเป็นส่วนตัว:** `privacy.scan_release` (§12) — ทุกข้อเป็น error
5. **LLM:** ชื่อหัวข้อที่ fallback เป็น keyword (เมื่อ provider = llm) และงาน LLM อื่นที่มี fallback = เตือน (ให้รัน `atlas llm` ใหม่)
6. **ความปลอดภัยของรอบ:** `manifest.release` ≠ ชื่อโฟลเดอร์ = error; ชื่อรอบต้องเป็นชื่อโฟลเดอร์ชั้นเดียว (`^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$` — `../x` ถูกปฏิเสธ; ค่าดีฟอลต์คือ `YYYYQn` ของวันที่รัน และลำดับรอบเรียงตาม `state/releases/index.json` หรือตามชื่อ จึงควรใช้ `YYYYQn` เสมอ); cluster ปฏิเสธการรันรอบที่มีรอบใหม่กว่าอยู่แล้วใน state
7. **diff กับรอบก่อน** (`--previous` หรือโฟลเดอร์ `manifest.previous_release` ข้าง ๆ; ไม่พบ = เตือนและข้าม): จำนวนหัวข้อเปลี่ยน > `max_topic_count_change` (0.25), รหัสเดิมเหลือ < `min_kept_ids` (0.9), หัวข้อเดิมเปลี่ยนสถานะ > `max_status_change_frac` (0.3), ขนาดเปลี่ยน ≥ `size_swing_ratio` (2) เท่าในหัวข้อ ≥ `size_swing_min_articles` (50) = เตือน; บทความทั้งหมดลด > `max_article_drop` (0.02) = **error**

## 7. P2 — รุ่นบรรณาธิการ (contract 2.1, เพิ่มอย่างเดียว)

ไฟล์ใหม่ทุกไฟล์เป็น optional และประกาศใน `manifest.modules` (`journals`, `journal_detail`, `methods`, `match`, และ `diff` ตั้งแต่รอบที่สองเป็นต้นไป); `CountItem.id` (ใหม่) ทำให้หน้าหัวข้อลิงก์ไปยังวารสารได้ ข้อมูลระดับบุคคลและข้อความบทคัดย่อ **ไม่** ถูกเผยแพร่ในไฟล์ใดเลย · หน้าต่าง: W = `journals.window_years` / `methods.window_years` (5) ปีสมบูรณ์ล่าสุด, R/B = หน้าต่าง emerging

### Checkpoint ใหม่ใน `work_dir` (ลบได้)

| ไฟล์ | step | เนื้อหา |
|---|---|---|
| `12_methods_articles` · `12_methods_topics` · `12_methods_notes` · `12_methods_meta.json` | `methods` | วิธีวิจัยรายบทความ (article_id, year, topic_id, methods, sample_size) · ต่อหัวข้อที่มี ≥ `methods.min_articles` (30) บทความในหน้าต่าง · บันทึกหัวข้อ (topic_id, th, en, source — เฉพาะ `methods.provider: llm`) · เวอร์ชัน lexicon, หน้าต่าง, สัดส่วนทั้งคลัง/รายปี, สถิติ LLM |
| `13_journals` · `13_journal_years` · `13_journal_topics` · `13_journal_drift` · `13_journal_shifts` · `13_journal_topic_years` · `13_journal_peers` · `13_journal_completeness` · `13_journal_methods` · `13_special_issue` · `13_journal_opportunities` · `13_journals_meta.json` | `journals` | ตัวตนวารสาร (+ทะเบียน), ความครบถ้วน D2, เจ้าของ/สัดส่วนในสถาบัน D3, ความหลากหลายสถาบัน, ผู้แต่งต่างประเทศ (สัดส่วน), drift D1, สัดส่วนหัวข้อรายปี (§10), เพื่อน D4, ช่องว่างฉบับพิเศษ D5, วิธีวิจัย D7 — อ่านแถวผู้แต่งที่ step นี้ (และ journal_metrics) เท่านั้น |
| `14_match.json` | `match` | ดัชนี trigram: gram, idf, น้ำหนักต่อหัวข้อ, สัดส่วนหัวข้อของแต่ละวารสาร |
| `state_dir/releases/<release>/snapshot.json` | `export` | สรุปย่อของรอบ (หัวข้อ: id → status, size, share_recent, score, ชื่อ + KPI + รายชื่อวารสาร) ที่รอบถัดไปใช้ทำ `diff.json`; รอบก่อน P2 ที่ไม่มี snapshot ใช้ `output/data/<prev>/` แทน (`previous_source: output`); หาไม่ได้ทั้งคู่ = ไม่มี diff.json |

### ไฟล์ที่เผยแพร่ (`data/<release>/`)

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `journals.json` | `JournalsFile` | `window`/`recent`/`baseline`, `min_articles`, `completeness_weights`, `inhouse_flag_share` (null = ไม่มีเครื่องหมาย; ทำเครื่องหมายได้เฉพาะวารสารที่ `owner_source` = registry), เกณฑ์ special issue (`special_issue_statuses`, `_max_hosts`, `_min_host_articles`), `drift_reference_years`; `journals[]` = `JournalSummary`; `special_issue[]` = `SpecialIssueTopic` (topic, hosts, top_host_share, articles_recent) |
| `journals/<id>.json` | `JournalDetail` | `years` (year, articles), `topics` (TopicShare), `drift` (DriftPoint: year, articles, distance = Jensen–Shannon; null = น้อยเกิน), `gained`/`lost` (TopicShift), `peers` (cosine ของสัดส่วนหัวข้อ), `completeness` (7 องค์ประกอบ: abstract_en, title_en, keywords_en, doi, references, refs_romanized, affiliations — key, rate, n), `methods`, `opportunities` (`in_scope` \| `adjacent`, journal_articles, hosts), `topic_years` (2.4: ดู §10) |
| `methods.json` | `MethodsFile` | `lexicon_version`, `window`, `articles`, `with_methods`, `monoculture_methods`, `monoculture_min_share`, `monoculture_share`, `min_articles`, `methods[]` (key/th/en), `corpus` + `by_year` (สัดส่วนวิธีต่อปี), `topics[]` = `TopicMethods` (articles, with_methods, coverage, สัดส่วนวิธี, ควอร์ไทล์ขนาดตัวอย่าง, `monoculture` + `monoculture_share`, `note` เมื่อใช้ LLM) |
| `diff.json` | `DiffFile` | `release`, `previous_release`, `previous_source` (`state` \| `output`), `kpis` (key, previous, current), `new_topics` (event new/split/merge + parents), `retired` (`merged_into` เฉพาะที่ lineage ระบุว่ารวมเข้า), `restructured` (หัวข้อที่คงรหัสผ่านการรวม/แยก), `status_changes`, `movers` (≥ `changes.min_share_delta`, ≤ `changes.movers`), `journals_compared`, `new_journals` |
| `match.json` | `MatchIndex` | `analyzer: char_wb3`, `fold: atlas-fold-1`, `docs`, `max_terms`, `grams` + `idf`, `topics[]` (terms, weights), `journals[]` (topics, shares), `min_similarity`, `fit_topics`, `min_query_chars` — ไม่มีข้อความบทความ; ไม่อยู่ใน HTML ออฟไลน์ |

`JournalSummary` (หนึ่งแถวต่อวารสาร): `id` (เช่น `so02.BECJournal` — ฟังก์ชันคงที่ของ `journal_key` `<server>:<OJS path>`; key ที่ไม่ใช่ ASCII-safe = `J` + 12 hex ของ sha1), `key`, `path`, `name_th`/`name_en`/`issn`/`eissn`/`tci_tier`/`tci_field`/`publisher`/`url` (จากทะเบียน, ว่างได้), `in_registry`, `articles`, `articles_window`, `articles_recent`, `first_year`, `last_year`, `active` (มีบทความใน R), `low_data` (น้อยกว่า `journals.min_articles` (20) ในหน้าต่าง → ทุกอัตราเป็น null), `group`, `completeness` (0–100, **ไม่ใช่การประเมินอย่างเป็นทางการของ TCI**), `owner` + `owner_source` (`registry` \| `inferred`; เว็บแสดง "อนุมาน / inferred") + `owner_matched`, `inhouse_share`, `n_orgs`, `effective_orgs`, `foreign_share`, `affiliation_coverage`, `methods_coverage`.

PDPA: ตัวเลขของวารสารเป็นยอดรวมเท่านั้น — ไม่มีชื่อบุคคล แถวต่อผู้แต่ง หรืออันดับบุคคล; "ผู้แต่งต่างประเทศ" = สัดส่วนบทความที่มีสังกัด ≥ 1 แห่งนอกประเทศไทย

## 8. P3 — รุ่นผู้บริหาร (contract 2.2, เพิ่มอย่างเดียว)

ไฟล์ใหม่ทุกไฟล์ optional และประกาศใน `manifest.modules` (`institutions`, `institution_detail`, `regions`, `sdg`, `global`, `gaps`); โมดูลที่ข้ามพร้อมเหตุผลอยู่ใน `manifest.skipped_modules` (เช่น `{"global": "OpenAlex unavailable: …"}`, `{"institutions": "institutions.enabled is false"}`). หน้าต่าง: W = `institutions.window_years` (5) ปีสมบูรณ์ล่าสุด, R = หน้าต่าง emerging. PDPA: เผยแพร่เฉพาะยอดรวมระดับสถาบัน — ไม่มีชื่อบุคคล แถวต่อผู้แต่ง หรือบทคัดย่อ; สถาบันที่มีบทความในหน้าต่างน้อยกว่า `institutions.min_articles` (5) ถูกนับในยอดรวมแต่ไม่อยู่ในไฟล์ใด (รายการ, หน้า, คู่ความร่วมมือ, สถาบันหลักของจังหวัด, `top` ของ concentration, ข้อเสนอ R6)

### Checkpoint ใหม่ใน `work_dir` (ลบได้)

| ไฟล์ | step | เนื้อหา |
|---|---|---|
| `15_article_institutions` · `15_institutions` · `15_inst_years` · `15_inst_topics` · `15_inst_pairs` · `15_inst_countries` · `15_inst_suggest` · `15_provinces` · `15_regions` · `15_province_topics` · `15_institutions_meta.json` | `institutions` | คู่ (บทความ, สถาบัน) ทุกปี · หนึ่งแถวต่อสถาบัน (inst_key, code, ชื่อ, type, province, country, source, ror, articles/articles_total/articles_recent, intl_share, partners, topics, published) · บทความรายปี · หัวข้อ · คู่ความร่วมมือ (≥ `network_min_articles`) · ประเทศคู่ความร่วมมือ · ข้อเสนอ R6 (cosine ≥ `suggest_min_similarity` และไม่มีบทความร่วมกัน) · บทความรายจังหวัด/ภาค (บทความหนึ่งนับทุกจังหวัดของผู้แต่ง) · หัวข้อรายจังหวัด (§11) · หน้าต่างปี, coverage, KPI (`institutions_total` = สถาบันที่มีชื่อและมีบทความในหน้าต่าง), population |
| `16_topic_goals` · `16_sdg_meta.json` | `sdg` | topic_id, framework, goal_id, score (สูงสุด `sdg.max_goals_per_topic` ต่อกรอบ) · method (embedding \| lexical), version, กรอบและเป้าหมาย |
| `17_benchmark` · `17_benchmark_meta.json` | `benchmark` | ต่อ OpenAlex subfield: world_R/B, country_R/B, tci_R, world_ratio, activity_index, country_share, opportunity · `{"skipped": เหตุผล}` เมื่อข้าม |
| `18_gap_few_institutions` · `18_gap_bridges` · `18_gap_world` · `18_concentration` · `18_gaps_meta.json` | `gaps` | หัวข้อสถานะ `gaps.statuses` ที่สถาบันทำน้อย · คู่หัวข้อเพื่อนบ้านที่สถาบันซ้อนกันน้อย · โอกาสจาก benchmark + หัวข้อที่ตรงกัน · HHI และ top share ต่อหัวข้อ/สาขา (scope, unit, kind, articles, hhi, top_share, top_key, concentrated) |
| `state_dir/ror/<dump>.<country>.json` | `institutions` | แคชข้อมูล ROR เฉพาะประเทศ (สร้างจาก `institutions.ror_path` ครั้งแรกครั้งเดียว) |

### ไฟล์ที่เผยแพร่ (`data/<release>/`)

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `institutions.json` | `InstitutionsFile` | `window`/`recent`, `min_articles`, `network_min_articles`, `articles_with_org`, `pct_international`, `pct_multi_institution` (เศษส่วน), `sources` (alias/ror/name); `institutions[]` = `InstitutionSummary` (id = alias inst_id \| `ror-<ROR id>` \| `o<10 hex ของ sha1(org key)>`, name_th/en, type, province, country, source, ror, articles, articles_total, articles_recent, intl_share, partners, topics, group); `edges[]` = `CollabEdge` (a, b, articles); `countries[]` = `CountryCount`; `province_names[]` |
| `institutions/<id>.json` | `InstitutionDetail` | `years`, `topics` (TopicShare), `partners` (Partner), `countries`, `suggested` (Suggestion: id, similarity, topics — R6) |
| `regions.json` | `RegionsFile` | `window`, `articles_with_org`, `articles_located`, `coverage`, `population_year`; `provinces[]` = `ProvinceStat` (code, ชื่อ, region, articles, articles_recent, share, institutions, per_100k (null เมื่อไม่มีประชากร), top[], topics (2.5)); `regions[]` (key, articles, share) — ส่วนแบ่งรวมกันเกิน 1 ได้ (บทความนับเต็มทุกจังหวัดของผู้แต่ง) |
| `sdg.json` | `SdgFile` | `method`, `version`, `frameworks[]` (sdg, bcg, ววน., หมุดหมายแผนฯ 13), `goals[]` = `GoalStat` (id, framework, number, th/en, topics, articles_recent, share_recent, share_ratio); `Topic.sdg` ในรายหัวข้อ = เลข SDG (เฉพาะกรอบ `sdg`) |
| `global.json` | `GlobalFile` | `source` (เช่น openalex@วันที่), `country`, `recent`, `baseline`, เกณฑ์ (`min_world_works`, `min_world_ratio`, `max_activity_index`), `subfields[]` = `SubfieldBench` (world/country recent/baseline, tci_recent, world_ratio, activity_index, country_share, opportunity, topics) |
| `gaps.json` | `GapsFile` | เกณฑ์ที่ใช้ (recent, statuses, max_institutions, bridge_min_similarity, bridge_max_jaccard, min_articles, max_top_share, max_hhi), `few_institutions[]`, `bridges[]` (a, b, similarity, shared, jaccard), `world[]`, `concentration[]` = `Concentration` (scope, id, kind, articles, hhi, top_share, top, top_name, concentrated) |

หน่วย KPI: `Kpis.pct_international` / `pct_multi_institution` เป็น **เปอร์เซ็นต์** (เหมือน `pct_abstract_en`), `provinces` เป็นจำนวนจังหวัดที่มีบทความ; สัดส่วนในไฟล์โมดูล (`intl_share`, `share`, `coverage`, `top_share`) เป็น **เศษส่วน** 0–1. `Overview.executive` = `bullets_th` / `bullets_en` / `source: "template"` — ประโยคแม่แบบสร้างตอน export จากไฟล์ข้างต้น (ไม่มี LLM; ตัวเลขทุกตัวมาจากไฟล์)

## 9. P4 — รุ่นนักวิจัย (contract 2.3, เพิ่มอย่างเดียว)

ไฟล์ใหม่ทุกไฟล์ optional และประกาศใน `manifest.modules` (`references`, `search`, `galaxy`, `kwtrends`); โมดูลที่ข้ามพร้อมเหตุผลอยู่ใน `manifest.skipped_modules` (เช่น `{"references": "reference coverage 12.3% of 4,210 articles 2015–2025 (< references.min_coverage 50.0%)"}`, `{"galaxy": "layout.galaxy is false"}`). ลำดับ step: `… gaps → references → search → kwtrends → export`. PDPA: ข้อมูลบทความที่เผยแพร่ = id, ชื่อเรื่อง TH/EN, ปี, ชื่อวารสาร, หัวข้อ, DOI, ลิงก์ ThaiJO, จำนวน "ถูกอ้างใน TCI" เท่านั้น — **ไม่มีชื่อผู้แต่งและไม่มีบทคัดย่อ** ในไฟล์ใดเลย (ดัชนีค้นหาสร้างจากชื่อเรื่อง + คำสำคัญของผู้แต่ง; ไม่มีข้อความรายการอ้างอิง); `test_release` สแกนไฟล์ใหม่ทุกไฟล์หาชื่อผู้แต่ง/ข้อความบทคัดย่อของไฟล์จริง 11 ไฟล์

### Checkpoint ใหม่ใน `work_dir` (ลบได้)

| ไฟล์ | step | เนื้อหา |
|---|---|---|
| `19_ref_matches` · `19_article_cites` · `19_journal_refs` · `19_topic_flows` · `19_refs_meta.json` | `references` | citing_id, cited_id, method (`doi` \| `title`) · article_id, cited_in_tci (จำนวนบทความในคลังที่อ้างถึง นับครั้งเดียวต่อบทความที่อ้าง; > 0 เท่านั้น) · ต่อวารสารที่มีบทความที่มีรายการอ้างอิง ≥ `references.min_journal_articles`: journal_key, journal, articles, articles_with_refs, refs_median, age_median, share_recent, share_thai, share_doi · หัวข้อที่อ้าง → หัวข้อที่ถูกอ้าง, n · window (ช่วงที่วิเคราะห์), coverage, counts, methods, published/skipped, internal/internal_reason |
| `20_docs` · `20_postings` · `20_galaxy_points` · `20_search_meta.json` | `search` | ordinal, article_id, title_th/en, year, journal_index, topic_id (−1 = ยังไม่จัดหมวด), doi, url (ไม่มีผู้แต่ง ไม่มีบทคัดย่อ) · คู่ (token, ordinal) ไม่ซ้ำ เรียงแล้ว · ordinal, x, y (0…65535 บน view box ของแผนที่, −1 = ไม่มีพิกัด), topic_id, year · n_docs, window, journals, years, search {published, skipped, tokenizer_version, …}, galaxy {published, skipped, bounds, placed} |
| `21_kw_years` · `21_glossary` · `21_kwtrends_meta.json` | `kwtrends` | lang, key, term, rank, year, count (หนึ่งแถวต่อคำ × ปีของอนุกรมเวลา) · scope (`topic` \| `all`), topic_id (−1 = ทั้งคลัง), rank, th_key, en_key, th, en, n · published, skipped, years, totals, totals_th, totals_en, candidates, kept, paired_articles, pairs |
| `16_topic_goal_scores` | `sdg` | (เฉพาะ `sdg.method` embedding) cosine ทุกคู่หัวข้อ × เป้าหมาย คอลัมน์เดียวกับ `16_topic_goals` — อ่านโดย `atlas sdg-scores` เท่านั้น ไม่เผยแพร่ |

**ลำดับบทความ (doc ordinal):** หนึ่ง ordinal ต่อบทความที่เผยแพร่ = ตำแหน่งใน `01_articles` เรียงตาม `article_id` เฉพาะบทความที่มีปีอยู่ในช่วงที่วิเคราะห์ (`atlas.checkpoints.analysed_window` = ปีของอนุกรมเวลา + ปีล่าสุดที่ตัดออก) และมีชื่อเรื่อง TH หรือ EN — ไฟล์ค้นหาและ `galaxy.json` ใช้ ordinal เดียวกัน (`atlas.search_index.doc_order`)

**การตัดคำ (tokenizer_version 1):** NFC, ตัวพิมพ์เล็ก, เลขไทย → 0–9, แบ่งเป็นช่วงอักษรไทย/ช่วงอักษรอื่น; ช่วงไทยตัดด้วย pythainlp `newmm`; เก็บ token ≥ 2 code point ที่ไม่อยู่ใน stopword (ตัวเลขล้วนเก็บเฉพาะ 4 หลัก = ปี), ยาว ≤ `search.max_token_chars`, df ≥ `search.min_df`. ฝั่งค้น (`query_tokens` ใน Python = `web/src/lib/searchTokens.ts`) ไม่ใช้ pythainlp: ช่วงไทยจับคู่แบบยาวที่สุดก่อนกับ vocab, คำที่ไม่พบรายงานเป็น `unknown` — ทั้งสองฝั่งตรึงด้วย `pipeline/tests/fixtures/search_parity.json` (สร้างใหม่ด้วย `pipeline/scripts/make_search_parity.py`)

### ไฟล์ที่เผยแพร่ (`data/<release>/`)

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `references.json` | `ReferencesFile` | (เผยแพร่เมื่อ coverage ≥ `references.min_coverage`) `window`, `articles`, `articles_with_refs`, `coverage`, `refs_counted`, เกณฑ์ (`min_coverage`, `min_journal_articles`, `recent_years`); `journals[]` = `JournalRefs` (journal, id → `journals/<id>.json`, articles, articles_with_refs, refs_median, age_median, share_recent, share_thai, share_doi); `internal` = `InternalCitations` (matches, citing/cited_articles, share_doi/share_title, min_flow, `topics[]` received/given, `flows[]` source→target ≥ `min_flow`, `top_articles[]` = `CitedArticle` ไม่มีผู้แต่ง) หรือ null + `internal_reason` เมื่อจับคู่ได้ < `references.min_internal_matches` |
| `search/meta.json` | `SearchMeta` | tokenizer_version, n_docs, n_tokens, n_postings, index_shards, docs_per_shard, doc_shards, max_token_chars, max_results, min_df, fields (title_th, title_en, keywords_th, keywords_en), stopwords, journals (รายชื่อ — แถว doc อ้างด้วย index), years |
| `search/vocab.json` | `SearchVocab` | `tokens` (เรียงตาม code point) + `df` ต่อ token |
| `search/idx-<NNN>.json` | `SearchIndexShard` | `shard`, `postings`: token → ordinal เรียงไม่ซ้ำ เข้ารหัส delta (ค่าแรกเป็นค่าจริง ต่อไปเป็นผลต่าง); token อยู่ shard `fnv1a32(token) % index_shards` (FNV-1a 32 บิตบนไบต์ UTF-8) — เขียนครบทุก shard แม้ว่าง |
| `search/docs-<NNN>.json` | `SearchDocShard` | `shard`, `start` + `docs[]` = `[article_id, title_th, title_en, year, journal_index, topic id \| null, doi \| null, ThaiJO url \| null, cited_in_tci]` ของ ordinal `start …` (shard = ordinal // docs_per_shard) |
| `galaxy.json` | `GalaxyFile` | แบบคอลัมน์ ตรงกับ ordinal: `n` (= n_docs), `scale` (65535), `bounds` (x0, y0, x1, y1 = view box ของแผนที่หัวข้อ), `topics` (รหัสหัวข้อ), `x`/`y` (−1 = ไม่มีพิกัด), `t` (index ใน topics, −1 = ยังไม่จัดหมวด), `yr` — ข้ามเมื่อ `layout.galaxy: false` หรือไม่มี `09_galaxy` |
| `kwtrends.json` | `KwTrendsFile` | `years` (ปีของอนุกรมเวลา — ไม่รวมปีล่าสุดที่ตัดออก), `totals` (= `series.json` corpus_total), `totals_th`/`totals_en` (บทความที่มีคำสำคัญไทย/อังกฤษ ≥ 1), เกณฑ์ (`min_count`, `max_keywords`, `glossary_min_pairs`); `keywords[]` = `KeywordTrend` (term, lang, n, counts ต่อปี) — สัดส่วน = counts ÷ totals; `glossary[]` = `GlossaryItem` (th, en, n) ทั้งคลัง สูงสุด `kwtrends.glossary_max` |
| `topics/<id>.json` (เพิ่มฟิลด์) | `TopicDetail` | `cited_in_tci` (จำนวนครั้งที่บทความของหัวข้อถูกบทความอื่นในคลังอ้าง; null = ไม่เผยแพร่ส่วน internal), `glossary` (คู่คำไทย↔อังกฤษเด่นของหัวข้อ สูงสุด `kwtrends.glossary_per_topic`; **null = โมดูลไม่ถูกเผยแพร่, [] = ไม่พบคู่คำ**) |
| `latest.json` (เพิ่มฟิลด์) | `Latest` | `feeds: true` เมื่อ `atlas publish --site` เขียนฟีด Atom (ต้องตั้ง `publish.site_url`) — ไม่อยู่ใน latest ที่ฝังใน HTML ออฟไลน์ |

`search/` และ `galaxy.json` ไม่อยู่ใน HTML ออฟไลน์ (`export.offline_exclude: [match.json, search, galaxy.json]` และ publish ตัดสองตัวหลังเสมอ) — หน้า `/search` และ `/galaxy` ของฉบับออฟไลน์อธิบายตัวเองผ่าน `ModuleFile`

### ฟีด Atom (เขียนโดย `atlas publish --site` เท่านั้น ไม่ใช่ส่วนของรอบข้อมูล)

| ไฟล์ | เนื้อหา |
|---|---|
| `<site>/data/feeds/releases.xml` | หนึ่ง entry ต่อรอบที่อยู่บนเว็บ ใหม่สุดก่อน (≤ `publish.feed_max_entries`, 12): title = รอบ, summary = headline ของ overview (TH, EN) + สิ่งที่เปลี่ยน (ใหม่/หายไป/เปลี่ยนสถานะ จาก `diff.json` เมื่อมี), ลิงก์ `<site_url>#/topics` |
| `<site>/data/feeds/topics/<id>.xml` | หนึ่งฟีดต่อหัวข้อของรอบใหม่สุด; entry = รอบที่มีหัวข้อนั้น (ชื่อ, ชื่อสถานะไทย/อังกฤษ, บทความในช่วง R เขียนเป็นปี, อัตราโตของสัดส่วน), ลิงก์ `<site_url>#/topics/<id>`; ฟีดของหัวข้อที่ไม่อยู่ในรอบใหม่สุดถูกลบ |

สร้างจากไฟล์ที่อยู่บนเว็บเท่านั้น (`manifest.json`, `overview.json`, `diff.json`, `topics.json` ของแต่ละรอบ — ไฟล์ที่การลดขนาดรอบเก่าเก็บไว้) → รันซ้ำได้ไบต์เดิม; `<updated>` = `generated_at` ของ manifest; XML escape เอง (`xml.sax.saxutils.escape`) และตัดอักขระควบคุมที่ XML 1.0 ไม่รับ

## 10. สัดส่วนหัวข้อรายปีของวารสาร (contract 2.4, เพิ่มอย่างเดียว)

`JournalDetail.topic_years` (`JournalTopicYears` หรือ **null = ไม่เผยแพร่**: วารสารข้อมูลน้อย (< `journals.min_articles` ในหน้าต่างของโมดูล), `journals.year_mix_topics: 0`, หรือรอบที่ออกก่อน 2.4)

| ฟิลด์ | ความหมาย |
|---|---|
| `years` | ทุกปีในหน้าต่างของโมดูล (`journals.window_years`, เช่น 2020–2024) |
| `articles` | บทความของวารสารที่เข้าหัวข้อ ต่อปี |
| `min_articles` | = `journals.year_mix_min_articles` (10) — ปีที่ `articles` น้อยกว่านี้มีสัดส่วนเป็น null ทุกเส้น (ไม่ใช่ศูนย์) |
| `topics[]` | `JournalTopicLine` = `topic` + `shares` (ต่อปี) ของ `journals.year_mix_topics` (0–4, ดีฟอลต์ 4) หัวข้อที่ใหญ่ที่สุดของวารสารในหน้าต่าง (มากไปน้อย, เสมอกันเรียงตาม id) |
| `other` | สัดส่วนของหัวข้ออื่นทั้งหมดรวมกัน ต่อปี — ปีที่มีค่า: `sum(topics[].shares[k]) + other[k] = 1` |

ทุกอาร์เรย์ยาวเท่า `years` (validator ตรวจ). Checkpoint: `13_journal_topic_years` (journal_key, year, topic_id (-1 = อื่น ๆ), articles, share) จาก `journal_topics.topic_years`. เว็บ: หน้า `/journals/:id` ส่วน "ตีพิมพ์เรื่องอะไรบ้าง" แสดงเป็น small multiples (ช่องละหัวข้อ แกนตั้งเดียวกัน) + แท็บตาราง (ปี × หัวข้อ + เรื่องอื่น) + ประโยคตัวอย่าง และบอกปีที่เว้นว่างใต้กราฟ

## 11. หัวข้อรายจังหวัด (contract 2.5, เพิ่มอย่างเดียว)

`ProvinceStat.topics` (ใน `regions.json`) = `TopicShare[]` ของ `institutions.province_topics` (5) หัวข้อที่ใหญ่ที่สุดของจังหวัดในหน้าต่างของโมดูลสถาบัน (มากไปน้อย, เสมอกันเรียงตาม id; `share` = สัดส่วนของบทความในจังหวัดที่จัดเข้าหัวข้อได้; บทความนับครั้งเดียวต่อจังหวัดของผู้เขียน) — `[]` เมื่อไม่มีหรือรอบเก่า. Checkpoint `15_province_topics` (province, topic_id, count, share) จาก `institutions.province_topics()`. เว็บ: `/province` (ทุกจังหวัดแยกตามภาค) และ `/province/:code` ("งานวิจัยในจังหวัดของฉัน")

## 12. กติกาความถูกต้องและความเป็นส่วนตัวที่ pipeline บังคับ (หลังรีวิวก่อนรันคลังจริง 500K)

- **ชื่อสถาบันที่เผยแพร่:** `atlas/orgs.py` ตัดอีเมล เว็บ เบอร์โทร (เฉพาะเมื่อป้าย tel/โทร มีตัวเลขตามหลัง — "Tel Aviv", "สถานีโทรทัศน์" ไม่ถูกตัด) รหัสไปรษณีย์ เลขที่บ้าน หมู่/ซอย ออกจากสังกัดก่อนสร้างทั้งคีย์และชื่อ ("เขต 9" ของเขตสุขภาพ/เขตพื้นที่ไม่ใช่ที่อยู่ จึงอยู่ในชื่อ) และเผยแพร่ชื่อที่ "มีคำบอกองค์กร" เท่านั้น (`is_org_name`: มหาวิทยาลัย สถาบัน โรงพยาบาล กรม สำนักงาน University Institute … ยาว ≤ 120 ตัวอักษร ≤ 14 คำ ไม่มี `@`) สังกัดที่ไม่ผ่าน (ชื่อคนเดี่ยว ที่อยู่ "นักวิชาการอิสระ") ถูกนับในยอดรวมแต่ไม่มีชื่อ ไม่ถูกแสดง ลิงก์ หรือจับคู่ในเครือข่าย
- **สถาบันในหน้าหัวข้อ:** แสดงเฉพาะสถาบันที่เผยแพร่ (≥ `institutions.min_articles` บทความในหน้าต่างของโมดูลสถาบันและมีชื่อ) — ไม่มีรายการสำรองแบบไม่จำกัดเกณฑ์อีกแล้ว (เมื่อปิด `institutions.enabled` ใช้เกณฑ์ `min_articles` เดียวกันนับบทความทั้งคลังต่อ org_key)
- **`kpis.institutions`** = สถาบันที่มีชื่อและมีบทความในหน้าต่างของโมดูลสถาบัน (`15_institutions_meta.json → institutions_total`; ไม่ใช่ทุกการสะกดตลอดทุกปี) — ปรับตารางชื่อสถาบันแล้วตัวเลขเปลี่ยนน้อยลงเมื่อเทียบรอบก่อน; `kpis.journals` นับ `journal_key` ไม่ใช่ชื่อ
- **ด่านความเป็นส่วนตัว (`atlas/privacy.py`, `scan_release`):** `atlas validate` / `atlas publish` สแกนรอบที่จะเผยแพร่ (ทุกข้อเป็น error):
  1. อีเมล หรือ ORCID iD (`NNNN-NNNN-NNNN-NNNX`) ในไฟล์ `.json` / `.xml` / `.html` ใด ๆ ของโฟลเดอร์รอบ
  2. ชื่อ-นามสกุลผู้แต่ง (≥ 2 คำ และ ≥ 6 ตัวอักษรเมื่อพับแล้ว; อ่านจาก `work/01_authors` คอลัมน์ name/name_en เฉพาะตอนสแกน ตัดคำนำหน้าอย่าง ผศ.ดร./Asst. Prof. ออกก่อน และไม่นับ "ชื่อ" ที่มีคำบอกองค์กร) ปรากฏเป็นคำติดกัน 2–4 คำในสตริงชื่อองค์กร: ทุกสตริงใน `institutions.json` และ `institutions/*.json`, ฟิลด์ `owner`/`publisher` ใน `journals.json` และ `journals/*.json`, รายการ `institutions` ใน `topics/*.json` — ข้อความ error แสดงสตริงสังกัด ไม่แสดงชื่อคน (สูงสุด 10 รายการ + จำนวนที่เหลือ); ข้ามเมื่อไม่มี `01_authors`
  - ยกเว้น: ชื่อสถาบันจากตารางชื่อสถาบันที่คัดเอง/ROR (`source` = alias/ror), ผู้จัดพิมพ์จากทะเบียนวารสาร และสตริงใน `validation.privacy_allow` ที่คนตรวจแล้ว (ใส่ตามตัวอักษรที่ error แสดง)
- **ด่านตรวจข้ามไฟล์ของ P4 (`validate._check_research`):** `doc_shards` = ⌈`n_docs` ÷ `docs_per_shard`⌉, ครบทุก doc shard และแต่ละ shard เริ่มที่ `shard × docs_per_shard`, จำนวนแถวรวม = `search/meta.json.n_docs`, ครบทุก index shard, จำนวน token ใน `vocab.json` = `n_tokens`, `galaxy.n` = `n_docs`, หัวข้อในแถวบทความและ `galaxy.topics` มีอยู่ใน `topics.json` (ทั้งหมดเป็น error) · `vocab.json` ใหญ่เกิน 8 MB = คำเตือน (พิจารณา `search.min_df: 2`)
- **ingest:** ตัดซ้ำด้วยชื่อเรื่อง**ทั้งชื่อ** + ปี (ชื่อยาวที่ต่างกันตอนท้าย เช่น "…ปีที่ 1" / "…ปีที่ 4" ไม่ใช่เรื่องเดียวกัน; DOI ต่างกันทั้งคู่ = ไม่ซ้ำ; ชื่อสั้น < 40 ตัวอักษรที่คนละวารสารไม่ซ้ำ); เพดานไฟล์ผิด (`max_error_ratio`) ตรวจ**ก่อน**เขียน checkpoint; จำนวนที่ตัดทิ้งทุกเหตุผลอยู่ใน `work/01_ingest_meta.json` และบรรทัดสรุป; รหัส `file:` ของ md ที่ไม่มี URL มาจากโฟลเดอร์+ชื่อไฟล์ (รายละเอียด §1.2)
- **วารสาร = `journal_key`:** series, emerging, keywords, รายการวารสารของหัวข้อ และ KPI นับวารสารด้วยรหัส ไม่ใช่ชื่อที่แสดง (ชื่อไทย/อังกฤษของวารสารเดียวกันไม่ทำให้นับสองฉบับหรือเป็น "วารสารใหม่")
- **org_key:** สังกัดภาษาไทยที่เป็นชื่อเครือข่าย ("มหาวิทยาลัยราชภัฏ" / "…ราชมงคล" / "วิทยาลัยพยาบาลบรมราชชนนี" / "…สิรินธร") ใช้คำถัดไป (วิทยาเขต) ต่อท้ายคีย์ (ยกเว้นคำถัดไปเป็นคำนำหน้าชื่อคน ตัวเลข หรือเครื่องหมาย) — เปลี่ยนค่า `n_orgs_R` ที่ใช้ตัดสินความกว้าง (นิยามและเกณฑ์ไม่เปลี่ยน — EMERGING_SPEC §3.0)
- **จังหวัดจากชื่อ:** อ่าน "จังหวัด…" / "จ.…" ที่ระบุชัดก่อนชื่อจังหวัดหลังคำ ราชภัฏ / มหาวิทยาลัย / โรงพยาบาล / วิทยาลัยพยาบาลบรมราชชนนี; ไม่ใช้ตัว "จ" เดี่ยวเป็นคำนำ; จังหวัดแรกที่พบชนะ และอ่านภาษาไทยก่อนอังกฤษ; สังกัดภาษาไทยที่ลงท้ายด้วยชื่อประเทศ (ไม่มี "ประเทศ") ถือเป็นต่างประเทศเมื่อเป็นชื่อประเทศที่ไม่กำกวม
- **เว็บไซต์โตช้าลง:** `publish.keep_full_releases` (ดีฟอลต์ 1) — รอบเก่าบนเว็บเก็บเฉพาะ `manifest · overview · topics · taxonomy · diff` + โฟลเดอร์ `topics/` (ฟีดลิงก์ถึง) และไม่ตัดรอบที่ `latest.json` ชี้อยู่ (รวมตอนย้อนกลับด้วย `--set-latest`); `export.offline_max_mb` (ดีฟอลต์ 60) — `atlas-offline.html` ใส่ไฟล์รายละเอียดหัวข้อ → วารสาร → สถาบันจนเต็มเพดาน (§6.2)
- **คลัสเตอร์:** `clustering.hdbscan_backend` ดีฟอลต์ `fast` (ต้อง `uv sync --extra fast`; sklearn ช้าแบบกำลังสองที่ 500K) — เปลี่ยนกลางทางทำให้กลุ่มต่างไป
