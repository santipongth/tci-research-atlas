"""Corpus format 1.0 — the article files the data team prepares (docs/corpus/README.md).

One JSON object per line (JSON Lines, UTF-8) in corpus/articles/*.jsonl or *.jsonl.gz; journal details live in
corpus/journals.csv (same columns as registry/journals.example.csv). Field names follow Crossref / JATS / OpenAlex;
dates are ISO 8601, years are Common Era, languages ISO 639-1, countries ISO 3166-1 alpha-2, Thai provinces
ISO 3166-2:TH. The pydantic models are the source of truth → docs/corpus/corpus.schema.json (`atlas corpus schema`).
Unknown keys are errors (they catch misspelt field names); anything else the team wants to keep goes in `extra`.
Author names are read for affiliations only and are never published (PDPA).
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CORPUS_SCHEMA = "tci-atlas-corpus/1.0"
ArticleType = Literal["research-article", "review-article", "academic-article", "case-report",
                      "short-communication", "book-review", "editorial", "erratum", "other"]
Role = Literal["lecturer", "researcher", "student-master", "student-doctoral", "student", "other"]
STUDENT_ROLES = ("student-master", "student-doctoral", "student")
DOI = r"^10\.\d{4,9}/\S+$"
ORCID = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"
ROR = r"^https://ror\.org/0[a-z0-9]{6}\d{2}$"
ISSN = r"^\d{4}-\d{3}[\dX]$"
KEY = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$"      # ids and journal keys: ASCII, no spaces
URL = r"^https?://\S+$"


@lru_cache(maxsize=1)
def _province_codes() -> frozenset[str]:
    from atlas.places import provinces
    return frozenset(provinces())


def _year(v: int | None, what: str) -> int | None:
    if v is not None and v > 2400:
        raise ValueError(f"{what} {v} looks like a Buddhist Era year: write the Common Era year ({v - 543})")
    return v


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)


class LangText(_M):
    th: str | None = None
    en: str | None = None


class Keywords(_M):
    th: list[str] = Field(default_factory=list)
    en: list[str] = Field(default_factory=list)


class Pages(_M):
    first: str | None = None
    last: str | None = None


class Affiliation(_M):
    name: LangText                                   # the affiliation as printed, e.g. faculty + university
    ror: str | None = Field(None, pattern=ROR)
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    province: str | None = Field(None, pattern=r"^TH-\d{2}$")

    @field_validator("province")
    @classmethod
    def _known_province(cls, v: str | None) -> str | None:
        if v is not None and v not in _province_codes():
            raise ValueError(f"{v} is not one of the 77 ISO 3166-2:TH province codes")
        return v


class Author(_M):
    position: int | None = Field(None, ge=1)         # 1 = first author; the list order is used when absent
    name: LangText                                    # read only to keep authors apart — never published
    orcid: str | None = Field(None, pattern=ORCID)
    corresponding: bool | None = None
    role: Role | None = None
    affiliations: list[Affiliation] = Field(default_factory=list)


class Reference(_M):
    text: str = Field(min_length=1)                   # one whole reference, as printed
    doi: str | None = Field(None, pattern=DOI)
    year: int | None = Field(None, ge=1500, le=2400)
    translated: bool = False                          # the romanised copy of a Thai reference ("Translated Thai References")

    @field_validator("year", mode="after")
    @classmethod
    def _ce(cls, v: int | None) -> int | None:
        return _year(v, "reference year")


class Funding(_M):
    funder: str = Field(min_length=1)
    grant_id: str | None = None


class Provenance(_M):
    retrieved: date | None = None
    extracted_from: Literal["html", "pdf", "oai-pmh", "api", "manual", "other"] | None = None
    ocr: bool | None = None


class Article(_M):
    schema_version: Literal["tci-atlas-corpus/1.0"] = Field(alias="schema")
    id: str | None = Field(None, pattern=KEY)         # stable across quarters; derived when absent (see the guide)
    source: Literal["thaijo", "tci", "other"] | None = None
    doi: str | None = Field(None, pattern=DOI)
    url: str | None = Field(None, pattern=URL)
    issue_url: str | None = Field(None, pattern=URL)
    journal_key: str = Field(pattern=KEY)            # the journal's row in journals.csv
    journal_title: LangText | None = None
    issn: str | None = Field(None, pattern=ISSN)
    eissn: str | None = Field(None, pattern=ISSN)
    volume: str | None = None
    issue: str | None = None
    pages: Pages | None = None
    published: date | None = None
    year: int | None = Field(None, ge=1900, le=2600)
    article_type: ArticleType | None = None
    language: str | None = Field(None, pattern=r"^[a-z]{2}$")
    title: LangText
    abstract: LangText | None = None
    keywords: Keywords | None = None
    authors: list[Author] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    funding: list[Funding] = Field(default_factory=list)
    license: str | None = None
    provenance: Provenance | None = None
    extra: dict[str, Any] | None = None

    @field_validator("year", mode="after")
    @classmethod
    def _ce(cls, v: int | None) -> int | None:
        v = _year(v, "year")
        if v is not None and v > 2100:
            raise ValueError(f"year {v} is in the future")
        return v

    @field_validator("published", mode="after")
    @classmethod
    def _published_ce(cls, v: date | None) -> date | None:
        if v is not None:
            _year(v.year, "published year")
        return v

    @model_validator(mode="after")
    def _consistent(self) -> Article:
        if not (self.title.th or self.title.en):
            raise ValueError("title needs th or en")
        if self.published and self.year and self.published.year != self.year:
            raise ValueError(f"year {self.year} differs from the year of published ({self.published.isoformat()})")
        return self


def corpus_json_schema() -> dict:
    s = Article.model_json_schema(by_alias=True)
    s["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    s["$id"] = "https://github.com/santipongth/tci-research-atlas/docs/corpus/corpus.schema.json"
    s["title"] = f"TCI Research Atlas corpus article ({CORPUS_SCHEMA})"
    return s


def write_corpus_schema(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(corpus_json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                 encoding="utf-8")
    return p
