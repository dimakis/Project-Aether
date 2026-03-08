"""Tool group API schemas.

Feature 34: Dynamic Tool Registry.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — required at runtime for Pydantic model fields
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.storage.entities.tool_group import ToolGroup


class ToolGroupResponse(BaseModel):
    """Response schema for a single tool group."""

    id: str
    name: str
    display_name: str
    description: str | None = None
    tool_names: list[str]
    tool_count: int
    is_read_only: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_entity(cls, group: ToolGroup) -> ToolGroupResponse:
        return cls(
            id=group.id,
            name=group.name,
            display_name=group.display_name,
            description=group.description,
            tool_names=group.tool_names or [],
            tool_count=len(group.tool_names or []),
            is_read_only=group.is_read_only,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )


class ToolGroupListResponse(BaseModel):
    """Response for listing all tool groups."""

    items: list[ToolGroupResponse]
    total: int


class ToolGroupCreate(BaseModel):
    """Request schema for creating a tool group."""

    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    tool_names: list[str] = Field(..., min_length=1)
    is_read_only: bool = True


class ToolGroupUpdate(BaseModel):
    """Request schema for updating a tool group."""

    display_name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    tool_names: list[str] | None = Field(None, min_length=1)
    is_read_only: bool | None = None
