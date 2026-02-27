"""Add previous_config column for automation/script/scene rollback.

Stores the snapshot of the existing HA config taken before deployment
so that any proposal type can be fully rolled back -- not just disabled.

Mirrors previous_dashboard_config (migration 027) but for all other
proposal types (automation, script, scene, entity_command, helper).

Revision ID: 031_previous_config
Revises: 030_workflow_definitions
Create Date: 2026-02-27
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "031_previous_config"
down_revision: str | None = "030_workflow_definitions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "automation_proposal",
        sa.Column("previous_config", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("automation_proposal", "previous_config")
