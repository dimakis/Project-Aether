"""Passkey credential entity model.

Stores WebAuthn credential public keys for passkey (Face ID / Touch ID)
authentication. Each row represents one registered authenticator device.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class PasskeyCredential(Base, UUIDMixin, TimestampMixin):
    """Stored WebAuthn credential for passkey authentication.

    Each credential represents a registered device (phone, laptop, etc.)
    that can authenticate via biometrics (Face ID, Touch ID, Windows Hello).
    """

    __tablename__ = "passkey_credential"
    __table_args__ = (
        Index("ix_passkey_credential_id", "credential_id", unique=True),
    )

    # WebAuthn credential data
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        unique=True,
        doc="WebAuthn credential ID (unique per authenticator)",
    )
    public_key: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        doc="COSE public key bytes for signature verification",
    )
    sign_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Signature counter for replay protection",
    )
    transports: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        doc='Authenticator transports (e.g. ["internal", "hybrid"])',
    )

    # User-friendly metadata
    device_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="User-friendly device label (e.g. 'iPhone 15')",
    )
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Username this credential belongs to",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When this credential was last used to authenticate",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<PasskeyCredential(device={self.device_name!r}, "
            f"username={self.username!r})>"
        )
