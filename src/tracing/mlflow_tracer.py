"""MLflow tracer: AetherTracer class, get_tracer, get_tracing_status."""

import time
from contextlib import suppress
from types import TracebackType
from typing import Any

from src.tracing.mlflow_init import (
    _current_tracer,
    _ensure_mlflow_initialized,
    _safe_import_mlflow,
    _traces_available,
)
from src.tracing.mlflow_logging import (
    log_metric as _log_metric,
)
from src.tracing.mlflow_logging import (
    log_metrics as _log_metrics,
)
from src.tracing.mlflow_logging import (
    log_param as _log_param,
)
from src.tracing.mlflow_logging import (
    log_params as _log_params,
)
from src.tracing.mlflow_runs import end_run, start_run


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
        _log_metric("workflow.duration_ms", duration_ms)

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
        _log_metric("workflow.duration_ms", duration_ms)

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
            return str(self.run.info.run_id)
        return None

    def log_param(self, key: str, value: object) -> None:
        _log_param(key, value)

    def log_params(self, params: dict[str, object]) -> None:
        _log_params(params)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        _log_metric(key, value, step)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        _log_metrics(metrics, step)

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
    from src.settings import get_settings

    initialized = _ensure_mlflow_initialized()
    settings = get_settings()
    return {
        "tracking_uri": settings.mlflow_tracking_uri,
        "experiment_name": settings.mlflow_experiment_name,
        "mlflow_initialized": initialized,
        "traces_enabled": initialized and _traces_available,
    }
