"""Integration test fixtures using testcontainers.

Provides real PostgreSQL containers for integration testing
without requiring external infrastructure.

Constitution: Reliability & Quality - real service testing.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import Base

# Try to import testcontainers, skip tests if not available
try:
    from testcontainers.postgres import PostgresContainer

    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    PostgresContainer = None  # type: ignore


# =============================================================================
# POSTGRESQL CONTAINER
# =============================================================================


@pytest.fixture(scope="session")
def postgres_container() -> Generator[Any, None, None]:
    """Start a PostgreSQL container for integration tests.

    Uses testcontainers to spin up a real PostgreSQL instance.
    Container is shared across all integration tests in the session.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not installed")

    try:
        with PostgresContainer(
            image="postgres:16-alpine",
            username="test",
            password="test",
            dbname="aether_test",
        ) as postgres:
            yield postgres
    except Exception as e:
        pytest.skip(f"Docker/Podman not available: {e}")


@pytest.fixture(scope="session")
def postgres_url(postgres_container: PostgresContainer) -> str:
    """Get async connection URL for the PostgreSQL container."""
    # testcontainers gives us a sync URL, convert to async
    sync_url = postgres_container.get_connection_url()
    # Replace psycopg2 with asyncpg
    async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
    async_url = async_url.replace("psycopg2", "asyncpg")
    return async_url


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def integration_engine(postgres_url: str) -> AsyncGenerator[Any, None]:
    """Create async engine connected to the test container."""
    engine = create_async_engine(
        postgres_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def integration_session(
    integration_engine: Any,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for each integration test.

    Each test gets a fresh transaction that is rolled back after.
    """
    session_factory = async_sessionmaker(
        bind=integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        # Start a transaction
        async with session.begin():
            yield session
            # Transaction is rolled back when we exit


@pytest.fixture
async def clean_tables(integration_engine: Any) -> AsyncGenerator[None, None]:
    """Clean all tables before and after the test.

    Use this fixture when you need a completely clean database
    and don't want transaction rollback behavior.
    """
    async with integration_engine.begin() as conn:
        # Truncate all tables
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    yield

    async with integration_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# =============================================================================
# INTEGRATION TEST SETTINGS
# =============================================================================


@pytest.fixture
def integration_settings(postgres_url: str) -> Any:
    """Create settings pointing to the test container."""
    from pydantic import SecretStr

    from src.settings import Settings

    return Settings(
        environment="development",  # Use valid environment
        debug=True,
        database_url=postgres_url,
        ha_url="http://localhost:8124",  # Mock HA port
        ha_token=SecretStr("test-token"),
        openai_api_key=SecretStr("test-key"),
        mlflow_tracking_uri="http://localhost:5001",  # Test MLflow port
        sandbox_enabled=False,
    )


# =============================================================================
# MARKERS
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register integration test markers."""
    config.addinivalue_line(
        "markers",
        "integration: Integration tests requiring real services",
    )
    config.addinivalue_line(
        "markers",
        "requires_postgres: Tests requiring PostgreSQL container",
    )
