"""Add 'critical' to insightimpact enum.

Migration 005 defined insightimpact as (low, medium, high). The Python
InsightImpact enum includes CRITICAL = "critical" but no migration ever
added this value, causing ProgrammingError when querying with
InsightImpact.CRITICAL.

Revision ID: 036_insightimpact_critical
Revises: 035_insightstatus_enum_values
Create Date: 2026-03-09
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "036_insightimpact_critical"
down_revision: str | None = "035_insightstatus_enum_values"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE insightimpact ADD VALUE IF NOT EXISTS 'critical'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; no-op.
    pass
