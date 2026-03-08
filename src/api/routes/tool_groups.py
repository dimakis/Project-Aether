"""Tool group CRUD endpoints.

Feature 34: Dynamic Tool Registry.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.api.schemas.tool_groups import (
    ToolGroupCreate,
    ToolGroupListResponse,
    ToolGroupResponse,
    ToolGroupUpdate,
)
from src.dal.tool_groups import ToolGroupRepository
from src.storage import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tool-groups", tags=["Tool Groups"])


def _get_known_tool_names() -> set[str]:
    """Get all known tool names from the Python registry."""
    from src.tools.registry import get_all_tools

    return {getattr(t, "name", "") for t in get_all_tools() if getattr(t, "name", "")}


def _validate_tool_names(tool_names: list[str]) -> list[str]:
    """Validate tool names exist in the registry. Returns list of unknown names."""
    known = _get_known_tool_names()
    return [n for n in tool_names if n not in known]


@router.get("", response_model=ToolGroupListResponse)
async def list_tool_groups() -> ToolGroupListResponse:
    async with get_session() as session:
        repo = ToolGroupRepository(session)
        groups = await repo.list_all()
        items = [ToolGroupResponse.from_entity(g) for g in groups]
        return ToolGroupListResponse(items=items, total=len(items))


@router.get("/{name}", response_model=ToolGroupResponse)
async def get_tool_group(name: str) -> ToolGroupResponse:
    async with get_session() as session:
        repo = ToolGroupRepository(session)
        group = await repo.get_by_name(name)
        if not group:
            raise HTTPException(status_code=404, detail=f"Tool group '{name}' not found")
        return ToolGroupResponse.from_entity(group)


@router.post("", response_model=ToolGroupResponse, status_code=201)
async def create_tool_group(body: ToolGroupCreate) -> ToolGroupResponse:
    unknown = _validate_tool_names(body.tool_names)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown tool names: {unknown}",
        )

    async with get_session() as session:
        repo = ToolGroupRepository(session)
        existing = await repo.get_by_name(body.name)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Tool group '{body.name}' already exists",
            )
        group = await repo.create(body.model_dump())
        await session.commit()
        return ToolGroupResponse.from_entity(group)


@router.put("/{name}", response_model=ToolGroupResponse)
async def update_tool_group(name: str, body: ToolGroupUpdate) -> ToolGroupResponse:
    if body.tool_names is not None:
        unknown = _validate_tool_names(body.tool_names)
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown tool names: {unknown}",
            )

    async with get_session() as session:
        repo = ToolGroupRepository(session)
        update_data = body.model_dump(exclude_unset=True)
        group = await repo.update(name, update_data)
        if not group:
            raise HTTPException(status_code=404, detail=f"Tool group '{name}' not found")
        await session.commit()
        return ToolGroupResponse.from_entity(group)
