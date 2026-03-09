"""Agent base classes and concrete agent implementations.

All agent classes are re-exported here for backward compatibility.
Canonical definitions live in their own modules:
- base.py: BaseAgent, AgentContext
- librarian.py: LibrarianAgent
- architect/: ArchitectAgent, ArchitectWorkflow, StreamEvent
- data_scientist/: DataScientistAgent, DataScientistWorkflow
- developer.py: DeveloperAgent, DeveloperWorkflow
- dashboard_designer.py: DashboardDesignerAgent
- behavioral_analyst.py: BehavioralAnalyst
- diagnostic_analyst.py: DiagnosticAnalyst
- energy_analyst.py: EnergyAnalyst

Uses lazy imports to avoid pulling in the full tool/graph/tracing
dependency graph when only a subset of agents is needed.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    # a2a_client
    "A2AClientError": "src.agents.a2a_client",
    "A2ARemoteClient": "src.agents.a2a_client",
    # a2a_service
    "create_a2a_service": "src.agents.a2a_service",
    # architect
    "ArchitectAgent": "src.agents.architect",
    "ArchitectWorkflow": "src.agents.architect",
    "StreamEvent": "src.agents.architect",
    # base
    "AgentContext": "src.agents.base",
    "BaseAgent": "src.agents.base",
    # behavioral_analyst
    "BehavioralAnalyst": "src.agents.behavioral_analyst",
    # dashboard_designer
    "DashboardDesignerAgent": "src.agents.dashboard_designer",
    # data_scientist
    "DataScientistAgent": "src.agents.data_scientist",
    "DataScientistWorkflow": "src.agents.data_scientist",
    # developer
    "DeveloperAgent": "src.agents.developer",
    "DeveloperWorkflow": "src.agents.developer",
    # diagnostic_analyst
    "DiagnosticAnalyst": "src.agents.diagnostic_analyst",
    # dual_mode
    "AgentInvoker": "src.agents.dual_mode",
    "resolve_agent_invoker": "src.agents.dual_mode",
    # energy_analyst
    "EnergyAnalyst": "src.agents.energy_analyst",
    # execution_context
    "emit_progress": "src.agents.execution_context",
    # knowledge
    "KnowledgeAgent": "src.agents.knowledge",
    # librarian
    "LibrarianAgent": "src.agents.librarian",
    # orchestrator
    "OrchestratorAgent": "src.agents.orchestrator",
    # registry
    "AGENT_REGISTRY": "src.agents.registry",
    "create_agent_from_config": "src.agents.registry",
    "get_agent_class": "src.agents.registry",
    # re-exports from other packages
    "AgentRole": "src.graph.state",
    "BaseState": "src.graph.state",
    "add_span_event": "src.tracing",
    "get_active_span": "src.tracing",
    "log_dict": "src.tracing",
    "log_param": "src.tracing",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]

    if name in _EXPORTS:
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr

    raise AttributeError(f"module 'src.agents' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
    from src.agents.a2a_client import A2AClientError, A2ARemoteClient
    from src.agents.a2a_service import create_a2a_service
    from src.agents.architect import ArchitectAgent, ArchitectWorkflow, StreamEvent
    from src.agents.base import AgentContext, BaseAgent
    from src.agents.behavioral_analyst import BehavioralAnalyst
    from src.agents.dashboard_designer import DashboardDesignerAgent
    from src.agents.data_scientist import DataScientistAgent, DataScientistWorkflow
    from src.agents.developer import DeveloperAgent, DeveloperWorkflow
    from src.agents.diagnostic_analyst import DiagnosticAnalyst
    from src.agents.dual_mode import AgentInvoker, resolve_agent_invoker
    from src.agents.energy_analyst import EnergyAnalyst
    from src.agents.execution_context import emit_progress
    from src.agents.knowledge import KnowledgeAgent
    from src.agents.librarian import LibrarianAgent
    from src.agents.orchestrator import OrchestratorAgent
    from src.agents.registry import AGENT_REGISTRY, create_agent_from_config, get_agent_class
    from src.graph.state import AgentRole, BaseState
    from src.tracing import add_span_event, get_active_span, log_dict, log_param

__all__ = [
    "AGENT_REGISTRY",
    "A2AClientError",
    "A2ARemoteClient",
    "AgentContext",
    "AgentInvoker",
    "AgentRole",
    "ArchitectAgent",
    "ArchitectWorkflow",
    "BaseAgent",
    "BaseState",
    "BehavioralAnalyst",
    "DashboardDesignerAgent",
    "DataScientistAgent",
    "DataScientistWorkflow",
    "DeveloperAgent",
    "DeveloperWorkflow",
    "DiagnosticAnalyst",
    "EnergyAnalyst",
    "KnowledgeAgent",
    "LibrarianAgent",
    "OrchestratorAgent",
    "StreamEvent",
    "add_span_event",
    "create_a2a_service",
    "create_agent_from_config",
    "emit_progress",
    "get_active_span",
    "get_agent_class",
    "log_dict",
    "log_param",
    "resolve_agent_invoker",
]
