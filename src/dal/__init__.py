"""Data Access Layer for Project Aether.

Provides a clean interface for database operations
with caching, transactions, and query optimization.
"""

from src.dal.areas import AreaRepository
from src.dal.devices import DeviceRepository
from src.dal.entities import EntityRepository
from src.dal.sync import DiscoverySyncService

__all__ = [
    "EntityRepository",
    "DeviceRepository",
    "AreaRepository",
    "DiscoverySyncService",
]
