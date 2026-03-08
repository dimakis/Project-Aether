"""Insight model for Data Science team analysis results.

Stores energy optimization insights, anomaly detections,
and other analytical outputs from the Data Science team.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any, TypeVar

from sqlalchemy import JSON, DateTime, Enum, Float, String, Text, TypeDecorator, Uuid, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base

_E = TypeVar("_E", bound=enum.Enum)


def _enum_column(enum_cls: type[_E]) -> TypeDecorator[_E]:
    """Enum column that persists by value and loads by value or name (legacy).

    Uses String as the impl so SQLAlchemy's internal Enum validation
    is bypassed; the DB-level enum constraint is maintained by the
    PostgreSQL column type created in migrations.
    """

    class _EnumByNameOrValue(TypeDecorator[_E]):
        impl = String(255)
        cache_ok = True

        def process_bind_param(self, value: Any, dialect: Any) -> str | None:
            if value is None:
                return None
            if isinstance(value, enum_cls):
                return str(value.value)
            return str(value)

        def process_result_value(self, value: Any, dialect: Any) -> _E | None:
            if value is None:
                return None
            if isinstance(value, enum_cls):
                return value
            s = str(value).strip()
            for member in enum_cls:
                if s in (member.value, member.name):
                    return member
            raise LookupError(
                f"{value!r} is not among the defined enum values. "
                f"Enum: {enum_cls.__name__}. "
                f"Possible: {[e.value for e in enum_cls]}"
            )

    return _EnumByNameOrValue()


class InsightType(str, enum.Enum):
    """Types of insights the Data Science team can generate."""

    ENERGY_OPTIMIZATION = "energy_optimization"
    ANOMALY_DETECTION = "anomaly"
    USAGE_PATTERN = "pattern"
    COST_SAVING = "recommendation"
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


class InsightImpact(str, enum.Enum):
    """Impact level of an insight."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InsightStatus(str, enum.Enum):
    """Status of an insight through its lifecycle."""

    PENDING = "generated"  # Just generated, awaiting review
    REVIEWED = "reviewed"  # User has seen it
    ACTIONED = "acted_upon"  # User took action based on it
    DISMISSED = "dismissed"  # User dismissed it


class Insight(Base):
    """Analysis insight from the Data Science team.

    Represents an analytical finding such as energy optimization
    opportunities, anomaly detections, or usage patterns.
    """

    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)

    # Insight classification: persist by value; load by value or name (legacy rows)
    type: Mapped[InsightType] = mapped_column(
        _enum_column(InsightType),
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
    impact: Mapped[InsightImpact] = mapped_column(
        Enum(
            InsightImpact,
            name="insightimpact",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        doc="Impact level: low, medium, high, critical",
    )

    # Related entities
    entities: Mapped[list[str]] = mapped_column(
        ARRAY(Uuid(as_uuid=False)),
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

    # Status tracking: persist by value; load by value or name (legacy rows)
    status: Mapped[InsightStatus] = mapped_column(
        _enum_column(InsightStatus),
        nullable=False,
        default=InsightStatus.PENDING,
        index=True,
    )

    # Conversation context (for task tagging)
    conversation_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        doc="Originating conversation ID",
    )
    task_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Human-readable label for the task that produced this insight",
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
        self.reviewed_at = datetime.now(UTC)

    def mark_actioned(self) -> None:
        """Mark insight as actioned."""
        self.status = InsightStatus.ACTIONED
        self.actioned_at = datetime.now(UTC)

    def dismiss(self) -> None:
        """Dismiss the insight."""
        self.status = InsightStatus.DISMISSED
