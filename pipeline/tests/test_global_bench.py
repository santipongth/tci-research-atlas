"""Thailand vs the world (OpenAlex): share-based world growth, activity index, opportunities; skips, never fails."""
import json
from pathlib import Path

import pandas as pd
import pytest

from atlas.global_bench import benchmark
from atlas.io_utils import write_table
from atlas.pipeline import STEPS
from tests.p2_work import make_p2_work

NAMES = {"1702": "Artificial Intelligence", "2208": "Electrical and Electronic Engineering"}


def fake_fetch(calls):
    """group_by answers for domain 3 only; recent = 2022–2024, baseline = 2017–2021."""
    def fetch(path, params):
        calls.append(params)
        flt = params["filter"]
        if "primary_topic.domain.id:3" not in flt:
            return {"group_by": []}
        recent = "publication_year:2022-2024" in flt
        if "country_code:TH" in flt:
            counts = {"1702": 100, "2208": 900} if recent else {"1702": 50, "2208": 1_000}
        else:
            counts = {"1702": 50_000, "2208": 40_000} if recent else {"1702": 30_000, "2208": 60_000}
        return {"meta": {"count": sum(counts.values())}, "group_by": [
            {"key": f"https://openalex.org/subfields/{k}", "key_display_name": NAMES[k], "count": v}
            for k, v in counts.items()]}
    return fetch


def _cfg(tmp_path, source="openalex"):
    cfg = make_p2_work(tmp_path)
    work = Path(cfg["pipeline"]["work_dir"])
    write_table(pd.DataFrame({
        "topic_id": [1, 2, 3], "group_id": [22, 22, 17], "group_en": ["Engineering", "Engineering", "Computer Science"],
        "group_th": ["วิศวกรรมศาสตร์", "วิศวกรรมศาสตร์", "วิทยาการคอมพิวเตอร์"], "subfield_id": ["2208", "2208", "1702"],
        "subfield_en": [NAMES["2208"], NAMES["2208"], NAMES["1702"]], "vote_share": [0.9, 0.9, 0.9],
        "cross_field": [False, False, False], "source": [source] * 3}), work / "10_taxonomy.parquet")
    return cfg, work


def test_world_growth_activity_index_and_opportunities(tmp_path):
    cfg, work = _cfg(tmp_path)
    calls = []
    b = benchmark(cfg, fetch=fake_fetch(calls)).set_index("subfield_id")
    assert len(calls) == 16 and all(c["group_by"] == "primary_topic.subfield.id" and c["per_page"] == 200 for c in calls)
    assert b.loc["1702", "world_ratio"] == pytest.approx(5 / 3) and b.loc["1702", "activity_index"] == pytest.approx(0.18)
    assert bool(b.loc["1702", "opportunity"]) and not bool(b.loc["2208", "opportunity"])
    assert b.loc["1702", "tci_R"] == 12 and b.loc["1702", "field_id"] == "17"
    meta = json.loads((work / "17_benchmark_meta.json").read_text(encoding="utf-8"))
    assert meta["skipped"] is None and meta["recent"] == [2022, 2024] and meta["baseline"] == [2017, 2021]
    assert STEPS.index("sdg") < STEPS.index("benchmark") < STEPS.index("export")


def test_offline_or_unanchored_runs_skip_with_a_reason(tmp_path):
    cfg, work = _cfg(tmp_path)
    assert benchmark(cfg).empty                                  # the real fetcher: ATLAS_OFFLINE=1 in every test
    assert "ATLAS_OFFLINE" in json.loads((work / "17_benchmark_meta.json").read_text(encoding="utf-8"))["skipped"]
    assert not (work / "17_benchmark.parquet").exists()
    cfg, work = _cfg(tmp_path / "agg", source="agglomerative")
    assert benchmark(cfg, fetch=fake_fetch([])).empty
    assert "OpenAlex subfields" in json.loads((work / "17_benchmark_meta.json").read_text(encoding="utf-8"))["skipped"]
    cfg["benchmark"]["enabled"] = False
    benchmark(cfg, fetch=fake_fetch([]))
    assert "enabled" in json.loads((work / "17_benchmark_meta.json").read_text(encoding="utf-8"))["skipped"]
