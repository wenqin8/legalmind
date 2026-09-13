"""Relational models for identity, ownership, and legal knowledge."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


JSON_VALUE = JSON().with_variant(JSONB(), "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    username_normalized: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    email_normalized: Mapped[str] = mapped_column(
        String(254), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_id_user_id", "id", "user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="新咨询")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="conversations")


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(
            "domain IN ('marriage_family', 'labor_dispute', 'traffic_accident', 'contract_dispute')",
            name="ck_cases_domain",
        ),
        CheckConstraint(
            "source_kind IN ('demo', 'official', 'public_reference')",
            name="ck_cases_source_kind",
        ),
        CheckConstraint(
            "import_status IN ('pending', 'indexed', 'failed')",
            name="ck_cases_import_status",
        ),
        CheckConstraint(
            "(is_demo AND is_synthetic AND source_kind = 'demo' "
            "AND case_number LIKE 'DEMO-%' AND court IS NULL "
            "AND judgment_date IS NULL AND source_url IS NULL) "
            "OR (NOT is_demo AND NOT is_synthetic AND source_kind <> 'demo' "
            "AND court IS NOT NULL AND judgment_date IS NOT NULL AND source_url IS NOT NULL)",
            name="ck_cases_source_consistency",
        ),
        Index("ix_cases_domain_status", "domain", "import_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    case_number: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    court: Mapped[str | None] = mapped_column(String(300))
    judgment_date: Mapped[date | None] = mapped_column(Date)
    sample_date: Mapped[date | None] = mapped_column(Date)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    facts: Mapped[str] = mapped_column(Text, nullable=False)
    dispute_focus: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    law_references: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False, default=list)
    source_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(300))
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    authorization_note: Mapped[str] = mapped_column(Text, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    import_status: Mapped[str] = mapped_column(String(20), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class LegalProvision(Base):
    __tablename__ = "legal_provisions"
    __table_args__ = (
        CheckConstraint(
            "legal_status IN ('effective', 'amended', 'repealed', 'unknown')",
            name="ck_legal_provisions_legal_status",
        ),
        CheckConstraint(
            "source_kind IN ('official', 'public_reference')",
            name="ck_legal_provisions_source_kind",
        ),
        CheckConstraint(
            "import_status IN ('pending', 'indexed', 'failed')",
            name="ck_legal_provisions_import_status",
        ),
        UniqueConstraint(
            "regulation_name",
            "article_number",
            "content_hash",
            name="uq_legal_provisions_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    record_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    regulation_name: Mapped[str] = mapped_column(String(500), nullable=False)
    article_number: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(300), nullable=False)
    published_at: Mapped[date] = mapped_column(Date, nullable=False)
    effective_at: Mapped[date | None] = mapped_column(Date)
    legal_status: Mapped[str] = mapped_column(String(20), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    publisher: Mapped[str] = mapped_column(String(300), nullable=False)
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    authorization_note: Mapped[str] = mapped_column(Text, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    import_status: Mapped[str] = mapped_column(String(20), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('case', 'legal_provision')",
            name="ck_knowledge_chunks_source_type",
        ),
        CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_index"),
        CheckConstraint("character_count > 0", name="ck_knowledge_chunks_character_count"),
        UniqueConstraint(
            "source_type",
            "source_id",
            "chunk_index",
            name="uq_knowledge_chunks_source_index",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
