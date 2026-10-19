"""Validated configuration for the TCI Research Atlas pipeline (pydantic v2).

`load_config()` returns a plain dict so modules keep using cfg["section"]["key"].
Every field has a default equal to config.example.yaml; unknown keys are errors.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PipelineCfg(_Strict):
    name: str = "tci-research-atlas"
    work_dir: str = "./work"          # regenerable checkpoints — safe to delete
    output_dir: str = "./output"
    state_dir: str = "./state"        # persistent: embedding store, label cache, previous run
    seed: int = 42
    release: str | None = Field(None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")  # None → YYYYQn of today


class DedupCfg(_Strict):
    enabled: bool = True


class InputCfg(_Strict):
    format: Literal["thaijo_md", "table"] = "thaijo_md"
    path: str = "../corpus"
    glob: str = "**/*.md"
    workers: int = Field(4, ge=1)
    max_error_ratio: float = Field(0.01, ge=0, le=1)   # unreadable/unparsable files / files found; above it ingest stops
    min_year: int = 1990
    max_year: int | None = None
    columns: dict[str, str] = Field(default_factory=lambda: {
        "article_id": "id", "title_th": "title_th", "title_en": "title_en",
        "abstract_th": "abstract_th", "abstract_en": "abstract_en",
        "keywords_th": "keywords_th", "keywords_en": "keywords_en",
        "authors": "authors", "affiliations": "affiliations", "journal_name": "journal",
        "year": "year", "doi": "doi", "url": "url",
    })
    dedup: DedupCfg = Field(default_factory=DedupCfg)


class ApiEmbedCfg(_Strict):
    """OpenAI-compatible /embeddings endpoint, run by atlas.embed_runner (see docs/OPERATIONS.md)."""
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "ATLAS_EMBED_API_KEY"     # the NAME of the env var holding the key — never the key
    model: str = "text-embedding-3-large"
    dimensions: int | None = Field(1024, ge=1)   # sent only when set (null for bge-m3)
    store_id: str | None = None                  # null -> "api|<model>|<dimensions>" (never includes base_url)
    batch_size: int = Field(32, ge=1)
    max_batch_chars: int = Field(60_000, ge=1)
    concurrency: int = Field(4, ge=1)
    requests_per_minute: int | None = Field(None, ge=1)
    request_timeout: float = Field(120.0, gt=0)
    max_retries: int | None = Field(None, ge=0)  # null = retry transient errors forever
    backoff_initial: float = Field(2.0, gt=0)
    backoff_max: float = 300.0
    min_text_chars: int = Field(512, ge=1)
    checkpoint_every: int = Field(2000, ge=1)
    lock_stale_seconds: int = Field(300, ge=1)  # no heartbeat this long -> `atlas status` says hung

    @model_validator(mode="after")
    def _backoff_order(self) -> ApiEmbedCfg:
        if self.backoff_max < self.backoff_initial:
            raise ValueError("embedding.api.backoff_max must be >= backoff_initial")
        return self


class LocalEmbedCfg(_Strict):
    model: str = "BAAI/bge-m3"
    device: str = "cuda"
    batch_size: int = 32
    fp16: bool = True
    max_seq_length: int = 1024
    checkpoint_every: int = 5000
    lock_stale_seconds: int = Field(300, ge=1)   # no heartbeat this long -> `atlas status` says hung


class LiteEmbedCfg(_Strict):
    dim: int = 128
    ngram_min: int = 2
    ngram_max: int = 4
    max_features: int = 100_000
    min_df: int = 2


class EmbeddingCfg(_Strict):
    provider: Literal["api", "local", "lite"] = "local"   # lite = CI/tests only; api = paid
    lite_max_docs: int = Field(50_000, ge=1)              # lite above this prints a WARNING (degraded run)
    api: ApiEmbedCfg = Field(default_factory=ApiEmbedCfg)
    local: LocalEmbedCfg = Field(default_factory=LocalEmbedCfg)
    lite: LiteEmbedCfg = Field(default_factory=LiteEmbedCfg)
    doc_fields: list[str] = Field(default_factory=lambda: [
        "title_th", "title_en", "keywords_th", "keywords_en", "abstract_th", "abstract_en"])
    max_chars_per_doc: int = 6000


class FineLevelCfg(_Strict):
    umap_n_components: int = 10
    umap_n_neighbors: int = 15
    umap_min_dist: float = 0.0
    hdbscan_min_cluster_size: int = 150
    hdbscan_min_samples: int = 20


class LeidenCfg(_Strict):
    k: int = Field(15, ge=2)
    resolution: float = Field(1.0, gt=0.0)
    min_cluster_size: int = Field(150, ge=2)
    n_iterations: int = -1


class ClusteringCfg(_Strict):
    algorithm: Literal["hdbscan", "leiden"] = "hdbscan"
    hdbscan_backend: Literal["sklearn", "fast"] = "sklearn"
    leiden: LeidenCfg = Field(default_factory=LeidenCfg)
    reducer: Literal["umap", "pca"] = "umap"
    pca_dims: int = 128
    pca_fit_sample: int = Field(100_000, ge=100)
    umap_fit_sample: int = 150_000
    fine: FineLevelCfg = Field(default_factory=FineLevelCfg)
    merge_similarity: float = Field(0.8, ge=0.0, le=1.0)
    outlier_min_similarity: float = Field(0.35, ge=-1.0, le=1.0)
    n_groups: int = Field(20, ge=1)
    ctfidf_top_n: int = 20
    ctfidf_max_docs_per_topic: int = 400


class MergeCfg(_Strict):
    enabled: bool = True
    min_similarity: float = Field(0.85, gt=0.0, le=1.0)
    max_pairs: int = Field(30, ge=0)


class LabelingCfg(_Strict):
    provider: Literal["llm", "off"] = "off"
    overrides_path: str | None = None     # editors' CSV keyed by T000123; the example config sets ./registry/…
    merge: MergeCfg = Field(default_factory=MergeCfg)
    n_repr_docs: int = 8
    mmr_lambda: float = Field(0.7, ge=0.0, le=1.0)

    @field_validator("provider", mode="before")
    @classmethod
    def _provider_alias(cls, v):
        if v is False:                    # YAML reads a bare `off` as boolean false
            return "off"
        return "llm" if v == "api" else v     # P0 name


class TopicsCfg(_Strict):
    mode: Literal["auto", "fit", "assign"] = "auto"
    refit_every_releases: int = Field(4, ge=1)
    refit_max_unassigned: float = Field(0.15, ge=0.0, le=1.0)
    match_containment: float = Field(0.5, gt=0.0, le=1.0)
    match_min_shared: int = Field(5, ge=1)


class OpenAlexCfg(_Strict):
    base_url: str = "https://api.openalex.org"
    mailto: str | None = None
    api_key_env: str = "OPENALEX_API_KEY"
    requests_per_second_keyless: float = Field(8.0, gt=0)
    requests_per_second_keyed: float = Field(25.0, gt=0)
    max_pages_keyed: int = Field(1, ge=1)
    country_code: str = "TH"
    per_subfield: int = Field(100, ge=1, le=100)
    seed: int = 42
    timeout: float = 30.0
    max_retries: int = Field(3, ge=1)


class TaxonomyCfg(_Strict):
    source: Literal["openalex", "off"] = "openalex"
    reference_path: str | None = None
    openalex: OpenAlexCfg = Field(default_factory=OpenAlexCfg)
    k: int = Field(20, ge=1)
    max_articles_per_topic: int = Field(200, ge=1)
    min_vote_share: float = Field(0.5, ge=0.0, le=1.0)
    holdout_frac: float = Field(0.2, gt=0.0, lt=1.0)


class SizeCfg(_Strict):
    rule: Literal["quantile", "absolute"] = "quantile"
    large_quantile: float = Field(0.75, gt=0.0, lt=1.0)
    large_share: float = 0.015


class EmergingRuleCfg(_Strict):
    min_growth_lo: float = 0.10
    min_share_ratio: float = 1.8


class HotRuleCfg(_Strict):
    min_growth_lo: float = 0.0


class DecliningRuleCfg(_Strict):
    max_growth_hi: float = 0.0
    max_share_ratio: float = 0.8


class BreadthCfg(_Strict):
    min_journals: int = 3
    min_orgs: int = 3
    max_new_journal_share: float = 0.5
    min_org_coverage: float = 0.5     # apply the institution rule only when >= 50% of R articles have affiliations


class BurstCfg(_Strict):
    s: float = 2.0
    gamma: float = 1.0


class ScoreWeightsCfg(_Strict):
    growth: float = 0.30
    acceleration: float = 0.20
    burst: float = 0.15
    novelty: float = 0.15
    coherence: float = 0.10
    breadth: float = 0.10


class EmergingCfg(_Strict):
    definition_version: Literal[3] = 3
    as_of_year: int | None = None     # null = today's calendar year; the running year is never complete
    min_year_complete: int | None = None
    backfill_min_ratio: float = 0.6
    backfill_ref_years: int = Field(3, ge=1)
    backfill_max_trim: int = Field(2, ge=0)
    max_abs_log_growth: float = Field(10.0, gt=0.0)   # |log growth| or CI bound above this = not estimable
    recent_window: int = 3
    baseline_window: int = 5
    trend_window: int = 5
    min_articles_recent: int = 30
    ci_level: float = Field(0.90, gt=0.5, lt=1.0)
    size: SizeCfg = Field(default_factory=SizeCfg)
    emerging: EmergingRuleCfg = Field(default_factory=EmergingRuleCfg)
    hot: HotRuleCfg = Field(default_factory=HotRuleCfg)
    declining: DecliningRuleCfg = Field(default_factory=DecliningRuleCfg)
    breadth: BreadthCfg = Field(default_factory=BreadthCfg)
    burst: BurstCfg = Field(default_factory=BurstCfg)
    score_weights: ScoreWeightsCfg = Field(default_factory=ScoreWeightsCfg)


class NowcastCfg(_Strict):
    enabled: bool = True
    min_months: int = Field(3, ge=1, le=12)
    profile_years: int = Field(3, ge=1)
    as_of: str | None = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class ForecastCfg(_Strict):
    horizon: int = Field(2, ge=1)
    min_history_years: int = Field(6, ge=3)
    models: list[Literal["naive", "drift", "nb_glm", "ets_damped"]] = Field(
        default_factory=lambda: ["naive", "drift", "nb_glm", "ets_damped"])
    total_models: list[Literal["naive", "drift", "ets_damped"]] = Field(
        default_factory=lambda: ["naive", "drift", "ets_damped"])
    cv_origins: int = Field(4, ge=3)
    min_train_years: int = Field(4, ge=3)
    min_skill: float = 0.0
    max_mase: float = Field(1.0, gt=0.0)
    min_calibration: int = Field(20, ge=1)
    nowcast: NowcastCfg = Field(default_factory=NowcastCfg)


class KeywordsCfg(_Strict):
    enabled: bool = True
    min_docs_recent: int = Field(7, ge=1)
    max_doc_share: float = Field(0.15, gt=0.0, le=1.0)
    novelty_min_ratio: float = Field(2.0, gt=0.0)
    min_active_years: int = Field(3, ge=1)
    min_orgs: int = Field(3, ge=0)
    min_journals: int = Field(3, ge=0)
    max_new_journal_share: float = Field(0.5, gt=0.0, le=1.0)
    min_growth_lo: float = 0.0
    max_terms: int = Field(50, ge=1)


class LayoutCfg(_Strict):
    umap_2d_neighbors: int = 12
    umap_2d_min_dist: float = 0.35
    view_w: int = 1680
    view_h: int = 1040
    edge_similarity_threshold: float = 0.55
    max_edges_per_node: int = 4
    stable: bool = True
    anchor: float = Field(0.9, ge=0.0, le=1.0)
    init_neighbors: int = Field(3, ge=1)
    galaxy: bool = True


class ExportCfg(_Strict):
    formats: list[Literal["json", "csv"]] = Field(default_factory=lambda: ["json", "csv"])
    include_forecast_in_json: bool = True
    v2: bool = True
    repr_articles: int = Field(12, ge=1)
    max_topic_journals: int = Field(10, ge=1)
    max_topic_orgs: int = Field(10, ge=1)
    max_neighbors: int = Field(6, ge=0)


class ValidateCfg(_Strict):
    max_topic_count_change: float = Field(0.25, ge=0.0)
    min_kept_ids: float = Field(0.9, ge=0.0, le=1.0)
    max_status_change_frac: float = Field(0.3, ge=0.0, le=1.0)
    size_swing_ratio: float = Field(2.0, gt=1.0)
    size_swing_min_articles: int = Field(50, ge=1)
    max_article_drop: float = Field(0.02, ge=0.0, le=1.0)


class BakeoffCandidate(_Strict):
    name: str
    provider: Literal["api", "local", "lite"]
    model: str = ""
    base_url: str = ""
    dimensions: int | None = None
    store_id: str | None = None       # api only; None → the P0 runner's default "api|<model>|<dimensions>"


class BakeoffCfg(_Strict):
    sample: int = Field(5000, ge=50)
    k: int = Field(10, ge=1)
    holdout_frac: float = Field(0.2, gt=0.0, lt=1.0)
    seeds: list[int] = Field(default_factory=lambda: [1, 2, 3])
    algorithms: list[Literal["hdbscan", "hdbscan_fast", "leiden"]] = Field(
        default_factory=lambda: ["hdbscan", "hdbscan_fast", "leiden"])
    npmi_top_n: int = Field(10, ge=2)
    embedding_candidates: list[BakeoffCandidate] = Field(default_factory=list)


class LlmEndpointCfg(_Strict):
    base_url: str = ""                # e.g. https://openrouter.ai/api/v1 — empty = LLM not configured
    api_key_env: str = "ATLAS_LLM_API_KEY"
    json_mode: bool = True
    concurrency: int = Field(4, ge=1)
    request_timeout: float = Field(120.0, gt=0.0)
    max_retries: int | None = Field(None, ge=0)       # None = retry transient errors without limit
    backoff_initial: float = Field(2.0, gt=0.0)
    backoff_max: float = Field(300.0, gt=0.0)
    price_per_mtok_in: float | None = Field(None, ge=0.0)
    price_per_mtok_out: float | None = Field(None, ge=0.0)

    @model_validator(mode="after")
    def _backoff_order(self) -> LlmEndpointCfg:
        if self.backoff_max < self.backoff_initial:
            raise ValueError("llm.endpoints.<name>.backoff_max must be >= backoff_initial")
        return self


class LlmTaskCfg(_Strict):
    endpoint: str = "default"
    model: str = ""
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(600, ge=16)


class LlmTasksCfg(_Strict):
    label: LlmTaskCfg = Field(default_factory=lambda: LlmTaskCfg(temperature=0.2, max_output_tokens=600))
    merge: LlmTaskCfg = Field(default_factory=lambda: LlmTaskCfg(temperature=0.0, max_output_tokens=300))
    narrative: LlmTaskCfg = Field(default_factory=lambda: LlmTaskCfg(temperature=0.3, max_output_tokens=900))
    brief: LlmTaskCfg = Field(default_factory=lambda: LlmTaskCfg(temperature=0.3, max_output_tokens=1200))


class LlmCfg(_Strict):
    prompts_dir: str | None = None    # None = the repo's prompts/ folder
    budget_usd: float | None = Field(None, ge=0.0)
    max_repairs: int = Field(2, ge=0)
    max_regenerations: int = Field(1, ge=0)
    lock_stale_seconds: float = Field(300.0, gt=0.0)
    endpoints: dict[str, LlmEndpointCfg] = Field(default_factory=lambda: {"default": LlmEndpointCfg()})
    tasks: LlmTasksCfg = Field(default_factory=LlmTasksCfg)

    @model_validator(mode="after")
    def _known_endpoints(self):
        for name in LlmTasksCfg.model_fields:
            ep = getattr(self.tasks, name).endpoint
            if ep not in self.endpoints:
                raise ValueError(f"llm.tasks.{name}.endpoint {ep!r} is not defined in llm.endpoints")
        return self


class ReviewCfg(_Strict):
    sample_size: int = Field(50, ge=1)
    n_titles: int = Field(5, ge=1)


class NarrativeCfg(_Strict):
    provider: Literal["llm", "template"] = "template"
    statuses: list[Literal["EMERGING", "WATCH", "HOT", "DECLINING"]] = Field(
        default_factory=lambda: ["EMERGING", "HOT", "DECLINING"])
    top_n: int = Field(10, ge=0)
    n_titles: int = Field(5, ge=0)
    brief: bool = True


class AtlasConfig(_Strict):
    pipeline: PipelineCfg = Field(default_factory=PipelineCfg)
    input: InputCfg = Field(default_factory=InputCfg)
    embedding: EmbeddingCfg = Field(default_factory=EmbeddingCfg)
    clustering: ClusteringCfg = Field(default_factory=ClusteringCfg)
    labeling: LabelingCfg = Field(default_factory=LabelingCfg)
    llm: LlmCfg = Field(default_factory=LlmCfg)
    review: ReviewCfg = Field(default_factory=ReviewCfg)
    narrative: NarrativeCfg = Field(default_factory=NarrativeCfg)
    topics: TopicsCfg = Field(default_factory=TopicsCfg)
    taxonomy: TaxonomyCfg = Field(default_factory=TaxonomyCfg)
    emerging: EmergingCfg = Field(default_factory=EmergingCfg)
    keywords: KeywordsCfg = Field(default_factory=KeywordsCfg)
    forecast: ForecastCfg = Field(default_factory=ForecastCfg)
    layout: LayoutCfg = Field(default_factory=LayoutCfg)
    export: ExportCfg = Field(default_factory=ExportCfg)
    validation: ValidateCfg = Field(default_factory=ValidateCfg)
    bakeoff: BakeoffCfg = Field(default_factory=BakeoffCfg)


def _resolve(p: str, base: Path) -> str:
    q = Path(p)
    return str((q if q.is_absolute() else base / q).resolve())


def load_config(path: str | Path | None = None) -> dict:
    """Validate a YAML config (missing keys take defaults) and resolve relative paths."""
    raw: dict = {}
    base = Path.cwd()
    if path:
        p = Path(path)
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        base = p.resolve().parent
    cfg = AtlasConfig.model_validate(raw).model_dump()
    for key in ("work_dir", "output_dir", "state_dir"):
        cfg["pipeline"][key] = _resolve(cfg["pipeline"][key], base)
    cfg["input"]["path"] = _resolve(cfg["input"]["path"], base)
    if cfg["labeling"]["overrides_path"]:
        cfg["labeling"]["overrides_path"] = _resolve(cfg["labeling"]["overrides_path"], base)
    if cfg["llm"]["prompts_dir"]:
        cfg["llm"]["prompts_dir"] = _resolve(cfg["llm"]["prompts_dir"], base)
    if cfg["taxonomy"]["reference_path"]:
        cfg["taxonomy"]["reference_path"] = _resolve(cfg["taxonomy"]["reference_path"], base)
    return cfg
