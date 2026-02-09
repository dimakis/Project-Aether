"""Integration test fixtures using testcontainers.

Provides real PostgreSQL containers for integration testing
without requiring external infrastructure.

Constitution: Reliability & Quality - real service testing.
"""

import os
import shutil
import subprocess


def _configure_container_runtime() -> None:
    """Auto-detect container runtime so testcontainers works with Docker or Podman.

    Detection order (first match wins):
      1. DOCKER_HOST already set — respect it.
      2. /var/run/docker.sock exists — standard Docker.
      3. Linux rootless Podman socket.
      4. macOS Podman machine socket via ``podman machine inspect``.
      5. None found — do nothing; tests will skip gracefully.
    """
    if os.environ.get("DOCKER_HOST"):
        return
    if os.path.exists("/var/run/docker.sock"):
        return

    # Linux rootless Podman
    linux_socket = f"/run/user/{os.getuid()}/podman/podman.sock"
    if os.path.exists(linux_socket):
        os.environ["DOCKER_HOST"] = f"unix://{linux_socket}"
        os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
        return

    # macOS Podman machine
    if shutil.which("podman"):
        try:
            result = subprocess.run(
                ["podman", "machine", "inspect",
                 "--format", "{{.ConnectionInfo.PodmanSocket.Path}}"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                sock = result.stdout.strip()
                if sock and os.path.exists(sock):
                    os.environ["DOCKER_HOST"] = f"unix://{sock}"
                    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass


_configure_container_runtime()

from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import src.storage.entities  # noqa: F401 — register all models with Base.metadata
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


@pytest_asyncio.fixture(scope="session", loop_scope="session")
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


@pytest_asyncio.fixture(loop_scope="session")
async def integration_session(
    integration_engine: Any,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for each integration test.

    Uses a connection-level transaction that is always rolled back,
    so even code that calls session.commit() won't persist data.
    This gives each test a clean slate.

    Pattern: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    """
    async with integration_engine.connect() as conn:
        trans = await conn.begin()

        # Bind session to connection that already has a transaction
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # Start a SAVEPOINT so that session.commit() releases the savepoint
        # rather than committing the real transaction.
        await session.begin_nested()

        # When code calls session.commit(), it releases the savepoint.
        # Re-open a new savepoint so subsequent operations keep working.
        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(session_sync, transaction):
            if transaction.nested and not transaction._parent.nested:
                session_sync.begin_nested()

        yield session

        await session.close()
        await trans.rollback()


@pytest_asyncio.fixture(loop_scope="session")
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
