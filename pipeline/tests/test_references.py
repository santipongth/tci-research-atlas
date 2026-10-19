"""references step (P4, D7 + R12): matching references to corpus articles, coverage gate, journal practice."""
import json

import pandas as pd

from atlas.config import load_config
from atlas.export_research import cited_counts, references_file, topic_citations
from atlas.io_utils import write_table
from atlas.pipeline import STEPS
from atlas.references import journal_practice, match_references, references
from atlas.schema import contract as C

TH_TITLE = "ประสิทธิผลของนวัตกรรมการสื่อสารการตลาดเพื่อสังคม ของกรีนพีซประเทศไทย"
EN_TITLE = "Barriers to e-commerce adoption in Thai small and medium enterprises"


def _articles():
    return pd.DataFrame([
        {"article_id": "a1", "doi": "10.14456/becj.2016.13", "title_th": TH_TITLE, "title_en": "Greenpeace study"},
        {"article_id": "a2", "doi": "10.14456/BECJ.2016.29", "title_th": "", "title_en": EN_TITLE},
        {"article_id": "a3", "doi": "", "title_th": "การศึกษาความพึงพอใจของผู้ใช้บริการห้องสมุด", "title_en": ""},
        {"article_id": "a4", "doi": "", "title_th": "การศึกษาความพึงพอใจของผู้ใช้บริการห้องสมุด", "title_en": ""},
        {"article_id": "a5", "doi": "", "title_th": "", "title_en": "Citing article"},
    ])


def _ref(aid, text, **kw):
    return {"article_id": aid, "text": text, "year": 2016, "lang": "latin", "translated": False,
            "self_citation": False, **kw}


def test_doi_match_ignores_case_and_trailing_punctuation():
    refs = pd.DataFrame([_ref("a5", "Smith, J. (2016). Something. Journal, 1(1). https://doi.org/10.14456/becj.2016.29.")])
    m = match_references(_articles(), refs, 15)
    assert m.to_dict("records") == [{"citing_id": "a5", "cited_id": "a2", "method": "doi"}]


def test_thai_title_segment_matches_without_tone_marks_or_spaces():
    text = ("ชนม์ชนก เพ็งกุล. (2559). ประสิทธิผลของนวัตกรรมการสื่อสารการตลาดเพื่อสังคมของกรีนพีซประเทศไทย. "
            "วารสารบริหารธุรกิจ, 11(1), 151-160.")
    m = match_references(_articles(), pd.DataFrame([_ref("a5", text, lang="th")]), 15)
    assert m.to_dict("records") == [{"citing_id": "a5", "cited_id": "a1", "method": "title"}]
    folded = text.replace("\N{THAI CHARACTER MAI THO}", "").replace("\N{THAI CHARACTER MAI EK}", "")
    assert match_references(_articles(), pd.DataFrame([_ref("a5", folded)]), 15)["cited_id"].tolist() == ["a1"]


def test_a_title_shared_by_two_articles_never_matches():
    refs = pd.DataFrame([_ref("a5", "Author. (2015). การศึกษาความพึงพอใจของผู้ใช้บริการห้องสมุด. วารสาร, 2(1).")])
    assert match_references(_articles(), refs, 15).empty


def test_self_citations_and_self_matches_are_dropped():
    refs = pd.DataFrame([
        _ref("a2", f"Someone. (2016). {EN_TITLE}. Journal."),                       # the article cites itself
        _ref("a5", f"Someone. (2016). {EN_TITLE}. Journal.", self_citation=True),   # flagged by ingest
        _ref("a5", f"Someone. (2016). {EN_TITLE}. Journal.", translated=True),      # translated duplicate
    ])
    assert match_references(_articles(), refs, 15).empty


def test_an_article_counts_once_per_citing_article():
    refs = pd.DataFrame([_ref("a5", f"A. (2016). {EN_TITLE}. J."), _ref("a5", "B. (2016). x. doi:10.14456/becj.2016.29"),
                         _ref("a1", f"C. (2016). {EN_TITLE}. J.")])
    m = match_references(_articles(), refs, 15)
    assert sorted(zip(m["citing_id"], m["cited_id"], m["method"])) == [("a1", "a2", "title"), ("a5", "a2", "doi")]


def test_journal_practice_medians_on_a_tiny_table():
    arts = pd.DataFrame({"article_id": ["x1", "x2", "x3", "y1"], "year": [2020, 2020, 2021, 2020],
                         "journal_key": ["so02:J", "so02:J", "so02:J", "so03:K"], "journal": ["J", "J", "J", "K"]})
    refs = pd.DataFrame([
        {"article_id": "x1", "text": "a 10.1000/abc", "year": 2018, "lang": "latin"},
        {"article_id": "x1", "text": "b", "year": 2010, "lang": "th"},
        {"article_id": "x1", "text": "c", "year": None, "lang": "th"},
        {"article_id": "x2", "text": "d", "year": 2019, "lang": "latin"},
        {"article_id": "y1", "text": "e", "year": 2019, "lang": "latin"},
    ])
    p = journal_practice(arts, refs, 2, 5)
    assert p["journal_key"].tolist() == ["so02:J"]                       # K: 1 article with refs < 2
    r = p.iloc[0]
    assert r["articles"] == 3 and r["articles_with_refs"] == 2 and r["refs_median"] == 2.0   # (3 + 1) / 2
    assert r["age_median"] == 2.0                                       # ages 2, 10, 1 → 2
    assert abs(r["share_recent"] - 2 / 3) < 1e-9 and r["share_thai"] == 0.5 and r["share_doi"] == 0.25


def _work(tmp_path, n_articles: int, with_refs: int, min_internal: int = 1):
    cfg = load_config(None)
    work = tmp_path / "work"
    cfg["pipeline"].update(work_dir=str(work), output_dir=str(tmp_path / "out"), state_dir=str(tmp_path / "state"))
    cfg["references"]["min_internal_matches"] = min_internal
    cfg["references"]["min_journal_articles"] = 1
    arts = pd.DataFrame({"article_id": [f"so02:J:{i}" for i in range(n_articles)],
                         "year": [2020 + i % 3 for i in range(n_articles)], "journal_name": "J",
                         "title": [f"Title number {i:03d} about a topic" for i in range(n_articles)],
                         "title_th": "", "title_en": [f"Title number {i:03d} about a topic" for i in range(n_articles)],
                         "doi": "", "url": "https://so02.tci-thaijo.org/x", "abstract_en": "secret abstract"})
    refs = pd.DataFrame([_ref(f"so02:J:{i}", f"Writer. (2019). Title number {(i + 1) % n_articles:03d} about a topic. J.")
                         for i in range(with_refs)])
    write_table(arts, work / "01_articles.parquet")
    write_table(refs, work / "01_references.parquet")
    write_table(arts[["article_id"]], work / "02_docs.parquet")
    write_table(arts[["article_id"]].assign(fine_topic=[i % 2 for i in range(n_articles)]), work / "04_fine_topics.parquet")
    (work / "06_meta.json").write_text(json.dumps({"years": [2020, 2021], "trimmed_years": [2022]}), encoding="utf-8")
    return cfg, work


def test_low_coverage_skips_the_module_with_the_number(tmp_path):
    cfg, work = _work(tmp_path, 10, 3)
    meta = references(cfg)
    assert meta["coverage"] == 0.3 and not meta["published"]
    model, why = references_file(cfg, work, {0: "T000000", 1: "T000001"})
    assert model is None and "30.0%" in why and "min_coverage" in why
    assert cited_counts(work) == {} and topic_citations(work) is None


def test_published_references_file_validates_and_counts_citations(tmp_path):
    cfg, work = _work(tmp_path, 10, 8)
    meta = references(cfg)
    assert meta["published"] and meta["internal"] and meta["matches"] == 8 and meta["methods"] == {"doi": 0, "title": 8}
    model, why = references_file(cfg, work, {0: "T000000", 1: "T000001"}, {"so02:J": "so02.J"})
    assert why is None and model.coverage == 0.8 and model.journals[0].id == "so02.J"
    assert model.internal.matches == 8 and model.internal.share_title == 1.0
    assert sum(t.received for t in model.internal.topics) == 8
    assert len(model.internal.top_articles) == 8 and model.internal.top_articles[0].count == 1
    C.ReferencesFile.model_validate_json(model.model_dump_json())
    assert "secret" not in model.model_dump_json()
    assert cited_counts(work)["so02:J:1"] == 1 and set(topic_citations(work)) == {0, 1}
    assert STEPS.index("gaps") < STEPS.index("references") < STEPS.index("export")


def _field_names(model: type) -> set[str]:
    names = set()
    for name, f in model.model_fields.items():
        names.add(name)
        for arg in getattr(f.annotation, "__args__", ()) + (f.annotation,):
            inner = getattr(arg, "__args__", ())
            for t in (arg, *inner):
                if isinstance(t, type) and issubclass(t, C._Model):
                    names |= _field_names(t)
    return names


def test_references_file_has_no_author_or_abstract_field():
    names = _field_names(C.ReferencesFile)
    assert {"journals", "top_articles", "title"} <= names
    assert not [n for n in names if "author" in n or "abstract" in n or n in ("text", "name")]
