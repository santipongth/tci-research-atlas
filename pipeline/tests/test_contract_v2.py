import pytest
from pydantic import ValidationError

from atlas.schema.contract import (
    FILE_MODELS,
    GroupInfo,
    SeriesFile,
    TopicDetail,
    TopicNowcast,
    contract_json_schema,
    model_for,
)


def test_every_published_file_has_a_model_and_a_schema_entry():
    props = contract_json_schema()["properties"]
    assert set(props) == {"manifest", "overview", "taxonomy", "topics", "topic_detail", "series", "edges",
                          "keywords", "latest", "journals", "journal_detail", "methods", "diff", "match",
                          "institutions", "institution_detail", "regions", "sdg", "global", "gaps", "references",
                          "search_meta", "search_vocab", "search_index", "search_docs", "galaxy", "kwtrends"}
    assert model_for("topics/T000001.json") is TopicDetail and model_for("overview.json") is FILE_MODELS["overview.json"]
    assert model_for("unknown.json") is None


def test_series_must_be_aligned_and_ids_patterned():
    SeriesFile(years=[2023, 2024], corpus_total=[10, 12], topics={"T000001": [1, 2]})
    with pytest.raises(ValidationError, match="one value per year"):
        SeriesFile(years=[2023, 2024], corpus_total=[10, 12], topics={"T000001": [1]})
    with pytest.raises(ValidationError):
        TopicDetail(id="T1", articles=[])


def test_nan_and_hex_colours_are_rejected():
    with pytest.raises(ValidationError):
        TopicNowcast(year=2025, as_of_month=4, ytd=3, mean=float("nan"))
    with pytest.raises(ValidationError):
        GroupInfo(id="F33", th="ก", en="A", color="#FF5F1F", size=1, n_topics=1, x=0, y=0, r=1)
    GroupInfo(id="F33", th="ก", en="A", color="cat-01", size=1, n_topics=1, x=0, y=0, r=1)


def test_groups_always_carry_a_bilingual_name():
    for th, en in (("", "A"), ("ก", "")):
        with pytest.raises(ValidationError):
            GroupInfo(id="G05", th=th, en=en, color="cat-01", size=1, n_topics=1, x=0, y=0, r=1)
    GroupInfo(id="G105", th="ก", en="A", color="cat-02", size=1, n_topics=1, x=0, y=0, r=1)   # > 99 coarse groups


def _metrics(**over):
    m = dict(count_recent=40, share_recent=0.01, share_baseline=0.0, share_ratio=None, no_baseline=True,
             share_growth=None, share_growth_lo=None, share_growth_hi=None, acceleration=0.0, burst_frac=0.0,
             novelty=0.0, n_journals_R=3, n_orgs_R=3, new_journal_share=0.0, journal_hhi=0.1, journal_driven=False,
             low_data_reason="not_estimable")
    return {**m, **over}


def test_no_baseline_topics_carry_a_null_ratio_and_a_low_data_reason():
    from atlas.schema.contract import TopicMetrics

    assert TopicMetrics(**_metrics()).share_ratio is None
    with pytest.raises(ValidationError):
        TopicMetrics(**_metrics(low_data_reason="other"))


def test_manifest_carries_the_interval_level_and_llm_accounting():
    from atlas.schema.contract import LabelStats, LlmTaskStats, Manifest

    m = Manifest(release="2026Q4", generated_at="2026-10-18T00:00:00Z", pipeline_version="abc", config_hash="0" * 16,
                 embedding_model="api|bge-m3|None", ci_level=0.9, trimmed_years=[2026],
                 labels=LabelStats(provider="llm", llm=10, keywords=1, overrides=2),
                 llm=[LlmTaskStats(task="label", model="m", items=11, from_cache=5, generated=5, repaired=1,
                                   fallback=1, cost_usd=0.02)])
    assert m.definition_version == 3 and m.llm[0].fallback == 1
