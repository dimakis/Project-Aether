"""Insight API schemas.

Pydantic schemas for insight endpoints - User Story 3.

Energy optimization suggestions and Data Science team analysis results.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InsightType(str, Enum):
    """Types of insights."""

    ENERGY_OPTIMIZATION = "energy_optimization"
    ANOMALY_DETECTION = "anomaly_detection"
    USAGE_PATTERN = "usage_pattern"
    COST_SAVING = "cost_saving"
    MAINTENANCE_PREDICTION = "maintenance_prediction"
    # Feature 03: Intelligent Optimization
    AUTOMATION_GAP = "automation_gap"
    AUTOMATION_INEFFICIENCY = "automation_inefficiency"
    CORRELATION = "correlation"
    DEVICE_HEALTH = "device_health"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    # Conversational Insights: additional preset types
    COMFORT_ANALYSIS = "comfort_analysis"
    SECURITY_AUDIT = "security_audit"
    WEATHER_CORRELATION = "weather_correlation"
    AUTOMATION_EFFICIENCY = "automation_efficiency"
    CUSTOM = "custom"


class InsightStatus(str, Enum):
    """Insight lifecycle status."""

    PENDING = "pending"
    REVIEWED = "reviewed"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class InsightCreate(BaseModel):
    """Schema for creating an insight directly."""

    type: InsightType = Field(description="Insight category")
    title: str = Field(max_length=500, description="Brief summary")
    description: str = Field(max_length=10_000, description="Detailed explanation (markdown supported)")
    evidence: dict[str, Any] = Field(
        description="Supporting data (charts, statistics, queries)"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0",
    )
    impact: str = Field(
        max_length=20,
        description="Potential impact: low, medium, high, critical",
    )
    entities: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="Related entity IDs",
    )
    script_path: str | None = Field(
        default=None,
        max_length=500,
        description="Path to analysis script",
    )
    script_output: dict[str, Any] | None = Field(
        default=None,
        description="Script execution results",
    )
    mlflow_run_id: str | None = Field(
        default=None,
        max_length=100,
        description="MLflow run ID for traceability",
    )


class InsightResponse(BaseModel):
    """Schema for insight response."""

    id: str = Field(description="Insight UUID")
    type: InsightType = Field(description="Insight category")
    title: str = Field(description="Brief summary")
    description: str = Field(description="Detailed explanation")
    evidence: dict[str, Any] = Field(description="Supporting data")
    confidence: float = Field(description="Confidence score 0.0-1.0")
    impact: str = Field(description="Impact level")
    entities: list[str] = Field(description="Related entity IDs")
    script_path: str | None = Field(description="Analysis script path")
    script_output: dict[str, Any] | None = Field(description="Script results")
    status: InsightStatus = Field(description="Current status")
    mlflow_run_id: str | None = Field(description="MLflow run ID")
    created_at: datetime = Field(description="When generated")
    reviewed_at: datetime | None = Field(description="When reviewed")
    actioned_at: datetime | None = Field(description="When actioned")

    model_config = {"from_attributes": True}


class InsightListResponse(BaseModel):
    """Schema for list of insights."""

    items: list[InsightResponse] = Field(description="Insights")
    total: int = Field(description="Total count")
    limit: int = Field(description="Page size")
    offset: int = Field(description="Current offset")


class InsightSummary(BaseModel):
    """Schema for insight summary/counts."""

    total: int = Field(description="Total insights")
    by_type: dict[str, int] = Field(description="Count by insight type")
    by_status: dict[str, int] = Field(description="Count by status")
    pending_count: int = Field(description="Insights awaiting review")
    high_impact_count: int = Field(description="High/critical impact insights")


class AnalysisRequest(BaseModel):
    """Schema for requesting an energy analysis."""

    analysis_type: str = Field(
        default="energy",
        max_length=50,
        description="Type of analysis: energy, anomaly, pattern",
    )
    entity_ids: list[str] | None = Field(
        default=None,
        description="Specific entity IDs to analyze (None = all energy sensors)",
    )
    hours: int = Field(
        default=24,
        ge=1,
        le=168 * 4,  # Max 4 weeks
        description="Hours of history to analyze",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis-specific options",
    )


class AnalysisJob(BaseModel):
    """Schema for an analysis job status."""

    job_id: str = Field(description="Job UUID")
    status: str = Field(
        description="Job status: pending, running, completed, failed"
    )
    analysis_type: str = Field(description="Type of analysis")
    progress: float = Field(
        ge=0.0,
        le=1.0,
        description="Progress 0.0-1.0",
    )
    started_at: datetime = Field(description="When started")
    completed_at: datetime | None = Field(default=None, description="When completed")
    mlflow_run_id: str | None = Field(default=None, description="MLflow run ID")
    insight_ids: list[str] = Field(
        default_factory=list,
        description="Generated insight IDs",
    )
    error: str | None = Field(
        default=None,
        description="Error message if failed",
    )


class AnalysisJobResponse(BaseModel):
    """Schema for analysis job response."""

    job: AnalysisJob = Field(description="Job details")
    insights: list[InsightResponse] = Field(
        default_factory=list,
        description="Generated insights (if completed)",
    )


class ReviewRequest(BaseModel):
    """Schema for marking an insight as reviewed."""

    reviewed_by: str = Field(
        default="user",
        max_length=100,
        description="Who reviewed",
    )
    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Review comment",
    )


class ActionRequest(BaseModel):
    """Schema for marking an insight as actioned."""

    actioned_by: str = Field(
        default="user",
        max_length=100,
        description="Who took action",
    )
    action_taken: str | None = Field(
        default=None,
        max_length=2000,
        description="What action was taken",
    )
    create_automation: bool = Field(
        default=False,
        description="Whether to create an automation from this insight",
    )


class DismissRequest(BaseModel):
    """Schema for dismissing an insight."""

    reason: str | None = Field(
        default=None,
        max_length=2000,
        description="Why dismissed",
    )


class EnergyStatsResponse(BaseModel):
    """Schema for energy statistics."""

    entity_id: str = Field(description="Energy sensor entity ID")
    friendly_name: str | None = Field(description="Friendly name")
    total_kwh: float = Field(description="Total energy consumption")
    average_kwh: float = Field(description="Average consumption")
    peak_value: float = Field(description="Peak value")
    peak_timestamp: datetime | None = Field(description="When peak occurred")
    daily_totals: dict[str, float] = Field(description="Daily breakdown")
    hourly_averages: dict[str, float] = Field(description="Hourly averages")
    hours_analyzed: int = Field(description="Hours of data analyzed")


class EnergyOverviewResponse(BaseModel):
    """Schema for energy overview."""

    sensors: list[EnergyStatsResponse] = Field(description="Per-sensor stats")
    total_kwh: float = Field(description="Total across all sensors")
    sensor_count: int = Field(description="Number of energy sensors")
    hours_analyzed: int = Field(description="Hours of data")
    analysis_timestamp: datetime = Field(description="When analyzed")


# Exports
__all__ = [
    # Enums
    "InsightType",
    "InsightStatus",
    # Insight CRUD
    "InsightCreate",
    "InsightResponse",
    "InsightListResponse",
    "InsightSummary",
    # Analysis
    "AnalysisRequest",
    "AnalysisJob",
    "AnalysisJobResponse",
    # Actions
    "ReviewRequest",
    "ActionRequest",
    "DismissRequest",
    # Energy
    "EnergyStatsResponse",
    "EnergyOverviewResponse",
]
