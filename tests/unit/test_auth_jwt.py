"""Unit tests for JWT authentication.

Tests the JWT-based session authentication including:
- Password login with JWT cookie response
- JWT token validation (cookie and Bearer header)
- Logout (cookie clearing)
- /auth/me session check
- JWT + API key coexistence
- Auth bypass when AUTH_PASSWORD is not set
"""

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.api.main import create_app
from src.settings import Settings, get_settings

# =============================================================================
# Fixtures
# =============================================================================


def _make_settings(**overrides) -> Settings:
    """Create test settings with auth defaults."""
    defaults = {
        "environment": "testing",
        "debug": True,
        "database_url": "postgresql+asyncpg://test:test@localhost:5432/aether_test",
        "ha_url": "http://localhost:8123",
        "ha_token": SecretStr("test-token"),
        "openai_api_key": SecretStr("test-api-key"),
        "mlflow_tracking_uri": "http://localhost:5000",
        "sandbox_enabled": False,
        "auth_username": "admin",
        "auth_password": SecretStr("test-password-123"),
        "jwt_secret": SecretStr("test-jwt-secret-key-for-testing-minimum-32bytes"),
        "jwt_expiry_hours": 72,
        "api_key": SecretStr(""),  # API key auth disabled by default
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _patch_settings(monkeypatch, settings: Settings) -> None:
    """Monkeypatch get_settings() on the settings module.

    auth.py and auth routes use `import src.settings as _settings_mod`
    (module-level import), so patching the module attribute is sufficient.
    """
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)


def _patch_db_session(monkeypatch) -> None:
    """Patch get_session in auth routes to return a mock (no real DB).

    The login endpoint now checks the DB for password hash before
    falling back to env vars. This mock returns no config (None)
    so the env var fallback is used in tests.
    """
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def _mock_get_session():
        yield mock_session

    monkeypatch.setattr("src.api.routes.auth.get_session", _mock_get_session)


@pytest.fixture
async def auth_client(monkeypatch):
    """Create a test client with JWT auth enabled."""
    get_settings.cache_clear()
    settings = _make_settings()
    _patch_settings(monkeypatch, settings)
    _patch_db_session(monkeypatch)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    get_settings.cache_clear()


@pytest.fixture
async def auth_and_apikey_client(monkeypatch):
    """Create a test client with both JWT and API key auth enabled."""
    get_settings.cache_clear()
    settings = _make_settings(api_key=SecretStr("test-api-key-123"))
    _patch_settings(monkeypatch, settings)
    _patch_db_session(monkeypatch)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    get_settings.cache_clear()


@pytest.fixture
async def no_password_client(monkeypatch):
    """Create a test client with no auth password set (auth disabled)."""
    get_settings.cache_clear()
    settings = _make_settings(auth_password=SecretStr(""))
    _patch_settings(monkeypatch, settings)
    _patch_db_session(monkeypatch)
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    get_settings.cache_clear()


def _make_jwt(
    secret: str = "test-jwt-secret-key-for-testing-minimum-32bytes",
    exp_hours: int = 72,
    sub: str = "admin",
) -> str:
    """Create a valid JWT token for testing."""
    payload = {
        "sub": sub,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_hours * 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


# =============================================================================
# Login Tests
# =============================================================================


@pytest.mark.asyncio
class TestPasswordLogin:
    """Test POST /api/v1/auth/login endpoint."""

    async def test_login_with_valid_credentials(self, auth_client: AsyncClient):
        """Successful login returns 200 and sets JWT cookie."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-password-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["username"] == "admin"

        # Check that httpOnly cookie is set
        cookies = response.cookies
        assert "aether_session" in cookies

    async def test_login_with_wrong_password(self, auth_client: AsyncClient):
        """Wrong password returns 401."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        assert response.status_code == 401

    async def test_login_with_wrong_username(self, auth_client: AsyncClient):
        """Wrong username returns 401."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={"username": "hacker", "password": "test-password-123"},
        )
        assert response.status_code == 401

    async def test_login_without_body(self, auth_client: AsyncClient):
        """Missing body returns 422."""
        response = await auth_client.post("/api/v1/auth/login")
        assert response.status_code == 422

    async def test_login_endpoint_exempt_from_auth(self, auth_client: AsyncClient):
        """Login endpoint should be accessible without prior authentication."""
        response = await auth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-password-123"},
        )
        # Should not get 401 from the global auth dependency
        assert response.status_code == 200


# =============================================================================
# Logout Tests
# =============================================================================


@pytest.mark.asyncio
class TestLogout:
    """Test POST /api/v1/auth/logout endpoint."""

    async def test_logout_clears_cookie(self, auth_client: AsyncClient):
        """Logout should clear the session cookie."""
        # First login
        login_resp = await auth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-password-123"},
        )
        assert login_resp.status_code == 200

        # Then logout
        token = login_resp.json()["token"]
        response = await auth_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Cookie should be cleared (max_age=0 or deleted)
        set_cookie = response.headers.get("set-cookie", "")
        assert "aether_session" in set_cookie


# =============================================================================
# Session Check Tests
# =============================================================================


@pytest.mark.asyncio
class TestAuthMe:
    """Test GET /api/v1/auth/me endpoint."""

    async def test_me_with_valid_jwt_cookie(self, auth_client: AsyncClient):
        """GET /auth/me with valid JWT cookie returns user info."""
        # Login first to get cookie
        login_resp = await auth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-password-123"},
        )
        token = login_resp.json()["token"]

        response = await auth_client.get(
            "/api/v1/auth/me",
            cookies={"aether_session": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["username"] == "admin"

    async def test_me_with_valid_bearer_token(self, auth_client: AsyncClient):
        """GET /auth/me with valid Bearer token returns user info."""
        token = _make_jwt()
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True

    async def test_me_without_credentials(self, auth_client: AsyncClient):
        """GET /auth/me without any credentials returns 401."""
        response = await auth_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_with_expired_jwt(self, auth_client: AsyncClient):
        """GET /auth/me with expired JWT returns 401."""
        token = _make_jwt(exp_hours=-1)  # Already expired
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_me_with_invalid_jwt(self, auth_client: AsyncClient):
        """GET /auth/me with invalid JWT returns 401."""
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )
        assert response.status_code == 401

    async def test_me_with_wrong_secret(self, auth_client: AsyncClient):
        """GET /auth/me with JWT signed by wrong secret returns 401."""
        token = _make_jwt(secret="wrong-secret-but-long-enough-32bytes!!")
        response = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


# =============================================================================
# JWT Protected Route Tests
# =============================================================================


@pytest.mark.asyncio
class TestJWTProtectedRoutes:
    """Test that JWT tokens work for accessing protected routes.

    Uses /api/v1/models endpoint which doesn't require DB access,
    avoiding connection hangs in unit tests.
    """

    async def test_protected_route_with_jwt_cookie(self, auth_client: AsyncClient):
        """Protected route accessible with JWT cookie."""
        token = _make_jwt()
        response = await auth_client.get(
            "/api/v1/models",
            cookies={"aether_session": token},
        )
        # Should not be 401 (auth passes)
        assert response.status_code != 401

    async def test_protected_route_with_bearer_token(self, auth_client: AsyncClient):
        """Protected route accessible with Bearer token."""
        token = _make_jwt()
        response = await auth_client.get(
            "/api/v1/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code != 401

    async def test_protected_route_without_any_auth(self, auth_client: AsyncClient):
        """Protected route returns 401 without authentication."""
        response = await auth_client.get("/api/v1/models")
        assert response.status_code == 401

    async def test_protected_route_with_expired_jwt(self, auth_client: AsyncClient):
        """Protected route returns 401 with expired JWT."""
        token = _make_jwt(exp_hours=-1)
        response = await auth_client.get(
            "/api/v1/models",
            cookies={"aether_session": token},
        )
        assert response.status_code == 401


# =============================================================================
# JWT + API Key Coexistence Tests
# =============================================================================


@pytest.mark.asyncio
class TestJWTAndAPIKeyCoexistence:
    """Test that JWT and API key auth work side by side."""

    async def test_api_key_still_works(self, auth_and_apikey_client: AsyncClient):
        """API key auth continues to work alongside JWT."""
        response = await auth_and_apikey_client.get(
            "/api/v1/models",
            headers={"X-API-Key": "test-api-key-123"},
        )
        assert response.status_code != 401

    async def test_jwt_works_when_api_key_configured(self, auth_and_apikey_client: AsyncClient):
        """JWT auth works even when API key is also configured."""
        token = _make_jwt()
        response = await auth_and_apikey_client.get(
            "/api/v1/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code != 401

    async def test_neither_auth_returns_401(self, auth_and_apikey_client: AsyncClient):
        """No auth at all returns 401 when both are configured."""
        response = await auth_and_apikey_client.get("/api/v1/models")
        assert response.status_code == 401


# =============================================================================
# Auth Bypass Tests
# =============================================================================


@pytest.mark.asyncio
class TestAuthBypass:
    """Test auth behavior when password is not configured."""

    async def test_no_password_disables_jwt_auth(self, no_password_client: AsyncClient):
        """When AUTH_PASSWORD is empty, routes are accessible without JWT."""
        response = await no_password_client.get("/api/v1/models")
        # Should not require auth
        assert response.status_code != 401

    async def test_login_returns_error_when_no_password(self, no_password_client: AsyncClient):
        """Login endpoint returns error when auth is not configured."""
        response = await no_password_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "anything"},
        )
        # Should indicate auth is not configured
        assert response.status_code in (400, 404, 501)


# =============================================================================
# Health Endpoint Exemption
# =============================================================================


@pytest.mark.asyncio
class TestHealthExemptionWithJWT:
    """Test that health endpoints remain exempt with JWT auth."""

    async def test_health_works_without_jwt(self, auth_client: AsyncClient):
        """Health endpoint works without any authentication."""
        response = await auth_client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_metrics_requires_auth(self, auth_client: AsyncClient):
        """Metrics endpoint requires authentication."""
        response = await auth_client.get("/api/v1/metrics")
        assert response.status_code == 401
