"""Session context management for trace correlation.

Provides a session ID that flows through all operations within a request,
enabling correlation of related spans across agents, tools, and workflows.
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

# Context variable for current session ID
_session_id: ContextVar[str | None] = ContextVar("trace_session_id", default=None)


def start_session() -> str:
    """Start a new trace session and return its ID.

    This should be called at the entry point of a user request
    (e.g., API endpoint, CLI command, workflow start).

    Returns:
        The new session ID (UUID string)
    """
    sid = str(uuid4())
    _session_id.set(sid)
    return sid


def get_session_id() -> str | None:
    """Get the current session ID.

    Returns:
        Current session ID or None if no session is active
    """
    return _session_id.get()


def set_session_id(session_id: str) -> None:
    """Set the current session ID.

    Use this to restore a session ID from a stored state
    (e.g., when resuming a workflow).

    Args:
        session_id: The session ID to set
    """
    _session_id.set(session_id)


@contextmanager
def session_context(session_id: str | None = None) -> Generator[str, None, None]:
    """Context manager for session scope.

    Creates a new session or uses provided ID, then restores
    the previous session on exit.

    Args:
        session_id: Optional session ID to use (creates new if None)

    Yields:
        The active session ID
    """
    previous = _session_id.get()
    sid = session_id or str(uuid4())
    _session_id.set(sid)
    try:
        yield sid
    finally:
        _session_id.set(previous)


def clear_session() -> None:
    """Clear the current session ID.

    Use this when a session is complete or to reset state.
    """
    _session_id.set(None)


__all__ = [
    "clear_session",
    "get_session_id",
    "session_context",
    "set_session_id",
    "start_session",
]
