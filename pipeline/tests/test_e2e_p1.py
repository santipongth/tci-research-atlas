"""P1 acceptance (slow): two synthetic "quarters" through the whole pipeline.

Q1 = 20K-article synthetic corpus; Q2 = Q1 + 2K late-arriving articles, re-clustered from scratch
(topics.mode: fit — the hard case for stable ids). Checks the spec's P1 verification items:
stable ids (≥ 90% kept, ARI ≥ 0.8), forecast 80% intervals cover 70–90% in an honest hold-out,
shown forecasts have MASE < 1, taxonomy and emerging keywords recover what was planted, the map
stays put, narratives exist for the planted signals, and the contract v2 release validates (diffs
cleanly against Q1) and lands on a static site with latest.json and the offline HTML.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import adjusted_rand_score

from atlas.config import load_config
from atlas.forecast import rolling_coverage
from atlas.io_utils import read_table
from atlas.pipeline import STEPS, run
from atlas.publish import publish
from atlas.synth import SUBFIELDS, generate, reference_works
from atlas.validate import validate_release

PIPELINE = Path(__file__).resolve().parent.parent


def _cfg(root: Path, release: str, corpus: Path, ref: Path, mode: str) -> dict:
    cfg = load_config(PIPELINE / "configs" / "ci.yaml")
    cfg["pipeline"].update(work_dir=str(root / f"work_{release}"), output_dir=str(root / "out"),
                           state_dir=str(root / "state"), release=release)
    cfg["input"]["path"] = str(corpus)
    cfg["taxonomy"]["reference_path"] = str(ref)
    cfg["topics"]["mode"] = mode
    return cfg


@pytest.mark.slow
def test_p1_two_quarters_on_the_synthetic_corpus(tmp_path):
    corpus = tmp_path / "corpus"
    generate(corpus / "base", n=20_000, seed=7)
    ref = tmp_path / "reference.jsonl"
    ref.write_text("\n".join(json.dumps(w) for w in reference_works()), encoding="utf-8")
    run(_cfg(tmp_path, "2026Q1", corpus / "base", ref, "auto"), STEPS)
    generate(corpus / "extra", n=2_000, seed=8, id_offset=1_000_000)
    cfg2 = _cfg(tmp_path, "2026Q2", corpus, ref, "fit")
    run(cfg2, STEPS)
    w1, w2 = tmp_path / "work_2026Q1", tmp_path / "work_2026Q2"

    # stable topic ids across a full refit
    meta = json.loads((w2 / "04_topics_meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "fit" and meta["kept_fraction"] >= 0.9
    both = read_table(w1 / "04_fine_topics.parquet").merge(read_table(w2 / "04_fine_topics.parquet"),
                                                         on="article_id", suffixes=("_1", "_2"))
    assert adjusted_rand_score(both["fine_topic_1"], both["fine_topic_2"]) >= 0.8

    # forecast: honest hold-out backtest (2-year horizon from 3 successive cut-off years, pooled)
    series = read_table(w2 / "06_series.parquet")
    m6 = json.loads((w2 / "06_meta.json").read_text(encoding="utf-8"))
    totals = pd.Series({int(y): int(n) for y, n in m6["totals"].items()}).sort_index()
    cov = rolling_coverage(series, totals, int(m6["last_complete_year"]), cfg2["forecast"], n_cuts=3)
    assert 0.70 <= cov["coverage80"] <= 0.90, cov
    fc = read_table(w2 / "08_forecasts.parquet")
    assert fc["show"].any() and (fc.loc[fc["show"], "mase"] < 1).all()

    # taxonomy + planted signals
    truth = pd.concat([pd.read_csv(corpus / "base" / "_truth.csv"), pd.read_csv(corpus / "extra" / "_truth.csv")])
    tt = read_table(w2 / "04_fine_topics.parquet").merge(truth, on="article_id")
    dominant = tt[tt["fine_topic"] >= 0].groupby("fine_topic")["topic"].agg(lambda s: s.value_counts().index[0])
    tax = read_table(w2 / "10_taxonomy.parquet").set_index("topic_id")
    hits = [tax.loc[t, "subfield_id"] == SUBFIELDS[k][0] for t, k in dominant.items()]
    assert np.mean(hits) >= 0.9
    em = read_table(w2 / "07_emerging.parquet").set_index("topic_id")
    role_topic = tt[tt["fine_topic"] >= 0].groupby("role")["fine_topic"].agg(lambda s: s.value_counts().index[0])
    assert em.loc[role_topic["emerging"], "status"] == "EMERGING"
    assert em.loc[role_topic["confound"], "status"] == "WATCH"
    assert em.loc[role_topic["hot"], "status"] == "HOT" and em.loc[role_topic["declining"], "status"] == "DECLINING"
    kw = read_table(w2 / "07_keywords.parquet").set_index("key")
    assert bool(kw.loc["chatgpt", "emerging"]) and bool(kw.loc["buddhism", "journal_driven"])

    # the map stays put
    def topic_xy(work):
        lay = read_table(work / "09_layout.parquet")
        return lay[lay["kind"] == "topic"].set_index("id")[["x", "y"]]

    p1, p2 = topic_xy(w1), topic_xy(w2)
    common = p1.index.intersection(p2.index)
    moved = np.hypot(*(p2.loc[common].to_numpy() - p1.loc[common].to_numpy()).T)
    assert np.median(moved) < 0.05 * cfg2["layout"]["view_w"]

    # narratives (template provider — no LLM in CI) for the planted signals
    narr = read_table(w2 / "11_narratives.parquet").set_index("topic_id")
    assert role_topic["emerging"] in narr.index and narr.loc[role_topic["declining"], "source"] == "template"
    assert json.loads((w2 / "11_brief.json").read_text(encoding="utf-8"))["brief"]["source"] == "template"

    # contract v2 release validates, diffs cleanly against Q1 and lands on a static site
    rep = validate_release(tmp_path / "out" / "data" / "2026Q2", None, cfg2["validation"])
    assert not rep.errors, rep.errors
    assert rep.stats["kept_ids"] >= 0.9 and rep.previous_dir is not None
    man = json.loads((tmp_path / "out" / "data" / "2026Q2" / "manifest.json").read_text(encoding="utf-8"))
    assert {"institutions", "regions", "sdg", "gaps"} <= set(man["modules"]) and man["skipped_modules"].get("global")
    assert all((tmp_path / "out" / "data" / "2026Q2" / f).is_file() for f in ("search/meta.json", "kwtrends.json"))
    site = tmp_path / "site"
    site.mkdir()
    (site / "offline-template.html").write_text('<script type="application/json" id="atlas-data"></script>',
                                                encoding="utf-8")
    r = publish(cfg2, site=site, allow_warnings=True, tarball=True)
    assert json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))["release"] == "2026Q2"
    assert Path(r["offline_html"]).stat().st_size > 100_000 and Path(r["tarball"]).stat().st_size > 0
