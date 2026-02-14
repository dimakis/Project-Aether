"""Shared utilities for HA Registry routes."""

import uuid as _uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.storage import get_session


def _is_valid_uuid(value: str) -> bool:
    """Return True if *value* is a valid UUID string."""
    try:
        _uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with get_session() as session:
        yield session
