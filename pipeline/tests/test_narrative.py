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
                                                   "totals": {str(y): 1000 for y in range(2015, 2025)},
                                                   "n_articles": 10_500}),
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
    # the headline names the ANALYSED count (complete years) and says so — the KPI tile shows the whole corpus
    assert "วิเคราะห์ 10,000 บทความ" in brief["headline_th"] and "2015–2024" in brief["headline_th"]
    assert "10,000 articles analysed" in brief["headline_en"]
    from atlas.narrative import brief_job

    facts = brief_job(cfg).items[0].prompt
    assert "บทความที่นำมาวิเคราะห์" in facts and "10,000" in facts and "10,500" in facts and "ทั้งคลัง" in facts
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


def test_word_form_multiples_and_fractions_are_rejected():
    facts = "- สัดส่วน: 1.20% → 3.60% (3.0 เท่า)\n- 12 วารสาร"
    for bad in ["โตเป็นสองเท่า", "เพิ่มเป็นสองเท่าตัว", "grew many fold", "doubled in size", "halved", "twice as big",
                "เติบโตหลายเท่า", "เหลือครึ่งหนึ่ง", "a tenfold rise", "share fell by ½", "สิบเท่า"]:
        assert grounding_error([bad], facts, []) is not None, bad
    assert grounding_error(["โตเป็นสามเท่า", "tripled"], facts, []) is None            # 3 is in the facts


RATIO_FACTS = ("- สัดส่วนของบทความทั้งหมด: ช่วงฐาน 2017–2021 (5 ปี) = 1.00% → ช่วงล่าสุด 2022–2024 (3 ปี) = 1.30% "
               "(1.3 เท่า)\n- บทความช่วง 2022–2024 (3 ปี): 240 เรื่อง จาก 12 วารสาร 30 สถาบัน")


def test_a_multiple_must_be_a_ratio_fact_never_a_window_length_or_count():
    # reviewer probes on a 1.3× topic: 3 and 5 are window lengths, 12/240 are counts — none is a ratio
    for bad in ["the share tripled", "สัดส่วนเพิ่มขึ้นสามเท่า", "สัดส่วนเพิ่มขึ้นห้าเท่า", "five times its baseline",
                "สัดส่วนเพิ่มขึ้นร้อยเท่า", "สัดส่วนเพิ่มขึ้น 5 เท่า", "3 times the baseline share", "a 12-fold rise",
                "สัดส่วนเพิ่มขึ้นสิบสองเท่า", "twenty times", "a hundredfold rise", "a thousandfold rise",
                "doubled", "double the share", "up 5x", "×3", "สัดส่วนเพิ่มขึ้นยี่สิบเท่า", "๕ เท่า",
                "สองร้อยสี่สิบเท่า", "twelve-fold", "two hundred and forty times", "many times higher"]:
        assert grounding_error([bad], RATIO_FACTS, [], growth=0.1) is not None, bad
    for good in ["สัดส่วนเพิ่มขึ้น 1.3 เท่า", "the share is about 1.3 times its baseline", "share rose 1.3x",
                 "สัดส่วนเพิ่มขึ้นหนึ่งจุดสามเท่า", "240 เรื่องจาก 12 วารสารเท่านั้น", "สัดส่วนยังเท่าเดิมในบางปี"]:
        assert grounding_error([good], RATIO_FACTS, [], growth=0.1) is None, good
    # the exact share_ratio may be passed instead of reading "(x เท่า)" from the facts: 1.27 → "1.3 times"
    assert grounding_error(["about 1.3 times"], "- 1.3", [], ratios=[1.27]) is None
    assert grounding_error(["doubled"], "- x", [], ratios=[1.96]) is None                      # 1.96 → 2.0
    assert grounding_error(["doubled"], "- x", [], ratios=[1.6]) is not None                   # never round 1.6 to 2
    assert grounding_error(["5 เท่า"], "- (5 เท่า) in a title", [], ratios=[1.3]) is not None  # only the given ratio
    # a topic's own name / keyword is not a claim ("Double burden of malnutrition")
    assert grounding_error(["Double burden of malnutrition: 1.3 times"], RATIO_FACTS, [],
                           own_terms=["Double burden of malnutrition"]) is None


def test_number_words_before_a_multiple_are_parsed():
    from atlas.narrative import multiples_in

    cases = {"สิบสองเท่า": 12, "ยี่สิบเท่า": 20, "ร้อยเท่า": 100, "สามสิบห้าเท่า": 35, "พันห้าร้อยเท่า": 1500,
             "ร้อยเอ็ดเท่า": 101, "หนึ่งจุดสามเท่า": 1.3, "twenty-five times": 25, "a hundred times": 100,
             "hundredfold": 100, "thousandfold": 1000, "tenfold": 10, "two hundred and forty times": 240,
             "tripled": 3, "quadrupling": 4, "double": 2, "twice": 2, "halved": 0.5, "2.5-fold": 2.5, "๑๒ เท่า": 12}
    for text, n in cases.items():
        assert multiples_in(text) == [n], (text, multiples_in(text))
    assert multiples_in("ร้อยละ 5 ของบทความ เท่ากับ 0.4% และเท่ากัน") == []          # percent / equality words
    assert multiples_in("published three times the year before") == [3]


def test_brief_sentences_naming_several_topics_are_checked_with_exactly_one_rate_number():
    ng = {"AI-assisted learning": 0.3, "Print media": -0.2, "Rice farming": 0.25}
    facts = "- 12 8"
    assert grounding_error(["AI-assisted learning and Print media both grew 12% per year."], facts, [],
                           named_growth=ng) is not None
    assert grounding_error(["AI-assisted learning and Rice farming grew 12% per year."], facts, [],
                           named_growth=ng) is None
    assert grounding_error(["AI-assisted learning grew 12% per year while Print media fell 8% per year."], facts, [],
                           named_growth=ng) is None                       # two rate numbers: skipped
    assert grounding_error(["AI-assisted learning and Print media grew."], facts, [], named_growth=ng) is None


def test_no_baseline_rejects_any_multiple_wording():
    facts = "- ช่วงฐาน 2017–2021 (5 ปี): ไม่มีบทความ | ช่วงล่าสุด 2022–2024 (3 ปี): 0.40%"
    for bad in ["โต 3 เท่า", "grew 3 times", "a 3-fold rise", "up 3x", "×3"]:
        assert grounding_error([bad], facts, [], no_baseline=True) is not None, bad
    assert grounding_error(["หัวข้อใหม่ที่ไม่มีฐานเปรียบเทียบ 0.4%"], facts, [], no_baseline=True) is None


def test_direction_must_match_growth():
    facts = "- 5 ปี"
    assert "direction" in grounding_error(["สัดส่วนเพิ่มขึ้น"], facts, [], growth=-0.2)
    assert "direction" in grounding_error(["shares fell"], facts, [], growth=0.3)
    assert grounding_error(["สัดส่วนลดลง", "share fell"], facts, [], growth=-0.2) is None
    assert grounding_error(["สัดส่วนลดลง"], facts, [], growth=0.005) is None        # within ±1%
    assert grounding_error(["เพิ่มเติม"], facts, [], growth=-0.2) is None            # "additionally" is not a rise
    assert grounding_error(["x"], facts, [], growth=float("nan")) is None


def test_brief_direction_per_sentence_with_one_topic():
    facts = "- AI-assisted learning, Print media 5"
    ng = {"AI-assisted learning": 0.3, "Print media": -0.2}
    assert grounding_error(["Print media share grew. AI-assisted learning share grew."], facts, [], named_growth=ng) is not None
    assert grounding_error(["AI-assisted learning share grew while Print media share fell."], facts, [], named_growth=ng) is None


def test_minor_tokenisation_case_and_nan():
    assert grounding_error(["ปี 2022,2023 และ 2024"], "- 2022 2023 2024", []) is None
    assert grounding_error(["unlike rice farming"], "- x", ["Rice farming"]) is not None
    import pandas as pd

    from atlas.narrative import brief_facts
    em = pd.DataFrame({"status": ["EMERGING"], "emerging_score": [1.0], "count_recent": [5], "share_growth": [float("nan")],
                       "share_growth_lo": [float("nan")], "share_growth_hi": [float("nan")]}, index=[1])
    lab = pd.DataFrame({"name_th": ["ก"], "name_en": ["A"]}, index=[1])
    cfg = {"emerging": {"recent_window": 3, "baseline_window": 5, "ci_level": 0.9}, "pipeline": {"work_dir": "."}}
    import json
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "06_meta.json").write_text(json.dumps({"totals": {"2024": 10}}), encoding="utf-8")
        cfg["pipeline"]["work_dir"] = d
        assert "nan" not in brief_facts(cfg, lab, em, 2024).lower()


def test_direction_false_rejects_are_gone():
    facts = "- สัดส่วน 5 ปี 12"
    up, down = 0.3, -0.2
    # neutral words / topic names / compounds never trigger
    assert grounding_error(["ช่วยลดความเสี่ยงและลดต้นทุน"], facts, [], growth=up) is None
    assert grounding_error(["งานวิจัยเรื่องการลดคาร์บอน"], facts, [], growth=up, own_terms=["การลดคาร์บอน"]) is None
    assert grounding_error(["สัดส่วนของการลดคาร์บอนอยู่ที่ 12%"], facts, [], growth=up, own_terms=["การลดคาร์บอน"]) is None
    assert grounding_error(["negative growth of the share"], facts, [], growth=down) is None
    assert grounding_error(["growth of the share is positive"], facts, [], growth=down) is None
    assert grounding_error(["เพิ่มประสิทธิภาพ และโต๊ะกลม"], facts, [], growth=down) is None
    assert grounding_error(["the dropout rate and first half"], facts, [], growth=up) is None
    # rate sentences are checked
    assert "direction" in grounding_error(["เติบโต 12% ต่อปี"], facts, [], growth=-0.12)
    assert "direction" in grounding_error(["ลดลง 10% ต่อปี"], "- 10 ปี", [], growth=0.1)
    assert "direction" in grounding_error(["The share rose."], facts, [], growth=down)
    # a non-rate sentence is not direction-checked
    assert grounding_error(["จำนวนวารสารลดลง"], facts, [], growth=up) is None
    # equality words are not multiples
    nb = "- ไม่มีฐานเปรียบเทียบ 0.4%"
    assert grounding_error(["เท่ากับ 0.4% เทียบเท่าหัวข้อใหญ่ เท่ากัน"], nb, [], no_baseline=True) is None
    assert grounding_error(["in the first half and second half"], "- x", []) is None
    assert grounding_error(["share halved"], "- x", []) is not None


def _watch_row(**over):
    row = {"status": "WATCH", "share_baseline": 0.004, "share_recent": 0.012, "share_ratio": 3.0, "share_growth": 0.3,
           "share_growth_lo": 0.15, "share_growth_hi": 0.45, "count_recent": 60, "n_journals_R": 2, "n_orgs_R": 2,
           "new_journal_share": 0.6, "orgs_unverified": False, "journal_driven": True, "emerging_score": 70.0}
    return pd.Series({**row, **over})


def test_watch_is_worded_as_a_failed_breadth_test_with_the_topic_reasons(make_cfg, tmp_path):
    from atlas.narrative import breadth_reasons, template_narrative, topic_facts

    cfg = make_cfg(tmp_path)
    lab = pd.Series({"name_th": "สื่อใหม่", "name_en": "New media", "keywords": "สื่อ; media", "description": ""})
    e = _watch_row()
    th, en = breadth_reasons(cfg, e)
    assert th == ["มาจาก 2 วารสาร (เกณฑ์ ≥ 3)", "2 สถาบัน (เกณฑ์ ≥ 3)", "บทความจากวารสารที่เพิ่งเข้าระบบ 60% (เกณฑ์ < 50%)"]
    assert en == ["from 2 journals (needs ≥ 3)", "2 institutions (needs ≥ 3)",
                  "60% of articles from journals new to the index (needs < 50%)"]
    facts = topic_facts(cfg, lab, e, None, 2024)
    assert "ไม่ผ่านเกณฑ์ความกว้าง" in facts and "มาจาก 2 วารสาร" in facts
    t = template_narrative(cfg, lab, e, 2024)
    assert "ไม่ผ่านเกณฑ์ความกว้าง" in t["th"] and "did not pass the breadth test" in t["en"]
    assert "single journal" not in t["en"] and "วารสารเดียว" not in t["th"]
    assert grounding_error([t["th"], t["en"]], facts, [], growth=0.3) is None          # every number is a fact
    # only the failed parts are named; the institution rule is not claimed when it was skipped (orgs_unverified)
    assert breadth_reasons(cfg, _watch_row(n_journals_R=5, n_orgs_R=1, orgs_unverified=True))[0] == [
        "บทความจากวารสารที่เพิ่งเข้าระบบ 60% (เกณฑ์ < 50%)"]
    assert breadth_reasons(cfg, _watch_row(new_journal_share=0.1, n_orgs_R=7))[1] == ["from 2 journals (needs ≥ 3)"]
    assert breadth_reasons(cfg, pd.Series({"status": "EMERGING", "journal_driven": False})) == ([], [])


def test_brief_words_watch_as_the_breadth_test(make_cfg, tmp_path):
    from atlas.narrative import brief_facts, template_brief

    cfg = make_cfg(tmp_path)
    work = _work(cfg)
    em = pd.DataFrame([_watch_row()], index=[3])
    em = pd.concat([em, pd.DataFrame([_watch_row(status="EMERGING", journal_driven=False)], index=[1])])
    b = template_brief(cfg, em, 2024, 10_000, 2015)
    assert any("ไม่ผ่านเกณฑ์ความกว้าง" in x for x in b["bullets_th"])
    assert any("did not pass the breadth test" in x for x in b["bullets_en"])
    from atlas.io_utils import read_table

    labels = read_table(work / "05_labels.parquet").set_index("topic_id")
    facts = brief_facts(cfg, labels, em, 2024)
    watch = [ln for ln in facts.splitlines() if "การปลูกข้าว" in ln][0]
    assert "ไม่ผ่านเกณฑ์ความกว้าง" in watch and "มาจาก 2 วารสาร" in watch
