"""Config version CRUD endpoints: list, create, update, promote, rollback, delete."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from src.api.rate_limit import limiter
from src.dal.agents import AgentConfigVersionRepository, AgentRepository
from src.storage import get_session

from .schemas import AgentConfigVersionCreate, AgentConfigVersionUpdate, ConfigVersionResponse
from .serializers import _serialize_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Agents"])


@router.get(
    "/{agent_name}/config/versions",
    response_model=list[ConfigVersionResponse],
)
async def list_config_versions(agent_name: str) -> list[ConfigVersionResponse]:
    """List all config versions for an agent."""
    async with get_session() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        config_repo = AgentConfigVersionRepository(session)
        versions = await config_repo.list_versions(agent.id)
        return [ConfigVersionResponse(**_serialize_config(v)) for v in versions]


@router.post(
    "/{agent_name}/config/versions",
    response_model=ConfigVersionResponse,
    status_code=201,
)
async def create_config_version(
    agent_name: str,
    body: AgentConfigVersionCreate,
) -> ConfigVersionResponse:
    """Create a new draft config version for an agent."""
    async with get_session() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        config_repo = AgentConfigVersionRepository(session)
        try:
            version = await config_repo.create_draft(
                agent_id=agent.id,
                model_name=body.model_name,
                temperature=body.temperature,
                fallback_model=body.fallback_model,
                tools_enabled=body.tools_enabled,
                change_summary=body.change_summary,
                bump_type=body.bump_type,
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        await session.commit()
        return ConfigVersionResponse(**_serialize_config(version))


@router.patch(
    "/{agent_name}/config/versions/{version_id}",
    response_model=ConfigVersionResponse,
)
async def update_config_version(
    agent_name: str,
    version_id: str,
    body: AgentConfigVersionUpdate,
) -> ConfigVersionResponse:
    """Update a draft config version."""
    async with get_session() as session:
        config_repo = AgentConfigVersionRepository(session)
        fields = body.model_dump(exclude_unset=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        try:
            version = await config_repo.update_draft(version_id, **fields)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        if not version:
            raise HTTPException(status_code=404, detail="Config version not found")

        await session.commit()
        return ConfigVersionResponse(**_serialize_config(version))


@router.post(
    "/{agent_name}/config/versions/{version_id}/promote",
    response_model=ConfigVersionResponse,
)
@limiter.limit("10/minute")
async def promote_config_version(
    request: Request,
    agent_name: str,
    version_id: str,
    bump_type: str = Query("patch", pattern="^(major|minor|patch)$"),
) -> ConfigVersionResponse:
    """Promote a draft config version to active.

    Query params:
        bump_type: Semver bump type (major / minor / patch). Defaults to patch.
    """
    async with get_session() as session:
        config_repo = AgentConfigVersionRepository(session)
        try:
            version = await config_repo.promote(version_id, bump_type=bump_type)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        await session.commit()

        # Invalidate runtime cache so agents pick up the new config
        from src.agents.config_cache import invalidate_agent_config

        invalidate_agent_config(agent_name)

        logger.info(
            "Config v%d promoted for agent %s (model=%s)",
            version.version_number,
            agent_name,
            version.model_name,
        )
        return ConfigVersionResponse(**_serialize_config(version))


@router.post(
    "/{agent_name}/config/rollback",
    response_model=ConfigVersionResponse,
)
async def rollback_config_version(agent_name: str) -> ConfigVersionResponse:
    """Rollback to the previous config version (creates a new draft)."""
    async with get_session() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        config_repo = AgentConfigVersionRepository(session)
        try:
            version = await config_repo.rollback(agent.id)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        await session.commit()
        return ConfigVersionResponse(**_serialize_config(version))


@router.delete(
    "/{agent_name}/config/versions/{version_id}",
    status_code=204,
)
async def delete_config_version(agent_name: str, version_id: str) -> None:
    """Delete a draft config version."""
    async with get_session() as session:
        config_repo = AgentConfigVersionRepository(session)
        try:
            deleted = await config_repo.delete_draft(version_id)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        if not deleted:
            raise HTTPException(status_code=404, detail="Config version not found")

        await session.commit()
