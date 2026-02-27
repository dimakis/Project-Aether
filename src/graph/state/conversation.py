"""Conversation state for Architect/Developer agents."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .base import MessageState
from .enums import ApprovalDecision, ConversationStatus


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

    # Orchestration (Feature 30: Domain-Agnostic Orchestration)
    channel: str | None = None  # "voice", "text", or "api"
    active_agent: str | None = None  # Agent handling the current turn
    workflow_preset: str | None = None  # Workflow preset ID (e.g. "full-analysis")
    disabled_agents: list[str] = Field(default_factory=list)  # Agents excluded from preset

    # Trace context — populated by @mlflow.trace() wrapper for frontend activity panel
    last_trace_id: str | None = None
