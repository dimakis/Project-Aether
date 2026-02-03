"""Agent entity model.

Represents an agent in the system for tracing and orchestration purposes.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage.models import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.storage.entities.conversation import Conversation

# Valid agent names in the system
AgentName = Literal[
    "librarian",
    "categorizer",
    "architect",
    "developer",
    "data_scientist",
    "orchestrator",
]


class Agent(Base, UUIDMixin, TimestampMixin):
    """Agent entity for tracking agent instances and their configurations.

    Agents are the core actors in Project Aether:
    - Librarian: HA entity discovery and sync
    - Categorizer: Entity classification and grouping
    - Architect: Automation design and user interaction
    - Developer: Automation implementation
    - Data Scientist: Analytics and optimization
    - Orchestrator: Multi-agent coordination

    Attributes:
        id: Unique identifier (UUID)
        name: Agent identifier (e.g., 'librarian', 'architect')
        description: Human-readable description of agent's purpose
        version: Semantic version of the agent implementation
        prompt_template: System prompt template (versioned in MLflow)
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
    prompt_template: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="System prompt template (versioned in MLflow for observability)",
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="agent",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Agent(name={self.name!r}, version={self.version!r})>"

    @classmethod
    def create(
        cls,
        name: AgentName,
        description: str,
        version: str = "0.1.0",
        prompt_template: str | None = None,
    ) -> "Agent":
        """Factory method to create a new Agent.

        Args:
            name: Agent identifier
            description: Human-readable description
            version: Semantic version (default: 0.1.0)
            prompt_template: Optional system prompt template

        Returns:
            New Agent instance (not yet persisted)
        """
        return cls(
            name=name,
            description=description,
            version=version,
            prompt_template=prompt_template,
        )
