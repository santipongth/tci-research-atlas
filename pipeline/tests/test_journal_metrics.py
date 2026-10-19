"""D2 metadata completeness and D3 in-house / diversity / foreign authors — aggregates per journal."""
import numpy as np
import pandas as pd
import pytest

from atlas.config import DEFAULT_COMPLETENESS_WEIGHTS
from atlas.countries import is_foreign_affiliation
from atlas.journal_metrics import (
    article_completeness,
    author_metrics,
    completeness_table,
    owner_key_of,
    owners,
)
from atlas.orgs import org_key

NU = "คณะบริหารธุรกิจ มหาวิทยาลัยนเรศวร"
CU = "คณะครุศาสตร์ จุฬาลงกรณ์มหาวิทยาลัย"
KU = "มหาวิทยาลัยเกษตรศาสตร์"


def _arts():
    return pd.DataFrame({
        "article_id": ["a1", "a2", "a3", "a4", "b1"],
        "journal_key": ["so02:J1", "so02:J1", "so02:J1", "so02:J1", "so03:J2"],
        "abstract_en": ["x", "", "x", "x", "x"], "title_en": ["t", "t", "t", "", "t"],
        "keywords_en": ["k", "k", "", "", "k"], "doi": ["10.1/a", "", "", "", "10.1/b"],
        "has_references": [True, True, False, True, True], "self_citation_only": [False, True, False, False, False]})


def _authors():
    rows = [("a1", NU, ""), ("a1", "", "University of Tokyo, Japan"), ("a2", NU, ""), ("a3", CU, ""),
            ("a4", "", ""), ("b1", KU, "")]
    df = pd.DataFrame(rows, columns=["article_id", "affiliation_th", "affiliation_en"])
    return df.assign(org_key=[org_key(t, e) for t, e in zip(df["affiliation_th"], df["affiliation_en"])])


def _refs():
    return pd.DataFrame({"article_id": ["a1", "a1", "a2", "a3"], "lang": ["th", "latin", "th", "latin"],
                         "translated": [False, True, False, False]})


@pytest.mark.parametrize("th, en, foreign", [
    ("", "University of Tokyo, Japan", True),
    ("มหาวิทยาลัยแห่งชาติลาว สปป.ลาว", "", True),
    ("ภาควิชาภาษาจีน คณะมนุษยศาสตร์ มหาวิทยาลัยเชียงใหม่", "", False),     # "จีน" without "ประเทศ"
    ("", "Japanese Studies Center, Thammasat University", False),
    ("", "Asian Institute of Technology, Pathum Thani, Thailand", False),
    ("มหาวิทยาลัยโตเกียว ประเทศญี่ปุ่น", "", True),
    ("", "Cardiff University, UK", True),
    ("", "", False),
])
def test_foreign_affiliations(th, en, foreign):
    assert is_foreign_affiliation(th, en) is foreign


def test_article_completeness_marks_unknown_elements_as_missing_data():
    comp = article_completeness(_arts(), _refs(), _authors()).set_index("article_id")
    assert comp.loc["a1", "doi"] and not comp.loc["a2", "doi"]
    assert not comp.loc["a2", "references"]                         # only "how to cite this article"
    assert comp.loc["a1", "refs_romanized"] and not comp.loc["a2", "refs_romanized"]
    assert pd.isna(comp.loc["a3", "refs_romanized"])                # no Thai-language references
    assert not comp.loc["a4", "affiliations"] and comp.loc["a1", "affiliations"]
    assert pd.isna(article_completeness(_arts(), _refs(), _authors().iloc[0:0]).loc[0, "affiliations"])


def test_completeness_score_is_a_weighted_mean_of_known_rates():
    arts = _arts()
    comp = article_completeness(arts, _refs(), _authors())
    long, score = completeness_table(comp, arts.set_index("article_id")["journal_key"], DEFAULT_COMPLETENESS_WEIGHTS)
    j1 = long[long["journal_key"] == "so02:J1"].set_index("component")
    assert j1.loc["doi", "rate"] == pytest.approx(0.25) and j1.loc["doi", "n"] == 4
    assert j1.loc["refs_romanized", "n"] == 2 and j1.loc["refs_romanized", "rate"] == pytest.approx(0.5)
    w = DEFAULT_COMPLETENESS_WEIGHTS
    expected = 100 * sum(w[c] * j1.loc[c, "rate"] for c in w) / sum(w.values())
    assert score["so02:J1"] == pytest.approx(round(expected, 1))
    j2 = long[long["journal_key"] == "so03:J2"].set_index("component")
    assert np.isnan(j2.loc["refs_romanized", "rate"])               # J2 cites no Thai sources: weight dropped
    known = {c: w[c] for c in w if c != "refs_romanized"}
    assert score["so03:J2"] == pytest.approx(round(100 * sum(known[c] * j2.loc[c, "rate"] for c in known)
                                                   / sum(known.values()), 1))


def test_owner_from_registry_or_inferred_and_labelled():
    arts, auth = _arts(), _authors()
    display = {org_key(NU, ""): "มหาวิทยาลัยนเรศวร"}
    inferred = owners(arts, auth, {}, 0.2, display).set_index("journal_key")
    assert inferred.loc["so02:J1", "owner_source"] == "inferred"
    assert inferred.loc["so02:J1", "owner_name"] == "มหาวิทยาลัยนเรศวร"
    assert inferred.loc["so02:J1", "owner_share"] == pytest.approx(2 / 3)    # a4 has no recognised organisation
    reg = owners(arts, auth, {"so02:J1": "จุฬาลงกรณ์มหาวิทยาลัย"}, 0.2, display).set_index("journal_key")
    assert reg.loc["so02:J1", "owner_source"] == "registry" and reg.loc["so02:J1", "owner_matched"]
    assert reg.loc["so02:J1", "owner_share"] == pytest.approx(1 / 3)
    strict = owners(arts, auth, {}, 0.9, display).set_index("journal_key")
    assert pd.isna(strict.loc["so02:J1", "owner_source"]) and strict.loc["so02:J1", "owner_key"] == ""
    assert owner_key_of("Chulalongkorn University") == org_key("", "Chulalongkorn University")


def test_inhouse_diversity_and_foreign_shares():
    arts, auth = _arts(), _authors()
    own = owners(arts, auth, {}, 0.2, {})
    m = author_metrics(arts, auth, own).set_index("journal_key")
    j1 = m.loc["so02:J1"]
    assert j1["with_org"] == 3 and j1["affiliation_coverage"] == pytest.approx(0.75)
    assert j1["inhouse_share"] == pytest.approx(2 / 3)
    assert j1["n_orgs"] == 3                                    # NU, Tokyo, CU
    p = np.array([2, 1, 1]) / 4
    assert j1["effective_orgs"] == pytest.approx(1 / (p ** 2).sum())
    assert j1["foreign_share"] == pytest.approx(1 / 3)
    none = author_metrics(arts, auth.iloc[0:0], owners(arts, auth.iloc[0:0], {}, 0.2, {})).set_index("journal_key")
    assert none.loc["so02:J1", "with_org"] == 0 and np.isnan(none.loc["so02:J1", "inhouse_share"])


# ---------------------------------------------------------------- review follow-ups
def test_inhouse_share_is_null_when_the_registry_owner_is_not_found_among_authors():
    arts, auth = _arts(), _authors()
    own = owners(arts, auth, {"so02:J1": "Naresuan University"}, 0.2, {})      # written differently from the data
    assert not own.set_index("journal_key").loc["so02:J1", "owner_matched"]
    m = author_metrics(arts, auth, own).set_index("journal_key")
    assert np.isnan(m.loc["so02:J1", "inhouse_share"])                           # not 0.0: unknown, not zero
    assert m.loc["so02:J1", "with_org"] == 3 and m.loc["so02:J1", "n_orgs"] == 3  # the other metrics stay


def test_a_component_missing_from_the_whole_corpus_is_unknown_not_zero():
    arts = _arts().drop(columns=["doi", "has_references"])
    comp = article_completeness(arts, _refs(), _authors())
    assert comp["doi"].isna().all() and comp["references"].isna().all()
    blank = _arts().assign(abstract_en="")
    assert article_completeness(blank, _refs(), _authors())["abstract_en"].isna().all()
    no_rows = article_completeness(_arts(), _refs().iloc[0:0], _authors())      # table input: no reference rows at all
    assert no_rows["references"].isna().all()
    long, score = completeness_table(comp, _arts().set_index("article_id")["journal_key"],
                                     DEFAULT_COMPLETENESS_WEIGHTS)
    assert long[long["component"] == "doi"]["rate"].isna().all() and score.notna().all()


def test_a_self_citation_line_is_not_a_thai_reference():
    refs = pd.DataFrame({"article_id": ["a1", "a2", "a3"], "lang": ["th", "th", "th"],
                         "translated": [True, False, False], "self_citation": [False, False, True]})
    comp = article_completeness(_arts(), refs, _authors()).set_index("article_id")
    assert comp.loc["a1", "refs_romanized"] and not comp.loc["a2", "refs_romanized"]
    assert pd.isna(comp.loc["a3", "refs_romanized"])                            # only "how to cite this article"


def test_completeness_ignores_articles_without_a_journal_key():
    arts = _arts()
    comp = article_completeness(arts, _refs(), _authors())
    keys = arts.set_index("article_id")["journal_key"].copy()
    keys["a4"] = ""
    long, _ = completeness_table(comp, keys, DEFAULT_COMPLETENESS_WEIGHTS)
    assert "" not in set(long["journal_key"])


def test_a_thai_japan_name_is_not_foreign_and_a_missing_thai_affiliation_does_not_hide_a_foreign_one():
    assert is_foreign_affiliation("", "Thai-Japan Institute of Technology, Bangkok") is False
    arts = pd.DataFrame({"article_id": ["k1", "k2"], "journal_key": ["j", "j"]})
    auth = pd.DataFrame({"article_id": ["k1", "k2"], "affiliation_th": [None, KU],
                         "affiliation_en": ["Kyoto University, Japan", None]})
    auth["org_key"] = [org_key(t if isinstance(t, str) else "", e if isinstance(e, str) else "")
                       for t, e in zip(auth["affiliation_th"], auth["affiliation_en"])]
    m = author_metrics(arts, auth, owners(arts, auth, {}, 0.2, {})).set_index("journal_key")
    assert m.loc["j", "foreign_share"] == pytest.approx(0.5)
