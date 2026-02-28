"""Add tool_groups_enabled column to agent_config_version.

Feature 34: Dynamic Tool Registry.
Allows agent configs to reference tool groups in addition to
individual tool names.

Revision ID: 032_agent_config_tool_groups
Revises: 031_tool_groups
Create Date: 2026-02-28
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "032_agent_config_tool_groups"
down_revision: str | None = "031_tool_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_config_version",
        sa.Column("tool_groups_enabled", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_config_version", "tool_groups_enabled")
