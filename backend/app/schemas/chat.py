"""Validated request and response objects for legal chat."""

from datetime import date as Date, datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, JsonValue, model_validator
from app.schemas.tasks import TaskAction, TaskState

CHAT_DISCLAIMER = (
    "AI 生成内容仅供参考，不构成法律意见。重要事项请核对原始依据或咨询专业人士。"
)

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
    task_action: TaskAction | None = None
    task_revision: UUID | None = None


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_type: SourceType
    source_id: UUID
    title: str = Field(min_length=1, max_length=500)
    reference_number: str = Field(min_length=1, max_length=200)
    publisher: str | None = Field(default=None, min_length=1, max_length=300)
    date: Date | None = None
    sample_date: Date | None = None
    source_url: AnyHttpUrl | None = None
    source_kind: SourceKind
    is_demo: bool
    is_synthetic: bool = False
    citation_id: str = Field(default="S1", pattern=r"^S[1-5]$")
    version: str | None = None
    effective_from: Date | None = None
    effective_until: Date | None = None
    verified_at: Date | None = None
    status_as_of: Date | None = None
    legal_status: Literal["effective", "amended", "repealed", "unknown"] | None = None
    original_text: str | None = Field(default=None, max_length=30000)
    applicability: Literal["general_reference", "event_candidate"] | None = None
    temporal_rule: Literal['event_date', 'pending_after_effective'] = 'event_date'
    transition_text: str | None = None

    @model_validator(mode="after")
    def preserve_source_boundary(self):
        if (self.source_kind == "demo") != self.is_demo or self.is_demo != self.is_synthetic:
            raise ValueError("Inconsistent source kind")
        if self.is_demo and (self.date is not None or self.source_url is not None or not self.reference_number.startswith("DEMO-")):
            raise ValueError("Demo sources cannot contain judicial dates or links")
        if self.source_type == "legal_provision" and (self.source_kind != "official" or self.is_demo or
                not all((self.version, self.effective_from, self.verified_at, self.status_as_of, self.original_text, self.source_url, self.applicability))):
            raise ValueError("Legal citations require a verified official version and verbatim text")
        return self


class ChatData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: str = Field(min_length=1, max_length=32000)
    intent: IntentType
    sources: list[SourceReference]
    session_id: UUID
    missing_fields: list[str]
    warnings: list[str]
    document_id: UUID | None = None
    task: TaskState | None = None


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=32000)
    created_at: datetime
    turn_id: UUID | None = None
    intent: IntentType | None = None
    sources: list[SourceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    document_id: UUID | None = None
    task: TaskState | None = None


class HistoryData(BaseModel):
    session_id: UUID
    messages: list[ConversationMessage]
    history_expired: bool
    warnings: list[str]


class ConversationSummary(BaseModel):
    session_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    history_expired: bool


class ConversationsData(BaseModel):
    items: list[ConversationSummary]
    total: int
    offset: int
    limit: int


class DeletedConversationData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deleted_session_id: UUID
