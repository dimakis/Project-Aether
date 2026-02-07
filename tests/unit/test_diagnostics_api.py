"""Unit tests for diagnostics API endpoints.

Tests the /api/v1/diagnostics/* endpoints.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.api.main import create_app
from src.settings import Settings, get_settings

JWT_SECRET = "test-jwt-secret-key-for-testing-minimum-32bytes"


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        environment="testing",
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/aether_test",
        ha_url="http://localhost:8123",
        ha_token=SecretStr("test-token"),
        openai_api_key=SecretStr("test-api-key"),
        mlflow_tracking_uri="http://localhost:5000",
        sandbox_enabled=False,
        auth_username="admin",
        auth_password=SecretStr("test-password"),
        jwt_secret=SecretStr(JWT_SECRET),
        api_key=SecretStr(""),
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_jwt() -> str:
    payload = {
        "sub": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 72 * 3600,
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture
async def client(monkeypatch):
    """Test client with auth configured."""
    get_settings.cache_clear()
    settings = _make_settings()
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    get_settings.cache_clear()


@pytest.mark.asyncio
class TestHAHealth:
    """Test GET /api/v1/diagnostics/ha-health."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/diagnostics/ha-health")
        assert response.status_code == 401

    async def test_returns_health_data(self, client: AsyncClient):
        token = _make_jwt()

        from src.diagnostics.entity_health import EntityDiagnostic
        from src.diagnostics.integration_health import IntegrationHealth

        mock_unavail = [
            EntityDiagnostic(
                entity_id="sensor.broken",
                state="unavailable",
                available=False,
                last_changed="2026-02-06T10:00:00Z",
                integration="mqtt",
                issues=["Entity unavailable"],
            ),
        ]
        mock_stale = [
            EntityDiagnostic(
                entity_id="sensor.old",
                state="on",
                available=True,
                last_changed="2026-01-01T00:00:00Z",
                integration="zwave",
                issues=["Not updated in 24+ hours"],
            ),
        ]
        mock_unhealthy = [
            IntegrationHealth(
                entry_id="entry1",
                domain="mqtt",
                title="MQTT",
                state="setup_error",
                reason="Connection refused",
            ),
        ]

        with (
            patch(
                "src.api.routes.diagnostics.find_unavailable_entities",
                AsyncMock(return_value=mock_unavail),
            ),
            patch(
                "src.api.routes.diagnostics.find_stale_entities",
                AsyncMock(return_value=mock_stale),
            ),
            patch(
                "src.api.routes.diagnostics.find_unhealthy_integrations",
                AsyncMock(return_value=mock_unhealthy),
            ),
            patch("src.api.routes.diagnostics.get_ha_client"),
        ):
            response = await client.get(
                "/api/v1/diagnostics/ha-health",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["unavailable_entities"]) == 1
        assert data["unavailable_entities"][0]["entity_id"] == "sensor.broken"
        assert len(data["stale_entities"]) == 1
        assert len(data["unhealthy_integrations"]) == 1
        assert data["unhealthy_integrations"][0]["domain"] == "mqtt"


@pytest.mark.asyncio
class TestErrorLog:
    """Test GET /api/v1/diagnostics/error-log."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/diagnostics/error-log")
        assert response.status_code == 401

    async def test_returns_parsed_log(self, client: AsyncClient):
        token = _make_jwt()

        from src.diagnostics.log_parser import ErrorLogEntry

        mock_entries = [
            ErrorLogEntry(
                timestamp="2026-02-06 10:00:00",
                level="ERROR",
                logger="homeassistant.components.mqtt",
                message="Connection lost",
            ),
            ErrorLogEntry(
                timestamp="2026-02-06 10:01:00",
                level="WARNING",
                logger="homeassistant.components.zwave",
                message="Device not responding",
            ),
        ]
        mock_summary = {
            "total": 2,
            "errors": 1,
            "warnings": 1,
            "by_level": {"ERROR": 1, "WARNING": 1},
        }
        mock_patterns = [
            {
                "pattern": "connection_error",
                "severity": "high",
                "suggestion": "Check MQTT broker connectivity",
                "matched_entries": 1,
            }
        ]

        mock_mcp = MagicMock()
        mock_mcp.get_error_log = AsyncMock(return_value="fake log text")

        with (
            patch(
                "src.api.routes.diagnostics.get_ha_client",
                return_value=mock_mcp,
            ),
            patch(
                "src.api.routes.diagnostics.parse_error_log",
                return_value=mock_entries,
            ),
            patch(
                "src.api.routes.diagnostics.get_error_summary",
                return_value=mock_summary,
            ),
            patch(
                "src.api.routes.diagnostics.categorize_by_integration",
                return_value={"mqtt": [mock_entries[0]]},
            ),
            patch(
                "src.api.routes.diagnostics.analyze_errors",
                return_value=mock_patterns,
            ),
        ):
            response = await client.get(
                "/api/v1/diagnostics/error-log",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total"] == 2
        assert data["summary"]["errors"] == 1
        assert "mqtt" in data["by_integration"]
        assert len(data["known_patterns"]) == 1


@pytest.mark.asyncio
class TestConfigCheck:
    """Test GET /api/v1/diagnostics/config-check."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/diagnostics/config-check")
        assert response.status_code == 401

    async def test_returns_config_result(self, client: AsyncClient):
        token = _make_jwt()

        from src.diagnostics.config_validator import ConfigCheckResult

        mock_result = ConfigCheckResult(
            result="valid",
            errors=[],
            warnings=["Deprecated config found"],
        )

        mock_mcp = MagicMock()
        with (
            patch(
                "src.api.routes.diagnostics.get_ha_client",
                return_value=mock_mcp,
            ),
            patch(
                "src.api.routes.diagnostics.run_config_check",
                AsyncMock(return_value=mock_result),
            ),
        ):
            response = await client.get(
                "/api/v1/diagnostics/config-check",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["warnings"]) == 1
        assert data["errors"] == []


@pytest.mark.asyncio
class TestRecentTraces:
    """Test GET /api/v1/diagnostics/traces/recent."""

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/diagnostics/traces/recent")
        assert response.status_code == 401

    async def test_returns_traces(self, client: AsyncClient):
        token = _make_jwt()

        mock_trace = MagicMock()
        mock_trace.info.request_id = "trace-123"
        mock_trace.info.status.value = "OK"
        mock_trace.info.timestamp_ms = 1707264000000
        mock_trace.info.execution_time_ms = 1500

        mock_client = MagicMock()
        mock_client.search_traces.return_value = [mock_trace]

        with (
            patch("src.api.routes.diagnostics.MlflowClient", return_value=mock_client),
            patch("src.api.routes.diagnostics.get_settings") as mock_settings,
        ):
            mock_settings.return_value.mlflow_tracking_uri = "http://localhost:5000"
            mock_settings.return_value.mlflow_experiment_name = "aether"
            response = await client.get(
                "/api/v1/diagnostics/traces/recent",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0
