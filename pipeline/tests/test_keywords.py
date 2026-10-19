import json

import pandas as pd

from atlas.config import load_config
from atlas.io_utils import read_table, write_table
from atlas.keywords import KEYWORD_COLUMNS, emerging_keywords, keyword_rows, keywords

CFG = load_config(None)
YEARS = list(range(2015, 2025))              # last complete 2024 → R 2022–24, B 2017–21, W 2020–24
OLD_J = ["jA", "jB", "jC", "jD"]


def _docs():
    """filler docs + planted terms: rising (4 journals, 5 orgs), rising-but-one-new-journal, generic, flat."""
    rows, authors, n = [], [], 0

    def add(year, journal, kw_en, org):
        nonlocal n
        rows.append({"article_id": f"a{n}", "year": year, "journal_name": journal, "keywords_th": "",
                     "keywords_en": kw_en})
        authors.append({"article_id": f"a{n}", "org_key": org})
        n += 1

    rising = {2017: 1, 2019: 1, 2020: 2, 2021: 3, 2022: 8, 2023: 16, 2024: 30}
    for y in YEARS:
        for i in range(200):
            add(y, OLD_J[i % 4], "survey; filler", f"org{i % 6}")
        for i in range(rising.get(y, 0)):
            add(y, OLD_J[i % 4], "ChatGPT; survey", f"org{i % 5}")
            add(y, "jNew" if y >= 2022 else OLD_J[i % 4], "Buddhism online", f"org{i % 5}")
        for i in range(10):
            add(y, OLD_J[i % 4], "Steady Topic", f"org{i % 5}")
        for i in range({2022: 3, 2023: 4, 2024: 5}.get(y, 0)):
            add(y, OLD_J[i % 4], "LLM agents", f"org{i % 2}")      # new in R (no baseline), only 2 orgs
    return pd.DataFrame(rows).astype({"year": "Int64"}), pd.DataFrame(authors)


def test_keyword_rows_fold_case_spacing_and_duplicates():
    docs = pd.DataFrame({"article_id": ["a"], "year": [2020], "journal_name": ["j"],
                         "keywords_th": ["การศึกษา; การศึกษา "], "keywords_en": ["ChatGPT; chat gpt; x"]})
    kw = keyword_rows(docs)
    assert sorted(kw["key"]) == ["chatgpt", "การศึกษา"]          # 1-char key dropped, "chat gpt" = "ChatGPT"


def test_emerging_requires_novelty_persistence_breadth_and_growth():
    docs, authors = _docs()
    kw = keyword_rows(docs)
    totals = docs.groupby("year").size()
    totals.index = totals.index.astype(int)
    jfirst = docs.groupby("journal_name")["year"].min().rename("first_year").reset_index().rename(
        columns={"journal_name": "journal"})
    raw = emerging_keywords(kw, totals, 2024, CFG["emerging"], CFG["keywords"], authors, jfirst)
    assert list(raw.columns) == KEYWORD_COLUMNS
    out = raw.set_index("key")
    assert bool(out.loc["chatgpt", "emerging"]) and out.loc["chatgpt", "term"] == "ChatGPT"
    assert bool(out.loc["buddhismonline", "journal_driven"]) and not bool(out.loc["buddhismonline", "emerging"])
    assert "survey" not in out.index                                # in > 15% of documents → generic
    assert "steadytopic" not in out.index                           # no novelty (share ratio ≈ 1)
    assert out.index[0] == "chatgpt"                                # emerging terms sort first
    assert bool(out.loc["llmagents", "no_baseline"]) and not bool(out.loc["chatgpt", "no_baseline"])
    assert not bool(out.loc["llmagents", "emerging"])               # 2 institutions < min_orgs


def test_keywords_step_and_disabled_switch(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    work = tmp_path / "work"
    docs, authors = _docs()
    write_table(docs, work / "02_docs.parquet")
    write_table(authors, work / "01_authors.parquet")
    write_table(pd.DataFrame({"article_id": docs["article_id"], "fine_topic": 1}), work / "04_fine_topics.parquet")
    totals = docs.groupby("year").size()
    (work / "06_meta.json").write_text(json.dumps({"last_complete_year": 2024,
                                                   "totals": {str(int(y)): int(n) for y, n in totals.items()}}),
                                       encoding="utf-8")
    write_table(docs.groupby("journal_name")["year"].min().astype(int).rename("first_year").reset_index()
                .rename(columns={"journal_name": "journal"}), work / "06_journal_first_year.parquet")
    out = keywords(cfg)
    assert out.set_index("key").loc["chatgpt", "topic_id"] == 1
    assert len(read_table(work / "07_keywords.parquet")) == len(out)
    cfg["keywords"]["enabled"] = False
    assert keywords(cfg).empty and read_table(work / "07_keywords.parquet").empty


def test_smoothing_articles_is_a_config_key():
    docs, authors = _docs()
    totals = docs.groupby("year").size()
    totals.index = totals.index.astype(int)
    jfirst = docs.groupby("journal_name")["year"].min().rename("first_year").reset_index().rename(
        columns={"journal_name": "journal"})
    heavy = {**CFG["keywords"], "smoothing_articles": 1e6}           # B swamped by pseudo-articles → ratio ≈ 1
    out = emerging_keywords(keyword_rows(docs), totals, 2024, CFG["emerging"], heavy, authors, jfirst)
    assert "chatgpt" not in set(out["key"])
