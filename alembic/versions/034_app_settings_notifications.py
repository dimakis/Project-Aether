"""Add notifications column to app_settings.

Feature 37: Proactive insight notifications.
The entity and DAL already expect this column; migration was missing.

Revision ID: 034_app_settings_notifications
Revises: 033_optimization_tables
Create Date: 2026-02-28

"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "034_app_settings_notifications"
down_revision: str | None = "033_optimization_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column(
            "notifications",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "notifications")
