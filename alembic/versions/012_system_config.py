"""Add system_config table for HA-verified setup.

Stores HA connection details (URL + encrypted token), admin password hash,
and setup completion timestamp. Single-row table created during first-time setup.

Revision ID: 012_system_config
Revises: 011_llm_usage
Create Date: 2026-02-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "012_system_config"
down_revision: str | None = "011_llm_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create system_config table."""
    op.create_table(
        "system_config",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("ha_url", sa.String(500), nullable=False),
        sa.Column("ha_token_encrypted", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column(
            "setup_completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
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
    """Drop system_config table."""
    op.drop_table("system_config")
