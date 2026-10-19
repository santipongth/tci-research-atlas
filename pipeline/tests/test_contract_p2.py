"""Contract 2.1: the editors' files validate strictly and appear in the JSON Schema."""
import pytest
from pydantic import ValidationError

from atlas.schema.contract import (
    SCHEMA_VERSION,
    CountItem,
    DiffFile,
    JournalDetail,
    JournalSummary,
    MatchIndex,
    MethodYears,
    contract_json_schema,
    model_for,
)

SUMMARY = {"id": "so02.BECJournal", "key": "so02:BECJournal", "path": "BECJournal", "articles": 40,
           "articles_window": 25, "active": True, "low_data": False}


def test_schema_version_and_definitions():
    assert SCHEMA_VERSION.startswith("2.") and SCHEMA_VERSION != "2.0.0"
    schema = contract_json_schema()
    assert {"journals", "journal_detail", "methods", "diff", "match"} <= set(schema["properties"])
    assert schema["definitions"]["CountItem"]["properties"]["id"]["default"] is None
    assert model_for("journals/so02.BECJournal.json") is JournalDetail
    assert model_for("journals.json").__name__ == "JournalsFile"


def test_journal_fields_from_the_registry_are_optional():
    j = JournalSummary.model_validate(SUMMARY)
    assert j.name_th == "" and j.tci_tier is None and j.owner_source is None and j.completeness is None
    for bad in ({"id": "so02:BECJournal"}, {"tci_tier": 4}, {"completeness": 101}, {"owner_source": "guess"}):
        with pytest.raises(ValidationError):
            JournalSummary.model_validate({**SUMMARY, **bad})
    assert CountItem(key="BECJournal", count=3).id is None


def test_match_index_must_be_aligned():
    base = {"analyzer": "char_wb3", "fold": "atlas-fold-1", "docs": 10, "max_terms": 2, "min_similarity": 0.05,
            "fit_topics": 5, "min_query_chars": 40, "grams": [" ab", "ab "], "idf": [1.0, 1.2],
            "topics": [{"id": "T000001", "terms": [0, 1], "weights": [0.6, 0.8]}],
            "journals": [{"id": "so02.A", "topics": ["T000001"], "shares": [0.5]}]}
    assert MatchIndex.model_validate(base).topics[0].id == "T000001"
    for bad in ({"idf": [1.0]}, {"topics": [{"id": "T000001", "terms": [0, 2], "weights": [0.6, 0.8]}]},
                {"journals": [{"id": "so02.A", "topics": ["T000001"], "shares": []}]},
                {"analyzer": "word"}, {"idf": [1.0, float("nan")]}):
        with pytest.raises(ValidationError):
            MatchIndex.model_validate({**base, **bad})


def test_method_years_and_diff_are_strict():
    with pytest.raises(ValidationError):
        MethodYears(years=[2023, 2024], articles=[1, 2], shares={"survey": [0.5]})
    d = {"release": "2026Q4", "previous_release": "2026Q3", "previous_source": "state", "kpis": [],
         "new_topics": [{"topic": "T000004", "event": "split", "parents": ["T000003"]}], "retired": [],
         "status_changes": [{"topic": "T000001", "previous": "STABLE", "current": "EMERGING"}], "movers": [],
         "journals_compared": True}
    assert DiffFile.model_validate(d).new_journals == [] and DiffFile.model_validate(d).restructured == []
    merged = DiffFile.model_validate({**d, "retired": [{"topic": "T000002", "merged_into": "T000001"}],
                                      "restructured": [{"topic": "T000001", "event": "merge",
                                                        "parents": ["T000001", "T000002"]}]})
    assert merged.retired[0].merged_into == "T000001" and merged.restructured[0].event == "merge"
    for bad in ({"retired": [{"topic": "T000002", "merged_into": "X"}]},
                {"restructured": [{"topic": "T000001", "event": "continue", "parents": []}]}):
        with pytest.raises(ValidationError):
            DiffFile.model_validate({**d, **bad})
    with pytest.raises(ValidationError):
        DiffFile.model_validate({**d, "status_changes": [{"topic": "T000001", "previous": "OLD", "current": "HOT"}]})
