"""WorkflowDefinition entity for persistent workflow storage (Feature 29).

Stores declarative workflow configurations as JSONB so they can be
loaded, compiled, and executed dynamically.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class WorkflowDefinitionEntity(Base, UUIDMixin, TimestampMixin):
    """Persistent storage for declarative workflow definitions."""

    __tablename__ = "workflow_definition"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    state_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    intent_patterns: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
