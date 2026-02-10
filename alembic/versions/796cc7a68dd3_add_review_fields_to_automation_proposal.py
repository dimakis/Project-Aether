"""add review fields to automation_proposal

Revision ID: 796cc7a68dd3
Revises: 022_zone_url_preference
Create Date: 2026-02-10 11:33:03.231614

Feature 28: Smart Config Review — add fields for storing original YAML,
review annotations, batch session grouping, and split proposal tracking.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "796cc7a68dd3"
down_revision: str | None = "022_zone_url_preference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add review fields to automation_proposal table."""
    op.add_column(
        "automation_proposal",
        sa.Column("original_yaml", sa.Text(), nullable=True),
    )
    op.add_column(
        "automation_proposal",
        sa.Column(
            "review_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "automation_proposal",
        sa.Column("review_session_id", sa.UUID(as_uuid=False), nullable=True),
    )
    op.add_column(
        "automation_proposal",
        sa.Column("parent_proposal_id", sa.UUID(as_uuid=False), nullable=True),
    )
    op.create_index(
        "ix_automation_proposal_review_session_id",
        "automation_proposal",
        ["review_session_id"],
    )
    op.create_foreign_key(
        "fk_automation_proposal_parent_proposal_id",
        "automation_proposal",
        "automation_proposal",
        ["parent_proposal_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove review fields from automation_proposal table."""
    op.drop_constraint(
        "fk_automation_proposal_parent_proposal_id",
        "automation_proposal",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_automation_proposal_review_session_id",
        table_name="automation_proposal",
    )
    op.drop_column("automation_proposal", "parent_proposal_id")
    op.drop_column("automation_proposal", "review_session_id")
    op.drop_column("automation_proposal", "review_notes")
    op.drop_column("automation_proposal", "original_yaml")
