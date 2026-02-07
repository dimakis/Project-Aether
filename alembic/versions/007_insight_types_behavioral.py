"""Extend InsightType enum with behavioral analysis types (Feature 03).

Adds new InsightType values for the Intelligent Optimization feature:
- automation_gap: Manual pattern that could be automated
- automation_inefficiency: Existing automation that could be improved
- correlation: Entity relationship discovery
- device_health: Device anomaly or health issue
- behavioral_pattern: User behavior pattern

Revision ID: 007_insight_types_behavioral
Revises: 006_composite_indexes
Create Date: 2026-02-07
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_insight_types_behavioral"
down_revision: str | None = "006_composite_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# New InsightType enum values to add
NEW_INSIGHT_TYPES = [
    "automation_gap",
    "automation_inefficiency",
    "correlation",
    "device_health",
    "behavioral_pattern",
]


def upgrade() -> None:
    """Add new InsightType enum values."""
    # PostgreSQL ALTER TYPE ... ADD VALUE cannot run inside a transaction
    # Each ADD VALUE must be committed separately
    for value in NEW_INSIGHT_TYPES:
        op.execute(f"ALTER TYPE insighttype ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Remove new InsightType enum values.

    Note: PostgreSQL does not support removing enum values directly.
    A full enum recreation would be needed, which is risky for production.
    This downgrade is intentionally a no-op.
    """
    pass
