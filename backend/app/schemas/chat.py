"""Validated request and response objects for legal chat."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, JsonValue

CHAT_DISCLAIMER = (
    "AI 生成内容仅供参考，不构成法律意见。重要事项请核对原始依据或咨询专业人士。"
)
NO_RETRIEVAL_WARNING = "当前版本尚未接入法律资料检索，未提供可核验来源。"
NO_CONTEXT_WARNING = "当前版本仅保存会话归属，不保存消息正文或上下文。"

DocumentType = Literal["civil_complaint", "civil_defense", "general_contract"]
IntentType = Literal["qa", "search", "document"]
SourceKind = Literal["demo", "official", "public_reference"]
SourceType = Literal["case", "legal_provision"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = None
    document_type: DocumentType | None = None
    document_params: dict[str, JsonValue] | None = None


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_type: SourceType
    source_id: UUID
    title: str = Field(min_length=1, max_length=500)
    reference_number: str = Field(min_length=1, max_length=200)
    publisher: str = Field(min_length=1, max_length=300)
    date: date
    source_url: AnyHttpUrl | None = None
    source_kind: SourceKind
    is_demo: bool


class ChatData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: str = Field(min_length=1, max_length=20000)
    intent: IntentType
    sources: list[SourceReference]
    session_id: UUID
    missing_fields: list[str]
    warnings: list[str]


class DeletedConversationData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deleted_session_id: UUID
