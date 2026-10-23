import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas.schema.contract import SCHEMA_VERSION, Topic, contract_json_schema

REPO = Path(__file__).resolve().parents[2]
SAMPLE = {
    "id": "T000123", "group": "G01", "th": "\N{THAI CHARACTER PHO PHAN}", "en": "Older adults", "size": 120,
    "x": 1.0, "y": 2.0, "r": 3.0, "status": "EMERGING", "score": 88.5,
    "metrics": {"count_recent": 90, "share_recent": 0.01, "share_baseline": 0.004, "share_ratio": 2.5,
                "share_growth": 0.4, "share_growth_lo": 0.2, "share_growth_hi": 0.6, "acceleration": 0.1,
                "burst_frac": 0.67, "burst_years": [2023, 2024], "novelty": 0.7, "coherence": 0.8,
                "n_journals_R": 5, "n_orgs_R": 7, "new_journal_share": 0.0, "journal_hhi": 0.3,
                "journal_driven": False},
}


def test_schema_lists_all_statuses():
    status = contract_json_schema()["definitions"]["Topic"]["properties"]["status"]
    assert set(status["enum"]) == {"EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA"}


def test_sample_topic_validates_and_bad_id_fails():
    assert Topic.model_validate(SAMPLE).lineage.event == "new"
    with pytest.raises(ValidationError):
        Topic.model_validate({**SAMPLE, "id": "t1"})
    with pytest.raises(ValidationError):
        Topic.model_validate({**SAMPLE, "status": "RISING"})


def test_v3_contract_fields():
    defs = contract_json_schema()["definitions"]
    assert defs["Manifest"]["properties"]["definition_version"]["default"] == 3
    assert defs["TopicMetrics"]["properties"]["orgs_unverified"] == {
        "default": False, "title": "Orgs Unverified", "type": "boolean"}
    assert Topic.model_validate(SAMPLE).metrics.orgs_unverified is False


def test_committed_schema_is_up_to_date():
    committed = json.loads((REPO / "web" / "src" / "data" / "contract.schema.json").read_text(encoding="utf-8"))
    assert committed == contract_json_schema(), "run: uv run atlas schema && (cd ../web && npm run gen:types)"
    assert SCHEMA_VERSION == "2.5.0"
