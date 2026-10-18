# EMERGING_SPEC — นิยาม "Emerging" ของ TCI (definition_version 2)

> **source of truth** ของนิยาม — ถ้าโค้ดกับเอกสารไม่ตรงกัน ถือเป็นบั๊ก
> Implementation: `pipeline/atlas/emerging.py` · Thresholds: `config.yaml → emerging:` · Tests: `pipeline/tests/test_emerging.py`
> อนุมัติใช้ v2 เมื่อ 2026-10-18 (ยังไม่เคยเผยแพร่ตัวเลข v1 ต่อสาธารณะ) — v1 อยู่ในภาคผนวก

## 1. ปรัชญา
คำถามของผู้บริหาร: **"อะไรที่ยังเล็ก แต่โตเร็วอย่างมีนัยสำคัญ และโตจากหลายวารสาร/หลายสถาบัน — ที่อีก 2–3 ปีจะกลายเป็นเรื่องใหญ่?"**
ยึดกรอบ 5 คุณลักษณะของ emergence (Rotolo, Hicks & Martin 2015): ใหม่ · โตเร็ว · เกาะกลุ่ม · มีผลกระทบ · ไม่แน่นอน
- วัด **สัดส่วน (share)** ไม่ใช่จำนวนดิบ (corpus โตทุกปี)
- ทุกการ "โต/ลด" ต้อง **มีนัยสำคัญทางสถิติ** (ช่วงเชื่อมั่น) ไม่ใช่แค่ทิศทางของ noise
- ต้อง **กว้างพอ** (หลายวารสาร หลายสถาบัน) — กันหัวข้อที่ "โต" เพียงเพราะวารสารใหม่เข้าระบบ
- หัวข้อที่ข้อมูลน้อยเกินจะ **ไม่ถูกฟันธง** (`LOW_DATA`)

## 2. หน้าต่างเวลา
- `last_complete_year` = ปีล่าสุดที่ข้อมูลสมบูรณ์ (backfill guard: ปีล่าสุดที่ยอดรวม < `backfill_min_ratio` × median ถูกตัด; ตั้งเองได้ด้วย `min_year_complete`)
- **R** = `recent_window` ปีล่าสุด (3) · **B** = `baseline_window` ปีก่อน R (5) · **W** = `trend_window` ปีล่าสุด (5) ใช้วัดแนวโน้ม

## 3. มิติที่วัดต่อหัวข้อ
| มิติ | วิธีคำนวณ | ความหมาย |
|---|---|---|
| `share_recent`, `share_baseline` | บทความหัวข้อ ÷ บทความทั้งหมด ในช่วง R / B (ตัวหารรวมบทความที่ยังไม่จัดหมวด) | ขนาดสัมพัทธ์ |
| `share_ratio` | share_R ÷ share_B | โตเร็วกว่าภาพรวมกี่เท่า |
| `share_growth` (+`_lo`, `_hi`) | Poisson GLM `log E[c_t] = log N_t + a + b·t` บนปีใน W; growth = e^b − 1; ช่วงเชื่อมั่น `ci_level` (90%) ด้วย quasi-Poisson SE `se·√φ`, `φ = max(1, χ²/df)` | อัตราโตต่อปีของ share พร้อมความไม่แน่นอน |
| `acceleration` | log growth ใน R − log growth ใน B | เร่งตัวหรือชะลอ |
| `burst_frac`, `burst_years` | Kleinberg 2 สถานะ (§5) | สัดส่วนปีใน R ที่ "ระเบิด" |
| `novelty` | 0.5 × สัดส่วนบทความของหัวข้อที่อยู่ใน R + 0.5 × (1 − อายุ/15), อายุ = ปีนับจากปีแรกที่ยอด ≥ max(3, 10% ของจุดสูงสุด) | ความใหม่ |
| `coherence` | cosine เฉลี่ยของบทความกับ centroid | หัวข้อเกาะกลุ่มชัดเจนแค่ไหน |
| `n_journals_R`, `n_orgs_R` | จำนวนวารสาร / สถาบันที่มีบทความในหัวข้อช่วง R | ความกว้างของชุมชน |
| `new_journal_share` | สัดส่วนบทความใน R ที่มาจากวารสารที่ปรากฏครั้งแรกในช่วง R | ตัวชี้ journal-entry bias |
| `journal_hhi` | Herfindahl ของวารสารใน R | การกระจุกตัว |

## 4. ขนาด "ใหญ่/เล็ก"
`large` = `share_recent` ≥ quantile `size.large_quantile` (0.75) ของหัวข้อที่จำแนกได้ (ไม่รวม `LOW_DATA`) — ใช้ค่าตายตัว `size.large_share` ได้ด้วย `size.rule: absolute`

## 5. Kleinberg burst detection
สถานะ burst คาดหวังอัตรา `s` × อัตราปกติ (ปรับตามขนาด corpus รายปี, Poisson) · ค่าเข้าสถานะ burst = `γ·ln(T)` (T = จำนวนปี) ลงฟรี · หาเส้นทางด้วย Viterbi · `burst_frac` = |burst ∩ R| / |R|

## 6. เกณฑ์สถานะ (ตรวจตามลำดับ — ข้อแรกที่เข้าคือคำตอบ)
| ลำดับ | สถานะ | เงื่อนไข (ค่าดีฟอลต์) |
|---|---|---|
| 1 | `LOW_DATA` ข้อมูลน้อย | count_R < 30 **หรือ** ประมาณ share_growth ไม่ได้ |
| 2 | `EMERGING` กำลังเกิดใหม่ | เล็ก **และ** `share_growth_lo` ≥ +10%/ปี **และ** `share_ratio` ≥ 1.8 **และ** ความกว้างผ่าน |
| 3 | `WATCH` จับตา | เข้าเกณฑ์การเติบโตของข้อ 2 แต่ **ความกว้างไม่ผ่าน** |
| 4 | `HOT` กำลังร้อน | ใหญ่ **และ** `share_growth_lo` > 0 |
| 5 | `DECLINING` กำลังลดลง | `share_growth_hi` < 0 **และ** `share_ratio` ≤ 0.8 |
| 6 | `STABLE` คงที่ | อื่น ๆ |

**ความกว้างผ่าน** = `n_journals_R` ≥ 3 **และ** (`n_orgs_R` ≥ 3 **หรือ** บทความใน R มีข้อมูลสังกัด < 50%) **และ** `new_journal_share` < 0.5
`journal_driven` = เข้าเกณฑ์การเติบโต แต่ความกว้างไม่ผ่าน (ตรงกับ `WATCH`)

## 7. Emerging Score (0–100)
`score = 100 × Σ wᵢ · P(มิติᵢ)` — P = percentile rank ภายในรอบรันเดียวกัน
น้ำหนัก: growth (`share_growth_lo`) 0.30 · acceleration 0.20 · burst 0.15 · novelty 0.15 · coherence 0.10 · breadth (`log(1+journals) + log(1+orgs)`) 0.10
⚠️ ใช้ **จัดอันดับ** เท่านั้น — เทียบ score ข้ามรอบรันไม่ได้ (ใช้มิติดิบ เช่น `share_growth` ถ้าต้องการเทียบ)

## 8. ตัวอย่าง (จาก tests)
| หัวข้อ | ข้อมูล | ผล |
|---|---|---|
| A | 10/ปี → 60, 120, 240 ใน R, 4 วารสาร 5 สถาบัน | `EMERGING` |
| B | เกิดปี 2022 จากวารสารใหม่ 1 ฉบับ | `WATCH` (journal_driven) |
| C | ใหญ่ โต +3%/ปี สม่ำเสมอ | `HOT` |
| D | ลด 15%/ปี | `DECLINING` |
| E | คงที่ 2,500/ปี | `STABLE` |
| F | 3, 5, 8 เรื่องใน R | `LOW_DATA` |

## 9. การทดสอบ
`pipeline/tests/test_emerging.py` ล็อก: สถานะของทั้ง 9 สถานการณ์, flag journal_driven, ขอบเขต score, corpus 2 ปีไม่ crash, GLM คืนอัตราโตที่ฝังไว้, Kleinberg เจอ burst ที่ฝังไว้
`pipeline/tests/test_e2e_synth.py` (slow): corpus สังเคราะห์ 20K เรื่อง — ต้องได้ EMERGING / WATCH / HOT / DECLINING ตามที่ฝังไว้ และไม่มี HOT/DECLINING ปลอมในหัวข้อคงที่

แก้นิยาม = แก้เอกสารนี้ + `config.example.yaml` + tests พร้อมกันเสมอ และเพิ่ม `definition_version`

## ภาคผนวก — นิยาม v1 (เลิกใช้ 2026-10-18)
EMERGING: share_R < 1.5% และ CAGR(ปีแรก–ปีสุดท้ายของ R) ≥ 25% และ share_ratio ≥ 1.8 และ count_R ≥ 30 · HOT: share_R ≥ 1.5% และ slope_share > 0 · DECLINING: share ลด 3 ปีติด · score 4 มิติ (growth 0.35, acceleration 0.25, burst 0.20, novelty 0.20)
เหตุผลที่เลิก: เกณฑ์ไม่มีความไม่แน่นอน (HOT/DECLINING ถูก noise หลอก — DECLINING พังในการทดสอบจริง), 1.5% ขึ้นกับจำนวนหัวข้อ, ไม่กันหัวข้อที่โตเพราะวารสารใหม่, novelty ไม่ทำงานในรอบแรก, burst intensity เอียงไปหาหัวข้อใหญ่
