"""Shared FastAPI dependencies.

Provides common dependency callables used across route modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.storage import get_session

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.ha.client import HAClient


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session scoped to a single request."""
    async with get_session() as session:
        yield session


async def get_ha(zone_id: str | None = None) -> HAClient:
    """Provide an HA client for the requested zone.

    Uses the cached async client factory. Suitable for use with
    ``Depends(get_ha)`` in FastAPI route handlers.
    """
    from src.ha.client import get_ha_client_async

    return await get_ha_client_async(zone_id)
