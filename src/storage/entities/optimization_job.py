"""Optimization job entity model.

Feature 38: Optimization Persistence.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OptimizationJob(Base, UUIDMixin, TimestampMixin):
    """Persistent optimization job record."""

    __tablename__ = "optimization_job"

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=JobStatus.PENDING.value, index=True
    )
    analysis_types: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    hours_analyzed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    insight_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suggestion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommendations: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    suggestions = relationship("AutomationSuggestionEntity", back_populates="job", lazy="selectin")
