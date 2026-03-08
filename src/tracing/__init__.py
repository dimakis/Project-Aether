"""MLflow tracing and observability for Project Aether.

Implements the Constitution's Observability requirement:
"Every agent negotiation and data science insight must be traced via MLflow."

This module provides:
- MLflow client initialization and configuration
- Experiment management
- Tracing decorators for agents
- Metric logging utilities
- Session context for trace correlation

Uses lazy imports to avoid loading MLflow until actually needed.
"""

from typing import TYPE_CHECKING

# Define all exports and their source modules
_EXPORTS = {
    # Initialization
    "init_mlflow": "src.tracing.mlflow",
    "get_or_create_experiment": "src.tracing.mlflow",
    "enable_autolog": "src.tracing.mlflow",
    # Run management
    "start_run": "src.tracing.mlflow",
    "start_experiment_run": "src.tracing.mlflow",
    "end_run": "src.tracing.mlflow",
    "get_active_run": "src.tracing.mlflow",
    # Logging
    "log_param": "src.tracing.mlflow",
    "log_params": "src.tracing.mlflow",
    "log_metric": "src.tracing.mlflow",
    "log_metrics": "src.tracing.mlflow",
    "log_dict": "src.tracing.mlflow",
    # Feedback & assessment (MLflow 3.x)
    "log_human_feedback": "src.tracing.mlflow",
    "log_code_feedback": "src.tracing.mlflow",
    "log_expectation": "src.tracing.mlflow",
    "search_traces": "src.tracing.mlflow",
    # Decorators (for non-LLM spans; LLM calls use autolog)
    "trace_with_uri": "src.tracing.mlflow",
    "traced_node": "src.tracing.mlflow",
    "get_active_span": "src.tracing.mlflow",
    "add_span_event": "src.tracing.mlflow",
    "get_tracing_status": "src.tracing.mlflow",
    # Tracer class
    "AetherTracer": "src.tracing.mlflow",
    "get_tracer": "src.tracing.mlflow",
    # Session context
    "start_session": "src.tracing.context",
    "get_session_id": "src.tracing.context",
    "set_session_id": "src.tracing.context",
    "session_context": "src.tracing.context",
}

# Cache for imported attributes
_cache: dict = {}


def __getattr__(name: str):
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]

    if name in _EXPORTS:
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr

    raise AttributeError(f"module 'src.tracing' has no attribute '{name}'")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


# Type hints for IDE support (only evaluated during type checking)
if TYPE_CHECKING:
    from src.tracing.context import (
        get_session_id,
        session_context,
        set_session_id,
        start_session,
    )
    from src.tracing.mlflow import (
        AetherTracer,
        add_span_event,
        enable_autolog,
        end_run,
        get_active_run,
        get_active_span,
        get_or_create_experiment,
        get_tracer,
        get_tracing_status,
        init_mlflow,
        log_code_feedback,
        log_dict,
        log_expectation,
        log_human_feedback,
        log_metric,
        log_metrics,
        log_param,
        log_params,
        search_traces,
        start_experiment_run,
        start_run,
        trace_with_uri,
        traced_node,
    )

__all__ = [
    # Tracer class
    "AetherTracer",
    "add_span_event",
    "enable_autolog",
    "end_run",
    "get_active_run",
    "get_active_span",
    "get_or_create_experiment",
    "get_session_id",
    "get_tracer",
    "get_tracing_status",
    # Initialization
    "init_mlflow",
    # Feedback & assessment (MLflow 3.x)
    "log_code_feedback",
    "log_dict",
    "log_expectation",
    "log_human_feedback",
    "log_metric",
    "log_metrics",
    # Logging
    "log_param",
    "log_params",
    "search_traces",
    "session_context",
    "set_session_id",
    "start_experiment_run",
    # Run management
    "start_run",
    # Session context
    "start_session",
    # Decorators (for non-LLM spans; LLM calls use autolog)
    "trace_with_uri",
    "traced_node",
]
