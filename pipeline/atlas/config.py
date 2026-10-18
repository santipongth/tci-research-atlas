"""Validated configuration for the TCI Research Atlas pipeline (pydantic v2).

`load_config()` returns a plain dict so modules keep using cfg["section"]["key"].
Every field has a default equal to config.example.yaml; unknown keys are errors.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PipelineCfg(_Strict):
    name: str = "tci-research-atlas"
    work_dir: str = "./work"          # regenerable checkpoints — safe to delete
    output_dir: str = "./output"
    state_dir: str = "./state"        # persistent: embedding store, label cache, previous run
    seed: int = 42


class DedupCfg(_Strict):
    enabled: bool = True


class InputCfg(_Strict):
    format: Literal["thaijo_md", "table"] = "thaijo_md"
    path: str = "../corpus"
    glob: str = "**/*.md"
    workers: int = Field(4, ge=1)
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
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "ATLAS_API_KEY"
    model: str = "text-embedding-3-large"
    dimensions: int | None = 1024
    batch_size: int = 256
    max_retries: int = 6
    checkpoint_every: int = 5000


class LocalEmbedCfg(_Strict):
    model: str = "BAAI/bge-m3"
    device: str = "cuda"
    batch_size: int = 32
    fp16: bool = True
    max_seq_length: int = 1024
    checkpoint_every: int = 5000


class LiteEmbedCfg(_Strict):
    dim: int = 128
    ngram_min: int = 2
    ngram_max: int = 4
    max_features: int = 100_000
    min_df: int = 2


class EmbeddingCfg(_Strict):
    provider: Literal["api", "local", "lite"] = "lite"
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


class ClusteringCfg(_Strict):
    reducer: Literal["umap", "pca"] = "umap"
    pca_dims: int = 128
    umap_fit_sample: int = 150_000
    fine: FineLevelCfg = Field(default_factory=FineLevelCfg)
    merge_similarity: float = Field(0.8, ge=0.0, le=1.0)
    outlier_min_similarity: float = Field(0.35, ge=-1.0, le=1.0)
    n_groups: int = Field(20, ge=1)
    ctfidf_top_n: int = 20
    ctfidf_max_docs_per_topic: int = 400


class LabelApiCfg(_Strict):
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "ATLAS_API_KEY"
    model: str = "gpt-5-mini"
    temperature: float = 0.2
    max_retries: int = 5
    concurrency: int = 8


class LabelingCfg(_Strict):
    provider: Literal["api", "off"] = "off"
    api: LabelApiCfg = Field(default_factory=LabelApiCfg)
    n_repr_docs: int = 8
    mmr_lambda: float = Field(0.7, ge=0.0, le=1.0)


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
    definition_version: Literal[2] = 2
    min_year_complete: int | None = None
    backfill_min_ratio: float = 0.6
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


class ForecastCfg(_Strict):
    horizon: int = 2
    min_history_years: int = 6
    models: list[Literal["naive", "linear", "poisson"]] = Field(
        default_factory=lambda: ["naive", "linear", "poisson"])
    backtest_years: int = 3
    min_skill: float = 0.0


class LayoutCfg(_Strict):
    umap_2d_neighbors: int = 12
    umap_2d_min_dist: float = 0.35
    view_w: int = 1680
    view_h: int = 1040
    edge_similarity_threshold: float = 0.55
    max_edges_per_node: int = 4


class ExportCfg(_Strict):
    formats: list[Literal["json", "csv"]] = Field(default_factory=lambda: ["json", "csv"])
    include_forecast_in_json: bool = True


class AtlasConfig(_Strict):
    pipeline: PipelineCfg = Field(default_factory=PipelineCfg)
    input: InputCfg = Field(default_factory=InputCfg)
    embedding: EmbeddingCfg = Field(default_factory=EmbeddingCfg)
    clustering: ClusteringCfg = Field(default_factory=ClusteringCfg)
    labeling: LabelingCfg = Field(default_factory=LabelingCfg)
    emerging: EmergingCfg = Field(default_factory=EmergingCfg)
    forecast: ForecastCfg = Field(default_factory=ForecastCfg)
    layout: LayoutCfg = Field(default_factory=LayoutCfg)
    export: ExportCfg = Field(default_factory=ExportCfg)


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
    return cfg
