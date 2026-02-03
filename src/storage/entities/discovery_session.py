"""DiscoverySession model for tracking entity discovery runs."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class DiscoveryStatus(StrEnum):
    """Status of a discovery session."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DiscoverySession(Base, UUIDMixin, TimestampMixin):
    """Tracks entity discovery runs by the Librarian agent.

    Records what was discovered, added, removed, and any errors encountered.
    """

    __tablename__ = "discovery_sessions"

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When discovery started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When discovery completed",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=DiscoveryStatus.RUNNING,
        nullable=False,
        doc="Session status",
    )

    # Entity counts
    entities_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Total entities discovered",
    )
    entities_added: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="New entities added",
    )
    entities_removed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Entities removed (no longer in HA)",
    )
    entities_updated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Entities with updated state/attributes",
    )

    # Device counts
    devices_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Total devices discovered/inferred",
    )
    devices_added: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="New devices added",
    )

    # Area counts
    areas_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Total areas discovered",
    )
    areas_added: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="New areas added",
    )

    # Other counts
    floors_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Floors discovered (0 until MCP supports floors)",
    )
    labels_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Labels discovered (0 until MCP supports labels)",
    )
    integrations_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Integrations discovered",
    )
    services_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Services discovered",
    )
    automations_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="HA automations discovered",
    )
    scripts_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Scripts discovered",
    )
    scenes_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Scenes discovered",
    )

    # Domain breakdown
    domain_counts: Mapped[dict[str, int] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Entity count per domain",
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if failed",
    )
    errors: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="List of non-fatal errors encountered",
    )

    # MCP gap tracking
    mcp_gaps_encountered: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="MCP capability gaps encountered during discovery",
    )

    # Observability
    mlflow_run_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="MLflow run ID for tracing",
    )

    # Trigger info
    triggered_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="What triggered this discovery (manual, scheduled, event)",
    )

    def __repr__(self) -> str:
        return f"<DiscoverySession(id={self.id}, status={self.status}, entities_found={self.entities_found})>"

    @property
    def duration_seconds(self) -> float | None:
        """Calculate discovery duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
