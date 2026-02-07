"""Add insight_schedules table for scheduled and event-driven analysis.

Feature 10: Scheduled & Event-Driven Insights.

Revision ID: 008_insight_schedules
Revises: 007_insight_types_behavioral
Create Date: 2026-02-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_insight_schedules"
down_revision: str | None = "007_insight_types_behavioral"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create insight_schedules table."""
    op.create_table(
        "insight_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # What to run
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("entity_ids", sa.JSON(), nullable=True),
        sa.Column("hours", sa.Integer(), nullable=False, server_default=sa.text("24")),
        sa.Column("options", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        # Trigger configuration
        sa.Column("trigger_type", sa.String(20), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=True),
        sa.Column("webhook_event", sa.String(100), nullable=True),
        sa.Column("webhook_filter", sa.JSON(), nullable=True),
        # Execution tracking
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_result", sa.String(20), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Index for webhook matching
    op.create_index("ix_insight_schedules_trigger_type", "insight_schedules", ["trigger_type"])
    op.create_index("ix_insight_schedules_webhook_event", "insight_schedules", ["webhook_event"])
    op.create_index("ix_insight_schedules_enabled", "insight_schedules", ["enabled"])


def downgrade() -> None:
    """Drop insight_schedules table."""
    op.drop_index("ix_insight_schedules_enabled", table_name="insight_schedules")
    op.drop_index("ix_insight_schedules_webhook_event", table_name="insight_schedules")
    op.drop_index("ix_insight_schedules_trigger_type", table_name="insight_schedules")
    op.drop_table("insight_schedules")
