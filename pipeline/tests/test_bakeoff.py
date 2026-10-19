import math

import numpy as np
import pandas as pd
import pytest

from atlas.bakeoff import (
    ari_stability,
    clustering_bakeoff,
    embedding_bakeoff,
    knn_accuracy,
    neighbor_purity,
    npmi_coherence,
    purity,
    render_report,
    run_bakeoff,
)
from atlas.config import load_config
from atlas.io_utils import write_table

WORDS = {0: "ข้าว เกษตรกร ผลผลิต rice farmer yield", 1: "เบาหวาน อินซูลิน ผู้ป่วย diabetes insulin patient",
         2: "ท่องเที่ยว โฮมสเตย์ ชุมชน tourism homestay community"}


def _blobs(k=3, n_per=40, seed=0, noise=0.05):
    rng = np.random.default_rng(seed)
    X = np.vstack([np.eye(16)[c] + rng.normal(0, noise, (n_per, 16)) for c in range(k)])
    return (X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32), np.repeat(np.arange(k), n_per)


def test_metric_values_on_known_inputs():
    X, y = _blobs()
    assert knn_accuracy(X, y, 5, 0.3, 0) == 1.0 and neighbor_purity(X, y, 5) == 1.0
    assert purity(np.array([0, 0, 1, 1, -1]), ["a", "b", "c", "c", "a"]) == pytest.approx(0.75)
    assert ari_stability([np.array([0, 0, 1, 1]), np.array([1, 1, 0, 0])]) == pytest.approx(1.0)
    docs = [{"a", "b"}] * 50 + [{"c", "d"}] * 50
    assert npmi_coherence({0: ["a", "b"]}, docs, 10) == pytest.approx(1.0)
    assert npmi_coherence({0: ["a", "c"]}, docs, 10) == pytest.approx(-1.0)
    assert math.isnan(npmi_coherence({0: ["zzz"]}, docs, 10))


def test_embedding_bakeoff_ranks_a_real_signal_above_noise():
    texts = [f"{WORDS[t]} เอกสาร {i}" for i in range(60) for t in (0, 1, 2)]
    journals = [f"j{t}" for i in range(60) for t in (0, 1, 2)]
    truth = [t for i in range(60) for t in (0, 1, 2)]
    from atlas.embed import lite_embed

    lite = {"dim": 16, "ngram_min": 2, "ngram_max": 4, "max_features": 5000, "min_df": 1}
    cands = {"lite": lambda t: lite_embed(t, lite, 0),
             "noise": lambda t: np.random.default_rng(0).normal(size=(len(t), 16)),
             "broken": lambda t: (_ for _ in ()).throw(RuntimeError("no key"))}
    ref = ([WORDS[0]] * 10 + [WORDS[1]] * 10, ["1102"] * 10 + ["2712"] * 10)
    df = embedding_bakeoff(texts, journals, cands, k=5, holdout_frac=0.3, seed=1, truth=truth, reference=ref)
    r = df.set_index("candidate")
    assert r.loc["lite", "journal_knn_acc"] > 0.95 > r.loc["noise", "journal_knn_acc"]
    assert r.loc["lite", "subfield_knn_acc"] == 1.0 and r.loc["lite", "truth_purity"] > 0.95
    assert "no key" in r.loc["broken", "error"]


def test_clustering_bakeoff_and_report():
    X, y = _blobs(k=3, n_per=60)
    texts = [WORDS[int(t)] for t in y]
    ccfg = load_config(None)["clustering"]
    ccfg.update(reducer="pca")
    ccfg["fine"].update(hdbscan_min_cluster_size=20, hdbscan_min_samples=5)
    ccfg["leiden"].update(k=10, min_cluster_size=20)
    df = clustering_bakeoff(X, texts, ccfg, ["hdbscan", "hdbscan_fast", "leiden"], [1, 2], truth=y, npmi_top_n=5)
    h = df.set_index("algorithm").loc["hdbscan"]
    assert h["n_topics"] == 3 and h["ari_stability"] == 1.0 and h["purity"] == 1.0 and h["npmi"] > 0.5
    assert h["ari_vs_first"] == 1.0
    assert set(df["algorithm"]) == {"hdbscan", "hdbscan_fast", "leiden"}   # optional ones may be error rows
    fast = df.set_index("algorithm").loc["hdbscan_fast"]
    assert fast["error"] or fast["ari_vs_first"] > 0.95                   # same partition as sklearn
    md = render_report(None, df, {"sample": len(X)})
    assert md.startswith("# Bake-off report") and "| hdbscan |" in md and "Best stable clustering" in md


def test_best_embedding_line_ranks_by_the_mean_of_the_available_scores_and_is_advisory():
    emb = pd.DataFrame({"candidate": ["fast-journal", "balanced"], "journal_knn_acc": [0.95, 0.85],
                        "subfield_knn_acc": [0.40, 0.80], "truth_purity": [0.30, 0.90]})
    md = render_report(emb, None, {})
    assert "**balanced**" in md and "advisory" in md                  # not the journal-accuracy winner alone
    no_ref = emb.assign(subfield_knn_acc=float("nan"), truth_purity=float("nan"))
    assert "**fast-journal**" in render_report(no_ref, None, {})       # only journal accuracy available


def test_run_bakeoff_from_a_work_dir(make_cfg, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg["bakeoff"].update(sample=120, seeds=[1, 2], algorithms=["hdbscan"])
    cfg["clustering"].update(reducer="pca")
    cfg["clustering"]["fine"].update(hdbscan_min_cluster_size=15, hdbscan_min_samples=5)
    X, y = _blobs(k=3, n_per=50)
    work = tmp_path / "work"
    ids = [f"a{i}" for i in range(len(y))]
    write_table(pd.DataFrame({"article_id": ids, "doc_text": [WORDS[int(t)] for t in y],
                              "journal_name": [f"j{t}" for t in y]}), work / "02_docs.parquet")
    np.save(work / "03_embeddings.npy", X)
    truth = tmp_path / "truth.csv"
    pd.DataFrame({"article_id": ids, "topic": y}).to_csv(truth, index=False)
    md = run_bakeoff(cfg, "all", truth)
    assert "## Embedding models" in md and "lite (configured)" in md and "| hdbscan |" in md
