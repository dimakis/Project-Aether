"""Model rating entity for tracking per-agent model evaluations."""

from typing import Any

from sqlalchemy import CheckConstraint, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class ModelRating(Base, UUIDMixin, TimestampMixin):
    """User rating for a model used by a specific agent.

    Captures subjective quality assessment along with the model
    configuration snapshot at time of rating.
    """

    __tablename__ = "model_ratings"

    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Model identifier (e.g. gpt-4o, gemini-2.5-flash)",
    )
    agent_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Agent role this rating applies to (e.g. architect, data_scientist)",
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="1-5 star rating",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional notes about performance",
    )
    config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Model config at time of rating (temperature, context window, cost, etc.)",
    )

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_model_ratings_rating_range"),
        Index("ix_model_ratings_model_agent", "model_name", "agent_role"),
    )

    def __repr__(self) -> str:
        return f"<ModelRating(model={self.model_name}, agent={self.agent_role}, rating={self.rating})>"
