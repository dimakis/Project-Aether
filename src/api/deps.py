"""Shared FastAPI dependencies.

Provides common dependency callables used across route modules.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.storage import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session scoped to a single request."""
    async with get_session() as session:
        yield session
