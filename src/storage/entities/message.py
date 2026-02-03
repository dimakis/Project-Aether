"""Message entity model.

Individual messages within a conversation - User Story 2.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.conversation import Conversation


class Message(Base, UUIDMixin, TimestampMixin):
    """Individual messages within a conversation.

    Tracks all messages between user and agent, including tool calls
    and responses. Used for conversation history and debugging.
    """

    __tablename__ = "message"

    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK to parent conversation",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Message author: user, assistant, system",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Message content (may include structured data)",
    )
    tool_calls: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Tool/function calls made by assistant",
    )
    tool_results: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Results from tool calls",
    )
    tokens_used: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Token count for cost tracking",
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Response time in milliseconds",
    )
    mlflow_span_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="MLflow trace span ID for observability",
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        doc="Additional message metadata",
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        content_preview = self.content[:50] if self.content else ""
        return f"<Message(role={self.role!r}, content={content_preview!r}...)>"
