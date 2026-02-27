"""Model context propagation for multi-agent delegation.

Carries the user's LLM model selection through the agent delegation chain,
so that specialist agents (e.g. Data Science team) use the same model the user
chose in the UI rather than falling back to the global default.

Also carries tracing metadata (parent_span_id) for inter-agent trace linking.

Pattern follows src/tracing/context.py (session_context with contextvars).

Resolution order for any agent (Feature 23 update):
    1. Explicit model context (user's UI selection, propagated via contextvars)
    2. DB-backed active config version (per-agent settings from UI config page)
    3. Per-agent env var settings (e.g. DATA_SCIENTIST_MODEL from .env)
    4. Global default (LLM_MODEL from .env)
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass(frozen=True, slots=True)
class ModelContext:
    """Immutable model context propagated through agent delegation.

    Attributes:
        model_name: The LLM model identifier (e.g. "anthropic/claude-sonnet-4")
        temperature: Generation temperature (0.0-2.0)
        parent_span_id: MLflow span ID of the calling agent for trace linking
    """

    model_name: str | None = None
    temperature: float | None = None
    parent_span_id: str | None = None


# Context variable holding the active model context
_model_ctx: ContextVar[ModelContext | None] = ContextVar("model_context", default=None)


def get_model_context() -> ModelContext | None:
    """Get the active model context.

    Returns:
        Current ModelContext or None if no context is active.
    """
    return _model_ctx.get()


def set_model_context(ctx: ModelContext) -> None:
    """Set the active model context.

    Use this to restore a context from stored state.

    Args:
        ctx: The ModelContext to set.
    """
    _model_ctx.set(ctx)


@contextmanager
def model_context(
    model_name: str | None = None,
    temperature: float | None = None,
    parent_span_id: str | None = None,
) -> Generator[ModelContext, None, None]:
    """Context manager that sets the active model context.

    Saves and restores the previous context on exit, so nested
    calls are safe.

    Args:
        model_name: LLM model identifier
        temperature: Generation temperature
        parent_span_id: MLflow span ID for trace linking

    Yields:
        The newly active ModelContext
    """
    previous = _model_ctx.get()
    ctx = ModelContext(
        model_name=model_name,
        temperature=temperature,
        parent_span_id=parent_span_id,
    )
    _model_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _model_ctx.set(previous)


def clear_model_context() -> None:
    """Clear the active model context."""
    _model_ctx.set(None)


def resolve_model(
    agent_model: str | None = None,
    agent_temperature: float | None = None,
    db_model: str | None = None,
    db_temperature: float | None = None,
) -> tuple[str | None, float | None]:
    """Resolve model name and temperature using the priority chain.

    Resolution order (Feature 23 update):
        1. Active model context (user's UI selection)
        2. DB-backed agent config (from active config version)
        3. Per-agent env var settings (passed as arguments)
        4. Returns (None, None) — caller falls back to global default

    Args:
        agent_model: Per-agent model override from env var settings
        agent_temperature: Per-agent temperature override from env var settings
        db_model: Per-agent model from DB active config version
        db_temperature: Per-agent temperature from DB active config version

    Returns:
        Tuple of (model_name, temperature). Either or both may be None,
        indicating the caller should use its own default.
    """
    ctx = _model_ctx.get()

    # Priority 1: Active model context (user selection propagated via delegation)
    if ctx and ctx.model_name:
        return ctx.model_name, ctx.temperature

    # Priority 2: DB-backed active config version (Feature 23)
    if db_model:
        return db_model, db_temperature

    # Priority 3: Per-agent env var settings
    if agent_model:
        return agent_model, agent_temperature

    # Priority 4: Caller uses its own default (global settings)
    return None, None


__all__ = [
    "ModelContext",
    "clear_model_context",
    "get_model_context",
    "model_context",
    "resolve_model",
    "set_model_context",
]
