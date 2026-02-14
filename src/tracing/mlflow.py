"""MLflow 3.x experiment setup, tracing, and GenAI evaluation utilities.

Provides comprehensive tracing for agent operations, LLM calls,
and data science workflows (Constitution: Observability), plus
MLflow 3.x feedback/assessment bridging and trace search.

All functions are defensive - they silently skip tracing if MLflow
is unavailable or misconfigured, rather than crashing the application.

Requires MLflow >= 3.5.0 (v2 fallback paths have been removed).

This module re-exports from focused submodules for backwards compatibility.
All existing `from src.tracing.mlflow import X` continue to work.
"""

from src.tracing.mlflow_feedback import (
    log_code_feedback,
    log_expectation,
    log_human_feedback,
    search_traces,
)
from src.tracing.mlflow_init import (
    _disable_traces,  # noqa: F401 - re-export for backward compat
    _safe_import_mlflow,  # noqa: F401 - re-export for backward compat
    enable_autolog,
    get_or_create_experiment,
    init_mlflow,
)
from src.tracing.mlflow_logging import log_dict, log_metric, log_metrics, log_param, log_params
from src.tracing.mlflow_runs import end_run, get_active_run, start_experiment_run, start_run
from src.tracing.mlflow_spans import (
    _is_async,  # noqa: F401 - used by tests
    add_span_event,
    get_active_span,
    trace_with_uri,
)
from src.tracing.mlflow_tracer import AetherTracer, get_tracer, get_tracing_status

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
    "log_code_feedback",
    "log_dict",
    "log_expectation",
    "log_human_feedback",
    "log_metric",
    "log_metrics",
    "log_param",
    "log_params",
    "search_traces",
    "start_experiment_run",
    "start_run",
    "trace_with_uri",
]
