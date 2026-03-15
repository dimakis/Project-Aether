"""Align database column types with ORM entity definitions.

Fixes schema drift accumulated across early migrations where column
types diverged from the ORM:

Part A — Convert VARCHAR(36) primary keys to native UUID:
  - insights.id
  - workflow_definition.id
  - tool_group.id

Part B — Fix insights column types:
  - impact:        varchar(50)  -> insightimpact enum
  - evidence:      json         -> jsonb
  - entities:      json         -> jsonb (HA entity ID strings, not UUIDs)
  - script_output: json         -> jsonb

Part C — Fix conversation.status:
  - varchar(20) -> conversationstatus enum

Revision ID: 041_schema_alignment
Revises: 040_normalize_insightstatus_data
Create Date: 2026-03-15
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "041_schema_alignment"
down_revision: str | None = "040_normalize_insightstatus_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Part A: VARCHAR(36) PKs → UUID ────────────────────────────────
    for table in ("insights", "workflow_definition", "tool_group"):
        op.alter_column(
            table,
            "id",
            type_=postgresql.UUID(as_uuid=False),
            existing_type=sa.String(36),
            postgresql_using="id::uuid",
        )

    # ── Part B: insights column types ─────────────────────────────────
    # impact: varchar(50) → insightimpact enum
    op.execute(
        "ALTER TABLE insights ALTER COLUMN impact TYPE insightimpact USING impact::insightimpact"
    )

    # evidence: json → jsonb
    op.alter_column(
        "insights",
        "evidence",
        type_=postgresql.JSONB(),
        existing_type=sa.JSON(),
        postgresql_using="evidence::jsonb",
    )

    # entities: json → jsonb (stores HA entity ID strings, not UUIDs)
    op.alter_column(
        "insights",
        "entities",
        type_=postgresql.JSONB(),
        existing_type=sa.JSON(),
        postgresql_using="entities::jsonb",
        server_default=sa.text("'[]'::jsonb"),
    )

    # script_output: json → jsonb
    op.alter_column(
        "insights",
        "script_output",
        type_=postgresql.JSONB(),
        existing_type=sa.JSON(),
        postgresql_using="script_output::jsonb",
    )

    # ── Part C: conversation.status → conversationstatus enum ─────────
    op.execute(
        "ALTER TABLE conversation "
        "ALTER COLUMN status TYPE conversationstatus "
        "USING status::conversationstatus"
    )


def downgrade() -> None:
    # ── Part C reverse ────────────────────────────────────────────────
    op.execute("ALTER TABLE conversation ALTER COLUMN status TYPE varchar(20) USING status::text")

    # ── Part B reverse ────────────────────────────────────────────────
    op.alter_column(
        "insights",
        "script_output",
        type_=sa.JSON(),
        existing_type=postgresql.JSONB(),
    )

    op.alter_column(
        "insights",
        "entities",
        type_=sa.JSON(),
        existing_type=postgresql.JSONB(),
        server_default=None,
    )

    op.alter_column(
        "insights",
        "evidence",
        type_=sa.JSON(),
        existing_type=postgresql.JSONB(),
    )

    op.execute("ALTER TABLE insights ALTER COLUMN impact TYPE varchar(50) USING impact::text")

    # ── Part A reverse ────────────────────────────────────────────────
    for table in ("insights", "workflow_definition", "tool_group"):
        op.alter_column(
            table,
            "id",
            type_=sa.String(36),
            existing_type=postgresql.UUID(as_uuid=False),
            postgresql_using="id::text",
        )
