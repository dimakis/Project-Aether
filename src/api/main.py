"""FastAPI application configuration and setup.

Main entry point for the HTTP API with CORS, middleware,
rate limiting, and lifecycle management.
"""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.auth import verify_api_key
from src.api.rate_limit import limiter
from src.api.routes import api_router
from src.exceptions import AetherError, ConfigurationError, HAClientError, ValidationError
from src.settings import Settings, get_settings
from src.storage import close_db, init_db
from src.tracing import init_mlflow

# Context variable for correlation ID (thread-safe, async-safe)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Singleton app instance
_app: FastAPI | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database, MLflow
    - Shutdown: Close database connections

    Args:
        app: FastAPI application instance

    Yields:
        None (context for application runtime)
    """
    # Startup
    settings = get_settings()

    if settings.environment != "testing":
        # Initialize MLflow (Constitution: Observability)
        init_mlflow()

        # Initialize database (Constitution: State)
        await init_db()

    # Start scheduler (Feature 10: Scheduled & Event-Driven Insights)
    # Respects AETHER_ROLE to prevent duplicate jobs in multi-replica deployments
    scheduler = None
    should_start_scheduler = (
        settings.scheduler_enabled
        and settings.environment != "testing"
        and settings.aether_role in ("all", "scheduler")
    )
    if should_start_scheduler:
        from src.scheduler import SchedulerService

        scheduler = SchedulerService()
        await scheduler.start()

    yield

    # Shutdown
    # Signal SSE streams to close so uvicorn can complete graceful shutdown/reload
    from src.api.routes.activity_stream import signal_shutdown

    signal_shutdown()

    if scheduler:
        await scheduler.stop()
    await close_db()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        settings: Optional settings override (uses get_settings() if not provided)

    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Aether",
        description="Agentic Home Automation System for Home Assistant",
        version="0.1.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Configure CORS — restrict methods and headers in non-development
    allowed_methods = ["*"] if settings.environment in ("development", "testing") else [
        "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS",
    ]
    allowed_headers = ["*"] if settings.environment in ("development", "testing") else [
        "Authorization", "Content-Type", "X-API-Key", "X-Correlation-ID",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_allowed_origins(settings),
        allow_credentials=True,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
    )

    # Configure rate limiting (T188)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add request body size limit middleware (prevents DoS via oversized payloads)
    app.middleware("http")(_body_size_limit_middleware)

    # Add security headers middleware (outermost = runs on every response)
    app.middleware("http")(_security_headers_middleware)

    # Add correlation ID middleware (must be before routes)
    app.middleware("http")(_correlation_middleware)

    # Add request tracing middleware (lazy import to avoid circular dependency)
    from src.api.middleware import RequestTracingMiddleware

    app.add_middleware(RequestTracingMiddleware)

    # Register routes with API key authentication
    # Auth is applied globally but exempts health endpoints (handled in auth.py)
    app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])

    # Add exception handlers
    _register_exception_handlers(app)

    return app


def _get_allowed_origins(settings: Settings) -> list[str]:
    """Get allowed CORS origins based on environment.

    Priority:
    1. Explicit ALLOWED_ORIGINS env var (comma-separated)
    2. Environment-based defaults

    Args:
        settings: Application settings

    Returns:
        List of allowed origins
    """
    # Explicit override
    if settings.allowed_origins:
        return [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

    # Environment-based defaults
    if settings.environment in ("development", "testing"):
        return ["*"]
    elif settings.environment == "staging":
        return [
            "http://localhost:3000",
            "http://localhost:8080",
            settings.ha_url,
        ]
    else:
        # Production: only allow HA instance + WebAuthn origin
        origins = [settings.ha_url]
        if settings.webauthn_origin and settings.webauthn_origin not in origins:
            origins.append(settings.webauthn_origin)
        return origins


async def _body_size_limit_middleware(request: Request, call_next):
    """Middleware to reject requests with oversized bodies.

    Prevents denial-of-service attacks via large payloads.
    WebSocket upgrade requests are exempt.

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler

    Returns:
        Response, or 413 if content-length exceeds the limit
    """
    from fastapi.responses import JSONResponse

    from src.api.rate_limit import MAX_REQUEST_BODY_BYTES

    # Skip WebSocket upgrades
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": 413,
                    "message": f"Request body too large. Maximum size is {MAX_REQUEST_BODY_BYTES} bytes.",
                    "type": "request_too_large",
                }
            },
        )

    return await call_next(request)


async def _security_headers_middleware(request: Request, call_next):
    """Middleware to add security-related HTTP headers.

    Adds headers that protect against common web vulnerabilities:
    - XSS, MIME sniffing, clickjacking, referrer leakage
    - HSTS for transport security (production/staging)
    - CSP to restrict resource loading
    - Permissions-Policy to restrict browser features

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler

    Returns:
        Response with security headers
    """
    settings = get_settings()
    response = await call_next(request)

    # Prevent MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # XSS protection (legacy browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # HSTS: enforce HTTPS in production/staging (browsers will refuse HTTP after first visit)
    if settings.environment in ("production", "staging"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    # Content-Security-Policy: restrict resource loading to same origin
    # API endpoints return JSON, so a strict CSP is appropriate.
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'"
    )

    # Permissions-Policy: disable unnecessary browser features
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )

    # Prevent caching of API responses
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

    return response


async def _correlation_middleware(request: Request, call_next):
    """Middleware to generate and propagate correlation IDs.

    Generates a correlation ID at the start of each request and stores it
    in a context variable. Also includes it in response headers.

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in the chain

    Returns:
        Response with X-Correlation-ID header
    """
    # Check if correlation ID is provided in request header
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    # Store in context variable for use by exceptions
    _correlation_id.set(correlation_id)

    # Process request
    response = await call_next(request)

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    return response


def get_correlation_id() -> str | None:
    """Get the current request's correlation ID from context.

    Returns:
        Correlation ID string or None if not in request context
    """
    return _correlation_id.get()


def _register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers.

    Args:
        app: FastAPI application
    """
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse

    @app.exception_handler(AetherError)
    async def aether_error_handler(
        request: Request,
        exc: AetherError,
    ) -> JSONResponse:
        """Handle Aether application errors with correlation ID."""
        # Use correlation ID from exception or context
        correlation_id = exc.correlation_id or get_correlation_id() or str(uuid.uuid4())

        # Determine error type and status code
        error_type = exc.__class__.__name__.replace("Error", "_error").lower()
        status_code = 500

        if isinstance(exc, AetherError):
            # Map specific error types to status codes
            if isinstance(exc, ValidationError):
                status_code = 400
            elif isinstance(exc, ConfigurationError):
                status_code = 500
            elif isinstance(exc, HAClientError) and exc.status_code:
                status_code = exc.status_code
            elif isinstance(exc, HAClientError):
                status_code = 502  # Bad Gateway for HA client errors

        # Log the error
        import structlog

        logger = structlog.get_logger()
        logger.error(
            "Aether error",
            error_type=error_type,
            correlation_id=correlation_id,
            exc_info=exc,
        )

        # Sanitize error message for non-debug environments
        message = str(exc) if settings.debug else f"An error occurred. Correlation ID: {correlation_id}"
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": status_code,
                    "message": message,
                    "type": error_type,
                    "correlation_id": correlation_id,
                }
            },
            headers={"X-Correlation-ID": correlation_id},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        """Handle HTTP exceptions with consistent format."""
        correlation_id = get_correlation_id() or str(uuid.uuid4())
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "http_error",
                    "correlation_id": correlation_id,
                }
            },
            headers={"X-Correlation-ID": correlation_id},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        settings = get_settings()
        correlation_id = get_correlation_id() or str(uuid.uuid4())

        # Log the error
        import structlog

        logger = structlog.get_logger()
        logger.exception(
            "Unhandled exception",
            correlation_id=correlation_id,
            exc_info=exc,
        )

        # Return sanitized response
        detail = str(exc) if settings.debug else "Internal server error"
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": 500,
                    "message": detail,
                    "type": "internal_error",
                    "correlation_id": correlation_id,
                }
            },
            headers={"X-Correlation-ID": correlation_id},
        )


def get_app() -> FastAPI:
    """Get or create the singleton FastAPI application.

    Returns:
        FastAPI application instance
    """
    global _app
    if _app is None:
        _app = create_app()
    return _app


# For uvicorn: use "src.api.main:get_app" with --factory flag,
# or "src.api.main:app" which lazily initializes on first access.
def __getattr__(name: str) -> Any:
    """Module-level __getattr__ for lazy app initialization.

    Only creates the app when 'app' is accessed, not at import time.
    This prevents DB/MLflow connections from being triggered during imports,
    which would break test environments.
    """
    if name == "app":
        return get_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
