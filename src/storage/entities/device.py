"""Device model for Home Assistant device registry."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, HAEntityMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.area import Area
    from src.storage.entities.ha_entity import HAEntity


class Device(Base, UUIDMixin, TimestampMixin, HAEntityMixin):
    """Home Assistant device from device registry.

    Devices represent physical or logical hardware (hubs, sensors, etc.).
    Note: Some fields are nullable as MCP doesn't yet support full device info.
    """

    __tablename__ = "devices"

    # HA identity
    ha_device_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Home Assistant device ID",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Device display name",
    )
    name_by_user: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="User-defined device name",
    )

    # Area relationship
    area_id: Mapped[str | None] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL"),
        nullable=True,
        doc="Area this device belongs to",
    )
    area: Mapped["Area | None"] = relationship(
        "Area",
        back_populates="devices",
    )

    # Manufacturer info (nullable - HA gap)
    manufacturer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Device manufacturer (null until MCP supports devices)",
    )
    model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Device model (null until MCP supports devices)",
    )
    sw_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Software/firmware version",
    )
    hw_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Hardware version",
    )

    # Integration info
    config_entry_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Config entry that created this device",
    )
    via_device_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Parent device ID (for nested devices)",
    )

    # Identifiers (stored as JSON array of [domain, id] tuples)
    identifiers: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Device identifiers [[domain, id], ...]",
    )
    connections: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Device connections [[type, id], ...]",
    )

    # Status
    disabled: Mapped[bool] = mapped_column(
        default=False,
        doc="Whether device is disabled",
    )
    disabled_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="What disabled the device (user, integration, config_entry)",
    )

    # Entities
    entities: Mapped[list["HAEntity"]] = relationship(
        "HAEntity",
        back_populates="device",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_devices_name", "name"),
        Index("ix_devices_manufacturer", "manufacturer"),
    )

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name={self.name}, ha_device_id={self.ha_device_id})>"
