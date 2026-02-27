"""Shared utilities for HA Registry routes."""

import uuid as _uuid

from src.api.deps import get_db

__all__ = ["_is_valid_uuid", "get_db"]


def _is_valid_uuid(value: str) -> bool:
    """Return True if *value* is a valid UUID string."""
    try:
        _uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
