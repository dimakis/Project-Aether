"""Conversation entity model.

A dialogue session between user and an agent - User Story 2.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.agent import Agent
    from src.storage.entities.automation_proposal import AutomationProposal
    from src.storage.entities.message import Message


class ConversationStatus(enum.Enum):
    """Status of a conversation."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Conversation(Base, UUIDMixin, TimestampMixin):
    """A dialogue session between user and an agent (primarily Architect).

    Conversations track the full context of automation design discussions,
    including all messages, proposals generated, and relevant entities.
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
        doc="Conversation summary (auto-generated from first message)",
    )
    status: Mapped[ConversationStatus] = mapped_column(
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True,
        doc="Conversation state: active, completed, archived",
    )
    context: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Conversation context (entities involved, preferences, history)",
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
        cascade="all, delete-orphan",
    )
    proposals: Mapped[list["AutomationProposal"]] = relationship(
        "AutomationProposal",
        back_populates="conversation",
        lazy="selectin",
        order_by="AutomationProposal.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id!r}, status={self.status.value!r})>"

    def complete(self) -> None:
        """Mark conversation as completed."""
        self.status = ConversationStatus.COMPLETED

    def archive(self) -> None:
        """Archive the conversation."""
        self.status = ConversationStatus.ARCHIVED

    @property
    def message_count(self) -> int:
        """Get number of messages in conversation."""
        return len(self.messages) if self.messages else 0

    @property
    def proposal_count(self) -> int:
        """Get number of proposals in conversation."""
        return len(self.proposals) if self.proposals else 0
