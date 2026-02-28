"""Automation suggestion entity model.

Feature 38: Optimization Persistence.
"""

from enum import Enum

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AutomationSuggestionEntity(Base, UUIDMixin, TimestampMixin):
    """Persistent automation suggestion linked to an optimization job."""

    __tablename__ = "automation_suggestion"

    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("optimization_job.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    entities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    proposed_trigger: Mapped[str | None] = mapped_column(String(500), nullable=True)
    proposed_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_insight_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SuggestionStatus.PENDING.value
    )

    job = relationship("OptimizationJob", back_populates="suggestions")
