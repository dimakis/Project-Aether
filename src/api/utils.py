"""API utility functions.

Shared helpers for route handlers.
"""

import logging

from src.settings import get_settings

logger = logging.getLogger(__name__)


def sanitize_error(exc: Exception, *, context: str = "Operation") -> str:
    """Return a safe error message for API responses.

    In debug/development mode, includes the original exception message.
    In production, returns a generic message and logs the real error
    server-side for debugging via correlation ID.

    Args:
        exc: The caught exception
        context: Human-readable operation name for the generic message

    Returns:
        Sanitized error string safe to return to clients
    """
    settings = get_settings()

    # Always log the real error server-side
    logger.exception("%s failed", context)

    if settings.debug or settings.environment in ("development", "testing"):
        return f"{context} failed: {exc!s}"

    return f"{context} failed. Check server logs for details."
