"""FastAPI application configuration and setup.

Main entry point for the HTTP API with CORS, middleware,
rate limiting, and lifecycle management.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter
from src.api.routes import api_router
from src.settings import Settings, get_settings
from src.storage import close_db, init_db
from src.tracing import init_mlflow

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

    # Initialize MLflow (Constitution: Observability)
    init_mlflow()

    # Initialize database (Constitution: State)
    if settings.environment != "testing":
        await init_db()

    # Start scheduler (Feature 10: Scheduled & Event-Driven Insights)
    scheduler = None
    if settings.scheduler_enabled and settings.environment != "testing":
        from src.scheduler import SchedulerService

        scheduler = SchedulerService()
        await scheduler.start()

    yield

    # Shutdown
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

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_allowed_origins(settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure rate limiting (T188)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Register routes
    app.include_router(api_router, prefix="/api/v1")

    # Add exception handlers
    _register_exception_handlers(app)

    return app


def _get_allowed_origins(settings: Settings) -> list[str]:
    """Get allowed CORS origins based on environment.

    Args:
        settings: Application settings

    Returns:
        List of allowed origins
    """
    if settings.environment == "development":
        return ["*"]
    elif settings.environment == "staging":
        return [
            "http://localhost:3000",
            "http://localhost:8080",
            settings.ha_url,
        ]
    else:
        # Production: only allow HA instance
        return [settings.ha_url]


def _register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers.

    Args:
        app: FastAPI application
    """
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        """Handle HTTP exceptions with consistent format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "http_error",
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        settings = get_settings()

        # Log the error
        import structlog

        logger = structlog.get_logger()
        logger.exception("Unhandled exception", exc_info=exc)

        # Return sanitized response
        detail = str(exc) if settings.debug else "Internal server error"
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": 500,
                    "message": detail,
                    "type": "internal_error",
                }
            },
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


# For uvicorn: uvicorn src.api.main:app
app = get_app()
