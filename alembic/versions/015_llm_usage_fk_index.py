"""Add FK constraint and index on llm_usage.conversation_id.

The column existed but had no FK constraint or index, causing:
- No referential integrity enforcement
- Slow queries when filtering by conversation_id

Revision ID: 015_llm_usage_fk_index
Revises: 014_insight_types_extended
Create Date: 2026-02-07
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015_llm_usage_fk_index"
down_revision: str | None = "014_insight_types_extended"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add FK constraint and index on llm_usage.conversation_id."""
    # Add index for query performance
    op.create_index(
        "ix_llm_usage_conversation_id",
        "llm_usage",
        ["conversation_id"],
    )

    # Add FK constraint for referential integrity
    op.create_foreign_key(
        "fk_llm_usage_conversation_id",
        "llm_usage",
        "conversation",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove FK constraint and index."""
    op.drop_constraint("fk_llm_usage_conversation_id", "llm_usage", type_="foreignkey")
    op.drop_index("ix_llm_usage_conversation_id", table_name="llm_usage")
