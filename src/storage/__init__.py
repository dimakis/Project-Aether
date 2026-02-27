"""Database connection and session management.

Provides async SQLAlchemy engine, session factory, and connection utilities.
Uses asyncpg for PostgreSQL async support (Constitution: State).

Thread-safety: All singleton access is protected by threading.RLock to prevent
race conditions during concurrent initialization (T186).  RLock (reentrant)
is required because get_session_factory() calls get_engine() while holding
the lock.
"""

import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.settings import Settings, get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

# Module-level engine and session factory (initialized lazily)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_init_lock = threading.RLock()


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Get or create the async database engine.

    Thread-safe: Uses double-checked locking to prevent concurrent
    engine creation in multi-threaded environments (e.g., uvicorn workers).

    Args:
        settings: Optional settings override. Uses get_settings() if not provided.

    Returns:
        Configured AsyncEngine instance.
    """
    global _engine

    if _engine is None:
        with _init_lock:
            if _engine is None:
                settings = settings or get_settings()
                _engine = create_async_engine(
                    str(settings.database_url),
                    pool_size=settings.database_pool_size,
                    max_overflow=settings.database_max_overflow,
                    pool_timeout=settings.database_pool_timeout,
                    pool_recycle=settings.database_pool_recycle,
                    pool_pre_ping=True,
                    echo=settings.debug,
                )

    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory.

    Thread-safe: Uses double-checked locking to prevent concurrent
    session factory creation.

    Args:
        settings: Optional settings override. Uses get_settings() if not provided.

    Returns:
        Configured async_sessionmaker instance.
    """
    global _session_factory

    if _session_factory is None:
        with _init_lock:
            if _session_factory is None:
                engine = get_engine(settings)
                _session_factory = async_sessionmaker(
                    bind=engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False,
                )

    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session with automatic cleanup.

    Usage:
        async with get_session() as session:
            result = await session.execute(query)

    Yields:
        AsyncSession instance that is automatically closed.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def get_committing_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a session that auto-commits on successful exit.

    Wraps :func:`get_session` and calls ``session.commit()`` before
    closing when no exception occurred.  On exception the session is
    closed without committing, allowing the caller to handle rollback.

    Designed for use as ``session_factory`` in :class:`ExecutionContext`
    so that tools (e.g. DS team report lifecycle) persist their changes
    without requiring each call-site to commit explicitly.

    Usage:
        async with get_committing_session() as session:
            session.add(entity)
            await session.flush()
            # commit happens automatically on exit
    """
    async with get_session() as session:
        yield session
        await session.commit()


@asynccontextmanager
async def get_connection() -> AsyncGenerator["AsyncConnection", None]:
    """Provide a raw async database connection.

    Useful for raw SQL or migration operations.

    Yields:
        AsyncConnection instance that is automatically closed.
    """
    engine = get_engine()
    async with engine.connect() as connection:
        yield connection


async def init_db() -> None:
    """Initialize database connection pool.

    Call this at application startup to eagerly initialize the connection pool.
    """
    engine = get_engine()
    # Verify connectivity
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_db() -> None:
    """Close database connections.

    Call this at application shutdown to cleanly close all connections.
    Thread-safe: Acquires lock before modifying singletons.
    """
    global _engine, _session_factory

    with _init_lock:
        if _engine is not None:
            await _engine.dispose()
            _engine = None
            _session_factory = None


# Public API
__all__ = [
    "close_db",
    "get_committing_session",
    "get_connection",
    "get_engine",
    "get_session",
    "get_session_factory",
    "init_db",
]
