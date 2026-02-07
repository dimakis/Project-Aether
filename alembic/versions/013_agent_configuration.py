"""Add agent configuration versioning tables and agent status.

Feature 23: Agent Configuration Page.
Creates agent_config_version and agent_prompt_version tables for versioned
per-agent LLM settings and prompt templates. Extends the agent table with
status lifecycle and active version FK pointers.

Revision ID: 013_agent_configuration
Revises: 012_system_config
Create Date: 2026-02-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "013_agent_configuration"
down_revision: str | None = "012_system_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create version tables and extend agent table."""
    # --- agent_config_version ---
    op.create_table(
        "agent_config_version",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "agent_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agent.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("fallback_model", sa.String(100), nullable=True),
        sa.Column("tools_enabled", JSONB(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_agent_config_version_agent_id",
        "agent_config_version",
        ["agent_id"],
    )
    op.create_index(
        "ix_agent_config_version_status",
        "agent_config_version",
        ["status"],
    )

    # --- agent_prompt_version ---
    op.create_table(
        "agent_prompt_version",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "agent_id",
            UUID(as_uuid=False),
            sa.ForeignKey("agent.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_agent_prompt_version_agent_id",
        "agent_prompt_version",
        ["agent_id"],
    )
    op.create_index(
        "ix_agent_prompt_version_status",
        "agent_prompt_version",
        ["status"],
    )

    # --- Extend agent table ---
    op.add_column(
        "agent",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="enabled",
        ),
    )
    op.create_index("ix_agent_status", "agent", ["status"])

    op.add_column(
        "agent",
        sa.Column(
            "active_config_version_id",
            UUID(as_uuid=False),
            sa.ForeignKey(
                "agent_config_version.id",
                ondelete="SET NULL",
                use_alter=True,
                name="fk_agent_active_config_version_id",
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "agent",
        sa.Column(
            "active_prompt_version_id",
            UUID(as_uuid=False),
            sa.ForeignKey(
                "agent_prompt_version.id",
                ondelete="SET NULL",
                use_alter=True,
                name="fk_agent_active_prompt_version_id",
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop version tables and remove agent extensions."""
    # Remove agent columns first (FK dependency)
    op.drop_column("agent", "active_prompt_version_id")
    op.drop_column("agent", "active_config_version_id")
    op.drop_index("ix_agent_status", table_name="agent")
    op.drop_column("agent", "status")

    # Drop version tables
    op.drop_index("ix_agent_prompt_version_status", table_name="agent_prompt_version")
    op.drop_index("ix_agent_prompt_version_agent_id", table_name="agent_prompt_version")
    op.drop_table("agent_prompt_version")

    op.drop_index("ix_agent_config_version_status", table_name="agent_config_version")
    op.drop_index("ix_agent_config_version_agent_id", table_name="agent_config_version")
    op.drop_table("agent_config_version")
