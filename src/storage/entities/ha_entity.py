"""HA Entity model for Home Assistant entity registry."""

from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, HAEntityMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.area import Area
    from src.storage.entities.device import Device


class HAEntity(Base, UUIDMixin, TimestampMixin, HAEntityMixin):
    """Home Assistant entity from entity registry.

    This is the core entity model representing all HA entities
    (lights, sensors, switches, etc.).
    """

    __tablename__ = "ha_entities"

    # HA identity
    entity_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Home Assistant entity ID (e.g., light.living_room)",
    )
    domain: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Entity domain (light, sensor, switch, etc.)",
    )
    platform: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Integration platform that provides this entity",
    )

    # Names
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Entity display name",
    )
    original_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Original name from the device/integration",
    )

    # Current state
    state: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Current state value",
    )
    attributes: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="Entity attributes as JSON",
    )

    # Device relationship
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        doc="Device this entity belongs to",
    )
    device: Mapped["Device | None"] = relationship(
        "Device",
        back_populates="entities",
    )

    # Area relationship (can be set directly or inherited from device)
    area_id: Mapped[str | None] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL"),
        nullable=True,
        doc="Area this entity belongs to",
    )
    area: Mapped["Area | None"] = relationship(
        "Area",
        back_populates="entities",
    )

    # Entity capabilities
    device_class: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Device class (e.g., temperature, motion)",
    )
    unit_of_measurement: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Unit of measurement for sensors",
    )
    supported_features: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Bitmask of supported features",
    )
    state_class: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="State class (measurement, total, total_increasing)",
    )

    # Entity options
    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="MDI icon name",
    )
    entity_category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Entity category (config, diagnostic)",
    )

    # Status
    disabled: Mapped[bool] = mapped_column(
        default=False,
        doc="Whether entity is disabled",
    )
    disabled_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="What disabled the entity",
    )
    hidden: Mapped[bool] = mapped_column(
        default=False,
        doc="Whether entity is hidden from UI",
    )
    hidden_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="What hid the entity",
    )

    # Labels (HA gap - stored as JSON array for future use)
    labels: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Entity labels (null until MCP supports labels)",
    )

    # Config entry
    config_entry_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Config entry ID",
    )

    # Unique ID for the integration
    unique_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Unique ID within the platform",
    )

    __table_args__ = (
        # domain index is already created by index=True on the column
        Index("ix_ha_entities_device_class", "device_class"),
        Index("ix_ha_entities_state", "state"),
        Index("ix_ha_entities_domain_state", "domain", "state"),
    )

    def __repr__(self) -> str:
        return f"<HAEntity(id={self.id}, entity_id={self.entity_id}, state={self.state})>"

    @property
    def friendly_name(self) -> str:
        """Get friendly name from attributes or fall back to name."""
        if self.attributes and "friendly_name" in self.attributes:
            return cast("str", self.attributes["friendly_name"])
        return self.name
