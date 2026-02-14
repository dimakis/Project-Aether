"""Seed agents endpoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from src.api.rate_limit import limiter
from src.dal.agents import (
    AgentConfigVersionRepository,
    AgentPromptVersionRepository,
    AgentRepository,
)
from src.storage import get_session
from src.storage.entities.agent import AgentStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Agents"])


@router.post("/seed", response_model=dict, status_code=201)
@limiter.limit("5/minute")
async def seed_agents(request: Request) -> dict[str, Any]:
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
        {
            "name": "energy_analyst",
            "description": "Energy consumption analysis, cost optimization, and usage patterns.",
            "status": AgentStatus.ENABLED.value,
            "model": settings.data_scientist_model or settings.llm_model,
            "temperature": settings.data_scientist_temperature or settings.llm_temperature,
            "prompt_name": None,
        },
        {
            "name": "behavioral_analyst",
            "description": "User behavior patterns, routine detection, and automation suggestions.",
            "status": AgentStatus.ENABLED.value,
            "model": settings.data_scientist_model or settings.llm_model,
            "temperature": settings.data_scientist_temperature or settings.llm_temperature,
            "prompt_name": None,
        },
        {
            "name": "diagnostic_analyst",
            "description": "System health monitoring, error diagnosis, and integration troubleshooting.",
            "status": AgentStatus.ENABLED.value,
            "model": settings.data_scientist_model or settings.llm_model,
            "temperature": settings.data_scientist_temperature or settings.llm_temperature,
            "prompt_name": None,
        },
        {
            "name": "dashboard_designer",
            "description": "Lovelace dashboard design, YAML generation, and deployment.",
            "status": AgentStatus.ENABLED.value,
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "prompt_name": "dashboard_designer_system",
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
