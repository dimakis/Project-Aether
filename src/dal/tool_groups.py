"""Tool group data access layer.

Feature 34: Dynamic Tool Registry.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from src.storage.entities.tool_group import ToolGroup

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ToolGroupRepository:
    """Repository for tool group CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_name(self, name: str) -> ToolGroup | None:
        result = await self.session.execute(select(ToolGroup).where(ToolGroup.name == name))
        return result.scalar_one_or_none()

    async def get_by_names(self, names: list[str]) -> list[ToolGroup]:
        if not names:
            return []
        result = await self.session.execute(select(ToolGroup).where(ToolGroup.name.in_(names)))
        return list(result.scalars().all())

    async def list_all(self) -> list[ToolGroup]:
        result = await self.session.execute(select(ToolGroup).order_by(ToolGroup.name))
        return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> ToolGroup:
        from uuid import uuid4

        group = ToolGroup(id=str(uuid4()), **data)
        self.session.add(group)
        await self.session.flush()
        return group

    async def update(self, name: str, data: dict[str, Any]) -> ToolGroup | None:
        group = await self.get_by_name(name)
        if not group:
            return None
        for key, value in data.items():
            if hasattr(group, key) and key not in ("id", "name", "created_at"):
                setattr(group, key, value)
        await self.session.flush()
        return group
