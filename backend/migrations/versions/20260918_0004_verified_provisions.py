"""Add provenance and version metadata without changing existing legal records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260918_0004"
down_revision = "20260917_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("legal_provisions", sa.Column("verification", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True))


def downgrade():
    op.drop_column("legal_provisions", "verification")
