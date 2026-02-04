"""Fix insights schema to align with data model.

Revision ID: 005_fix_insights_schema
Revises: 004_insights
Create Date: 2026-02-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_fix_insights_schema"
down_revision: str | None = "004_insights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop old insights table and recreate with correct schema."""
    # Drop old table and types (no data expected)
    op.execute("DROP TABLE IF EXISTS insights CASCADE")
    op.execute("DROP TYPE IF EXISTS insightstatus")
    op.execute("DROP TYPE IF EXISTS insighttype")
    op.execute("DROP TYPE IF EXISTS insightimpact")

    # Define enums per data-model.md
    insight_type = sa.Enum(
        "energy_optimization",
        "pattern",
        "anomaly",
        "recommendation",
        name="insighttype",
    )
    insight_status = sa.Enum(
        "generated",
        "reviewed",
        "acted_upon",
        "dismissed",
        name="insightstatus",
    )
    insight_impact = sa.Enum(
        "low",
        "medium",
        "high",
        name="insightimpact",
    )

    op.create_table(
        "insights",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("type", insight_type, nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("impact", insight_impact, nullable=False),
        sa.Column(
            "entities",
            postgresql.ARRAY(postgresql.UUID(as_uuid=False)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("script_path", sa.String(512), nullable=True),
        sa.Column("script_output", postgresql.JSONB, nullable=True),
        sa.Column(
            "status",
            insight_status,
            nullable=False,
            server_default=sa.text("'generated'"),
            index=True,
        ),
        sa.Column("mlflow_run_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_insights_created_at", "insights", ["created_at"])
    op.create_index("ix_insights_mlflow_run_id", "insights", ["mlflow_run_id"])


def downgrade() -> None:
    """Restore previous insights schema."""
    op.execute("DROP TABLE IF EXISTS insights CASCADE")
    op.execute("DROP TYPE IF EXISTS insightstatus")
    op.execute("DROP TYPE IF EXISTS insighttype")
    op.execute("DROP TYPE IF EXISTS insightimpact")

    # Previous enums from 004_insights
    insight_type = sa.Enum(
        "energy_optimization",
        "anomaly_detection",
        "usage_pattern",
        "cost_saving",
        "maintenance_prediction",
        name="insighttype",
    )
    insight_status = sa.Enum(
        "pending",
        "reviewed",
        "actioned",
        "dismissed",
        name="insightstatus",
    )

    op.create_table(
        "insights",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", insight_type, nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("impact", sa.String(50), nullable=False),
        sa.Column("entities", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("script_path", sa.String(512), nullable=True),
        sa.Column("script_output", sa.JSON, nullable=True),
        sa.Column(
            "status",
            insight_status,
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("mlflow_run_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actioned_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_insights_created_at", "insights", ["created_at"])
    op.create_index("ix_insights_mlflow_run_id", "insights", ["mlflow_run_id"])
