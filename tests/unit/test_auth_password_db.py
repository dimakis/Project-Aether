"""Tests for password login with DB hash (first) and env var fallback.

Tests:
- DB password hash is checked before env var
- Correct DB password returns JWT
- Wrong DB password falls through to env var
- Env var fallback works when no DB config exists
- No password configured at all returns appropriate error
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.api.main import create_app
from src.settings import Settings, get_settings
from tests.helpers.auth import make_test_settings

# =============================================================================
# Fixtures
# =============================================================================


def _patch_settings(monkeypatch, settings: Settings) -> None:
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)


def _make_mock_session(config=None):
    """Create a mock session that returns the given config."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = config
    session.execute = AsyncMock(return_value=result_mock)

    @asynccontextmanager
    async def _mock_get_session():
        yield session

    return _mock_get_session


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt (like the setup endpoint does)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# =============================================================================
# Password DB Login Tests
# =============================================================================


class TestPasswordDBLogin:
    """Tests for password login with DB hash priority."""

    @pytest.mark.asyncio
    async def test_correct_db_password_returns_jwt(self, monkeypatch):
        """Correct DB password hash match returns JWT."""
        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr("env-password-123"))
        _patch_settings(monkeypatch, settings)

        db_password = "db-secret-password"
        mock_config = MagicMock()
        mock_config.password_hash = _hash_password(db_password)
        mock_config.ha_url = "http://ha.local:8123"

        with patch("src.api.routes.auth.get_session", _make_mock_session(mock_config)):
            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": "admin",
                        "password": db_password,
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["username"] == "admin"
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_wrong_db_password_falls_through_to_env(self, monkeypatch):
        """Wrong DB password falls through to env var and succeeds if matched."""
        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr("env-password-123"))
        _patch_settings(monkeypatch, settings)

        mock_config = MagicMock()
        mock_config.password_hash = _hash_password("different-db-password")
        mock_config.ha_url = "http://ha.local:8123"

        with patch("src.api.routes.auth.get_session", _make_mock_session(mock_config)):
            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # Use the env var password
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": "admin",
                        "password": "env-password-123",
                    },
                )

        assert resp.status_code == 200
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_no_db_config_uses_env_var(self, monkeypatch):
        """When no DB config exists, env var password works."""
        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr("env-only-pass"))
        _patch_settings(monkeypatch, settings)

        with patch("src.api.routes.auth.get_session", _make_mock_session(None)):
            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": "admin",
                        "password": "env-only-pass",
                    },
                )

        assert resp.status_code == 200
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_wrong_password_everywhere_returns_401(self, monkeypatch):
        """Wrong password for both DB and env returns 401."""
        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr("env-pass"))
        _patch_settings(monkeypatch, settings)

        mock_config = MagicMock()
        mock_config.password_hash = _hash_password("db-pass")

        with patch("src.api.routes.auth.get_session", _make_mock_session(mock_config)):
            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": "admin",
                        "password": "totally-wrong",
                    },
                )

        assert resp.status_code == 401
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_no_password_configured_returns_501(self, monkeypatch):
        """No password configured (no DB, no env) returns 501."""
        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr(""))
        _patch_settings(monkeypatch, settings)

        with patch("src.api.routes.auth.get_session", _make_mock_session(None)):
            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": "admin",
                        "password": "anything",
                    },
                )

        assert resp.status_code == 501
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_db_password_without_hash_uses_env_fallback(self, monkeypatch):
        """DB config exists but password_hash is None -> falls to env var."""
        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr("env-fallback"))
        _patch_settings(monkeypatch, settings)

        mock_config = MagicMock()
        mock_config.password_hash = None  # Setup was done without password

        with patch("src.api.routes.auth.get_session", _make_mock_session(mock_config)):
            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": "admin",
                        "password": "env-fallback",
                    },
                )

        assert resp.status_code == 200
        get_settings.cache_clear()
