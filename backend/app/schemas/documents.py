"""Document templates are the sole field-definition source for API clients."""

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.chat import DocumentType, SourceReference

DRAFT_WARNING = "草稿，提交或签署前须人工审核"


class TemplateField(BaseModel):
    name: str
    label: str
    required: bool = True
    max_length: int


class DocumentTemplate(BaseModel):
    document_type: DocumentType
    name: str
    fields: list[TemplateField]


def _fields(*items: tuple[str, str, int]) -> list[TemplateField]:
    return [TemplateField(name=name, label=label, max_length=limit) for name, label, limit in items]


TEMPLATES = {
    "civil_complaint": DocumentTemplate(document_type="civil_complaint", name="民事起诉状", fields=_fields(
        ("plaintiff", "原告", 500), ("defendant", "被告", 500), ("claims", "诉讼请求", 4000),
        ("facts_and_reasons", "事实与理由", 4000), ("court", "受理法院", 500))),
    "civil_defense": DocumentTemplate(document_type="civil_defense", name="民事答辩状", fields=_fields(
        ("respondent", "答辩人", 500), ("case_reference", "案件标识（按已知材料填写）", 500),
        ("defense_opinions", "答辩意见", 4000), ("court", "受理法院", 500))),
    "general_contract": DocumentTemplate(document_type="general_contract", name="通用合同", fields=_fields(
        ("party_a", "甲方", 500), ("party_b", "乙方", 500), ("subject", "合同标的", 500),
        ("main_terms", "主要条款", 4000), ("effective_date", "生效日期或生效条件", 500))),
}


class TemplatesData(BaseModel):
    items: list[DocumentTemplate]


class DocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    document_type: DocumentType
    parameters: dict[str, str]
    additional_instructions: str = Field(default="", max_length=4000)
    use_references: bool = True

    @field_validator("parameters", mode="before")
    @classmethod
    def validate_parameter_size(cls, value):
        if not isinstance(value, dict) or len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 20480:
            raise ValueError("Invalid parameters")
        return value


class DocumentData(BaseModel):
    document_id: UUID
    document_type: DocumentType
    title: str
    content: str
    sources: list[SourceReference]
    warnings: list[str]
    created_at: datetime
