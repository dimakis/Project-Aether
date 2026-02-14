"""Add dashboard_config column to automation_proposal.

Feature: Dashboard Editor — Lovelace config changes go through HITL proposals.

Revision ID: 025_dashboard_proposals
Revises: 024_schedule_depth_strategy
Create Date: 2026-02-14
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "025_dashboard_proposals"
down_revision: str | None = "024_schedule_depth_strategy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add dashboard_config JSONB column to automation_proposal."""
    op.add_column(
        "automation_proposal",
        sa.Column(
            "dashboard_config",
            JSONB,
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove dashboard_config column from automation_proposal."""
    op.drop_column("automation_proposal", "dashboard_config")
