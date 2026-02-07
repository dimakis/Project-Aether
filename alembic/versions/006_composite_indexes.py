"""Add composite indexes for query performance (T191).

Adds composite indexes to supplement existing individual column indexes:
- Message(conversation_id, created_at) for get_last_n() pagination
- AutomationProposal(status, created_at) for status-filtered listing

Revision ID: 006_composite_indexes
Revises: 5fb8fe70b71f
Create Date: 2026-02-06
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_composite_indexes"
down_revision: str | None = "5fb8fe70b71f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite indexes for common query patterns."""
    op.create_index(
        "ix_messages_conversation_created",
        "message",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_proposals_status_created",
        "automation_proposal",
        ["status", "created_at"],
    )


def downgrade() -> None:
    """Remove composite indexes."""
    op.drop_index("ix_proposals_status_created", table_name="automation_proposal")
    op.drop_index("ix_messages_conversation_created", table_name="message")
