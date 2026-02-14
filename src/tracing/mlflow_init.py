"""MLflow initialization, safe import, and module-level globals.

Provides _safe_import_mlflow, _ensure_mlflow_initialized, _check_trace_backend,
_disable_traces, enable_autolog, init_mlflow, get_or_create_experiment.
"""

from __future__ import annotations

# IMPORTANT: Set MLflow environment variables BEFORE any imports that might
# trigger MLflow initialization. This prevents trace logging from stalling
# the CLI if the server is unreachable or returns errors.
import os

os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "3")
os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
# Disable async trace logging to get immediate feedback on failures
os.environ.setdefault("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "false")

import importlib.util
import logging
import warnings
from contextvars import ContextVar
from typing import TYPE_CHECKING, cast

from src.settings import get_settings

if TYPE_CHECKING:
    import types

    from src.tracing.mlflow_tracer import AetherTracer

_logger = logging.getLogger(__name__)

# Flag to track if MLflow is available
_mlflow_available: bool = True
_mlflow_initialized: bool = False
_autolog_enabled: bool = False
_traces_available: bool = True
_traces_checked: bool = False

# Context variable for current tracer
_current_tracer: ContextVar[AetherTracer | None] = ContextVar("current_tracer", default=None)


def _safe_import_mlflow() -> types.ModuleType | None:
    """Safely import MLflow, returning None if unavailable."""
    global _mlflow_available
    if not _mlflow_available:
        return None
    try:
        warnings.filterwarnings(
            "ignore",
            message=r"Union type hint.*inferred as AnyType",
            category=UserWarning,
        )
        import mlflow

        # Re-suppress noisy loggers after MLflow configures its own
        from src.logging_config import suppress_noisy_loggers

        suppress_noisy_loggers()
        return mlflow
    except ImportError:
        _mlflow_available = False
        _logger.debug("MLflow not installed, tracing disabled")
        return None


def _ensure_mlflow_initialized() -> bool:
    """Ensure MLflow is initialized with correct tracking URI.

    Returns:
        True if MLflow is ready, False otherwise
    """
    global _mlflow_initialized, _mlflow_available

    if not _mlflow_available:
        return False

    if _mlflow_initialized:
        return True

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return False

    try:
        settings = get_settings()
        uri = settings.mlflow_tracking_uri

        # Ensure URI is valid
        if not uri or uri.startswith("/mlflow"):
            # Fall back to HTTP server (matches containerized MLflow in compose.yaml)
            uri = "http://localhost:5002"
            _logger.debug(f"Using fallback MLflow URI: {uri}")

        mlflow.set_tracking_uri(uri)
        _check_trace_backend(uri)
        _mlflow_initialized = True
        return True
    except Exception as e:
        _mlflow_available = False
        _logger.debug(f"MLflow initialization failed: {e}")
        return False


def _check_trace_backend(uri: str) -> None:
    """Detect whether the MLflow backend supports trace ingestion.

    We enable traces by default and rely on graceful degradation:
    - If the server is unreachable, traces are disabled
    - If trace calls fail at runtime, they're caught and traces are disabled
    - Users can disable traces with MLFLOW_DISABLE_TRACES=true

    Note: MLflow v3.9.0 has a known bug with PostgreSQL backends that causes
    trace ingestion to fail. Use SQLite backend or set MLFLOW_DISABLE_TRACES=true.
    """
    global _traces_available, _traces_checked
    if _traces_checked:
        return
    _traces_checked = True

    # Allow users to explicitly disable traces
    if os.environ.get("MLFLOW_DISABLE_TRACES", "").lower() in ("true", "1", "yes"):
        _disable_traces("traces disabled via MLFLOW_DISABLE_TRACES")
        return

    # For local file-based backends (sqlite, file), traces work without HTTP
    if not uri or not uri.startswith(("http://", "https://")):
        _traces_available = True
        _logger.debug("MLflow using local backend, traces enabled")
        return

    # For HTTP backends, verify the server is reachable
    try:
        import httpx

        base_url = uri.rstrip("/")
        try:
            health_response = httpx.get(f"{base_url}/health", timeout=2.0)
            if health_response.status_code >= 500:
                _disable_traces(f"MLflow server unhealthy: status {health_response.status_code}")
                return
        except httpx.RequestError as e:
            _disable_traces(f"MLflow server unreachable: {e}")
            return

        # Server is healthy, enable traces
        _traces_available = True
        _logger.debug("MLflow HTTP trace backend enabled")
    except Exception as e:
        _disable_traces(f"trace backend check failed: {e}")


def _disable_traces(reason: str) -> None:
    """Disable MLflow trace logging for this process.

    Sets multiple environment variables to ensure traces are fully disabled
    and won't cause further errors or retries.
    """
    global _traces_available
    if not _traces_available:
        return  # Already disabled

    _traces_available = False
    os.environ["MLFLOW_TRACE_SAMPLING_RATIO"] = "0"
    os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "false"
    os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "0"

    # Also try to disable via MLflow's API if available
    try:
        mlflow = _safe_import_mlflow()
        if mlflow and hasattr(mlflow, "tracing"):
            tracing = mlflow.tracing
            if hasattr(tracing, "disable"):
                tracing.disable()
    except Exception:
        _logger.debug("Failed to disable MLflow tracing via API", exc_info=True)

    _logger.debug("MLflow trace logging disabled: %s", reason)


def enable_autolog() -> None:
    """Enable MLflow auto-tracing for supported libraries.

    Enables automatic tracing for:
    - OpenAI API calls (via mlflow.openai.autolog)
    - LangChain operations (via mlflow.langchain.autolog)

    This is idempotent - calling multiple times has no effect.
    """
    global _autolog_enabled

    if _autolog_enabled:
        return

    if not _ensure_mlflow_initialized():
        return

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    trace_enabled = _traces_available

    # Enable OpenAI autolog
    try:
        mlflow.openai.autolog(
            disable=False,
            exclusive=False,
            disable_for_unsupported_versions=True,
            silent=True,
            log_traces=trace_enabled,
        )
        _logger.debug("MLflow OpenAI autolog enabled")
    except AttributeError:
        _logger.debug("MLflow OpenAI autolog not available (mlflow.openai missing)")
    except Exception as e:
        _logger.debug(f"Failed to enable OpenAI autolog: {e}")

    # Enable LangChain autolog only when the optional dependency is installed
    if importlib.util.find_spec("langchain") is not None:
        try:
            mlflow.langchain.autolog(
                disable=False,
                exclusive=False,
                disable_for_unsupported_versions=True,
                silent=True,
                log_traces=trace_enabled,
                log_input_examples=True,  # Capture input messages
                log_model_signatures=True,  # Log model info
            )
            _logger.debug("MLflow LangChain autolog enabled with input logging")
        except AttributeError:
            _logger.debug("MLflow LangChain autolog not available (mlflow.langchain missing)")
        except Exception as e:
            _logger.debug(f"Failed to enable LangChain autolog: {e}")
    else:
        _logger.debug("LangChain not installed; skipping MLflow LangChain autolog")

    _autolog_enabled = True


def init_mlflow() -> object:
    """Initialize MLflow with settings from environment.

    Sets the active experiment, enables autolog, and returns a client.

    Returns:
        Configured MlflowClient instance or None if unavailable
    """
    if not _ensure_mlflow_initialized():
        return None

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return None

    # Set the active experiment so @mlflow.trace() and autolog know where to log.
    # Without this, traces fail with a foreign-key error on the MLflow backend
    # because experiment_id is empty.
    try:
        settings = get_settings()
        experiment_name = settings.mlflow_experiment_name
        get_or_create_experiment(experiment_name)
        mlflow.set_experiment(experiment_name)
        _logger.debug(f"MLflow active experiment set to '{experiment_name}'")
    except Exception as e:
        _logger.debug(f"Failed to set MLflow experiment: {e}")

    # Enable autolog when initializing
    enable_autolog()

    try:
        from mlflow.tracking import MlflowClient

        settings = get_settings()
        return MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    except Exception as e:
        _logger.debug(f"Failed to create MLflow client: {e}")
        return None


def get_or_create_experiment(name: str | None = None) -> str | None:
    """Get or create an MLflow experiment.

    Args:
        name: Experiment name (defaults to settings.mlflow_experiment_name)

    Returns:
        Experiment ID or None if MLflow unavailable
    """
    if not _ensure_mlflow_initialized():
        return None

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return None

    try:
        settings = get_settings()
        experiment_name = name or settings.mlflow_experiment_name

        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(experiment_name)
        else:
            experiment_id = experiment.experiment_id

        return cast("str", experiment_id)
    except Exception as e:
        _logger.debug(f"Failed to get/create experiment: {e}")
        return None
