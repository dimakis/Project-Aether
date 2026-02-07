"""System health and status endpoints.

Provides health checks for load balancers and
detailed status for monitoring dashboards.

Endpoints:
- /health  — Lightweight liveness probe (no dependency checks)
- /ready   — Readiness probe (checks critical dependencies like DB)
- /status  — Detailed component health for monitoring dashboards
- /metrics — Operational metrics (rate-limit exempt, auth-gated in production)
"""

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from src.api.metrics import get_metrics_collector
from src.api.rate_limit import limiter
from src.api.schemas import (
    ComponentHealth,
    HealthResponse,
    HealthStatus,
    SystemStatus,
)
from src.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Track application start time for uptime calculation
_start_time: float = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check (Liveness)",
    description="Simple health check for load balancers. Returns 200 if the service is running.",
)
async def health_check() -> HealthResponse:
    """Basic health check endpoint (liveness probe).

    Returns a simple healthy status if the application is running.
    Used by load balancers and container orchestrators for liveness probes.
    Does NOT check dependencies — use /ready for readiness probes.

    Returns:
        HealthResponse with current status
    """
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness Probe",
    description="Readiness check that verifies critical dependencies (database). Returns 503 if not ready.",
)
async def readiness_check() -> HealthResponse:
    """Readiness probe for container orchestrators (K8s readiness probe).

    Checks critical dependencies (database). Returns 200 when the pod
    is ready to accept traffic, 503 otherwise.

    Returns:
        HealthResponse with readiness status
    """
    from fastapi import HTTPException

    db_health = await _check_database()
    if db_health.status == HealthStatus.UNHEALTHY:
        raise HTTPException(
            status_code=503,
            detail="Not ready: database unavailable",
        )
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
    )


@router.get(
    "/metrics",
    summary="Operational Metrics",
    description="Returns current operational metrics including request rates, latency percentiles, error counts, and agent invocations.",
)
@limiter.exempt
async def get_metrics(request: Request) -> dict:
    """Get current operational metrics.

    In production, this endpoint requires authentication (handled by
    the global auth dependency). The rate limiter is exempt because
    Prometheus/monitoring systems poll frequently.

    Returns metrics including:
    - Request counts (by method, path, status)
    - Latency percentiles (p50, p95, p99)
    - Error counts (by error type)
    - Active requests
    - Agent invocations (by role)
    - Uptime

    Returns:
        Dictionary with all current metrics
    """
    metrics = get_metrics_collector()
    return metrics.get_metrics()


@router.get(
    "/status",
    response_model=SystemStatus,
    summary="System Status",
    description="Detailed system status including component health checks.",
)
async def system_status() -> SystemStatus:
    """Detailed system status endpoint.

    Performs health checks on all system components and returns
    their individual statuses along with overall system health.

    Returns:
        SystemStatus with component-level health information
    """
    settings = get_settings()
    components: list[ComponentHealth] = []

    # Check database connectivity
    db_health = await _check_database()
    components.append(db_health)

    # Check MLflow connectivity
    mlflow_health = await _check_mlflow()
    components.append(mlflow_health)

    # Check Home Assistant connectivity
    ha_health = await _check_home_assistant()
    components.append(ha_health)

    # Determine overall status
    overall_status = _determine_overall_status(components)

    return SystemStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
        environment=settings.environment,
        components=components,
        uptime_seconds=time.time() - _start_time,
    )


async def _check_database() -> ComponentHealth:
    """Check database connectivity.

    Returns:
        ComponentHealth for the database
    """
    start = time.perf_counter()

    try:
        from sqlalchemy import text

        from src.storage import get_session

        async with get_session() as session:
            await session.execute(text("SELECT 1"))

        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="PostgreSQL connected",
            latency_ms=latency,
        )

    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        # Log the real error server-side; return a sanitized message to clients
        logger.error("Database health check failed: %s", e, exc_info=True)
        settings = get_settings()
        message = f"Database error: {e!s}" if settings.debug else "Database unavailable"
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=message,
            latency_ms=latency,
        )


async def _check_mlflow() -> ComponentHealth:
    """Check MLflow tracking server connectivity.

    Returns:
        ComponentHealth for MLflow
    """
    start = time.perf_counter()

    try:
        import mlflow

        from src.settings import get_settings

        settings = get_settings()
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

        # Try to list experiments (lightweight check)
        client = mlflow.tracking.MlflowClient()
        client.search_experiments(max_results=1)

        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="mlflow",
            status=HealthStatus.HEALTHY,
            message="MLflow tracking server connected",
            latency_ms=latency,
        )

    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        # MLflow is not critical - mark as degraded, not unhealthy
        logger.warning("MLflow health check failed: %s", e)
        settings = get_settings()
        message = f"MLflow unavailable: {e!s}" if settings.debug else "MLflow unavailable"
        return ComponentHealth(
            name="mlflow",
            status=HealthStatus.DEGRADED,
            message=message,
            latency_ms=latency,
        )


async def _check_home_assistant() -> ComponentHealth:
    """Check Home Assistant connectivity.

    Returns:
        ComponentHealth for Home Assistant
    """
    start = time.perf_counter()

    try:
        import httpx

        from src.settings import get_settings

        settings = get_settings()

        # Skip check if no HA URL configured
        if not settings.ha_url:
            return ComponentHealth(
                name="home_assistant",
                status=HealthStatus.DEGRADED,
                message="Home Assistant URL not configured",
            )

        # Check HA API endpoint
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.ha_url}/api/",
                headers={
                    "Authorization": f"Bearer {settings.ha_token.get_secret_value()}",
                },
            )

            latency = (time.perf_counter() - start) * 1000

            if response.status_code == 200:
                return ComponentHealth(
                    name="home_assistant",
                    status=HealthStatus.HEALTHY,
                    message="Home Assistant connected",
                    latency_ms=latency,
                )
            elif response.status_code == 401:
                return ComponentHealth(
                    name="home_assistant",
                    status=HealthStatus.UNHEALTHY,
                    message="Home Assistant authentication failed",
                    latency_ms=latency,
                )
            else:
                return ComponentHealth(
                    name="home_assistant",
                    status=HealthStatus.DEGRADED,
                    message=f"Home Assistant returned status {response.status_code}",
                    latency_ms=latency,
                )

    except httpx.TimeoutException:
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            name="home_assistant",
            status=HealthStatus.UNHEALTHY,
            message="Home Assistant connection timed out",
            latency_ms=latency,
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        logger.warning("Home Assistant health check failed: %s", e)
        settings = get_settings()
        message = (
            f"Home Assistant error: {e!s}" if settings.debug else "Home Assistant unavailable"
        )
        return ComponentHealth(
            name="home_assistant",
            status=HealthStatus.UNHEALTHY,
            message=message,
            latency_ms=latency,
        )


def _determine_overall_status(components: list[ComponentHealth]) -> HealthStatus:
    """Determine overall system status from component statuses.

    Rules:
    - Any UNHEALTHY critical component (database) -> UNHEALTHY
    - Any UNHEALTHY non-critical component -> DEGRADED
    - Any DEGRADED component -> DEGRADED
    - All HEALTHY -> HEALTHY

    Args:
        components: List of component health statuses

    Returns:
        Overall system health status
    """
    critical_components = {"database"}

    has_unhealthy_critical = False
    has_unhealthy_noncritical = False
    has_degraded = False

    for component in components:
        if component.status == HealthStatus.UNHEALTHY:
            if component.name in critical_components:
                has_unhealthy_critical = True
            else:
                has_unhealthy_noncritical = True
        elif component.status == HealthStatus.DEGRADED:
            has_degraded = True

    if has_unhealthy_critical:
        return HealthStatus.UNHEALTHY
    elif has_unhealthy_noncritical or has_degraded:
        return HealthStatus.DEGRADED
    else:
        return HealthStatus.HEALTHY
