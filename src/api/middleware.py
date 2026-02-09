"""Request tracing middleware for FastAPI.

Provides request-level tracing and operational metrics collection.
Logs request method, path, status code, duration, and correlation ID.
"""

import time
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.metrics import get_metrics_collector

logger = structlog.get_logger()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing and metrics collection.

    Logs structured request information and updates metrics collector
    for operational monitoring.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log tracing information.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in the chain

        Returns:
            Response with tracing headers
        """
        # Start timing
        start = time.perf_counter()

        # Get metrics collector
        metrics = get_metrics_collector()

        # Track active request
        metrics.increment_active_requests()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start) * 1000

            # Get correlation ID from context (lazy import to avoid circular dependency)
            from src.api.main import get_correlation_id

            correlation_id = get_correlation_id()

            # Record metrics
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Log structured request information
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
            )

            return response

        except Exception as e:
            # Calculate duration even on error
            duration_ms = (time.perf_counter() - start) * 1000

            # Record error metrics
            error_type = type(e).__name__
            metrics.record_error(error_type)

            # Get correlation ID from context (lazy import to avoid circular dependency)
            from src.api.main import get_correlation_id

            correlation_id = get_correlation_id()

            # Log error
            logger.error(
                "request_error",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
                error_type=error_type,
                exc_info=e,
            )

            # Re-raise to let exception handlers process it
            raise

        finally:
            # Decrement active requests
            metrics.decrement_active_requests()
