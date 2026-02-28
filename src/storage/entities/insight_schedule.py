"""InsightSchedule model for scheduled and event-driven analysis jobs.

Feature 10: Scheduled & Event-Driven Insights.
Stores configuration for recurring cron jobs and HA webhook-triggered analysis.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base


class TriggerType(str, enum.Enum):
    """How the insight schedule is triggered."""

    CRON = "cron"  # Periodic via APScheduler cron expression
    WEBHOOK = "webhook"  # On-demand via HA webhook event
    EVENT = "event"  # Triggered by real-time HA event stream (Feature 35)


class InsightSchedule(Base):
    """Scheduled or event-driven insight analysis job.

    Represents a configured analysis that runs either:
    - Periodically via cron expression (APScheduler)
    - On-demand when a Home Assistant event fires a webhook
    """

    __tablename__ = "insight_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Human-readable label
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # What analysis to run
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Analysis type: energy, behavioral, anomaly, device_health, etc.",
    )
    entity_ids: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Scope to specific HA entity IDs (null = all relevant entities)",
    )
    hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24,
        doc="Lookback window in hours for the analysis",
    )
    options: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Extra analysis parameters passed to the Data Science team",
    )

    # Trigger configuration
    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="'cron' or 'webhook'",
    )
    cron_expression: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Cron expression, e.g. '0 2 * * *' (cron triggers only)",
    )
    webhook_event: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Event label for matching, e.g. 'device_offline' (webhook triggers only)",
    )
    webhook_filter: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Match criteria, e.g. {'entity_id': 'sensor.power*', 'to_state': 'unavailable'}",
    )

    # Execution tracking
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_result: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="'success', 'failed', 'timeout'",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    run_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Analysis depth/strategy configuration (Feature 33: DS Deep Analysis)
    depth: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="standard",
        server_default="standard",
        doc="Analysis depth: quick, standard, deep",
    )
    strategy: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="parallel",
        server_default="parallel",
        doc="Execution strategy: parallel, teamwork",
    )
    timeout_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        doc="Optional timeout override in seconds (null = use depth default)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<InsightSchedule {self.id[:8]} "
            f"name={self.name!r} trigger={self.trigger_type} "
            f"enabled={self.enabled}>"
        )

    def record_run(self, success: bool, error: str | None = None) -> None:
        """Record the result of a job execution."""
        self.last_run_at = datetime.now(UTC)
        self.last_result = "success" if success else "failed"
        self.last_error = error
        self.run_count += 1
