"""Shared test fixtures for Project Aether.

Provides common fixtures used across unit, integration, and E2E tests.
Constitution: Reliability & Quality - comprehensive test infrastructure.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.settings import Settings
from src.storage.models import Base


# =============================================================================
# EVENT LOOP
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# SETTINGS
# =============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Provide test settings with safe defaults."""
    return Settings(
        environment="testing",  # Skip DB init and scheduler in tests
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/aether_test",
        ha_url="http://localhost:8123",
        ha_token=SecretStr("test-token"),
        openai_api_key=SecretStr("test-api-key"),
        mlflow_tracking_uri="http://localhost:5000",
        sandbox_enabled=False,  # Disable sandbox in tests
    )


@pytest.fixture
def mock_settings(test_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Mock get_settings() to return test settings."""
    from src import settings

    monkeypatch.setattr(settings, "get_settings", lambda: test_settings)
    return test_settings


# =============================================================================
# DATABASE
# =============================================================================


@pytest.fixture
async def async_engine(test_settings: Settings) -> AsyncGenerator[Any, None]:
    """Create async database engine for testing."""
    engine = create_async_engine(
        str(test_settings.database_url),
        echo=False,
        pool_pre_ping=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(
    async_engine: Any,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for tests.

    Each test gets a fresh session that rolls back after completion.
    """
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock database session for unit tests."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# =============================================================================
# HA CLIENT
# =============================================================================


@pytest.fixture
def mock_ha_client() -> MagicMock:
    """Mock HA client for Home Assistant interactions.

    Provides realistic mock responses for HA operations.
    """
    client = MagicMock()

    # System overview
    client.system_overview = AsyncMock(
        return_value={
            "total_entities": 42,
            "domains": {
                "light": {"count": 10, "states": {"on": 3, "off": 7}},
                "switch": {"count": 8, "states": {"on": 2, "off": 6}},
                "sensor": {"count": 20, "states": {}},
                "binary_sensor": {"count": 4, "states": {"on": 1, "off": 3}},
            },
        }
    )

    # List entities
    client.list_entities = AsyncMock(
        return_value=[
            {
                "entity_id": "light.living_room",
                "state": "off",
                "name": "Living Room",
                "area_id": "living_room",
            },
            {
                "entity_id": "light.bedroom",
                "state": "on",
                "name": "Bedroom",
                "area_id": "bedroom",
            },
        ]
    )

    # Get entity
    client.get_entity = AsyncMock(
        return_value={
            "entity_id": "light.living_room",
            "state": "off",
            "attributes": {
                "friendly_name": "Living Room",
                "brightness": 0,
                "supported_features": 44,
            },
        }
    )

    # Entity action
    client.entity_action = AsyncMock(return_value={"success": True})

    # Call service
    client.call_service = AsyncMock(return_value={})

    return client


# =============================================================================
# LLM / OPENAI
# =============================================================================


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock LLM for testing agent logic without API calls."""
    from langchain_core.messages import AIMessage

    llm = MagicMock()

    # Mock invoke
    llm.invoke = MagicMock(
        return_value=AIMessage(
            content="This is a mock response from the LLM.",
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
        )
    )

    # Mock ainvoke
    llm.ainvoke = AsyncMock(
        return_value=AIMessage(
            content="This is a mock async response from the LLM.",
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
        )
    )

    return llm


# =============================================================================
# MLFLOW
# =============================================================================


@pytest.fixture
def mock_mlflow(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock MLflow to prevent actual tracking during tests."""
    import mlflow

    mock = MagicMock()
    mock.active_run.return_value = None

    monkeypatch.setattr(mlflow, "set_tracking_uri", mock.set_tracking_uri)
    monkeypatch.setattr(mlflow, "set_experiment", mock.set_experiment)
    monkeypatch.setattr(mlflow, "start_run", mock.start_run)
    monkeypatch.setattr(mlflow, "end_run", mock.end_run)
    monkeypatch.setattr(mlflow, "log_param", mock.log_param)
    monkeypatch.setattr(mlflow, "log_params", mock.log_params)
    monkeypatch.setattr(mlflow, "log_metric", mock.log_metric)
    monkeypatch.setattr(mlflow, "log_metrics", mock.log_metrics)
    monkeypatch.setattr(mlflow, "set_tag", mock.set_tag)
    monkeypatch.setattr(mlflow, "active_run", mock.active_run)

    return mock


# =============================================================================
# SANDBOX
# =============================================================================


@pytest.fixture
def mock_sandbox_runner() -> AsyncMock:
    """Mock sandbox runner for testing without containers."""
    from src.sandbox.runner import SandboxResult

    runner = AsyncMock()
    runner.run = AsyncMock(
        return_value=SandboxResult(
            success=True,
            exit_code=0,
            stdout="Script output",
            stderr="",
            duration_seconds=0.5,
            timed_out=False,
            policy_name="standard",
        )
    )
    return runner


# =============================================================================
# FASTAPI TEST CLIENT
# =============================================================================


@pytest.fixture
def test_app(mock_settings: Settings) -> Any:
    """Create FastAPI test application."""
    from src.api.main import create_app

    return create_app(mock_settings)


@pytest.fixture
async def async_client(test_app: Any) -> AsyncGenerator[Any, None]:
    """Provide async HTTP client for API testing."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client


# =============================================================================
# MARKERS
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (require services)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full system)")
    config.addinivalue_line("markers", "slow: Slow tests")
