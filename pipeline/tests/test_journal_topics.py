"""Topic mix, peer journals (D4), scope drift (D1) and the special-issue finder (D5)."""
import numpy as np
import pandas as pd
import pytest

from atlas.journal_topics import (
    journal_opportunities,
    peer_journals,
    scope_drift,
    special_issue,
    topic_mix,
    topic_shifts,
)


def _jt(spec):
    """spec: {(journal, topic, year): n} → one row per article."""
    rows = [(j, t, y) for (j, t, y), n in spec.items() for _ in range(n)]
    return pd.DataFrame(rows, columns=["journal_key", "topic_id", "year"])


def test_topic_mix_shares_sum_to_one_per_journal():
    jt = _jt({("A", 1, 2020): 3, ("A", 2, 2021): 1, ("B", 2, 2021): 2, ("A", 1, 2010): 9})
    m = topic_mix(jt, 2020, 2021)
    a = m[m["journal_key"] == "A"].set_index("topic_id")
    assert a.loc[1, "count"] == 3 and a.loc[1, "share"] == pytest.approx(0.75)
    assert m.groupby("journal_key")["share"].sum().round(9).eq(1).all()


def test_peers_are_the_most_similar_eligible_journals():
    jt = _jt({("A", 1, 2022): 8, ("A", 2, 2022): 2, ("B", 1, 2022): 7, ("B", 2, 2022): 3,
              ("C", 3, 2022): 10, ("D", 1, 2022): 1})
    m = topic_mix(jt, 2022, 2022)
    peers = peer_journals(m, {"A", "B", "C"}, k=2, min_similarity=0.2)
    assert [p for p, _ in peers["A"]] == ["B"]                     # C shares no topic; D is not eligible
    assert peers["A"][0][1] == pytest.approx(0.62 / np.sqrt(0.68 * 0.58), abs=1e-4)
    assert peers["C"] == []
    assert peer_journals(m, {"A", "B"}, k=0, min_similarity=0.0) == {}


def test_scope_drift_is_zero_for_a_steady_journal_and_high_for_a_new_scope():
    steady = {("A", 1, y): 10 for y in range(2015, 2023)}
    moved = {("B", 1, y): 10 for y in range(2015, 2021)} | {("B", 2, 2021): 10, ("B", 2, 2022): 10}
    d = scope_drift(_jt(steady | moved), list(range(2018, 2023)), ref_years=3, min_articles=10)
    a = d[d["journal_key"] == "A"].set_index("year")["distance"]
    b = d[d["journal_key"] == "B"].set_index("year")["distance"]
    assert (a == 0).all() and b[2020] == 0 and b[2021] == pytest.approx(1.0)
    assert 0 < b[2022] < 1                                         # its reference years now mix both topics
    small = scope_drift(_jt({("C", 1, 2020): 3, ("C", 1, 2019): 30}), [2020], 3, 10)
    assert small["articles"].tolist() == [3] and np.isnan(small["distance"].iloc[0])


def test_topic_shifts_list_gains_and_losses():
    jt = _jt({("A", 1, 2016): 10, ("A", 2, 2016): 10, ("A", 1, 2023): 4, ("A", 3, 2023): 16})
    s = topic_shifts(jt, (2014, 2018), (2022, 2024), n=5, min_articles=10)
    gained = s[s["kind"] == "gained"].set_index("topic_id")
    lost = s[s["kind"] == "lost"].set_index("topic_id")
    assert list(gained.index) == [3] and gained.loc[3, "share_after"] == pytest.approx(0.8)
    assert list(lost.index) == [2, 1] and lost.loc[2, "share_before"] == pytest.approx(0.5)
    assert topic_shifts(jt, (2014, 2018), (2022, 2024), n=5, min_articles=50).empty


def test_special_issue_finds_emerging_topics_with_few_host_journals():
    jt = _jt({("A", 7, 2023): 5, ("B", 7, 2024): 1, ("A", 8, 2023): 4, ("B", 8, 2023): 4, ("C", 8, 2023): 4,
              ("A", 9, 2023): 9})
    status = pd.Series({7: "EMERGING", 8: "EMERGING", 9: "STABLE", 10: "WATCH"})
    s = special_issue(jt, status, ["EMERGING", "WATCH"], min_host_articles=3, max_hosts=2).set_index("topic_id")
    assert list(s.index) == [7]                                    # 8 has 3 hosts; 9 is STABLE; 10 has no articles
    assert s.loc[7, "hosts"] == 1 and s.loc[7, "top_host_share"] == pytest.approx(5 / 6)
    assert s.loc[7, "articles_R"] == 6


def test_opportunities_rank_in_scope_before_adjacent():
    opps = pd.DataFrame({"topic_id": [7, 11], "hosts": [1, 0], "top_host_share": [1.0, 0.0], "articles_R": [6, 2]})
    mix = topic_mix(_jt({("A", 7, 2023): 2, ("A", 1, 2023): 9, ("B", 1, 2023): 5}), 2023, 2023)
    edges = pd.DataFrame({"s": [1], "t": [11], "w": [0.7]})
    o = journal_opportunities(opps, mix, edges, scope_topics=5, per_journal=5)
    a = o[o["journal_key"] == "A"]
    assert a["topic_id"].tolist() == [7, 11] and a["reason"].tolist() == ["in_scope", "adjacent"]
    assert a["journal_articles"].tolist() == [2, 0]
    assert o[o["journal_key"] == "B"]["reason"].tolist() == ["adjacent"]
    assert journal_opportunities(opps, mix, edges.iloc[0:0], 5, 1)["topic_id"].tolist() == [7]
