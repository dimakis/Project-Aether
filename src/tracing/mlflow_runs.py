"""MLflow run management: start_run, end_run, start_experiment_run, get_active_run."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from src.tracing.mlflow_init import (
    _ensure_mlflow_initialized,
    _safe_import_mlflow,
    get_or_create_experiment,
)


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
        import logging

        logging.getLogger(__name__).debug(f"Failed to start run: {e}")
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
        import logging

        logging.getLogger(__name__).debug(f"Failed to end run: {e}")


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
