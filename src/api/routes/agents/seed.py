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

# Routing metadata is static — it describes what each agent *can* do,
# not runtime config.  Model/temperature are resolved at seed time from
# settings so they're added dynamically in seed_agents().
AGENT_DEFS: list[dict[str, Any]] = [
    {
        "name": "architect",
        "description": "Automation design and user interaction. The primary conversational agent.",
        "status": AgentStatus.PRIMARY.value,
        "prompt_name": "architect_system",
        "domain": "home",
        "is_routable": True,
        "intent_patterns": ["home_automation", "device_control", "lights", "scenes", "scripts"],
        "capabilities": ["control_devices", "create_automations", "query_entities"],
    },
    {
        "name": "knowledge",
        "description": "General knowledge and questions. Answers without tools using LLM knowledge.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
        "domain": "knowledge",
        "is_routable": True,
        "intent_patterns": ["general_question", "explain", "trivia", "how_to", "definition"],
        "capabilities": ["answer_questions", "explain_concepts"],
    },
    {
        "name": "data_scientist",
        "description": "Energy analysis, behavioral patterns, and data-driven insights.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": "data_scientist_system",
        "domain": "analytics",
        "is_routable": True,
        "intent_patterns": [
            "energy_analysis",
            "usage_patterns",
            "anomaly_detection",
            "optimization",
        ],
        "capabilities": ["analyze_data", "generate_reports", "run_scripts"],
    },
    {
        "name": "dashboard_designer",
        "description": "Lovelace dashboard design, YAML generation, and deployment.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": "dashboard_designer_system",
        "domain": "dashboard",
        "is_routable": True,
        "intent_patterns": ["dashboard_design", "lovelace", "ui_layout", "cards"],
        "capabilities": ["design_dashboards", "generate_yaml", "deploy_dashboards"],
    },
    {
        "name": "librarian",
        "description": "HA entity discovery, cataloging, and sync.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
    },
    {
        "name": "developer",
        "description": "Automation deployment and YAML generation.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
    },
    {
        "name": "orchestrator",
        "description": "Intent classification and multi-agent routing.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
    },
    {
        "name": "energy_analyst",
        "description": "Energy consumption analysis, cost optimization, and usage patterns.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
    },
    {
        "name": "behavioral_analyst",
        "description": "User behavior patterns, routine detection, and automation suggestions.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
    },
    {
        "name": "diagnostic_analyst",
        "description": "System health monitoring, error diagnosis, and integration troubleshooting.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
    },
    {
        "name": "food",
        "description": "Cooking, recipes, meal planning, and kitchen appliance control.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
        "domain": "food",
        "is_routable": True,
        "intent_patterns": ["hungry", "recipe", "cooking", "meal", "food", "order_food", "preheat"],
        "capabilities": ["search_recipes", "control_kitchen_appliances", "order_food"],
        "tools_enabled": [
            "web_search",
            "get_entity_state",
            "list_entities_by_domain",
            "search_entities",
            "seek_approval",
        ],
        "model_tier": "standard",
    },
    {
        "name": "research",
        "description": "Web research, information gathering, and summarization.",
        "status": AgentStatus.ENABLED.value,
        "prompt_name": None,
        "domain": "research",
        "is_routable": True,
        "intent_patterns": [
            "research",
            "search",
            "find_information",
            "look_up",
            "compare",
            "review",
        ],
        "capabilities": ["web_search", "summarize", "compare_options"],
        "tools_enabled": ["web_search"],
        "model_tier": "standard",
    },
]


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

    created_agents = 0
    created_configs = 0
    created_prompts = 0

    async with get_session() as session:
        agent_repo = AgentRepository(session)
        config_repo = AgentConfigVersionRepository(session)
        prompt_repo = AgentPromptVersionRepository(session)

        for defn in AGENT_DEFS:
            model = _resolve_model(defn["name"], settings)
            temperature = _resolve_temperature(defn["name"], settings)

            agent = await agent_repo.create_or_update(
                name=defn["name"],
                description=defn["description"],
                status=defn["status"],
                domain=defn.get("domain"),
                is_routable=defn.get("is_routable", False),
                intent_patterns=defn.get("intent_patterns", []),
                capabilities=defn.get("capabilities", []),
            )
            created_agents += 1

            existing_config = await config_repo.get_active(agent.id)
            if not existing_config and model:
                config_kwargs: dict[str, Any] = {
                    "agent_id": agent.id,
                    "model_name": model,
                    "temperature": temperature,
                    "change_summary": "Initial seed from environment settings",
                }
                if defn.get("tools_enabled"):
                    config_kwargs["tools_enabled"] = defn["tools_enabled"]
                config = await config_repo.create_draft(**config_kwargs)
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
        "Seeded %d agents (routing metadata included), %d configs, %d prompts",
        created_agents,
        created_configs,
        created_prompts,
    )

    return {
        "agents_seeded": created_agents,
        "configs_created": created_configs,
        "prompts_created": created_prompts,
    }


_DS_AGENTS = {"data_scientist", "energy_analyst", "behavioral_analyst", "diagnostic_analyst"}
_LLM_AGENTS = {"architect", "orchestrator", "dashboard_designer", "knowledge", "food", "research"}


def _resolve_model(agent_name: str, settings: Any) -> str | None:
    """Resolve the LLM model for an agent from settings."""
    if agent_name in _DS_AGENTS:
        result: str | None = settings.data_scientist_model or settings.llm_model
        return result
    if agent_name in _LLM_AGENTS:
        return str(settings.llm_model) if settings.llm_model else None
    return None


def _resolve_temperature(agent_name: str, settings: Any) -> float | None:
    """Resolve the LLM temperature for an agent from settings."""
    if agent_name in _DS_AGENTS:
        temp: float | None = settings.data_scientist_temperature or settings.llm_temperature
        return temp
    if agent_name in _LLM_AGENTS:
        return float(settings.llm_temperature) if settings.llm_temperature is not None else None
    return None
