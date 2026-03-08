"""Create optimization_job and automation_suggestion tables.

Feature 38: Optimization Persistence.

Revision ID: 033_optimization_tables
Revises: 032_agent_config_tool_groups
Create Date: 2026-02-28
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "033_optimization_tables"
down_revision: str | None = "032_agent_config_tool_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "optimization_job",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("analysis_types", postgresql.JSONB(), nullable=True),
        sa.Column("hours_analyzed", sa.Integer(), nullable=True),
        sa.Column("insight_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("suggestion_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendations", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "automation_suggestion",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("optimization_job.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("entities", postgresql.JSONB(), nullable=True),
        sa.Column("proposed_trigger", sa.String(500), nullable=True),
        sa.Column("proposed_action", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_insight_type", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("automation_suggestion")
    op.drop_table("optimization_job")
