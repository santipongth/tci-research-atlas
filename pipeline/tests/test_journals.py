"""Step `journals`: one table per editors' feature, aggregates only."""
import json

import pandas as pd
import pytest

from atlas.io_utils import read_table
from atlas.journals import journals
from atlas.methods import methods
from atlas.pipeline import STEPS
from tests.p2_work import make_p2_work


@pytest.fixture
def work(tmp_path):
    cfg = make_p2_work(tmp_path)
    methods(cfg)
    journals(cfg)
    return cfg, tmp_path / "work"


def test_summary_has_identity_counts_and_rates(work):
    _, w = work
    s = read_table(w / "13_journals.parquet").set_index("journal_key")
    assert list(s.index) == ["so02:J1", "so03:J2", "so04:J3"]
    j1 = s.loc["so02:J1"]
    assert j1["code"] == "so02.J1" and j1["path"] == "J1" and not j1["in_registry"] and j1["name_th"] == ""
    assert j1["articles"] == 45 and j1["articles_window"] == 25 and j1["first_year"] == 2015 and j1["active"]
    assert j1["owner_source"] == "inferred" and j1["owner_name"] == "มหาวิทยาลัยนเรศวร"
    assert 0.5 < j1["inhouse_share"] < 1 and j1["n_orgs"] == 2 and 1 < j1["effective_orgs"] < 2
    assert j1["foreign_share"] == 0                                 # the Tokyo co-author published in 2015
    assert 0 < j1["completeness"] <= 100 and j1["methods_coverage"] == 1
    j3 = s.loc["so04:J3"]
    assert j3["low_data"] and pd.isna(j3["completeness"]) and pd.isna(j3["inhouse_share"])
    assert j3["owner_name"] == "" and pd.isna(j3["owner_source"]) and not j3["owner_matched"]   # no inferred owner


def test_topics_peers_drift_and_special_issue(work):
    _, w = work
    mix = read_table(w / "13_journal_topics.parquet")
    assert mix.groupby("journal_key")["share"].sum().round(9).eq(1).all()
    peers = read_table(w / "13_journal_peers.parquet")
    assert set(zip(peers["journal_key"], peers["peer_key"])) == {("so02:J1", "so03:J2"), ("so03:J2", "so02:J1")}
    drift = read_table(w / "13_journal_drift.parquet")
    j2 = drift[drift["journal_key"] == "so03:J2"].set_index("year")["distance"]
    assert pd.isna(j2[2020]) and j2[2023] > 0                       # 2020 has no reference years; 2022+ adds topic 3
    si = read_table(w / "13_special_issue.parquet")
    assert si["topic_id"].tolist() == [3] and si["hosts"].tolist() == [1]
    opp = read_table(w / "13_journal_opportunities.parquet")
    got = {(r.journal_key, r.reason) for r in opp.itertuples()}
    assert got == {("so03:J2", "in_scope"), ("so02:J1", "adjacent")}
    comp = read_table(w / "13_journal_completeness.parquet")
    assert set(comp["journal_key"]) == {"so02:J1", "so03:J2"}       # low-data journals publish no rates
    meth = read_table(w / "13_journal_methods.parquet")
    assert set(meth["method"]) >= {"survey", "interview"}
    meta = json.loads((w / "13_journals_meta.json").read_text(encoding="utf-8"))
    assert meta["windows"]["W"] == [2020, 2024] and meta["windows"]["R"] == [2022, 2024]


def test_registry_names_the_journal_and_its_owner(tmp_path):
    cfg = make_p2_work(tmp_path)
    reg = tmp_path / "journals.csv"
    reg.write_text("journal_key,name_th,tci_tier,publisher_org\nJ1,วารสาร ก,1,จุฬาลงกรณ์มหาวิทยาลัย\nnowhere,x,,\n",
                   encoding="utf-8-sig")
    cfg["journals"]["registry_path"] = str(reg)
    journals(cfg)
    s = read_table(tmp_path / "work" / "13_journals.parquet").set_index("journal_key")
    j1 = s.loc["so02:J1"]
    assert j1["in_registry"] and j1["name_th"] == "วารสาร ก" and j1["tci_tier"] == 1
    assert j1["owner_source"] == "registry" and j1["owner_name"] == "จุฬาลงกรณ์มหาวิทยาลัย" and j1["owner_matched"]
    assert 0 < j1["inhouse_share"] < 0.5
    meta = json.loads((tmp_path / "work" / "13_journals_meta.json").read_text(encoding="utf-8"))
    assert meta["registry"]["matched"] == 1 and "match no journal" in meta["registry"]["warnings"][0]


def test_step_order():
    assert STEPS.index("layout") < STEPS.index("methods") < STEPS.index("journals") < STEPS.index("export")


def test_inferred_owner_name_keeps_its_tone_marks(tmp_path):
    from atlas.io_utils import write_table
    from atlas.orgs import org_key
    from tests.p2_work import NU

    cfg = make_p2_work(tmp_path)
    w = tmp_path / "work"
    authors = read_table(w / "01_authors.parquet")
    mj = "คณะวิทยาศาสตร์ มหาวิทยาลัยแม่โจ้"
    authors["affiliation_th"] = authors["affiliation_th"].replace(NU, mj)
    authors["org_key"] = [org_key(t, e) for t, e in zip(authors["affiliation_th"], authors["affiliation_en"])]
    write_table(authors, w / "01_authors.parquet")
    journals(cfg)
    s = read_table(w / "13_journals.parquet").set_index("journal_key")
    assert s.loc["so02:J1", "owner_name"] == "มหาวิทยาลัยแม่โจ้"


def test_a_rerun_deletes_the_previous_tables_first(work):
    cfg, w = work
    assert list(w.glob("13_*"))
    (w / "06_meta.json").unlink()
    with pytest.raises(FileNotFoundError):
        journals(cfg)
    assert not list(w.glob("13_*"))
