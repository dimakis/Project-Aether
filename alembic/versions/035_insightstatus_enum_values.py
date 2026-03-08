"""Add pending and actioned to insightstatus enum.

Migration 005 defined insightstatus as generated, reviewed, acted_upon, dismissed.
The application entity uses pending, reviewed, actioned, dismissed. Add the
missing values so INSERTs with pending/actioned succeed.

Revision ID: 035_insightstatus_enum_values
Revises: 034_app_settings_notifications
Create Date: 2026-02-28

"""

from __future__ import annotations

from typing import Sequence  # noqa: UP035 — match 034 migration style

from alembic import op

revision: str = "035_insightstatus_enum_values"
down_revision: str | None = "034_app_settings_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL: add new enum values (IF NOT EXISTS not available in older PG)
    op.execute("ALTER TYPE insightstatus ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE insightstatus ADD VALUE IF NOT EXISTS 'actioned'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; no-op.
    pass
