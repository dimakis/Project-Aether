"""Common Pydantic schemas for API requests and responses.

Provides reusable schema definitions for consistent
API responses across all endpoints.

Submodule schemas use lazy imports to reduce startup cost.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel, Field

_EXPORTS = {
    "AreaListResponse": "src.api.schemas.areas",
    "AreaResponse": "src.api.schemas.areas",
    "ChatRequest": "src.api.schemas.conversations",
    "ChatResponse": "src.api.schemas.conversations",
    "ConversationCreate": "src.api.schemas.conversations",
    "ConversationDetailResponse": "src.api.schemas.conversations",
    "ConversationListResponse": "src.api.schemas.conversations",
    "ConversationResponse": "src.api.schemas.conversations",
    "MessageCreate": "src.api.schemas.conversations",
    "MessageResponse": "src.api.schemas.conversations",
    "StreamChunk": "src.api.schemas.conversations",
    "DeviceListResponse": "src.api.schemas.devices",
    "DeviceResponse": "src.api.schemas.devices",
    "EntityListResponse": "src.api.schemas.entities",
    "EntityQueryRequest": "src.api.schemas.entities",
    "EntityQueryResult": "src.api.schemas.entities",
    "EntityResponse": "src.api.schemas.entities",
    "EntitySyncRequest": "src.api.schemas.entities",
    "EntitySyncResponse": "src.api.schemas.entities",
    "AutomationListResponse": "src.api.schemas.ha_automations",
    "AutomationResponse": "src.api.schemas.ha_automations",
    "HARegistrySummary": "src.api.schemas.ha_automations",
    "SceneListResponse": "src.api.schemas.ha_automations",
    "SceneResponse": "src.api.schemas.ha_automations",
    "ScriptListResponse": "src.api.schemas.ha_automations",
    "ScriptResponse": "src.api.schemas.ha_automations",
    "ServiceCallRequest": "src.api.schemas.ha_automations",
    "ServiceCallResponse": "src.api.schemas.ha_automations",
    "ServiceListResponse": "src.api.schemas.ha_automations",
    "ServiceResponse": "src.api.schemas.ha_automations",
    "HelperCreateRequest": "src.api.schemas.helpers",
    "HelperCreateResponse": "src.api.schemas.helpers",
    "HelperDeleteResponse": "src.api.schemas.helpers",
    "HelperListResponse": "src.api.schemas.helpers",
    "HelperResponse": "src.api.schemas.helpers",
    "HelperType": "src.api.schemas.helpers",
    "ActionRequest": "src.api.schemas.insights",
    "AnalysisJob": "src.api.schemas.insights",
    "AnalysisJobResponse": "src.api.schemas.insights",
    "AnalysisRequest": "src.api.schemas.insights",
    "DismissRequest": "src.api.schemas.insights",
    "EnergyOverviewResponse": "src.api.schemas.insights",
    "EnergyStatsResponse": "src.api.schemas.insights",
    "InsightCreate": "src.api.schemas.insights",
    "InsightListResponse": "src.api.schemas.insights",
    "InsightResponse": "src.api.schemas.insights",
    "InsightStatus": "src.api.schemas.insights",
    "InsightSummary": "src.api.schemas.insights",
    "InsightType": "src.api.schemas.insights",
    "ReviewRequest": "src.api.schemas.insights",
    "AutomationSuggestionResponse": "src.api.schemas.optimization",
    "OptimizationAnalysisType": "src.api.schemas.optimization",
    "OptimizationRequest": "src.api.schemas.optimization",
    "OptimizationResult": "src.api.schemas.optimization",
    "SuggestionAcceptRequest": "src.api.schemas.optimization",
    "SuggestionListResponse": "src.api.schemas.optimization",
    "SuggestionRejectRequest": "src.api.schemas.optimization",
    "SuggestionStatus": "src.api.schemas.optimization",
    "ApprovalRequest": "src.api.schemas.proposals",
    "DeploymentRequest": "src.api.schemas.proposals",
    "DeploymentResponse": "src.api.schemas.proposals",
    "ProposalCreate": "src.api.schemas.proposals",
    "ProposalListResponse": "src.api.schemas.proposals",
    "ProposalResponse": "src.api.schemas.proposals",
    "ProposalYAMLResponse": "src.api.schemas.proposals",
    "RejectionRequest": "src.api.schemas.proposals",
    "RollbackRequest": "src.api.schemas.proposals",
    "RollbackResponse": "src.api.schemas.proposals",
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
    raise AttributeError(f"module 'src.api.schemas' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return [
        *_EXPORTS.keys(),
        "ComponentHealth",
        "ErrorDetail",
        "ErrorResponse",
        "ErrorType",
        "HealthResponse",
        "HealthStatus",
        "PaginationMeta",
        "PaginatedResponse",
        "SuccessResponse",
        "SystemStatus",
    ]


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
        default_factory=lambda: datetime.now(UTC),
        description="Health check timestamp",
    )
    version: str = Field(description="Application version")


class SystemStatus(BaseModel):
    """Detailed system status response."""

    status: HealthStatus = Field(..., description="Overall system health")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Status check timestamp",
    )
    version: str = Field(description="Application version")
    environment: str = Field(..., description="Current environment")
    components: list[ComponentHealth] = Field(
        default_factory=list,
        description="Individual component health statuses",
    )
    uptime_seconds: float | None = Field(
        default=None,
        description="Application uptime in seconds",
    )
    public_url: str | None = Field(
        default=None,
        description="Externally reachable base URL (for webhook URLs, etc.)",
    )
    deployment_mode: str = Field(
        default="monolith",
        description="Deployment mode: monolith or distributed",
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


if TYPE_CHECKING:
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
    from src.api.schemas.helpers import (
        HelperCreateRequest,
        HelperCreateResponse,
        HelperDeleteResponse,
        HelperListResponse,
        HelperResponse,
        HelperType,
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

__all__ = [
    "ActionRequest",
    "AnalysisJob",
    "AnalysisJobResponse",
    "AnalysisRequest",
    "ApprovalRequest",
    "AreaListResponse",
    "AreaResponse",
    "AutomationListResponse",
    "AutomationResponse",
    "AutomationSuggestionResponse",
    "ChatRequest",
    "ChatResponse",
    "ComponentHealth",
    "ConversationCreate",
    "ConversationDetailResponse",
    "ConversationListResponse",
    "ConversationResponse",
    "DeploymentRequest",
    "DeploymentResponse",
    "DeviceListResponse",
    "DeviceResponse",
    "DismissRequest",
    "EnergyOverviewResponse",
    "EnergyStatsResponse",
    "EntityListResponse",
    "EntityQueryRequest",
    "EntityQueryResult",
    "EntityResponse",
    "EntitySyncRequest",
    "EntitySyncResponse",
    "ErrorDetail",
    "ErrorResponse",
    "ErrorType",
    "HARegistrySummary",
    "HealthResponse",
    "HealthStatus",
    "HelperCreateRequest",
    "HelperCreateResponse",
    "HelperDeleteResponse",
    "HelperListResponse",
    "HelperResponse",
    "HelperType",
    "InsightCreate",
    "InsightListResponse",
    "InsightResponse",
    "InsightStatus",
    "InsightSummary",
    "InsightType",
    "MessageCreate",
    "MessageResponse",
    "OptimizationAnalysisType",
    "OptimizationRequest",
    "OptimizationResult",
    "PaginatedResponse",
    "PaginationMeta",
    "ProposalCreate",
    "ProposalListResponse",
    "ProposalResponse",
    "ProposalYAMLResponse",
    "RejectionRequest",
    "ReviewRequest",
    "RollbackRequest",
    "RollbackResponse",
    "SceneListResponse",
    "SceneResponse",
    "ScriptListResponse",
    "ScriptResponse",
    "ServiceCallRequest",
    "ServiceCallResponse",
    "ServiceListResponse",
    "ServiceResponse",
    "StreamChunk",
    "SuccessResponse",
    "SuggestionAcceptRequest",
    "SuggestionListResponse",
    "SuggestionRejectRequest",
    "SuggestionStatus",
    "SystemStatus",
]
