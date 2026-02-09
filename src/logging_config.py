"""Logging configuration for Project Aether.

Provides structured logging with appropriate levels for application
code vs third-party libraries.
"""

# FIRST: Suppress noisy loggers BEFORE any other imports
# This must happen before mlflow is imported anywhere
import logging
import warnings

logging.getLogger("mlflow").setLevel(logging.WARNING)
logging.getLogger("mlflow.types").setLevel(logging.ERROR)
logging.getLogger("mlflow.types.type_hints").setLevel(logging.ERROR)
logging.getLogger("mlflow.models.signature").setLevel(logging.ERROR)

# Suppress MLflow type-hint warnings emitted via warnings.warn()
warnings.filterwarnings("ignore", module=r"mlflow\.types\.type_hints")
warnings.filterwarnings("ignore", module=r"mlflow\.models\.signature")
warnings.filterwarnings(
    "ignore",
    message=r"Union type hint.*inferred as AnyType",
    category=UserWarning,
)
logging.getLogger("alembic").setLevel(logging.WARNING)

import sys
from typing import Literal

from src.settings import get_settings

# List of noisy third-party loggers to suppress
NOISY_LOGGERS = [
    "alembic",
    "alembic.runtime",
    "alembic.runtime.migration",
    "alembic.runtime.plugins",
    "httpcore",
    "httpx",
    "urllib3",
    "asyncio",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "mlflow",
    # MLflow's internal type inference logs warnings about its own Union types
    # (ResponsesAgentRequest, ResponsesAgentResponse) - not our code
    "mlflow.types.type_hints",
    # MLflow model signature inference warnings about Union type hints
    "mlflow.models.signature",
    # MLflow tracing modules - suppress trace send errors
    "mlflow.tracing",
    "mlflow.tracing.export",
    "mlflow.tracing.processor",
    "mlflow.tracking._tracking_service.client",
]

# Per-logger levels for noisy libraries
NOISY_LOGGER_LEVELS = {
    "mlflow.types.type_hints": logging.ERROR,
    "mlflow.models.signature": logging.ERROR,
    "mlflow.tracing": logging.CRITICAL,
    "mlflow.tracing.export": logging.CRITICAL,
    "mlflow.tracing.processor": logging.CRITICAL,
}


def suppress_noisy_loggers() -> None:
    """Suppress noisy third-party loggers.

    Call this after importing libraries that configure their own logging.
    """
    for logger_name in NOISY_LOGGERS:
        logger = logging.getLogger(logger_name)
        level = NOISY_LOGGER_LEVELS.get(logger_name, logging.WARNING)
        logger.setLevel(level)
        # Clear any handlers added by the library
        logger.handlers.clear()


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] | None = None,
) -> None:
    """Configure application logging.

    Sets up structured logging with:
    - Application logs at configured level
    - Third-party library logs suppressed to WARNING+
    - Clean console output format

    Args:
        level: Override log level (defaults to settings.log_level or INFO)
    """
    settings = get_settings()
    log_level = level or getattr(settings, "log_level", "INFO")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with clean format
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, log_level))

    # Simple format for console
    formatter = logging.Formatter(
        "%(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set application loggers to configured level
    for app_logger in ["src", "aether"]:
        logging.getLogger(app_logger).setLevel(getattr(logging, log_level))

    # Suppress noisy third-party loggers
    suppress_noisy_loggers()


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Configure logging on module import
configure_logging()
