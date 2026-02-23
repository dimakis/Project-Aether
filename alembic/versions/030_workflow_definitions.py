"""Add workflow_definition table for dynamic workflow storage.

Feature 29: Dynamic Workflow Composition.
Stores declarative workflow configs (nodes, edges, routing) as JSONB
so they can be loaded and compiled at runtime.

Revision ID: 028_workflow_definitions
Revises: 026_agent_routing_fields
Create Date: 2026-02-23
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "030_workflow_definitions"
down_revision: str | None = "029_agent_routing_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_definition",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("state_type", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", index=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("intent_patterns", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("workflow_definition")
