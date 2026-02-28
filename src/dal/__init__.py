"""Data Access Layer for Project Aether.

Provides a clean interface for database operations
with caching, transactions, and query optimization.
"""

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
