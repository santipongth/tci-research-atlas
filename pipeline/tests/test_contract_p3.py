"""Contract 2.2: the executives' files validate strictly, are additive, and appear in the JSON Schema."""
import pytest
from pydantic import ValidationError

from atlas.schema.contract import (
    SCHEMA_VERSION,
    InstitutionSummary,
    Kpis,
    Manifest,
    ProvinceStat,
    contract_json_schema,
    model_for,
)


def test_version_definitions_and_paths():
    assert SCHEMA_VERSION == "2.2.0"
    assert {"institutions", "institution_detail", "regions", "sdg", "global", "gaps"} <= set(
        contract_json_schema()["properties"])
    assert model_for("institutions/nu.json").__name__ == "InstitutionDetail"
    assert model_for("gaps.json").__name__ == "GapsFile" and model_for("institutions.json").__name__ == "InstitutionsFile"


def test_p3_fields_are_strict_and_older_files_still_validate():
    base = {"id": "nu", "source": "alias", "articles": 40, "articles_total": 90}
    assert InstitutionSummary.model_validate(base).province is None
    for bad in ({"id": "NU"}, {"province": "TH-1"}, {"country": "tha"}, {"type": "school"}, {"intl_share": float("nan")}):
        with pytest.raises(ValidationError):
            InstitutionSummary.model_validate({**base, **bad})
    with pytest.raises(ValidationError):
        ProvinceStat.model_validate({"code": "TH-99x", "name_th": "x", "name_en": "x", "region": "north", "articles": 1})
    kpis = {"articles": 1, "assigned_articles": 1, "topics": 1, "groups": 1, "journals": 1, "institutions": 1,
            "pct_abstract_en": 0, "pct_doi": 0, "pct_keywords": 0}
    assert Kpis.model_validate(kpis).pct_international is None                 # a 2.1 overview still validates
    m = Manifest.model_validate({"release": "2026Q4", "generated_at": "x", "pipeline_version": "x",
                                 "config_hash": "x", "embedding_model": "x"})
    assert m.skipped_modules == {}
