"""Add ha_zone table for multi-server HA support.

Seeds the default zone from the existing system_config row so that
existing installations keep working without re-setup.

Revision ID: 020_ha_zones
Revises: 019_flow_grades
Create Date: 2026-02-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "020_ha_zones"
down_revision: str | None = "019_flow_grades"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ha_zone",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("ha_url", sa.String(500), nullable=False),
        sa.Column("ha_url_remote", sa.String(500), nullable=True),
        sa.Column("ha_token_encrypted", sa.Text, nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
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
            nullable=False,
        ),
    )

    # Seed the default zone from existing system_config (if any)
    conn = op.get_bind()
    row = conn.execute(
        sa.text("SELECT id, ha_url, ha_token_encrypted FROM system_config LIMIT 1")
    ).fetchone()

    if row:
        from uuid import uuid4

        zone_id = str(uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO ha_zone (id, name, slug, ha_url, ha_token_encrypted, is_default, icon) "
                "VALUES (:id, :name, :slug, :ha_url, :token, true, :icon)"
            ),
            {
                "id": zone_id,
                "name": "Home",
                "slug": "home",
                "ha_url": row.ha_url,
                "token": row.ha_token_encrypted,
                "icon": "mdi:home",
            },
        )


def downgrade() -> None:
    op.drop_table("ha_zone")
