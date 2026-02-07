"""Database entity models.

All SQLAlchemy ORM models for Project Aether.
"""

# Core models
from src.storage.entities.agent import Agent
from src.storage.entities.conversation import Conversation, ConversationStatus
from src.storage.entities.message import Message

# HA Registry models (User Story 1)
from src.storage.entities.area import Area
from src.storage.entities.device import Device
from src.storage.entities.discovery_session import DiscoverySession, DiscoveryStatus
from src.storage.entities.ha_automation import HAAutomation, Scene, Script, Service
from src.storage.entities.ha_entity import HAEntity

# Automation Proposals (User Story 2)
from src.storage.entities.automation_proposal import (
    AutomationProposal,
    ProposalStatus,
    VALID_TRANSITIONS,
)

# Insights (User Story 3)
from src.storage.entities.insight import Insight, InsightStatus, InsightType

# Insight Schedules (Feature 10)
from src.storage.entities.insight_schedule import InsightSchedule, TriggerType

__all__ = [
    # Core
    "Agent",
    "Conversation",
    "ConversationStatus",
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
    # Automation Proposals
    "AutomationProposal",
    "ProposalStatus",
    "VALID_TRANSITIONS",
    # Insights
    "Insight",
    "InsightType",
    "InsightStatus",
    # Insight Schedules (Feature 10)
    "InsightSchedule",
    "TriggerType",
]
