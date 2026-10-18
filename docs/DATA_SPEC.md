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

ปัญหาข้อความที่ซ่อมให้อัตโนมัติ: อักษรไทย Private-Use (U+F700–F71A) จาก PDF, `ํา`→`ำ`, ช่องว่างก่อนสระบน/ล่าง · flag ใน `text_quality`: `thai_pua_repaired`, `tone_marks_missing`, `stat_symbols_missing`

ตาราง (`input.format: table`, csv/json/jsonl/parquet) ยังรองรับผ่าน `input.columns`

ตรวจคลังก่อนรัน: `uv run atlas profile /path/to/corpus --md ../logs/profile.md` (รายงานคุณภาพคลัง: จำนวนไฟล์ ช่วงปี ฟิลด์ว่าง วารสารที่อัปโหลดย้อนหลัง)

กฎความสะอาดที่ ingest ทำให้: ตัดแถวที่ `year` < `input.min_year` · dedup ด้วย article_id, DOI และชื่อเรื่องที่ normalize แล้ว + ปี · พ.ศ. → ค.ศ. (พ.ศ. − 543) อัตโนมัติ

## 2. Checkpoints (work_dir — ลบได้) และ state (state_dir — ห้ามลบ)
ไฟล์ตารางใช้ `io_utils.write_table/read_table` (parquet ถ้ามี pyarrow, ไม่งั้น pickle)

| ไฟล์ | step | คอลัมน์สำคัญ |
|---|---|---|
| `01_articles` | ingest | article_id, journal_name, year, year_source, title_th/en, abstract_th/en, keywords_th/en, authors, affiliations, n_authors, n_student_authors, n_references, has_references, self_citation_only, text_quality |
| `01_authors` | ingest | article_id, position, name, name_en, affiliation_th/en, role, is_student, org_key |
| `01_references` | ingest | article_id, position, text, year, lang, translated, self_citation |
| `02_docs` | preprocess | 01_articles + doc_text |
| `03_embeddings.npy`, `03_meta.json` | embed | matrix (แถวตรงกับ 02_docs), model_id |
| `04_fine_topics`, `04_coarse_topics` | cluster | article_id → topic (−1 = ยังไม่จัดหมวด) |
| `04_topic_info` | cluster | topic_id, size, top_terms, top_keywords, coarse_topic, coherence |
| `04_centroids.npy`, `04_centroid_ids.json` | cluster | centroid ต่อหัวข้อ |
| `05_labels` | label | topic_id, name_th, name_en, description, keywords, cache_key (`cache_key` = sha256(model + prompt) 16 ตัวแรก; `"fallback"` เมื่อ `label.provider: "off"`) |
| `06_series` | series | topic_id, year, count, count_with_org, corpus_total, share |
| `06_topic_journal_year`, `06_topic_org_year`, `06_journal_first_year`, `06_meta.json` | series | ใช้คำนวณความกว้าง + ปีสมบูรณ์ล่าสุด |
| `07_emerging` | emerging | ดู docs/EMERGING_SPEC.md §3 + status, journal_driven, emerging_score, definition_version |
| `08_forecasts` | forecast | model, backtest_mae/mape, mase, skill_vs_naive, show, hist/fc (JSON) |
| `09_layout`, `09_edges` | layout | id, kind, x, y, r, parent · s, t, w |
| `state/embeddings/<model>/` | embed | index + shards (ถาวร) |
| `state/label_cache` | label | cache_key → ชื่อหัวข้อ |
| `state/prev/centroids.npy` | export | centroid รอบนี้ สำหรับรอบหน้า |

## 3. Output: `atlas_data.json` (สัญญากับเว็บ)

ผลิตโดย `atlas/export.py` — **ห้ามเปลี่ยน schema โดยไม่แก้ `web/src/lib/loader.ts` ตาม**

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
    "definition_version": 2,
    "assigned_articles": 198000,
    "unassigned_articles": 2003
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
      "coherence": 0.31,                // v1.1
      "forecast_uncertain": false,      // v1.1
      "forecast": {                      // null ถ้าไม่ผ่าน skill gate หรือปิด include_forecast_in_json
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
ต่อ node แบบ topic เพิ่ม: `share_growth`, `share_growth_lo`, `share_growth_hi` (ช่วงเชื่อมั่นของการโตของ share), `n_journals_R`, `n_orgs_R` (จำนวนวารสาร/สถาบันในช่วง R), `journal_driven`, `coherence`, `forecast_uncertain`
ต่อ `meta` เพิ่ม: `schema_version = "1.1"`, `definition_version = 2`, `assigned_articles`, `unassigned_articles`
`forecast` เป็น null เว้นแต่ผ่าน skill gate (`show` = true); `forecast_uncertain` = true เมื่อมี forecast แต่ไม่ผ่าน gate (เว็บจึงไม่แสดงเส้นทำนาย)

## 4. การแปลงฝั่งเว็บ (loader.normalize)

| pipeline (snake) | web (camel) | หมายเหตุ |
|---|---|---|
| `nodeId` | `id` | |
| `kind: "topic"` | `kind: "field"` | group คงเดิม |
| `nTopics` | `nFields` | |
| `emerging_score` | `emergingScore` | |
| `burst_years` | `burstYears` | |
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
| `manifest.json` | เวอร์ชัน pipeline, config emerging ที่ใช้, จำนวนต่าง ๆ — ใช้ย้อนดูว่ารอบนั้นคำนวณด้วยนิยามแบบไหน |

## 6. Data contract v2 (P1)

`pipeline/atlas/schema/contract.py` → `web/src/data/contract.schema.json` → `web/src/data/contract.ts`
สร้างด้วย `uv run atlas schema` และ `npm run gen:types` (CI ตรวจ drift ทั้งสองขั้น)
