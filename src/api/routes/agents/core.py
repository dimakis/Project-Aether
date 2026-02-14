"""Agent CRUD endpoints: list, get, update status, clone, quick model switch."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.dal.agents import (
    AgentConfigVersionRepository,
    AgentPromptVersionRepository,
    AgentRepository,
)
from src.storage import get_session
from src.storage.entities.agent import AgentStatus

from .schemas import (
    AgentListResponse,
    AgentResponse,
    AgentStatusUpdate,
    QuickModelSwitch,
)
from .serializers import _serialize_agent

router = APIRouter(tags=["Agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents() -> AgentListResponse:
    """List all agents with their active config/prompt versions."""
    async with get_session() as session:
        repo = AgentRepository(session)

        agents = await repo.list_all()
        items = []
        for agent in agents:
            # Use eager-loaded relationships instead of N+1 manual queries
            items.append(
                AgentResponse(
                    **_serialize_agent(
                        agent,
                        agent.active_config_version,
                        agent.active_prompt_version,
                    )
                )
            )

        return AgentListResponse(agents=items, total=len(items))


@router.get("/{agent_name}", response_model=AgentResponse)
async def get_agent(agent_name: str) -> AgentResponse:
    """Get agent details by name."""
    async with get_session() as session:
        repo = AgentRepository(session)

        agent = await repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Use eager-loaded relationships instead of manual queries
        return AgentResponse(
            **_serialize_agent(
                agent,
                agent.active_config_version,
                agent.active_prompt_version,
            )
        )


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
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {body.status}. Must be disabled, enabled, or primary.",
            ) from e

        try:
            agent = await repo.update_status(agent_name, new_status)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        await session.commit()

        # Refresh to pick up eager-loaded relationships after commit
        await session.refresh(agent)

        return AgentResponse(
            **_serialize_agent(
                agent,
                agent.active_config_version,
                agent.active_prompt_version,
            )
        )


@router.post("/{agent_name}/clone", response_model=AgentResponse, status_code=201)
async def clone_agent(agent_name: str) -> AgentResponse:
    """Clone an agent with its active config and prompt as new drafts.

    Creates a new agent named ``{agent_name}_copy`` (or ``_copy2`` etc. if
    the name already exists). The active config and prompt versions are
    copied as new drafts on the cloned agent, ready for editing.

    This makes it trivial to swap LLM backends: clone, change the model
    in the cloned config, promote, and disable the original.
    """
    async with get_session() as session:
        agent_repo = AgentRepository(session)
        config_repo = AgentConfigVersionRepository(session)
        prompt_repo = AgentPromptVersionRepository(session)

        source = await agent_repo.get_by_name(agent_name)
        if not source:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Generate a unique clone name
        clone_name = f"{agent_name}_copy"
        suffix = 1
        while await agent_repo.get_by_name(clone_name):
            suffix += 1
            clone_name = f"{agent_name}_copy{suffix}"

        # Create the cloned agent
        cloned = await agent_repo.create_or_update(
            name=clone_name,
            description=f"Clone of {source.description}",
            version=source.version,
            status=AgentStatus.ENABLED.value,
        )
        await session.flush()

        # Clone active config version as a draft
        src_config = source.active_config_version
        if src_config:
            new_config = await config_repo.create_draft(
                agent_id=cloned.id,
                model_name=src_config.model_name,
                temperature=src_config.temperature,
                fallback_model=src_config.fallback_model,
                tools_enabled=src_config.tools_enabled,
                change_summary=f"Cloned from {agent_name}",
            )
            await session.flush()

            # Auto-promote the config
            await config_repo.promote(new_config.id)
            await session.flush()

        # Clone active prompt version as a draft
        src_prompt = source.active_prompt_version
        if src_prompt:
            new_prompt = await prompt_repo.create_draft(
                agent_id=cloned.id,
                prompt_template=src_prompt.prompt_template,
                change_summary=f"Cloned from {agent_name}",
            )
            await session.flush()

            # Auto-promote the prompt
            await prompt_repo.promote(new_prompt.id)
            await session.flush()

        await session.commit()

        # Refresh to pick up eager-loaded relationships
        await session.refresh(cloned)

        return AgentResponse(
            **_serialize_agent(
                cloned,
                cloned.active_config_version,
                cloned.active_prompt_version,
            )
        )


@router.patch("/{agent_name}/model", response_model=AgentResponse)
async def quick_model_switch(
    agent_name: str,
    body: QuickModelSwitch,
) -> AgentResponse:
    """Quick model switch: create a new config version and promote in one step.

    Creates a draft config version with the new model (copying temperature
    and other settings from the current active config), then auto-promotes it.
    """
    from src.agents.config_cache import invalidate_agent_config

    async with get_session() as session:
        agent_repo = AgentRepository(session)
        config_repo = AgentConfigVersionRepository(session)

        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Get current config to copy settings
        current = agent.active_config_version
        temp = current.temperature if current else None
        fallback = current.fallback_model if current else None
        tools = current.tools_enabled if current else None

        try:
            version = await config_repo.create_draft(
                agent_id=agent.id,
                model_name=body.model_name,
                temperature=temp,
                fallback_model=fallback,
                tools_enabled=tools,
                change_summary=f"Quick switch to {body.model_name}",
            )
            await session.flush()

            await config_repo.promote(version.id)
            await session.flush()
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        await session.commit()
        invalidate_agent_config(agent_name)

        await session.refresh(agent)
        return AgentResponse(
            **_serialize_agent(
                agent,
                agent.active_config_version,
                agent.active_prompt_version,
            )
        )
