"""Database entity models.

All SQLAlchemy ORM models for Project Aether.
"""

# Existing models
from src.storage.entities.agent import Agent
from src.storage.entities.conversation import Conversation
from src.storage.entities.message import Message

# HA Registry models (User Story 1)
from src.storage.entities.area import Area
from src.storage.entities.device import Device
from src.storage.entities.discovery_session import DiscoverySession, DiscoveryStatus
from src.storage.entities.ha_automation import HAAutomation, Scene, Script, Service
from src.storage.entities.ha_entity import HAEntity

__all__ = [
    # Existing
    "Agent",
    "Conversation",
    "Message",
    # HA Registry
    "Area",
    "Device",
    "HAEntity",
    "DiscoverySession",
    "DiscoveryStatus",
    "HAAutomation",
    "Script",
    "Scene",
    "Service",
]
