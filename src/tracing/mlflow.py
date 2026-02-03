"""MLflow experiment setup and tracing decorators.

Provides comprehensive tracing for agent operations, LLM calls,
and data science workflows (Constitution: Observability).
"""

import functools
import time
from collections.abc import Callable
from contextvars import ContextVar
from datetime import datetime
from typing import Any, ParamSpec, TypeVar

import mlflow
from mlflow.entities import Run
from mlflow.tracking import MlflowClient

from src.settings import get_settings

# Type variables for decorator typing
P = ParamSpec("P")
R = TypeVar("R")

# Context variable for current tracer
_current_tracer: ContextVar["AetherTracer | None"] = ContextVar(
    "current_tracer", default=None
)


def init_mlflow() -> MlflowClient:
    """Initialize MLflow with settings from environment.

    Returns:
        Configured MlflowClient instance
    """
    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    return MlflowClient(tracking_uri=settings.mlflow_tracking_uri)


def get_or_create_experiment(name: str | None = None) -> str:
    """Get or create an MLflow experiment.

    Args:
        name: Experiment name (defaults to settings.mlflow_experiment_name)

    Returns:
        Experiment ID
    """
    settings = get_settings()
    experiment_name = name or settings.mlflow_experiment_name

    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        experiment_id = mlflow.create_experiment(experiment_name)
    else:
        experiment_id = experiment.experiment_id

    return experiment_id


def start_run(
    run_name: str | None = None,
    experiment_name: str | None = None,
    tags: dict[str, str] | None = None,
    nested: bool = False,
) -> Run:
    """Start a new MLflow run.

    Args:
        run_name: Optional name for the run
        experiment_name: Experiment to log to (default from settings)
        tags: Optional tags to add to the run
        nested: Whether this is a nested run

    Returns:
        Active MLflow Run
    """
    experiment_id = get_or_create_experiment(experiment_name)
    mlflow.set_experiment(experiment_id=experiment_id)

    run = mlflow.start_run(run_name=run_name, tags=tags, nested=nested)

    # Log standard tags
    mlflow.set_tag("aether.version", "0.1.0")
    mlflow.set_tag("aether.started_at", datetime.utcnow().isoformat())

    return run


def end_run(status: str = "FINISHED") -> None:
    """End the current MLflow run.

    Args:
        status: Run status (FINISHED, FAILED, KILLED)
    """
    mlflow.end_run(status=status)


from contextlib import contextmanager
from typing import Generator


@contextmanager
def start_experiment_run(
    run_name: str | None = None,
    experiment_name: str | None = None,
    tags: dict[str, str] | None = None,
) -> Generator[Run, None, None]:
    """Context manager for MLflow runs.

    Automatically ends the run when exiting the context.

    Args:
        run_name: Optional name for the run
        experiment_name: Experiment to log to
        tags: Optional tags

    Yields:
        Active MLflow Run

    Example:
        with start_experiment_run("my_experiment") as run:
            mlflow.log_metric("accuracy", 0.95)
    """
    run = start_run(run_name=run_name, experiment_name=experiment_name, tags=tags)
    try:
        yield run
    except Exception:
        end_run(status="FAILED")
        raise
    else:
        end_run(status="FINISHED")


def get_active_run() -> Run | None:
    """Get the currently active MLflow run.

    Returns:
        Active Run or None if no run is active
    """
    return mlflow.active_run()


# =============================================================================
# LOGGING UTILITIES
# =============================================================================


def log_param(key: str, value: Any) -> None:
    """Log a parameter to the active run.

    Args:
        key: Parameter name
        value: Parameter value
    """
    if mlflow.active_run():
        mlflow.log_param(key, value)


def log_params(params: dict[str, Any]) -> None:
    """Log multiple parameters to the active run.

    Args:
        params: Dictionary of parameter names to values
    """
    if mlflow.active_run():
        mlflow.log_params(params)


def log_metric(key: str, value: float, step: int | None = None) -> None:
    """Log a metric to the active run.

    Args:
        key: Metric name
        value: Metric value
        step: Optional step number
    """
    if mlflow.active_run():
        mlflow.log_metric(key, value, step=step)


def log_metrics(metrics: dict[str, float], step: int | None = None) -> None:
    """Log multiple metrics to the active run.

    Args:
        metrics: Dictionary of metric names to values
        step: Optional step number
    """
    if mlflow.active_run():
        mlflow.log_metrics(metrics, step=step)


def log_dict(data: dict[str, Any], filename: str) -> None:
    """Log a dictionary as a JSON artifact.

    Args:
        data: Dictionary to log
        filename: Artifact filename (should end in .json)
    """
    if mlflow.active_run():
        mlflow.log_dict(data, filename)


def log_agent_action(
    agent: str,
    action: str,
    input_data: dict[str, Any] | None = None,
    output_data: dict[str, Any] | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
) -> None:
    """Log an agent action with structured data.

    Args:
        agent: Agent name (librarian, architect, etc.)
        action: Action being performed
        input_data: Input to the action
        output_data: Output from the action
        duration_ms: Duration in milliseconds
        error: Error message if failed
    """
    if not mlflow.active_run():
        return

    mlflow.set_tag(f"agent.{agent}.last_action", action)

    if duration_ms is not None:
        log_metric(f"agent.{agent}.{action}.duration_ms", duration_ms)

    if error:
        mlflow.set_tag(f"agent.{agent}.{action}.error", error[:250])  # Truncate

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


# =============================================================================
# DECORATORS
# =============================================================================


def trace_agent(agent_name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to trace agent function execution.

    Usage:
        @trace_agent("librarian")
        async def discover_entities(state: DiscoveryState) -> DiscoveryState:
            ...

    Args:
        agent_name: Name of the agent for logging

    Returns:
        Decorated function
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            error_msg: str | None = None

            try:
                # Log start
                mlflow.set_tag(f"agent.{agent_name}.status", "running")
                log_param(f"agent.{agent_name}.function", func.__name__)

                result = await func(*args, **kwargs)  # type: ignore[misc]

                mlflow.set_tag(f"agent.{agent_name}.status", "completed")
                return result

            except Exception as e:
                error_msg = str(e)
                mlflow.set_tag(f"agent.{agent_name}.status", "failed")
                mlflow.set_tag(f"agent.{agent_name}.error", error_msg[:250])
                raise

            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_metric(f"agent.{agent_name}.duration_ms", duration_ms)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            error_msg: str | None = None

            try:
                mlflow.set_tag(f"agent.{agent_name}.status", "running")
                log_param(f"agent.{agent_name}.function", func.__name__)

                result = func(*args, **kwargs)

                mlflow.set_tag(f"agent.{agent_name}.status", "completed")
                return result

            except Exception as e:
                error_msg = str(e)
                mlflow.set_tag(f"agent.{agent_name}.status", "failed")
                mlflow.set_tag(f"agent.{agent_name}.error", error_msg[:250])
                raise

            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_metric(f"agent.{agent_name}.duration_ms", duration_ms)

        # Return appropriate wrapper based on function type
        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


def trace_llm_call(
    model: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to trace LLM API calls.

    Logs token usage, latency, and model info.

    Usage:
        @trace_llm_call(model="gpt-4o")
        async def generate_response(prompt: str) -> str:
            ...

    Args:
        model: Model name (optional, can be inferred from response)

    Returns:
        Decorated function
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]

                # Log LLM metrics
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_metric("llm.call.duration_ms", duration_ms)

                if model:
                    mlflow.set_tag("llm.model", model)

                # Try to extract token usage from result
                _log_token_usage(result)

                return result

            except Exception as e:
                mlflow.set_tag("llm.call.error", str(e)[:250])
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)

                duration_ms = (time.perf_counter() - start_time) * 1000
                log_metric("llm.call.duration_ms", duration_ms)

                if model:
                    mlflow.set_tag("llm.model", model)

                _log_token_usage(result)

                return result

            except Exception as e:
                mlflow.set_tag("llm.call.error", str(e)[:250])
                raise

        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator


def _log_token_usage(result: Any) -> None:
    """Extract and log token usage from LLM response."""
    if not mlflow.active_run():
        return

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


def asyncio_iscoroutinefunction(func: Callable[..., Any]) -> bool:
    """Check if a function is an async coroutine function."""
    import asyncio
    import inspect

    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)


# =============================================================================
# TRACER CLASS
# =============================================================================


class AetherTracer:
    """Context manager for tracing complete workflows.

    Provides a structured way to trace multi-step operations
    with nested runs and automatic cleanup.

    Usage:
        async with AetherTracer("discovery") as tracer:
            tracer.log_param("domain_count", 5)
            await discover_entities()
            tracer.log_metric("entities_found", 42)
    """

    def __init__(
        self,
        name: str,
        experiment_name: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Initialize the tracer.

        Args:
            name: Run name
            experiment_name: Experiment to log to
            tags: Additional tags
        """
        self.name = name
        self.experiment_name = experiment_name
        self.tags = tags or {}
        self.run: Run | None = None
        self._start_time: float = 0

    async def __aenter__(self) -> "AetherTracer":
        """Enter the tracing context."""
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
        """Exit the tracing context."""
        duration_ms = (time.perf_counter() - self._start_time) * 1000
        log_metric("workflow.duration_ms", duration_ms)

        if exc_type is not None:
            mlflow.set_tag("workflow.status", "failed")
            mlflow.set_tag("workflow.error", str(exc_val)[:250] if exc_val else "")
            end_run(status="FAILED")
        else:
            mlflow.set_tag("workflow.status", "completed")
            end_run(status="FINISHED")

        _current_tracer.set(None)

    def __enter__(self) -> "AetherTracer":
        """Sync enter for non-async contexts."""
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
        """Sync exit for non-async contexts."""
        duration_ms = (time.perf_counter() - self._start_time) * 1000
        log_metric("workflow.duration_ms", duration_ms)

        if exc_type is not None:
            mlflow.set_tag("workflow.status", "failed")
            mlflow.set_tag("workflow.error", str(exc_val)[:250] if exc_val else "")
            end_run(status="FAILED")
        else:
            mlflow.set_tag("workflow.status", "completed")
            end_run(status="FINISHED")

        _current_tracer.set(None)

    @property
    def run_id(self) -> str | None:
        """Get the current run ID."""
        return self.run.info.run_id if self.run else None

    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter."""
        log_param(key, value)

    def log_params(self, params: dict[str, Any]) -> None:
        """Log multiple parameters."""
        log_params(params)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        """Log a metric."""
        log_metric(key, value, step)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        """Log multiple metrics."""
        log_metrics(metrics, step)

    def set_tag(self, key: str, value: str) -> None:
        """Set a tag on the run."""
        if mlflow.active_run():
            mlflow.set_tag(key, value)


def get_tracer() -> AetherTracer | None:
    """Get the current active tracer.

    Returns:
        Active AetherTracer or None
    """
    return _current_tracer.get()


# Exports
__all__ = [
    "init_mlflow",
    "get_or_create_experiment",
    "start_run",
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
    "AetherTracer",
    "get_tracer",
]
