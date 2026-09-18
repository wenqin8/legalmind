"""Add owned generated document drafts.

Revision ID: 20260917_0003
Revises: 20260913_0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260917_0003"
down_revision = "20260913_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversations", sa.Column("history_commit_id", sa.Uuid(), nullable=True))
    json_value = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "generated_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parameters", json_value, nullable=False),
        sa.Column("additional_instructions", sa.Text(), nullable=False),
        sa.Column("sources", json_value, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("document_type IN ('civil_complaint', 'civil_defense', 'general_contract')", name="ck_documents_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_documents_id_user_id", "generated_documents", ["id", "user_id"])


def downgrade():
    op.drop_index("ix_generated_documents_id_user_id", table_name="generated_documents")
    op.drop_table("generated_documents")
    op.drop_column("conversations", "history_commit_id")
