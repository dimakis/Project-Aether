"""Database entity models.

All SQLAlchemy ORM models for Project Aether.
"""

# Analysis Reports (Feature 33: DS Deep Analysis)
# Core models
from src.storage.entities.agent import Agent
from src.storage.entities.agent_config_version import AgentConfigVersion, VersionStatus
from src.storage.entities.agent_prompt_version import AgentPromptVersion
from src.storage.entities.analysis_report import AnalysisReport, ReportStatus

# App Settings (runtime-configurable via UI)
from src.storage.entities.app_settings import AppSettings

# HA Registry models (User Story 1)
from src.storage.entities.area import Area

# Automation Proposals (User Story 2)
from src.storage.entities.automation_proposal import (
    VALID_TRANSITIONS,
    AutomationProposal,
    ProposalStatus,
    ProposalType,
)
from src.storage.entities.conversation import Conversation, ConversationStatus
from src.storage.entities.device import Device
from src.storage.entities.discovery_session import DiscoverySession, DiscoveryStatus
from src.storage.entities.ha_automation import HAAutomation, Scene, Script, Service
from src.storage.entities.ha_entity import HAEntity

# HA Zones (multi-server support)
from src.storage.entities.ha_zone import HAZone

# Insights (User Story 3)
from src.storage.entities.insight import Insight, InsightStatus, InsightType

# Insight Schedules (Feature 10)
from src.storage.entities.insight_schedule import InsightSchedule, TriggerType

# LLM Usage Tracking
from src.storage.entities.llm_usage import LLMUsage
from src.storage.entities.message import Message

# Model Ratings
from src.storage.entities.model_rating import ModelRating

# Authentication
from src.storage.entities.passkey_credential import PasskeyCredential

# System Configuration
from src.storage.entities.system_config import SystemConfig

# Tool Groups (Feature 34: Dynamic Tool Registry)
from src.storage.entities.tool_group import ToolGroup

# User Profiles
from src.storage.entities.user_profile import UserProfile

# Workflow Definitions (Feature 29)
from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

__all__ = [
    "VALID_TRANSITIONS",
    "Agent",
    "AgentConfigVersion",
    "AgentPromptVersion",
    "AnalysisReport",
    "AppSettings",
    "Area",
    "AutomationProposal",
    "Conversation",
    "ConversationStatus",
    "Device",
    "DiscoverySession",
    "DiscoveryStatus",
    "HAAutomation",
    "HAEntity",
    "HAZone",
    "Insight",
    "InsightSchedule",
    "InsightStatus",
    "InsightType",
    "LLMUsage",
    "Message",
    "ModelRating",
    "PasskeyCredential",
    "ProposalStatus",
    "ProposalType",
    "ReportStatus",
    "Scene",
    "Script",
    "Service",
    "SystemConfig",
    "ToolGroup",
    "TriggerType",
    "UserProfile",
    "VersionStatus",
    "WorkflowDefinitionEntity",
]
