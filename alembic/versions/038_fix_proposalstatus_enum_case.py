"""Fix proposalstatus enum casing: rename lowercase to UPPERCASE.

Migration 037 added 'disabled' and 'deprecated' as lowercase, but
SQLAlchemy emits the Python enum .name (UPPERCASE) in queries, matching
the convention of all other values (DRAFT, PROPOSED, etc.).

Revision ID: 038_fix_proposalstatus_enum_case
Revises: 037_proposal_lifecycle_states
Create Date: 2026-03-09
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "038_fix_proposalstatus_enum_case"
down_revision: str | None = "037_proposal_lifecycle_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE proposalstatus RENAME VALUE 'disabled' TO 'DISABLED'")
    op.execute("ALTER TYPE proposalstatus RENAME VALUE 'deprecated' TO 'DEPRECATED'")


def downgrade() -> None:
    op.execute("ALTER TYPE proposalstatus RENAME VALUE 'DISABLED' TO 'disabled'")
    op.execute("ALTER TYPE proposalstatus RENAME VALUE 'DEPRECATED' TO 'deprecated'")
