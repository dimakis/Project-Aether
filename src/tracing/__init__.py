"""MLflow tracing and observability for Project Aether.

Implements the Constitution's Observability requirement:
"Every agent negotiation and data science insight must be traced via MLflow."

This module provides:
- MLflow client initialization and configuration
- Experiment management
- Tracing decorators for agents
- Metric logging utilities
"""

from src.tracing.mlflow import (
    AetherTracer,
    end_run,
    get_active_run,
    get_or_create_experiment,
    get_tracer,
    init_mlflow,
    log_agent_action,
    log_dict,
    log_metric,
    log_metrics,
    log_param,
    log_params,
    start_run,
    trace_agent,
    trace_llm_call,
)

__all__ = [
    # Initialization
    "init_mlflow",
    "get_or_create_experiment",
    # Run management
    "start_run",
    "end_run",
    "get_active_run",
    # Logging
    "log_param",
    "log_params",
    "log_metric",
    "log_metrics",
    "log_dict",
    "log_agent_action",
    # Decorators
    "trace_agent",
    "trace_llm_call",
    # Tracer class
    "AetherTracer",
    "get_tracer",
]
