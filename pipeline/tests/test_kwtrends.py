"""kwtrends step (P4, R7): author-keyword trends over the series years and the TH-EN glossary."""
import json

import pandas as pd
import pytest
from pydantic import ValidationError

from atlas.config import load_config
from atlas.export_research import kwtrends_file
from atlas.io_utils import read_table, write_table
from atlas.kwtrends import glossary, glossary_pairs, keyword_rows, keyword_trends, kwtrends
from atlas.pipeline import STEPS
from atlas.schema import contract as C

KAN_TALAT = "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER RO RUA}" \
            "\N{THAI CHARACTER TO TAO}\N{THAI CHARACTER LO LING}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER DO DEK}"
KAFAE = "\N{THAI CHARACTER KO KAI}\N{THAI CHARACTER SARA AA}\N{THAI CHARACTER FO FAN}\N{THAI CHARACTER SARA AE}"
SANGKHOM = "\N{THAI CHARACTER SO SUA}\N{THAI CHARACTER MAI HAN-AKAT}\N{THAI CHARACTER NGO NGU}" \
           "\N{THAI CHARACTER KHO KHWAI}\N{THAI CHARACTER MO MA}"
CODE = {0: "T000000", 1: "T000001"}


def _docs(rows):
    return pd.DataFrame(rows, columns=["article_id", "year", "keywords_th", "keywords_en"])


def _work(tmp_path, rows, topics, years=(2020, 2021), trimmed=(2022,), **kw):
    cfg = load_config(None)
    work = tmp_path / "work"
    cfg["pipeline"].update(work_dir=str(work), output_dir=str(tmp_path / "out"), state_dir=str(tmp_path / "state"))
    cfg["kwtrends"].update(kw)
    docs = _docs(rows).assign(abstract_th="secret abstract", authors="Somchai Jaidee")
    write_table(docs, work / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": docs["article_id"], "fine_topic": topics}), work / "04_fine_topics.parquet")
    (work / "06_meta.json").write_text(json.dumps({"years": list(years), "trimmed_years": list(trimmed)}),
                                       encoding="utf-8")
    return cfg, work


def test_normalisation_merges_case_spacing_and_punctuation_variants():
    docs = _docs([("a1", 2020, "", "Machine Learning; machine  learning"),      # same key twice: counted once
                  ("a2", 2020, "", "MACHINE-LEARNING"),
                  ("a3", 2021, "", "machine learning ; ;"),
                  ("a4", 2021, "", "Machine Learning"),
                  ("a5", 2021, f" {KAN_TALAT} ", "x")])                             # "x": key shorter than 2
    rows = keyword_rows(docs, 2)
    assert set(rows["key"]) == {"machinelearning", KAN_TALAT}
    assert rows.groupby("key").size()["machinelearning"] == 4
    trends, candidates = keyword_trends(rows, [2020, 2021], 1, 10)
    assert candidates == 2
    ml = trends[trends["key"] == "machinelearning"]
    assert ml["term"].iloc[0] == "Machine Learning" and ml["count"].tolist() == [2, 2] and ml["lang"].iloc[0] == "en"
    assert trends.loc[trends["key"] == KAN_TALAT, "lang"].iloc[0] == "th"


def test_min_count_and_max_keywords_are_respected():
    rows = []
    for i in range(6):                                       # alpha 6, beta 5, gamma 4 articles
        rows.append((f"a{i}", 2020 + i % 2, "", "; ".join(k for k, n in (("alpha", 6), ("beta", 5), ("gamma", 4))
                                                          if i < n)))
    kw = keyword_rows(_docs(rows), 2)
    trends, _ = keyword_trends(kw, [2020, 2021], 5, 10)
    assert trends.drop_duplicates("key")["term"].tolist() == ["alpha", "beta"]          # gamma below min_count
    trends, _ = keyword_trends(kw, [2020, 2021], 1, 2)
    assert trends.drop_duplicates("key")["term"].tolist() == ["alpha", "beta"]          # max_keywords cut
    assert trends.groupby("key")["count"].sum().to_dict() == {"alpha": 6, "beta": 5}


def test_totals_per_year_equal_article_counts_and_trimmed_years_are_left_out(tmp_path):
    rows = [("a1", 2020, KAFAE, "coffee"), ("a2", 2020, "", ""), ("a3", 2021, KAFAE, ""),
            ("a4", 2021, "", "coffee"), ("a5", 2021, "", ""), ("a6", 2022, KAFAE, "coffee"),
            ("a7", None, KAFAE, "coffee")]
    cfg, work = _work(tmp_path, rows, [0, 0, 1, 1, 1, 0, -1], min_count=1)
    meta = kwtrends(cfg)
    assert meta["years"] == [2020, 2021] and meta["totals"] == [2, 3]          # every dated article, keywords or not
    assert meta["totals_th"] == [1, 1] and meta["totals_en"] == [1, 1]
    files, why, gl = kwtrends_file(cfg, work, CODE)
    assert why is None and files.years == [2020, 2021] and files.totals == [2, 3]
    assert {(k.term, k.lang): k.counts for k in files.keywords} == {(KAFAE, "th"): [1, 1], ("coffee", "en"): [1, 1]}
    assert all(k.n == sum(k.counts) for k in files.keywords)


def test_glossary_pairs_by_position_only_when_lengths_match():
    docs = _docs([("a1", 2020, f"{KAN_TALAT}; {KAFAE}", "Marketing; Coffee"),
                  ("a2", 2020, f"{KAN_TALAT}; {KAFAE}", "Marketing"),                 # lengths differ: no pairs
                  ("a3", 2020, f"{KAFAE}; {SANGKHOM}", "coffee ; Society"),
                  ("a4", 2020, f"Marketing; {KAFAE}", f"marketing; {KAFAE}"),         # copied sides are dropped
                  ("a5", 2020, "", "")])
    p = glossary_pairs(docs, 2)
    assert sorted(zip(p["article_id"], p["th"], p["en"])) == sorted([
        ("a1", KAN_TALAT, "Marketing"), ("a1", KAFAE, "Coffee"), ("a3", KAFAE, "coffee"), ("a3", SANGKHOM, "Society")])
    g = glossary(p, pd.Series({"a1": 0, "a3": 0}), 15, 2, 2000)
    assert g[["scope", "topic_id", "th", "en", "n"]].values.tolist() == [
        ["topic", 0, KAFAE, "Coffee", 2], ["all", -1, KAFAE, "Coffee", 2]]       # ties of written form: code point


def test_glossary_per_topic_top_n_and_min_pairs(tmp_path):
    pairs = [(KAFAE, "coffee")] * 4 + [(KAN_TALAT, "marketing")] * 3 + [(SANGKHOM, "society")]
    rows = [(f"t0-{i}", 2020, th, en) for i, (th, en) in enumerate(pairs)]
    rows += [("t1-0", 2021, KAFAE, "coffee"), ("t1-1", 2021, KAFAE, "coffee"), ("u-0", 2021, KAN_TALAT, "marketing")]
    cfg, work = _work(tmp_path, rows, [0] * len(pairs) + [1, 1, -1], glossary_per_topic=1, glossary_min_pairs=2,
                      glossary_max=2)
    kwtrends(cfg)
    g = read_table(work / "21_glossary.parquet")
    topic = g[g["scope"] == "topic"]
    assert topic[["topic_id", "th", "n"]].values.tolist() == [[0, KAFAE, 4], [1, KAFAE, 2]]       # top 1 per topic
    _, _, per_topic = kwtrends_file(cfg, work, CODE)
    assert per_topic == {0: [C.GlossaryItem(th=KAFAE, en="coffee", n=4)], 1: [C.GlossaryItem(th=KAFAE, en="coffee", n=2)]}
    model, _, _ = kwtrends_file(cfg, work, CODE)
    assert [(i.th, i.n) for i in model.glossary] == [(KAFAE, 6), (KAN_TALAT, 4)]     # unassigned counts overall
    cfg["kwtrends"].update(glossary_per_topic=15, glossary_min_pairs=3)
    kwtrends(cfg)
    _, _, per_topic = kwtrends_file(cfg, work, CODE)
    assert [(i.th, i.n) for i in per_topic[0]] == [(KAFAE, 4), (KAN_TALAT, 3)] and 1 not in per_topic  # n < 3


def test_kwtrends_json_is_strict_and_skips_carry_a_reason(tmp_path):
    rows = [(f"a{i}", 2020 + i % 2, KAFAE, "coffee") for i in range(6)]
    cfg, work = _work(tmp_path, rows, [0] * 6, min_count=5)
    kwtrends(cfg)
    model, why, per_topic = kwtrends_file(cfg, work, CODE)
    assert C.model_for("kwtrends.json") is C.KwTrendsFile and why is None
    raw = model.model_dump_json()

    def no_constant(c):
        raise ValueError(c)

    data = json.loads(raw, parse_constant=no_constant)          # no NaN / Infinity
    assert set(data) == {"schema_version", "years", "totals", "totals_th", "totals_en", "min_count", "max_keywords",
                         "glossary_min_pairs", "keywords", "glossary"}
    assert data["keywords"] == [{"term": "coffee", "lang": "en", "n": 6, "counts": [3, 3]},     # ties: lang, key
                                {"term": KAFAE, "lang": "th", "n": 6, "counts": [3, 3]}]
    assert "secret" not in raw and "Somchai" not in raw
    C.KwTrendsFile.model_validate_json(raw)
    with pytest.raises(ValidationError, match="one value per year"):
        C.KwTrendsFile.model_validate({**data, "keywords": [{**data["keywords"][0], "counts": [1]}]})
    names = {n for m in (C.KwTrendsFile, C.KeywordTrend, C.GlossaryItem) for n in m.model_fields}
    assert not [n for n in names if "author" in n or "abstract" in n]
    detail = C.TopicDetail(id="T000000", articles=[], glossary=per_topic.get(0, []))
    assert json.loads(detail.model_dump_json())["glossary"] == [{"th": KAFAE, "en": "coffee", "n": 6}]

    cfg["kwtrends"]["enabled"] = False
    kwtrends(cfg)
    assert not (work / "21_kw_years.parquet").exists()                    # stale tables of the last run removed
    assert kwtrends_file(cfg, work, CODE) == (None, "kwtrends.enabled is false", None)
    assert kwtrends_file(cfg, tmp_path / "nowhere", CODE) == (None, None, None)   # step never ran
    assert C.TopicDetail(id="T000000", articles=[]).glossary is None              # null = not published
    assert STEPS.index("search") < STEPS.index("kwtrends") < STEPS.index("export")
