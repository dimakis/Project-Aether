"""Add previous_dashboard_config column for dashboard rollback.

Stores the snapshot of the existing Lovelace config taken before
deployment so that dashboard proposals can be rolled back.

Revision ID: 027_previous_dashboard_config
Revises: 026_app_settings
Create Date: 2026-02-15
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "027_previous_dashboard_config"
down_revision: str | None = "026_app_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "automation_proposal",
        sa.Column("previous_dashboard_config", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("automation_proposal", "previous_dashboard_config")
