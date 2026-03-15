"""Convert app_settings.id from VARCHAR(36) to native UUID.

Migration 026 created the column as String(36), but the ORM UUIDMixin
declares it as UUID(as_uuid=False).  The type mismatch causes asyncpg
to emit ``WHERE app_settings.id = $1::UUID`` which Postgres rejects
with "operator does not exist: character varying = uuid".

Revision ID: 039_app_settings_id_to_uuid
Revises: 038_fix_proposalstatus_enum_case
Create Date: 2026-03-14
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "039_app_settings_id_to_uuid"
down_revision: str | None = "038_fix_proposalstatus_enum_case"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "app_settings",
        "id",
        type_=postgresql.UUID(as_uuid=False),
        existing_type=sa.String(36),
        postgresql_using="id::uuid",
    )


def downgrade() -> None:
    op.alter_column(
        "app_settings",
        "id",
        type_=sa.String(36),
        existing_type=postgresql.UUID(as_uuid=False),
        postgresql_using="id::text",
    )
