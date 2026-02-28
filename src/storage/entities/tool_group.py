"""Tool group entity model.

Stores named groups of tools for dynamic agent tool assignment.
Feature 34: Dynamic Tool Registry.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class ToolGroup(Base, UUIDMixin, TimestampMixin):
    """Named collection of tools for dynamic agent assignment.

    Groups organize tools by domain (e.g., HA queries, diagnostics)
    and carry a read-only flag for mutation registry classification.

    Attributes:
        name: Unique identifier (e.g., "ha_entity_query")
        display_name: Human-readable name (e.g., "HA Entity Queries")
        description: Optional description of the group's purpose
        tool_names: JSON array of tool name strings
        is_read_only: Whether all tools in this group are read-only
    """

    __tablename__ = "tool_group"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique group identifier",
    )
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Human-readable group name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional description of group purpose",
    )
    tool_names: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
        doc="JSON array of tool name strings",
    )
    is_read_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        doc="Whether all tools in this group are read-only (fail-safe: default true)",
    )

    def __repr__(self) -> str:
        return f"<ToolGroup(name={self.name!r}, tools={len(self.tool_names)})>"
