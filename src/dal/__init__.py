"""Data Access Layer for Project Aether.

Provides a clean interface for database operations
with caching, transactions, and query optimization.

Uses lazy imports to avoid loading all repositories at import time.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    # agents
    "AgentConfigVersionRepository": "src.dal.agents",
    "AgentPromptVersionRepository": "src.dal.agents",
    "AgentRepository": "src.dal.agents",
    # areas
    "AreaRepository": "src.dal.areas",
    # automations
    "AutomationRepository": "src.dal.automations",
    "SceneRepository": "src.dal.automations",
    "ScriptRepository": "src.dal.automations",
    # conversations
    "ConversationRepository": "src.dal.conversations",
    "MessageRepository": "src.dal.conversations",
    "ProposalRepository": "src.dal.conversations",
    # devices
    "DeviceRepository": "src.dal.devices",
    # entities
    "EntityRepository": "src.dal.entities",
    # insight_schedules
    "InsightScheduleRepository": "src.dal.insight_schedules",
    # insights
    "InsightRepository": "src.dal.insights",
    # optimization
    "AutomationSuggestionRepository": "src.dal.optimization",
    "OptimizationJobRepository": "src.dal.optimization",
    # queries
    "NaturalLanguageQueryEngine": "src.dal.queries",
    "query_entities": "src.dal.queries",
    # services
    "ServiceRepository": "src.dal.services",
    "seed_services": "src.dal.services",
    # sync
    "DiscoverySyncService": "src.dal.sync",
    # tool_groups
    "ToolGroupRepository": "src.dal.tool_groups",
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

    raise AttributeError(f"module 'src.dal' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
    from src.dal.agents import (
        AgentConfigVersionRepository,
        AgentPromptVersionRepository,
        AgentRepository,
    )
    from src.dal.areas import AreaRepository
    from src.dal.automations import AutomationRepository, SceneRepository, ScriptRepository
    from src.dal.conversations import (
        ConversationRepository,
        MessageRepository,
        ProposalRepository,
    )
    from src.dal.devices import DeviceRepository
    from src.dal.entities import EntityRepository
    from src.dal.insight_schedules import InsightScheduleRepository
    from src.dal.insights import InsightRepository
    from src.dal.optimization import (
        AutomationSuggestionRepository,
        OptimizationJobRepository,
    )
    from src.dal.queries import NaturalLanguageQueryEngine, query_entities
    from src.dal.services import ServiceRepository, seed_services
    from src.dal.sync import DiscoverySyncService
    from src.dal.tool_groups import ToolGroupRepository

__all__ = [
    "AgentConfigVersionRepository",
    "AgentPromptVersionRepository",
    "AgentRepository",
    "AreaRepository",
    "AutomationRepository",
    "AutomationSuggestionRepository",
    "ConversationRepository",
    "DeviceRepository",
    "DiscoverySyncService",
    "EntityRepository",
    "InsightRepository",
    "InsightScheduleRepository",
    "MessageRepository",
    "NaturalLanguageQueryEngine",
    "OptimizationJobRepository",
    "ProposalRepository",
    "SceneRepository",
    "ScriptRepository",
    "ServiceRepository",
    "ToolGroupRepository",
    "query_entities",
    "seed_services",
]
