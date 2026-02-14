"""Prompt version CRUD + promote-both + prompt generation endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from src.api.rate_limit import limiter
from src.dal.agents import (
    AgentConfigVersionRepository,
    AgentPromptVersionRepository,
    AgentRepository,
)
from src.storage import get_session

from .schemas import (
    AgentPromptVersionCreate,
    AgentPromptVersionUpdate,
    ConfigVersionResponse,
    PromoteBothResponse,
    PromptGenerateRequest,
    PromptGenerateResponse,
    PromptVersionResponse,
)
from .serializers import _serialize_config, _serialize_prompt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Agents"])

# Tool definitions per agent role for prompt generation context
_AGENT_TOOLS: dict[str, list[str]] = {
    "architect": [
        "get_entity_state",
        "list_entities_by_domain",
        "search_entities",
        "get_domain_summary",
        "control_entity",
        "deploy_automation",
        "create_script",
        "create_scene",
        "list_automations",
        "render_template",
        "seek_approval",
        "analyze_energy",
        "analyze_behavior",
        "discover_entities",
        "get_entity_history",
        "diagnose_issue",
        "run_custom_analysis",
        "analyze_error_log",
        "find_unavailable_entities",
        "diagnose_entity",
        "check_integration_health",
        "validate_config",
        "create_insight_schedule",
    ],
    "data_scientist": [
        "run_custom_analysis",
        "analyze_energy",
        "analyze_behavior",
        "get_entity_history",
        "diagnose_issue",
    ],
    "librarian": [
        "discover_entities",
        "list_entities_by_domain",
        "search_entities",
        "get_domain_summary",
    ],
    "developer": [
        "deploy_automation",
        "delete_automation",
        "create_script",
        "create_scene",
    ],
    "orchestrator": [],
    "energy_analyst": [
        "run_custom_analysis",
        "analyze_energy",
        "get_entity_history",
    ],
    "behavioral_analyst": [
        "run_custom_analysis",
        "analyze_behavior",
        "get_entity_history",
    ],
    "diagnostic_analyst": [
        "run_custom_analysis",
        "diagnose_issue",
        "analyze_error_log",
        "find_unavailable_entities",
        "diagnose_entity",
        "check_integration_health",
    ],
    "dashboard_designer": [
        "generate_dashboard_yaml",
        "validate_dashboard_yaml",
        "list_dashboards",
    ],
}


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
                bump_type=body.bump_type,
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

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
            raise HTTPException(status_code=409, detail=str(e)) from e

        if not version:
            raise HTTPException(status_code=404, detail="Prompt version not found")

        await session.commit()
        return PromptVersionResponse(**_serialize_prompt(version))


@router.post(
    "/{agent_name}/prompt/versions/{version_id}/promote",
    response_model=PromptVersionResponse,
)
@limiter.limit("10/minute")
async def promote_prompt_version(
    request: Request,
    agent_name: str,
    version_id: str,
    bump_type: str = Query("patch", pattern="^(major|minor|patch)$"),
) -> PromptVersionResponse:
    """Promote a draft prompt version to active.

    Query params:
        bump_type: Semver bump type (major / minor / patch). Defaults to patch.
    """
    async with get_session() as session:
        prompt_repo = AgentPromptVersionRepository(session)
        try:
            version = await prompt_repo.promote(version_id, bump_type=bump_type)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

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
            raise HTTPException(status_code=409, detail=str(e)) from e

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
            raise HTTPException(status_code=409, detail=str(e)) from e

        if not deleted:
            raise HTTPException(status_code=404, detail="Prompt version not found")

        await session.commit()


@router.post("/{agent_name}/promote-all")
async def promote_both(
    agent_name: str,
    bump_type: str = Query("patch", pattern="^(major|minor|patch)$"),
) -> PromoteBothResponse:
    """Promote both config and prompt drafts to active in one operation.

    Query params:
        bump_type: Semver bump type (major / minor / patch). Defaults to patch.

    Promotes any existing drafts. If no drafts exist, returns a message.
    """
    async with get_session() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        config_repo = AgentConfigVersionRepository(session)
        prompt_repo = AgentPromptVersionRepository(session)

        promoted_config = None
        promoted_prompt = None
        errors: list[str] = []

        # Promote config draft if it exists
        config_draft = await config_repo.get_draft(agent.id)
        if config_draft:
            try:
                promoted_config = await config_repo.promote(
                    config_draft.id,
                    bump_type=bump_type,
                )
            except ValueError as e:
                errors.append(f"Config: {e}")

        # Promote prompt draft if it exists
        prompt_draft = await prompt_repo.get_draft(agent.id)
        if prompt_draft:
            try:
                promoted_prompt = await prompt_repo.promote(
                    prompt_draft.id,
                    bump_type=bump_type,
                )
            except ValueError as e:
                errors.append(f"Prompt: {e}")

        if not config_draft and not prompt_draft:
            raise HTTPException(
                status_code=409,
                detail="No drafts found to promote",
            )

        if errors:
            raise HTTPException(status_code=409, detail="; ".join(errors))

        # Update agent version from the latest promoted version
        latest_version = (
            promoted_config.version
            if promoted_config and promoted_config.version
            else promoted_prompt.version
            if promoted_prompt and promoted_prompt.version
            else None
        )
        if latest_version:
            agent.version = latest_version

        await session.commit()

        parts: list[str] = []
        if promoted_config:
            parts.append(f"config v{promoted_config.version or promoted_config.version_number}")
        if promoted_prompt:
            parts.append(f"prompt v{promoted_prompt.version or promoted_prompt.version_number}")

        return PromoteBothResponse(
            config=ConfigVersionResponse(**_serialize_config(promoted_config))
            if promoted_config
            else None,
            prompt=PromptVersionResponse(**_serialize_prompt(promoted_prompt))
            if promoted_prompt
            else None,
            message=f"Promoted {' and '.join(parts)} to active",
        )


@router.post(
    "/{agent_name}/prompt/generate",
    response_model=PromptGenerateResponse,
)
@limiter.limit("10/minute")
async def generate_prompt(
    request: Request,
    agent_name: str,
    body: PromptGenerateRequest,
) -> PromptGenerateResponse:
    """Generate a system prompt for an agent using AI.

    Uses the architect's LLM to generate a context-aware system prompt
    based on the agent's role, description, available tools, current
    prompt, and optional user instructions.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.llm import get_llm

    async with get_session() as session:
        repo = AgentRepository(session)
        agent = await repo.get_by_name(agent_name)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Gather context
        tools = _AGENT_TOOLS.get(agent_name, [])
        current_prompt = None
        if agent.active_prompt_version:
            current_prompt = agent.active_prompt_version.prompt_template

        # Build meta-prompt
        meta_parts = [
            "You are an expert AI prompt engineer. Your task is to generate a "
            "high-quality system prompt for an AI agent in a Home Assistant "
            "automation platform called Project Aether.",
            "",
            f"## Target Agent: {agent.name}",
            f"**Role**: {agent_name}",
            f"**Description**: {agent.description}",
        ]

        if tools:
            meta_parts.append("")
            meta_parts.append("## Available Tools")
            meta_parts.append(
                "The agent has access to these tools: " + ", ".join(f"`{t}`" for t in tools)
            )

        if current_prompt:
            meta_parts.append("")
            meta_parts.append("## Current System Prompt")
            meta_parts.append("Here is the agent's current system prompt for reference:")
            # Truncate very long prompts to avoid token waste
            truncated = current_prompt[:8000]
            if len(current_prompt) > 8000:
                truncated += "\n... (truncated)"
            meta_parts.append(f"```\n{truncated}\n```")

        meta_parts.append("")
        meta_parts.append("## Instructions")
        meta_parts.append(
            "Generate a comprehensive system prompt that:\n"
            "1. Clearly defines the agent's role and responsibilities\n"
            "2. Explains how and when to use each available tool\n"
            "3. Sets appropriate behavioral guidelines\n"
            "4. Includes safety constraints (e.g. HITL approval for mutations)\n"
            "5. Provides response formatting guidelines"
        )

        if body.user_input:
            meta_parts.append("")
            meta_parts.append("## Additional User Requirements")
            meta_parts.append(body.user_input)

        meta_parts.append("")
        meta_parts.append(
            "Return ONLY the system prompt text. Do not wrap it in code "
            "blocks or add any preamble/commentary."
        )

        meta_prompt = "\n".join(meta_parts)

        # Invoke LLM
        llm = get_llm()
        messages = [
            SystemMessage(content=meta_prompt),
            HumanMessage(content=f"Generate the system prompt for the {agent_name} agent."),
        ]
        response = await llm.ainvoke(messages)

        return PromptGenerateResponse(
            generated_prompt=str(response.content),
            agent_name=agent.name,
            agent_role=agent_name,
        )
