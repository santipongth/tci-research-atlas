"""'Match my abstract' index: analyzer parity with the web, ranking, size bound, no text published."""
import json
import math
from collections import Counter
from pathlib import Path

import pytest

from atlas.journals import journals
from atlas.matcher import PARITY_CASES, analyze, char_grams, match, match_fold
from atlas.pipeline import STEPS
from tests.p2_work import TOPIC_TEXT, make_p2_work

PARITY = Path(__file__).parent / "fixtures" / "match_parity.json"
SARA_AM = "\N{THAI CHARACTER SARA AM}"


def test_fold_matches_the_web_search_fold():
    assert match_fold("ความต้องการ") == "ความตองการ"
    assert match_fold("การท" + "\N{THAI CHARACTER NIKHAHIT}\N{THAI CHARACTER SARA AA}" + "งาน") == f"การท{SARA_AM}งาน"
    assert match_fold("  Café\tNaïve  ") == "cafe naive"
    assert match_fold("แชต" + chr(0x200B) + "บอต") == "แชตบอต"
    assert match_fold(None) == ""


def test_trigrams_follow_char_wb():
    assert char_grams("ab") == [" ab", "ab "]
    assert char_grams("a b") == [" a ", " b "]
    assert char_grams("cat") == [" ca", "cat", "at "]
    assert char_grams("") == []


def test_parity_fixture_is_up_to_date():
    cases = json.loads(PARITY.read_text(encoding="utf-8"))
    assert [c["text"] for c in cases] == list(PARITY_CASES)
    for c in cases:
        assert c["fold"] == match_fold(c["text"]) and c["grams"] == analyze(c["text"]), c["text"]


def _score(index: dict, text: str) -> list[tuple[float, int]]:
    """Reference scorer = web/src/lib/matcher.ts rankTopics: (1 + ln tf)·idf, unit length, dot product."""
    pos = {g: i for i, g in enumerate(index["grams"])}
    tf = Counter(g for g in analyze(text) if g in pos)
    q = {pos[g]: (1 + math.log(n)) * index["idf"][pos[g]] for g, n in tf.items()}
    norm = math.sqrt(sum(v * v for v in q.values())) or 1.0
    return sorted(((sum(q.get(i, 0.0) * w for i, w in zip(t["terms"], t["weights"])) / norm, t["topic_id"])
                   for t in index["topics"]), reverse=True)


@pytest.fixture
def built(tmp_path):
    cfg = make_p2_work(tmp_path)
    journals(cfg)
    return cfg, match(cfg)


def test_index_ranks_the_right_topic_and_lists_active_journals(built):
    cfg, index = built
    assert {t["topic_id"] for t in index["topics"]} == {1, 2, 3}
    for tid, text in TOPIC_TEXT.items():
        assert _score(index, text)[0][1] == tid
    t = index["topics"][0]
    assert len(t["terms"]) == len(t["weights"]) <= index["max_terms"]
    assert math.isclose(sum(w * w for w in t["weights"]), 1.0, abs_tol=1e-3)
    assert len(index["grams"]) == len(index["idf"]) and max(i for t in index["topics"] for i in t["terms"]) < len(
        index["grams"])
    assert {j["journal_key"] for j in index["journals"]} == {"so02:J1", "so03:J2"}    # J3 is low data
    saved = json.loads((Path(cfg["pipeline"]["work_dir"]) / "14_match.json").read_text(encoding="utf-8"))
    assert saved["bytes"] == index["bytes"] and saved["min_query_chars"] == 40


def test_the_index_is_size_bounded_and_carries_no_text(tmp_path, capsys):
    cfg = make_p2_work(tmp_path)
    cfg["match"].update(max_terms=100, min_terms=20, max_bytes=5_000)
    index = match(cfg)
    assert 20 <= index["max_terms"] < 100
    assert index["bytes"] <= 5_000 or "WARNING" in capsys.readouterr().out
    blob = json.dumps(index, ensure_ascii=False)
    assert all(len(g) <= 3 for g in index["grams"]) and TOPIC_TEXT[1][:12] not in blob


def test_disabled_match_removes_the_index(built):
    cfg, _ = built
    cfg["match"]["enabled"] = False
    assert match(cfg) == {}
    assert not (Path(cfg["pipeline"]["work_dir"]) / "14_match.json").exists()
    assert STEPS.index("journals") < STEPS.index("match") < STEPS.index("export")
