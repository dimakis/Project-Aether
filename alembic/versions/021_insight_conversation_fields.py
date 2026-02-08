"""Add conversation_id and task_label columns to insights.

Links insights to their originating conversation and task context
for the generic agent execution tracking system.

Revision ID: 021_insight_conversation_fields
Revises: 020_ha_zones
Create Date: 2026-02-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021_insight_conversation_fields"
down_revision: str | None = "020_ha_zones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "insights",
        sa.Column("conversation_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "insights",
        sa.Column("task_label", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_insights_conversation_id",
        "insights",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_insights_conversation_id", table_name="insights")
    op.drop_column("insights", "task_label")
    op.drop_column("insights", "conversation_id")
