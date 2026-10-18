"""Synthetic ThaiJO-style Markdown corpus with planted trends — for tests, CI and demos.

`generate(out_dir, n, seed)` writes one .md per article in the exact ThaiJO scrape layout
plus `_truth.csv` (article_id, topic, role, journal, year). Planted roles:

  emerging   small topic exploding in the recent window      → must become EMERGING
  confound   topic that exists only because a NEW journal joined in the recent window
             (looks emerging, single journal)                 → must become WATCH
  hot        large topic with rising share                    → must become HOT
  declining  topic whose share falls ~30%/year since 2018     → must become DECLINING
  stable     background topics

Data-quality quirks are injected on purpose: lost dates (1970-01-01 + year in DOI),
Thai PUA glyphs, English-only articles, self-citation-only references, duplicate files.
Every abstract uses all six topic terms so each planted topic forms one coherent cluster.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

YEARS = list(range(2012, 2026))      # 2025 is a partial year (the backfill guard must drop it)
PARTIAL_YEAR, PARTIAL_FACTOR = 2025, 0.4

TOPICS = [
    ("genai_edu", "emerging",
     ["ปัญญาประดิษฐ์เชิงสร้างสรรค์", "แชตจีพีที", "การเรียนรู้ด้วยเอไอ", "โมเดลภาษาขนาดใหญ่", "จริยธรรมเอไอ", "การประเมินงานเขียน"],
     ["generative AI", "ChatGPT", "AI-assisted learning", "large language model", "AI ethics", "writing assessment"]),
    ("buddhist_media", "confound",
     ["พุทธศาสนา", "สื่อธรรมะออนไลน์", "พระสงฆ์", "การเผยแผ่ศาสนา", "วัด", "ศีลธรรม"],
     ["Buddhism", "online dharma media", "monks", "religious propagation", "temple", "morality"]),
    ("elderly_care", "hot",
     ["ผู้สูงอายุ", "การดูแลระยะยาว", "ภาวะพึ่งพิง", "สังคมสูงวัย", "ผู้ดูแล", "คุณภาพชีวิตผู้สูงอายุ"],
     ["older adults", "long-term care", "dependency", "aging society", "caregivers", "quality of life"]),
    ("print_media", "declining",
     ["หนังสือพิมพ์", "สื่อสิ่งพิมพ์", "การอ่านหนังสือพิมพ์", "นิตยสาร", "ยอดจำหน่าย", "บรรณาธิกรณ์"],
     ["newspaper", "print media", "newspaper reading", "magazine", "circulation", "editing"]),
    ("tourism", "stable",
     ["การท่องเที่ยวชุมชน", "นักท่องเที่ยว", "โฮมสเตย์", "แหล่งท่องเที่ยว", "มัคคุเทศก์", "การตลาดท่องเที่ยว"],
     ["community-based tourism", "tourists", "homestay", "destination", "tour guide", "tourism marketing"]),
    ("rice_farming", "stable",
     ["ข้าว", "เกษตรกร", "ผลผลิตข้าว", "ปุ๋ยอินทรีย์", "นาข้าว", "โรคข้าว"],
     ["rice", "farmers", "rice yield", "organic fertilizer", "paddy field", "rice disease"]),
    ("sme_ecommerce", "stable",
     ["วิสาหกิจขนาดกลางและขนาดย่อม", "พาณิชย์อิเล็กทรอนิกส์", "ร้านค้าออนไลน์", "การชำระเงิน", "ผู้ประกอบการ", "ช่องทางจำหน่าย"],
     ["SMEs", "e-commerce", "online store", "e-payment", "entrepreneurs", "distribution channel"]),
    ("nursing_edu", "stable",
     ["นักศึกษาพยาบาล", "การฝึกปฏิบัติการพยาบาล", "สมรรถนะพยาบาล", "หอผู้ป่วย", "การสอนทางคลินิก", "วิชาชีพพยาบาล"],
     ["nursing students", "clinical practicum", "nursing competency", "ward", "clinical teaching", "nursing profession"]),
    ("diabetes", "stable",
     ["เบาหวาน", "ระดับน้ำตาลในเลือด", "ผู้ป่วยเบาหวาน", "การควบคุมอาหาร", "ภาวะแทรกซ้อน", "อินซูลิน"],
     ["diabetes", "blood glucose", "diabetic patients", "diet control", "complications", "insulin"]),
    ("local_gov", "stable",
     ["องค์กรปกครองส่วนท้องถิ่น", "การมีส่วนร่วมของประชาชน", "ธรรมาภิบาล", "เทศบาล", "งบประมาณท้องถิ่น", "การกระจายอำนาจ"],
     ["local government", "public participation", "good governance", "municipality", "local budget", "decentralization"]),
    ("math_learning", "stable",
     ["การจัดการเรียนรู้คณิตศาสตร์", "ผลสัมฤทธิ์ทางการเรียน", "นักเรียนมัธยม", "แบบฝึกทักษะ", "การแก้โจทย์ปัญหา", "เจตคติต่อคณิตศาสตร์"],
     ["mathematics learning", "learning achievement", "secondary students", "skill exercises", "problem solving", "attitude toward mathematics"]),
    ("water_quality", "stable",
     ["คุณภาพน้ำ", "แหล่งน้ำ", "โลหะหนัก", "น้ำเสีย", "การบำบัดน้ำ", "ลุ่มน้ำ"],
     ["water quality", "water sources", "heavy metals", "wastewater", "water treatment", "watershed"]),
    ("herbal_medicine", "stable",
     ["สมุนไพร", "สารสกัด", "ฤทธิ์ต้านอนุมูลอิสระ", "การแพทย์แผนไทย", "ตำรับยา", "พืชสมุนไพร"],
     ["herbal medicine", "extract", "antioxidant activity", "Thai traditional medicine", "formulation", "medicinal plants"]),
    ("hrm", "stable",
     ["การบริหารทรัพยากรมนุษย์", "ความผูกพันต่อองค์กร", "แรงจูงใจในการทำงาน", "พนักงาน", "ความพึงพอใจในงาน", "การลาออก"],
     ["human resource management", "organizational commitment", "work motivation", "employees", "job satisfaction", "turnover"]),
    ("thai_literature", "stable",
     ["วรรณกรรมไทย", "วรรณคดี", "กวีนิพนธ์", "นวนิยาย", "ภาษาถิ่น", "คติชน"],
     ["Thai literature", "classical literature", "poetry", "novels", "dialect", "folklore"]),
    ("energy", "stable",
     ["พลังงานแสงอาทิตย์", "เซลล์แสงอาทิตย์", "การประหยัดพลังงาน", "พลังงานทดแทน", "ไฟฟ้า", "ชีวมวล"],
     ["solar energy", "photovoltaic", "energy saving", "renewable energy", "electricity", "biomass"]),
]

JOURNALS = ["jedu", "nursingjournal", "jhealth", "jsoc", "jmgt", "jagri", "jsci", "jhum",
            "jtour", "jpolsci", "jcomm", "jeng"]
NEW_JOURNAL = "jnewbuddhist"          # joins ThaiJO in 2022 — the confound
INSTITUTIONS = [
    ("มหาวิทยาลัยนเรศวร", "Naresuan University"),
    ("จุฬาลงกรณ์มหาวิทยาลัย", "Chulalongkorn University"),
    ("มหาวิทยาลัยเชียงใหม่", "Chiang Mai University"),
    ("มหาวิทยาลัยขอนแก่น", "Khon Kaen University"),
    ("มหาวิทยาลัยราชภัฏเชียงราย", "Chiang Rai Rajabhat University"),
    ("มหาวิทยาลัยเทคโนโลยีราชมงคลล้านนา", "Rajamangala University of Technology Lanna"),
    ("มหาวิทยาลัยสงขลานครินทร์", "Prince of Songkla University"),
    ("มหาวิทยาลัยมหิดล", "Mahidol University"),
]
ROLES = ["", "", "อาจารย์ ", "ผู้ช่วยศาสตราจารย์ ", "รองศาสตราจารย์ ", "นักศึกษาปริญญาโท ", "นิสิตปริญญาเอก "]
FIRST = ["สมชาย", "สุดา", "วิภา", "ประเสริฐ", "กมล", "อรทัย", "ธนา", "จิราพร", "ณัฐ", "พิมพ์ชนก"]
LAST = ["ใจดี", "ศรีสุข", "ทองดี", "แก้วมณี", "บุญมา", "วงศ์ไทย", "สายทอง", "ประเสริฐศรี"]
METHODS_TH = ["โดยใช้แบบสอบถามกับกลุ่มตัวอย่าง", "ด้วยการสัมภาษณ์เชิงลึก", "เป็นการวิจัยกึ่งทดลอง",
              "วิเคราะห์ข้อมูลด้วยสถิติ t-test และ ANOVA", "เป็นการวิจัยเชิงคุณภาพ", "ใช้การวิเคราะห์สมการโครงสร้าง"]
METHODS_EN = ["using a questionnaire survey", "through in-depth interviews", "with a quasi-experimental design",
              "analysed with t-test and ANOVA", "as qualitative research", "using structural equation modelling"]
PUA_MAI_THO = chr(0xF70B)


def _share_profile(role: str, year: int) -> float:
    """Share of the year's corpus for planted topics (background topics fill the rest)."""
    if role == "emerging":
        return {2022: 0.005, 2023: 0.011, 2024: 0.024, 2025: 0.03}.get(year, 0.0008)
    if role == "confound":
        return {2022: 0.007, 2023: 0.012, 2024: 0.016, 2025: 0.02}.get(year, 0.0)
    if role == "hot":               # share +7%/year — statistically clear even with Poisson noise
        return 0.05 * 1.07 ** (year - YEARS[0])
    if role == "declining":         # flat, then falls ~30%/year — survives topic fragmentation
        return 0.06 * 0.7 ** max(0, year - 2018)
    raise ValueError(role)


def yearly_counts(n: int, seed: int) -> pd.DataFrame:
    """Deterministic topic × year article counts summing to ≈ n (corpus grows 5%/year)."""
    rng = np.random.default_rng(seed)
    units = np.array([1.05 ** i * (PARTIAL_FACTOR if y == PARTIAL_YEAR else 1.0) for i, y in enumerate(YEARS)])
    volume = units / units.sum() * n
    background = [t for t in TOPICS if t[1] == "stable"]
    bg_weight = rng.uniform(0.7, 1.3, len(background))
    rows = []
    for y, vol in zip(YEARS, volume):
        planted = {t[0]: _share_profile(t[1], y) for t in TOPICS if t[1] != "stable"}
        rest = 1.0 - sum(planted.values())
        w = bg_weight * rng.uniform(0.97, 1.03, len(background))
        shares = {**planted, **{t[0]: rest * wi / w.sum() for t, wi in zip(background, w)}}
        for key, sh in shares.items():
            rows.append({"topic": key, "year": y, "count": int(round(sh * vol))})
    return pd.DataFrame(rows)


def _sentence_th(rng, a, b):
    return rng.choice([f"งานวิจัยนี้มีวัตถุประสงค์เพื่อศึกษา{a}และ{b}",
                       f"ผลการวิจัยพบว่า{a}มีความสัมพันธ์กับ{b}อย่างมีนัยสำคัญ",
                       f"ข้อเสนอแนะคือควรส่งเสริม{a}ร่วมกับการพัฒนา{b}",
                       f"การศึกษา{a}ในบริบทของ{b}ยังมีอยู่จำกัด"])


def _sentence_en(rng, a, b):
    return rng.choice([f"This study examines {a} and {b}.",
                       f"Results show that {a} is significantly related to {b}.",
                       f"We recommend strengthening {a} together with {b}.",
                       f"Research on {a} in the context of {b} remains limited."])


def _article_md(rng, idx, topic, year, journal, host) -> tuple[str, str]:
    _key, _role, th, en = topic
    art_id = 100000 + idx
    article_id = f"{host}:{journal}:{art_id}"
    a_th, b_th = rng.choice(th, 2, replace=False)
    a_en, b_en = rng.choice(en, 2, replace=False)
    title_th = f"{a_th}กับ{b_th}: กรณีศึกษาที่ {idx}"
    title_en = f"{a_en.capitalize()} and {b_en}: case study {idx}"
    pth, pen = rng.permutation(th), rng.permutation(en)
    abs_th = " ".join([_sentence_th(rng, pth[i], pth[i + 1]) for i in (0, 2, 4)] + [str(rng.choice(METHODS_TH))])
    abs_en = " ".join([_sentence_en(rng, pen[i], pen[i + 1]) for i in (0, 2, 4)]
                      + [f"The study was conducted {rng.choice(METHODS_EN)}."])
    if rng.random() < 0.02:                                   # PDF glyph corruption
        abs_th = abs_th.replace("\N{THAI CHARACTER MAI THO}", PUA_MAI_THO)
    english_only = rng.random() < 0.05
    has_doi = rng.random() < 0.7
    doi = f"10.14456/{journal}.{year}.{idx % 50 + 1}" if has_doi else ""
    published = f"{year}-{rng.integers(1, 13):02d}-{rng.integers(1, 29):02d}"
    if has_doi and rng.random() < 0.04:                       # scrape lost the date
        published = "1970-01-01"
    authors = []
    for _ in range(int(rng.integers(1, 4))):
        inst_th, inst_en = INSTITUTIONS[int(rng.integers(len(INSTITUTIONS)))]
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        authors.append(f"- {name} ({rng.choice(ROLES)}คณะวิชาการ {inst_th} (Faculty, {inst_en}))")
    kw = list(rng.choice(th, 3, replace=False)) + list(rng.choice(en, 3, replace=False))
    if english_only:
        h1, kw = title_en, kw[3:]
        abstract = abs_en
    else:
        h1 = title_th
        abstract = f"{abs_th}   {title_en}   {abs_en}"
    if doi:
        abstract += f"      DOI:   http://dx.doi.org/{doi}"
    refs = []
    if rng.random() < 0.3:                                    # how-to-cite of the article itself
        refs.append(f"- {authors[0][2:].split(' (')[0]}. ({year + 543}). {h1}. วารสาร{journal}, 1(1), 1-10.")
    else:
        for r in range(int(rng.integers(0, 7))):
            ry = int(rng.integers(1995, year + 1))
            refs.append(f"- Author{r}, A. ({ry}). A reference about {rng.choice(en)}. Journal of Studies, {r + 1}(2), 10-20.")
    lines = [f"# {h1}", "", f"**Journal:** {journal}", f"**Published:** {published}",
             f"**Pages:** {idx % 90 + 1}-{idx % 90 + 12}",
             f"**Article URL:** https://{host}.tci-thaijo.org/index.php/{journal}/article/view/{art_id}",
             f"**Issue URL:** https://{host}.tci-thaijo.org/index.php/{journal}/issue/view/{year * 10 + idx % 3}",
             "", "**Authors:**", *authors, "", f"**Keywords:** {', '.join(kw)}", "", "## Abstract", "", abstract]
    if refs:
        lines += ["", "## References", *refs]
    return article_id, "\n".join(lines) + "\n"


def generate(out_dir: str | Path, n: int = 20_000, seed: int = 7) -> pd.DataFrame:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    counts = yearly_counts(n, seed)
    by_key = {t[0]: t for t in TOPICS}
    home = {t[0]: list(rng.choice(JOURNALS, 4, replace=False)) for t in TOPICS}
    truth, idx = [], 0
    for row in counts.itertuples(index=False):
        topic = by_key[row.topic]
        for _ in range(row.count):
            journal = NEW_JOURNAL if topic[1] == "confound" else str(rng.choice(home[row.topic]))
            host = f"so0{idx % 6 + 1}"
            article_id, md = _article_md(rng, idx, topic, row.year, journal, host)
            (out / f"{article_id.replace(':', '_')}.md").write_text(md, encoding="utf-8")
            if rng.random() < 0.01:                           # duplicate scrape of the same article
                (out / f"{article_id.replace(':', '_')}_dup.md").write_text(md, encoding="utf-8")
            truth.append({"article_id": article_id, "topic": row.topic, "role": topic[1],
                          "journal": journal, "year": row.year})
            idx += 1
    df = pd.DataFrame(truth)
    df.to_csv(out / "_truth.csv", index=False, encoding="utf-8")
    return df
