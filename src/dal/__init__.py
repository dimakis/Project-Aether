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
from src.dal.queries import NaturalLanguageQueryEngine, query_entities
from src.dal.services import ServiceRepository, seed_services
from src.dal.sync import DiscoverySyncService

__all__ = [
    "AgentConfigVersionRepository",
    "AgentPromptVersionRepository",
    # Agent configuration (Feature 23)
    "AgentRepository",
    "AreaRepository",
    # HA registry repositories
    "AutomationRepository",
    # Conversation repositories (US2)
    "ConversationRepository",
    "DeviceRepository",
    # Services
    "DiscoverySyncService",
    # Entity repositories
    "EntityRepository",
    # Insight repositories (US3)
    "InsightRepository",
    # Insight schedules (Feature 10)
    "InsightScheduleRepository",
    "MessageRepository",
    "NaturalLanguageQueryEngine",
    "ProposalRepository",
    "SceneRepository",
    "ScriptRepository",
    "ServiceRepository",
    "query_entities",
    "seed_services",
]
