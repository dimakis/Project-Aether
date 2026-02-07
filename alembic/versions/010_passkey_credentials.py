"""Add passkey_credential table for WebAuthn authentication.

Stores public keys for Face ID / Touch ID passkey login.

Revision ID: 010_passkey_credentials
Revises: 009_proposal_types
Create Date: 2026-02-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "010_passkey_credentials"
down_revision: str | None = "009_proposal_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create passkey_credential table."""
    op.create_table(
        "passkey_credential",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transports", JSONB(), nullable=True),
        sa.Column("device_name", sa.String(100), nullable=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_passkey_credential_id",
        "passkey_credential",
        ["credential_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop passkey_credential table."""
    op.drop_index("ix_passkey_credential_id", table_name="passkey_credential")
    op.drop_table("passkey_credential")
