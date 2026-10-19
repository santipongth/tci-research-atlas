"""Data contract v2 — the JSON files of one release (output/data/<release>/) that web v2 reads.

Pydantic models are the source of truth → JSON Schema (`atlas schema`) → TypeScript
(`npm run gen:types` in web/). CI fails when either generated file drifts.
Files: manifest.json, overview.json, taxonomy.json, topics.json, topics/<id>.json, series.json,
edges.json, keywords.json; output/data/latest.json points at the newest release.
Strict JSON: NaN/Infinity are validation errors. Colours are design-token keys (cat-01…), never hex.
Uncertainty bounds keep level-agnostic names (share_growth_lo/_hi); the level is manifest.ci_level.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2.0.0"
Status = Literal["EMERGING", "WATCH", "HOT", "DECLINING", "STABLE", "LOW_DATA"]
TOPIC_ID = r"^T\d{6}$"
GROUP_ID = r"^[FG]\d{2,}$"                # F = OpenAlex field id, G = agglomerative fallback group
COLOR_TOKEN = r"^cat-\d{2}$"              # colours are design-token keys, never hex


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)   # strict JSON: NaN/Infinity are errors


class FileEntry(_Model):
    path: str
    bytes: int
    sha256: str


class LlmTaskStats(_Model):
    task: str
    model: str
    items: int
    from_cache: int
    generated: int
    repaired: int
    fallback: int
    cost_usd: float


class LabelStats(_Model):
    provider: Literal["llm", "off"]
    llm: int = Field(description="topics named by the LLM (incl. cached names)")
    keywords: int = Field(description="topics named from author keywords (provider off or LLM fallback)")
    overrides: int = Field(description="topics whose name an editor corrected (labeling.overrides_path)")


class Manifest(_Model):
    schema_version: str = SCHEMA_VERSION
    release: str = Field(description="release tag, e.g. 2026Q4")
    generated_at: str
    pipeline_version: str
    config_hash: str
    definition_version: int = 3
    ci_level: float = Field(0.9, description="level of every *_lo/*_hi interval in this release")
    as_of_year: int | None = None
    trimmed_years: list[int] = Field(default_factory=list, description="years after last_complete_year")
    embedding_provider: str = ""
    embedding_model: str
    taxonomy_version: str | None = None
    modules: list[str] = Field(default_factory=list)
    files: list[FileEntry] = Field(default_factory=list)
    previous_release: str | None = None
    n_orgs_unverified: int = 0
    ingest_errors: int = 0
    labels: LabelStats | None = None
    llm: list[LlmTaskStats] = Field(default_factory=list)


class TopicMetrics(_Model):
    count_recent: int
    share_recent: float
    share_baseline: float
    share_ratio: float | None = Field(description="null when no_baseline")
    no_baseline: bool = Field(False, description="no articles in the baseline window — show 'new — no baseline'")
    share_growth: float | None
    share_growth_lo: float | None
    share_growth_hi: float | None
    acceleration: float
    burst_frac: float
    burst_years: list[int] = Field(default_factory=list)
    novelty: float
    coherence: float | None = None
    n_journals_R: int
    n_orgs_R: int
    new_journal_share: float
    journal_hhi: float
    journal_driven: bool
    orgs_unverified: bool = False      # v3: institution breadth rule skipped (affiliation coverage too low)
    low_data_reason: Literal["few_articles", "not_estimable"] | None = None


class TopicForecast(_Model):
    model: str
    mase: float | None
    skill_vs_naive: float
    show: bool
    years: list[int]
    mean: list[float]
    lo80: list[float]
    hi80: list[float]
    lo95: list[float]
    hi95: list[float]


class TopicLineage(_Model):
    born: str | None = None
    event: Literal["new", "continue", "split", "merge"] = "new"
    parents: list[str] = Field(default_factory=list)


class TopicNowcast(_Model):
    year: int
    as_of_month: int = Field(ge=1, le=12)
    ytd: int
    mean: float


class Topic(_Model):
    id: str = Field(pattern=TOPIC_ID)
    group: str
    th: str
    en: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    label_source: Literal["llm", "keywords", "override"] = "keywords"
    size: int
    x: float
    y: float
    r: float
    status: Status
    score: float
    metrics: TopicMetrics
    forecast: TopicForecast | None = None
    lineage: TopicLineage = Field(default_factory=TopicLineage)
    sdg: list[int] = Field(default_factory=list)
    subfield: str | None = None               # OpenAlex subfield id, e.g. "3304"
    subfield_en: str = ""
    cross_field: bool = False                 # subfield vote < taxonomy.min_vote_share
    taxonomy_vote: float | None = None
    nowcast: TopicNowcast | None = None


class TopicsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    topics: list[Topic]


class GroupInfo(_Model):
    id: str = Field(pattern=GROUP_ID)
    th: str = Field(min_length=1)             # every map group has a name in both languages
    en: str = Field(min_length=1)
    color: str = Field(pattern=COLOR_TOKEN)
    size: int
    n_topics: int
    x: float
    y: float
    r: float


class SubfieldInfo(_Model):
    id: str
    en: str
    group: str = Field(pattern=GROUP_ID)
    n_topics: int
    size: int


class TaxonomyFile(_Model):
    schema_version: str = SCHEMA_VERSION
    source: Literal["openalex", "agglomerative"]
    version: str | None = None
    holdout_accuracy_subfield: float | None = None
    holdout_accuracy_field: float | None = None
    groups: list[GroupInfo]
    subfields: list[SubfieldInfo] = Field(default_factory=list)


class YearCount(_Model):
    year: int
    articles: float


class Kpis(_Model):
    articles: int
    assigned_articles: int
    topics: int
    groups: int
    journals: int
    institutions: int
    pct_abstract_en: float
    pct_doi: float
    pct_keywords: float


class DataQuality(_Model):
    year_missing: int
    unassigned_articles: int
    completeness_method: str                       # median (v3 backfill guard) | configured (min_year_complete)
    text_quality: dict[str, int] = Field(default_factory=dict)


class Brief(_Model):
    headline_th: str
    headline_en: str
    bullets_th: list[str] = Field(default_factory=list)
    bullets_en: list[str] = Field(default_factory=list)
    source: Literal["llm", "template"]


class Overview(_Model):
    schema_version: str = SCHEMA_VERSION
    release: str
    previous_release: str | None = None
    generated_at: str
    definition_version: int = 3
    last_complete_year: int
    kpis: Kpis
    status_counts: dict[str, int]
    corpus_by_year: list[YearCount]
    corpus_forecast: list[YearCount] = Field(default_factory=list)
    nowcast: TopicNowcast | None = None
    lineage_events: dict[str, int] = Field(default_factory=dict)
    retired_topics: list[str] = Field(default_factory=list)
    data_quality: DataQuality
    brief: Brief | None = None


class SeriesFile(_Model):
    schema_version: str = SCHEMA_VERSION
    years: list[int]
    corpus_total: list[int]
    topics: dict[str, list[int]]

    @model_validator(mode="after")
    def _aligned(self):
        n = len(self.years)
        if len(self.corpus_total) != n or any(len(v) != n for v in self.topics.values()):
            raise ValueError("every series must have one value per year")
        return self


class Edge(_Model):
    s: str = Field(pattern=TOPIC_ID)
    t: str = Field(pattern=TOPIC_ID)
    w: float


class EdgesFile(_Model):
    schema_version: str = SCHEMA_VERSION
    edges: list[Edge]


class RepresentativeArticle(_Model):
    article_id: str
    title: str
    title_en: str = ""
    year: int | None = None
    journal: str = ""
    url: str = ""
    doi: str = ""
    gx: float | None = None
    gy: float | None = None


class CountItem(_Model):
    key: str
    count: int


class Narrative(_Model):
    th: str
    en: str
    source: Literal["llm", "template"]


class TopicDetail(_Model):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(pattern=TOPIC_ID)
    articles: list[RepresentativeArticle]
    journals: list[CountItem] = Field(default_factory=list)
    institutions: list[CountItem] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    neighbors: list[str] = Field(default_factory=list)
    narrative: Narrative | None = None


class EmergingKeyword(_Model):
    term: str
    count_recent: int
    share_ratio: float | None = Field(description="null when no_baseline")
    no_baseline: bool = False
    growth: float | None
    growth_lo: float | None
    n_active_years: int
    n_orgs_R: int
    n_journals_R: int
    journal_driven: bool
    emerging: bool
    topic: str | None = None


class KeywordsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    keywords: list[EmergingKeyword]


class Latest(_Model):
    release: str
    path: str
    schema_version: str = SCHEMA_VERSION
    generated_at: str


# published file → model (validate + export use the same table); topics/<id>.json → TopicDetail
FILE_MODELS: dict[str, type[_Model]] = {
    "manifest.json": Manifest, "overview.json": Overview, "taxonomy.json": TaxonomyFile,
    "topics.json": TopicsFile, "series.json": SeriesFile, "edges.json": EdgesFile, "keywords.json": KeywordsFile,
}


def model_for(path: str) -> type[_Model] | None:
    if path.startswith("topics/") and path.endswith(".json"):
        return TopicDetail
    return FILE_MODELS.get(path)


def contract_json_schema() -> dict:
    from pydantic.json_schema import models_json_schema

    files = {"manifest": Manifest, "overview": Overview, "taxonomy": TaxonomyFile, "topics": TopicsFile,
             "topic_detail": TopicDetail, "series": SeriesFile, "edges": EdgesFile, "keywords": KeywordsFile,
             "latest": Latest}
    _, top = models_json_schema([(m, "validation") for m in files.values()], ref_template="#/definitions/{model}")
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "AtlasContract",
        "type": "object",
        "properties": {k: {"$ref": f"#/definitions/{m.__name__}"} for k, m in files.items()},
        "required": ["manifest", "topics"],
        "additionalProperties": False,
        "definitions": top["$defs"],
    }


def write_json_schema(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(contract_json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                 encoding="utf-8")
    return p
