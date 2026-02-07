"""Insight model for Data Scientist analysis results.

Stores energy optimization insights, anomaly detections,
and other analytical outputs from the Data Scientist agent.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class InsightType(str, enum.Enum):
    """Types of insights the Data Scientist can generate."""

    ENERGY_OPTIMIZATION = "energy_optimization"
    ANOMALY_DETECTION = "anomaly_detection"
    USAGE_PATTERN = "usage_pattern"
    COST_SAVING = "cost_saving"
    MAINTENANCE_PREDICTION = "maintenance_prediction"
    # Feature 03: Intelligent Optimization
    AUTOMATION_GAP = "automation_gap"
    AUTOMATION_INEFFICIENCY = "automation_inefficiency"
    CORRELATION = "correlation"
    DEVICE_HEALTH = "device_health"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    # Conversational Insights: additional preset types
    COMFORT_ANALYSIS = "comfort_analysis"
    SECURITY_AUDIT = "security_audit"
    WEATHER_CORRELATION = "weather_correlation"
    AUTOMATION_EFFICIENCY = "automation_efficiency"
    CUSTOM = "custom"


class InsightStatus(str, enum.Enum):
    """Status of an insight through its lifecycle."""

    PENDING = "pending"  # Just generated, awaiting review
    REVIEWED = "reviewed"  # User has seen it
    ACTIONED = "actioned"  # User took action based on it
    DISMISSED = "dismissed"  # User dismissed it


class Insight(Base):
    """Analysis insight from the Data Scientist agent.

    Represents an analytical finding such as energy optimization
    opportunities, anomaly detections, or usage patterns.
    """

    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Insight classification
    type: Mapped[InsightType] = mapped_column(
        Enum(InsightType),
        nullable=False,
        index=True,
    )

    # Human-readable content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Analysis data
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Supporting data for the insight",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Confidence score 0.0-1.0",
    )
    impact: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Impact level: low, medium, high, critical",
    )

    # Related entities
    entities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Entity IDs related to this insight",
    )

    # Script execution (if applicable)
    script_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Path to the analysis script",
    )
    script_output: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Output from script execution",
    )

    # Status tracking
    status: Mapped[InsightStatus] = mapped_column(
        Enum(InsightStatus),
        nullable=False,
        default=InsightStatus.PENDING,
        index=True,
    )

    # MLflow tracing (Constitution: Observability)
    mlflow_run_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        doc="MLflow run ID for traceability",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Insight {self.id[:8]} type={self.type.value} status={self.status.value}>"

    def mark_reviewed(self) -> None:
        """Mark insight as reviewed."""
        self.status = InsightStatus.REVIEWED
        self.reviewed_at = datetime.now(timezone.utc)

    def mark_actioned(self) -> None:
        """Mark insight as actioned."""
        self.status = InsightStatus.ACTIONED
        self.actioned_at = datetime.now(timezone.utc)

    def dismiss(self) -> None:
        """Dismiss the insight."""
        self.status = InsightStatus.DISMISSED
