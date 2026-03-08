"""Base state definitions for LangGraph agents.

Provides Pydantic models for graph state management.
All graphs use these models to maintain typed, validated state.
"""

from .analysis import (
    AnalysisState,
    CommunicationEntry,
    ScriptExecution,
    SpecialistFinding,
    TeamAnalysis,
)
from .automation_builder import AutomationBuilderState
from .base import BaseState, MessageState
from .conversation import (
    ApprovalState,
    AutomationSuggestion,
    ConversationState,
    HITLApproval,
)
from .dashboard import DashboardState
from .discovery import DiscoveryState, EntitySummary
from .enums import (
    AgentRole,
    AnalysisDepth,
    AnalysisType,
    ApprovalDecision,
    ConversationStatus,
    DiscoveryStatus,
    ExecutionStrategy,
)
from .orchestrator import OrchestratorState
from .review import ReviewState
from .workflow import DEFAULT_WORKFLOW_PRESETS, WorkflowPreset

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
