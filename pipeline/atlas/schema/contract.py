"""Data contract v2 — the JSON files of one release (output/data/<release>/) that web v2 reads.

Pydantic models are the source of truth → JSON Schema (`atlas schema`) → TypeScript
(`npm run gen:types` in web/). CI fails when either generated file drifts.
Files: manifest.json, overview.json, taxonomy.json, topics.json, topics/<id>.json, series.json,
edges.json, keywords.json; P2 (2.1): journals.json, journals/<id>.json, methods.json, diff.json, match.json —
optional modules listed in manifest.modules. output/data/latest.json points at the newest release.
Strict JSON: NaN/Infinity are validation errors. Colours are design-token keys (cat-01…), never hex.
Uncertainty bounds keep level-agnostic names (share_growth_lo/_hi); the level is manifest.ci_level.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2.1.0"                  # 2.1: editors' modules (journals, methods, diff, match)
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
    cost_usd: float = Field(description="spend of this task for the whole release: every run, from the LLM journal")
    this_run_cost_usd: float = Field(0.0, description="spend of the run that produced this export")


class LabelStats(_Model):
    provider: Literal["llm", "off"]
    llm: int = Field(description="topics named by the LLM (incl. cached names)")
    keywords: int = Field(description="topics named from author keywords (provider off or LLM fallback)")
    overrides: int = Field(description="topics whose name an editor corrected (labeling.overrides_path)")
    reused: int = Field(0, description="topics that kept the previous release's name (lineage continue, keywords "
                                       "unchanged by labeling.reuse_min_jaccard) — no LLM call")


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
    ingest_errors: int | None = Field(None, description="files that could not be read or parsed; null = not "
                                                        "recorded (work_dir from before per-file error recording)")
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
    label_source: Literal["llm", "keywords", "override", "reused"] = "keywords"
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
    id: str | None = Field(None, description="journal id (journals/<id>.json) when the item is a journal of a "
                                             "release with the journals module")


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


# ---------------------------------------------------------------------- P2 editors' modules (schema 2.1)
JOURNAL_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$"
Completeness = Literal["abstract_en", "title_en", "keywords_en", "doi", "references", "refs_romanized", "affiliations"]


class YearWindow(_Model):
    start: int
    end: int


class JournalSummary(_Model):
    id: str = Field(pattern=JOURNAL_ID, description="journals/<id>.json; stable across releases")
    key: str = Field(description="corpus key <server>:<OJS path> (or name:<normalised name>)")
    path: str = Field(description="OJS path — shown when the registry gives no name")
    name_th: str = ""
    name_en: str = ""
    issn: str = ""
    eissn: str = ""
    tci_tier: int | None = Field(None, ge=1, le=3)
    tci_field: str = ""
    publisher: str = ""
    url: str = ""
    in_registry: bool = False
    articles: int
    articles_window: int
    articles_recent: int = 0
    first_year: int | None = None
    last_year: int | None = None
    active: bool = Field(description="published in the recent window R")
    low_data: bool = Field(description="fewer than min_articles in the window: every rate is null")
    group: str | None = Field(None, description="map group holding most of its window articles")
    completeness: float | None = Field(None, ge=0, le=100, description="D2 metadata completeness 0–100 (not the "
                                                                       "official TCI assessment)")
    owner: str = Field("", description="owner institution as written (registry) or its most frequent written name")
    owner_source: Literal["registry", "inferred"] | None = None
    owner_matched: bool = Field(False, description="the owner was found among the authors' organisations")
    inhouse_share: float | None = None
    n_orgs: int = 0
    effective_orgs: float | None = None
    foreign_share: float | None = None
    affiliation_coverage: float | None = None
    methods_coverage: float | None = None


class SpecialIssueTopic(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    hosts: int
    top_host_share: float
    articles_recent: int


class JournalsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    window: YearWindow
    recent: YearWindow
    baseline: YearWindow
    min_articles: int
    completeness_weights: dict[str, float]
    inhouse_flag_share: float | None = Field(None, description="journals.inhouse_flag_share: only journals whose "
                                                               "owner_source is 'registry' may be marked above it; "
                                                               "null = no mark")
    special_issue_statuses: list[Status] = Field(default_factory=list)
    special_issue_max_hosts: int = 0
    special_issue_min_host_articles: int = 0
    drift_reference_years: int = 0
    journals: list[JournalSummary]
    special_issue: list[SpecialIssueTopic] = Field(default_factory=list)


class JournalYear(_Model):
    year: int
    articles: int


class TopicShare(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    count: int
    share: float


class DriftPoint(_Model):
    year: int
    articles: int
    distance: float | None = Field(description="Jensen–Shannon distance to the reference years; null = too few")


class TopicShift(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    share_before: float
    share_after: float


class Peer(_Model):
    id: str = Field(pattern=JOURNAL_ID)
    similarity: float


class CompletenessItem(_Model):
    key: Completeness
    rate: float | None
    n: int


class MethodShare(_Model):
    method: str
    count: int
    share: float


class JournalOpportunity(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    reason: Literal["in_scope", "adjacent"]
    journal_articles: int
    hosts: int


class JournalDetail(_Model):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(pattern=JOURNAL_ID)
    years: list[JournalYear] = Field(default_factory=list)
    topics: list[TopicShare] = Field(default_factory=list)
    drift: list[DriftPoint] = Field(default_factory=list)
    gained: list[TopicShift] = Field(default_factory=list)
    lost: list[TopicShift] = Field(default_factory=list)
    peers: list[Peer] = Field(default_factory=list)
    completeness: list[CompletenessItem] = Field(default_factory=list)
    methods: list[MethodShare] = Field(default_factory=list)
    opportunities: list[JournalOpportunity] = Field(default_factory=list)


class MethodInfo(_Model):
    key: str
    th: str
    en: str


class MethodYears(_Model):
    years: list[int]
    articles: list[int]
    shares: dict[str, list[float]]

    @model_validator(mode="after")
    def _aligned(self):
        n = len(self.years)
        if len(self.articles) != n or any(len(v) != n for v in self.shares.values()):
            raise ValueError("every method series must have one value per year")
        return self


class TopicMethods(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    articles: int
    with_methods: int
    coverage: float
    methods: list[MethodShare]
    sample_size_n: int = 0
    sample_size_median: float | None = None
    sample_size_q1: float | None = None
    sample_size_q3: float | None = None
    monoculture_share: float | None = None
    monoculture: bool = False
    note: Narrative | None = None


class MethodsFile(_Model):
    schema_version: str = SCHEMA_VERSION
    lexicon_version: str
    window: YearWindow
    articles: int
    with_methods: int
    monoculture_methods: list[str]
    monoculture_min_share: float
    monoculture_share: float | None = None
    min_articles: int
    methods: list[MethodInfo]
    corpus: list[MethodShare]
    by_year: MethodYears
    topics: list[TopicMethods]


class KpiChange(_Model):
    key: str
    previous: float
    current: float


class NewTopic(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    event: Literal["new", "split", "merge"]
    parents: list[str] = Field(default_factory=list)


class RetiredTopic(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    th: str = ""
    en: str = ""
    merged_into: str | None = Field(None, pattern=TOPIC_ID, description="the topic of this release it merged into "
                                                                       "(lineage); null = it ended")


class RestructuredTopic(_Model):
    topic: str = Field(pattern=TOPIC_ID, description="a topic that kept its id through a merge or a split")
    event: Literal["split", "merge"]
    parents: list[str] = Field(default_factory=list)


class StatusChange(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    previous: Status
    current: Status


class Mover(_Model):
    topic: str = Field(pattern=TOPIC_ID)
    share_previous: float
    share_current: float


class DiffFile(_Model):
    schema_version: str = SCHEMA_VERSION
    release: str
    previous_release: str
    previous_source: Literal["state", "output"]
    kpis: list[KpiChange]
    new_topics: list[NewTopic]
    retired: list[RetiredTopic]
    restructured: list[RestructuredTopic] = Field(default_factory=list)
    status_changes: list[StatusChange]
    movers: list[Mover]
    journals_compared: bool
    new_journals: list[str] = Field(default_factory=list)


class MatchTopic(_Model):
    id: str = Field(pattern=TOPIC_ID)
    terms: list[int]
    weights: list[float]


class MatchJournal(_Model):
    id: str = Field(pattern=JOURNAL_ID)
    topics: list[str]
    shares: list[float]


class MatchIndex(_Model):
    schema_version: str = SCHEMA_VERSION
    analyzer: Literal["char_wb3"]
    fold: Literal["atlas-fold-1"]
    docs: int
    max_terms: int
    min_similarity: float
    fit_topics: int
    min_query_chars: int
    grams: list[str]
    idf: list[float]
    topics: list[MatchTopic]
    journals: list[MatchJournal] = Field(default_factory=list)

    @model_validator(mode="after")
    def _aligned(self):
        if len(self.grams) != len(self.idf):
            raise ValueError("grams and idf differ in length")
        n = len(self.grams)
        for t in self.topics:
            if len(t.terms) != len(t.weights) or any(not 0 <= i < n for i in t.terms):
                raise ValueError(f"match topic {t.id}: terms/weights misaligned or out of range")
        for j in self.journals:
            if len(j.topics) != len(j.shares):
                raise ValueError(f"match journal {j.id}: topics/shares misaligned")
        return self


P2_FILE_MODELS: dict[str, type[_Model]] = {"journals.json": JournalsFile, "methods.json": MethodsFile,
                                           "diff.json": DiffFile, "match.json": MatchIndex}


# published file → model (validate + export use the same table); topics/<id>.json → TopicDetail
FILE_MODELS: dict[str, type[_Model]] = {
    "manifest.json": Manifest, "overview.json": Overview, "taxonomy.json": TaxonomyFile,
    "topics.json": TopicsFile, "series.json": SeriesFile, "edges.json": EdgesFile, "keywords.json": KeywordsFile,
    **P2_FILE_MODELS,
}


def model_for(path: str) -> type[_Model] | None:
    if path.startswith("topics/") and path.endswith(".json"):
        return TopicDetail
    if path.startswith("journals/") and path.endswith(".json"):
        return JournalDetail
    return FILE_MODELS.get(path)


def contract_json_schema() -> dict:
    from pydantic.json_schema import models_json_schema

    files = {"manifest": Manifest, "overview": Overview, "taxonomy": TaxonomyFile, "topics": TopicsFile,
             "topic_detail": TopicDetail, "series": SeriesFile, "edges": EdgesFile, "keywords": KeywordsFile,
             "latest": Latest, "journals": JournalsFile, "journal_detail": JournalDetail, "methods": MethodsFile,
             "diff": DiffFile, "match": MatchIndex}
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
