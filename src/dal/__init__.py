"""Data Access Layer for Project Aether.

Provides a clean interface for database operations
with caching, transactions, and query optimization.
"""

from src.dal.areas import AreaRepository
from src.dal.automations import AutomationRepository, SceneRepository, ScriptRepository
from src.dal.conversations import (
    ConversationRepository,
    MessageRepository,
    ProposalRepository,
)
from src.dal.devices import DeviceRepository
from src.dal.entities import EntityRepository
from src.dal.insights import InsightRepository
from src.dal.insight_schedules import InsightScheduleRepository
from src.dal.queries import NaturalLanguageQueryEngine, query_entities
from src.dal.services import ServiceRepository, seed_services
from src.dal.sync import DiscoverySyncService

__all__ = [
    # Entity repositories
    "EntityRepository",
    "DeviceRepository",
    "AreaRepository",
    # HA registry repositories
    "AutomationRepository",
    "ScriptRepository",
    "SceneRepository",
    "ServiceRepository",
    # Conversation repositories (US2)
    "ConversationRepository",
    "MessageRepository",
    "ProposalRepository",
    # Insight repositories (US3)
    "InsightRepository",
    # Insight schedules (Feature 10)
    "InsightScheduleRepository",
    # Services
    "DiscoverySyncService",
    "NaturalLanguageQueryEngine",
    "query_entities",
    "seed_services",
]
