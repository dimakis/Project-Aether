"""Dual-mode agent invocation (Phase 3).

Resolves whether to invoke an agent locally (in-process) or remotely
(via A2A service) based on the ``DEPLOYMENT_MODE`` setting.

In monolith mode, agents are instantiated directly.
In distributed mode, the ``A2ARemoteClient`` is used to call the
remote service.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from src.graph.state import BaseState

logger = logging.getLogger(__name__)

_AGENT_CLASS_MAP: dict[str, str] = {
    "architect": "src.agents.architect.ArchitectAgent",
    "energy_analyst": "src.agents.energy_analyst.EnergyAnalyst",
    "behavioral_analyst": "src.agents.behavioral_analyst.BehavioralAnalyst",
    "diagnostic_analyst": "src.agents.diagnostic_analyst.DiagnosticAnalyst",
    "data_scientist": "src.agents.data_scientist.DataScientistAgent",
}

_DISTRIBUTED_AGENTS = frozenset(_AGENT_CLASS_MAP.keys())

_AGENT_URL_MAP: dict[str, str] = {
    "architect": "architect_service_url",
    "data_scientist": "ds_orchestrator_url",
    "energy_analyst": "ds_analysts_url",
    "behavioral_analyst": "ds_analysts_url",
    "diagnostic_analyst": "ds_analysts_url",
}


@dataclass
class AgentInvoker:
    """Dispatches agent calls in either local or remote mode."""

    mode: Literal["local", "remote"]
    agent_cls: type | None = None
    service_url: str | None = None

    async def invoke(self, state: BaseState, **kwargs: Any) -> dict[str, Any]:
        """Invoke the agent, dispatching based on mode."""
        if self.mode == "remote" and self.service_url:
            return await self._invoke_remote(state, **kwargs)
        return await self._invoke_local(state, **kwargs)

    async def _invoke_local(self, state: BaseState, **kwargs: Any) -> dict[str, Any]:
        """Instantiate the agent in-process and invoke."""
        if self.agent_cls is None:
            return {}
        agent = self.agent_cls()
        result: dict[str, Any] = await agent.invoke(state, **kwargs)
        return result

    async def _invoke_remote(self, state: BaseState, **kwargs: Any) -> dict[str, Any]:
        """Call the remote A2A service."""
        from src.agents.a2a_client import A2ARemoteClient

        client = A2ARemoteClient(base_url=self.service_url or "")
        return await client.invoke(state)


def _import_class(dotted_path: str) -> type | None:
    """Import a class from a whitelisted dotted module path.

    Only paths present in ``_AGENT_CLASS_MAP`` are allowed.
    Returns None on import failure instead of crashing.
    """
    if dotted_path not in _AGENT_CLASS_MAP.values():
        logger.warning("Import path %r not in agent class whitelist", dotted_path)
        return None
    try:
        import importlib

        module_path, class_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls: type = getattr(module, class_name)
        return cls
    except (ImportError, AttributeError) as e:
        logger.warning("Failed to import agent class %r: %s", dotted_path, e)
        return None


def resolve_agent_invoker(agent_name: str) -> AgentInvoker:
    """Resolve an AgentInvoker based on deployment mode and agent name.

    Args:
        agent_name: Agent identifier (e.g., 'energy_analyst').

    Returns:
        AgentInvoker configured for local or remote invocation.
    """
    from src.settings import get_settings

    settings = get_settings()

    if settings.deployment_mode == "distributed" and agent_name in _DISTRIBUTED_AGENTS:
        url_attr = _AGENT_URL_MAP.get(agent_name)
        service_url = getattr(settings, url_attr, None) if url_attr else None
        if service_url:
            return AgentInvoker(
                mode="remote",
                service_url=service_url,
            )

    cls_path = _AGENT_CLASS_MAP.get(agent_name)
    agent_cls = _import_class(cls_path) if cls_path else None

    return AgentInvoker(
        mode="local",
        agent_cls=agent_cls,
    )
