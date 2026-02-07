"""Agent configuration CRUD API.

Feature 23: Agent Configuration Page.

Provides endpoints for managing agents and their versioned LLM
configurations (model settings and prompt templates) with
draft -> active -> archived promotion lifecycle.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.dal.agents import (
    AgentConfigVersionRepository,
    AgentPromptVersionRepository,
    AgentRepository,
)
from src.storage import get_session
from src.storage.entities.agent import AgentStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])


# ─── Request / Response Schemas ───────────────────────────────────────────────


class AgentConfigVersionCreate(BaseModel):
    """Request body for creating a config version draft."""

    model_name: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    fallback_model: str | None = None
    tools_enabled: list[str] | None = None
    change_summary: str | None = None


class AgentConfigVersionUpdate(BaseModel):
    """Request body for updating a config version draft."""

    model_name: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    fallback_model: str | None = None
    tools_enabled: list[str] | None = None
    change_summary: str | None = None


class AgentPromptVersionCreate(BaseModel):
    """Request body for creating a prompt version draft."""

    prompt_template: str = Field(..., min_length=1)
    change_summary: str | None = None


class AgentPromptVersionUpdate(BaseModel):
    """Request body for updating a prompt version draft."""

    prompt_template: str | None = None
    change_summary: str | None = None


class AgentStatusUpdate(BaseModel):
    """Request body for updating agent status."""

    status: str = Field(..., pattern="^(disabled|enabled|primary)$")


class ConfigVersionResponse(BaseModel):
    """Response schema for a config version."""

    id: str
    agent_id: str
    version_number: int
    status: str
    model_name: str | None
    temperature: float | None
    fallback_model: str | None
    tools_enabled: list[str] | None
    change_summary: str | None
    promoted_at: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PromptVersionResponse(BaseModel):
    """Response schema for a prompt version."""

    id: str
    agent_id: str
    version_number: int
    status: str
    prompt_template: str
    change_summary: str | None
    promoted_at: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    """Response schema for an agent."""

    id: str
    name: str
    description: str
    version: str
    status: str
    active_config_version_id: str | None
    active_prompt_version_id: str | None
    active_config: ConfigVersionResponse | None = None
    active_prompt: PromptVersionResponse | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Response schema for agent list."""

    agents: list[AgentResponse]
    total: int


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _serialize_config(cv: Any) -> dict[str, Any]:
    """Serialize a config version to response dict."""
    return {
        "id": cv.id,
        "agent_id": cv.agent_id,
        "version_number": cv.version_number,
        "status": cv.status,
        "model_name": cv.model_name,
        "temperature": cv.temperature,
        "fallback_model": cv.fallback_model,
        "tools_enabled": cv.tools_enabled,
        "change_summary": cv.change_summary,
        "promoted_at": cv.promoted_at.isoformat() if cv.promoted_at else None,
        "created_at": cv.created_at.isoformat() if cv.created_at else "",
        "updated_at": cv.updated_at.isoformat() if cv.updated_at else "",
    }


def _serialize_prompt(pv: Any) -> dict[str, Any]:
    """Serialize a prompt version to response dict."""
    return {
        "id": pv.id,
        "agent_id": pv.agent_id,
        "version_number": pv.version_number,
        "status": pv.status,
        "prompt_template": pv.prompt_template,
        "change_summary": pv.change_summary,
        "promoted_at": pv.promoted_at.isoformat() if pv.promoted_at else None,
        "created_at": pv.created_at.isoformat() if pv.created_at else "",
        "updated_at": pv.updated_at.isoformat() if pv.updated_at else "",
    }


def _serialize_agent(agent: Any, active_config: Any = None, active_prompt: Any = None) -> dict[str, Any]:
    """Serialize an agent to response dict."""
    result: dict[str, Any] = {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "version": agent.version,
        "status": agent.status,
        "active_config_version_id": agent.active_config_version_id,
        "active_prompt_version_id": agent.active_prompt_version_id,
        "active_config": _serialize_config(active_config) if active_config else None,
        "active_prompt": _serialize_prompt(active_prompt) if active_prompt else None,
        "created_at": agent.created_at.isoformat() if agent.created_at else "",
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else "",
    }
    return result


# ─── Agent Endpoints ──────────────────────────────────────────────────────────


@router.get("", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """List all agents with their active config/prompt versions."""
    async with get_session() as session:
        repo = AgentRepository(session)
        config_repo = AgentConfigVersionRepository(session)
        prompt_repo = AgentPromptVersionRepository(session)

        agents = await repo.list_all()
        items = []
        for agent in agents:
            active_config = await config_repo.get_active(agent.id)
            active_prompt = await prompt_repo.get_active(agent.id)
            items.append(
                AgentResponse(**_serialize_agent(agent, active_config, active_prompt))
            )

        return AgentListResponse(agents=items, total=len(items))


@router.get("/{agent_name}", response_model=AgentResponse)
async def get_agent(agent_name: str) -> AgentResponse:
    """Get agent details by name."""
    async with get_session() as session:
        repo = AgentRepository(session)
        config_repo = AgentConfigVersionRepository(session)
        prompt_repo = AgentPromptVersionRepository(session)

        agent = await repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        active_config = await config_repo.get_active(agent.id)
        active_prompt = await prompt_repo.get_active(agent.id)

        return AgentResponse(**_serialize_agent(agent, active_config, active_prompt))


@router.patch("/{agent_name}", response_model=AgentResponse)
async def update_agent_status(
    agent_name: str,
    body: AgentStatusUpdate,
) -> AgentResponse:
    """Update agent lifecycle status."""
    async with get_session() as session:
        repo = AgentRepository(session)

        try:
            new_status = AgentStatus(body.status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {body.status}. Must be disabled, enabled, or primary.",
            )

        try:
            agent = await repo.update_status(agent_name, new_status)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        await session.commit()

        config_repo = AgentConfigVersionRepository(session)
        prompt_repo = AgentPromptVersionRepository(session)
        active_config = await config_repo.get_active(agent.id)
        active_prompt = await prompt_repo.get_active(agent.id)

        return AgentResponse(**_serialize_agent(agent, active_config, active_prompt))


# ─── Config Version Endpoints ─────────────────────────────────────────────────


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
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

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
            raise HTTPException(status_code=409, detail=str(e))

        if not version:
            raise HTTPException(status_code=404, detail="Config version not found")

        await session.commit()
        return ConfigVersionResponse(**_serialize_config(version))


@router.post(
    "/{agent_name}/config/versions/{version_id}/promote",
    response_model=ConfigVersionResponse,
)
async def promote_config_version(
    agent_name: str,
    version_id: str,
) -> ConfigVersionResponse:
    """Promote a draft config version to active."""
    async with get_session() as session:
        config_repo = AgentConfigVersionRepository(session)
        try:
            version = await config_repo.promote(version_id)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

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
            raise HTTPException(status_code=409, detail=str(e))

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
            raise HTTPException(status_code=409, detail=str(e))

        if not deleted:
            raise HTTPException(status_code=404, detail="Config version not found")

        await session.commit()


# ─── Prompt Version Endpoints ─────────────────────────────────────────────────


@router.get(
    "/{agent_name}/prompt/versions",
    response_model=list[PromptVersionResponse],
)
async def list_prompt_versions(agent_name: str) -> list[PromptVersionResponse]:
    """List all prompt versions for an agent."""
    async with get_session() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        prompt_repo = AgentPromptVersionRepository(session)
        versions = await prompt_repo.list_versions(agent.id)
        return [PromptVersionResponse(**_serialize_prompt(v)) for v in versions]


@router.post(
    "/{agent_name}/prompt/versions",
    response_model=PromptVersionResponse,
    status_code=201,
)
async def create_prompt_version(
    agent_name: str,
    body: AgentPromptVersionCreate,
) -> PromptVersionResponse:
    """Create a new draft prompt version for an agent."""
    async with get_session() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        prompt_repo = AgentPromptVersionRepository(session)
        try:
            version = await prompt_repo.create_draft(
                agent_id=agent.id,
                prompt_template=body.prompt_template,
                change_summary=body.change_summary,
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

        await session.commit()
        return PromptVersionResponse(**_serialize_prompt(version))


@router.patch(
    "/{agent_name}/prompt/versions/{version_id}",
    response_model=PromptVersionResponse,
)
async def update_prompt_version(
    agent_name: str,
    version_id: str,
    body: AgentPromptVersionUpdate,
) -> PromptVersionResponse:
    """Update a draft prompt version."""
    async with get_session() as session:
        prompt_repo = AgentPromptVersionRepository(session)

        try:
            version = await prompt_repo.update_draft(
                version_id,
                prompt_template=body.prompt_template,
                change_summary=body.change_summary,
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

        if not version:
            raise HTTPException(status_code=404, detail="Prompt version not found")

        await session.commit()
        return PromptVersionResponse(**_serialize_prompt(version))


@router.post(
    "/{agent_name}/prompt/versions/{version_id}/promote",
    response_model=PromptVersionResponse,
)
async def promote_prompt_version(
    agent_name: str,
    version_id: str,
) -> PromptVersionResponse:
    """Promote a draft prompt version to active."""
    async with get_session() as session:
        prompt_repo = AgentPromptVersionRepository(session)
        try:
            version = await prompt_repo.promote(version_id)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

        await session.commit()

        # Invalidate runtime cache so agents pick up the new prompt
        from src.agents.config_cache import invalidate_agent_config
        invalidate_agent_config(agent_name)

        logger.info(
            "Prompt v%d promoted for agent %s",
            version.version_number,
            agent_name,
        )
        return PromptVersionResponse(**_serialize_prompt(version))


@router.post(
    "/{agent_name}/prompt/rollback",
    response_model=PromptVersionResponse,
)
async def rollback_prompt_version(agent_name: str) -> PromptVersionResponse:
    """Rollback to the previous prompt version (creates a new draft)."""
    async with get_session() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        prompt_repo = AgentPromptVersionRepository(session)
        try:
            version = await prompt_repo.rollback(agent.id)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

        await session.commit()
        return PromptVersionResponse(**_serialize_prompt(version))


@router.delete(
    "/{agent_name}/prompt/versions/{version_id}",
    status_code=204,
)
async def delete_prompt_version(agent_name: str, version_id: str) -> None:
    """Delete a draft prompt version."""
    async with get_session() as session:
        prompt_repo = AgentPromptVersionRepository(session)
        try:
            deleted = await prompt_repo.delete_draft(version_id)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

        if not deleted:
            raise HTTPException(status_code=404, detail="Prompt version not found")

        await session.commit()


# ─── Seed Endpoint ────────────────────────────────────────────────────────────


@router.post("/seed", response_model=dict, status_code=201)
async def seed_agents() -> dict[str, Any]:
    """Seed default agents with initial configurations.

    Creates agent records for all known roles (if they don't exist)
    and populates initial config and prompt versions from env vars
    and file-based prompts.
    """
    from src.agents.prompts import load_prompt
    from src.settings import get_settings

    settings = get_settings()

    # Agent definitions
    agent_defs: list[dict[str, Any]] = [
        {
            "name": "architect",
            "description": "Automation design and user interaction. The primary conversational agent.",
            "status": AgentStatus.PRIMARY.value,
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "prompt_name": "architect_system",
        },
        {
            "name": "data_scientist",
            "description": "Energy analysis, behavioral patterns, and data-driven insights.",
            "status": AgentStatus.ENABLED.value,
            "model": settings.data_scientist_model or settings.llm_model,
            "temperature": settings.data_scientist_temperature or settings.llm_temperature,
            "prompt_name": "data_scientist_system",
        },
        {
            "name": "librarian",
            "description": "HA entity discovery, cataloging, and sync.",
            "status": AgentStatus.ENABLED.value,
            "model": None,
            "temperature": None,
            "prompt_name": None,
        },
        {
            "name": "developer",
            "description": "Automation deployment and YAML generation.",
            "status": AgentStatus.ENABLED.value,
            "model": None,
            "temperature": None,
            "prompt_name": None,
        },
        {
            "name": "orchestrator",
            "description": "Multi-agent coordination and workflow management.",
            "status": AgentStatus.ENABLED.value,
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "prompt_name": None,
        },
    ]

    created_agents = 0
    created_configs = 0
    created_prompts = 0

    async with get_session() as session:
        agent_repo = AgentRepository(session)
        config_repo = AgentConfigVersionRepository(session)
        prompt_repo = AgentPromptVersionRepository(session)

        for defn in agent_defs:
            # Create or update agent
            agent = await agent_repo.create_or_update(
                name=defn["name"],
                description=defn["description"],
                status=defn["status"],
            )
            created_agents += 1

            # Create initial config version if none exists
            existing_config = await config_repo.get_active(agent.id)
            if not existing_config and defn["model"]:
                config = await config_repo.create_draft(
                    agent_id=agent.id,
                    model_name=defn["model"],
                    temperature=defn["temperature"],
                    change_summary="Initial seed from environment settings",
                )
                await config_repo.promote(config.id)
                created_configs += 1

            # Create initial prompt version if none exists
            existing_prompt = await prompt_repo.get_active(agent.id)
            if not existing_prompt and defn["prompt_name"]:
                try:
                    prompt_text = load_prompt(defn["prompt_name"])
                    prompt = await prompt_repo.create_draft(
                        agent_id=agent.id,
                        prompt_template=prompt_text,
                        change_summary="Initial seed from file-based prompt",
                    )
                    await prompt_repo.promote(prompt.id)
                    created_prompts += 1
                except FileNotFoundError:
                    logger.warning(
                        "Prompt file not found for %s: %s",
                        defn["name"],
                        defn["prompt_name"],
                    )

        await session.commit()

    logger.info(
        "Seeded %d agents, %d configs, %d prompts",
        created_agents,
        created_configs,
        created_prompts,
    )

    return {
        "agents_seeded": created_agents,
        "configs_created": created_configs,
        "prompts_created": created_prompts,
    }
