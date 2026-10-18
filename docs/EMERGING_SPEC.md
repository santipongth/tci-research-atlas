# EMERGING_SPEC — นิยาม "Emerging" ของ TCI (ฉบับสมบูรณ์)

> เอกสารนี้คือ **source of truth** ของนิยาม — ถ้าโค้ดกับเอกสารไม่ตรงกัน ให้ถือว่าเป็นบั๊กและแจ้งทีม
> Implementation: `pipeline/atlas/emerging.py` · Thresholds: `config.yaml → emerging:` · Tests: `pipeline/tests/test_emerging.py`

## 1. ปรัชญา

"Emerging" ในบริบท TCI ต้องตอบคำถามของผู้บริหาร: **"อะไรที่เล็กแต่กำลังโตเร็วและมาใหม่ — ที่ถ้าปล่อยไว้อีก 2–3 ปีจะกลายเป็นเรื่องใหญ่?"**

ดังนั้นนิยามต้อง:
1. **วัดจากขนาดสัมพัทธ์ (share) ไม่ใช่จำนวนดิบ** — corpus โตทุกปี จำนวนดิบทำให้ทุกหัวข้อดูเหมือนโต
2. **แยก "เล็กแต่โต" (EMERGING) ออกจาก "ใหญ่และโต" (HOT)** — คนละความหมาย คนละการใช้งาน
3. **ทนกับปัญหาข้อมูลจริงของ TCI** — วารสาร backfill ย้อนหลัง, บางปียอดน้อยผิดปกติ, หัวข้อจิ๋วสุ่มผันผวน
4. **ทุก threshold ปรับได้ใน config** — ไม่ hardcode

## 2. หน้าต่างเวลา

```
|<------ B (baseline: 5 ปี) ------>|<--- R (recent: 3 ปี) --->|
2017  2018  2019  2020  2021       2022  2023  2024
                                            ↑ last_complete_year
```

- `R` = `recent_window` ปีล่าสุด**ที่ข้อมูลสมบูรณ์** (default 3)
- `B` = `baseline_window` ปีก่อน R (default 5)
- **Backfill guard**: ปีล่าสุดที่มียอดบทความรวม < 60% ของ median รายปี ถือว่าข้อมูลยังไม่ครบ → ตัดออกจากหน้าต่างวิเคราะห์ (`last_complete_year` จะถอยลง) — ป้องกัน "ทุกหัวข้อดูเหมือนลดลง" ในปีที่วารสารยังลงข้อมูลไม่เสร็จ
- บังคับผ่าน `emerging.min_year_complete` ได้ถ้าทีมต้องการกำหนดเอง

## 3. มิติที่วัด (ต่อ topic)

| มิติ | สูตร | ตีความ |
|---|---|---|
| `share_R`, `share_B` | `count_topic / count_corpus` ในช่วงนั้น | ขนาดสัมพัทธ์ (กัน corpus โต) |
| `cagr_recent` | `((c_last+0.5)/(c_first+0.5))^(1/(n−1)) − 1` | อัตราโตเฉลี่ยต่อปีในช่วง R (+0.5 คือ Laplace smoothing กัน log(0)) |
| `share_ratio` | `share_R / share_B` | โตเร็วกว่า corpus กี่เท่า |
| `slope_share` | OLS slope ของ share เทียบปี ช่วง B∪R (normalize ด้วย mean share) | ทิศทางระยะยาว |
| `acceleration` | `slope(count‖R) − slope(count‖B)` (normalize) | เร่งตัวหรือชะลอ |
| `burst_intensity` + `burst_years` | Kleinberg 2-state (ดู §4) | ช่วงที่ยอด "ระเบิด" ผิดปกติ |
| `novelty` | `1 − max cosine_sim(centroid, centroids_รอบก่อน)` | หัวข้อนี้เคยมีในรอบก่อนไหม (ไม่มีรอบก่อน → 0.5) |

## 4. Kleinberg burst detection

ตรวจ "ช่วงระเบิด" ของจำนวนบทความรายปีด้วยโมเดล automaton 2 สถานะ (ปกติ / burst):

- แต่ละปีสังเกต count ด้วย Poisson; state 1 (burst) มีอัตราสูงกว่า state 0 ตามสัดส่วน `s = 2.0`
- อัตราคาดหวังปรับตาม **ขนาด corpus ของปีนั้น** (บทความมากขึ้นทั้งระบบ ≠ burst ของหัวข้อ)
- เปลี่ยนสถานะมีค่าใช้จ่าย `γ × ln(n)` (default γ=1.0 — สูงขึ้น = หาเฉพาะ burst ที่ยาว/ชัด)
- หาเส้นทางสถานะที่ดีสุดด้วย **Viterbi** → ปีที่อยู่ใน state 1 = `burst_years`
- `burst_intensity` = สัดส่วนปีที่ burst ในช่วง R

## 5. เกณฑ์จำแนกสถานะ (เรียงลำดับ — ข้อบนมาก่อน)

| ลำดับ | สถานะ | เงื่อนไข (default) |
|---|---|---|
| 1 | **EMERGING** กำลังเกิดใหม่ | `share_R < 0.015` **และ** `cagr_recent ≥ 0.25` **และ** `share_ratio ≥ 1.8` **และ** `count_R ≥ 30` |
| 2 | **HOT** กำลังร้อน | `share_R ≥ 0.015` **และ** `slope_share > 0` |
| 3 | **DECLINING** กำลังลดลง | slope ของ share ติดลบต่อเนื่อง ≥ 3 ปีท้าย |
| 4 | **STABLE** คงที่ | ไม่เข้าเงื่อนไขใด |

เหตุผลของแต่ละ threshold:
- **`share_R < 1.5%`** — บังคับว่า emerging ต้อง "ยังเล็ก"; ถ้าใหญ่แล้วยังโตอยู่ นั่นคือ HOT ไม่ใช่ของใหม่
- **`CAGR ≥ 25%/ปี`** — การโตที่มีนัยสำคัญในหน้าต่าง 3 ปี (ต่ำกว่านี้มักเป็น noise)
- **`share_ratio ≥ 1.8`** — ต้องโตเร็วกว่า corpus เกือบ 2 เท่า กันกรณีระบบวารสารโตพาทุกอย่างโต
- **`count_R ≥ 30`** — กัน noise: หัวข้อ 5 เรื่อง → 15 เรื่อง เป็น CAGR 200% แต่ไม่มีความหมายเชิงนโยบาย

## 6. Emerging Score (0–100)

```
score = 100 × ( 0.35 × P(growth)
              + 0.25 × P(acceleration)
              + 0.20 × P(burst_intensity)
              + 0.20 × P(novelty) )
```

- `P(·)` = percentile rank ของ topic นั้น **ภายในรอบรันเดียวกัน** (rank 0–1)
- growth = `cagr_recent` ที่ clip ไว้
- score ใช้ **จัดอันดับ** หน้า Emerging Themes บนเว็บ — ไม่ใช่ค่าสัมบูรณ์
- ⚠️ เพราะเป็น percentile ภายในรอบ → **เทียบ score ข้ามรอบรันโดยตรงไม่ได้** (ถ้าต้องการเทียบข้ามรอบ ให้ใช้มิติดิบ เช่น cagr_recent, share_R)

## 7. ตัวอย่าง

| topic | share_B | share_R | CAGR_R | ratio | ผล |
|---|---|---|---|---|---|
| A: การเฝ้าระวัง PM2.5 | 0.2% | 0.9% | +55%/ปี | 4.5× | **EMERGING** (เล็ก โตเร็ว โตกว่า corpus) |
| B: โรคเบาหวาน | 4.1% | 4.8% | +6%/ปี | 1.17× | **HOT** (ใหญ่และยังโต) |
| C: การจัดการชั้นเรียนดั้งเดิม | 2.2% | 1.4% | −11%/ปี | 0.64× | **DECLINING** (share ลด 3+ ปีติด) |
| D: วิศวกรรมโครงสร้าง | 1.8% | 1.7% | +1%/ปี | 0.94× | **STABLE** |
| E: หัวข้อจิ๋ว X | 0.001% | 0.004% | +120%/ปี | 4× | STABLE — โดน `count_R ≥ 30` ตัด (มีแค่ 8 เรื่อง) |

## 8. การทดสอบ

`pipeline/tests/test_emerging.py` ล็อกพฤติกรรมสำคัญ:
- หัวข้อ synthetic ที่ออกแบบให้เข้าเงื่อนไขต้องได้ EMERGING จริง (ที่สเกล corpus 100K)
- หัวข้อใหญ่ที่โตต้องได้ HOT ไม่ใช่ EMERGING
- burst detection ต้องหา burst ที่ฝังไว้ในข้อมูลเจอ (regression test ของ Viterbi)
- backfill guard ต้องตัดปีที่ยอดตก

แก้นิยาม = แก้ spec นี้ + config.example.yaml + tests พร้อมกันเสมอ
