"""HA Automation, Script, and Scene models."""

from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, HAEntityMixin, TimestampMixin, UUIDMixin


class HAAutomation(Base, UUIDMixin, TimestampMixin, HAEntityMixin):
    """Home Assistant automation synced from HA.

    Represents automations defined in Home Assistant.
    """

    __tablename__ = "ha_automations"

    # HA identity
    ha_automation_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Home Assistant automation ID",
    )
    entity_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Entity ID (automation.xxx)",
    )

    # Metadata
    alias: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Automation display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Automation description",
    )

    # State
    state: Mapped[str] = mapped_column(
        String(50),
        default="on",
        doc="Current state (on, off)",
    )
    mode: Mapped[str] = mapped_column(
        String(50),
        default="single",
        doc="Execution mode (single, restart, queued, parallel)",
    )

    # Trigger info (summary)
    trigger_types: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Types of triggers used",
    )
    trigger_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Number of triggers",
    )

    # Action info (summary)
    action_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Number of actions",
    )
    condition_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Number of conditions",
    )

    # Full config (if available)
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Full automation config (null until MCP supports config fetch)",
    )

    # Last triggered
    last_triggered: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Last triggered timestamp from HA",
    )

    __table_args__ = (
        Index("ix_ha_automations_alias", "alias"),
        Index("ix_ha_automations_state", "state"),
    )

    def __repr__(self) -> str:
        return f"<HAAutomation(id={self.id}, alias={self.alias}, state={self.state})>"


class Script(Base, UUIDMixin, TimestampMixin, HAEntityMixin):
    """Home Assistant script from script domain.

    Note: sequence is nullable as MCP doesn't support script config fetch.
    """

    __tablename__ = "scripts"

    # HA identity
    entity_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Entity ID (script.xxx)",
    )

    # Metadata
    alias: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Script display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Script description",
    )

    # State
    state: Mapped[str] = mapped_column(
        String(50),
        default="off",
        doc="Current state (on=running, off=idle)",
    )
    mode: Mapped[str] = mapped_column(
        String(50),
        default="single",
        doc="Execution mode",
    )

    # Icon
    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="MDI icon",
    )

    # Config (HA gap)
    sequence: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Script sequence (null until MCP supports script config)",
    )
    fields: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Script input fields",
    )

    # Last triggered
    last_triggered: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Last triggered timestamp",
    )

    __table_args__ = (Index("ix_scripts_alias", "alias"),)

    def __repr__(self) -> str:
        return f"<Script(id={self.id}, alias={self.alias}, state={self.state})>"


class Scene(Base, UUIDMixin, TimestampMixin, HAEntityMixin):
    """Home Assistant scene from scene domain.

    Note: entity_states is nullable as MCP doesn't support scene config fetch.
    """

    __tablename__ = "scenes"

    # HA identity
    entity_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Entity ID (scene.xxx)",
    )

    # Metadata
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Scene display name",
    )

    # Icon
    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="MDI icon",
    )

    # Config (HA gap)
    entity_states: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Entity states in scene (null until MCP supports scene config)",
    )

    __table_args__ = (Index("ix_scenes_name", "name"),)

    def __repr__(self) -> str:
        return f"<Scene(id={self.id}, name={self.name})>"


class Service(Base, UUIDMixin, TimestampMixin):
    """Home Assistant service definition.

    Represents available services (light.turn_on, switch.toggle, etc.).
    Seeded with common services, expanded during discovery.
    """

    __tablename__ = "services"

    # Service identity
    domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Service domain",
    )
    service: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Service name",
    )

    # Metadata
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Human-readable name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Service description",
    )

    # Fields/parameters
    fields: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Service input fields schema",
    )
    target: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Target specification",
    )
    response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Response schema",
    )

    # Source
    is_seeded: Mapped[bool] = mapped_column(
        default=False,
        doc="Whether this is a seeded common service",
    )
    discovered_at: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Discovery session that found this",
    )

    __table_args__ = (
        Index("ix_services_domain_service", "domain", "service", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Service(domain={self.domain}, service={self.service})>"

    @property
    def full_service_name(self) -> str:
        """Get the full service name (domain.service)."""
        return f"{self.domain}.{self.service}"
