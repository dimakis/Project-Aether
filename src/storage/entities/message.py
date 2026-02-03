"""Message entity model.

Placeholder for User Story 2 - will be fully implemented then.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.conversation import Conversation


class Message(Base, UUIDMixin, TimestampMixin):
    """Message entity - placeholder for US2.

    Individual messages within a conversation.
    Full implementation in User Story 2.
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
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        doc="Additional message metadata",
    )
    tool_calls: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Tool calls made in this message",
    )
    tool_results: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Results from tool calls",
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Message(role={self.role!r}, content={self.content[:50]!r}...)>"
