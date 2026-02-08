"""Add semver 'version' column to agent config and prompt version tables.

Supports semantic versioning (e.g. '1.2.0') alongside the existing
integer version_number. Nullable for backward compatibility with
existing rows.

Revision ID: 018_agent_version_semver
Revises: 017_model_ratings
Create Date: 2026-02-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "018_agent_version_semver"
down_revision: str | None = "017_model_ratings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_config_version",
        sa.Column("version", sa.String(20), nullable=True),
    )
    op.add_column(
        "agent_prompt_version",
        sa.Column("version", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_prompt_version", "version")
    op.drop_column("agent_config_version", "version")
