"""MLflow experiment setup and tracing decorators.

Provides comprehensive tracing for agent operations, LLM calls,
and data science workflows (Constitution: Observability).

All functions are defensive - they silently skip tracing if MLflow
is unavailable or misconfigured, rather than crashing the application.
"""

# IMPORTANT: Set MLflow environment variables BEFORE any imports that might
# trigger MLflow initialization. This prevents trace logging from stalling
# the CLI if the server is unreachable or returns errors.
import os

os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "3")
os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
# Disable async trace logging to get immediate feedback on failures
os.environ.setdefault("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "false")

import functools
import importlib.util
import logging
import time
import warnings
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, ParamSpec, TypeVar

from src.settings import get_settings

# Type variables for decorator typing
P = ParamSpec("P")
R = TypeVar("R")

# Logger for tracing issues (debug level to avoid noise)
_logger = logging.getLogger(__name__)

# Flag to track if MLflow is available
_mlflow_available: bool = True
_mlflow_initialized: bool = False
_autolog_enabled: bool = False
_traces_available: bool = True
_traces_checked: bool = False

# Context variable for current tracer
_current_tracer: ContextVar["AetherTracer | None"] = ContextVar("current_tracer", default=None)


def _safe_import_mlflow():
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
        pass

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


def init_mlflow() -> Any:
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

        return experiment_id
    except Exception as e:
        _logger.debug(f"Failed to get/create experiment: {e}")
        return None


def start_run(
    run_name: str | None = None,
    experiment_name: str | None = None,
    tags: dict[str, str] | None = None,
    nested: bool = False,
) -> Any:
    """Start a new MLflow run.

    Args:
        run_name: Optional name for the run
        experiment_name: Experiment to log to (default from settings)
        tags: Optional tags to add to the run
        nested: Whether this is a nested run

    Returns:
        Active MLflow Run or None if unavailable
    """
    if not _ensure_mlflow_initialized():
        return None

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return None

    try:
        experiment_id = get_or_create_experiment(experiment_name)
        if experiment_id:
            mlflow.set_experiment(experiment_id=experiment_id)

        run = mlflow.start_run(run_name=run_name, tags=tags, nested=nested)

        # Log standard tags
        mlflow.set_tag("aether.version", "0.1.0")
        mlflow.set_tag("aether.started_at", datetime.now(UTC).isoformat())

        # Log session ID if available
        from src.tracing.context import get_session_id

        session_id = get_session_id()
        if session_id:
            mlflow.set_tag("session.id", session_id)

        return run
    except Exception as e:
        _logger.debug(f"Failed to start run: {e}")
        return None


def end_run(status: str = "FINISHED") -> None:
    """End the current MLflow run.

    Args:
        status: Run status (FINISHED, FAILED, KILLED)
    """
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        mlflow.end_run(status=status)
    except Exception as e:
        _logger.debug(f"Failed to end run: {e}")


@contextmanager
def start_experiment_run(
    run_name: str | None = None,
    experiment_name: str | None = None,
    tags: dict[str, str] | None = None,
) -> Generator[Any, None, None]:
    """Context manager for MLflow runs.

    Automatically ends the run when exiting the context.

    Args:
        run_name: Optional name for the run
        experiment_name: Experiment to log to
        tags: Optional tags

    Yields:
        Active MLflow Run or None if unavailable
    """
    run = start_run(run_name=run_name, experiment_name=experiment_name, tags=tags)
    try:
        yield run
    except Exception:
        end_run(status="FAILED")
        raise
    else:
        end_run(status="FINISHED")


def get_active_run() -> Any:
    """Get the currently active MLflow run.

    Returns:
        Active Run or None if no run is active
    """
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return None

    try:
        return mlflow.active_run()
    except Exception:
        return None


# =============================================================================
# LOGGING UTILITIES
# =============================================================================


def log_param(key: str, value: object) -> None:
    """Log a parameter to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_param(key, value)
    except Exception as e:
        _logger.debug(f"Failed to log param {key}: {e}")


def log_params(params: dict[str, object]) -> None:
    """Log multiple parameters to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_params(params)
    except Exception as e:
        _logger.debug(f"Failed to log params: {e}")


def log_metric(key: str, value: float, step: int | None = None) -> None:
    """Log a metric to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_metric(key, value, step=step)
    except Exception as e:
        _logger.debug(f"Failed to log metric {key}: {e}")


def log_metrics(metrics: dict[str, float], step: int | None = None) -> None:
    """Log multiple metrics to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_metrics(metrics, step=step)
    except Exception as e:
        _logger.debug(f"Failed to log metrics: {e}")


def log_dict(data: dict[str, object], filename: str) -> None:
    """Log a dictionary as a JSON artifact."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_dict(data, filename)
    except Exception as e:
        _logger.debug(f"Failed to log dict to {filename}: {e}")


# =============================================================================
# SPAN UTILITIES
# =============================================================================


def get_active_span() -> Any | None:
    """Return the current active span if supported by this MLflow version."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return None

    try:
        # MLflow 3.x uses get_current_active_span()
        get_span = getattr(mlflow, "get_current_active_span", None)
        if get_span:
            return get_span()
        # Fallback for older versions
        active_span = getattr(mlflow, "active_span", None)
        if active_span:
            return active_span()
    except Exception:
        pass
    return None


def add_span_event(
    span: Any,
    name: str,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Add an event to a span (MLflow 3.x compatible).

    MLflow 3.x changed add_event() to require a SpanEvent object.
    This helper provides a backward-compatible interface.
    """
    if span is None or not hasattr(span, "add_event"):
        return

    try:
        from mlflow.entities import SpanEvent

        event = SpanEvent(name=name, attributes=attributes or {})
        span.add_event(event)
    except (ImportError, TypeError, Exception) as e:
        _logger.debug(f"Failed to add span event: {e}")


# =============================================================================
# DECORATORS
# =============================================================================


def _is_async(func: Callable[..., Any]) -> bool:
    """Check if a function is async."""
    import asyncio
    import inspect

    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)


def trace_with_uri(
    name: str | None = None,
    span_type: str = "UNKNOWN",
    attributes: dict[str, Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Trace a function with an MLflow span.

    Creates a proper MLflow span for the decorated function, capturing
    timing, errors, and custom attributes. If MLflow is unavailable,
    the function runs without tracing.

    Args:
        name: Span name (defaults to function name)
        span_type: Type of span (CHAIN, TOOL, LLM, RETRIEVER, etc.)
        attributes: Additional attributes to attach to the span

    Returns:
        Decorated function with tracing
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        span_name = name or func.__name__
        traced_func: Callable[..., Any] | None = None

        def _get_traced(mlflow: Any) -> Callable[..., Any] | None:
            nonlocal traced_func
            if traced_func is not None:
                return traced_func
            if hasattr(mlflow, "trace"):
                traced_func = mlflow.trace(
                    func,
                    name=span_name,
                    span_type=span_type,
                    attributes=attributes,
                )
                return traced_func
            return None

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[misc]
            global _traces_available
            if not _ensure_mlflow_initialized():
                return await func(*args, **kwargs)  # type: ignore[misc]

            if not _traces_available:
                return await func(*args, **kwargs)  # type: ignore[misc]

            mlflow = _safe_import_mlflow()
            if mlflow is None:
                return await func(*args, **kwargs)  # type: ignore[misc]

            try:
                traced = _get_traced(mlflow)
                if traced is not None:
                    return await traced(*args, **kwargs)  # type: ignore[misc]

                # Fallback for older MLflow versions without trace()
                with mlflow.start_span(
                    name=span_name,
                    span_type=span_type,
                    attributes=attributes,
                ):
                    return await func(*args, **kwargs)  # type: ignore[misc]
            except Exception as e:
                _disable_traces("span creation failed; backend rejected traces")
                _logger.debug(f"Span creation failed, running without trace: {e}")
                return await func(*args, **kwargs)  # type: ignore[misc]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            global _traces_available
            if not _ensure_mlflow_initialized():
                return func(*args, **kwargs)

            if not _traces_available:
                return func(*args, **kwargs)

            mlflow = _safe_import_mlflow()
            if mlflow is None:
                return func(*args, **kwargs)

            try:
                traced = _get_traced(mlflow)
                if traced is not None:
                    return traced(*args, **kwargs)

                # Fallback for older MLflow versions without trace()
                with mlflow.start_span(
                    name=span_name,
                    span_type=span_type,
                    attributes=attributes,
                ):
                    return func(*args, **kwargs)
            except Exception as e:
                _disable_traces("span creation failed; backend rejected traces")
                _logger.debug(f"Span creation failed, running without trace: {e}")
                return func(*args, **kwargs)

        if _is_async(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


# =============================================================================
# TRACER CLASS
# =============================================================================


class AetherTracer:
    """Context manager for tracing complete workflows.

    Provides a structured way to trace multi-step operations
    with nested runs and automatic cleanup. Automatically captures
    session ID for trace correlation.
    """

    def __init__(
        self,
        name: str,
        experiment_name: str | None = None,
        tags: dict[str, str] | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize tracer.

        Args:
            name: Name for the MLflow run
            experiment_name: Experiment to log to
            tags: Additional tags
            session_id: Optional session ID (auto-captured if not provided)
        """
        self.name = name
        self.experiment_name = experiment_name
        self.tags = tags or {}
        self._session_id = session_id
        self.run: Any = None
        self._start_time: float = 0

    @property
    def session_id(self) -> str | None:
        """Get the session ID for this tracer."""
        if self._session_id:
            return self._session_id

        # Try to get from context
        try:
            from src.tracing.context import get_session_id

            return get_session_id()
        except Exception:
            return None

    async def __aenter__(self) -> "AetherTracer":
        self._start_time = time.perf_counter()

        # Add session ID to tags
        tags = dict(self.tags)
        if self.session_id:
            tags["session.id"] = self.session_id

        self.run = start_run(
            run_name=self.name,
            experiment_name=self.experiment_name,
            tags=tags,
        )
        _current_tracer.set(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        mlflow = _safe_import_mlflow()
        duration_ms = (time.perf_counter() - self._start_time) * 1000
        log_metric("workflow.duration_ms", duration_ms)

        if exc_type is not None:
            if mlflow and mlflow.active_run():
                mlflow.set_tag("workflow.status", "failed")
                mlflow.set_tag("workflow.error", str(exc_val)[:250] if exc_val else "")
            end_run(status="FAILED")
        else:
            if mlflow and mlflow.active_run():
                mlflow.set_tag("workflow.status", "completed")
            end_run(status="FINISHED")

        _current_tracer.set(None)

    def __enter__(self) -> "AetherTracer":
        self._start_time = time.perf_counter()

        # Add session ID to tags
        tags = dict(self.tags)
        if self.session_id:
            tags["session.id"] = self.session_id

        self.run = start_run(
            run_name=self.name,
            experiment_name=self.experiment_name,
            tags=tags,
        )
        _current_tracer.set(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        mlflow = _safe_import_mlflow()
        duration_ms = (time.perf_counter() - self._start_time) * 1000
        log_metric("workflow.duration_ms", duration_ms)

        if exc_type is not None:
            if mlflow and mlflow.active_run():
                mlflow.set_tag("workflow.status", "failed")
                mlflow.set_tag("workflow.error", str(exc_val)[:250] if exc_val else "")
            end_run(status="FAILED")
        else:
            if mlflow and mlflow.active_run():
                mlflow.set_tag("workflow.status", "completed")
            end_run(status="FINISHED")

        _current_tracer.set(None)

    @property
    def run_id(self) -> str | None:
        if self.run and hasattr(self.run, "info"):
            return self.run.info.run_id
        return None

    def log_param(self, key: str, value: object) -> None:
        log_param(key, value)

    def log_params(self, params: dict[str, object]) -> None:
        log_params(params)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        log_metric(key, value, step)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        log_metrics(metrics, step)

    def set_tag(self, key: str, value: str) -> None:
        mlflow = _safe_import_mlflow()
        if mlflow and mlflow.active_run():
            with suppress(Exception):
                mlflow.set_tag(key, value)


def get_tracer() -> AetherTracer | None:
    """Get the current active tracer."""
    return _current_tracer.get()


def get_tracing_status() -> dict[str, object]:
    """Return current MLflow tracing configuration and status."""
    initialized = _ensure_mlflow_initialized()
    settings = get_settings()
    return {
        "tracking_uri": settings.mlflow_tracking_uri,
        "experiment_name": settings.mlflow_experiment_name,
        "mlflow_initialized": initialized,
        "traces_enabled": initialized and _traces_available,
    }


# Exports
__all__ = [
    "AetherTracer",
    "add_span_event",
    "enable_autolog",
    "end_run",
    "get_active_run",
    "get_active_span",
    "get_or_create_experiment",
    "get_tracer",
    "get_tracing_status",
    "init_mlflow",
    "log_dict",
    "log_metric",
    "log_metrics",
    "log_param",
    "log_params",
    "start_experiment_run",
    "start_run",
    "trace_with_uri",
]
