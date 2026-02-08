"""Home Assistant Zone entity model.

Represents a connection to a Home Assistant instance (a "zone").
Each zone stores one or two access URLs (local + remote) and an
encrypted long-lived access token.  One zone is marked as the default.
"""

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class HAZone(Base, UUIDMixin, TimestampMixin):
    """A Home Assistant server connection ("zone").

    Examples:
        - "Home" at localhost:8123 (local) + myha.duckdns.org (remote)
        - "Beach House" at 192.168.1.50:8123 (local only)
    """

    __tablename__ = "ha_zone"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Human-readable zone name (e.g. 'Home', 'Beach House')",
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        doc="URL-safe unique identifier",
    )
    ha_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Primary/local Home Assistant URL",
    )
    ha_url_remote: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Public/remote Home Assistant URL (Nabu Casa, DuckDNS, etc.)",
    )
    ha_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="HA long-lived access token, Fernet-encrypted",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether this is the default zone",
    )
    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Zone center latitude (optional)",
    )
    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Zone center longitude (optional)",
    )
    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="MDI icon name (e.g. 'mdi:home', 'mdi:beach')",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<HAZone(name={self.name!r}, slug={self.slug!r}, "
            f"ha_url={self.ha_url!r}, is_default={self.is_default})>"
        )
