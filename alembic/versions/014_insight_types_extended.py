"""Extend InsightType enum with additional analysis types.

Adds new InsightType values for conversational insights feature:
- comfort_analysis: Temperature/humidity comfort scoring
- security_audit: Door/window/motion sensor coverage gaps
- weather_correlation: Energy usage vs weather patterns
- automation_efficiency: Existing automation trigger/run analysis
- custom: Free-form user-defined analysis

Revision ID: 014_insight_types_extended
Revises: 013_agent_configuration
Create Date: 2026-02-07
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014_insight_types_extended"
down_revision: str | None = "013_agent_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# New InsightType enum values to add
NEW_INSIGHT_TYPES = [
    "comfort_analysis",
    "security_audit",
    "weather_correlation",
    "automation_efficiency",
    "custom",
]


def upgrade() -> None:
    """Add new InsightType enum values."""
    # PostgreSQL ALTER TYPE ... ADD VALUE cannot run inside a transaction
    for value in NEW_INSIGHT_TYPES:
        op.execute(f"ALTER TYPE insighttype ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """Remove new InsightType enum values.

    Note: PostgreSQL does not support removing enum values directly.
    A full enum recreation would be needed, which is risky for production.
    This downgrade is intentionally a no-op.
    """
    pass
