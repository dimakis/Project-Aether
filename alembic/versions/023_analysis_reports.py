"""Add analysis_reports table for DS deep analysis.

Stores comprehensive analysis reports with depth, strategy, linked
insights, artifact paths, and communication logs.

Feature 33: DS Deep Analysis.

Revision ID: 023_analysis_reports
Revises: 796cc7a68dd3
Create Date: 2026-02-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "023_analysis_reports"
down_revision: str | None = "796cc7a68dd3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("analysis_type", sa.String(50), nullable=False, index=True),
        sa.Column("depth", sa.String(20), nullable=False),
        sa.Column("strategy", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "completed", "failed", name="reportstatus"),
            nullable=False,
            server_default="running",
            index=True,
        ),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("insight_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("artifact_paths", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("communication_log", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("communication_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("conversation_id", sa.String(36), nullable=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("analysis_reports")
    # Drop the enum type if using PostgreSQL
    op.execute("DROP TYPE IF EXISTS reportstatus")
