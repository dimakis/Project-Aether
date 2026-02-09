"""Optimization API schemas.

Pydantic schemas for the optimization endpoints - Feature 03.

Behavioral analysis, automation gap detection, and DS-to-Architect
suggestion flow.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OptimizationAnalysisType(str, Enum):
    """Types of optimization analysis."""

    BEHAVIOR_ANALYSIS = "behavior_analysis"
    AUTOMATION_ANALYSIS = "automation_analysis"
    AUTOMATION_GAP_DETECTION = "automation_gap_detection"
    CORRELATION_DISCOVERY = "correlation_discovery"
    DEVICE_HEALTH = "device_health"
    COST_OPTIMIZATION = "cost_optimization"


class SuggestionStatus(str, Enum):
    """Status of an automation suggestion."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class OptimizationRequest(BaseModel):
    """Schema for requesting an optimization analysis."""

    analysis_types: list[OptimizationAnalysisType] = Field(
        default=[OptimizationAnalysisType.BEHAVIOR_ANALYSIS],
        description="Types of analysis to run",
    )
    hours: int = Field(
        default=168,
        ge=1,
        le=720,
        description="Hours of history to analyze (default: 168 = 1 week)",
    )
    entity_ids: list[str] | None = Field(
        default=None,
        description="Specific entity IDs to focus on (None = all)",
    )
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Areas to focus on (e.g., 'kitchen', 'bedroom')",
    )


class AutomationSuggestionResponse(BaseModel):
    """Schema for an automation suggestion from the DS."""

    id: str = Field(description="Suggestion UUID")
    pattern: str = Field(description="Description of the detected pattern")
    entities: list[str] = Field(description="Entity IDs involved")
    proposed_trigger: str = Field(description="Suggested trigger")
    proposed_action: str = Field(description="Suggested action")
    confidence: float = Field(description="Confidence score 0.0-1.0")
    source_insight_type: str = Field(description="Analysis type that generated this")
    status: SuggestionStatus = Field(
        default=SuggestionStatus.PENDING,
        description="Current status",
    )
    created_at: datetime = Field(description="When generated")

    model_config = {"from_attributes": True}


class OptimizationResult(BaseModel):
    """Schema for optimization analysis results."""

    job_id: str = Field(description="Job UUID")
    status: str = Field(description="Job status: pending, running, completed, failed")
    analysis_types: list[str] = Field(description="Types of analysis run")
    hours_analyzed: int = Field(description="Hours of data analyzed")
    insight_count: int = Field(description="Number of insights found")
    suggestion_count: int = Field(description="Number of automation suggestions")
    insights: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Analysis insights",
    )
    suggestions: list[AutomationSuggestionResponse] = Field(
        default_factory=list,
        description="Automation suggestions",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Text recommendations",
    )
    started_at: datetime = Field(description="When started")
    completed_at: datetime | None = Field(default=None, description="When completed")
    error: str | None = Field(default=None, description="Error if failed")


class SuggestionAcceptRequest(BaseModel):
    """Schema for accepting a suggestion."""

    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional comment",
    )


class SuggestionRejectRequest(BaseModel):
    """Schema for rejecting a suggestion."""

    reason: str | None = Field(
        default=None,
        max_length=2000,
        description="Reason for rejection",
    )


class SuggestionListResponse(BaseModel):
    """Schema for list of suggestions."""

    items: list[AutomationSuggestionResponse] = Field(description="Suggestions")
    total: int = Field(description="Total count")


# Exports
__all__ = [
    "AutomationSuggestionResponse",
    "OptimizationAnalysisType",
    "OptimizationRequest",
    "OptimizationResult",
    "SuggestionAcceptRequest",
    "SuggestionListResponse",
    "SuggestionRejectRequest",
    "SuggestionStatus",
]
