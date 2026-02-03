"""User Story 2 - Conversations and Automation Proposals.

Revision ID: 003_conversations_us2
Revises: 002_ha_registry
Create Date: 2026-02-03

Updates conversation and message tables with US2 fields.
Creates automation_proposal table for HITL workflow.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_conversations_us2"
down_revision: str | None = "002_ha_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply User Story 2 schema changes."""
    # Add new columns to message table
    op.add_column(
        "message",
        sa.Column("tokens_used", sa.Integer(), nullable=True),
    )
    op.add_column(
        "message",
        sa.Column("latency_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "message",
        sa.Column("mlflow_span_id", sa.String(100), nullable=True),
    )

    # Create automation_proposal table
    op.create_table(
        "automation_proposal",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False, server_default="single"),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PROPOSED",
                "APPROVED",
                "REJECTED",
                "DEPLOYED",
                "ROLLED_BACK",
                "ARCHIVED",
                name="proposalstatus",
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("ha_automation_id", sa.String(255), nullable=True),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("mlflow_run_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_automation_proposal")),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversation.id"],
            name=op.f("fk_automation_proposal_conversation_id_conversation"),
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "ha_automation_id",
            name=op.f("uq_automation_proposal_ha_automation_id"),
        ),
    )

    # Create indexes for automation_proposal
    op.create_index(
        op.f("ix_automation_proposal_conversation_id"),
        "automation_proposal",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_automation_proposal_status"),
        "automation_proposal",
        ["status"],
        unique=False,
    )

    # Add index on conversation status (if not exists)
    # Note: This might already exist from initial migration


def downgrade() -> None:
    """Revert User Story 2 schema changes."""
    # Drop automation_proposal indexes
    op.drop_index(
        op.f("ix_automation_proposal_status"),
        table_name="automation_proposal",
    )
    op.drop_index(
        op.f("ix_automation_proposal_conversation_id"),
        table_name="automation_proposal",
    )

    # Drop automation_proposal table
    op.drop_table("automation_proposal")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS proposalstatus")

    # Remove columns from message table
    op.drop_column("message", "mlflow_span_id")
    op.drop_column("message", "latency_ms")
    op.drop_column("message", "tokens_used")
