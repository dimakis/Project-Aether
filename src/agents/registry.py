"""Agent registry and runtime-configurable agent factory.

Provides name-to-class mapping for all known agents and a factory
function that instantiates agents from DB-backed ``AgentRuntimeConfig``.

Built agents automatically:
- Use the DB-backed prompt (or fall back to file-based)
- Resolve model and temperature via the Feature 23 priority chain
- Bind the correct tool set via ``get_tools_for_agent()``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.agents.base import BaseAgent
    from src.agents.config_cache import AgentRuntimeConfig

logger = logging.getLogger(__name__)

AGENT_REGISTRY: dict[str, str] = {
    "architect": "src.agents.architect.ArchitectAgent",
    "developer": "src.agents.developer.DeveloperAgent",
    "librarian": "src.agents.librarian.LibrarianAgent",
    "dashboard_designer": "src.agents.dashboard_designer.DashboardDesignerAgent",
    "orchestrator": "src.agents.orchestrator.OrchestratorAgent",
    "energy_analyst": "src.agents.energy_analyst.EnergyAnalyst",
    "behavioral_analyst": "src.agents.behavioral_analyst.BehavioralAnalyst",
    "diagnostic_analyst": "src.agents.diagnostic_analyst.DiagnosticAnalyst",
    "data_scientist": "src.agents.data_scientist.DataScientistAgent",
    "knowledge": "src.agents.knowledge.KnowledgeAgent",
}


def get_agent_class(agent_name: str) -> type[BaseAgent] | None:
    """Import and return the agent class for the given name.

    Returns None if the agent name is unknown or the import fails.
    """
    dotted_path = AGENT_REGISTRY.get(agent_name)
    if not dotted_path:
        logger.warning("Unknown agent name: %s", agent_name)
        return None

    try:
        import importlib

        module_path, class_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls: type[BaseAgent] = getattr(module, class_name)
        return cls
    except (ImportError, AttributeError) as exc:
        logger.warning("Failed to import agent class for %s: %s", agent_name, exc)
        return None


async def create_agent_from_config(
    agent_name: str,
    config: AgentRuntimeConfig | None = None,
    **overrides: Any,
) -> BaseAgent | None:
    """Create an agent instance using DB-backed runtime config.

    Resolves model, temperature, prompt, and tools from the config,
    applying the Feature 23 priority chain (user context > DB > env > default).

    Args:
        agent_name: Agent identifier (e.g. ``"architect"``).
        config: Pre-fetched runtime config.  If None, will be loaded.
        **overrides: Keyword args forwarded to the agent constructor
            (e.g. ``model_name``, ``temperature``).

    Returns:
        Configured agent instance, or None if the agent class is not found.
    """
    from src.agents.config_cache import get_agent_runtime_config
    from src.agents.model_context import resolve_model
    from src.agents.prompts import load_prompt_for_agent
    from src.tools.registry import get_tools_for_agent

    if config is None:
        config = await get_agent_runtime_config(agent_name)

    db_model = config.model_name if config else None
    db_temperature = config.temperature if config else None
    db_prompt = config.prompt_template if config else None
    tools_enabled = config.tools_enabled if config else None

    model_name, temperature = resolve_model(
        db_model=db_model,
        db_temperature=db_temperature,
        agent_model=overrides.pop("model_name", None),
        agent_temperature=overrides.pop("temperature", None),
    )

    try:
        prompt = load_prompt_for_agent(agent_name, db_prompt=db_prompt)
    except FileNotFoundError:
        prompt = None

    tools = get_tools_for_agent(agent_name, tools_enabled=tools_enabled)

    cls = get_agent_class(agent_name)
    if cls is None:
        return None

    init_kwargs: dict[str, Any] = {}
    if model_name:
        init_kwargs["model_name"] = model_name
    if temperature is not None:
        init_kwargs["temperature"] = temperature
    init_kwargs.update(overrides)

    agent = cls(**init_kwargs)

    agent._runtime_prompt = prompt  # type: ignore[attr-defined]
    agent._runtime_tools = tools  # type: ignore[attr-defined]
    agent._runtime_config = config  # type: ignore[attr-defined]

    return agent
