"""LLM usage entity model.

Tracks individual LLM API calls for usage auditing and cost estimation.
Each row represents one LLM invocation with token counts and cost.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.conversation import Conversation


class LLMUsage(Base, UUIDMixin, TimestampMixin):
    """Tracks individual LLM API calls for usage and cost auditing."""

    __tablename__ = "llm_usage"
    __table_args__ = (
        Index("ix_llm_usage_created_at", "created_at"),
        Index("ix_llm_usage_model", "model"),
        Index("ix_llm_usage_conversation_id", "conversation_id"),
    )

    # Provider and model info
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="LLM provider (e.g. openrouter, openai, google)",
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Model name (e.g. gpt-4o, anthropic/claude-sonnet-4)",
    )

    # Token counts
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of input/prompt tokens",
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of output/completion tokens",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total tokens (input + output)",
    )

    # Cost
    cost_usd: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Estimated cost in USD (null if pricing unknown)",
    )

    # Performance
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Response time in milliseconds",
    )

    # Context
    conversation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversation.id", ondelete="SET NULL"),
        nullable=True,
        doc="FK to conversation (nullable for non-conversational calls)",
    )
    agent_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Agent role (e.g. architect, data_scientist)",
    )
    request_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="chat",
        doc="Type of request (chat, insight, scheduled, tool)",
    )

    # Relationships
    conversation: Mapped["Conversation | None"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<LLMUsage(model={self.model!r}, "
            f"tokens={self.total_tokens}, "
            f"cost=${self.cost_usd or 0:.4f})>"
        )
