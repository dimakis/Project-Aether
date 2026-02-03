"""Conversation entity model.

Placeholder for User Story 2 - will be fully implemented then.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.agent import Agent
    from src.storage.entities.message import Message


class Conversation(Base, UUIDMixin, TimestampMixin):
    """Conversation entity - placeholder for US2.

    A dialogue session between user and an agent (primarily Architect).
    Full implementation in User Story 2.
    """

    __tablename__ = "conversation"

    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK to the agent handling this conversation",
    )
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="default_user",
        index=True,
        doc="User identifier",
    )
    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Conversation summary (auto-generated)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        doc="Conversation state: active, completed, archived",
    )
    context: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Conversation context (entities involved, preferences)",
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="conversations",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        lazy="selectin",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Conversation(id={self.id!r}, status={self.status!r})>"
