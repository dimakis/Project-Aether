"""MLflow logging: log_param, log_params, log_metric, log_metrics, log_dict."""

import logging

from src.tracing.mlflow_init import _safe_import_mlflow

_logger = logging.getLogger(__name__)


def log_param(key: str, value: object) -> None:
    """Log a parameter to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_param(key, value)
    except Exception as e:
        _logger.debug("Failed to log param %s: %s", key, e)


def log_params(params: dict[str, object]) -> None:
    """Log multiple parameters to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_params(params)
    except Exception as e:
        _logger.debug("Failed to log params: %s", e)


def log_metric(key: str, value: float, step: int | None = None) -> None:
    """Log a metric to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_metric(key, value, step=step)
    except Exception as e:
        _logger.debug("Failed to log metric %s: %s", key, e)


def log_metrics(metrics: dict[str, float], step: int | None = None) -> None:
    """Log multiple metrics to the active run."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_metrics(metrics, step=step)
    except Exception as e:
        _logger.debug("Failed to log metrics: %s", e)


def log_dict(data: dict[str, object], filename: str) -> None:
    """Log a dictionary as a JSON artifact."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return

    try:
        if mlflow.active_run():
            mlflow.log_dict(data, filename)
    except Exception as e:
        _logger.debug("Failed to log dict to %s: %s", filename, e)
