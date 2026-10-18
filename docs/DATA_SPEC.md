# DATA_SPEC — สเปกข้อมูลเข้า/ออก

## 1. Input: metadata บทความ TCI

ไฟล์เดียว รองรับ `.csv` / `.json` / `.jsonl` / `.parquet` — แถวละ 1 บทความ
mapping ชื่อคอลัมน์ตั้งใน `config.yaml` ที่ `input.columns` (เปลี่ยนได้ตามหน้า export จริง)

| ฟิลด์มาตรฐาน | จำเป็น | หมายเหตุ |
|---|---|---|
| `article_id` | ✅ | id เฉพาะของบทความ |
| `title_th` / `title_en` | ✅ (อย่างน้อยหนึ่ง) | ชื่อเรื่อง |
| `year` | ✅ | ปีตีพิมพ์ — รับทั้ง พ.ศ./ค.ศ. (ingest แปลงให้เป็น ค.ศ.) |
| `abstract_th` / `abstract_en` | แนะนำอย่างยิ่ง | คุณภาพ cluster/label ขึ้นกับ abstract มาก |
| `keywords_th` / `keywords_en` | แนะนำ | คั่นด้วย `;` หรือ `,` |
| `authors` | ทางเลือก | คั่นด้วย `;` (สำหรับ author network อนาคต) |
| `affiliations` | ทางเลือก | |
| `journal_name` | แนะนำ | ใช้ทำ journal view อนาคต |
| `volume` / `issue` | ทางเลือก | |
| `tci_tier` | ทางเลือก | Tier 1/2 ของ TCI ถ้ามี |
| `doi` / `url` | ทางเลือก | ลิงก์กลับไปหาบทความ |

ตรวจก่อนรัน: `python scripts/validate_input.py --config config.yaml`
(รายงานจำนวนแถว, ช่วงปี, % ฟิลด์ว่าง, แจ้งเตือนคอลัมน์หาย)

กฎความสะอาดที่ ingest ทำให้:
- ตัดแถวที่ `year` < `input.min_year` (default 2000) หรือปีเพี้ยน
- dedup: ชื่อเรื่องคล้ายกัน ≥ 95% (rapidfuzz) → เก็บ record ที่ metadata ครบกว่า
- พ.ศ. → ค.ศ. (พ.ศ. − 543) อัตโนมัติ — ตรวจจากช่วงค่า

## 2. Checkpoints กลางทาง (work_dir)

ทุก step เขียน/อ่านจาก `work_dir` (default `./work`) — ลบทิ้งแล้วรันใหม่ได้เสมอ
ไฟล์ตารางใช้ `io_utils.write_table/read_table` (parquet ถ้ามี pyarrow, ไม่งั้น pickle)

| ไฟล์ | step | คอลัมน์สำคัญ |
|---|---|---|
| `01_articles.parquet` | ingest | article_id, title, abstract, year (ค.ศ.), journal, ... |
| `02_docs.parquet` | preprocess | article_id, title, abstract, doc_text, year |
| `03_embeddings.npy` | embed | matrix (n_articles × dim) + `03_ids.json` |
| `04_topics.parquet` | cluster | article_id → topic_id (fine), coarse_topic |
| `04_topic_info.parquet` | cluster | topic_id, size, coarse_topic, top_terms |
| `04_centroids.npy` + `04_centroid_ids.json` | cluster | centroid ต่อ topic (ใช้ทำ novelty/edges) |
| `05_labels.parquet` | label | level, topic_id, name_th, name_en, description, keywords, prompt_hash |
| `06_topic_year.parquet` | series | topic_id, year, count |
| `06_meta.json` | series | last_complete_year, years, totals |
| `07_emerging.parquet` | emerging | topic_id, status, emerging_score, cagr_recent, share_recent, share_baseline, burst_years, novelty, ... |
| `08_forecasts.parquet` | forecast | topic_id, model, backtest_mape, hist_years/counts, fc_years/mean/lo/hi (JSON string) |
| `09_layout.parquet` | layout | id, kind (group/topic), parent, x, y, r |
| `09_edges.parquet` | layout | s, t, w |
| `prev/centroids.npy` | export | centroid รอบนี้ เก็บไว้ให้รอบหน้าคำนวณ novelty |

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
    "total_groups": 14
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
      "status": "EMERGING",             // EMERGING | HOT | DECLINING | STABLE
      "emerging_score": 92.5,           // 0–100 หรือ null
      "cagr_recent": 0.612,             // CAGR ช่วง R (ทศนิยม)
      "burst_years": "2022,2023",       // ปีที่ burst คั่นด้วย , หรือ ""
      "forecast": {                      // null ถ้าปิด include_forecast_in_json
        "model": "linear",              // linear | poisson | prophet
        "backtest_mape": 12.4,          // %
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
