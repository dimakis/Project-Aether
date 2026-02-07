"""Add proposal_type and service_call columns to automation_proposal.

Supports entity commands, scripts, and scenes as proposal types
in addition to the existing automation type.

Revision ID: 009_proposal_types
Revises: 008_insight_schedules
Create Date: 2026-02-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "009_proposal_types"
down_revision: str | None = "008_insight_schedules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add proposal_type and service_call columns."""
    op.add_column(
        "automation_proposal",
        sa.Column(
            "proposal_type",
            sa.String(20),
            nullable=False,
            server_default="automation",
        ),
    )
    op.add_column(
        "automation_proposal",
        sa.Column("service_call", JSONB(), nullable=True),
    )
    # Index for filtering by type
    op.create_index(
        "ix_proposals_type",
        "automation_proposal",
        ["proposal_type"],
    )


def downgrade() -> None:
    """Remove proposal_type and service_call columns."""
    op.drop_index("ix_proposals_type", table_name="automation_proposal")
    op.drop_column("automation_proposal", "service_call")
    op.drop_column("automation_proposal", "proposal_type")
