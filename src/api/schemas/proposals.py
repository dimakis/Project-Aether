"""Automation proposal API schemas.

Pydantic schemas for proposal endpoints - User Story 2.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProposalCreate(BaseModel):
    """Schema for creating a proposal directly (bypass conversation)."""

    name: str = Field(max_length=255, description="Automation name")
    trigger: dict | list = Field(default_factory=dict, description="HA trigger configuration")
    actions: dict | list = Field(default_factory=dict, description="HA action configuration")
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="What the automation does",
    )
    conditions: dict | list | None = Field(
        default=None,
        description="HA conditions",
    )
    mode: str = Field(
        default="single",
        max_length=20,
        description="Execution mode: single, restart, queued, parallel",
    )
    proposal_type: str = Field(
        default="automation",
        max_length=50,
        description="Type: automation, entity_command, script, scene",
    )
    service_call: dict | None = Field(
        default=None,
        description="Service call details for entity_command type (domain, service, entity_id, data)",
    )


class ReviewNote(BaseModel):
    """A single review annotation describing a suggested change."""

    change: str = Field(description="What was changed")
    rationale: str = Field(description="Why the change was suggested")
    category: str = Field(
        description="Category: energy, behavioral, efficiency, security, redundancy"
    )


class ProposalResponse(BaseModel):
    """Schema for proposal response."""

    id: str = Field(description="Proposal UUID")
    proposal_type: str = Field(
        default="automation", description="Type: automation, entity_command, script, scene"
    )
    conversation_id: str | None = Field(description="Source conversation")
    name: str = Field(description="Automation name")
    description: str | None = Field(description="Description")
    trigger: dict | list = Field(description="Trigger configuration")
    conditions: dict | list | None = Field(description="Conditions")
    actions: dict | list = Field(description="Actions")
    mode: str = Field(description="Execution mode")
    service_call: dict | None = Field(
        default=None, description="Service call details for entity_command type"
    )
    status: str = Field(description="Proposal status")
    ha_automation_id: str | None = Field(description="HA automation ID if deployed")
    proposed_at: datetime | None = Field(description="When proposed")
    approved_at: datetime | None = Field(description="When approved")
    approved_by: str | None = Field(description="Who approved")
    deployed_at: datetime | None = Field(description="When deployed")
    rolled_back_at: datetime | None = Field(description="When rolled back")
    rejection_reason: str | None = Field(description="Why rejected")
    created_at: datetime = Field(description="Record creation")
    updated_at: datetime = Field(description="Last update")

    # Review fields (Feature 28: Smart Config Review)
    original_yaml: str | None = Field(
        default=None, description="Original YAML before review (present = review proposal)"
    )
    review_notes: list[dict] | None = Field(
        default=None, description="Structured change annotations [{change, rationale, category}]"
    )
    review_session_id: str | None = Field(
        default=None, description="UUID grouping proposals from a batch review"
    )
    parent_proposal_id: str | None = Field(
        default=None, description="Parent proposal ID for split reviews"
    )

    model_config = {"from_attributes": True}


class ProposalYAMLResponse(ProposalResponse):
    """Schema for proposal with YAML content."""

    yaml_content: str = Field(description="Generated HA automation YAML")


class ProposalListResponse(BaseModel):
    """Schema for list of proposals."""

    items: list[ProposalResponse] = Field(description="Proposals")
    total: int = Field(description="Total count")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Current offset")


class ApprovalRequest(BaseModel):
    """Schema for approving a proposal."""

    approved_by: str = Field(
        default="user",
        max_length=100,
        description="Who is approving",
    )
    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional approval comment",
    )
    trace_id: str | None = Field(
        default=None,
        description="MLflow trace ID from the conversation that generated this proposal",
    )


class RejectionRequest(BaseModel):
    """Schema for rejecting a proposal."""

    reason: str = Field(max_length=2000, description="Why the proposal was rejected")
    rejected_by: str = Field(
        default="user",
        max_length=100,
        description="Who is rejecting",
    )
    trace_id: str | None = Field(
        default=None,
        description="MLflow trace ID from the conversation that generated this proposal",
    )


class DeploymentRequest(BaseModel):
    """Schema for deploying an approved proposal."""

    force: bool = Field(
        default=False,
        description="Force deployment even if already deployed",
    )


class DeploymentResponse(BaseModel):
    """Schema for deployment result."""

    success: bool = Field(description="Whether deployment succeeded")
    proposal_id: str = Field(description="Proposal ID")
    ha_automation_id: str | None = Field(description="HA automation ID")
    method: str = Field(description="Deployment method used")
    yaml_content: str = Field(description="Deployed YAML")
    instructions: str | None = Field(
        default=None,
        description="Manual instructions if needed",
    )
    deployed_at: datetime | None = Field(description="When deployed")
    error: str | None = Field(
        default=None,
        description="Error message if failed",
    )


class RollbackRequest(BaseModel):
    """Schema for rollback request."""

    reason: str | None = Field(
        default=None,
        max_length=2000,
        description="Why rolling back",
    )


class RollbackResponse(BaseModel):
    """Schema for rollback result."""

    success: bool = Field(description="Whether rollback succeeded")
    proposal_id: str = Field(description="Proposal ID")
    ha_automation_id: str | None = Field(description="HA automation ID that was rolled back")
    ha_disabled: bool = Field(
        default=False,
        description="Whether the automation was actually disabled in HA",
    )
    ha_error: str | None = Field(
        default=None,
        description="Error message if HA disable failed",
    )
    rolled_back_at: datetime = Field(description="When rolled back")
    note: str | None = Field(
        default=None,
        description="Additional notes",
    )


# Exports
__all__ = [
    "ApprovalRequest",
    "DeploymentRequest",
    "DeploymentResponse",
    "ProposalCreate",
    "ProposalListResponse",
    "ProposalResponse",
    "ProposalYAMLResponse",
    "RejectionRequest",
    "ReviewNote",
    "RollbackRequest",
    "RollbackResponse",
]
