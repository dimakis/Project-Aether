"""Unit tests for System API routes.

Tests GET /health, GET /ready, GET /status, and GET /metrics endpoints
with mocked dependencies -- no real database, MLflow, or Home Assistant connections.

The get_session dependency is overridden with a mock AsyncSession so
the test never attempts a real Postgres connection (which would hang
indefinitely in a unit-test environment).
"""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient


def _make_test_app():
    """Create a minimal FastAPI app with the system router."""
    from fastapi import FastAPI

    from src.api.routes.system import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def system_app():
    """Lightweight FastAPI app with system routes and mocked dependencies."""
    return _make_test_app()


@pytest.fixture
async def system_client(system_app):
    """Async HTTP client wired to the system test app."""
    async with AsyncClient(
        transport=ASGITransport(app=system_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
class TestHealthCheck:
    """Tests for GET /api/v1/health."""

    async def test_health_check_returns_healthy(self, system_client):
        """Should return healthy status with timestamp and version."""
        response = await system_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


@pytest.mark.asyncio
class TestReadinessCheck:
    """Tests for GET /api/v1/ready."""

    async def test_ready_check_returns_healthy_when_db_available(self, system_client):
        """Should return healthy status when database is available."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        with patch("src.storage.get_session", _mock_get_session):
            response = await system_client.get("/api/v1/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["version"] == "0.1.0"
            assert "timestamp" in data

    async def test_ready_check_returns_503_when_db_unavailable(self, system_client):
        """Should return 503 when database is unavailable."""

        @asynccontextmanager
        async def _mock_get_session():
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(side_effect=Exception("Connection failed"))
            yield mock_session

        with patch("src.storage.get_session", _mock_get_session):
            response = await system_client.get("/api/v1/ready")

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "database unavailable" in data["detail"].lower()


@pytest.mark.asyncio
class TestMetrics:
    """Tests for GET /api/v1/metrics."""

    async def test_get_metrics_returns_metrics_dict(self, system_client):
        """Should return metrics dictionary from metrics collector."""
        mock_metrics = {
            "requests": {"total": 100, "by_method": {"GET": 80, "POST": 20}},
            "latency": {"p50": 10.5, "p95": 50.2, "p99": 100.1},
            "errors": {"total": 5, "by_type": {"ValidationError": 3, "HTTPException": 2}},
            "active_requests": 2,
            "agent_invocations": {"planner": 10, "executor": 5},
            "uptime_seconds": 3600.0,
        }

        mock_collector = MagicMock()
        mock_collector.get_metrics = MagicMock(return_value=mock_metrics)

        with patch("src.api.routes.system.get_metrics_collector", return_value=mock_collector):
            response = await system_client.get("/api/v1/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data == mock_metrics
            mock_collector.get_metrics.assert_called_once()

    async def test_get_metrics_handles_empty_metrics(self, system_client):
        """Should return empty metrics dictionary when no metrics available."""
        mock_collector = MagicMock()
        mock_collector.get_metrics = MagicMock(return_value={})

        with patch("src.api.routes.system.get_metrics_collector", return_value=mock_collector):
            response = await system_client.get("/api/v1/metrics")

            assert response.status_code == 200
            data = response.json()
            assert data == {}


@pytest.mark.asyncio
class TestSystemStatus:
    """Tests for GET /api/v1/status."""

    async def test_system_status_all_healthy(self, system_client):
        """Should return healthy status when all components are healthy."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.ha_url = "http://localhost:8123"
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value = MagicMock(return_value="test-token")
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"
        mock_settings.debug = False

        mock_mlflow_client = MagicMock()
        mock_mlflow_client.search_experiments = MagicMock(return_value=[])

        with (
            patch("src.storage.get_session", _mock_get_session),
            patch("src.api.routes.system.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_mlflow_client),
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Mock httpx response for Home Assistant check
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_httpx_context = AsyncMock()
            mock_httpx_context.__aenter__ = AsyncMock(return_value=mock_httpx_context)
            mock_httpx_context.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_context.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value = mock_httpx_context

            response = await system_client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["version"] == "0.1.0"
            assert data["environment"] == mock_settings.environment
            assert "timestamp" in data
            assert "uptime_seconds" in data
            assert isinstance(data["components"], list)
            assert len(data["components"]) == 3

            # Verify component names
            component_names = [c["name"] for c in data["components"]]
            assert "database" in component_names
            assert "mlflow" in component_names
            assert "home_assistant" in component_names

            # Verify all components are healthy
            for component in data["components"]:
                assert component["status"] == "healthy"
                assert "latency_ms" in component or component.get("latency_ms") is None

    async def test_system_status_database_unhealthy(self, system_client):
        """Should return unhealthy status when database is unavailable."""

        @asynccontextmanager
        async def _mock_get_session():
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(side_effect=Exception("DB connection failed"))
            yield mock_session

        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.debug = False

        mock_mlflow_client = MagicMock()
        mock_mlflow_client.search_experiments = MagicMock(return_value=[])

        with (
            patch("src.storage.get_session", _mock_get_session),
            patch("src.api.routes.system.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_mlflow_client),
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Mock httpx response for Home Assistant check
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_httpx_context = AsyncMock()
            mock_httpx_context.__aenter__ = AsyncMock(return_value=mock_httpx_context)
            mock_httpx_context.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_context.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value = mock_httpx_context

            response = await system_client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"  # Database is critical
            assert len(data["components"]) == 3

            # Find database component
            db_component = next(c for c in data["components"] if c["name"] == "database")
            assert db_component["status"] == "unhealthy"

    async def test_system_status_mlflow_degraded(self, system_client):
        """Should return degraded status when MLflow is unavailable."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.ha_url = "http://localhost:8123"
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value = MagicMock(return_value="test-token")
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"
        mock_settings.debug = False

        mock_mlflow_client_instance = MagicMock()
        mock_mlflow_client_instance.search_experiments = MagicMock(
            side_effect=Exception("MLflow connection failed")
        )

        with (
            patch("src.storage.get_session", _mock_get_session),
            patch("src.api.routes.system.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_mlflow_client_instance),
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Mock httpx response for Home Assistant check
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_httpx_context = AsyncMock()
            mock_httpx_context.__aenter__ = AsyncMock(return_value=mock_httpx_context)
            mock_httpx_context.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_context.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value = mock_httpx_context

            response = await system_client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"  # MLflow is non-critical

            # Find MLflow component
            mlflow_component = next(c for c in data["components"] if c["name"] == "mlflow")
            assert mlflow_component["status"] == "degraded"

    async def test_system_status_home_assistant_unconfigured(self, system_client):
        """Should return degraded status when Home Assistant URL is not configured."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.ha_url = None  # Not configured
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"
        mock_settings.debug = False

        mock_mlflow_client = MagicMock()
        mock_mlflow_client.search_experiments = MagicMock(return_value=[])

        with (
            patch("src.storage.get_session", _mock_get_session),
            patch("src.api.routes.system.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_mlflow_client),
        ):
            response = await system_client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"

            # Find Home Assistant component
            ha_component = next(c for c in data["components"] if c["name"] == "home_assistant")
            assert ha_component["status"] == "degraded"
            assert "not configured" in ha_component["message"].lower()

    async def test_system_status_home_assistant_timeout(self, system_client):
        """Should return unhealthy status when Home Assistant times out."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.ha_url = "http://localhost:8123"
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value = MagicMock(return_value="test-token")
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"
        mock_settings.debug = False

        mock_mlflow_client = MagicMock()
        mock_mlflow_client.search_experiments = MagicMock(return_value=[])

        with (
            patch("src.storage.get_session", _mock_get_session),
            patch("src.api.routes.system.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_mlflow_client),
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Mock httpx to raise TimeoutException
            mock_httpx_context = AsyncMock()
            mock_httpx_context.__aenter__ = AsyncMock(return_value=mock_httpx_context)
            mock_httpx_context.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_context.get = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            mock_httpx_client.return_value = mock_httpx_context

            response = await system_client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"  # HA is non-critical

            # Find Home Assistant component
            ha_component = next(c for c in data["components"] if c["name"] == "home_assistant")
            assert ha_component["status"] == "unhealthy"
            assert "timed out" in ha_component["message"].lower()

    async def test_system_status_home_assistant_auth_failed(self, system_client):
        """Should return unhealthy status when Home Assistant authentication fails."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.ha_url = "http://localhost:8123"
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value = MagicMock(return_value="invalid-token")
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"
        mock_settings.debug = False

        mock_mlflow_client = MagicMock()
        mock_mlflow_client.search_experiments = MagicMock(return_value=[])

        with (
            patch("src.storage.get_session", _mock_get_session),
            patch("src.api.routes.system.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_mlflow_client),
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Mock httpx response with 401 status
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_httpx_context = AsyncMock()
            mock_httpx_context.__aenter__ = AsyncMock(return_value=mock_httpx_context)
            mock_httpx_context.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_context.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value = mock_httpx_context

            response = await system_client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"

            # Find Home Assistant component
            ha_component = next(c for c in data["components"] if c["name"] == "home_assistant")
            assert ha_component["status"] == "unhealthy"
            assert "authentication failed" in ha_component["message"].lower()

    async def test_system_status_home_assistant_non_200_status(self, system_client):
        """Should return degraded status when Home Assistant returns non-200 status."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.ha_url = "http://localhost:8123"
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value = MagicMock(return_value="test-token")
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"
        mock_settings.debug = False

        mock_mlflow_client = MagicMock()
        mock_mlflow_client.search_experiments = MagicMock(return_value=[])

        with (
            patch("src.storage.get_session", _mock_get_session),
            patch("src.api.routes.system.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_mlflow_client),
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Mock httpx response with 500 status
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_httpx_context = AsyncMock()
            mock_httpx_context.__aenter__ = AsyncMock(return_value=mock_httpx_context)
            mock_httpx_context.__aexit__ = AsyncMock(return_value=None)
            mock_httpx_context.get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value = mock_httpx_context

            response = await system_client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"

            # Find Home Assistant component
            ha_component = next(c for c in data["components"] if c["name"] == "home_assistant")
            assert ha_component["status"] == "degraded"
            assert "status 500" in ha_component["message"]

    async def test_system_status_includes_uptime(self, system_client):
        """Should include uptime_seconds in response."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        mock_settings = MagicMock()
        mock_settings.environment = "testing"
        mock_settings.ha_url = None
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"
        mock_settings.debug = False

        mock_mlflow_client = MagicMock()
        mock_mlflow_client.search_experiments = MagicMock(return_value=[])

        with (
            patch("src.storage.get_session", _mock_get_session),
            patch("src.api.routes.system.get_settings", return_value=mock_settings),
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_mlflow_client),
        ):
            response = await system_client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()
            assert "uptime_seconds" in data
            assert isinstance(data["uptime_seconds"], (int, float))
            assert data["uptime_seconds"] >= 0
