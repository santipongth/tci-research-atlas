"""Gap finder and concentration risk: HHI / top share, few institutions, weak bridges, world opportunities."""
from pathlib import Path

import pandas as pd
import pytest

from atlas.gaps import concentration, few_institution_topics, gaps, weak_bridges
from atlas.institutions import institutions
from atlas.io_utils import read_table, write_table
from atlas.pipeline import STEPS
from tests.p2_work import make_p2_work


def test_concentration_hhi_and_top_share():
    df = pd.DataFrame({"article_id": [1, 2, 3, 4, 4], "unit": [7] * 5, "item": ["a", "a", "a", "b", "a"]})
    out = concentration(df, "unit", "item").set_index("unit")
    assert out.loc[7, "articles"] == 4 and out.loc[7, "top_key"] == "a" and out.loc[7, "top_share"] == 1.0
    assert out.loc[7, "hhi"] == pytest.approx(0.8 ** 2 + 0.2 ** 2)


def test_weak_bridges_and_few_institution_topics():
    edges = pd.DataFrame({"s": [1, 2, 1], "t": [2, 3, 3], "w": [0.7, 0.9, 0.5]})
    out = weak_bridges(edges, {1: {"a", "b"}, 2: {"a", "b"}, 3: {"c"}}, 0.6, 0.1, 10)
    assert list(zip(out["s"], out["t"])) == [(2, 3)] and out.iloc[0]["jaccard"] == 0.0
    status = pd.Series({1: "STABLE", 2: "EMERGING", 3: "WATCH"})
    assert few_institution_topics(status, pd.Series({1: 1, 2: 9, 3: 2}), ["EMERGING", "WATCH"], 5).to_dict() == {3: 2}


def test_step_lists_world_gaps_concentration_and_thin_topics(tmp_path):
    cfg = make_p2_work(tmp_path)
    cfg["risk"]["min_articles"] = 5
    work = Path(cfg["pipeline"]["work_dir"])
    institutions(cfg)
    write_table(pd.DataFrame({"topic_id": [1, 2, 3], "group_id": [14, 14, 17], "group_en": ["B", "B", "C"],
                              "group_th": ["ข", "ข", "ค"], "subfield_id": ["1409", "1406", "1702"],
                              "subfield_en": ["Tourism", "Marketing", "Artificial Intelligence"],
                              "vote_share": [0.9] * 3, "cross_field": [False] * 3, "source": ["openalex"] * 3}),
                work / "10_taxonomy.parquet")
    write_table(pd.DataFrame({"subfield_id": ["1702", "1406"], "subfield_en": ["Artificial Intelligence", "Marketing"],
                              "field_id": ["17", "14"], "world_R": [50_000, 9_000], "world_B": [30_000, 9_000],
                              "country_R": [100, 400], "country_B": [50, 300], "tci_R": [12, 21],
                              "world_ratio": [1.67, 1.0], "activity_index": [0.18, 2.1], "country_share": [0.002, 0.04],
                              "opportunity": [True, False]}), work / "17_benchmark.parquet")
    gaps(cfg)
    world = read_table(work / "18_gap_world.parquet")
    assert world["subfield_id"].tolist() == ["1702"] and world.iloc[0]["topics"] == "3"
    conc = read_table(work / "18_concentration.parquet")
    t3 = conc[(conc["scope"] == "topic") & (conc["unit"] == 3)].set_index("kind")
    assert t3.loc["journal", "top_key"] == "so03:J2" and t3.loc["journal", "top_share"] == 1.0
    assert bool(t3.loc["journal", "concentrated"]) and bool(t3.loc["institution", "concentrated"])
    assert (conc["articles"] >= 5).all()
    few = read_table(work / "18_gap_few_institutions.parquet")
    assert few.set_index("topic_id")["institutions"].to_dict() == {3: 1}          # EMERGING, one institution
    assert STEPS.index("benchmark") < STEPS.index("gaps") < STEPS.index("export")
