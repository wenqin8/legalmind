"""Create legal source and knowledge chunk tables.

Revision ID: 20260913_0002
Revises: 20260912_0001
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0002"
down_revision: str | Sequence[str] | None = "20260912_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_value = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_number", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("court", sa.String(length=300), nullable=True),
        sa.Column("judgment_date", sa.Date(), nullable=True),
        sa.Column("sample_date", sa.Date(), nullable=True),
        sa.Column("domain", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("facts", sa.Text(), nullable=False),
        sa.Column("dispute_focus", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("law_references", json_value, nullable=False),
        sa.Column("source_kind", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_title", sa.String(length=500), nullable=False),
        sa.Column("publisher", sa.String(length=300), nullable=True),
        sa.Column("source_description", sa.Text(), nullable=False),
        sa.Column("authorization_note", sa.Text(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("import_status", sa.String(length=20), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "domain IN ('marriage_family', 'labor_dispute', 'traffic_accident', 'contract_dispute')",
            name="ck_cases_domain",
        ),
        sa.CheckConstraint(
            "source_kind IN ('demo', 'official', 'public_reference')",
            name="ck_cases_source_kind",
        ),
        sa.CheckConstraint(
            "import_status IN ('pending', 'indexed', 'failed')",
            name="ck_cases_import_status",
        ),
        sa.CheckConstraint(
            "(is_demo AND is_synthetic AND source_kind = 'demo' "
            "AND case_number LIKE 'DEMO-%' AND court IS NULL "
            "AND judgment_date IS NULL AND source_url IS NULL) "
            "OR (NOT is_demo AND NOT is_synthetic AND source_kind <> 'demo' "
            "AND court IS NOT NULL AND judgment_date IS NOT NULL AND source_url IS NOT NULL)",
            name="ck_cases_source_consistency",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_number"),
        sa.UniqueConstraint("content_hash"),
    )
    op.create_index(
        "ix_cases_domain_status",
        "cases",
        ["domain", "import_status"],
        unique=False,
    )

    op.create_table(
        "legal_provisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.String(length=200), nullable=False),
        sa.Column("regulation_name", sa.String(length=500), nullable=False),
        sa.Column("article_number", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("issuing_authority", sa.String(length=300), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=False),
        sa.Column("effective_at", sa.Date(), nullable=True),
        sa.Column("legal_status", sa.String(length=20), nullable=False),
        sa.Column("source_kind", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("source_title", sa.String(length=500), nullable=False),
        sa.Column("publisher", sa.String(length=300), nullable=False),
        sa.Column("source_description", sa.Text(), nullable=False),
        sa.Column("authorization_note", sa.Text(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("import_status", sa.String(length=20), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "legal_status IN ('effective', 'amended', 'repealed', 'unknown')",
            name="ck_legal_provisions_legal_status",
        ),
        sa.CheckConstraint(
            "source_kind IN ('official', 'public_reference')",
            name="ck_legal_provisions_source_kind",
        ),
        sa.CheckConstraint(
            "import_status IN ('pending', 'indexed', 'failed')",
            name="ck_legal_provisions_import_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash"),
        sa.UniqueConstraint("record_id"),
        sa.UniqueConstraint(
            "regulation_name",
            "article_number",
            "content_hash",
            name="uq_legal_provisions_version",
        ),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('case', 'legal_provision')",
            name="ck_knowledge_chunks_source_type",
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_index"),
        sa.CheckConstraint(
            "character_count > 0",
            name="ck_knowledge_chunks_character_count",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash"),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "chunk_index",
            name="uq_knowledge_chunks_source_index",
        ),
    )


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_table("legal_provisions")
    op.drop_index("ix_cases_domain_status", table_name="cases")
    op.drop_table("cases")
