"""Flow grade entity model.

Stores user feedback (thumbs up/down) on conversation steps and
overall flow quality. Supports both per-span grading and conversation-level
grading.

Feature: Flow Grading.
"""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class FlowGrade(Base, UUIDMixin, TimestampMixin):
    """User feedback grade for a conversation step or overall flow.

    Attributes:
        id: Unique identifier (UUID)
        conversation_id: FK to conversation
        span_id: Optional span/trace ID for step-level grading
        grade: 1 (thumbs up) or -1 (thumbs down)
        comment: Optional user comment
        agent_role: Agent that produced this step (if known)
    """

    __tablename__ = "flow_grade"

    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK to conversation",
    )
    span_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Span/trace ID for step-level grading (null = overall)",
    )
    grade: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="1 = thumbs up, -1 = thumbs down",
    )
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional user comment",
    )
    agent_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Agent role that produced this step",
    )

    def __repr__(self) -> str:
        return (
            f"<FlowGrade(conversation_id={self.conversation_id!r}, "
            f"span_id={self.span_id!r}, grade={self.grade})>"
        )
