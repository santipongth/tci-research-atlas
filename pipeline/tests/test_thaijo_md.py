import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from atlas.sources.thaijo_md import (
    fill_years_from_issue,
    parse_markdown,
    rejoin_references,
    resolve_year,
    split_title,
)

# Expected facts for the 11 real files, verified by hand against the source Markdown.
GOLDEN = {
    "54971": dict(year=2014, src="published", doi="10.14456/becj.2014.15",
                  title_th="ทักษะแห่งอนาคตใหม่การศึกษาเพื่อศตวรรษที่ 21",
                  title_en="21st Century Skills Rethinking How Students Learn",
                  abs_en="", n_auth=1, kw=(2, 1), refs=0, counted=0, self_only=False, flags=[]),
    "62642": dict(year=2018, src="published", doi="", title_th="",
                  title_en_start="Attitudes of Naresuan University BBA",
                  abs_en_start="There are a large number", n_auth=1, kw=(0, 4),
                  refs=13, counted=10, self_only=False, flags=[]),
    "54895": dict(year=2014, src="doi", doi="10.14456/becj.2014.27",
                  title_en="A Development of Operating Process Model for TQA Implementation",
                  abs_en_start="The purpose of this paper", n_auth=4, kw=(3, 3),
                  refs=0, counted=0, self_only=False, flags=[]),
    "74141": dict(year=2016, src="published", doi="10.14456/becj.2016.34",
                  title_en="Developmentof Production Supervisor’s Competency Standards in the Automotive Part Industries",
                  abs_en_start="This research aims to study the production", n_auth=2, kw=(4, 4),
                  refs=1, counted=0, self_only=True, flags=[]),
    "54905": dict(year=2013, src="published", doi="10.14456/becj.2013.20",
                  title_en="The Study of Employees’ Competency Requirement in MICE Industry of Thailand",
                  abs_en_start="The research objectives were", n_auth=2, kw=(5, 6),
                  refs=0, counted=0, self_only=False, flags=["thai_pua_repaired"]),
    "54875": dict(year=2014, src="doi", doi="10.14456/becj.2014.24",
                  title_en="Daily Newspapers Reading by Naresuan University Freshmen",
                  abs_en_start="This research aims to study daily", n_auth=1, kw=(3, 3),
                  refs=0, counted=0, self_only=False, flags=[]),
    "62409": dict(year=2016, src="published", doi="10.14456/becj.2016.13",
                  title_en_start="Effectiveness of Innovative Social Marketing Communication",
                  abs_en_start="This research aimed to study the effectiveness", n_auth=2, kw=(5, 5),
                  refs=1, counted=0, self_only=True, flags=[]),
    "91640": dict(year=2017, src="published", doi="10.14456/becj.2017.2",
                  title_en="Cultural Strategies for Thailand to be a High-Income Country",
                  abs_en_start="Many factors are involved", n_auth=1, kw=(5, 5),
                  refs=1, counted=0, self_only=True, flags=[]),
    "62430": dict(year=2016, src="published", doi="10.14456/becj.2016.18",
                  title_en="Communication Proficiency of Comedy Show “Jam Aud Na Marn”",
                  abs_en_start="The study of the Communication Proficiency", n_auth=1, kw=(3, 3),
                  refs=1, counted=0, self_only=True, flags=[]),
    "87805": dict(year=2018, src="published", doi="",
                  title_en="Marketing Mix Affecting the Decision Making on Purchasing the Products of Akha Ama Coffee",
                  abs_th="", abs_en_start="This research aimed to study the marketing mix", n_auth=5, kw=(3, 0),
                  refs=14, counted=14, self_only=False, flags=["stat_symbols_missing"]),
    "74136": dict(year=2016, src="published", doi="10.14456/becj.2016.29",
                  title_en="Barriers to e-commerce adoption in Thai small and medium enterprises",
                  abs_en_start="This research studies of barriers", n_auth=1, kw=(4, 4),
                  refs=1, counted=0, self_only=True, flags=[]),
}


def _parse(thaijo_dir, art_id):
    p = thaijo_dir / f"so02_BECJournal_{art_id}.md"
    return parse_markdown(p.read_text(encoding="utf-8"), p.name)


@pytest.mark.parametrize("art_id", sorted(GOLDEN))
def test_golden_real_files(thaijo_dir, art_id):
    g, r = GOLDEN[art_id], _parse(thaijo_dir, art_id)
    assert r["article_id"] == f"so02:BECJournal:{art_id}"
    assert r["journal_name"] == "BECJournal"
    assert (r["year"], r["year_source"]) == (g["year"], g["src"])
    assert r["doi"] == g["doi"]
    if "title_th" in g:
        assert r["title_th"] == g["title_th"]
    if "title_en" in g:
        assert r["title_en"] == g["title_en"]
    if "title_en_start" in g:
        assert r["title_en"].startswith(g["title_en_start"])
    if "abs_en" in g:
        assert r["abstract_en"] == g["abs_en"]
    if "abs_en_start" in g:
        assert r["abstract_en"].startswith(g["abs_en_start"])
    if "abs_th" in g:
        assert r["abstract_th"] == g["abs_th"]
    assert len(r["authors"]) == g["n_auth"]
    assert (len(r["keywords_th"]), len(r["keywords_en"])) == g["kw"]
    assert len(r["references"]) == g["refs"]
    assert r["n_references"] == g["counted"]
    assert r["self_citation_only"] is g["self_only"]
    assert r["text_quality"] == g["flags"]
    assert "DOI" not in r["abstract_en"] and "DOI" not in r["abstract_th"]


def test_pua_file_text_is_repaired(thaijo_dir):
    r = _parse(thaijo_dir, "54905")
    assert "ความต้องการ" in r["abstract_th"]
    assert "เจ้าหน้าที่" in r["abstract_th"]
    assert r["keywords_th"][0] == "ความต้องการ"
    assert r["authors"][1]["role"] == "รองศาสตราจารย์"
    assert r["authors"][1]["affiliation_th"].startswith("ภาควิชาการท่องเที่ยว")


def test_roles_students_and_nested_affiliations(thaijo_dir):
    tqa = _parse(thaijo_dir, "54895")
    assert tqa["authors"][0]["role"] == "นิสิตปริญญาเอก" and tqa["authors"][0]["is_student"]
    assert tqa["authors"][1]["role"] == "รองศาสตราจารย์" and not tqa["authors"][1]["is_student"]
    gp = _parse(thaijo_dir, "62409")
    a0, a1 = gp["authors"]
    assert a0["is_student"] and a0["role"] == "นักศึกษาปริญญาโท"
    assert a0["affiliation_en"].startswith("Department of Innovative Marketing Communication")
    assert a1["role"] == "ผู้ช่วยศาสตราจารย์"
    assert a1["affiliation_en"].startswith("Graduate School of Communication Arts")
    en = _parse(thaijo_dir, "62642")["authors"][0]
    assert (en["name"], en["name_en"]) == ("ชาตรี ปรีดาอนันทสุข", "Chatree Preedaananthasuk")
    assert en["affiliation_th"] == "" and en["affiliation_en"].startswith("Faculty of Business")


def test_bom_and_crlf_parse_identically(thaijo_dir):
    text = (thaijo_dir / "so02_BECJournal_54895.md").read_text(encoding="utf-8")
    variant = "\N{ZERO WIDTH NO-BREAK SPACE}" + text.replace("\n", "\r\n")
    assert parse_markdown(variant) == parse_markdown(text)


def test_split_title_variants():
    assert split_title("ภาษาไทยยาวพอสมควร [An English Title Here]") == ("ภาษาไทยยาวพอสมควร", "An English Title Here")
    # the alternate-language part must hold >= 15 letters (Thai consonants + Latin) to count as a title
    assert split_title("An English Title Here (ชื่อเรื่องภาษาไทยที่ยาวพอสมควรแน่นอน)") == (
        "ชื่อเรื่องภาษาไทยที่ยาวพอสมควรแน่นอน", "An English Title Here")
    th, en = split_title("การพัฒนาตัวแบบรางวัลคุณภาพแห่งชาติ (TQA)")      # short acronym stays in the title
    assert th.endswith("(TQA)") and en == ""


def test_rejoin_references_wrapped_lines(thaijo_dir):
    refs = _parse(thaijo_dir, "62642")["references"]
    assert len(refs) == 13
    assert sum(r["translated"] for r in refs) == 3
    assert refs[0]["year"] == 2013                      # (2556) BE → CE
    assert refs[5]["text"].startswith("Freeman, R.E.") and refs[5]["year"] == 2010
    assert refs[9]["text"].startswith("Webometrics.") and refs[9]["year"] == 2016


def test_resolve_year_rules():
    assert resolve_year("2016-06-29", "") == (2016, "published")
    assert resolve_year("1970-01-01", "10.14456/becj.2014.27") == (2014, "doi")
    assert resolve_year("2559-01-01", "") == (2016, "published")
    assert resolve_year("", "") == (None, "")


def test_fill_years_from_issue():
    recs = [{"year": 2015, "issue_url": "u1", "year_source": "published"},
            {"year": None, "issue_url": "u1", "year_source": ""},
            {"year": None, "issue_url": "u2", "year_source": ""}]
    fill_years_from_issue(recs)
    assert recs[1]["year"] == 2015 and recs[1]["year_source"] == "issue_median"
    assert recs[2]["year"] is None


def test_rejoin_handles_empty():
    assert rejoin_references([]) == []


@settings(max_examples=300, deadline=None)
@given(st.text())
def test_parser_never_raises_on_arbitrary_text(text):
    r = parse_markdown(text)
    assert set(r) >= {"article_id", "year", "authors", "references", "text_quality"}


LINES = ["# ชื่อเรื่อง", "**Journal:** J", "**Published:** 1970-01-01", "**Authors:**", "- ก (", "- x [y] ((",
         "**Keywords:** ,,;", "## Abstract", "   DOI:   ", "## References", "- (2559)", "- Smith, A. (", ""]


@settings(max_examples=300, deadline=None)
@given(st.lists(st.sampled_from(LINES), max_size=30))
def test_parser_never_raises_on_broken_structure(lines):
    parse_markdown("\n".join(lines))
