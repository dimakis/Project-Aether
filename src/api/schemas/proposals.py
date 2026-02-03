"""Automation proposal API schemas.

Pydantic schemas for proposal endpoints - User Story 2.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProposalCreate(BaseModel):
    """Schema for creating a proposal directly (bypass conversation)."""

    name: str = Field(description="Automation name")
    trigger: dict | list = Field(description="HA trigger configuration")
    actions: dict | list = Field(description="HA action configuration")
    description: str | None = Field(
        default=None,
        description="What the automation does",
    )
    conditions: dict | list | None = Field(
        default=None,
        description="HA conditions",
    )
    mode: str = Field(
        default="single",
        description="Execution mode: single, restart, queued, parallel",
    )


class ProposalResponse(BaseModel):
    """Schema for proposal response."""

    id: str = Field(description="Proposal UUID")
    conversation_id: str | None = Field(description="Source conversation")
    name: str = Field(description="Automation name")
    description: str | None = Field(description="Description")
    trigger: dict | list = Field(description="Trigger configuration")
    conditions: dict | list | None = Field(description="Conditions")
    actions: dict | list = Field(description="Actions")
    mode: str = Field(description="Execution mode")
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
        description="Who is approving",
    )
    comment: str | None = Field(
        default=None,
        description="Optional approval comment",
    )


class RejectionRequest(BaseModel):
    """Schema for rejecting a proposal."""

    reason: str = Field(description="Why the proposal was rejected")
    rejected_by: str = Field(
        default="user",
        description="Who is rejecting",
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
        description="Why rolling back",
    )


class RollbackResponse(BaseModel):
    """Schema for rollback result."""

    success: bool = Field(description="Whether rollback succeeded")
    proposal_id: str = Field(description="Proposal ID")
    ha_automation_id: str | None = Field(description="HA automation ID that was rolled back")
    rolled_back_at: datetime = Field(description="When rolled back")
    note: str | None = Field(
        default=None,
        description="Additional notes",
    )


# Exports
__all__ = [
    "ProposalCreate",
    "ProposalResponse",
    "ProposalYAMLResponse",
    "ProposalListResponse",
    "ApprovalRequest",
    "RejectionRequest",
    "DeploymentRequest",
    "DeploymentResponse",
    "RollbackRequest",
    "RollbackResponse",
]
