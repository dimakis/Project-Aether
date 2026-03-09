"""Database entity models.

All SQLAlchemy ORM models for Project Aether.

Uses lazy imports to avoid loading all entity models at import time.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    "Agent": "src.storage.entities.agent",
    "AgentConfigVersion": "src.storage.entities.agent_config_version",
    "VersionStatus": "src.storage.entities.agent_config_version",
    "AgentPromptVersion": "src.storage.entities.agent_prompt_version",
    "AnalysisReport": "src.storage.entities.analysis_report",
    "ReportStatus": "src.storage.entities.analysis_report",
    "AppSettings": "src.storage.entities.app_settings",
    "Area": "src.storage.entities.area",
    "VALID_TRANSITIONS": "src.storage.entities.automation_proposal",
    "AutomationProposal": "src.storage.entities.automation_proposal",
    "ProposalStatus": "src.storage.entities.automation_proposal",
    "ProposalType": "src.storage.entities.automation_proposal",
    "AutomationSuggestionEntity": "src.storage.entities.automation_suggestion",
    "SuggestionStatus": "src.storage.entities.automation_suggestion",
    "Conversation": "src.storage.entities.conversation",
    "ConversationStatus": "src.storage.entities.conversation",
    "Device": "src.storage.entities.device",
    "DiscoverySession": "src.storage.entities.discovery_session",
    "DiscoveryStatus": "src.storage.entities.discovery_session",
    "HAAutomation": "src.storage.entities.ha_automation",
    "Scene": "src.storage.entities.ha_automation",
    "Script": "src.storage.entities.ha_automation",
    "Service": "src.storage.entities.ha_automation",
    "HAEntity": "src.storage.entities.ha_entity",
    "HAZone": "src.storage.entities.ha_zone",
    "Insight": "src.storage.entities.insight",
    "InsightImpact": "src.storage.entities.insight",
    "InsightStatus": "src.storage.entities.insight",
    "InsightType": "src.storage.entities.insight",
    "InsightSchedule": "src.storage.entities.insight_schedule",
    "TriggerType": "src.storage.entities.insight_schedule",
    "LLMUsage": "src.storage.entities.llm_usage",
    "Message": "src.storage.entities.message",
    "ModelRating": "src.storage.entities.model_rating",
    "JobStatus": "src.storage.entities.optimization_job",
    "OptimizationJob": "src.storage.entities.optimization_job",
    "PasskeyCredential": "src.storage.entities.passkey_credential",
    "SystemConfig": "src.storage.entities.system_config",
    "ToolGroup": "src.storage.entities.tool_group",
    "UserProfile": "src.storage.entities.user_profile",
    "WorkflowDefinitionEntity": "src.storage.entities.workflow_definition",
}

_cache: dict[str, Any] = {}
_bootstrapped = False


def _bootstrap_all() -> None:
    """Load all entity modules so SQLAlchemy mappers can resolve relationships."""
    global _bootstrapped
    if _bootstrapped:
        return
    from importlib import import_module

    # Load in dependency order: Agent first (referenced by Conversation, etc.)
    ordered = [
        "src.storage.entities.agent",
        "src.storage.entities.area",
        "src.storage.entities.device",
        "src.storage.entities.conversation",
        "src.storage.entities.message",
        "src.storage.entities.automation_proposal",
    ]
    remaining = set(_EXPORTS.values()) - set(ordered)
    for module_path in [*ordered, *sorted(remaining)]:
        import_module(module_path)
    _bootstrapped = True


def __getattr__(name: str) -> Any:
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]
    if name in _EXPORTS:
        _bootstrap_all()  # Ensure all entities loaded for SQLAlchemy relationship resolution
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr
    raise AttributeError(f"module 'src.storage.entities' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
    from src.storage.entities.agent import Agent
    from src.storage.entities.agent_config_version import AgentConfigVersion, VersionStatus
    from src.storage.entities.agent_prompt_version import AgentPromptVersion
    from src.storage.entities.analysis_report import AnalysisReport, ReportStatus
    from src.storage.entities.app_settings import AppSettings
    from src.storage.entities.area import Area
    from src.storage.entities.automation_proposal import (
        VALID_TRANSITIONS,
        AutomationProposal,
        ProposalStatus,
        ProposalType,
    )
    from src.storage.entities.automation_suggestion import (
        AutomationSuggestionEntity,
        SuggestionStatus,
    )
    from src.storage.entities.conversation import Conversation, ConversationStatus
    from src.storage.entities.device import Device
    from src.storage.entities.discovery_session import DiscoverySession, DiscoveryStatus
    from src.storage.entities.ha_automation import HAAutomation, Scene, Script, Service
    from src.storage.entities.ha_entity import HAEntity
    from src.storage.entities.ha_zone import HAZone
    from src.storage.entities.insight import (
        Insight,
        InsightImpact,
        InsightStatus,
        InsightType,
    )
    from src.storage.entities.insight_schedule import InsightSchedule, TriggerType
    from src.storage.entities.llm_usage import LLMUsage
    from src.storage.entities.message import Message
    from src.storage.entities.model_rating import ModelRating
    from src.storage.entities.optimization_job import JobStatus, OptimizationJob
    from src.storage.entities.passkey_credential import PasskeyCredential
    from src.storage.entities.system_config import SystemConfig
    from src.storage.entities.tool_group import ToolGroup
    from src.storage.entities.user_profile import UserProfile
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
    "AutomationSuggestionEntity",
    "Conversation",
    "ConversationStatus",
    "Device",
    "DiscoverySession",
    "DiscoveryStatus",
    "HAAutomation",
    "HAEntity",
    "HAZone",
    "Insight",
    "InsightImpact",
    "InsightSchedule",
    "InsightStatus",
    "InsightType",
    "JobStatus",
    "LLMUsage",
    "Message",
    "ModelRating",
    "OptimizationJob",
    "PasskeyCredential",
    "ProposalStatus",
    "ProposalType",
    "ReportStatus",
    "Scene",
    "Script",
    "Service",
    "SuggestionStatus",
    "SystemConfig",
    "ToolGroup",
    "TriggerType",
    "UserProfile",
    "VersionStatus",
    "WorkflowDefinitionEntity",
]
