"""MLflow span utilities: get_active_span, add_span_event, trace_with_uri decorator."""

import functools
import logging
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from src.tracing.mlflow_init import (
    _disable_traces,
    _ensure_mlflow_initialized,
    _safe_import_mlflow,
    _traces_available,
)

P = ParamSpec("P")
R = TypeVar("R")

_logger = logging.getLogger(__name__)


def get_active_span() -> Any | None:
    """Return the current active MLflow span, or None."""
    mlflow = _safe_import_mlflow()
    if mlflow is None:
        return None

    try:
        return mlflow.get_current_active_span()
    except Exception:
        return None


def add_span_event(
    span: Any,
    name: str,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Add a SpanEvent to an MLflow span.

    Wraps the SpanEvent construction for a cleaner call-site API.
    """
    if span is None or not hasattr(span, "add_event"):
        return

    try:
        from mlflow.entities import SpanEvent

        event = SpanEvent(name=name, attributes=attributes or {})  # type: ignore[abstract]
        span.add_event(event)
    except (ImportError, TypeError, Exception) as e:
        _logger.debug(f"Failed to add span event: {e}")


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

        def _get_traced(mlflow: Any) -> Callable[..., Any]:
            """Create and cache the mlflow.trace()-wrapped function."""
            nonlocal traced_func
            if traced_func is None:
                traced_func = mlflow.trace(
                    func,
                    name=span_name,
                    span_type=span_type,
                    attributes=attributes,
                )
            return traced_func

        def _tag_trace_session(mlflow: Any) -> None:
            """Tag the current trace with session ID for grouping."""
            try:
                from src.tracing.context import get_session_id

                session_id = get_session_id()
                if session_id:
                    mlflow.update_current_trace(tags={"mlflow.trace.session": session_id})
            except Exception:
                _logger.debug("Failed to tag trace with session ID", exc_info=True)

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not _ensure_mlflow_initialized() or not _traces_available:
                return await func(*args, **kwargs)  # type: ignore[misc, no-any-return]

            mlflow = _safe_import_mlflow()
            if mlflow is None:
                return await func(*args, **kwargs)  # type: ignore[misc, no-any-return]

            try:
                traced = _get_traced(mlflow)
                result = await traced(*args, **kwargs)
                _tag_trace_session(mlflow)
                return result  # type: ignore[no-any-return]
            except Exception as e:
                _disable_traces("span creation failed; backend rejected traces")
                _logger.debug(f"Span creation failed, running without trace: {e}")
                return await func(*args, **kwargs)  # type: ignore[misc, no-any-return]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not _ensure_mlflow_initialized() or not _traces_available:
                return func(*args, **kwargs)

            mlflow = _safe_import_mlflow()
            if mlflow is None:
                return func(*args, **kwargs)

            try:
                traced = _get_traced(mlflow)
                result = traced(*args, **kwargs)
                _tag_trace_session(mlflow)
                return result  # type: ignore[no-any-return]
            except Exception as e:
                _disable_traces("span creation failed; backend rejected traces")
                _logger.debug(f"Span creation failed, running without trace: {e}")
                return func(*args, **kwargs)

        if _is_async(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator
