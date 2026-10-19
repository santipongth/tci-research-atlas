# DATA_SPEC — สเปกข้อมูลเข้า/ออก

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
| `05_labels` | label | level, topic_id, name_th, name_en, description, keywords, cache_key (key ของ LLM cache หรือ `"fallback"`), label_source (`llm` \| `keywords` \| `override`) |
| `05_labels_meta.json` | label | provider, model_id, topics, from_cache, generated, repaired, fallback, overrides, unknown_overrides, cost_usd |
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
| `state/releases/index.json`, `state/releases/<release>/topics/`, `…/layout.parquet` | cluster, layout | ลำดับรอบ · assignments, registry (born/status/last_seen), lineage, model.json · ตำแหน่งหัวข้อ |
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
| `manifest.json` | `Manifest` | release, previous_release, definition_version, **ci_level** (ระดับของช่วง `*_lo/*_hi` ทุกตัว), as_of_year, trimmed_years, embedding_provider/model, taxonomy_version, n_orgs_unverified, ingest_errors, labels {provider, llm, keywords, overrides}, llm [{task, model, items, from_cache, generated, repaired, fallback, cost_usd}], files [{path, bytes, sha256}] |
| `overview.json` | `Overview` | KPI, จำนวนตามสถานะ, ยอดรายปี + พยากรณ์ยอดรวม, nowcast, lineage events, retired topics, data_quality (completeness), **brief** (headline + bullets, source llm/template) |
| `taxonomy.json` | `TaxonomyFile` | source (openalex/agglomerative), groups (F33 / G03, ชื่อ TH/EN, สี token, ตำแหน่ง hub), subfields |
| `topics.json` | `TopicsFile` | หัวข้อ: id T000123, group, ชื่อ, label_source, ขนาด, ตำแหน่ง, status, score, metrics, forecast, lineage, subfield, cross_field, nowcast |
| `topics/<id>.json` | `TopicDetail` | บทความตัวแทน (ชื่อเรื่อง + ลิงก์ ThaiJO + พิกัด galaxy), วารสาร/สถาบันหลัก, คำสำคัญ, เพื่อนบ้าน, **narrative** — สถาบันนับตาม `org_key` (พับวรรณยุกต์/ตัวพิมพ์เพื่อรวมคำสะกดต่างกัน) แต่ `institutions[].key` เป็น**ชื่อที่เขียนจริง**ที่พบบ่อยที่สุดของ key นั้น (ส่วนชื่อองค์กรของสังกัด เช่น "มหาวิทยาลัยเกษตรศาสตร์" / "Naresuan University" — ไม่ตัดวรรณยุกต์ ไม่แปลงตัวพิมพ์; ไม่มีชื่อคณะ/ตำแหน่ง) |
| `series.json`, `edges.json`, `keywords.json` | `SeriesFile`, `EdgesFile`, `KeywordsFile` | ยอดรายปีต่อหัวข้อ · เส้นเชื่อม · emerging keywords |
| `output/data/latest.json` | `Latest` | {release, path: "<release>/manifest.json", schema_version, generated_at} — ชี้รอบใหม่สุดเท่านั้น (export/publish รอบเก่ากว่าไม่ย้าย; `atlas publish --set-latest` บังคับ) · `generated_at` ของทุกไฟล์ = snapshot_at (UTC) ของ work_dir จึง export ซ้ำได้ไฟล์เดิมทุกไบต์ |

- `metrics.share_ratio` เป็น **null** และ `no_baseline: true` เมื่อไม่มีบทความในช่วงฐาน (เว็บแสดง "ใหม่ — ไม่มีฐานเปรียบเทียบ") — เช่นเดียวกับ keyword
- `metrics.low_data_reason`: `few_articles` (count_recent < `min_articles_recent`) หรือ `not_estimable` (ประมาณอัตราโตไม่ได้) เมื่อ status = LOW_DATA
- กลุ่ม fallback (taxonomy.source = agglomerative): id 1000 + coarse, code `G<n>`, ชื่อ "ยังไม่จัดสาขา (กลุ่ม N)" / "Unmapped group N"
- `atlas validate` ตรวจ integrity (sha256) · schema · ความสอดคล้อง · diff กับรอบก่อน · fallback ของ LLM; `atlas publish --site <dir>` วาง `data/<release>/` + `data/latest.json` + `atlas-offline.html` (ข้อมูลฝังใน `<script type="application/json" id="atlas-data">` ของ `offline-template.html` ที่ web build สร้าง)
- ความปลอดภัยของรอบ: validate เป็น error เมื่อ `manifest.release` ไม่ตรงกับชื่อโฟลเดอร์ และเตือน (ข้าม diff) เมื่อไม่พบโฟลเดอร์รอบก่อนหน้า; ชื่อรอบต้องเป็นรูป YYYYQn (`../x` ถูกปฏิเสธ)
