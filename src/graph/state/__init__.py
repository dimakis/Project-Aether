"""Base state definitions for LangGraph agents.

Provides Pydantic models for graph state management.
All graphs use these models to maintain typed, validated state.

Uses lazy imports to avoid loading all state models at import time.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    # analysis
    "AnalysisState": "src.graph.state.analysis",
    "CommunicationEntry": "src.graph.state.analysis",
    "ScriptExecution": "src.graph.state.analysis",
    "SpecialistFinding": "src.graph.state.analysis",
    "TeamAnalysis": "src.graph.state.analysis",
    # automation_builder
    "AutomationBuilderState": "src.graph.state.automation_builder",
    # base
    "BaseState": "src.graph.state.base",
    "MessageState": "src.graph.state.base",
    # conversation
    "ApprovalState": "src.graph.state.conversation",
    "AutomationSuggestion": "src.graph.state.conversation",
    "ConversationState": "src.graph.state.conversation",
    "HITLApproval": "src.graph.state.conversation",
    # dashboard
    "DashboardState": "src.graph.state.dashboard",
    # discovery
    "DiscoveryState": "src.graph.state.discovery",
    "EntitySummary": "src.graph.state.discovery",
    # enums
    "AgentRole": "src.graph.state.enums",
    "AnalysisDepth": "src.graph.state.enums",
    "AnalysisType": "src.graph.state.enums",
    "ApprovalDecision": "src.graph.state.enums",
    "ConversationStatus": "src.graph.state.enums",
    "DiscoveryStatus": "src.graph.state.enums",
    "ExecutionStrategy": "src.graph.state.enums",
    # orchestrator
    "OrchestratorState": "src.graph.state.orchestrator",
    # review
    "ReviewState": "src.graph.state.review",
    # workflow
    "DEFAULT_WORKFLOW_PRESETS": "src.graph.state.workflow",
    "WorkflowPreset": "src.graph.state.workflow",
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

    raise AttributeError(f"module 'src.graph.state' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
    from src.graph.state.analysis import (
        AnalysisState,
        CommunicationEntry,
        ScriptExecution,
        SpecialistFinding,
        TeamAnalysis,
    )
    from src.graph.state.automation_builder import AutomationBuilderState
    from src.graph.state.base import BaseState, MessageState
    from src.graph.state.conversation import (
        ApprovalState,
        AutomationSuggestion,
        ConversationState,
        HITLApproval,
    )
    from src.graph.state.dashboard import DashboardState
    from src.graph.state.discovery import DiscoveryState, EntitySummary
    from src.graph.state.enums import (
        AgentRole,
        AnalysisDepth,
        AnalysisType,
        ApprovalDecision,
        ConversationStatus,
        DiscoveryStatus,
        ExecutionStrategy,
    )
    from src.graph.state.orchestrator import OrchestratorState
    from src.graph.state.review import ReviewState
    from src.graph.state.workflow import DEFAULT_WORKFLOW_PRESETS, WorkflowPreset

__all__ = [
    "DEFAULT_WORKFLOW_PRESETS",
    "AgentRole",
    "AnalysisDepth",
    "AnalysisState",
    "AnalysisType",
    "ApprovalDecision",
    "ApprovalState",
    "AutomationBuilderState",
    "AutomationSuggestion",
    "BaseState",
    "CommunicationEntry",
    "ConversationState",
    "ConversationStatus",
    "DashboardState",
    "DiscoveryState",
    "DiscoveryStatus",
    "EntitySummary",
    "ExecutionStrategy",
    "HITLApproval",
    "MessageState",
    "OrchestratorState",
    "ReviewState",
    "ScriptExecution",
    "SpecialistFinding",
    "TeamAnalysis",
    "WorkflowPreset",
]
