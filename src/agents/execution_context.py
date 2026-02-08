"""Execution context propagation for agent workflows.

Carries cross-cutting concerns through agent delegation chains via
contextvars, so that any agent or tool can access progress emission,
DB session factories, conversation IDs, and task labels without
explicit parameter threading.

Pattern follows src/agents/model_context.py and src/tracing/context.py.

The ExecutionContext is set at the streaming layer (e.g. stream_conversation)
and read by BaseAgent.trace_span() for auto-progress emission and by
BaseAnalyst for auto-session acquisition.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Literal

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    """A progress event emitted by agents during execution.

    Attributes:
        type: Event kind — ``agent_start`` / ``agent_end`` for lifecycle,
              ``status`` for free-form progress messages.
        agent: The agent role identifier (e.g. ``"energy_analyst"``).
        message: Human-readable description of what is happening.
        ts: Unix timestamp (auto-populated from ``time.time()``).
    """

    type: Literal["agent_start", "agent_end", "status"]
    agent: str
    message: str
    ts: float = field(default_factory=time.time)


@dataclass
class ExecutionContext:
    """Cross-cutting context for agent execution.

    Propagated via contextvars through any delegation chain.
    Any agent or tool can read/emit without coupling to the caller.

    Attributes:
        progress_queue: Async queue for emitting progress events back
            to the streaming layer.  ``None`` when no consumer is active.
        session_factory: Callable that returns an async context manager
            yielding a database session.  Used by analysts to auto-acquire
            sessions for insight persistence.
        conversation_id: The originating conversation ID for task tagging.
        task_label: Human-readable label for the current task/analysis.
        tool_timeout: Default timeout in seconds for simple tool calls.
        analysis_timeout: Timeout in seconds for long-running analysis tools.
    """

    progress_queue: asyncio.Queue[ProgressEvent] | None = None
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None
    conversation_id: str | None = None
    task_label: str | None = None
    tool_timeout: float = 30.0
    analysis_timeout: float = 180.0


# Context variable holding the active execution context
_exec_ctx: ContextVar[ExecutionContext | None] = ContextVar(
    "execution_context", default=None
)


def get_execution_context() -> ExecutionContext | None:
    """Get the active execution context.

    Returns:
        Current ExecutionContext or None if no context is active.
    """
    return _exec_ctx.get()


def set_execution_context(ctx: ExecutionContext) -> None:
    """Set the active execution context.

    Use this to restore a context from stored state.

    Args:
        ctx: The ExecutionContext to set.
    """
    _exec_ctx.set(ctx)


def clear_execution_context() -> None:
    """Clear the active execution context."""
    _exec_ctx.set(None)


@asynccontextmanager
async def execution_context(
    progress_queue: asyncio.Queue[ProgressEvent] | None = None,
    session_factory: Callable[[], AbstractAsyncContextManager[Any]] | None = None,
    conversation_id: str | None = None,
    task_label: str | None = None,
    tool_timeout: float = 30.0,
    analysis_timeout: float = 180.0,
) -> AsyncGenerator[ExecutionContext, None]:
    """Async context manager that sets the active execution context.

    Saves and restores the previous context on exit, so nested
    calls are safe.

    Args:
        progress_queue: Queue for progress events (or None).
        session_factory: Callable returning async session context manager.
        conversation_id: Originating conversation ID.
        task_label: Human-readable task label.
        tool_timeout: Timeout for simple tool calls (seconds).
        analysis_timeout: Timeout for analysis tool calls (seconds).

    Yields:
        The newly active ExecutionContext.
    """
    previous = _exec_ctx.get()
    ctx = ExecutionContext(
        progress_queue=progress_queue,
        session_factory=session_factory,
        conversation_id=conversation_id,
        task_label=task_label,
        tool_timeout=tool_timeout,
        analysis_timeout=analysis_timeout,
    )
    _exec_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _exec_ctx.set(previous)


def emit_progress(
    type: Literal["agent_start", "agent_end", "status"],
    agent: str,
    message: str,
) -> None:
    """Emit a progress event to the active execution context's queue.

    This is a fire-and-forget convenience helper.  If no execution context
    is active, or the context has no progress queue, this is a silent no-op.

    Args:
        type: Event type (``agent_start``, ``agent_end``, or ``status``).
        agent: Agent role identifier.
        message: Human-readable progress message.
    """
    ctx = _exec_ctx.get()
    if ctx is None or ctx.progress_queue is None:
        return

    event = ProgressEvent(type=type, agent=agent, message=message)
    try:
        ctx.progress_queue.put_nowait(event)
    except asyncio.QueueFull:
        logger.warning(
            "Progress queue full, dropping event: %s %s", type, agent
        )


__all__ = [
    "ExecutionContext",
    "ProgressEvent",
    "clear_execution_context",
    "emit_progress",
    "execution_context",
    "get_execution_context",
    "set_execution_context",
]
