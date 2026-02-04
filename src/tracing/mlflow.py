"""MLflow experiment setup and tracing decorators.

Provides comprehensive tracing for agent operations, LLM calls,
and data science workflows (Constitution: Observability).

All functions are defensive - they silently skip tracing if MLflow
is unavailable or misconfigured, rather than crashing the application.
"""

import functools
import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Generator, ParamSpec, TypeVar

from src.settings import get_settings

# Type variables for decorator typing
P = ParamSpec("P")
R = TypeVar("R")

# Logger for tracing issues (debug level to avoid noise)
_logger = logging.getLogger(__name__)

# Flag to track if MLflow is available
_mlflow_available: bool = True
_mlflow_initialized: bool = False

# Context variable for current tracer
_current_tracer: ContextVar["AetherTracer | None"] = ContextVar(
    "current_tracer", default=None
)


def _safe_import_mlflow():
    """Safely import MLflow, returning None if unavailable."""
    global _mlflow_available
    if not _mlflow_available:
        return None
    try:
        import mlflow
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
            # Fall back to local directory
            uri = "./mlruns"
            _logger.debug(f"Using fallback MLflow URI: {uri}")
        
        mlflow.set_tracking_uri(uri)
        _mlflow_initialized = True
        return True
    except Exception as e:
        _mlflow_available = False
        _logger.debug(f"MLflow initialization failed: {e}")
        return False


def init_mlflow() -> Any:
    """Initialize MLflow with settings from environment.

    Returns:
        Configured MlflowClient instance or None if unavailable
    """
    if not _ensure_mlflow_initialized():
        return None
    
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return None
    
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
        mlflow.set_tag("aether.started_at", datetime.utcnow().isoformat())

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


def log_param(key: str, value: Any) -> None:
    """Log a parameter to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return
    
    try:
        if mlflow.active_run():
            mlflow.log_param(key, value)
    except Exception as e:
        _logger.debug(f"Failed to log param {key}: {e}")


def log_params(params: dict[str, Any]) -> None:
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


def log_dict(data: dict[str, Any], filename: str) -> None:
    """Log a dictionary as a JSON artifact."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return
    
    try:
        if mlflow.active_run():
            mlflow.log_dict(data, filename)
    except Exception as e:
        _logger.debug(f"Failed to log dict to {filename}: {e}")


def log_agent_action(
    agent: str,
    action: str,
    input_data: dict[str, Any] | None = None,
    output_data: dict[str, Any] | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
) -> None:
    """Log an agent action with structured data."""
    mlflow = _safe_import_mlflow()
    if mlflow is None or not mlflow.active_run():
        return
    
    try:
        mlflow.set_tag(f"agent.{agent}.last_action", action)

        if duration_ms is not None:
            log_metric(f"agent.{agent}.{action}.duration_ms", duration_ms)

        if error:
            mlflow.set_tag(f"agent.{agent}.{action}.error", error[:250])

        # Log detailed data as artifact
        action_data = {
            "agent": agent,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "input": input_data,
            "output": output_data,
            "duration_ms": duration_ms,
            "error": error,
        }
        log_dict(action_data, f"actions/{agent}_{action}_{int(time.time())}.json")
    except Exception as e:
        _logger.debug(f"Failed to log agent action: {e}")


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


def trace_agent(agent_name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to trace agent function execution."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            mlflow = _safe_import_mlflow()

            try:
                if mlflow and mlflow.active_run():
                    mlflow.set_tag(f"agent.{agent_name}.status", "running")
                    log_param(f"agent.{agent_name}.function", func.__name__)

                result = await func(*args, **kwargs)  # type: ignore[misc]

                if mlflow and mlflow.active_run():
                    mlflow.set_tag(f"agent.{agent_name}.status", "completed")
                return result

            except Exception as e:
                if mlflow and mlflow.active_run():
                    mlflow.set_tag(f"agent.{agent_name}.status", "failed")
                    mlflow.set_tag(f"agent.{agent_name}.error", str(e)[:250])
                raise

            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_metric(f"agent.{agent_name}.duration_ms", duration_ms)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            mlflow = _safe_import_mlflow()

            try:
                if mlflow and mlflow.active_run():
                    mlflow.set_tag(f"agent.{agent_name}.status", "running")
                    log_param(f"agent.{agent_name}.function", func.__name__)

                result = func(*args, **kwargs)

                if mlflow and mlflow.active_run():
                    mlflow.set_tag(f"agent.{agent_name}.status", "completed")
                return result

            except Exception as e:
                if mlflow and mlflow.active_run():
                    mlflow.set_tag(f"agent.{agent_name}.status", "failed")
                    mlflow.set_tag(f"agent.{agent_name}.error", str(e)[:250])
                raise

            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_metric(f"agent.{agent_name}.duration_ms", duration_ms)

        if _is_async(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


def trace_llm_call(
    model: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to trace LLM API calls."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            mlflow = _safe_import_mlflow()

            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]

                duration_ms = (time.perf_counter() - start_time) * 1000
                log_metric("llm.call.duration_ms", duration_ms)

                if model and mlflow and mlflow.active_run():
                    mlflow.set_tag("llm.model", model)

                _log_token_usage(result)
                return result

            except Exception as e:
                if mlflow and mlflow.active_run():
                    mlflow.set_tag("llm.call.error", str(e)[:250])
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            mlflow = _safe_import_mlflow()

            try:
                result = func(*args, **kwargs)

                duration_ms = (time.perf_counter() - start_time) * 1000
                log_metric("llm.call.duration_ms", duration_ms)

                if model and mlflow and mlflow.active_run():
                    mlflow.set_tag("llm.model", model)

                _log_token_usage(result)
                return result

            except Exception as e:
                if mlflow and mlflow.active_run():
                    mlflow.set_tag("llm.call.error", str(e)[:250])
                raise

        if _is_async(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


def _log_token_usage(result: Any) -> None:
    """Extract and log token usage from LLM response."""
    mlflow = _safe_import_mlflow()
    if mlflow is None or not mlflow.active_run():
        return

    try:
        # Handle OpenAI-style responses
        if hasattr(result, "usage") and result.usage:
            usage = result.usage
            if hasattr(usage, "prompt_tokens"):
                log_metric("llm.tokens.prompt", usage.prompt_tokens)
            if hasattr(usage, "completion_tokens"):
                log_metric("llm.tokens.completion", usage.completion_tokens)
            if hasattr(usage, "total_tokens"):
                log_metric("llm.tokens.total", usage.total_tokens)

        # Handle LangChain AIMessage with usage_metadata
        if hasattr(result, "usage_metadata") and result.usage_metadata:
            usage = result.usage_metadata
            if "input_tokens" in usage:
                log_metric("llm.tokens.prompt", usage["input_tokens"])
            if "output_tokens" in usage:
                log_metric("llm.tokens.completion", usage["output_tokens"])
    except Exception:
        pass


def trace_with_uri(
    name: str | None = None,
    span_type: str = "UNKNOWN",
    attributes: dict[str, Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Trace a function - ensures MLflow is initialized first.
    
    This is a lightweight wrapper that ensures tracking URI is set.
    If MLflow is unavailable, the function runs without tracing.
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if _is_async(func):
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[misc]
                _ensure_mlflow_initialized()
                return await func(*args, **kwargs)  # type: ignore[misc]
            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            _ensure_mlflow_initialized()
            return func(*args, **kwargs)
        return sync_wrapper

    return decorator


# =============================================================================
# TRACER CLASS
# =============================================================================


class AetherTracer:
    """Context manager for tracing complete workflows.

    Provides a structured way to trace multi-step operations
    with nested runs and automatic cleanup.
    """

    def __init__(
        self,
        name: str,
        experiment_name: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.experiment_name = experiment_name
        self.tags = tags or {}
        self.run: Any = None
        self._start_time: float = 0

    async def __aenter__(self) -> "AetherTracer":
        self._start_time = time.perf_counter()
        self.run = start_run(
            run_name=self.name,
            experiment_name=self.experiment_name,
            tags=self.tags,
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
        self.run = start_run(
            run_name=self.name,
            experiment_name=self.experiment_name,
            tags=self.tags,
        )
        _current_tracer.set(self)
        return self

    def __exit__(
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

    @property
    def run_id(self) -> str | None:
        if self.run and hasattr(self.run, "info"):
            return self.run.info.run_id
        return None

    def log_param(self, key: str, value: Any) -> None:
        log_param(key, value)

    def log_params(self, params: dict[str, Any]) -> None:
        log_params(params)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        log_metric(key, value, step)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        log_metrics(metrics, step)

    def set_tag(self, key: str, value: str) -> None:
        mlflow = _safe_import_mlflow()
        if mlflow and mlflow.active_run():
            try:
                mlflow.set_tag(key, value)
            except Exception:
                pass


def get_tracer() -> AetherTracer | None:
    """Get the current active tracer."""
    return _current_tracer.get()


# Exports
__all__ = [
    "init_mlflow",
    "get_or_create_experiment",
    "start_run",
    "start_experiment_run",
    "end_run",
    "get_active_run",
    "log_param",
    "log_params",
    "log_metric",
    "log_metrics",
    "log_dict",
    "log_agent_action",
    "trace_agent",
    "trace_llm_call",
    "trace_with_uri",
    "get_active_span",
    "add_span_event",
    "AetherTracer",
    "get_tracer",
]
