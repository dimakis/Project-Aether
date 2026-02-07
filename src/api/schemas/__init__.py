"""Common Pydantic schemas for API requests and responses.

Provides reusable schema definitions for consistent
API responses across all endpoints.
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Import entity schemas
from src.api.schemas.areas import AreaListResponse, AreaResponse
from src.api.schemas.conversations import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    StreamChunk,
)
from src.api.schemas.devices import DeviceListResponse, DeviceResponse
from src.api.schemas.entities import (
    EntityListResponse,
    EntityQueryRequest,
    EntityQueryResult,
    EntityResponse,
    EntitySyncRequest,
    EntitySyncResponse,
)
from src.api.schemas.ha_automations import (
    AutomationListResponse,
    AutomationResponse,
    HARegistrySummary,
    SceneListResponse,
    SceneResponse,
    ScriptListResponse,
    ScriptResponse,
    ServiceCallRequest,
    ServiceCallResponse,
    ServiceListResponse,
    ServiceResponse,
)
from src.api.schemas.insights import (
    ActionRequest,
    AnalysisJob,
    AnalysisJobResponse,
    AnalysisRequest,
    DismissRequest,
    EnergyOverviewResponse,
    EnergyStatsResponse,
    InsightCreate,
    InsightListResponse,
    InsightResponse,
    InsightStatus,
    InsightSummary,
    InsightType,
    ReviewRequest,
)
from src.api.schemas.optimization import (
    AutomationSuggestionResponse,
    OptimizationAnalysisType,
    OptimizationRequest,
    OptimizationResult,
    SuggestionAcceptRequest,
    SuggestionListResponse,
    SuggestionRejectRequest,
    SuggestionStatus,
)
from src.api.schemas.proposals import (
    ApprovalRequest,
    DeploymentRequest,
    DeploymentResponse,
    ProposalCreate,
    ProposalListResponse,
    ProposalResponse,
    ProposalYAMLResponse,
    RejectionRequest,
    RollbackRequest,
    RollbackResponse,
)

T = TypeVar("T")


class ErrorType(StrEnum):
    """Standard error types."""

    HTTP_ERROR = "http_error"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    SERVICE_UNAVAILABLE = "service_unavailable"


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Human-readable error message")
    type: ErrorType = Field(..., description="Error type classification")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error details",
    )


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    error: ErrorDetail


class HealthStatus(StrEnum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status for a single component."""

    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Component health status")
    message: str | None = Field(default=None, description="Additional status message")
    latency_ms: float | None = Field(
        default=None,
        description="Component response latency in milliseconds",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: HealthStatus = Field(..., description="Overall system health")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Health check timestamp",
    )
    version: str = Field(default="0.1.0", description="Application version")


class SystemStatus(BaseModel):
    """Detailed system status response."""

    status: HealthStatus = Field(..., description="Overall system health")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Status check timestamp",
    )
    version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(..., description="Current environment")
    components: list[ComponentHealth] = Field(
        default_factory=list,
        description="Individual component health statuses",
    )
    uptime_seconds: float | None = Field(
        default=None,
        description="Application uptime in seconds",
    )


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there's a next page")
    has_prev: bool = Field(..., description="Whether there's a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    data: list[T] = Field(..., description="Page of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response wrapper."""

    data: T = Field(..., description="Response data")
    message: str | None = Field(default=None, description="Optional success message")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str = Field(..., description="Response message")


# Exports
__all__ = [
    # Error types
    "ErrorType",
    "ErrorDetail",
    "ErrorResponse",
    # Health
    "HealthStatus",
    "ComponentHealth",
    "HealthResponse",
    "SystemStatus",
    # Pagination
    "PaginationMeta",
    "PaginatedResponse",
    "SuccessResponse",
    "MessageResponse",
    # Entities
    "EntityResponse",
    "EntityListResponse",
    "EntityQueryRequest",
    "EntityQueryResult",
    "EntitySyncRequest",
    "EntitySyncResponse",
    # Areas
    "AreaResponse",
    "AreaListResponse",
    # Devices
    "DeviceResponse",
    "DeviceListResponse",
    # Automations, Scripts, Scenes
    "AutomationResponse",
    "AutomationListResponse",
    "ScriptResponse",
    "ScriptListResponse",
    "SceneResponse",
    "SceneListResponse",
    # Services
    "ServiceResponse",
    "ServiceListResponse",
    "ServiceCallRequest",
    "ServiceCallResponse",
    # HA Registry
    "HARegistrySummary",
    # Conversations (US2)
    "ConversationCreate",
    "ConversationResponse",
    "ConversationDetailResponse",
    "ConversationListResponse",
    "MessageCreate",
    "MessageResponse",
    "ChatRequest",
    "ChatResponse",
    "StreamChunk",
    # Proposals (US2)
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
    # Optimization (Feature 03)
    "OptimizationAnalysisType",
    "SuggestionStatus",
    "OptimizationRequest",
    "AutomationSuggestionResponse",
    "OptimizationResult",
    "SuggestionAcceptRequest",
    "SuggestionRejectRequest",
    "SuggestionListResponse",
    # Insights (US3)
    "InsightType",
    "InsightStatus",
    "InsightCreate",
    "InsightResponse",
    "InsightListResponse",
    "InsightSummary",
    "AnalysisRequest",
    "AnalysisJob",
    "AnalysisJobResponse",
    "ReviewRequest",
    "ActionRequest",
    "DismissRequest",
    "EnergyStatsResponse",
    "EnergyOverviewResponse",
]
