"""search step (P4, R2 + R8): index tokens, greedy query tokens, shards, doc rows and galaxy points."""
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from atlas.config import load_config
from atlas.export_research import search_files
from atlas.io_utils import read_table, write_table
from atlas.pipeline import STEPS
from atlas.publish import offline_bundle
from atlas.schema import contract as C
from atlas.search_index import STOPWORDS, build_postings, doc_order, fnv1a32, query_tokens, search, tokens
from atlas.sources.thaijo_md import parse_markdown
from tests.conftest import FIXTURES

PARITY = FIXTURES / "search_parity.json"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_search_parity.py"


def _real_titles() -> list[tuple[str, str]]:
    out = []
    for p in sorted((FIXTURES / "thaijo_md").glob("*.md")):
        r = parse_markdown(p.read_text(encoding="utf-8"), p.name)
        out.append((r["title_th"], r["title_en"]))
    return out


def test_tokens_of_the_real_fixture_titles_are_stable():
    titles = _real_titles()
    assert len(titles) == 11
    assert tokens(titles[0][0]) == ["อ่าน", "หนังสือพิมพ์", "รายวัน", "นิสิต", "ชั้นปี", "มหาวิทยาลัยนเรศวร"]
    assert tokens(titles[0][1]) == ["daily", "newspapers", "reading", "naresuan", "university", "freshmen"]
    assert tokens(titles[7][0]) == ["อุปสรรค", "การนำ", "พาณิชย์", "อิเล็กทรอนิกส์", "มา", "ใช้", "วิสาหกิจ", "ขนาด",
                                    "กลาง", "ขนาดย่อม", "ไทย"]
    assert tokens(titles[7][1]) == ["barriers", "commerce", "adoption", "thai", "small", "medium", "enterprises"]
    for th, en in titles:
        toks = tokens(f"{th}\n{en}")
        assert toks and not set(toks) & STOPWORDS and all(len(t) >= 2 for t in toks)


def test_stopwords_are_dropped_and_only_four_digit_numbers_kept():
    assert tokens("The effect of การ ของ and ที่") == ["effect"]
    assert tokens("COVID-19 in 2019, 2563 ๒๕๖๓ 12345 3d") == ["covid", "2019", "2563", "2563", "3d"]
    assert tokens("") == [] and tokens("a , ; -") == []


def test_query_tokens_match_thai_greedily_and_name_unknown_words():
    vocab = {"การตลาด", "สังคม", "ประเทศ", "ไทย", "marketing"}
    assert query_tokens("การตลาดเพื่อสังคม", vocab, 24) == (["การตลาด", "สังคม"], [])
    assert query_tokens("Marketing ในประเทศไทย ประเทศ", vocab, 24) == (["marketing", "ประเทศ", "ไทย"], [])
    assert query_tokens("ปัญญาประดิษฐ์กับการตลาด blockchain", vocab, 24) == (
        ["การตลาด"], ["ปัญญาประดิษฐ์", "blockchain"])
    assert query_tokens("ณ ไทย a 19", vocab, 24) == (["ไทย"], [])        # never-indexable leftovers are ignored
    assert query_tokens("การตลาด", vocab, 3) == ([], ["ตลาด"])        # longest tried substring: max_chars


def test_fnv1a32_is_pinned():
    assert fnv1a32("") == 0x811C9DC5 and fnv1a32("a") == 0xE40C292C
    assert fnv1a32("การ") == 902013483 and fnv1a32("การ") % 64 == 43


def test_parity_fixture_regenerates_identically():
    spec = importlib.util.spec_from_file_location("make_search_parity", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert PARITY.read_text(encoding="utf-8") == mod.fixture_text()
    data = json.loads(mod.fixture_text())
    assert len(data["queries"]) >= 12 and data["max_token_chars"] == 24 and data["index_shards"] == 64
    vocab = set(data["vocab"])
    for case in data["queries"]:
        assert set(case["known"]) <= vocab and not set(case["unknown"]) & vocab


# ---------------------------------------------------------------- the step + export on a tiny work dir
def _work(tmp_path, galaxy=True):
    cfg = load_config(None)
    work = tmp_path / "work"
    cfg["pipeline"].update(work_dir=str(work), output_dir=str(tmp_path / "out"), state_dir=str(tmp_path / "state"))
    cfg["search"].update(index_shards=4, docs_per_shard=2)
    arts = pd.DataFrame([
        {"article_id": "so02:J:5", "year": 2021, "title_th": "การตลาดเพื่อสังคม", "title_en": "Social marketing",
         "keywords_th": "การตลาด; สังคม", "keywords_en": "marketing", "doi": "10.1/x5", "url": "https://so02/5"},
        {"article_id": "so02:J:1", "year": 2020, "title_th": "", "title_en": "Marketing mix of coffee shops",
         "keywords_th": "", "keywords_en": "marketing mix; coffee", "doi": "", "url": "https://so02/1"},
        {"article_id": "so02:J:3", "year": 2022, "title_th": "กาแฟในประเทศไทย", "title_en": "",
         "keywords_th": "กาแฟ", "keywords_en": "", "doi": "", "url": ""},
        {"article_id": "so02:J:2", "year": 2010, "title_th": "นอกช่วง", "title_en": "Out of window",
         "keywords_th": "", "keywords_en": "", "doi": "", "url": ""},
        {"article_id": "so02:J:4", "year": 2021, "title_th": "", "title_en": "", "keywords_th": "x", "keywords_en": "",
         "doi": "", "url": ""},
        {"article_id": "so02:J:0", "year": None, "title_th": "ไม่มีปี", "title_en": "", "keywords_th": "",
         "keywords_en": "", "doi": "", "url": ""},
    ]).assign(journal_name=["J", "K", "J", "J", "J", "J"], abstract_th="บทคัดย่อลับเฉพาะ",
              abstract_en="a secret abstract", authors="Somchai Jaidee")
    write_table(arts, work / "01_articles.parquet")
    write_table(arts[["article_id"]], work / "02_docs.parquet")
    write_table(pd.DataFrame({"article_id": arts["article_id"], "fine_topic": [0, 1, -1, 0, 0, 0]}),
                work / "04_fine_topics.parquet")
    (work / "06_meta.json").write_text(json.dumps({"years": [2020, 2021], "trimmed_years": [2022]}), encoding="utf-8")
    if galaxy:
        write_table(pd.DataFrame({"article_id": ["so02:J:5", "so02:J:1"], "topic_id": [0, 1], "gx": [840.0, 0.0],
                                  "gy": [520.0, 1040.0]}), work / "09_galaxy.parquet")
    return cfg, work


CODE = {0: "T000000", 1: "T000001"}


def test_doc_order_keeps_dated_titled_window_articles_in_id_order(tmp_path):
    _, work = _work(tmp_path)
    d = doc_order(work)
    assert d["article_id"].tolist() == ["so02:J:1", "so02:J:3", "so02:J:5"] and d["ordinal"].tolist() == [0, 1, 2]


def test_postings_are_sorted_unique_and_shards_decode_back(tmp_path):
    cfg, work = _work(tmp_path)
    meta = search(cfg)
    assert meta["n_docs"] == 3 and meta["search"]["published"] and meta["galaxy"]["published"]
    p = read_table(work / "20_postings.parquet")
    assert not p.duplicated().any()
    assert p.equals(p.sort_values(["token", "ordinal"]).reset_index(drop=True))
    files, skipped = search_files(cfg, work, CODE)
    assert skipped == {}
    assert sorted(k for k in files if "/idx-" in k) == [f"search/idx-{s:03d}.json" for s in range(4)]
    decoded = []
    for s in range(4):
        shard = files[f"search/idx-{s:03d}.json"]
        for tok, deltas in shard.postings.items():
            assert fnv1a32(tok) % 4 == s and all(d > 0 for d in deltas[1:])
            decoded += [(tok, int(o)) for o in np.cumsum(deltas)]
    assert sorted(decoded) == list(zip(p["token"], p["ordinal"].astype(int)))
    vocab = files["search/vocab.json"]
    assert vocab.tokens == sorted(vocab.tokens) and dict(zip(vocab.tokens, vocab.df))["marketing"] == 2
    assert "การ" not in vocab.tokens and "ไทย" in vocab.tokens
    m = files["search/meta.json"]
    assert (m.n_docs, m.doc_shards, m.journals, m.years) == (3, 2, ["J", "K"], [2020, 2021, 2022])
    for path, model in files.items():
        assert C.model_for(path) is type(model)
        type(model).model_validate_json(model.model_dump_json())


def test_doc_rows_carry_no_author_or_abstract(tmp_path):
    cfg, work = _work(tmp_path)
    search(cfg)
    files, _ = search_files(cfg, work, CODE)
    d0, d1 = files["search/docs-000.json"], files["search/docs-001.json"]
    assert (d0.start, d1.start) == (0, 2)
    assert list(d0.docs[0]) == ["so02:J:1", "", "Marketing mix of coffee shops", 2020, 1, "T000001", None,
                                "https://so02/1", 0]
    assert list(d1.docs[0]) == ["so02:J:5", "การตลาดเพื่อสังคม", "Social marketing", 2021, 0, "T000000", "10.1/x5",
                                "https://so02/5", 0]
    assert d0.docs[1][5] is None                                         # unassigned article: topic null
    blob = "".join(m.model_dump_json() for m in files.values())
    assert "secret" not in blob and "บทคัดย่อ" not in blob and "Somchai" not in blob
    names = {n for m in (C.SearchMeta, C.SearchVocab, C.SearchIndexShard, C.SearchDocShard, C.GalaxyFile)
             for n in m.model_fields}
    assert not [n for n in names if "author" in n or "abstract" in n]


def test_galaxy_points_align_with_doc_ordinals(tmp_path):
    cfg, work = _work(tmp_path)
    search(cfg)
    files, _ = search_files(cfg, work, CODE)
    g = files["galaxy.json"]
    assert g.n == files["search/meta.json"].n_docs == 3 and g.topics == ["T000000", "T000001"]
    assert g.x == [0, -1, 32768] and g.y == [65535, -1, 32768] and g.yr == [2020, 2022, 2021]
    rows = files["search/docs-000.json"].docs + files["search/docs-001.json"].docs
    assert [g.topics[t] if t >= 0 else None for t in g.t] == [r[5] for r in rows]


def test_galaxy_and_search_skips_carry_a_reason(tmp_path):
    cfg, work = _work(tmp_path, galaxy=False)
    search(cfg)
    files, skipped = search_files(cfg, work, CODE)
    assert "search/meta.json" in files and "galaxy.json" not in files and "09_galaxy" in skipped["galaxy"]
    cfg["layout"]["galaxy"] = False
    search(cfg)
    assert search_files(cfg, work, CODE)[1] == {"galaxy": "layout.galaxy is false"}
    cfg["search"]["enabled"] = False
    search(cfg)
    files, skipped = search_files(cfg, work, CODE)
    assert files == {} and skipped["search"] == "search.enabled is false" and "search" in skipped["galaxy"]
    assert not (work / "20_docs.parquet").exists()                       # stale tables of the last run removed
    assert search_files(cfg, tmp_path / "nowhere", CODE) == ({}, {})       # step never ran: no module, no reason


def test_an_empty_window_publishes_empty_but_valid_files(tmp_path):
    cfg, work = _work(tmp_path)
    (work / "06_meta.json").write_text(json.dumps({"years": [2030]}), encoding="utf-8")
    assert search(cfg)["n_docs"] == 0
    files, skipped = search_files(cfg, work, CODE)
    assert skipped == {} and files["search/meta.json"].doc_shards == 0 and files["galaxy.json"].n == 0
    assert len([k for k in files if "/idx-" in k]) == 4 and not [k for k in files if "/docs-" in k]


def test_contract_paths_steps_and_offline_exclusion(tmp_path):
    assert C.model_for("search/idx-007.json") is C.SearchIndexShard
    assert C.model_for("search/docs-1234.json") is C.SearchDocShard
    assert C.model_for("search/meta.json") is C.SearchMeta and C.model_for("galaxy.json") is C.GalaxyFile
    assert STEPS.index("references") < STEPS.index("search") < STEPS.index("export")
    cfg = load_config(None)
    assert cfg["export"]["offline_exclude"] == ["match.json", "search", "galaxy.json"]
    rel = tmp_path / "rel"
    (rel / "search").mkdir(parents=True)
    for name in ("overview.json", "galaxy.json", "search/meta.json", "search/idx-000.json", "searchable.json"):
        (rel / name).write_text("{}", encoding="utf-8")
    kept = set(offline_bundle(rel, {}, cfg["export"]["offline_exclude"])["files"])
    assert kept == {"overview.json", "searchable.json"}


@pytest.mark.slow
def test_twenty_thousand_titles_index_within_a_minute():
    rng = np.random.default_rng(7)
    th = ["การพัฒนา", "รูปแบบ", "การเรียนรู้", "นักศึกษา", "ชุมชน", "การท่องเที่ยว", "เศรษฐกิจ", "ผู้สูงอายุ",
          "นวัตกรรม", "สุขภาพ", "เกษตรกร", "ภาคเหนือ", "ของ", "ใน", "เพื่อ"]
    en = ["development", "model", "learning", "students", "community", "tourism", "economy", "elderly", "innovation",
          "health", "farmers", "northern", "thailand", "of", "the"]
    n = 20_000
    docs = pd.DataFrame({
        "ordinal": np.arange(n),
        "title_th": ["".join(rng.choice(th, 6)) + f" {i}" for i in range(n)],
        "title_en": [" ".join(rng.choice(en, 7)) + f" v{i}" for i in range(n)],
        "keywords_th": ["; ".join(rng.choice(th, 3)) for _ in range(n)],
        "keywords_en": ["; ".join(rng.choice(en, 3)) for _ in range(n)]})
    t0 = time.time()
    postings, vocab = build_postings(docs, 24, 1)
    assert time.time() - t0 < 60
    assert postings["ordinal"].nunique() == n and len(vocab) > n            # every v<i> is its own token
