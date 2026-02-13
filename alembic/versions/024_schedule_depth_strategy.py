"""Add depth, strategy, timeout_seconds columns to insight_schedules.

Feature 33: DS Deep Analysis — configurable analysis profiles for scheduled jobs.

Revision ID: 024_schedule_depth_strategy
Revises: 023_analysis_reports
Create Date: 2026-02-13
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "024_schedule_depth_strategy"
down_revision: str | None = "023_analysis_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add depth, strategy, and timeout_seconds to insight_schedules."""
    op.add_column(
        "insight_schedules",
        sa.Column(
            "depth",
            sa.String(20),
            nullable=False,
            server_default="standard",
        ),
    )
    op.add_column(
        "insight_schedules",
        sa.Column(
            "strategy",
            sa.String(20),
            nullable=False,
            server_default="parallel",
        ),
    )
    op.add_column(
        "insight_schedules",
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove depth, strategy, and timeout_seconds from insight_schedules."""
    op.drop_column("insight_schedules", "timeout_seconds")
    op.drop_column("insight_schedules", "strategy")
    op.drop_column("insight_schedules", "depth")
