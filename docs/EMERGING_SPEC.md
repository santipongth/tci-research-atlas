# EMERGING_SPEC — นิยาม "Emerging" ของ TCI (definition_version 3)

> **source of truth** ของนิยาม — ถ้าโค้ดกับเอกสารไม่ตรงกัน ถือเป็นบั๊ก
> Implementation: `pipeline/atlas/emerging.py` (สถานะ + score) · `pipeline/atlas/topics_time.py` (อนุกรมรายปี + ปีสมบูรณ์ล่าสุด) · `pipeline/atlas/keywords.py` (คำสำคัญเกิดใหม่, §8) · `pipeline/atlas/forecast.py` (skill gate, §9) · `pipeline/atlas/export_v2.py` (`low_data_reason`, `no_baseline`) · เว็บ: `web/src/lib/definition.ts` (§10)
> Thresholds: `config.yaml → emerging:` (ค่าดีฟอลต์ใน `pipeline/atlas/config.py` `EmergingCfg` = `pipeline/config.example.yaml` ทุกตัว — `emerging.definition_version` รับได้ค่าเดียวคือ `3`)
> Tests: `pipeline/tests/test_emerging.py`, `test_series.py`, `test_keywords.py`, `test_forecast.py` · เว็บ `web/src/lib/definitionConfig.test.ts`
> อนุมัติใช้ v2 เมื่อ 2026-10-18 (ยังไม่เคยเผยแพร่ตัวเลข v1 ต่อสาธารณะ) — v1 อยู่ในภาคผนวก
> **v3** (2026-10-18, ผู้ใช้อนุมัติ): ประมาณอัตราโตไม่ได้ = ไม่ฟันธง, ช่วงเชื่อมั่นแบบ Student-t, flag `orgs_unverified`, กฎปีสมบูรณ์ล่าสุดใหม่ — ดู "การเปลี่ยนแปลง v3" ท้ายเอกสาร

**สารบัญ:** §1 ปรัชญา · §2 หน้าต่างเวลา · §3 มิติที่วัด (+ ตัวตนวารสาร/สถาบัน) · §4 ใหญ่/เล็ก · §5 Kleinberg · §6 เกณฑ์สถานะ · §7 Score · §8 คำสำคัญเกิดใหม่ · §9 Forecast skill gate · §10 สิ่งที่เว็บแสดง · §11 ตัวอย่าง · §12 การทดสอบ · การเปลี่ยนแปลง v3 · ภาคผนวก v1

## 1. ปรัชญา
คำถามของผู้บริหาร: **"อะไรที่ยังเล็ก แต่โตเร็วอย่างมีนัยสำคัญ และโตจากหลายวารสาร/หลายสถาบัน — ที่อีก 2–3 ปีจะกลายเป็นเรื่องใหญ่?"**
ยึดกรอบ 5 คุณลักษณะของ emergence (Rotolo, Hicks & Martin 2015): ใหม่ · โตเร็ว · เกาะกลุ่ม · มีผลกระทบ · ไม่แน่นอน
- วัด **สัดส่วน (share)** ไม่ใช่จำนวนดิบ (corpus โตทุกปี)
- ทุกการ "โต/ลด" ต้อง **มีนัยสำคัญทางสถิติ** (ช่วงเชื่อมั่น) ไม่ใช่แค่ทิศทางของ noise
- ต้อง **กว้างพอ** (หลายวารสาร หลายสถาบัน) — กันหัวข้อที่ "โต" เพียงเพราะวารสารใหม่เข้าระบบ
- หัวข้อที่ข้อมูลน้อยเกินจะ **ไม่ถูกฟันธง** (`LOW_DATA`)

หน่วยของการจัดสถานะคือ **หัวข้อย่อย (fine topic)** จากขั้น cluster (`04_fine_topics`) — บทความที่ยังไม่จัดหมวด (−1) ไม่มีสถานะ แต่ถูกนับในตัวหารเสมอ

## 2. หน้าต่างเวลา
อนุกรมรายปีสร้างโดย `topics_time.build_series` จาก `02_docs` (เฉพาะบทความที่มีปี): `corpus_total` ของปี t = บทความที่มีปี t **ทั้งหมด** (จัดหมวดแล้วหรือไม่ก็ตาม) — ปีที่ไม่มีบทความในคลังเลยไม่มีแถว (ไม่ใช่ 0)

- `last_complete_year` (L) = ปีล่าสุดที่ข้อมูลสมบูรณ์ หาตามลำดับ (v3, `topics_time.last_complete_year`):
  1. ตั้ง `min_year_complete` ไว้ → ใช้ค่านั้นเลย (ไม่ตรวจอะไรต่อ; `06_meta.json → completeness.method = "configured"`)
  2. ผู้สมัคร = min(ปีล่าสุดที่มีข้อมูล, `as_of_year` − 1) — `as_of_year` = ค่าใน config; null = ปีปฏิทินของ `snapshot_at` ที่ขั้น cluster บันทึกไว้ใน `04_topics_meta.json` (รันต่อภายหลังก็ยังเป็นปีเดิม; ไม่มีบันทึก = วันนี้) — **ปีที่กำลังดำเนินอยู่ไม่ถือว่าครบเสมอ** และบทความที่ลงวันที่ล่วงหน้า (ฉบับปีหน้า) ไม่มีวันเป็นปีสมบูรณ์ล่าสุด
  3. backfill guard: ถ้ายอดรวมของผู้สมัคร < `backfill_min_ratio` (0.6) × median ของยอดรวมในช่วงปฏิทิน `backfill_ref_years` (3) ปีก่อนหน้าผู้สมัคร (ผู้สมัคร−3 … ผู้สมัคร−1; ปีในช่วงที่ไม่มีบทความเลยไม่มีแถวใน totals จึงไม่ถูกนับเข้า median และไม่นับเป็น 0; ถ้าไม่มีปีใดในช่วงมีข้อมูลเลย → ไม่ตัด) → ถอยไป 1 ปี ทำซ้ำได้ไม่เกิน `backfill_max_trim` (2) ครั้ง (`completeness.method = "median"`)
  4. ปีที่มีข้อมูลหลัง L ทั้งหมดบันทึกเป็น `trimmed_years` (พร้อม `as_of_year`) ใน `06_meta.json`, `atlas_data.json → meta` (legacy) และ `manifest.json` ของ contract v2 — บทความในปีเหล่านี้ยังอยู่ในคลัง (ใช้จัดหัวข้อ, ค้นหา, nowcast ของ Forecast v2) แต่ไม่ถูกใช้คำนวณแนวโน้ม
  - ถ้า `as_of_year` − 1 เก่ากว่าปีแรกของข้อมูล (ไม่มีปีใดครบได้) → `ValueError`
- หน้าต่าง (`emerging.definition_windows`, ทุกหน้าต่างจบที่ L):
  - **R** = `recent_window` (3) ปีล่าสุด = L−2 … L
  - **B** = `baseline_window` (5) ปีก่อน R = L−7 … L−3
  - **W** = `trend_window` (5) ปีล่าสุด = L−4 … L (ใช้วัดแนวโน้ม; ซ้อนกับ R ทั้งหมดและกับ B สองปี)
  - เช่น L = 2024 → R 2022–2024, B 2017–2021, W 2020–2024

## 3. มิติที่วัดต่อหัวข้อ
ข้อมูลเข้า (checkpoint ของขั้น series): `06_series` (topic_id, year, count, count_with_org, corpus_total, share), `06_topic_journal_year`, `06_topic_org_year`, `06_journal_first_year`; coherence จาก `04_topic_info`

| มิติ | วิธีคำนวณ | ความหมาย |
|---|---|---|
| `count_recent` | บทความของหัวข้อในช่วง R | ขนาดดิบ |
| `share_recent`, `share_baseline` | บทความหัวข้อ ÷ max(1, บทความทั้งหมด) ในช่วง R / B (ตัวหารรวมบทความที่ยังไม่จัดหมวด) | ขนาดสัมพัทธ์ |
| `share_ratio` | (share_R + ε) ÷ (share_B + ε), ε = 1e-12 | โตเร็วกว่าภาพรวมกี่เท่า (หัวข้อที่ไม่มีบทความใน B ได้ค่ามหาศาลโดยนิยาม; contract v2 เผยแพร่เป็น `null` + `no_baseline: true` เมื่อ `share_baseline` = 0) |
| `share_growth` (+`_lo`, `_hi`) | Poisson GLM `log E[c_t] = log N_t + a + b·(t − t̄)` บนปีใน W ที่ N_t > 0; growth = e^b − 1; ช่วง `ci_level` (0.90) = e^(b ± q·se) − 1 ด้วย quasi-Poisson SE `se·√φ`, `φ = max(1, Pearson χ²/df_resid)`; **q = Student-t (df = df_resid ของ GLM, = 3 สำหรับ W 5 ปี) เมื่อ φ > 1** (φ ประมาณจากข้อมูลเพียงไม่กี่จุด) และ q = normal เมื่อ φ = 1 (รู้ variance แบบ Poisson) — ดู §3.1 | อัตราโตต่อปีของ share พร้อมความไม่แน่นอน |
| `acceleration` | ln(1 + g_R) − ln(1 + g_B), g = `share_growth` (ค่ากลาง) ที่ fit บนปีใน R / ใน B (ฝั่งที่ประมาณไม่ได้นับเป็น 0) | เร่งตัวหรือชะลอ |
| `burst_frac`, `burst_years` | Kleinberg 2 สถานะ (§5); `burst_years` = ทุกปีที่อยู่ในสถานะ burst (คั่นด้วย `,`) | สัดส่วนปีใน R ที่ "ระเบิด" |
| `novelty` | 0.5 × (บทความของหัวข้อใน R ÷ บทความทั้งหมดของหัวข้อ) + 0.5 × (1 − min(อายุ, 15)/15), อายุ = max(0, L − ปีแรกที่ยอด ≥ max(3, 10% ของจุดสูงสุด)); ไม่มีปีใดถึงเกณฑ์ → อายุ 0 | ความใหม่ |
| `coherence` | ค่าเฉลี่ยของ (เวกเตอร์บทความ · centroid ของหัวข้อ) — cosine เฉลี่ยกับ centroid (ขั้น cluster) | หัวข้อเกาะกลุ่มชัดเจนแค่ไหน |
| `cagr_recent` | ((ปีสุดท้ายของ R + 0.5) ÷ (ปีแรกของ R + 0.5))^(1/(ปีใน R − 1)) − 1 | ใช้ใน `atlas_data.json` (legacy) เท่านั้น — ไม่ใช่เกณฑ์ |
| `n_journals_R` | จำนวน **`journal_key`** ที่มีบทความของหัวข้อในช่วง R | ความกว้างด้านวารสาร |
| `n_orgs_R` | จำนวน **`org_key`** (ไม่ว่าง) ที่มีบทความของหัวข้อในช่วง R | ความกว้างด้านสถาบัน |
| `new_journal_share` | บทความของหัวข้อใน R ที่มาจากวารสารที่ "ปรากฏครั้งแรก" ในช่วง R ÷ บทความของหัวข้อใน R (ปีแรกของวารสาร = ปีที่น้อยที่สุดของบทความที่มีปีทั้งคลัง ไม่ว่าจัดหมวดหรือไม่) | ตัวชี้ journal-entry bias |
| `journal_hhi` | Herfindahl (Σ สัดส่วน²) ของวารสารใน R | การกระจุกตัว |
| `org_coverage_R`, `orgs_unverified` | `org_coverage_R` = บทความใน R ที่มี `org_key` ≥ 1 ตัว ÷ `count_recent` (0 เมื่อ `count_recent` = 0); `orgs_unverified` = `org_coverage_R` < `breadth.min_org_coverage` (0.5) — ทุกสถานะ | ตรวจเกณฑ์สถาบันไม่ได้ (§6) |
| `large_share_threshold` | เกณฑ์ "ใหญ่" ของรอบนี้ (§4) — ค่าเดียวกันทุกแถว | |

### 3.0 ตัวตนของวารสารและสถาบัน (ข้อมูลเข้าของ `n_journals_R`, `new_journal_share`, `n_orgs_R`)
นิยามและ threshold **ไม่เปลี่ยน** แต่ค่าของข้อมูลเข้าขึ้นกับวิธีระบุตัวตน:
- **วารสาร = `journal_key`** (`registry.journal_keys`): ค่า `journal_key` ที่คลังรูปแบบ 1.0 ส่งมา หรือ `<server>:<OJS path>` จากรหัสบทความ ThaiJO (เช่น `so02:BECJournal`) หรือ `name:<ชื่อวารสารที่ normalize แล้ว 60 ตัวแรก>` สำหรับข้อมูลตาราง — ไม่ใช่ชื่อที่แสดง ชื่อไทย/อังกฤษของวารสารเดียวกันจึงไม่ทำให้นับเป็นสองฉบับหรือเป็น "วารสารใหม่"
- **สถาบัน = `org_key`** (`orgs.org_key`, คำนวณตอน ingest ต่อแถวผู้แต่ง×สังกัด): ชื่อองค์กรส่วนบนสุดของสังกัด (ตัดข้อมูลติดต่อ, พับวรรณยุกต์/ตัวพิมพ์) — สำหรับ **สังกัดภาษาไทย** ที่เป็นชื่อเครือข่าย (โทเค็นที่มีคำบอกระดับองค์กรและลงท้ายด้วย "ราชภัฏ" / "ราชมงคล" / "บรมราชชนนี" / "สิรินธร") คีย์รวมคำถัดไป (วิทยาเขต/ชื่อสถาบัน) ด้วย เช่น "มหาวิทยาลัยราชภัฏ เชียงใหม่" ≠ "มหาวิทยาลัยราชภัฏ อุดรธานี" (ยกเว้นคำถัดไปเป็นคำนำหน้าชื่อคน ตัวเลข หรือเครื่องหมาย) — ทำให้ `n_orgs_R` ของหัวข้อที่มีราชภัฏ/ราชมงคล/วพบ. หลายแห่งสูงขึ้นกว่าเดิม (เดิมรวมเป็นสถาบันเดียว)

### 3.1 เมื่อไหร่ "ประมาณ share_growth ไม่ได้" (คืน NaN ทั้ง 3 ค่า)
- ปีที่มีข้อมูล corpus (N_t > 0) < 3 ปี หรือหัวข้อไม่มีบทความเลยในหน้าต่าง
- **บทความของหัวข้อกระจุกอยู่ในปีเดียว** (ปีที่ยอด > 0 น้อยกว่า 2 ปี) — ถ้าอยู่ปีขอบ (เช่น หัวข้อเพิ่งเกิดปีสุดท้าย) MLE ของ b เป็นอนันต์ (perfect separation); ถ้าอยู่ปีกลางก็ได้ค่าจำกัดแต่ไม่มีความหมาย
- การ fit ล้มเหลวเชิงตัวเลข (`PerfectSeparationError`, `LinAlgError`, `ValueError`, `FloatingPointError`) — error ชนิดอื่นถือเป็นบั๊ก ปล่อยให้หยุดทำงาน
- ค่าไม่สมเหตุสมผล: b, b − q·se หรือ b + q·se ไม่เป็นจำนวนจำกัด หรือ |ค่า| > `max_abs_log_growth` (10 ≈ โต 22,000 เท่า/ปี) — ตรวจบนสเกล log **ก่อน** ยกกำลัง

ผลใน W → สถานะ `LOW_DATA` (§6 ข้อ 1); ผลใน R/B → `acceleration` ใช้ 0 แทนฝั่งนั้น

## 4. ขนาด "ใหญ่/เล็ก"
`large` = `share_recent` ≥ เกณฑ์ (`large_share_threshold`):
- `size.rule: quantile` (ดีฟอลต์) — เกณฑ์ = quantile `size.large_quantile` (0.75, แบบ linear interpolation ของ pandas) ของ `share_recent` ในหัวข้อที่จำแนกได้ (ไม่รวม `LOW_DATA`); ทุกหัวข้อเป็น `LOW_DATA` → เกณฑ์ = ∞ (ไม่มีหัวข้อใหญ่)
- `size.rule: absolute` — เกณฑ์ = `size.large_share` (0.015)

"เล็ก" = ไม่ใหญ่ (คำนวณกับทุกหัวข้อ แต่ `LOW_DATA` ตรวจก่อนเสมอ)

## 5. Kleinberg burst detection
รันบน **อนุกรมทั้งหมดของหัวข้อ** (ทุกปีใน `06_series` จนถึง L ไม่ใช่เฉพาะ W): อัตราปกติ p₀ = Σc ÷ ΣN, สถานะ burst คาดหวัง p₁ = min(`burst.s` (2.0) × p₀, 0.9999) (Poisson, ปรับตามขนาด corpus รายปี: λ_t = N_t·p) · ค่าเข้าสถานะ burst = `γ·ln(T)` (`burst.gamma` 1.0, T = จำนวนปี; T = 1 → γ) — รวมถึงการเริ่มปีแรกในสถานะ burst — ลงฟรี · หาเส้นทางด้วย Viterbi · ไม่มีบทความเลย → ไม่มี burst · `burst_frac` = |burst ∩ R| / |R|

## 6. เกณฑ์สถานะ (ตรวจตามลำดับ — ข้อแรกที่เข้าคือคำตอบ)
| ลำดับ | สถานะ (ชื่อที่แสดง ไทย / อังกฤษ) | เงื่อนไข (ค่าดีฟอลต์; key ใน `emerging:`) | ความหมายแบบภาษาง่าย (บรรทัดเดียว) |
|---|---|---|---|
| 1 | `LOW_DATA` ข้อมูลน้อย / Low data | `count_recent` < 30 (`min_articles_recent`) **หรือ** `share_growth` เป็น NaN (§3.1) | บทความยังน้อยเกินจะสรุป |
| 2 | `EMERGING` กำลังเกิดใหม่ / Emerging | เล็ก **และ** `share_growth_lo` **≥** 0.10 (`emerging.min_growth_lo`) **และ** `share_ratio` **≥** 1.8 (`emerging.min_share_ratio`) **และ** ความกว้างผ่าน | เล็กแต่โตเร็ว (และมาจากหลายวารสารหลายสถาบัน) |
| 3 | `WATCH` จับตา / Watch | เข้าเกณฑ์การเติบโตของข้อ 2 (รวม "เล็ก") แต่ **ความกว้างไม่ผ่าน** | โตเร็ว แต่มาจากไม่กี่วารสารหรือสถาบัน |
| 4 | `HOT` กำลังมาแรง / Hot | ใหญ่ **และ** `share_growth_lo` **>** 0 (`hot.min_growth_lo`) | ใหญ่และยังโต |
| 5 | `DECLINING` ลดลง / Declining | `share_growth_hi` **<** 0 (`declining.max_growth_hi`) **และ** `share_ratio` **≤** 0.8 (`declining.max_share_ratio`) — ไม่ขึ้นกับขนาด | สัดส่วนบทความลดลงชัดเจน |
| 6 | `STABLE` คงที่ / Stable | อื่น ๆ | ยังไม่เห็นการเปลี่ยนแปลงชัด |

**ชื่อที่แสดง (2026-10-23, web refresh):** HOT แสดงเป็น "กำลังมาแรง" (เดิม "กำลังร้อน") และ DECLINING เป็น "ลดลง" (เดิม "กำลังลดลง") ทั้งในเว็บ (`web/src/strings/common.ts` `status.*`, ความหมายบรรทัดเดียว `stat.mean.*`) และในประโยคที่ pipeline เขียน (`pipeline/atlas/narrative.py` `STATUS_TH` / `STATUS_EN` / `STATUS_MEANING_*`) — เปลี่ยนเฉพาะถ้อยคำ เงื่อนไข threshold และ `definition_version` (3) **ไม่เปลี่ยน** · รหัสสถานะ (`EMERGING` …) ใช้ในข้อมูลและเอกสารนี้เท่านั้น ข้อความสาธารณะใช้ชื่อที่แสดงเสมอ

**ความกว้างผ่าน** (`breadth:`) = `n_journals_R` ≥ 3 (`min_journals`) **และ** (`n_orgs_R` ≥ 3 (`min_orgs`) **หรือ** `orgs_unverified`) **และ** `new_journal_share` **<** 0.5 (`max_new_journal_share`)

`journal_driven` = เข้าเกณฑ์การเติบโตของข้อ 2 แต่ความกว้างไม่ผ่าน — คำนวณกับ **ทุกหัวข้อ** (ไม่ได้ตัด `LOW_DATA` ออก): ในหัวข้อที่ไม่ใช่ `LOW_DATA` ตรงกับ `WATCH` ทุกประการ แต่หัวข้อ `LOW_DATA` เพราะบทความน้อย (`count_recent` < 30) ที่อัตราโตประมาณได้และผ่านเกณฑ์การเติบโตก็ได้ `journal_driven = true` ด้วย (เช่น 4, 8, 16 เรื่องใน R จากวารสารเดียว)

`orgs_unverified` = true เมื่อเกณฑ์สถาบันถูกข้าม (ข้อมูลสังกัดใน R < `min_org_coverage`) — ไม่ลดสถานะ แต่เผยแพร่ต่อหัวข้อ (`topics.json → metrics.orgs_unverified`; legacy `atlas_data.json`) และนับรวมทุกสถานะใน `manifest.n_orgs_unverified` (legacy `meta.n_orgs_unverified`) เพื่อให้ผู้อ่านรู้ว่า EMERGING นั้นยังไม่ได้ตรวจความกว้างระดับสถาบัน

### 6.1 เหตุผลของ LOW_DATA ที่เผยแพร่ (`metrics.low_data_reason`, contract v2)
- `few_articles` — `count_recent` < `min_articles_recent` (ใช้เหตุผลนี้แม้อัตราโตจะประมาณไม่ได้ด้วย)
- `not_estimable` — บทความพอ แต่ `share_growth` เป็น NaN (§3.1)
- หัวข้อที่ไม่มีบทความในปีที่วิเคราะห์ยังมีแถว (ยอดเป็น 0 ทุกปี) จึงได้ `LOW_DATA` + `few_articles` ตามปกติ; หัวข้อที่ไม่มีแถวใน `07_emerging` เลย (checkpoint ไม่ตรงกัน) ถูกเผยแพร่เป็น `LOW_DATA` + `few_articles` พร้อม metrics ศูนย์/null

## 7. Emerging Score (0–100)
`emerging_score = 100 × Σ wᵢ · P(มิติᵢ)` — P = percentile rank (`rank(pct=True)`, ค่าเสมอกันได้อันดับเฉลี่ย) ภายในรอบรันเดียวกัน **เทียบกับทุกหัวข้อรวม `LOW_DATA`**
น้ำหนัก (`score_weights:`): growth 0.30 · acceleration 0.20 · burst 0.15 · novelty 0.15 · coherence 0.10 · breadth 0.10

| มิติ | ค่าที่จัดอันดับ | ค่าที่หายไป |
|---|---|---|
| growth | `share_growth_lo` | NaN → −1 (อันดับท้าย) |
| acceleration | `acceleration` | NaN → 0 |
| burst | `burst_frac` | — |
| novelty | `novelty` | — |
| coherence | `coherence` | NaN → median ของรอบ (ไม่มีเลย → 0) |
| breadth | ln(1 + `n_journals_R`) + ln(1 + `n_orgs_R`) | — |

`07_emerging` เรียงตาม `emerging_score` มากไปน้อย; contract v2 เผยแพร่เป็น `Topic.score` (ทศนิยม 1 ตำแหน่ง)
⚠️ ใช้ **จัดอันดับ** เท่านั้น — เทียบ score ข้ามรอบรันไม่ได้ (ใช้มิติดิบ เช่น `share_growth` ถ้าต้องการเทียบ)

## 8. คำสำคัญเกิดใหม่ (`pipeline/atlas/keywords.py` → `07_keywords` → `keywords.json`)
ระดับคำ ไม่ขึ้นกับการจัดหัวข้อ (Carley, Newman, Porter & Garner 2018) — ใช้หน้าต่าง R/B/W และ L ชุดเดียวกับ §2, ตัวหาร = `06_meta.json → totals` (บทความที่มีปีต่อปี ≤ L)
- คำ = คำสำคัญของผู้แต่ง (ไทย + อังกฤษ) รวมกลุ่มด้วย `norm_key` (ตัวพิมพ์ ช่องว่าง วรรณยุกต์หายพับรวมกัน; คีย์สั้นกว่า `keywords.min_key_length` (2) ไม่นับ); นับเป็น **จำนวนบทความต่อปี** (คำซ้ำในบทความเดียวนับครั้งเดียว); ชื่อที่แสดง = รูปที่เขียนบ่อยที่สุด
- **ผู้สมัคร** = ครบทุกข้อ: บทความใน R ≥ `min_docs_recent` (7) · สัดส่วนบทความทั้งคลัง (≤ L) ที่มีคำนี้ ≤ `max_doc_share` (0.15) (ตัดคำทั่วไป) · `share_ratio` = (c_R/N_R + ε_B) ÷ (c_B/N_B + ε_B) ≥ `novelty_min_ratio` (2.0) โดย ε_B = `smoothing_articles` (0.5) ÷ N_B · ปรากฏ ≥ `min_active_years` (3) ปีใน W (นับปีที่มีบทความ ไม่ต้องติดกัน)
- **เกิดใหม่ (`emerging`)** = ผู้สมัคร **และ** `growth_lo` (= `share_growth` ของ §3 บนปีใน W) **>** `keywords.min_growth_lo` (0.0) และเป็นจำนวนจำกัด **และ** `n_orgs_R` ≥ `keywords.min_orgs` (3) (**ไม่มี**ทางยกเว้นแบบ `orgs_unverified`) **และ** ไม่ `journal_driven`
- `journal_driven` (คำ) = `n_journals_R` < `keywords.min_journals` (3) **หรือ** `new_journal_share` ≥ `keywords.max_new_journal_share` (0.5) — วารสาร = `journal_key`, วารสารใหม่ = ปีแรก ≥ ปีแรกของ R (ตาราง `06_journal_first_year` เดียวกับหัวข้อ)
- `no_baseline` = ไม่มีบทความใน B (เผยแพร่ `share_ratio: null`); `topic_id` = หัวข้อย่อยที่พบคำนี้บ่อยที่สุดในบทความช่วง R (−1 = ไม่มี)
- เรียง: `emerging` ก่อน → `growth_lo` มากไปน้อย → `count_recent` → `key`; `keywords.json` เผยแพร่ `keywords.max_terms` (50) แถวแรก

## 9. Forecast skill gate (`pipeline/atlas/forecast.py`, Forecast v2)
นิยามสถานะไม่ใช้ forecast แต่การแสดงเส้นทำนายผูกกับนิยาม:
- หัวข้อ `LOW_DATA` **ไม่ถูกพยากรณ์เลย** (ตัดออกก่อนเข้า forecast) — ไม่มีการอ้างแนวโน้ม = ไม่มีเส้นทำนาย
- หัวข้อต้องมีประวัติ ≥ `forecast.min_history_years` (6) ปีนับจากปีแรกที่มีบทความ และคลังต้องมีปี ≥ เท่านั้น
- `show` = true เมื่อครบทุกข้อ: โมเดลที่เลือก ≠ `naive` · skill (= 1 − MAE ÷ MAE(naive) บนจุด backtest แบบ honest) **>** `forecast.min_skill` (0.0) · MASE เป็นจำนวนจำกัดและ **<** `forecast.max_mase` (1.0) · จำนวนจุด honest ≥ `forecast.min_honest_points` (3); โมเดลที่ fit ทั้งประวัติไม่ได้ → เผยแพร่เป็น `naive` และ `show = false`
- ไม่ผ่าน gate → เว็บแสดง "แนวโน้มไม่แน่นอน" (contract v2: `forecast.show = false` และอาร์เรย์ค่าทำนายว่าง; legacy `atlas_data.json`: `forecast: null` + `forecast_uncertain: true`)

## 10. สิ่งที่เว็บแสดง (`web/src/lib/definition.ts`)
contract v2 เผยแพร่เฉพาะ `manifest.definition_version`, `manifest.ci_level` และ `overview.last_complete_year` — threshold ที่เว็บพิมพ์ในข้อความกฎ (`strings/emerging.ts` `rule.*`) จึงเป็นค่าคงที่ `DEFINITION` ที่ต้องตรงกับ `pipeline/config.example.yaml` (`definitionConfig.test.ts` ตรวจทุกคู่และตรวจว่า `size.rule` = quantile, `definition_version` = 3):

| `DEFINITION` | ค่า | key ใน config |
|---|---|---|
| `emergingMinGrowthLo` | 0.1 | `emerging.emerging.min_growth_lo` |
| `emergingMinShareRatio` | 1.8 | `emerging.emerging.min_share_ratio` |
| `decliningMaxShareRatio` | 0.8 | `emerging.declining.max_share_ratio` |
| `largeQuantile` | 0.75 | `emerging.size.large_quantile` |
| `minArticlesRecent` | 30 | `emerging.min_articles_recent` |
| `minJournals` / `minOrgs` | 3 / 3 | `emerging.breadth.min_journals` / `min_orgs` |
| `maxNewJournalShare` | 0.5 | `emerging.breadth.max_new_journal_share` |
| `recentYears` / `baselineYears` / `trendYears` | 3 / 5 / 5 | `emerging.recent_window` / `baseline_window` / `trend_window` |
| `keywordMinActiveYears` | 3 | `keywords.min_active_years` |

- `windows(L)` คำนวณ R/B/W แบบเดียวกับ §2 จาก `overview.last_complete_year`; ระดับช่วงเชื่อมั่นในข้อความ = `manifest.ci_level`
- `largeShareThreshold` คำนวณเกณฑ์ "ใหญ่" ใหม่จาก `share_recent` ของหัวข้อที่ไม่ใช่ `LOW_DATA` (quantile แบบ linear เหมือน pandas) — ใช้กับแผนภาพ 4 ช่อง (portfolio) ซึ่งแบ่งตาม `share_growth` > 0 ไม่ใช่สถานะ
- `lib/breadth.ts` บอกว่าความกว้างข้อใดไม่ผ่าน (วารสาร, สถาบัน — ข้ามเมื่อ `orgs_unverified`, สัดส่วนวารสารใหม่)
- ค่าที่เว็บ**ไม่มี**เป็นค่าคงที่: `hot.min_growth_lo` และ `declining.max_growth_hi` (0 — เขียนในถ้อยคำ "มากกว่า 0" / "ก็ยังลด"), `breadth.min_org_coverage`, `burst.*`, `score_weights`, `max_abs_log_growth` — เปลี่ยนค่าเหล่านี้ต้องแก้ถ้อยคำเว็บเองด้วย (test ไม่จับ)

## 11. ตัวอย่าง (จาก `test_emerging.py`; คลังคงที่ 100,000 เรื่อง/ปี, ปี 2015–2024, L = 2024)
| หัวข้อ | ข้อมูล | ผล |
|---|---|---|
| 1 | 10/ปี (2015–19) → 15, 25 → 60, 120, 240 ใน R, 4 วารสาร 5 สถาบัน | `EMERGING` |
| 2 | เกิดปี 2022 (60, 120, 240) จากวารสารใหม่ 1 ฉบับ 1 สถาบัน | `WATCH` (journal_driven, new_journal_share = 1.0) |
| 3 | ใหญ่ 3,000/ปี โต +3%/ปี สม่ำเสมอ | `HOT` |
| 4 | 2,000/ปี ลด 15%/ปี | `DECLINING` |
| 5 | คงที่ 2,500/ปี | `STABLE` |
| 6 | 3, 5, 8 เรื่องใน R | `LOW_DATA` |
| 7 | มีบทความเฉพาะปี 2015–2016 (ไม่มีใน W) | `LOW_DATA` (ไม่ crash) |
| 8 | ข้อมูลเหมือนหัวข้อ 1 แต่วารสารเดียว | `WATCH` (journal_driven) |
| 9 | ข้อมูลเหมือนหัวข้อ 1 แต่ไม่มีข้อมูลสังกัด | `EMERGING` (`orgs_unverified` — เกณฑ์สถาบันถูกข้าม) |

## 12. การทดสอบ
`pipeline/tests/test_emerging.py` ล็อก: สถานะของทั้ง 9 สถานการณ์ (§11), flag journal_driven / orgs_unverified, ขอบเขต score, corpus 2 ปีไม่ crash, GLM คืนอัตราโตที่ฝังไว้, Kleinberg เจอ burst ที่ฝังไว้, (v3) บทความปีเดียว → NaN ไม่ใช่ตัวเลขมหาศาล, ขอบช่วงที่เกินเพดาน → NaN, error เชิงตัวเลข → NaN แต่ error อื่นหลุดออกมา, ช่วง t เมื่อ φ > 1 / normal เมื่อ φ = 1, หัวข้อเกิดปีสุดท้ายของ R หรือ B ไม่ crash และ acceleration ไม่เพี้ยน, 0 หัวข้อเขียนตารางว่างที่มีคอลัมน์ครบ — ใช้ค่าดีฟอลต์ที่ส่งมากับโค้ด (`load_config(None)`)
`pipeline/tests/test_series.py` ล็อกกฎปีสมบูรณ์ล่าสุด v3 (corpus โต 12%/ปีที่ปีล่าสุดครบ 25%, ฉบับลงวันที่ล่วงหน้า + ปีปัจจุบันไม่ครบ, ประวัติคงที่, ปีที่กำลังดำเนินอยู่ไม่ครบแม้ยอดสูง, เพดานการตัด, `min_year_complete` มีผลเหนือกว่า, `as_of_year` ก่อนข้อมูล = error, `as_of_year` มาจาก snapshot ของขั้น cluster) — ทุกเทสต์ส่ง `as_of_year` ตรง ๆ ไม่ขึ้นกับนาฬิกา
`pipeline/tests/test_keywords.py` ล็อกการพับคำ, เงื่อนไขใหม่ + ต่อเนื่อง + กว้าง + โต, สวิตช์ `keywords.enabled`, `smoothing_articles` เป็น key ของ config
`pipeline/tests/test_forecast.py` ล็อก skill gate (`min_honest_points`, หัวข้อ LOW_DATA ไม่ถูกพยากรณ์, fit ล้มเหลว → naive ไม่แสดง)
`pipeline/tests/test_e2e_synth.py` (slow): corpus สังเคราะห์ 20K เรื่อง — ต้องได้ EMERGING / WATCH / HOT / DECLINING ตามที่ฝังไว้ และไม่มี HOT/DECLINING ปลอมในหัวข้อคงที่
`pipeline/tests/test_pipeline_small.py` (slow): UMAP บน 11 ไฟล์จริง — ไม่ crash, ทุกหัวข้อ LOW_DATA, ไม่มี |share_growth| > 1e3
`web/src/lib/definitionConfig.test.ts`: ค่าคงที่ `DEFINITION` ของเว็บ = `pipeline/config.example.yaml` (§10)

แก้นิยาม = แก้เอกสารนี้ + `config.example.yaml` (+ ค่าดีฟอลต์ใน `config.py`) + `web/src/lib/definition.ts` + tests พร้อมกันเสมอ และเพิ่ม `definition_version` (ต้องแก้ `Literal[3]` ใน `EmergingCfg` และค่าดีฟอลต์ใน contract ด้วย)

## การเปลี่ยนแปลง v3 (v3 changes, 2026-10-18)
เกณฑ์สถานะ (§6), น้ำหนัก score (§7) และ threshold ทุกตัวของ v2 **คงเดิม** — v3 แก้ 4 จุดที่ทำให้ตัวเลขผิดหรือเกินจริง:
1. **share_growth ที่ประมาณไม่ได้ = NaN (→ LOW_DATA)** (§3.1) — v2 ส่งตัวเลขมหาศาล (growth ≈ 1e7, ขอบบน ≈ 1e28 ที่ถูกเผยแพร่เป็น STABLE) หรือ crash (`OverflowError`) เมื่อบทความของหัวข้อกระจุกอยู่ปีเดียว และหัวข้อที่เกิดปีสุดท้ายของ B ได้ acceleration ≈ −15 (ถูกดันลงท้ายตาราง score) · key ใหม่ `max_abs_log_growth: 10.0`
2. **ช่วงเชื่อมั่นแบบ Student-t เมื่อ overdispersed** — φ ประมาณจาก 5 จุด (df 3) แต่ v2 ใช้ quantile ปกติ z → ช่วง "90%" ครอบจริงราว 80% เมื่อข้อมูล overdispersed; v3 ใช้ `t.ppf((1+ci_level)/2, df_resid)` เมื่อ φ > 1 (กว้างขึ้น ~43% ที่ df 3) และ z เมื่อ φ = 1
3. **`orgs_unverified`** — เกณฑ์สถาบันยังถูกข้ามเมื่อข้อมูลสังกัดใน R < `breadth.min_org_coverage` (เหมือน v2) แต่ตอนนี้เปิดเผยเป็น flag ต่อหัวข้อ + จำนวนรวมใน meta/manifest
4. **ปีสมบูรณ์ล่าสุด** (§2) — v2 เทียบเฉพาะปีสุดท้ายกับ median ของทุกปีและตัดได้แค่ปีเดียว: corpus ที่โต 12%/ปีทำให้ปีที่ครบแค่ 25% ผ่านได้ และฉบับลงวันที่ล่วงหน้าทำให้ตัดแค่ปีหน้าแต่ปล่อยปีปัจจุบันที่ยังไม่ครบเข้ามา · key ใหม่ `as_of_year`, `backfill_ref_years: 3`, `backfill_max_trim: 2`; บันทึก `trimmed_years`, `as_of_year`

ส่วนที่ไม่เปลี่ยน: นิยาม `share_ratio` (= (share_R + ε) / (share_B + ε)) — หัวข้อใหม่ที่ไม่มี baseline จึงมีค่ามหาศาลโดยนิยามและผ่านเกณฑ์ ≥ 1.8 ได้ตามเจตนา (ถ้าข้อมูลพอ)

**การเปลี่ยนแปลงข้อมูลเข้าที่ไม่ใช่การเปลี่ยนนิยาม (ไม่เพิ่ม `definition_version`):** วารสารนับด้วย `journal_key` แทนชื่อวารสาร และ `org_key` แยกวิทยาเขตของราชภัฏ / ราชมงคล / บรมราชชนนี / สิรินธร (§3.0) — เปลี่ยนค่า `n_journals_R`, `new_journal_share`, `n_orgs_R` ของบางหัวข้อ ซึ่งอาจย้ายหัวข้อระหว่าง `EMERGING` ↔ `WATCH` เมื่อเทียบกับรอบที่รันก่อนการแก้นี้

## ภาคผนวก — นิยาม v1 (เลิกใช้ 2026-10-18)
EMERGING: share_R < 1.5% และ CAGR(ปีแรก–ปีสุดท้ายของ R) ≥ 25% และ share_ratio ≥ 1.8 และ count_R ≥ 30 · HOT: share_R ≥ 1.5% และ slope_share > 0 · DECLINING: share ลด 3 ปีติด · score 4 มิติ (growth 0.35, acceleration 0.25, burst 0.20, novelty 0.20)
เหตุผลที่เลิก: เกณฑ์ไม่มีความไม่แน่นอน (HOT/DECLINING ถูก noise หลอก — DECLINING พังในการทดสอบจริง), 1.5% ขึ้นกับจำนวนหัวข้อ, ไม่กันหัวข้อที่โตเพราะวารสารใหม่, novelty ไม่ทำงานในรอบแรก, burst intensity เอียงไปหาหัวข้อใหญ่
