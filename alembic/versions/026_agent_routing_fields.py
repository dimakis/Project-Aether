"""Add routing fields to agent table for Orchestrator discovery.

Feature 30: Domain-Agnostic Orchestration.
Adds domain, is_routable, intent_patterns, and capabilities columns
so the OrchestratorAgent can discover and route to domain agents.

Revision ID: 026_agent_routing_fields
Revises: 025_dashboard_proposals
Create Date: 2026-02-15
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026_agent_routing_fields"
down_revision: str | None = "025_dashboard_proposals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent",
        sa.Column("domain", sa.String(50), nullable=True, index=True),
    )
    op.add_column(
        "agent",
        sa.Column(
            "is_routable",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            index=True,
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "intent_patterns",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "capabilities",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("agent", "capabilities")
    op.drop_column("agent", "intent_patterns")
    op.drop_column("agent", "is_routable")
    op.drop_column("agent", "domain")
