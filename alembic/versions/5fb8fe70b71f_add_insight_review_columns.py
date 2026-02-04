"""add insight review columns

Revision ID: 5fb8fe70b71f
Revises: 005_fix_insights_schema
Create Date: 2026-02-04 22:26:04.617125
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5fb8fe70b71f"
down_revision: str | None = "005_fix_insights_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add reviewed_at and actioned_at columns to insights table."""
    op.add_column(
        "insights",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "insights",
        sa.Column("actioned_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove reviewed_at and actioned_at columns from insights table."""
    op.drop_column("insights", "actioned_at")
    op.drop_column("insights", "reviewed_at")
