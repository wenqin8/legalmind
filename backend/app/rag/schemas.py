"""Strict source and normalized schemas for legal knowledge imports."""

import re
from datetime import date, datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import ImportStatus, LegalDomain, LegalStatus, SourceKind, SourceType

DEMO_CASE_ID_PATTERN = re.compile(
    r"^DEMO-(MARRIAGE_FAMILY|LABOR_DISPUTE|TRAFFIC_ACCIDENT|CONTRACT_DISPUTE)-\d{3}$"
)


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CaseSourceRecord(StrictSchema):
    demo_id: str | None = None
    case_number: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    domain: LegalDomain
    summary: str = Field(min_length=1, max_length=5000)
    facts: str = Field(min_length=1, max_length=20000)
    dispute_focus: str = Field(min_length=1, max_length=10000)
    reasoning: str = Field(min_length=1, max_length=20000)
    court: str | None = Field(default=None, max_length=300)
    judgment_date: date | None = None
    sample_date: date | None = None
    law_references: list[str] = Field(default_factory=list, max_length=100)
    source_type: SourceType
    source_kind: SourceKind
    source_title: str = Field(min_length=1, max_length=500)
    source_description: str = Field(min_length=1, max_length=5000)
    source_url: AnyHttpUrl | None = None
    publisher: str | None = Field(default=None, max_length=300)
    is_demo: bool
    is_synthetic: bool
    collected_at: datetime
    authorization_note: str = Field(min_length=1, max_length=5000)

    @field_validator("law_references")
    @classmethod
    def validate_law_references(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Law references cannot contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Law references must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_source_invariants(self) -> "CaseSourceRecord":
        if self.source_type != SourceType.CASE:
            raise ValueError("Case records must use source_type=case")
        if self.collected_at.tzinfo is None:
            raise ValueError("collected_at must include a timezone")

        if self.is_demo:
            if self.demo_id is None or not DEMO_CASE_ID_PATTERN.fullmatch(self.demo_id):
                raise ValueError("Demo cases require a valid DEMO identifier")
            if self.case_number != self.demo_id:
                raise ValueError("Demo case_number must equal demo_id")
            if self.source_kind != SourceKind.DEMO or not self.is_synthetic:
                raise ValueError("Demo cases must be synthetic demo sources")
            if any((self.court, self.judgment_date, self.source_url, self.law_references)):
                raise ValueError("Demo cases cannot invent court, judgment, URL, or law data")
            if self.sample_date is None:
                raise ValueError("Demo cases require a sample_date")
            if "课程演示合成数据" not in self.source_description:
                raise ValueError("Demo cases require an explicit synthetic-data source label")
            if "不得作为真实案例" not in self.authorization_note:
                raise ValueError("Demo authorization must prohibit real-case representation")
        else:
            if self.demo_id is not None or self.case_number.startswith("DEMO-"):
                raise ValueError("Non-demo cases cannot use demo identifiers")
            if self.source_kind == SourceKind.DEMO or self.is_synthetic:
                raise ValueError("Non-demo cases cannot use demo source flags")
            if any(value is None for value in (self.court, self.judgment_date, self.source_url)):
                raise ValueError("Non-demo cases require court, judgment_date, and source_url")
            if not self.publisher:
                raise ValueError("Non-demo cases require a publisher")
        return self


class LegalProvisionSourceRecord(StrictSchema):
    record_id: str = Field(min_length=1, max_length=200)
    regulation_name: str = Field(min_length=1, max_length=500)
    article_number: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=30000)
    issuing_authority: str = Field(min_length=1, max_length=300)
    published_at: date
    effective_at: date | None = None
    legal_status: LegalStatus
    source_type: SourceType
    source_kind: SourceKind
    source_title: str = Field(min_length=1, max_length=500)
    source_description: str = Field(min_length=1, max_length=5000)
    source_url: AnyHttpUrl | None = None
    publisher: str | None = Field(default=None, max_length=300)
    is_demo: bool = False
    is_synthetic: bool = False
    collected_at: datetime
    authorization_note: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_source_invariants(self) -> "LegalProvisionSourceRecord":
        if self.source_type != SourceType.LEGAL_PROVISION:
            raise ValueError("Legal provisions must use source_type=legal_provision")
        if self.collected_at.tzinfo is None:
            raise ValueError("collected_at must include a timezone")
        if self.is_demo or self.is_synthetic or self.source_kind == SourceKind.DEMO:
            raise ValueError("Week-two legal provisions must be verified non-demo sources")
        if self.source_url is None or not self.publisher:
            raise ValueError("Legal provisions require a publisher and source_url")
        return self


class NormalizedCaseRecord(StrictSchema):
    id: UUID
    case_number: str
    title: str
    domain: LegalDomain
    summary: str
    facts: str
    dispute_focus: str
    reasoning: str
    court: str | None
    judgment_date: date | None
    sample_date: date | None
    law_references: list[str]
    source_kind: SourceKind
    source_title: str
    source_description: str
    source_url: str | None
    publisher: str | None
    is_demo: bool
    is_synthetic: bool
    collected_at: datetime
    authorization_note: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    import_status: ImportStatus = ImportStatus.PENDING


class NormalizedLegalProvisionRecord(StrictSchema):
    id: UUID
    record_id: str
    regulation_name: str
    article_number: str
    content: str
    issuing_authority: str
    published_at: date
    effective_at: date | None
    legal_status: LegalStatus
    source_kind: SourceKind
    source_title: str
    source_description: str
    source_url: str
    publisher: str
    is_demo: bool
    is_synthetic: bool
    collected_at: datetime
    authorization_note: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    import_status: ImportStatus = ImportStatus.PENDING


class ImportSummary(StrictSchema):
    received: int
    created: int
    skipped: int
