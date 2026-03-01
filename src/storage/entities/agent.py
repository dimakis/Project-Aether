"""Agent entity model.

Represents an agent in the system for tracing and orchestration purposes.
Extended in Feature 23 with status lifecycle and versioned configuration.
"""

from enum import Enum
from typing import TYPE_CHECKING, Literal

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.agent_config_version import AgentConfigVersion
    from src.storage.entities.agent_prompt_version import AgentPromptVersion
    from src.storage.entities.conversation import Conversation

# Valid agent names in the system
AgentName = Literal[
    "librarian",
    "categorizer",
    "architect",
    "developer",
    "data_scientist",
    "orchestrator",
    "knowledge",
    "dashboard_designer",
    "energy_analyst",
    "behavioral_analyst",
    "diagnostic_analyst",
    "food",
    "research",
]


class AgentStatus(str, Enum):
    """Agent lifecycle status."""

    DISABLED = "disabled"
    ENABLED = "enabled"
    PRIMARY = "primary"


# Valid status transitions
VALID_AGENT_STATUS_TRANSITIONS: dict[AgentStatus, set[AgentStatus]] = {
    AgentStatus.DISABLED: {AgentStatus.ENABLED},
    AgentStatus.ENABLED: {AgentStatus.DISABLED, AgentStatus.PRIMARY},
    AgentStatus.PRIMARY: {AgentStatus.DISABLED, AgentStatus.ENABLED},
}


class Agent(Base, UUIDMixin, TimestampMixin):
    """Agent entity for tracking agent instances and their configurations.

    Agents are the core actors in Project Aether:
    - Librarian: HA entity discovery and sync
    - Categorizer: Entity classification and grouping
    - Architect: Automation design and user interaction
    - Developer: Automation implementation
    - Data Science team: Analytics and optimization
    - Orchestrator: Multi-agent coordination

    Attributes:
        id: Unique identifier (UUID)
        name: Agent identifier (e.g., 'librarian', 'architect')
        description: Human-readable description of agent's purpose
        version: Semantic version of the agent implementation
        status: Lifecycle status (disabled, enabled, primary)
        prompt_template: Legacy system prompt template (superseded by AgentPromptVersion)
        active_config_version_id: FK to currently active config version
        active_prompt_version_id: FK to currently active prompt version
        created_at: When the agent record was created
        updated_at: Last update timestamp
    """

    # Override auto tablename for clarity
    __tablename__ = "agent"

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        doc="Agent identifier (e.g., 'librarian', 'architect')",
    )
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Human-readable description of the agent's purpose",
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="0.1.0",
        doc="Semantic version of the agent implementation",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AgentStatus.ENABLED.value,
        index=True,
        doc="Lifecycle status: disabled, enabled, or primary",
    )
    prompt_template: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Legacy system prompt template (superseded by AgentPromptVersion)",
    )
    # Routing metadata (Feature 30: Domain-Agnostic Orchestration)
    domain: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Domain classification for intent routing (e.g., 'home', 'knowledge', 'food')",
    )
    is_routable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        doc="Whether the Orchestrator can route messages to this agent",
    )
    intent_patterns: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        doc="Intent patterns for Orchestrator matching (e.g., ['home_automation', 'device_control'])",
    )
    capabilities: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        doc="Agent capabilities for discovery and Agent Card generation",
    )

    active_config_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agent_config_version.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
        doc="FK to currently active config version",
    )
    active_prompt_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agent_prompt_version.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
        doc="FK to currently active prompt version",
    )

    # Relationships — collection (one-to-many via agent_id FK on child)
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="agent",
        lazy="selectin",
    )
    config_versions: Mapped[list["AgentConfigVersion"]] = relationship(
        "AgentConfigVersion",
        back_populates="agent",
        foreign_keys="[AgentConfigVersion.agent_id]",
        lazy="selectin",
        order_by="AgentConfigVersion.version_number.desc()",
    )
    prompt_versions: Mapped[list["AgentPromptVersion"]] = relationship(
        "AgentPromptVersion",
        back_populates="agent",
        foreign_keys="[AgentPromptVersion.agent_id]",
        lazy="selectin",
        order_by="AgentPromptVersion.version_number.desc()",
    )

    # Relationships — active version pointers (many-to-one via FK on Agent)
    # These use post_update=True to handle the circular dependency:
    # Agent -> AgentConfigVersion (active_config_version_id)
    # AgentConfigVersion -> Agent (agent_id)
    active_config_version: Mapped["AgentConfigVersion | None"] = relationship(
        "AgentConfigVersion",
        foreign_keys=[active_config_version_id],
        post_update=True,
        lazy="selectin",
    )
    active_prompt_version: Mapped["AgentPromptVersion | None"] = relationship(
        "AgentPromptVersion",
        foreign_keys=[active_prompt_version_id],
        post_update=True,
        lazy="selectin",
    )

    @property
    def is_active(self) -> bool:
        """Check if agent is available for delegation."""
        return self.status in (AgentStatus.ENABLED.value, AgentStatus.PRIMARY.value)

    def can_transition_to(self, new_status: AgentStatus) -> bool:
        """Check if a status transition is valid.

        Args:
            new_status: Target status

        Returns:
            True if the transition is allowed
        """
        current = AgentStatus(self.status)
        return new_status in VALID_AGENT_STATUS_TRANSITIONS.get(current, set())

    def __repr__(self) -> str:
        return f"<Agent(name={self.name!r}, version={self.version!r}, status={self.status!r})>"

    @classmethod
    def create(
        cls,
        name: AgentName,
        description: str,
        version: str = "0.1.0",
        prompt_template: str | None = None,
        status: str = AgentStatus.ENABLED.value,
    ) -> "Agent":
        """Factory method to create a new Agent.

        Args:
            name: Agent identifier
            description: Human-readable description
            version: Semantic version (default: 0.1.0)
            prompt_template: Optional system prompt template
            status: Initial status (default: enabled)

        Returns:
            New Agent instance (not yet persisted)
        """
        return cls(
            name=name,
            description=description,
            version=version,
            prompt_template=prompt_template,
            status=status,
        )
