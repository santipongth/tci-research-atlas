# DATA_SPEC — สเปกข้อมูลเข้า/ออก

## 0. Input ที่แนะนำ: คลังรูปแบบ 1.0 (`input.format: corpus_jsonl`)

- **รูปแบบ:** JSON Lines หนึ่งบรรทัดต่อบทความ อยู่ใน `<คลัง>/articles/*.jsonl` หรือ `*.jsonl.gz` พร้อม `<คลัง>/journals.csv`
- **คู่มือสำหรับทีมข้อมูล:** `docs/corpus/README.md`
- **ตัวอย่าง:** `docs/corpus/example/`
- **schema:** `docs/corpus/corpus.schema.json` สร้างจาก `pipeline/atlas/schema/corpus.py` ด้วย `atlas corpus schema` (test ตรวจ drift)
- **ตัวอ่าน:** `atlas/sources/corpus_jsonl.py`
  - ตรวจทุกบรรทัดกับ model แล้วแปลงเป็น record แบบเดียวกับ `parse_markdown` ทุก step หลัง ingest จึงไม่ต้องแก้
  - บรรทัดที่ผิดบันทึกเป็น `01_ingest_errors` ในรูป `ไฟล์:บรรทัด` และใช้เพดาน `input.max_error_ratio` เดิม
  - `input.exclude_article_types` ตัดประเภทที่ไม่ใช่ผลงานวิจัยออก
- **รหัสบทความ:**
  - ใช้ `id` ที่ทีมใส่มาก่อน
  - ไม่มี → ถ้ามี URL ของ ThaiJO ใช้ `<server>:<journal>:<เลข>` (ตรงกับคลัง .md)
  - ไม่มี URL → ใช้ `doi:<doi>`
  - ไม่มี DOI → ใช้ `tci:<sha1(journal_key|ชื่อเรื่อง|ปี)[:16]>`
- **คอลัมน์ใหม่ใน checkpoint:** ทางอื่นเป็นค่าว่าง
  - `01_articles`: `journal_key`, `article_type`, `language`, `issn`, `eissn`, `volume`, `issue`
  - `01_authors`: `orcid`, `ror`, `country`, `province` และ `affiliation_index` (หนึ่งแถวต่อผู้แต่งต่อสังกัด)
  - `registry.journal_keys` ใช้ `journal_key` ที่ทีมใส่มาก่อน
  - `institutions_ref.Resolver` ใช้ `ror` / `country` / `province` เป็นค่าบอกใบ้ แต่ไม่ทับ alias
- **ย้ายคลังเดิม:** `atlas corpus convert <โฟลเดอร์ .md> --out <โฟลเดอร์>` ได้ตาราง ingest เท่าเดิม (test parity) และรหัสบทความเดิม

## 1. Input: ThaiJO Markdown (ค่าดีฟอลต์ `input.format: thaijo_md`)
หนึ่งไฟล์ .md ต่อบทความ (ตัวอย่างจริงใน `pipeline/tests/fixtures/thaijo_md/`):
| ส่วน | รูปแบบ | ที่ pipeline ทำ |
|---|---|---|
| `# ชื่อเรื่อง` | ไทย, อังกฤษ, `TH [EN]` หรือ `EN (TH)` | แยก title_th / title_en (วงเล็บสั้นอย่าง `(TQA)` ไม่ถูกแยก) |
| `**Journal:**` | OJS path เช่น `BECJournal` | journal_name (ชื่อเต็ม/ISSN มาจาก registry ใน P2) |
| `**Published:**` | YYYY-MM-DD; `1970-01-01` = วันที่หาย | ปี: Published → ปีใน DOI → median ของ issue → ว่าง |
| `**Article URL:**` | `https://so02.tci-thaijo.org/index.php/<journal>/article/view/<id>` | article_id = `so02:<journal>:<id>` (ไม่มี URL → `file:<sha1 ชื่อไฟล์>`) |
| `**Authors:**` | `- ชื่อ [EN name] (สังกัดไทย (สังกัด EN))` + คำนำหน้าวิชาการ | ชื่อ, สังกัด TH/EN, role, is_student, org_key |
| `**Keywords:**` | ไทย+อังกฤษคั่น `,` | keywords_th / keywords_en |
| `## Abstract` | บทคัดย่อไทย␣␣␣ชื่ออังกฤษ␣␣␣บทคัดย่ออังกฤษ␣␣␣DOI: … | แยกด้วยช่องว่าง ≥2 + สัดส่วนอักษร; ดึง DOI; ตัด label "Abstract" |
| `## References` | bullet ที่ถูกตัดบรรทัด | ต่อบรรทัด, ปี พ.ศ.→ค.ศ., ตัด self-citation และส่วน "Translated Thai References" ออกจากการนับ |

ปัญหาข้อความที่ซ่อมให้อัตโนมัติ: อักษรไทย Private-Use (U+F700–F71A) จาก PDF, `ํา`→`ำ`, ช่องว่างก่อนสระบน/ล่าง · flag ใน `text_quality`: `thai_pua_repaired`, `tone_marks_missing`, `stat_symbols_missing`, `decode_replaced` (ไฟล์มีไบต์ที่ไม่ใช่ UTF-8 — ถอดรหัสด้วย U+FFFD แทน บทความยังถูกเก็บ)

ตาราง (`input.format: table`, csv/json/jsonl/parquet) ยังรองรับผ่าน `input.columns`

ตรวจคลังก่อนรัน: `uv run atlas profile /path/to/corpus --md ../logs/profile.md` (รายงานคุณภาพคลัง: จำนวนไฟล์ ไฟล์ที่อ่าน/parse ไม่ได้ ช่วงปี บทความลงวันที่ล่วงหน้า ยอดต่อปีเทียบปีก่อน ฟิลด์ว่าง วารสารที่อัปโหลดย้อนหลัง DOI ซ้ำแต่ชื่อเรื่องต่างกัน)

กฎความสะอาดที่ ingest ทำให้: ตัดแถวที่ `year` < `input.min_year` · article_id ซ้ำถูกตัดเสมอ (แม้ปิด dedup) · dedup ด้วย article_id → DOI **ที่ชื่อเรื่องไทย หรือชื่อเรื่องอังกฤษ ที่ normalize แล้ว (80 ตัวแรก) ตรงกันอย่างน้อยฝั่งหนึ่งด้วย** (ฝั่งที่ว่างไม่นับ; DOI เดียวกันแต่ทั้งไทยและอังกฤษต่างกัน = metadata ผิด เก็บทุกเรื่องและนับเป็น `doi_title_conflicts`) → ชื่อเรื่องที่ normalize แล้ว + ปี · พ.ศ. → ค.ศ. (พ.ศ. − 543) อัตโนมัติ · ไฟล์ที่อ่านหรือ parse ไม่ได้ (OSError, parser error) ถูกบันทึกใน `01_ingest_errors` แล้วข้าม — แต่ถ้าสัดส่วนเกิน `input.max_error_ratio` (default 0.01) หรือไม่มีไฟล์ใด parse ได้ ingest จะหยุดด้วย RuntimeError (หลังเขียน `01_ingest_errors` แล้ว)

## 2. Checkpoints (work_dir — ลบได้) และ state (state_dir — ห้ามลบ)
ไฟล์ตารางใช้ `io_utils.write_table/read_table` (parquet ถ้ามี pyarrow, ไม่งั้น pickle)

| ไฟล์ | step | คอลัมน์สำคัญ |
|---|---|---|
| `01_articles` | ingest | article_id, journal_name, year, year_source, title_th/en, abstract_th/en, keywords_th/en, authors, affiliations, n_authors, n_student_authors, n_references, has_references, self_citation_only, text_quality |
| `01_authors` | ingest | article_id, position, name, name_en, affiliation_th/en, role, is_student, org_key |
| `01_ingest_errors` | ingest | path, error (`"ชนิด: ข้อความ"`) — ไฟล์ที่อ่าน/parse ไม่ได้และถูกข้าม (เขียนทุกรอบ อาจว่าง) |
| `01_references` | ingest | article_id, position, text, year, lang, translated, self_citation |
| `02_docs` | preprocess | 01_articles + doc_text |
| `03_embeddings.npy`, `03_meta.json` | embed | matrix (แถวตรงกับ 02_docs, normalize แล้ว); meta: model_id (= store id), n, dim + สำหรับ api/local: store_id, n_retries, n_truncated |
| `04_fine_topics` | cluster | article_id, fine_topic (−1 = ยังไม่จัดหมวด) |
| `04_coarse_topics` | cluster | article_id, coarse_topic (−1 = ยังไม่จัดหมวด) |
| `04_topic_info` | cluster | topic_id, size, top_terms, top_keywords, coarse_topic, coherence |
| `04_centroids.npy`, `04_centroid_ids.json` | cluster | centroid ต่อหัวข้อ |
| `05_labels` | label | level, topic_id, name_th, name_en, description, keywords, cache_key (key ของ LLM cache หรือ `"fallback"`), label_source (`llm` \| `keywords` \| `override` \| `reused` = ชื่อของรอบก่อน: lineage `continue` และคำสำคัญ + คำเด่นยังทับซ้อนกับชุดคำตอนตั้งชื่อ ≥ `labeling.reuse_min_jaccard` — ไม่เรียก LLM) |
| `05_labels_meta.json` | label | provider, model_id, topics, from_cache, generated, repaired, fallback, reused, overrides, unknown_overrides, cost_usd (การรันครั้งนี้) |
| `05_merge_suggestions`, `05_merge_meta.json` | label | topic_a, topic_b, similarity, same_topic (True/False/None), reason, source · สถิติ LLM งาน merge |
| `06_series` | series | topic_id, year, count, count_with_org, corpus_total, share |
| `06_topic_journal_year`, `06_topic_org_year`, `06_journal_first_year`, `06_meta.json` | series | ใช้คำนวณความกว้าง + ปีสมบูรณ์ล่าสุด; `06_meta.json` = last_complete_year, as_of_year, trimmed_years (ปีที่มีข้อมูลแต่ไม่ใช้คำนวณแนวโน้ม), years, totals (บทความที่นำมาวิเคราะห์ต่อปี), n_articles (ทั้งคลัง = `kpis.articles` — headline ของบทสรุปบอกจำนวนที่วิเคราะห์พร้อมป้ายกำกับ) |
| `07_emerging` | emerging | ดู docs/EMERGING_SPEC.md §3 + org_coverage_R, orgs_unverified, status, journal_driven, emerging_score, definition_version (คอลัมน์ครบแม้ไม่มีหัวข้อ) |
| `09_layout`, `09_edges` | layout | id, kind, x, y, r, parent · s, t, w |
| `04_lineage`, `04_topics_meta.json` | cluster | event (new/continue/split/merge/retired), topic_id, parents · release (รอบที่ทุกขั้นหลัง cluster ต้องเขียน — `atlas.state.work_release`), previous_release, mode (fit/assign), kept_fraction, events, snapshot_at (เวลาท้องถิ่น ISO 8601 พร้อม offset: ใช้กำหนด as_of_year, เพดานเดือน nowcast และ generated_at) |
| `06_months`, `06_partial_year` | series | year, month, count (วันที่ตีพิมพ์ที่ตรงกับปี) · topic_id, year, count ของปีหลัง last_complete_year (ใช้ทำ nowcast) |
| `06_meta.json` (เพิ่ม) | series | partial_totals (ยอดบทความของปีหลัง last_complete_year), completeness {method: median (backfill guard v3) \| configured}, snapshot_at (คัดลอกจาก 04_topics_meta) |
| `07_keywords` | keywords | term, key, count_recent, count_baseline, share_ratio, no_baseline, growth(_lo/_hi), n_active_years, n_orgs_R, n_journals_R, new_journal_share, journal_driven, topic_id, emerging |
| `08_forecasts` (v2), `08_forecast_meta.json` | forecast | model, backtest_mae/mape, mase, skill_vs_naive, show, hist/fc (JSON) + fc_lo80/hi80/lo95/hi95, nowcast_* · total_model, conformal, n_calibration, nowcast — ช่วงคาลิเบรตจากเรคคอร์ดที่ซื่อสัตย์ของโมเดลที่เลือก; `show` ต้องมีจุด backtest ซื่อสัตย์ ≥ `forecast.min_honest_points`; nowcast มีเฉพาะปีปฏิทินที่กำลังดำเนินอยู่ (`forecast.nowcast.min_month_share`) |
| `09_galaxy` | layout | article_id, topic_id, gx, gy |
| `10_taxonomy`, `10_taxonomy_meta.json` | taxonomy | topic_id, group_id, group_en/th, subfield_id/en, vote_share, cross_field, source · version, holdout accuracy — เมื่อ fallback เป็น agglomerative: group_id = 1000 + coarse, code `G<n>`, ชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" / "Unmapped group N", meta มีเหตุผล (เช่น งบ OpenAlex รายวันหมด) |
| `11_narratives`, `11_brief.json` | narrate | topic_id, status, th, en, source (llm\|template) · {brief, llm} |
| `state/embeddings/<slug>-<hash>/` | embed | index.parquet + shard_NNNNN.npy (ถาวร; slug/hash จาก store id: `api\|<model>\|<dimensions>` หรือ `embedding.api.store_id` — ไม่รวม base_url; `local\|<model>\|<max_seq_length>`; hash = sha1 8 ตัวแรก) |
| `…/<store>/journal.bin` | embed | write-ahead log ของเวกเตอร์ที่ได้แล้วแต่ยังไม่เข้า store: header `ATJ1` + uint32 dim; record = sha1 key 40 ไบต์ ASCII + dim × float32 little-endian (flush ทุก batch, fsync ≤ ทุก 10 วินาที) — รันครั้งถัดไป replay เข้า store แล้วลบ (record ท้ายที่ขาด/เสียถูกข้าม) |
| `…/<store>/progress.json` | embed | สถานะงาน (เขียนแบบ atomic ทุก ~5 วินาที + ทุก flush/เปลี่ยนสถานะ): kind, store_id, status (`running`/`backing_off`/`stopped`/`done`/`failed`), pid, total, cached, embedded, remaining, rate_per_s, eta_s, retries, truncated, truncated_total, store_vectors, journal_pending, checkpoint_postponed, last_error, last_error_at, last_event, recovered, started_at, updated_at — อ่านด้วย `atlas status` (แสดง `interrupted` เมื่อ process ตาย, `hung` เมื่อยังอยู่แต่ heartbeat เก่ากว่า `lock_stale_seconds`); ระหว่างรัน status ใช้ store_vectors/journal_pending จากไฟล์นี้ ไม่เปิดไฟล์ store |
| `…/<store>/.lock` | embed | ไฟล์ว่าง ไม่ถูกลบ — process ที่รันถือ OS lock (msvcrt/fcntl) บนไฟล์นี้ตลอดการรัน = กันรันซ้อนจริง; OS ปล่อยเองเมื่อ process ตาย; `atlas status` ตัดสินว่างานยังรันอยู่จาก lock นี้ (ลองล็อกแบบไม่รอแล้วปล่อยทันที) |
| `…/<store>/run.lock` | embed | ข้อมูลเท่านั้น `{pid, host, started_at, pid_started}` (pid_started = เวลาเริ่ม process จาก OS กัน PID reuse) — `atlas status` ใช้บอกว่า process ยังอยู่ไหม; ลบเมื่อจบ (ค้างได้ ไม่มีผล) |
| `…/<store>/run.log` | embed `--background` | stdout+stderr ของการรันเบื้องหลัง (ต่อท้ายทุกครั้ง) |
| `…/<store>/stop.flag` | embed-stop | คำขอหยุด — runner หยุดสุภาพ (รอ request ที่ค้าง, flush) แล้วลบ; flag ที่เขียนก่อน process ที่รันเริ่ม = ค้างจากรอบก่อน ถูกลบทิ้ง, flag ที่ใหม่กว่า (เช่น สั่งตอนยัง ingest) ถูกทำตาม |
| `…/<store>/truncated.parquet` | embed | key, original_chars, used_chars, run_started_at — ข้อความที่ server รับไม่ได้จนต้องตัด (ต่อท้ายทุกรอบ, สะสม; `atlas status` แสดงจำนวนรวม) |
| `state/llm_cache/<task>.jsonl` | label, narrate | cache + journal ของทุก call LLM: key = sha256(model + prompt_version + prompt) · output (null = บันทึกค่าใช้จ่ายของ call ที่ใช้ fallback) · cost_usd · release |
| `state/llm_cache/progress.json`, `.lock`, `run.lock`, `stop.flag`, `run.log` | label, narrate | ไฟล์งานแบบเดียวกับ embedding store (P0 `atlas.jobs`): สถานะ (`atlas status`, kind `llm`), OS lock กันรันซ้อน (+ ข้อมูล PID), คำขอหยุด (`atlas llm-stop`), log ของ `atlas llm --background` |
| `state/releases/index.json`, `state/releases/<release>/topics/`, `…/layout.parquet`, `…/labels.parquet` | cluster, layout, label | ลำดับรอบ · assignments, registry (born/status/last_seen), lineage, model.json · ตำแหน่งหัวข้อ · ชื่อหัวข้อจากเครื่อง (ก่อน overrides): topic_id, name_th/en, description, keywords, cache_key, origin (`llm` \| `keywords`), label_terms (ชุดคำที่ใช้ตั้งชื่อ — รอบถัดไปเทียบ Jaccard กับชุดนี้ จึงไม่ไหลทีละนิด) |
| `state/openalex/reference_*.parquet` + `.json` | taxonomy | งานอ้างอิง OpenAlex ที่ดึงแล้ว (ไม่ดึงซ้ำ; cache ใช้ร่วมกันทั้งโหมดมี key และไม่มี key) |
| `pipeline/registry/label_overrides.csv` (นอก state; ไม่เข้า git) | label | ชื่อที่บรรณาธิการแก้: topic_id (T000123), name_th, name_en, description, reviewer, reviewed_at, note |

## 3. Output: `atlas_data.json` (สัญญากับเว็บ)

> เว็บ v2 ไม่อ่านไฟล์นี้แล้ว (อ่าน contract v2 ใน §6) — คงไว้เพื่อความเข้ากันได้ และเลิกผลิตได้ใน P2

ผลิตโดย `atlas/export.py` — **ห้ามเปลี่ยน contract v2 โดยไม่ generate types (`npm run gen:types`) และแก้เว็บตาม**

```jsonc
{
  "meta": {
    "generated_at": "2026-10-18T...",   // ISO datetime (UTC)
    "pipeline_version": "git hash หรือ nogit",
    "last_complete_year": 2024,          // ปีสมบูรณ์สุดท้าย (หลัง backfill guard)
    "total_articles": 200003,
    "total_topics": 132,
    "total_groups": 14,
    "schema_version": "1.1",
    "definition_version": 3,
    "as_of_year": 2026,                  // ปีที่รัน (config emerging.as_of_year หรือปีปัจจุบัน)
    "trimmed_years": [2025, 2026],       // ปีที่มีข้อมูลหลัง last_complete_year (ไม่ใช้คำนวณแนวโน้ม)
    "assigned_articles": 198000,
    "unassigned_articles": 2003,
    "n_orgs_unverified": 3               // จำนวนหัวข้อที่ข้ามเกณฑ์สถาบัน
  },
  "groups": [
    { "id": "g0", "th": "สุขภาพ", "en": "Health", "color": "#E5484D",
      "articles": 52000, "rank": 1 }     // เรียงตาม articles desc, rank เริ่ม 1
  ],
  "nodes": [
    // kind = "group" (จุดศูนย์กลางกลุ่ม)
    { "nodeId": "g0", "kind": "group", "id": "g0", "th": "...", "en": "...",
      "color": "#E5484D", "articles": 52000, "rank": 1,
      "x": 840.0, "y": 520.0, "r": 96.0, "nTopics": 12 },
    // kind = "topic" (หัวข้อวิจัย — เว็บ map เป็น kind "field")
    { "nodeId": "t17", "kind": "topic",
      "group": "g0",                    // id กลุ่มแม่
      "th": "การเฝ้าระวังฝุ่น PM2.5", "en": "PM2.5 monitoring",
      "description": "คำอธิบาย 1 บรรทัด",
      "keywords": "PM2.5; คุณภาพอากาศ; ...",   // คั่นด้วย ;
      "articles": 900, "color": "#E5484D",
      "x": 812.4, "y": 448.2, "r": 30.1,
      "status": "EMERGING",             // EMERGING | WATCH | HOT | DECLINING | STABLE | LOW_DATA
      "emerging_score": 92.5,           // 0–100 หรือ null
      "cagr_recent": 0.612,             // CAGR ช่วง R (ทศนิยม)
      "burst_years": "2022,2023",       // ปีที่ burst คั่นด้วย , หรือ ""
      "share_growth": 0.42, "share_growth_lo": 0.18, "share_growth_hi": 0.71,  // v1.1
      "n_journals_R": 9, "n_orgs_R": 14,  // v1.1
      "journal_driven": false,          // v1.1
      "orgs_unverified": false,         // v1.1 (v3): ข้อมูลสังกัดใน R ไม่พอ → ไม่ได้ตรวจเกณฑ์ "≥ 3 สถาบัน"
      "coherence": 0.31,                // v1.1
      "forecast_uncertain": false,      // v1.1
      "forecast": {                      // null ถ้าไม่ผ่าน skill gate, status = LOW_DATA หรือปิด include_forecast_in_json
        "model": "linear",              // naive | linear | poisson
        "backtest_mape": 12.4,          // %
        "mase": 0.8, "skill_vs_naive": 0.2,  // แสดงเมื่อ skill > forecast.min_skill
        "hist_years":  [2017, ..., 2024],
        "hist_counts": [  12, ...,  240],
        "fc_years":    [2025, 2026],
        "fc_mean":     [ 268,  295],
        "fc_lo":       [ 231,  244],
        "fc_hi":       [ 305,  346]
      }
    }
  ],
  "links": [
    { "s": "t17", "t": "t42", "w": 0.61 }   // edge ความคล้ายระหว่าง topic
  ]
}
```

### schema 1.1 additions
ต่อ node แบบ topic เพิ่ม: `share_growth`, `share_growth_lo`, `share_growth_hi` (ช่วงเชื่อมั่นของการโตของ share; null = ประมาณไม่ได้), `n_journals_R`, `n_orgs_R` (จำนวนวารสาร/สถาบันในช่วง R), `journal_driven`, `orgs_unverified` (v3, additive), `coherence`, `forecast_uncertain`
ต่อ `meta` เพิ่ม: `schema_version = "1.1"`, `definition_version = 3`, `assigned_articles`, `unassigned_articles`, และ (v3, additive) `as_of_year`, `trimmed_years`, `n_orgs_unverified`
`forecast` เป็น null เว้นแต่ผ่าน skill gate (`show` = true) และสถานะไม่ใช่ `LOW_DATA`; `forecast_uncertain` = true เมื่อมี forecast แต่ไม่ผ่าน gate หรือหัวข้อเป็น `LOW_DATA` (เว็บจึงไม่แสดงเส้นทำนาย)

## 4. การแปลงฝั่งเว็บ (loader.normalize)

| pipeline (snake) | web (camel) | หมายเหตุ |
|---|---|---|
| `nodeId` | `id` | |
| `kind: "topic"` | `kind: "field"` | group คงเดิม |
| `nTopics` | `nFields` | |
| `emerging_score` | `emergingScore` | |
| `burst_years` | `burstYears` | |
| `orgs_unverified` | `orgsUnverified` | optional (ยังไม่มี UI ใน P0) |
| `meta.total_topics` | `totalFields` | |
| `meta.total_articles` | `totalArticles` | |
| `meta.total_groups` | `totalGroups` | |
| `meta.last_complete_year` | `lastCompleteYear` | |
| `meta.generated_at` | `generatedAt` | |

เว็บขาดฟิลด์เสริมได้เสมอ (status/emergingScore/forecast เป็น optional) — ขาด `groups`/`nodes` ไม่ได้

## 5. ไฟล์เสริมสำหรับนักวิเคราะห์ (output/)

| ไฟล์ | เนื้อหา |
|---|---|
| `topics.csv` | แคตตาล็อก topic ทั้งหมด (id, ชื่อ, คำอธิบาย, keywords, size, กลุ่ม) |
| `emerging.csv` | metric emerging ทุกตัวต่อ topic (เอาไป pivot/plot ต่อเองได้) |
| `forecasts.csv` | โมเดล + ค่าทำนายต่อ topic |
| `manifest.json` | เวอร์ชัน pipeline, `definition_version`, `ci_level`, `as_of_year`, `trimmed_years`, `n_orgs_unverified`, `embedding_provider`, `embedding_model_id` (จาก 03_meta.json), `n_labels_fallback` (หัวข้อที่ได้ชื่อจาก keyword แทน LLM), `ingest_errors` (จำนวนไฟล์ที่ข้าม), config emerging ที่ใช้, `counts` (= meta) — ใช้ย้อนดูว่ารอบนั้นคำนวณด้วยนิยาม/ข้อมูลแบบไหน |

## 6. Data contract v2 (P1)

`pipeline/atlas/schema/contract.py` → `web/src/data/contract.schema.json` → `web/src/data/contract.ts`
สร้างด้วย `uv run atlas schema` และ `npm run gen:types` (CI ตรวจ drift ทั้งสองขั้น)

รอบข้อมูลหนึ่งรอบ = `output/data/<release>/` (เช่น `2026Q4/`) — JSON แบบ strict (ไม่มี NaN/Infinity), สีเป็น token `cat-01…cat-12` ไม่ใช่ hex, ไม่มีบทคัดย่อและไม่มีข้อมูลระดับบุคคล

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `manifest.json` | `Manifest` | release, previous_release, definition_version, **ci_level** (ระดับของช่วง `*_lo/*_hi` ทุกตัว), as_of_year, trimmed_years, embedding_provider/model, taxonomy_version, n_orgs_unverified, ingest_errors (null = ไม่มีบันทึก — ไม่ใช่ 0), labels {provider, llm, keywords, overrides, reused}, llm [{task, model, items, from_cache, generated, repaired, fallback, cost_usd = ยอดรวมของรอบข้อมูลนี้ทุกครั้งที่รัน (จาก journal), this_run_cost_usd = เฉพาะการรันล่าสุด}], files [{path, bytes, sha256}] |
| `overview.json` | `Overview` | KPI, จำนวนตามสถานะ, ยอดรายปี + พยากรณ์ยอดรวม, nowcast, lineage events, retired topics, data_quality (completeness), **brief** (headline + bullets, source llm/template) |
| `taxonomy.json` | `TaxonomyFile` | source (openalex/agglomerative), groups (F33 / G03, ชื่อ TH/EN, สี token, ตำแหน่ง hub), subfields — สีผูกกับรหัสกลุ่ม ไม่ใช่ลำดับขนาด: สาขา OpenAlex ใช้ตารางคงที่ (`export_v2.FIELD_COLOR`; 12 สาขาที่พบบ่อยใน TCI ได้สีไม่ซ้ำกัน), กลุ่ม `G<n>` = `cat-(n mod 12 + 1)`; ถ้าสองกลุ่มในรอบเดียวกันได้สีเดียวกัน รหัสที่น้อยกว่าคงสีไว้ อีกกลุ่มเลื่อนไปสีว่างถัดไป (ตัดสินจากชุดรหัสเท่านั้น ไม่ใช่ขนาด) → กลุ่มเดิมสีเดิมทุกไตรมาส |
| `topics.json` | `TopicsFile` | หัวข้อ: id T000123, group, ชื่อ, label_source (`llm` \| `keywords` \| `override` \| `reused`), ขนาด, ตำแหน่ง, status, score, metrics, forecast, lineage, subfield, cross_field, nowcast |
| `topics/<id>.json` | `TopicDetail` | บทความตัวแทน (ชื่อเรื่อง + ลิงก์ ThaiJO + พิกัด galaxy), วารสาร/สถาบันหลัก, คำสำคัญ, เพื่อนบ้าน, **narrative** — สถาบันนับตาม `org_key` (พับวรรณยุกต์/ตัวพิมพ์เพื่อรวมคำสะกดต่างกัน) แต่ `institutions[].key` เป็น**ชื่อที่เขียนจริง**ที่พบบ่อยที่สุดของ key นั้น (ส่วนชื่อองค์กรของสังกัด เช่น "มหาวิทยาลัยเกษตรศาสตร์" / "Naresuan University" — ไม่ตัดวรรณยุกต์ ไม่แปลงตัวพิมพ์; ไม่มีชื่อคณะ/ตำแหน่ง) |
| `series.json`, `edges.json`, `keywords.json` | `SeriesFile`, `EdgesFile`, `KeywordsFile` | ยอดรายปีต่อหัวข้อ · เส้นเชื่อม · emerging keywords |
| `output/data/latest.json` | `Latest` | {release, path: "<release>/manifest.json", schema_version, generated_at} — ชี้รอบใหม่สุดเท่านั้น (export/publish รอบเก่ากว่าไม่ย้าย; `atlas publish --set-latest` บังคับ) · `generated_at` ของทุกไฟล์ = snapshot_at (UTC) ของ work_dir จึง export ซ้ำได้ไฟล์เดิมทุกไบต์ |

- `metrics.share_ratio` เป็น **null** และ `no_baseline: true` เมื่อไม่มีบทความในช่วงฐาน (เว็บแสดง "ใหม่ — ไม่มีฐานเปรียบเทียบ") — เช่นเดียวกับ keyword
- `metrics.low_data_reason`: `few_articles` (count_recent < `min_articles_recent`) หรือ `not_estimable` (ประมาณอัตราโตไม่ได้) เมื่อ status = LOW_DATA
- กลุ่ม fallback (taxonomy.source = agglomerative): id 1000 + coarse, code `G<n>`, ชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" / "Unmapped group N"
- `atlas validate` ตรวจ integrity (sha256) · schema · ความสอดคล้อง · diff กับรอบก่อน · fallback ของ LLM; `atlas publish --site <dir>` วาง `data/<release>/` + `data/latest.json` + `atlas-offline.html` (ข้อมูลฝังใน `<script type="application/json" id="atlas-data">` ของ `offline-template.html` ที่ web build สร้าง)
- ความปลอดภัยของรอบ: validate เป็น error เมื่อ `manifest.release` ไม่ตรงกับชื่อโฟลเดอร์ และเตือน (ข้าม diff) เมื่อไม่พบโฟลเดอร์รอบก่อนหน้า; ชื่อรอบต้องเป็นรูป YYYYQn (`../x` ถูกปฏิเสธ)

## 7. P2 — รุ่นบรรณาธิการ (contract 2.1, เพิ่มอย่างเดียว)

`SCHEMA_VERSION = "2.1.0"` — ไฟล์ใหม่ทุกไฟล์เป็น optional และประกาศใน `manifest.modules` (`journals`, `journal_detail`, `methods`, `match`, และ `diff` ตั้งแต่รอบที่สองเป็นต้นไป); เว็บตรวจเฉพาะ major = 2 และ `CountItem.id` (ใหม่) ทำให้หน้าหัวข้อลิงก์ไปยังวารสารได้ ข้อมูลระดับบุคคลและข้อความบทคัดย่อ **ไม่** ถูกเผยแพร่ในไฟล์ใดเลย

### Checkpoint ใหม่ใน `work_dir` (ลบได้)

| ไฟล์ | step | เนื้อหา |
|---|---|---|
| `12_methods_articles` · `12_methods_topics` · `12_methods_notes` · `12_methods_meta.json` | `methods` | วิธีวิจัยรายบทความ (article_id, year, topic_id, methods, sample_size) · ต่อหัวข้อที่มี ≥ `methods.min_articles` บทความในหน้าต่าง · บันทึกหัวข้อ (เฉพาะ `methods.provider: llm`) · เวอร์ชัน lexicon, หน้าต่าง, สัดส่วนทั้งคลัง/รายปี |
| `13_journals` · `13_journal_years` · `13_journal_topics` · `13_journal_drift` · `13_journal_shifts` · `13_journal_topic_years` · `13_journal_peers` · `13_journal_completeness` · `13_journal_methods` · `13_special_issue` · `13_journal_opportunities` · `13_journals_meta.json` | `journals` | ตัวตนวารสาร (+ทะเบียน), ความครบถ้วน D2, เจ้าของ/สัดส่วนในสถาบัน D3, ความหลากหลายสถาบัน, ผู้แต่งต่างประเทศ (สัดส่วน), drift D1, เพื่อน D4, ช่องว่างฉบับพิเศษ D5, วิธีวิจัย D7 — อ่านแถวผู้แต่งที่ step นี้เท่านั้น |
| `14_match.json` | `match` | ดัชนี trigram: gram, idf, น้ำหนักต่อหัวข้อ, สัดส่วนหัวข้อของแต่ละวารสาร |
| `state_dir/releases/<release>/snapshot.json` | `export` | สรุปย่อของรอบ (หัวข้อ + KPI + รายชื่อวารสาร) ที่รอบถัดไปใช้ทำ `diff.json`; รอบก่อน P2 ที่ไม่มี snapshot ใช้ `output/data/<prev>/` แทน (`previous_source: output`) |

### ไฟล์ที่เผยแพร่ (`data/<release>/`)

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `journals.json` | `JournalsFile` | `window`/`recent`/`baseline`, `min_articles`, `completeness_weights`, `inhouse_flag_share` (null = ไม่มีเครื่องหมาย), เกณฑ์ special issue (`special_issue_statuses`, `_max_hosts`, `_min_host_articles`), `drift_reference_years`; `journals[]` = `JournalSummary`; `special_issue[]` = `SpecialIssueTopic` (topic, hosts, top_host_share, articles_recent) |
| `journals/<id>.json` | `JournalDetail` | `years`, `topics` (TopicShare), `drift` (DriftPoint, distance = Jensen–Shannon), `gained`/`lost` (TopicShift), `peers` (cosine ของสัดส่วนหัวข้อ), `completeness` (7 องค์ประกอบ: abstract_en, title_en, keywords_en, doi, references, refs_romanized, affiliations), `methods`, `opportunities` (`in_scope` \| `adjacent`), `topic_years` (2.4: ดู §10) |
| `methods.json` | `MethodsFile` | `lexicon_version`, `window`, `methods[]` (key/th/en), `corpus` + `by_year` (สัดส่วนวิธีต่อปี), `topics[]` = `TopicMethods` (ครอบคลุม, สัดส่วนวิธี, ควอร์ไทล์ขนาดตัวอย่าง, `monoculture` + `monoculture_share`, `note` เมื่อใช้ LLM) |
| `diff.json` | `DiffFile` | `previous_release`, `previous_source` (`state` \| `output`), `kpis`, `new_topics` (event new/split/merge + parents), `retired` (`merged_into` เฉพาะที่ lineage ระบุว่ารวมเข้า), `restructured` (หัวข้อที่คงรหัสผ่านการรวม/แยก), `status_changes`, `movers`, `journals_compared`, `new_journals` |
| `match.json` | `MatchIndex` | `analyzer: char_wb3`, `fold: atlas-fold-1`, `grams` + `idf`, `topics[]` (terms, weights), `journals[]` (topics, shares), `min_similarity`, `fit_topics`, `min_query_chars` — ไม่มีข้อความบทความ; ไม่อยู่ใน HTML ออฟไลน์ |

`JournalSummary` (หนึ่งแถวต่อวารสาร): `id` (เช่น `so02.BECJournal` — ฟังก์ชันคงที่ของ `<server>:<OJS path>`; key ที่ไม่ใช่ ASCII = `J` + 12 hex ของ sha1), `key`, `path`, `name_th`/`name_en`/`issn`/`eissn`/`tci_tier`/`tci_field`/`publisher`/`url` (จากทะเบียน, ว่างได้), `in_registry`, `articles`, `articles_window`, `articles_recent`, `first_year`, `last_year`, `active`, `low_data` (น้อยกว่า `min_articles` → ทุกอัตราเป็น null), `group`, `completeness` (0–100, **ไม่ใช่การประเมินอย่างเป็นทางการของ TCI**), `owner` + `owner_source` (`registry` \| `inferred`; เว็บแสดง "อนุมาน / inferred") + `owner_matched`, `inhouse_share`, `n_orgs`, `effective_orgs`, `foreign_share`, `affiliation_coverage`, `methods_coverage`.

PDPA: ตัวเลขของวารสารเป็นยอดรวมเท่านั้น — ไม่มีชื่อบุคคล แถวต่อผู้แต่ง หรืออันดับบุคคล; "ผู้แต่งต่างประเทศ" = สัดส่วนบทความที่มีสังกัด ≥ 1 แห่งนอกประเทศไทย

## 8. P3 — รุ่นผู้บริหาร (contract 2.2, เพิ่มอย่างเดียว)

`SCHEMA_VERSION = "2.2.0"` — ไฟล์ใหม่ทุกไฟล์ optional และประกาศใน `manifest.modules` (`institutions`, `institution_detail`, `regions`, `sdg`, `global`, `gaps`); โมดูลที่ข้ามพร้อมเหตุผลอยู่ใน `manifest.skipped_modules` (เช่น `{"global": "OpenAlex unavailable: …"}`). PDPA: เผยแพร่เฉพาะยอดรวมระดับสถาบัน — ไม่มีชื่อบุคคล แถวต่อผู้แต่ง หรือบทคัดย่อ; สถาบันที่มีบทความในช่วงน้อยกว่า `institutions.min_articles` (5) ถูกนับในยอดรวมแต่ไม่อยู่ในไฟล์ใด (รายการ, หน้า, คู่ความร่วมมือ, สถาบันหลักของจังหวัด, `top` ของ concentration, ข้อเสนอ R6)

### Checkpoint ใหม่ใน `work_dir` (ลบได้)

| ไฟล์ | step | เนื้อหา |
|---|---|---|
| `15_article_institutions` · `15_institutions` · `15_inst_years` · `15_inst_topics` · `15_inst_pairs` · `15_inst_countries` · `15_inst_suggest` · `15_provinces` · `15_regions` · `15_institutions_meta.json` | `institutions` | คู่ (บทความ, สถาบัน) ทุกปี · หนึ่งแถวต่อสถาบัน (inst_key, code, ชื่อ, type, province, country, source, ror, articles/articles_total/articles_recent, intl_share, partners, topics, published) · บทความรายปี · หัวข้อ · คู่ความร่วมมือ (≥ `network_min_articles`) · ประเทศคู่ความร่วมมือ · ข้อเสนอ R6 (cosine ≥ `suggest_min_similarity` และไม่มีบทความร่วมกัน) · บทความรายจังหวัด/ภาค (บทความหนึ่งนับทุกจังหวัดของผู้แต่ง) · หน้าต่างปี, coverage, KPI, population |
| `16_topic_goals` · `16_sdg_meta.json` | `sdg` | topic_id, framework, goal_id, score (สูงสุด `sdg.max_goals_per_topic` ต่อกรอบ) · method (embedding \| lexical), version, กรอบและเป้าหมาย |
| `17_benchmark` · `17_benchmark_meta.json` | `benchmark` | ต่อ OpenAlex subfield: world_R/B, country_R/B, tci_R, world_ratio, activity_index, country_share, opportunity · `{"skipped": เหตุผล}` เมื่อข้าม |
| `18_gap_few_institutions` · `18_gap_bridges` · `18_gap_world` · `18_concentration` · `18_gaps_meta.json` | `gaps` | หัวข้อสถานะ `gaps.statuses` ที่สถาบันทำน้อย · คู่หัวข้อเพื่อนบ้านที่สถาบันซ้อนกันน้อย · โอกาสจาก benchmark + หัวข้อที่ตรงกัน · HHI และ top share ต่อหัวข้อ/สาขา |
| `state_dir/ror/<dump>.<country>.json` | `institutions` | แคชข้อมูล ROR เฉพาะประเทศ (สร้างจาก `institutions.ror_path` ครั้งแรกครั้งเดียว) |

### ไฟล์ที่เผยแพร่ (`data/<release>/`)

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `institutions.json` | `InstitutionsFile` | `window`/`recent`, `min_articles`, `network_min_articles`, `articles_with_org`, `pct_international`, `pct_multi_institution` (เศษส่วน), `sources` (alias/ror/name); `institutions[]` = `InstitutionSummary` (id, name_th/en, type, province, country, source, ror, articles, articles_total, articles_recent, intl_share, partners, topics, group); `edges[]` = `CollabEdge` (a, b, articles); `countries[]` = `CountryCount`; `province_names[]` |
| `institutions/<id>.json` | `InstitutionDetail` | `years`, `topics` (TopicShare), `partners` (Partner), `countries`, `suggested` (Suggestion: id, similarity, topics — R6) |
| `regions.json` | `RegionsFile` | `window`, `articles_with_org`, `articles_located`, `coverage`, `population_year`; `provinces[]` = `ProvinceStat` (code, ชื่อ, region, articles, articles_recent, share, institutions, per_100k (null เมื่อไม่มีประชากร), top[]); `regions[]` (key, articles, share) — ส่วนแบ่งรวมกันเกิน 1 ได้ (บทความนับเต็มทุกจังหวัดของผู้แต่ง) |
| `sdg.json` | `SdgFile` | `method`, `version`, `frameworks[]` (sdg, bcg, ววน., หมุดหมายแผนฯ 13), `goals[]` = `GoalStat` (id, framework, number, th/en, topics, articles_recent, share_recent, share_ratio); `Topic.sdg` ในรายหัวข้อ |
| `global.json` | `GlobalFile` | `source` (เช่น openalex@วันที่), `country`, `recent`, `baseline`, เกณฑ์ (`min_world_works`, `min_world_ratio`, `max_activity_index`), `subfields[]` = `SubfieldBench` (world/country recent/baseline, tci_recent, world_ratio, activity_index, country_share, opportunity, topics) |
| `gaps.json` | `GapsFile` | เกณฑ์ที่ใช้, `few_institutions[]`, `bridges[]` (a, b, similarity, shared, jaccard), `world[]`, `concentration[]` = `Concentration` (scope, id, kind, articles, hhi, top_share, top, top_name, concentrated) |

หน่วย KPI: `Kpis.pct_international` / `pct_multi_institution` เป็น **เปอร์เซ็นต์** (เหมือน `pct_abstract_en`), `provinces` เป็นจำนวนจังหวัดที่มีบทความ; สัดส่วนในไฟล์โมดูล (`intl_share`, `share`, `coverage`, `top_share`) เป็น **เศษส่วน** 0–1. `Overview.executive` = `bullets_th` / `bullets_en` / `source: "template"` — ประโยคแม่แบบสร้างตอน export จากไฟล์ข้างต้น (ไม่มี LLM; ตัวเลขทุกตัวมาจากไฟล์)

## 9. P4 — รุ่นนักวิจัย (contract 2.3, เพิ่มอย่างเดียว)

`SCHEMA_VERSION = "2.3.0"` — ไฟล์ใหม่ทุกไฟล์ optional และประกาศใน `manifest.modules` (`references`, `search`, `galaxy`, `kwtrends`); โมดูลที่ข้ามพร้อมเหตุผลอยู่ใน `manifest.skipped_modules` (เช่น `{"references": "reference coverage 12.3% of 4,210 articles 2015–2025 (< references.min_coverage 50.0%)"}`, `{"galaxy": "layout.galaxy is false"}`). ลำดับ step: `… gaps → references → search → kwtrends → export`. PDPA: ข้อมูลบทความที่เผยแพร่ = id, ชื่อเรื่อง TH/EN, ปี, ชื่อวารสาร, หัวข้อ, DOI, ลิงก์ ThaiJO, จำนวน "ถูกอ้างใน TCI" เท่านั้น — **ไม่มีชื่อผู้แต่งและไม่มีบทคัดย่อ** ในไฟล์ใดเลย (ดัชนีค้นหาสร้างจากชื่อเรื่อง + คำสำคัญของผู้แต่ง; ไม่มีข้อความรายการอ้างอิง); `test_release` สแกนไฟล์ใหม่ทุกไฟล์หาชื่อผู้แต่ง/ข้อความบทคัดย่อของไฟล์จริง 11 ไฟล์

### Checkpoint ใหม่ใน `work_dir` (ลบได้)

| ไฟล์ | step | เนื้อหา |
|---|---|---|
| `19_ref_matches` · `19_article_cites` · `19_journal_refs` · `19_topic_flows` · `19_refs_meta.json` | `references` | citing_id, cited_id, method (`doi` \| `title`) · article_id, cited_in_tci (จำนวนบทความในคลังที่อ้างถึง นับครั้งเดียวต่อบทความที่อ้าง; > 0 เท่านั้น) · ต่อวารสารที่มีบทความที่มีรายการอ้างอิง ≥ `references.min_journal_articles`: articles, articles_with_refs, refs_median, age_median, share_recent, share_thai, share_doi · หัวข้อที่อ้าง → หัวข้อที่ถูกอ้าง, n · window, coverage, counts, methods, published/skipped, internal/internal_reason |
| `20_docs` · `20_postings` · `20_galaxy_points` · `20_search_meta.json` | `search` | ordinal, article_id, title_th/en, year, journal_index, topic_id (−1 = ยังไม่จัดหมวด), doi, url (ไม่มีผู้แต่ง ไม่มีบทคัดย่อ) · คู่ (token, ordinal) ไม่ซ้ำ เรียงแล้ว · ordinal, x, y (0…65535 บน view box ของแผนที่, −1 = ไม่มีพิกัด), topic_id, year · n_docs, window, journals, years, search {published, skipped, tokenizer_version, …}, galaxy {published, skipped, bounds, placed} |
| `21_kw_years` · `21_glossary` · `21_kwtrends_meta.json` | `kwtrends` | lang, key, term, rank, year, count (หนึ่งแถวต่อคำ × ปีของอนุกรมเวลา) · scope (`topic` \| `all`), topic_id (−1 = ทั้งคลัง), rank, th_key, en_key, th, en, n · published, skipped, years, totals, totals_th, totals_en, candidates, kept, paired_articles, pairs |
| `16_topic_goal_scores` | `sdg` | (เฉพาะ `sdg.method` embedding) cosine ทุกคู่หัวข้อ × เป้าหมาย คอลัมน์เดียวกับ `16_topic_goals` — อ่านโดย `atlas sdg-scores` เท่านั้น ไม่เผยแพร่ |

**ลำดับบทความ (doc ordinal):** หนึ่ง ordinal ต่อบทความที่เผยแพร่ = ตำแหน่งใน `01_articles` เรียงตาม `article_id` เฉพาะบทความที่มีปีอยู่ในช่วงที่วิเคราะห์ (`atlas.checkpoints.analysed_window` = ปีของอนุกรมเวลา + ปีล่าสุดที่ตัดออก) และมีชื่อเรื่อง TH หรือ EN — ไฟล์ค้นหาและ `galaxy.json` ใช้ ordinal เดียวกัน (`atlas.search_index.doc_order`)

**การตัดคำ (tokenizer_version 1):** NFC, ตัวพิมพ์เล็ก, เลขไทย → 0–9, แบ่งเป็นช่วงอักษรไทย/ช่วงอักษรอื่น; ช่วงไทยตัดด้วย pythainlp `newmm`; เก็บ token ≥ 2 code point ที่ไม่อยู่ใน stopword (ตัวเลขล้วนเก็บเฉพาะ 4 หลัก = ปี), ยาว ≤ `search.max_token_chars`, df ≥ `search.min_df`. ฝั่งค้น (`query_tokens` ใน Python = `web/src/lib/searchTokens.ts`) ไม่ใช้ pythainlp: ช่วงไทยจับคู่แบบยาวที่สุดก่อนกับ vocab, คำที่ไม่พบรายงานเป็น `unknown` — ทั้งสองฝั่งตรึงด้วย `pipeline/tests/fixtures/search_parity.json` (สร้างใหม่ด้วย `pipeline/scripts/make_search_parity.py`)

### ไฟล์ที่เผยแพร่ (`data/<release>/`)

| ไฟล์ | model | เนื้อหา |
|---|---|---|
| `references.json` | `ReferencesFile` | (เผยแพร่เมื่อ coverage ≥ `references.min_coverage`) `window`, `articles`, `articles_with_refs`, `coverage`, `refs_counted`, เกณฑ์ (`min_coverage`, `min_journal_articles`, `recent_years`); `journals[]` = `JournalRefs` (journal, id → `journals/<id>.json`, refs_median, age_median, share_recent, share_thai, share_doi); `internal` = `InternalCitations` (matches, citing/cited_articles, share_doi/share_title, `topics[]` received/given, `flows[]` source→target ≥ `min_flow`, `top_articles[]` = `CitedArticle` ไม่มีผู้แต่ง) หรือ null + `internal_reason` เมื่อจับคู่ได้ < `references.min_internal_matches` |
| `search/meta.json` | `SearchMeta` | tokenizer_version, n_docs, n_tokens, n_postings, index_shards, docs_per_shard, doc_shards, max_token_chars, max_results, min_df, fields (title_th, title_en, keywords_th, keywords_en), stopwords, journals (รายชื่อ — แถว doc อ้างด้วย index), years |
| `search/vocab.json` | `SearchVocab` | `tokens` (เรียงตาม code point) + `df` ต่อ token |
| `search/idx-<NNN>.json` | `SearchIndexShard` | `postings`: token → ordinal เรียงไม่ซ้ำ เข้ารหัส delta (ค่าแรกเป็นค่าจริง ต่อไปเป็นผลต่าง); token อยู่ shard `fnv1a32(token) % index_shards` (FNV-1a 32 บิตบนไบต์ UTF-8) — เขียนครบทุก shard แม้ว่าง |
| `search/docs-<NNN>.json` | `SearchDocShard` | `start` + `docs[]` = `[article_id, title_th, title_en, year, journal_index, topic id \| null, doi \| null, ThaiJO url \| null, cited_in_tci]` ของ ordinal `start …` (shard = ordinal // docs_per_shard) |
| `galaxy.json` | `GalaxyFile` | แบบคอลัมน์ ตรงกับ ordinal: `n` (= n_docs), `scale` (65535), `bounds` (x0, y0, x1, y1 = view box ของแผนที่หัวข้อ), `topics` (รหัสหัวข้อ), `x`/`y` (−1 = ไม่มีพิกัด), `t` (index ใน topics, −1 = ยังไม่จัดหมวด), `yr` — ข้ามเมื่อ `layout.galaxy: false` หรือไม่มี `09_galaxy` |
| `kwtrends.json` | `KwTrendsFile` | `years` (ปีของอนุกรมเวลา — ไม่รวมปีล่าสุดที่ตัดออก), `totals` (= `series.json` corpus_total), `totals_th`/`totals_en` (บทความที่มีคำสำคัญไทย/อังกฤษ ≥ 1), เกณฑ์ (`min_count`, `max_keywords`, `glossary_min_pairs`); `keywords[]` = `KeywordTrend` (term, lang, n, counts ต่อปี) — สัดส่วน = counts ÷ totals; `glossary[]` = `GlossaryItem` (th, en, n) ทั้งคลัง สูงสุด `kwtrends.glossary_max` |
| `topics/<id>.json` (เพิ่มฟิลด์) | `TopicDetail` | `cited_in_tci` (จำนวนครั้งที่บทความของหัวข้อถูกบทความอื่นในคลังอ้าง; null = ไม่เผยแพร่ส่วน internal), `glossary` (คู่คำไทย↔อังกฤษเด่นของหัวข้อ สูงสุด `kwtrends.glossary_per_topic`; **null = โมดูลไม่ถูกเผยแพร่, [] = ไม่พบคู่คำ**) |
| `latest.json` (เพิ่มฟิลด์) | `Latest` | `feeds: true` เมื่อ `atlas publish --site` เขียนฟีด Atom (ต้องตั้ง `publish.site_url`) — ไม่อยู่ใน latest ที่ฝังใน HTML ออฟไลน์ |

`search/` และ `galaxy.json` ไม่อยู่ใน HTML ออฟไลน์ (`export.offline_exclude: [match.json, search, galaxy.json]`) — หน้า `/search` และ `/galaxy` ของฉบับออฟไลน์อธิบายตัวเองผ่าน `ModuleFile`

### ฟีด Atom (เขียนโดย `atlas publish --site` เท่านั้น ไม่ใช่ส่วนของรอบข้อมูล)

| ไฟล์ | เนื้อหา |
|---|---|
| `<site>/data/feeds/releases.xml` | หนึ่ง entry ต่อรอบที่อยู่บนเว็บ ใหม่สุดก่อน (≤ `publish.feed_max_entries`): title = รอบ, summary = headline ของ overview (TH, EN) + สิ่งที่เปลี่ยน (ใหม่/หายไป/เปลี่ยนสถานะ จาก `diff.json` เมื่อมี), ลิงก์ `<site_url>#/changes` |
| `<site>/data/feeds/topics/<id>.xml` | หนึ่งฟีดต่อหัวข้อของรอบใหม่สุด; entry = รอบที่มีหัวข้อนั้น (สถานะ, บทความในช่วงล่าสุด, อัตราโตของสัดส่วน), ลิงก์ `<site_url>#/topics/<id>`; ฟีดของหัวข้อที่ไม่อยู่ในรอบใหม่สุดถูกลบ |

สร้างจากไฟล์ที่อยู่บนเว็บเท่านั้น (`manifest.json`, `overview.json`, `diff.json`, `topics.json` ของแต่ละรอบ) → รันซ้ำได้ไบต์เดิม; `<updated>` = `generated_at` ของ manifest; XML escape เอง (`xml.sax.saxutils.escape`)

## 10. สัดส่วนหัวข้อรายปีของวารสาร (contract 2.4, เพิ่มอย่างเดียว)

`SCHEMA_VERSION = "2.4.0"` — `JournalDetail.topic_years` (`JournalTopicYears` หรือ **null = ไม่เผยแพร่**: วารสารข้อมูลน้อย (< `journals.min_articles` ในช่วง W), `journals.year_mix_topics: 0`, หรือรอบที่ออกก่อน 2.4)

| ฟิลด์ | ความหมาย |
|---|---|
| `years` | ทุกปีในช่วง W (เช่น 2020–2024) |
| `articles` | บทความของวารสารที่เข้าหัวข้อ ต่อปี |
| `min_articles` | = `journals.year_mix_min_articles` — ปีที่ `articles` น้อยกว่านี้มีสัดส่วนเป็น null ทุกเส้น (ไม่ใช่ศูนย์) |
| `topics[]` | `JournalTopicLine` = `topic` + `shares` (ต่อปี) ของ `journals.year_mix_topics` หัวข้อที่ใหญ่ที่สุดของวารสารในช่วง W (มากไปน้อย, เสมอกันเรียงตาม id) |
| `other` | สัดส่วนของหัวข้ออื่นทั้งหมดรวมกัน ต่อปี — ปีที่มีค่า: `sum(topics[].shares[k]) + other[k] = 1` |

ทุกอาร์เรย์ยาวเท่า `years` (validator ตรวจ). Checkpoint: `13_journal_topic_years` (journal_key, year, topic_id (-1 = อื่น ๆ), articles, share) จาก `journal_topics.topic_years`. เว็บ: หน้า `/journals/:id` ส่วน "ตีพิมพ์เรื่องอะไรบ้าง" แสดงเป็น small multiples (ช่องละหัวข้อ แกนตั้งเดียวกัน) + แท็บตาราง (ปี × หัวข้อ + เรื่องอื่น) + ประโยคตัวอย่าง และบอกปีที่เว้นว่างใต้กราฟ

## 11. หัวข้อรายจังหวัด (contract 2.5, เพิ่มอย่างเดียว)

`SCHEMA_VERSION = "2.5.0"` — `ProvinceStat.topics` (ใน `regions.json`) = `TopicShare[]` ของ `institutions.province_topics` หัวข้อที่ใหญ่ที่สุดของจังหวัดในช่วง W (มากไปน้อย, เสมอกันเรียงตาม id; `share` = สัดส่วนของบทความในจังหวัดที่จัดเข้าหัวข้อได้; บทความนับครั้งเดียวต่อจังหวัดของผู้เขียน) — `[]` เมื่อไม่มีหรือรอบเก่า. Checkpoint `15_province_topics` (province, topic_id, count, share) จาก `institutions.province_topics()`. เว็บ: `/province` (ทุกจังหวัดแยกตามภาค) และ `/province/:code` ("งานวิจัยในจังหวัดของฉัน")
