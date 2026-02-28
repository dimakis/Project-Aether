"""System configuration entity model.

Stores the single-row system configuration including:
- HA connection details (URL + encrypted token)
- Admin password hash (bcrypt)
- Setup completion timestamp

The HA token is encrypted at rest using Fernet (derived from JWT_SECRET).
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class SystemConfig(Base, UUIDMixin, TimestampMixin):
    """Single-row system configuration.

    Created during first-time setup when the user enters their HA URL and token.
    The HA token is stored encrypted (Fernet) for security at rest.
    """

    __tablename__ = "system_config"

    ha_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Validated Home Assistant instance URL",
    )
    ha_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="HA long-lived access token, Fernet-encrypted",
    )
    password_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="bcrypt hash of the admin fallback password (optional)",
    )
    setup_completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the initial setup was completed",
    )

    def __repr__(self) -> str:
        return (
            f"<SystemConfig(ha_url={self.ha_url!r}, "
            f"setup_completed_at={self.setup_completed_at!r})>"
        )
