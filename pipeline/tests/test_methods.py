"""Research-method lexicon, sample sizes and the methods step (aggregates only)."""
import json

import pandas as pd
import pytest

from atlas.config import AtlasConfig, load_config
from atlas.io_utils import read_table, write_table
from atlas.methods import (
    LEXICON_VERSION,
    METHOD_KEYS,
    detect_methods,
    methods,
    monoculture_share,
    sample_size,
    summarise_topics,
)


@pytest.mark.parametrize("text, found", [
    ("The alloy was characterised by SEM and XRD", []),                  # scanning electron microscopy
    ("We fitted the model by SEM with AMOS 24", ["sem"]),
    ("Analysis used SmartPLS", ["sem"]),
    ("CFA was run for the scale", []),
    ("Confirmatory factor analysis (CFA) of the scale", ["sem"]),
    ("Measured by means of a ruler; what it means for farmers", []),
    ("Pay rose by 12 percentage points, ร้อยละ 12 ของครัวเรือน", []),
    ("The mean score was 3.4 (mean = 3.4, SD 0.5)", ["descriptive_stats"]),
    ("ค่าเฉลี่ยและส่วนเบี่ยงเบนมาตรฐาน", ["descriptive_stats"]),
    ("การเรียนรู้เชิงลึกของผู้เรียนในห้องเรียน", []),                       # deep learning in pedagogy
    ("การเรียนรู้เชิงลึกด้วยโครงข่ายประสาทเทียม", ["ml"]),
    ("การเรียนรู้เชิงลึกด้วยโมเดลทำนาย", ["ml"]),
    ("Research and development expenditure and economic growth", []),
    ("Research and development of an innovative product prototype", ["rnd"]),
    ("การวิจัยและพัฒนาหลักสูตร", ["rnd"]),
])
def test_lexicon_is_precise(text, found):
    assert detect_methods(text) == found


def test_thai_and_english_methods_are_found_even_without_tone_marks():
    th = "การวิจัยนี้เก็บข้อมูลโดยใช้แบบสอบถาม วิเคราะห์ด้วยค่าเฉลี่ย และ t-test"
    assert detect_methods(th) == ["survey", "descriptive_stats", "inferential"]
    assert detect_methods("เป็นการวิจัยเชิงคุณภาพ ด้วยการสัมภาษณ์เชิงลึก") == ["interview", "qualitative"]
    damaged = "การวิจัยกึ่งทดลอง" + " " + "กลุ" + "มตัวอย" + "าง"            # tone marks lost in the PDF
    assert "experiment" in detect_methods(damaged)
    assert detect_methods("A quasi-experimental design with structural equation modelling (SEM)") == [
        "experiment", "sem"]
    assert detect_methods("Meaning-making in Thai poetry") == []           # "mean" only as a whole word
    assert len(LEXICON_VERSION) == 8 and "survey" in METHOD_KEYS


@pytest.mark.parametrize("text, n", [
    ("กลุ่มตัวอย่าง ได้แก่ นักเรียน จำนวน 400 คน", 400),
    ("กลุ" + "มตัวอย" + "าง 1,250 คน", 1250),
    ("ผู้ให้ข้อมูลสำคัญ 12 ราย", 12),
    ("data from 385 respondents were analysed", 385),
    ("a sample of 220 nurses", 220),
    ("n = 64", 64),
    ("the sample in 2019 was large", None),                   # a year is not a sample size
    ("กลุ่มตัวอย่างในปี 2562", None),                         # no unit → not read
    ("no numbers here", None),
    ("กลุ่มตัวอย่างจากโรงเรียน 5 แห่ง จำนวน 400 คน", 400),     # a place count is not the sample
    ("กลุ่มตัวอย่าง 12 ชุด จำนวน 300 ราย", 300),
    ("participants aged 18 to 25; 400 participants", 400),
    ("the sample was followed for 12 months across 400 households", 400),   # unit-bearing beats first-in-text
    ("participants aged 18 were recruited", None),
    ("sample size 24 months", None),
    ("n = 2.5", None),
    ("นักเรียนจำนวน 400 คน", 400),
    ("ตัวอย่าง 400 คน", 400),
    ("ประชากรจำนวน 10,000 คน", None),                              # a population, not a sample
])
def test_sample_size(text, n):
    assert sample_size(text) == n


def test_sample_size_takes_the_first_mention_and_respects_the_maximum():
    assert sample_size("n = 30 ... later 400 respondents") == 30
    assert sample_size("n = 5000000") is None
    assert sample_size("n = 5000000", max_size=10_000_000) == 5_000_000


def test_monoculture_share_counts_articles_using_only_the_listed_methods():
    m = pd.Series(["survey; descriptive_stats", "survey", "survey; inferential", "", "interview"])
    assert monoculture_share(m, ["survey", "descriptive_stats"]) == pytest.approx(2 / 4)
    assert monoculture_share(pd.Series(["", ""]), ["survey"]) is None


def test_topic_summary_skips_small_topics_and_reports_sample_sizes():
    cfg = load_config(None)["methods"] | {"min_articles": 3}
    am = pd.DataFrame({
        "article_id": list("abcdef"), "year": pd.array([2020, 2021, 2022, 2022, 2015, 2022], dtype="Int64"),
        "topic_id": [1, 1, 1, 1, 1, 2], "methods": ["survey; descriptive_stats", "survey", "interview", "", "survey",
                                                   "survey"],
        "sample_size": pd.array([400, 200, None, None, 50, 10], dtype="Int64")})
    s = summarise_topics(am, 2020, 2022, cfg)
    assert s["topic_id"].tolist() == [1]                     # topic 2 has 1 article; 2015 is outside the window
    row = s.iloc[0]
    assert row["articles"] == 4 and row["with_methods"] == 3 and row["coverage"] == pytest.approx(0.75)
    assert json.loads(row["counts"]) == {"survey": 2, "interview": 1, "descriptive_stats": 1}
    assert row["ss_n"] == 2 and row["ss_median"] == 300
    assert row["monoculture_share"] == pytest.approx(2 / 3) and bool(row["monoculture"]) is True


def test_unknown_monoculture_method_is_a_config_error():
    with pytest.raises(ValueError, match="monoculture_methods"):
        AtlasConfig.model_validate({"methods": {"monoculture_methods": ["questionnaires"]}})


def test_methods_step_writes_aggregates_and_never_the_text(tmp_path):
    cfg = load_config(None)
    cfg["pipeline"].update(work_dir=str(tmp_path))
    cfg["methods"]["min_articles"] = 2
    docs = pd.DataFrame({"article_id": ["a", "b", "c"], "year": pd.array([2023, 2024, None], dtype="Int64"),
                         "title_th": ["", "", ""], "title_en": ["", "", ""],
                         "abstract_th": ["ใช้แบบสอบถามกับกลุ่มตัวอย่าง 300 คน", "การสัมภาษณ์เชิงลึก", "แบบสอบถาม"],
                         "abstract_en": ["", "", ""]})
    write_table(docs, tmp_path / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": ["a", "b", "c"], "fine_topic": [4, 4, -1]}),
                tmp_path / "04_fine_topics.parquet")
    (tmp_path / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024, "years": [2023, 2024]}),
                                           encoding="utf-8")
    (tmp_path / "12_methods_notes.parquet").write_text("stale", encoding="utf-8")
    methods(cfg)
    arts = read_table(tmp_path / "12_methods_articles.parquet")
    assert set(arts.columns) == {"article_id", "year", "topic_id", "methods", "sample_size"}
    assert arts.set_index("article_id").loc["a", "sample_size"] == 300
    meta = json.loads((tmp_path / "12_methods_meta.json").read_text(encoding="utf-8"))
    assert meta["window"] == [2020, 2024] and meta["with_methods"] == 2
    assert meta["by_year"]["years"] == [2023, 2024] and meta["by_year"]["shares"]["survey"] == [1.0, 0.0]
    assert read_table(tmp_path / "12_methods_topics.parquet")["topic_id"].tolist() == [4]
    assert not (tmp_path / "12_methods_notes.parquet").exists()
    cfg["methods"]["enabled"] = False
    methods(cfg)
    assert not (tmp_path / "12_methods_topics.parquet").exists()


# ---------------------------------------------------------------- optional LLM notes (topic level only)
class FakeNoter:
    model_id = "fake-noter"

    def __init__(self, invent: bool = False):
        self.prompts, self.invent = [], invent
        self.model_id = "fake-inventor" if invent else "fake-noter"       # another model → no cache hit

    def chat(self, messages):
        from atlas.llm import Reply

        p = messages[0]["content"]
        self.prompts.append(p)
        out = ({"th": "ใช้แบบสอบถาม 99%", "en": "99% use questionnaires"} if self.invent else
               {"th": "บทความส่วนใหญ่ใช้แบบสอบถาม (100%)", "en": "Most articles use questionnaires (100%)"})
        return Reply(json.dumps(out, ensure_ascii=False), 0, 0, 0.0)


def _notes_work(tmp_path):
    cfg = load_config(None)
    cfg["pipeline"].update(work_dir=str(tmp_path / "w"), state_dir=str(tmp_path / "s"), release="2026Q4")
    work = tmp_path / "w"
    work.mkdir()
    cfg["methods"]["min_articles"] = 2
    docs = pd.DataFrame({"article_id": ["a", "b", "c", "old"], "year": pd.array([2023, 2024, 2024, 2005], dtype="Int64"),
                         "title": ["เรื่อง ก", "เรื่อง ข", "เรื่อง ค", "เรื่อง โบราณ"], "title_th": [""] * 4,
                         "title_en": [""] * 4, "abstract_th": ["ใช้แบบสอบถาม", "ใช้แบบสอบถาม", "แบบสอบถาม", "x"],
                         "abstract_en": [""] * 4})
    write_table(docs, work / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": ["a", "b", "c", "old"], "fine_topic": [4, 4, 4, 4]}),
                work / "04_fine_topics.parquet")
    write_table(pd.DataFrame({"level": ["fine"], "topic_id": [4], "name_th": ["การสำรวจความพึงพอใจ"],
                              "name_en": ["Satisfaction surveys"], "description": [""], "keywords": [""],
                              "cache_key": [""], "label_source": ["keywords"]}), work / "05_labels.parquet")
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024, "years": [2023, 2024]}),
                                       encoding="utf-8")
    return cfg, work


def test_notes_are_off_by_default_and_grounded_when_on(tmp_path):
    from atlas.llm_runner import JOBS

    cfg, work = _notes_work(tmp_path)
    methods(cfg)
    assert not (work / "12_methods_notes.parquet").exists()          # provider off → no LLM, no notes
    methods(cfg, llm=FakeNoter())
    notes = read_table(work / "12_methods_notes.parquet")
    assert notes.loc[0, "source"] == "llm" and "100%" in notes.loc[0, "th"]
    meta = json.loads((work / "12_methods_meta.json").read_text(encoding="utf-8"))
    assert meta["llm"]["task"] == "methods" and meta["llm"]["items"] == 1
    noter = FakeNoter(invent=True)
    methods(cfg, llm=noter)
    notes = read_table(work / "12_methods_notes.parquet")
    assert notes.loc[0, "source"] == "template" and "99" not in notes.loc[0, "th"]
    assert "บทความเรื่อง" not in noter.prompts[0] and "เรื่อง ก" in noter.prompts[0]   # titles only, never abstracts
    assert "เรื่อง โบราณ" not in noter.prompts[0]                      # titles come from the window the facts describe
    assert "methods" in JOBS


def test_meta_is_written_before_the_llm_notes_so_a_failed_run_keeps_it(tmp_path, monkeypatch):
    import atlas.methods as m

    cfg, work = _notes_work(tmp_path)

    def boom(cfg, llm=None):
        raise RuntimeError("endpoint down")

    monkeypatch.setattr(m, "method_notes", boom)
    with pytest.raises(RuntimeError):
        methods(cfg, llm=FakeNoter())
    meta = json.loads((work / "12_methods_meta.json").read_text(encoding="utf-8"))
    assert meta["lexicon_version"] == LEXICON_VERSION and "llm" not in meta
