"""Add 'disabled' and 'deprecated' to proposalstatus enum.

Extends the proposal lifecycle with two new states:
- disabled: temporarily inactive in HA (can be re-enabled)
- deprecated: marked for eventual removal (terminal except archived)

Revision ID: 037_proposal_lifecycle_states
Revises: 036_insightimpact_critical
Create Date: 2026-03-09
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "037_proposal_lifecycle_states"
down_revision: str | None = "036_insightimpact_critical"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE proposalstatus ADD VALUE IF NOT EXISTS 'disabled'")
    op.execute("ALTER TYPE proposalstatus ADD VALUE IF NOT EXISTS 'deprecated'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; no-op.
    pass
