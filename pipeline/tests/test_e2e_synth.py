import json
from pathlib import Path

import pandas as pd
import pytest

from atlas.config import load_config
from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run
from atlas.synth import TOPICS, generate

PIPELINE = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_synthetic_corpus_recovers_planted_signals(tmp_path):
    corpus = tmp_path / "synth"
    generate(corpus, n=20_000, seed=7)
    cfg = load_config(PIPELINE / "configs" / "ci.yaml")
    cfg["pipeline"].update(work_dir=str(tmp_path / "work"), output_dir=str(tmp_path / "out"),
                           state_dir=str(tmp_path / "state"))
    cfg["input"]["path"] = str(corpus)
    run(cfg, STEPS)

    em = read_table(tmp_path / "work" / "07_emerging.parquet").set_index("topic_id")
    fine = read_table(tmp_path / "work" / "04_fine_topics.parquet")
    truth = pd.read_csv(corpus / "_truth.csv")
    tt = fine.merge(truth, on="article_id")
    tt = tt[tt["fine_topic"] >= 0]

    def status_of(role):
        tid = tt[tt["role"] == role]["fine_topic"].value_counts().index[0]
        return em.loc[tid, "status"], bool(em.loc[tid, "journal_driven"])

    assert status_of("emerging") == ("EMERGING", False)
    assert status_of("confound") == ("WATCH", True)
    assert status_of("hot")[0] == "HOT"
    assert status_of("declining")[0] == "DECLINING"
    dominant = tt.groupby("fine_topic")["role"].agg(lambda x: x.value_counts().index[0])
    stable = em.loc[dominant[dominant == "stable"].index, "status"]
    assert not stable.isin(["HOT", "DECLINING", "EMERGING"]).any()
    assert len(em) <= 2 * len(TOPICS)
    purity = tt.groupby("fine_topic")["topic"].agg(lambda x: x.value_counts().iloc[0] / len(x)).mean()
    assert purity >= 0.95
    atlas = json.loads((tmp_path / "out" / "atlas_data.json").read_text(encoding="utf-8"))
    assert atlas["meta"]["definition_version"] == 2
