"""Unit tests for security headers middleware.

Tests that security-related HTTP headers are properly set on responses.
"""

import time

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
async def sec_client(monkeypatch):
    get_settings.cache_clear()
    settings = _make_settings()
    from src import settings as settings_module
    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    get_settings.cache_clear()


@pytest.mark.asyncio
class TestSecurityHeaders:
    """Test that security headers are present on responses."""

    async def test_x_content_type_options(self, sec_client: AsyncClient):
        """X-Content-Type-Options: nosniff is set."""
        response = await sec_client.get("/api/v1/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options(self, sec_client: AsyncClient):
        """X-Frame-Options: DENY is set."""
        response = await sec_client.get("/api/v1/health")
        assert response.headers.get("x-frame-options") == "DENY"

    async def test_x_xss_protection(self, sec_client: AsyncClient):
        """X-XSS-Protection header is set."""
        response = await sec_client.get("/api/v1/health")
        assert response.headers.get("x-xss-protection") == "1; mode=block"

    async def test_referrer_policy(self, sec_client: AsyncClient):
        """Referrer-Policy is set."""
        response = await sec_client.get("/api/v1/health")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_cache_control_on_api(self, sec_client: AsyncClient):
        """API responses have no-store cache control."""
        response = await sec_client.get("/api/v1/health")
        assert "no-store" in response.headers.get("cache-control", "")

    async def test_correlation_id_still_present(self, sec_client: AsyncClient):
        """X-Correlation-ID header is still present alongside security headers."""
        response = await sec_client.get("/api/v1/health")
        assert response.headers.get("x-correlation-id") is not None

    async def test_security_headers_on_auth_error(self, sec_client: AsyncClient):
        """Security headers present even on 401 responses."""
        response = await sec_client.get("/api/v1/models")
        assert response.status_code == 401
        assert response.headers.get("x-content-type-options") == "nosniff"


@pytest.mark.asyncio
class TestCORSOrigins:
    """Test CORS origin configuration."""

    async def test_production_cors_restricts_origins(self, monkeypatch):
        """Production environment restricts CORS origins."""
        get_settings.cache_clear()
        settings = _make_settings(
            environment="production",
            allowed_origins="https://home.example.com,https://alt.example.com",
        )
        from src import settings as settings_module
        monkeypatch.setattr(settings_module, "get_settings", lambda: settings)
        app = create_app(settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Preflight request from allowed origin
            response = await client.options(
                "/api/v1/health",
                headers={
                    "Origin": "https://home.example.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert "access-control-allow-origin" in response.headers

            # Preflight from disallowed origin
            response2 = await client.options(
                "/api/v1/health",
                headers={
                    "Origin": "https://evil.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
            # Should not include the evil origin
            allow_origin = response2.headers.get("access-control-allow-origin", "")
            assert "evil.com" not in allow_origin

        get_settings.cache_clear()
