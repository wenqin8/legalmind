"""Strict request and response schemas for the case retrieval API."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import LegalDomain, SourceKind

DEMO_CASE_WARNING = "课程演示合成数据，不是真实判例或法律依据"


class CaseSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=1000)
    domain: LegalDomain | None = None
    source_kind: SourceKind | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class CaseSearchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str
    case_number: str
    court: str | None
    judgment_date: date | None
    source_url: str | None
    domain: LegalDomain
    summary: str
    source_kind: SourceKind
    is_demo: bool
    is_synthetic: bool
    rrf_score: float
    vector_rank: int | None
    bm25_rank: int | None


class CaseSearchData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CaseSearchItem]
    count: int
    score_note: str = "rrf_score 仅表示检索排序依据，不表示法律结论置信度"


class CaseDetailData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str
    case_number: str
    court: str | None
    judgment_date: date | None
    sample_date: date | None
    domain: LegalDomain
    summary: str
    facts: str
    dispute_focus: str
    reasoning: str
    law_references: list[str]
    source_kind: SourceKind
    source_url: str | None
    source_title: str
    publisher: str | None
    source_description: str
    authorization_note: str
    is_demo: bool
    is_synthetic: bool
    warning: str
