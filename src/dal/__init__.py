"""Data Access Layer for Project Aether.

Provides a clean interface for database operations
with caching, transactions, and query optimization.
"""

from src.dal.areas import AreaRepository
from src.dal.automations import AutomationRepository, SceneRepository, ScriptRepository
from src.dal.devices import DeviceRepository
from src.dal.entities import EntityRepository
from src.dal.queries import NaturalLanguageQueryEngine, query_entities
from src.dal.services import ServiceRepository, seed_services
from src.dal.sync import DiscoverySyncService

__all__ = [
    "EntityRepository",
    "DeviceRepository",
    "AreaRepository",
    "AutomationRepository",
    "ScriptRepository",
    "SceneRepository",
    "ServiceRepository",
    "DiscoverySyncService",
    "NaturalLanguageQueryEngine",
    "query_entities",
    "seed_services",
]
