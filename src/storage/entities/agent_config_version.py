"""Agent config version entity model.

Stores versioned LLM configuration snapshots per agent (model, temperature,
fallback model, tool assignments). Supports draft -> active -> archived
promotion lifecycle.

Feature 23: Agent Configuration.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.agent import Agent


class VersionStatus(str, Enum):
    """Status of a config or prompt version."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class AgentConfigVersion(Base, UUIDMixin, TimestampMixin):
    """Versioned LLM configuration snapshot for an agent.

    Each version captures a complete configuration state (model, temperature,
    tools, fallback). Only one draft and one active version exist per agent
    at a time.

    Lifecycle: draft -> active -> archived (on next promotion)

    Attributes:
        id: Unique identifier (UUID)
        agent_id: FK to parent Agent
        version_number: Auto-incrementing version per agent (1, 2, 3, ...)
        status: draft | active | archived
        model_name: LLM model identifier (e.g. "anthropic/claude-sonnet-4")
        temperature: Generation temperature (0.0-2.0)
        fallback_model: Optional fallback model when primary is unavailable
        tools_enabled: JSON array of tool names assigned to this agent
        tool_groups_enabled: JSON array of tool group names assigned to this agent
        change_summary: Optional human-readable description of the change
        promoted_at: When this version was promoted to active
    """

    __tablename__ = "agent_config_version"

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
    version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Semantic version string (e.g. '1.2.0'). Computed from bump_type.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=VersionStatus.DRAFT.value,
        index=True,
        doc="Version status: draft, active, or archived",
    )
    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="LLM model identifier (e.g. 'anthropic/claude-sonnet-4')",
    )
    temperature: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Generation temperature (0.0-2.0)",
    )
    fallback_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Fallback model when primary is unavailable",
    )
    tools_enabled: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="JSON array of tool names assigned to this agent",
    )
    tool_groups_enabled: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="JSON array of tool group names assigned to this agent",
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
        back_populates="config_versions",
        foreign_keys=[agent_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AgentConfigVersion(agent_id={self.agent_id!r}, "
            f"v{self.version_number}, status={self.status!r})>"
        )

    @classmethod
    def create(
        cls,
        agent_id: str,
        version_number: int,
        *,
        version: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        fallback_model: str | None = None,
        tools_enabled: list[str] | None = None,
        tool_groups_enabled: list[str] | None = None,
        change_summary: str | None = None,
        status: str = VersionStatus.DRAFT.value,
    ) -> "AgentConfigVersion":
        """Factory method to create a new AgentConfigVersion.

        Args:
            agent_id: Parent agent ID
            version_number: Version number for this agent
            version: Semantic version string (e.g. '1.2.0')
            model_name: LLM model identifier
            temperature: Generation temperature
            fallback_model: Fallback model name
            tools_enabled: List of enabled tool names
            tool_groups_enabled: List of enabled tool group names
            change_summary: Description of the change
            status: Initial status (default: draft)

        Returns:
            New AgentConfigVersion instance (not yet persisted)
        """
        return cls(
            agent_id=agent_id,
            version_number=version_number,
            version=version,
            status=status,
            model_name=model_name,
            temperature=temperature,
            fallback_model=fallback_model,
            tools_enabled=tools_enabled,
            tool_groups_enabled=tool_groups_enabled,
            change_summary=change_summary,
        )
