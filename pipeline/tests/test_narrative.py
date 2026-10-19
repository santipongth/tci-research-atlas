import json
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.io_utils import write_table
from atlas.llm import Reply
from atlas.llm_runner import JOBS
from atlas.narrative import grounding_error, narrate, narrative_job
from atlas.pipeline import STEPS

NAMES = {1: ("การเรียนรู้ด้วย AI", "AI-assisted learning"), 2: ("สื่อสิ่งพิมพ์", "Print media"),
         3: ("การปลูกข้าว", "Rice farming"), 4: ("โมเดลภาษาขนาดใหญ่", "Large language models")}


def _work(cfg):
    """Topic 1 EMERGING, 2 DECLINING, 3 STABLE, 4 EMERGING with no baseline; data to 2024."""
    work = Path(cfg["pipeline"]["work_dir"])
    rng = np.random.default_rng(0)
    rows, fine = [], []
    for t in NAMES:
        for i in range(3):
            rows.append({"article_id": f"a{t}{i}", "title": f"บทความ {NAMES[t][1]} {i}", "doc_text": "x"})
            fine.append({"article_id": f"a{t}{i}", "fine_topic": t})
    emb = rng.normal(size=(len(rows), 8)).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    write_table(pd.DataFrame(rows), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", emb)
    write_table(pd.DataFrame(fine), work / "04_fine_topics.parquet")
    np.save(work / "04_centroids.npy", np.stack([emb[i * 3:i * 3 + 3].mean(0) for i in range(4)]))
    (work / "04_centroid_ids.json").write_text(json.dumps(list(NAMES)), encoding="utf-8")
    write_table(pd.DataFrame([{"level": "fine", "topic_id": t, "name_th": th, "name_en": en, "description": "",
                               "keywords": f"{en}; {th}", "cache_key": "x", "label_source": "llm"}
                              for t, (th, en) in NAMES.items()]), work / "05_labels.parquet")
    em = pd.DataFrame({
        "topic_id": [1, 2, 3, 4], "status": ["EMERGING", "DECLINING", "STABLE", "EMERGING"],
        "emerging_score": [80.0, 20.0, 50.0, 70.0], "count_recent": [240, 90, 300, 60],
        "share_baseline": [0.004, 0.02, 0.03, 0.0], "share_recent": [0.012, 0.008, 0.03, 0.004],
        "share_ratio": [3.0, 0.4, 1.0, 4e8], "share_growth": [0.35, -0.2, 0.0, 0.9],
        "share_growth_lo": [0.2, -0.3, -0.05, 0.4], "share_growth_hi": [0.5, -0.1, 0.05, 1.5],
        "n_journals_R": [12, 5, 20, 6], "n_orgs_R": [30, 8, 40, 9]})
    write_table(em, work / "07_emerging.parquet")
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024, "trimmed_years": [2025],
                                                   "totals": {str(y): 1000 for y in range(2015, 2025)}}),
                                       encoding="utf-8")
    write_table(pd.DataFrame([{"topic_id": 1, "show": True, "fc_years": "[2025, 2026]", "fc_mean": "[120.0, 130.0]",
                               "fc_lo80": "[100.0, 105.0]", "fc_hi80": "[140.0, 155.0]"}]),
                work / "08_forecasts.parquet")
    return work


def test_grounding_accepts_rounding_thai_digits_and_rejects_inventions():
    facts = "- สัดส่วน: 1.23% → 4.56% (3.7 เท่า)\n- บทความ 1,234 เรื่อง ช่วง 2022–2024 (3 ปี)"
    assert grounding_error(["สัดส่วนเพิ่มจาก 1.2% เป็น 4.6% ใน ๓ ปี", "1,234 articles in 2022–2024"], facts, []) is None
    assert "99" in grounding_error(["เพิ่มขึ้น 99%"], facts, [])
    assert "Rice farming" in grounding_error(["unlike Rice farming"], facts, ["Rice farming", "AI"])
    assert grounding_error(["about AI"], facts, ["AI"]) is None          # names under 4 characters are not checked


def test_templates_without_an_llm(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = _work(cfg)
    df = narrate(cfg)
    assert df["topic_id"].tolist() == [1, 4, 2] and set(df["source"]) == {"template"}   # EMERGING, then DECLINING
    by = df.set_index("topic_id")
    assert "ไม่มีบทความในช่วง" in by.loc[4, "th"] and "1.20%" in by.loc[1, "th"]
    brief = json.loads((work / "11_brief.json").read_text(encoding="utf-8"))["brief"]
    assert brief["source"] == "template" and "2024" in brief["headline_th"]
    item = {it.key: it for it in narrative_job(cfg).items}["T000004"]
    base = [ln for ln in item.prompt.splitlines() if ln.startswith("- ช่วงฐาน")][0]
    assert "ไม่มีฐานเปรียบเทียบ" in base and "เท่า" not in base


class FakeWriter:
    model_id = "fake-writer"

    def __init__(self):
        self.prompts = []

    def chat(self, messages):
        p = messages[0]["content"]
        self.prompts.append(p)
        if "headline_th" in p:
            out = {"headline_th": "หัวข้อการเรียนรู้ด้วย AI เติบโตเร็วที่สุดถึงปี 2024", "headline_en": "AI-assisted learning leads",
                   "bullets_th": ["1. มีหัวข้อกำลังเกิดใหม่ 2 หัวข้อ"], "bullets_en": ["- 2 emerging topics"]}
        elif "Print media" in p:
            out = {"th": "ลดลง 99% ต่อปี", "en": "down 99% a year"}                  # invented number
        elif "Large language models" in p:
            out = {"th": "โมเดลภาษาขนาดใหญ่เป็นหัวข้อใหม่ที่ไม่มีฐานเปรียบเทียบ", "en": "A new topic with no baseline"}
        else:
            out = {"th": "การเรียนรู้ด้วย AI โต 35% ต่อปี (ช่วงเชื่อมั่น 90%: 20% ถึง 50%)",
                   "en": "AI-assisted learning grows 35% a year (90% CI 20% to 50%)"}
        return Reply(json.dumps(out, ensure_ascii=False), 0, 0, 0.0)


def test_llm_narratives_are_grounded_or_replaced(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = _work(cfg)
    writer = FakeWriter()
    by = narrate(cfg, llm=writer).set_index("topic_id")
    assert by.loc[1, "source"] == "llm" and "35%" in by.loc[1, "th"]
    assert by.loc[4, "source"] == "llm"
    assert by.loc[2, "source"] == "template" and "99" not in by.loc[2, "th"]          # rejected twice → template
    assert sum("Print media" in p and "headline_th" not in p for p in writer.prompts) == 2   # first try + 1 regeneration
    assert any("rejected: numbers not in the facts: 99" in p for p in writer.prompts)
    saved = json.loads((work / "11_brief.json").read_text(encoding="utf-8"))
    assert saved["brief"]["source"] == "llm" and saved["brief"]["bullets_th"] == ["มีหัวข้อกำลังเกิดใหม่ 2 หัวข้อ"]
    assert set(saved["llm"]) == {"narrative", "brief"} and saved["llm"]["narrative"]["fallback"] == 1


def test_step_and_jobs_are_registered():
    assert STEPS.index("forecast") < STEPS.index("narrate") < STEPS.index("export")
    assert set(JOBS) == {"label", "merge", "narrative", "brief"}
