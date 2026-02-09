"""Area model for Home Assistant area registry."""

from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, HAEntityMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.device import Device
    from src.storage.entities.ha_entity import HAEntity


class Area(Base, UUIDMixin, TimestampMixin, HAEntityMixin):
    """Home Assistant area from area registry.

    Areas represent physical locations in the home (rooms, zones).
    Note: floor_id is nullable as MCP doesn't yet support floor registry.
    """

    __tablename__ = "areas"

    # HA identity
    ha_area_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Home Assistant area ID",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Area display name",
    )

    # Floor (nullable - HA gap)
    floor_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Floor ID (null until MCP supports floors)",
    )

    # Optional metadata
    icon: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="MDI icon name",
    )
    picture: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Area picture URL",
    )

    # Relationships
    entities: Mapped[list["HAEntity"]] = relationship(
        "HAEntity",
        back_populates="area",
        lazy="selectin",
    )
    devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="area",
        lazy="selectin",
    )

    __table_args__ = (Index("ix_areas_name", "name"),)

    def __repr__(self) -> str:
        return f"<Area(id={self.id}, name={self.name}, ha_area_id={self.ha_area_id})>"
