"""SDG + Thai frameworks at topic level: packaged goals, lexical mapping, cosine mapping (no network)."""
import json
from pathlib import Path

import numpy as np
import pytest

from atlas.pipeline import STEPS
from atlas.sdg import FrameworkError, goal_patterns, load_frameworks, pick, sdg, similarity_scores
from tests.p2_work import make_p2_work


def test_packaged_frameworks_are_complete():
    fw = load_frameworks()
    assert [f["key"] for f in fw["frameworks"]] == ["sdg", "bcg", "hesi", "nesdp13"]
    assert {f["key"]: len(f["goals"]) for f in fw["frameworks"]} == {"sdg": 17, "bcg": 3, "hesi": 4, "nesdp13": 13}
    assert [g["number"] for g in fw["frameworks"][0]["goals"]] == list(range(1, 18))


def test_a_bad_frameworks_file_is_refused(tmp_path):
    p = tmp_path / "f.yaml"
    p.write_text("frameworks:\n- {key: x, th: x, en: x, goals: [{id: a1, number: 1, th: a, en: a, keywords: []}]}\n",
                 encoding="utf-8")
    with pytest.raises(FrameworkError, match="keywords"):
        load_frameworks(p)


def test_latin_keywords_are_whole_words_and_thai_ones_text():
    rx = goal_patterns([{"id": "g", "keywords": ["aging", "การเรียนรู้"]}])["g"]
    assert rx.search("healthy aging") and not rx.search("managing staff") and rx.search("ชุมชนแห่งการเรียนรู")


def test_lexical_mapping_on_titles_and_keywords(tmp_path):
    cfg = make_p2_work(tmp_path)                       # provider "local" but no centroids → auto = lexical
    out = sdg(cfg)
    pairs = set(zip(out["topic_id"], out["goal_id"]))
    assert {(3, "sdg-04"), (1, "sdg-08"), (1, "nesdp13-02"), (2, "nesdp13-06")} <= pairs
    assert (2, "sdg-04") not in pairs
    assert out.groupby(["topic_id", "framework"]).size().max() <= cfg["sdg"]["max_goals_per_topic"]
    meta = json.loads((Path(cfg["pipeline"]["work_dir"]) / "16_sdg_meta.json").read_text(encoding="utf-8"))
    assert meta["method"] == "lexical" and meta["frameworks"][0]["goals"][3]["id"] == "sdg-04"
    assert STEPS.index("institutions") < STEPS.index("sdg") < STEPS.index("export")


def test_similarity_scores_rank_goals_by_cosine():
    s = similarity_scores(np.array([[1.0, 0.0], [0.0, 2.0]]), [7, 8], np.array([[0.9, 0.1], [0.1, 0.9]]),
                          ["sdg-01", "sdg-02"])
    top = pick(s, {"sdg-01": "sdg", "sdg-02": "sdg"}, 0.5, 1)
    assert list(zip(top["topic_id"], top["goal_id"])) == [(7, "sdg-01"), (8, "sdg-02")]


def test_embedding_runs_keep_every_cosine_for_sdg_scores(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    import atlas.sdg as sdg_mod
    from atlas.cli import app
    from atlas.io_utils import read_table
    from atlas.sdg import score_report

    cfg = make_p2_work(tmp_path)
    work = Path(cfg["pipeline"]["work_dir"])
    assert "method lexical" in (sdg(cfg), score_report(cfg))[1]                    # lexical: nothing to calibrate
    n_goals = sum(len(f["goals"]) for f in load_frameworks()["frameworks"])
    rng = np.random.default_rng(0)
    np.save(work / "04_centroids.npy", rng.normal(size=(3, 8)))
    (work / "04_centroid_ids.json").write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setattr(sdg_mod, "embed_texts", lambda cfg, texts, emb=None: rng.normal(size=(len(texts), 8)))
    cfg["sdg"]["method"] = "embedding"
    sdg(cfg)
    scores = read_table(work / "16_topic_goal_scores.parquet")
    assert len(scores) == 3 * n_goals and set(scores.columns) == {"topic_id", "framework", "goal_id", "score"}
    report = score_report(cfg)
    rows = [ln.split() for ln in report.splitlines() if ln.strip()[:4] in ("0.30", "0.35", "0.40", "0.45",
                                                                           "0.50", "0.55", "0.60")]
    assert [r[0] for r in rows] == ["0.30", "0.35", "0.40", "0.45", "0.50", "0.55", "0.60"]
    links = [int(r[1].replace(",", "")) for r in rows]
    assert links == sorted(links, reverse=True) and links[0] == int((scores["score"] >= 0.30).sum())
    assert "quantiles" in report
    monkeypatch.chdir(tmp_path)
    (tmp_path / "c.yaml").write_text(f"pipeline: {{work_dir: '{work.as_posix()}'}}\n", encoding="utf-8")
    res = CliRunner().invoke(app, ["sdg-scores", "-c", str(tmp_path / "c.yaml")])
    assert res.exit_code == 0 and "threshold" in res.output
