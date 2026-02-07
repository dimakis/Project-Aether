"""Agent prompt version entity model.

Stores versioned system prompt template snapshots per agent.
Supports draft -> active -> archived promotion lifecycle.

Feature 23: Agent Configuration.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.entities.agent_config_version import VersionStatus
from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.agent import Agent


class AgentPromptVersion(Base, UUIDMixin, TimestampMixin):
    """Versioned system prompt template for an agent.

    Each version captures a complete prompt template. Only one draft and
    one active version exist per agent at a time.

    Lifecycle: draft -> active -> archived (on next promotion)

    Attributes:
        id: Unique identifier (UUID)
        agent_id: FK to parent Agent
        version_number: Auto-incrementing version per agent (1, 2, 3, ...)
        status: draft | active | archived
        prompt_template: Full system prompt text
        change_summary: Optional human-readable description of the change
        promoted_at: When this version was promoted to active
    """

    __tablename__ = "agent_prompt_version"

    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK to parent Agent",
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Auto-incrementing version number per agent",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=VersionStatus.DRAFT.value,
        index=True,
        doc="Version status: draft, active, or archived",
    )
    prompt_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full system prompt template text",
    )
    change_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Human-readable description of the change",
    )
    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When this version was promoted to active",
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="prompt_versions",
        foreign_keys=[agent_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AgentPromptVersion(agent_id={self.agent_id!r}, "
            f"v{self.version_number}, status={self.status!r})>"
        )

    @classmethod
    def create(
        cls,
        agent_id: str,
        version_number: int,
        prompt_template: str,
        *,
        change_summary: str | None = None,
        status: str = VersionStatus.DRAFT.value,
    ) -> "AgentPromptVersion":
        """Factory method to create a new AgentPromptVersion.

        Args:
            agent_id: Parent agent ID
            version_number: Version number for this agent
            prompt_template: System prompt text
            change_summary: Description of the change
            status: Initial status (default: draft)

        Returns:
            New AgentPromptVersion instance (not yet persisted)
        """
        return cls(
            agent_id=agent_id,
            version_number=version_number,
            status=status,
            prompt_template=prompt_template,
            change_summary=change_summary,
        )
