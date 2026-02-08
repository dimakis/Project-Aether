"""Add url_preference column to ha_zone table.

Allows users to choose which URL (local, remote, or auto-fallback)
the backend uses when connecting to their Home Assistant instance.

Revision ID: 022_zone_url_preference
Revises: 021_insight_conversation_fields
Create Date: 2026-02-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "022_zone_url_preference"
down_revision: str | None = "021_insight_conversation_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ha_zone",
        sa.Column(
            "url_preference",
            sa.String(10),
            nullable=False,
            server_default="auto",
        ),
    )


def downgrade() -> None:
    op.drop_column("ha_zone", "url_preference")
