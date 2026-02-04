"""Create insights table for User Story 3.

Revision ID: 004
Revises: 003
Create Date: 2026-02-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_insights"
down_revision: Union[str, None] = "003_conversations_us2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create insights table."""
    # Define enum types
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

    # Create insights table (enums created automatically)
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
        sa.Column("status", insight_status, nullable=False, server_default="pending", index=True),
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

    # Create additional indexes
    op.create_index("ix_insights_created_at", "insights", ["created_at"])
    op.create_index("ix_insights_mlflow_run_id", "insights", ["mlflow_run_id"])


def downgrade() -> None:
    """Drop insights table."""
    op.drop_index("ix_insights_mlflow_run_id", table_name="insights")
    op.drop_index("ix_insights_created_at", table_name="insights")
    op.drop_table("insights")
    op.execute("DROP TYPE insightstatus")
    op.execute("DROP TYPE insighttype")
