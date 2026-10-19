"""A small hand-built work_dir for the P2 steps (journals, match).

Three journals, three topics, data to 2024:
  so02:J1  45 articles 2015–2024, topics 1 and 2, owner มหาวิทยาลัยนเรศวร (most authors), 1 Japanese co-author
  so03:J2  27 articles 2020–2024, topics 2 and 3 (topic 3 only from 2022: EMERGING, hosted by J2 alone)
  so04:J3   4 articles 2023–2024, topic 1 (low data)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from atlas.config import load_config
from atlas.io_utils import write_table
from atlas.orgs import org_key

NU = "คณะบริหารธุรกิจ มหาวิทยาลัยนเรศวร"
CU = "คณะครุศาสตร์ จุฬาลงกรณ์มหาวิทยาลัย"
TOKYO = "Graduate School of Education, University of Tokyo, Japan"
TOPIC_NAMES = {1: ("การท่องเที่ยวเชิงชุมชน", "Community-based tourism", "การท่องเที่ยว; ชุมชน; tourism"),
               2: ("การตลาดดิจิทัล", "Digital marketing", "การตลาดออนไลน์; สื่อสังคม; digital marketing"),
               3: ("ปัญญาประดิษฐ์ในการศึกษา", "AI in education", "ปัญญาประดิษฐ์; การเรียนรู้; generative AI")}
TOPIC_TEXT = {1: "การท่องเที่ยวโดยชุมชน นักท่องเที่ยว วิสาหกิจชุมชน community tourism homestay",
              2: "การตลาดออนไลน์ สื่อสังคมออนไลน์ พฤติกรรมผู้บริโภค digital marketing social media",
              3: "ปัญญาประดิษฐ์ แชตบอต การเรียนการสอน generative AI chatbot classroom"}


def _rows():
    spec = []                                             # (journal, topic, year)
    for y in range(2015, 2025):
        spec += [("so02:J1", 1, y)] * 3 + [("so02:J1", 2, y)] * (2 if y >= 2020 else 1)
    for y in range(2020, 2025):
        spec += [("so03:J2", 2, y)] * 3 + ([("so03:J2", 3, y)] * 4 if y >= 2022 else [])
    spec += [("so04:J3", 1, 2023), ("so04:J3", 1, 2023), ("so04:J3", 1, 2024), ("so04:J3", 1, 2024)]
    return spec


def make_p2_work(tmp_path: Path, release: str = "2026Q4") -> dict:
    cfg = load_config(None)
    cfg["pipeline"].update(work_dir=str(tmp_path / "work"), output_dir=str(tmp_path / "out"),
                           state_dir=str(tmp_path / "state"), release=release)
    cfg["journals"].update(min_articles=10, drift_min_articles=5)
    cfg["journals"]["special_issue_max_hosts"] = 1
    cfg["methods"]["min_articles"] = 5
    work = Path(cfg["pipeline"]["work_dir"])
    work.mkdir(parents=True, exist_ok=True)
    arts, authors, refs, fine = [], [], [], []
    for i, (jk, tid, year) in enumerate(_rows()):
        host, path = jk.split(":")
        aid = f"{host}:{path}:{1000 + i}"
        method = "ใช้แบบสอบถามกับกลุ่มตัวอย่าง 400 คน วิเคราะห์ด้วยค่าเฉลี่ย" if i % 2 else "การสัมภาษณ์เชิงลึก"
        arts.append({
            "article_id": aid, "journal_name": path, "year": year, "url": f"https://{host}.tci-thaijo.org/index.php/"
            f"{path}/article/view/{1000 + i}", "doi": f"10.1/{i}" if i % 3 else "",
            "title": f"{TOPIC_NAMES[tid][0]} กรณีที่ {i}", "title_th": f"{TOPIC_NAMES[tid][0]} กรณีที่ {i}",
            "title_en": f"{TOPIC_NAMES[tid][1]} case {i}" if i % 4 else "",
            "abstract_th": f"{TOPIC_TEXT[tid]} {method}", "abstract_en": TOPIC_TEXT[tid] if i % 2 else "",
            "keywords_th": TOPIC_NAMES[tid][2], "keywords_en": TOPIC_NAMES[tid][1] if i % 5 else "",
            "has_references": True, "self_citation_only": False, "doc_text": TOPIC_TEXT[tid]})
        aff = NU if jk == "so02:J1" and i % 4 else CU
        authors.append({"article_id": aid, "position": 0, "affiliation_th": aff, "affiliation_en": "",
                        "org_key": org_key(aff, "")})
        if i == 5:
            authors.append({"article_id": aid, "position": 1, "affiliation_th": "", "affiliation_en": TOKYO,
                            "org_key": org_key("", TOKYO)})
        refs.append({"article_id": aid, "position": 0, "lang": "th", "translated": bool(i % 2)})
        fine.append({"article_id": aid, "fine_topic": tid})
    a = pd.DataFrame(arts)
    a["year"] = a["year"].astype("Int64")
    write_table(a.drop(columns=["doc_text"]), work / "01_articles.parquet")
    write_table(pd.DataFrame(authors), work / "01_authors.parquet")
    write_table(pd.DataFrame(refs), work / "01_references.parquet")
    write_table(a, work / "02_docs.parquet")
    write_table(pd.DataFrame(fine), work / "04_fine_topics.parquet")
    write_table(pd.DataFrame([{"level": "fine", "topic_id": t, "name_th": th, "name_en": en, "description": "",
                               "keywords": kw, "cache_key": "", "label_source": "keywords"}
                              for t, (th, en, kw) in TOPIC_NAMES.items()]), work / "05_labels.parquet")
    years = list(range(2015, 2025))
    totals = {str(y): int((a["year"] == y).sum()) for y in years}
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024, "years": years, "totals": totals}),
                                       encoding="utf-8")
    write_table(pd.DataFrame({"topic_id": [1, 2, 3], "status": ["STABLE", "HOT", "EMERGING"],
                              "count_recent": [12, 21, 12]}), work / "07_emerging.parquet")
    write_table(pd.DataFrame({"s": [1, 2], "t": [2, 3], "w": [0.6, 0.7]}), work / "09_edges.parquet")
    return cfg
