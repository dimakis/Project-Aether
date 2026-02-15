"""Add app_settings table for runtime-configurable settings.

Stores chat, dashboard, and data_science settings as JSONB columns.
Single-row table — the API upserts on PATCH.

Revision ID: 026_app_settings
Revises: 025_dashboard_proposals
Create Date: 2026-02-15
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026_app_settings"
down_revision: str | None = "025_dashboard_proposals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("chat", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("dashboard", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("data_science", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
