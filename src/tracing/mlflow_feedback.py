"""MLflow 3.x feedback and assessment: log_human_feedback, log_code_feedback, log_expectation, search_traces."""

import logging
from typing import Any

from src.settings import get_settings
from src.tracing.mlflow_init import (
    _ensure_mlflow_initialized,
    _safe_import_mlflow,
    _traces_available,
)

_logger = logging.getLogger(__name__)


def log_human_feedback(
    trace_id: str,
    name: str,
    value: int | float | str | bool,
    source_id: str = "aether-ui",
    rationale: str | None = None,
) -> None:
    """Log human feedback on an MLflow trace.

    Bridges user-facing feedback (flow grades, ratings) into MLflow's
    assessment system so feedback is visible alongside traces in the UI.

    Args:
        trace_id: MLflow trace ID to attach feedback to
        name: Feedback metric name (e.g. "user_sentiment", "flow_grade")
        value: Feedback value (thumbs up/down, rating, sentiment string)
        source_id: Identifier for the feedback source (default: "aether-ui")
        rationale: Optional explanation for the feedback
    """
    if not _ensure_mlflow_initialized() or not _traces_available:
        return

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        from mlflow.entities import AssessmentSource, AssessmentSourceType

        mlflow.log_feedback(
            trace_id=trace_id,
            name=name,
            value=value,
            source=AssessmentSource(
                source_type=AssessmentSourceType.HUMAN,
                source_id=source_id,
            ),
            rationale=rationale,
        )
        _logger.debug("Logged human feedback '%s' on trace %s", name, trace_id[:12])
    except Exception as e:
        _logger.debug("Failed to log human feedback: %s", e)


def log_code_feedback(
    trace_id: str,
    name: str,
    value: int | float | str | bool,
    source_id: str = "aether-scorer",
    rationale: str | None = None,
) -> None:
    """Log programmatic/code-based feedback on an MLflow trace.

    Used by automated scorers and rule-based checks to record
    evaluation results against traces.

    Args:
        trace_id: MLflow trace ID to attach feedback to
        name: Feedback metric name (e.g. "tool_safety", "latency_ok")
        value: Feedback value
        source_id: Identifier for the scoring system
        rationale: Optional explanation for the score
    """
    if not _ensure_mlflow_initialized() or not _traces_available:
        return

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        from mlflow.entities import AssessmentSource, AssessmentSourceType

        mlflow.log_feedback(
            trace_id=trace_id,
            name=name,
            value=value,
            source=AssessmentSource(
                source_type=AssessmentSourceType.CODE,
                source_id=source_id,
            ),
            rationale=rationale,
        )
        _logger.debug("Logged code feedback '%s' on trace %s", name, trace_id[:12])
    except Exception as e:
        _logger.debug("Failed to log code feedback: %s", e)


def log_expectation(
    trace_id: str,
    name: str,
    value: object,
    source_id: str = "aether-ui",
) -> None:
    """Log a ground-truth expectation on an MLflow trace.

    Records what the correct or expected output should have been,
    enabling evaluation of agent accuracy over time.

    Args:
        trace_id: MLflow trace ID to attach the expectation to
        name: Expectation name (e.g. "expected_approval", "expected_action")
        value: The expected/ground-truth value
        source_id: Identifier for who provided the ground truth
    """
    if not _ensure_mlflow_initialized() or not _traces_available:
        return

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        from mlflow.entities import AssessmentSource, AssessmentSourceType

        mlflow.log_expectation(
            trace_id=trace_id,
            name=name,
            value=value,
            source=AssessmentSource(
                source_type=AssessmentSourceType.HUMAN,
                source_id=source_id,
            ),
        )
        _logger.debug("Logged expectation '%s' on trace %s", name, trace_id[:12])
    except Exception as e:
        _logger.debug("Failed to log expectation: %s", e)


def search_traces(
    experiment_names: list[str] | None = None,
    max_results: int = 100,
) -> Any:
    """Search for traces in the configured MLflow experiment.

    Thin wrapper around mlflow.search_traces() with defensive handling.

    Args:
        experiment_names: Experiment names to search (defaults to active experiment)
        max_results: Maximum number of traces to return

    Returns:
        DataFrame of traces, or None if MLflow unavailable
    """
    if not _ensure_mlflow_initialized() or not _traces_available:
        return None

    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return None

    try:
        settings = get_settings()
        names = experiment_names or [settings.mlflow_experiment_name]
        return mlflow.search_traces(
            experiment_names=names,
            max_results=max_results,
        )
    except Exception as e:
        _logger.debug("Failed to search traces: %s", e)
        return None
