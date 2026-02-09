"""Base state definitions for LangGraph agents.

Provides Pydantic models for graph state management.
All graphs use these models to maintain typed, validated state.
"""

from datetime import UTC, datetime
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
    # DS team specialists
    ENERGY_ANALYST = "energy_analyst"
    BEHAVIORAL_ANALYST = "behavioral_analyst"
    DIAGNOSTIC_ANALYST = "diagnostic_analyst"
    # Dashboard designer
    DASHBOARD_DESIGNER = "dashboard_designer"


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
        default_factory=lambda: datetime.now(UTC),
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
        self.decided_at = datetime.now(UTC)
        self.comment = comment

    def reject(self, rejected_by: str, reason: str) -> None:
        """Reject the proposal.

        Args:
            rejected_by: Who rejected
            reason: Why it was rejected
        """
        self.user_decision = ApprovalDecision.REJECTED
        self.decided_by = rejected_by
        self.decided_at = datetime.now(UTC)
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
# DASHBOARD STATE (Dashboard Designer Agent)
# =============================================================================


class DashboardState(ConversationState):
    """State for the Dashboard Designer agent.

    Extends ConversationState with dashboard-specific fields for
    Lovelace YAML generation, preview, and deployment.
    """

    # Generated dashboard configuration (Lovelace YAML)
    dashboard_yaml: str | None = None
    dashboard_title: str | None = None

    # Target HA dashboard (None = new dashboard)
    target_dashboard_id: str | None = None

    # Preview mode: True means show in UI before deploying to HA
    preview_mode: bool = True

    # Track which DS team specialists were consulted
    consulted_specialists: list[str] = Field(default_factory=list)


# =============================================================================
# ANALYSIS STATE (User Story 3 & 4: Data Science Team)
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
    """Structured automation suggestion from the DS Team.

    When the DS Team detects a high-confidence, high-impact pattern that could
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


# =============================================================================
# DS TEAM SHARED ANALYSIS STATE
# =============================================================================


class SpecialistFinding(BaseModel):
    """A single finding from one DS team specialist.

    Accumulated in TeamAnalysis.findings during multi-specialist analysis.
    Each specialist reads prior findings and flags cross-references or conflicts.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique finding identifier",
    )
    specialist: str = Field(
        description="Which specialist produced this: energy_analyst, behavioral_analyst, diagnostic_analyst",
    )
    finding_type: str = Field(
        description="Category: insight, concern, recommendation, data_quality_flag",
    )
    title: str = Field(description="Short title for the finding")
    description: str = Field(description="Detailed explanation")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Entity IDs relevant to this finding",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting data (metrics, stats, raw values)",
    )
    automation_suggestion: AutomationSuggestion | None = Field(
        default=None,
        description="Optional automation proposal if finding warrants one",
    )
    cross_references: list[str] = Field(
        default_factory=list,
        description="IDs of related findings from other specialists",
    )


class TeamAnalysis(BaseModel):
    """Shared analysis state for the DS team.

    Passed through each specialist node in the LangGraph workflow.
    Each specialist reads prior findings, adds their own, and flags
    cross-references or conflicts. A synthesis step then merges findings.
    """

    request_id: str = Field(description="Unique analysis request identifier")
    request_summary: str = Field(
        description="What the user/Architect asked for",
    )
    findings: list[SpecialistFinding] = Field(
        default_factory=list,
        description="Accumulated findings from all specialists",
    )
    consensus: str | None = Field(
        default=None,
        description="Synthesized view after all specialists contribute",
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description="Disagreements between specialists",
    )
    holistic_recommendations: list[str] = Field(
        default_factory=list,
        description="Combined, ranked recommendations",
    )
    synthesis_strategy: str | None = Field(
        default=None,
        description="Which synthesizer produced the consensus: 'programmatic' or 'llm'",
    )


# =============================================================================
# SCRIPT EXECUTION
# =============================================================================


class ScriptExecution(BaseModel):
    """Record of a sandboxed script execution (Constitution: Isolation)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    script_content: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
            "Structured automation suggestion from the DS Team when a "
            "high-confidence, high-impact insight is detected. Contains pattern, "
            "entities, proposed trigger/action, and evidence."
        ),
    )

    # Dashboard output (User Story 4)
    dashboard_yaml: str | None = None

    # DS team shared analysis (multi-specialist collaboration)
    team_analysis: TeamAnalysis | None = Field(
        default=None,
        description="Shared analysis state for the DS team. Populated during multi-specialist workflows.",
    )


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


# =============================================================================
# WORKFLOW PRESETS
# =============================================================================


class WorkflowPreset(BaseModel):
    """A preset workflow configuration for task flow customization.

    Defines which agents participate and which workflow graph to use
    for a given task type.
    """

    id: str
    name: str
    description: str
    agents: list[str] = Field(default_factory=list)
    workflow_key: str
    icon: str | None = None


DEFAULT_WORKFLOW_PRESETS: list[WorkflowPreset] = [
    WorkflowPreset(
        id="full-analysis",
        name="Full Analysis",
        description="Run all DS team specialists with programmatic synthesis for comprehensive insights.",
        agents=["energy_analyst", "behavioral_analyst", "diagnostic_analyst"],
        workflow_key="team_analysis",
        icon="bar-chart-3",
    ),
    WorkflowPreset(
        id="energy-only",
        name="Energy Only",
        description="Focus on energy consumption analysis and cost optimization.",
        agents=["energy_analyst"],
        workflow_key="team_analysis",
        icon="zap",
    ),
    WorkflowPreset(
        id="quick-diagnostic",
        name="Quick Diagnostic",
        description="Run diagnostic checks on system health, errors, and integrations.",
        agents=["diagnostic_analyst"],
        workflow_key="team_analysis",
        icon="stethoscope",
    ),
    WorkflowPreset(
        id="dashboard-design",
        name="Dashboard Design",
        description="Design Lovelace dashboards with DS team consultation for data-driven layouts.",
        agents=["dashboard_designer", "energy_analyst", "behavioral_analyst"],
        workflow_key="dashboard",
        icon="layout-dashboard",
    ),
    WorkflowPreset(
        id="conversation",
        name="General Chat",
        description="Open-ended conversation with the Architect agent.",
        agents=["architect"],
        workflow_key="conversation",
        icon="message-square",
    ),
]


# Exports
__all__ = [
    "DEFAULT_WORKFLOW_PRESETS",
    # Enums
    "AgentRole",
    "AnalysisState",
    "AnalysisType",
    "ApprovalDecision",
    "ApprovalState",
    # Analysis
    "AutomationSuggestion",
    # Base states
    "BaseState",
    "ConversationState",
    "ConversationStatus",
    # Dashboard
    "DashboardState",
    "DiscoveryState",
    "DiscoveryStatus",
    # Discovery
    "EntitySummary",
    # Conversation
    "HITLApproval",
    "MessageState",
    # Orchestrator
    "OrchestratorState",
    "ScriptExecution",
    "SpecialistFinding",
    "TeamAnalysis",
    # Workflow presets
    "WorkflowPreset",
]
