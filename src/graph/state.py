"""Base state definitions for LangGraph agents.

Provides Pydantic models for graph state management.
All graphs use these models to maintain typed, validated state.
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class AgentRole(StrEnum):
    """Agent roles in the system."""

    LIBRARIAN = "librarian"
    CATEGORIZER = "categorizer"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    DATA_SCIENTIST = "data_scientist"
    ORCHESTRATOR = "orchestrator"


class ConversationStatus(StrEnum):
    """Status of a conversation session."""

    ACTIVE = "active"
    WAITING_APPROVAL = "waiting_approval"  # HITL (Constitution: Safety First)
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveryStatus(StrEnum):
    """Status of an entity discovery session."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# BASE STATE MODELS
# =============================================================================


class BaseState(BaseModel):
    """Base state model with common fields.

    All graph states should inherit from this to ensure
    consistent tracing and identification.
    """

    run_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this graph run",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this graph run started",
    )
    current_agent: AgentRole | None = Field(
        default=None,
        description="Currently active agent (for tracing)",
    )


class MessageState(BaseState):
    """State model with message history.

    Uses LangGraph's add_messages reducer for proper message handling.
    """

    messages: Annotated[list[AnyMessage], add_messages] = Field(
        default_factory=list,
        description="Conversation message history",
    )


# =============================================================================
# DISCOVERY STATE (User Story 1: Librarian Agent)
# =============================================================================


class EntitySummary(BaseModel):
    """Summary of a discovered entity."""

    entity_id: str
    domain: str
    name: str
    state: str
    area_id: str | None = None
    device_id: str | None = None


class DiscoveryState(MessageState):
    """State for entity discovery workflow.

    Used by the Librarian agent during HA entity discovery.
    """

    status: DiscoveryStatus = DiscoveryStatus.RUNNING
    mlflow_run_id: str | None = None

    # Discovery progress
    domains_to_scan: list[str] = Field(default_factory=list)
    domains_scanned: list[str] = Field(default_factory=list)

    # Results
    entities_found: list[EntitySummary] = Field(default_factory=list)
    entities_added: int = 0
    entities_updated: int = 0
    entities_removed: int = 0
    devices_found: int = 0
    areas_found: int = 0
    services_found: int = 0

    # Errors
    errors: list[str] = Field(default_factory=list)

    # Self-healing: detected changes since last discovery
    entity_changes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Changes detected since last sync",
    )


# =============================================================================
# CONVERSATION STATE (User Story 2: Architect Interaction)
# =============================================================================


class HITLApproval(BaseModel):
    """Human-in-the-loop approval request (Constitution: Safety First)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    request_type: str  # "automation", "script", "scene"
    description: str
    yaml_content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved: bool | None = None  # None = pending
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None


class ApprovalDecision(StrEnum):
    """User decision for HITL approval."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalState(BaseModel):
    """State for HITL approval workflow.

    Tracks the approval decision for a proposal, including
    who made the decision and when.

    Constitution: Safety First - All automations require explicit
    human approval before deployment.
    """

    proposal_id: str = Field(description="ID of the proposal being approved")
    proposal_name: str = Field(description="Name of the automation for display")
    proposal_yaml: str = Field(description="YAML content for review")
    user_decision: ApprovalDecision = Field(
        default=ApprovalDecision.PENDING,
        description="Current approval status",
    )
    decided_by: str | None = Field(
        default=None,
        description="Who made the decision (user ID)",
    )
    decided_at: datetime | None = Field(
        default=None,
        description="When the decision was made",
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Why the proposal was rejected (if applicable)",
    )
    comment: str | None = Field(
        default=None,
        description="Optional comment from approver",
    )

    def approve(self, approved_by: str, comment: str | None = None) -> None:
        """Approve the proposal.

        Args:
            approved_by: Who approved
            comment: Optional comment
        """
        self.user_decision = ApprovalDecision.APPROVED
        self.decided_by = approved_by
        self.decided_at = datetime.now(timezone.utc)
        self.comment = comment

    def reject(self, rejected_by: str, reason: str) -> None:
        """Reject the proposal.

        Args:
            rejected_by: Who rejected
            reason: Why it was rejected
        """
        self.user_decision = ApprovalDecision.REJECTED
        self.decided_by = rejected_by
        self.decided_at = datetime.now(timezone.utc)
        self.rejection_reason = reason

    @property
    def is_pending(self) -> bool:
        """Check if still pending."""
        return self.user_decision == ApprovalDecision.PENDING

    @property
    def is_approved(self) -> bool:
        """Check if approved."""
        return self.user_decision == ApprovalDecision.APPROVED

    @property
    def is_rejected(self) -> bool:
        """Check if rejected."""
        return self.user_decision == ApprovalDecision.REJECTED


class ConversationState(MessageState):
    """State for user-agent conversation.

    Manages the flow between user and Architect/Developer agents.
    """

    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    status: ConversationStatus = ConversationStatus.ACTIVE

    # User context
    user_intent: str | None = None
    entities_mentioned: list[str] = Field(default_factory=list)
    areas_mentioned: list[str] = Field(default_factory=list)

    # Agent outputs
    categorizer_output: dict[str, Any] | None = None
    architect_design: dict[str, Any] | None = None
    developer_code: str | None = None

    # HITL approval queue (Constitution: Safety First)
    pending_approvals: list[HITLApproval] = Field(default_factory=list)
    approved_items: list[str] = Field(default_factory=list)
    rejected_items: list[str] = Field(default_factory=list)

    # Trace context — populated by @mlflow.trace() wrapper for frontend activity panel
    last_trace_id: str | None = None


# =============================================================================
# ANALYSIS STATE (User Story 3 & 4: Data Scientist)
# =============================================================================


class AnalysisType(StrEnum):
    """Types of analysis the Data Scientist can perform."""

    ENERGY_OPTIMIZATION = "energy_optimization"
    USAGE_PATTERNS = "usage_patterns"
    ANOMALY_DETECTION = "anomaly_detection"
    DASHBOARD_GENERATION = "dashboard_generation"
    DIAGNOSTIC = "diagnostic"
    CUSTOM = "custom"
    # Feature 03: Intelligent Optimization
    BEHAVIOR_ANALYSIS = "behavior_analysis"
    AUTOMATION_ANALYSIS = "automation_analysis"
    AUTOMATION_GAP_DETECTION = "automation_gap_detection"
    CORRELATION_DISCOVERY = "correlation_discovery"
    DEVICE_HEALTH = "device_health"
    COST_OPTIMIZATION = "cost_optimization"


class AutomationSuggestion(BaseModel):
    """Structured automation suggestion from the Data Scientist.

    When the DS detects a high-confidence, high-impact pattern that could
    be addressed by a Home Assistant automation, it creates this model
    for the Architect to review and refine into a full proposal.

    Feature 03: Intelligent Optimization — replaces plain string suggestion.
    """

    pattern: str = Field(
        description="Description of the detected pattern or gap",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Entity IDs involved in the pattern",
    )
    proposed_trigger: str = Field(
        default="",
        description="Suggested trigger for the automation (e.g., 'time: 22:00')",
    )
    proposed_action: str = Field(
        default="",
        description="Suggested action (e.g., 'turn off lights in living room')",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting data from the analysis",
    )
    source_insight_type: str = Field(
        default="",
        description="InsightType that generated this suggestion",
    )


class ScriptExecution(BaseModel):
    """Record of a sandboxed script execution (Constitution: Isolation)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    script_content: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    sandbox_policy: str = "default"  # gVisor policy used
    timed_out: bool = False


class AnalysisState(MessageState):
    """State for data analysis workflow.

    Used by the Data Scientist agent for insights and visualizations.
    """

    analysis_type: AnalysisType = AnalysisType.CUSTOM
    mlflow_run_id: str | None = None

    # Input data
    entity_ids: list[str] = Field(
        default_factory=list,
        description="Entities to analyze",
    )
    time_range_hours: int = Field(
        default=24,
        description="Hours of history to analyze",
    )
    custom_query: str | None = None
    diagnostic_context: str | None = Field(
        default=None,
        description="Pre-collected diagnostic data from Architect (logs, history, observations)",
    )

    # Script execution (Constitution: Isolation - gVisor sandbox)
    generated_script: str | None = None
    script_executions: list[ScriptExecution] = Field(default_factory=list)

    # Results
    insights: list[dict[str, Any]] = Field(default_factory=list)
    visualizations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Generated charts/graphs metadata",
    )
    recommendations: list[str] = Field(default_factory=list)

    # Reverse communication: automation suggestion from Data Scientist
    automation_suggestion: AutomationSuggestion | None = Field(
        default=None,
        description=(
            "Structured automation suggestion from the Data Scientist when a "
            "high-confidence, high-impact insight is detected. Contains pattern, "
            "entities, proposed trigger/action, and evidence."
        ),
    )

    # Dashboard output (User Story 4)
    dashboard_yaml: str | None = None


# =============================================================================
# ORCHESTRATOR STATE (Main Graph)
# =============================================================================


class OrchestratorState(MessageState):
    """State for the main orchestrator graph.

    Routes requests to the appropriate sub-graph (discovery, conversation, analysis).
    """

    # Routing
    intent: str | None = Field(
        default=None,
        description="Detected user intent",
    )
    target_graph: str | None = Field(
        default=None,
        description="Sub-graph to invoke (discovery, conversation, analysis)",
    )

    # Sub-graph results
    discovery_result: dict[str, Any] | None = None
    conversation_result: dict[str, Any] | None = None
    analysis_result: dict[str, Any] | None = None

    # Error handling
    error: str | None = None
    error_traceback: str | None = None


# Exports
__all__ = [
    # Enums
    "AgentRole",
    "ConversationStatus",
    "DiscoveryStatus",
    "AnalysisType",
    "ApprovalDecision",
    # Base states
    "BaseState",
    "MessageState",
    # Discovery
    "EntitySummary",
    "DiscoveryState",
    # Conversation
    "HITLApproval",
    "ApprovalState",
    "ConversationState",
    # Analysis
    "AutomationSuggestion",
    "ScriptExecution",
    "AnalysisState",
    # Orchestrator
    "OrchestratorState",
]
