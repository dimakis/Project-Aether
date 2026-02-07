"""Add model_ratings table.

Stores per-agent model quality ratings with config snapshots.

Revision ID: 017_model_ratings
Revises: 016_user_profiles
Create Date: 2026-02-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "017_model_ratings"
down_revision: str | None = "016_user_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create model_ratings table."""
    op.create_table(
        "model_ratings",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("agent_role", sa.String(50), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("config_snapshot", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_model_ratings_rating_range"),
    )

    op.create_index("ix_model_ratings_model_name", "model_ratings", ["model_name"])
    op.create_index("ix_model_ratings_agent_role", "model_ratings", ["agent_role"])
    op.create_index("ix_model_ratings_model_agent", "model_ratings", ["model_name", "agent_role"])


def downgrade() -> None:
    """Drop model_ratings table."""
    op.drop_index("ix_model_ratings_model_agent", table_name="model_ratings")
    op.drop_index("ix_model_ratings_agent_role", table_name="model_ratings")
    op.drop_index("ix_model_ratings_model_name", table_name="model_ratings")
    op.drop_table("model_ratings")
