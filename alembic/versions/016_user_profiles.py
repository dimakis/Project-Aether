"""Add user_profiles table.

Stores user identity data for login, display name, and optional
Google OAuth linkage.

Revision ID: 016_user_profiles
Revises: 015_llm_usage_fk_index
Create Date: 2026-02-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "016_user_profiles"
down_revision: str | None = "015_llm_usage_fk_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_profiles table."""
    op.create_table(
        "user_profiles",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("google_sub", sa.String(255), unique=True, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes
    op.create_index("ix_user_profiles_username", "user_profiles", ["username"], unique=True)
    op.create_index("ix_user_profiles_email", "user_profiles", ["email"], unique=True)
    op.create_index("ix_user_profiles_google_sub", "user_profiles", ["google_sub"], unique=True)


def downgrade() -> None:
    """Drop user_profiles table."""
    op.drop_index("ix_user_profiles_google_sub", table_name="user_profiles")
    op.drop_index("ix_user_profiles_email", table_name="user_profiles")
    op.drop_index("ix_user_profiles_username", table_name="user_profiles")
    op.drop_table("user_profiles")
