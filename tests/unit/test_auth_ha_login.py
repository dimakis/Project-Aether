"""Tests for HA token login endpoint.

Tests:
- POST /auth/login/ha-token with valid token validates against stored HA URL
- POST /auth/login/ha-token with invalid token returns 401
- POST /auth/login/ha-token when HA unreachable returns graceful error
- Falls back to env var HA URL when no DB config exists
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.api.main import create_app
from src.settings import Settings, get_settings
from tests.helpers.auth import JWT_SECRET, make_test_settings

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


# =============================================================================
# HA Token Login Tests
# =============================================================================


class TestHATokenLogin:
    """Tests for POST /api/v1/auth/login/ha-token."""

    @pytest.mark.asyncio
    async def test_valid_ha_token_returns_jwt(self, monkeypatch):
        """A valid HA token against stored HA URL returns JWT."""
        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr(""))
        _patch_settings(monkeypatch, settings)

        # Mock DB with stored HA config
        from src.dal.system_config import encrypt_token

        mock_config = MagicMock()
        mock_config.ha_url = "http://ha.local:8123"
        mock_config.ha_token_encrypted = encrypt_token("stored-token", JWT_SECRET)
        mock_config.password_hash = None

        with (
            patch("src.api.routes.auth.get_session", _make_mock_session(mock_config)),
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
        ):
            mock_verify.return_value = {"message": "API running."}

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login/ha-token",
                    json={
                        "ha_token": "valid-user-token",
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["username"] == "admin"
        # Verify the token was validated against the stored HA URL
        mock_verify.assert_awaited_once_with("http://ha.local:8123", "valid-user-token")
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_invalid_ha_token_returns_401(self, monkeypatch):
        """An invalid HA token returns 401."""
        from fastapi import HTTPException

        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr(""))
        _patch_settings(monkeypatch, settings)

        with (
            patch("src.api.routes.auth.get_session", _make_mock_session(None)),
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
        ):
            mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid HA token")

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login/ha-token",
                    json={
                        "ha_token": "bad-token",
                    },
                )

        assert resp.status_code == 401
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_ha_unreachable_returns_502(self, monkeypatch):
        """HA unreachable returns a graceful error."""
        from fastapi import HTTPException

        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr(""))
        _patch_settings(monkeypatch, settings)

        with (
            patch("src.api.routes.auth.get_session", _make_mock_session(None)),
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
        ):
            mock_verify.side_effect = HTTPException(status_code=502, detail="Cannot connect to HA")

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login/ha-token",
                    json={
                        "ha_token": "some-token",
                    },
                )

        assert resp.status_code == 502
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_falls_back_to_env_var_ha_url(self, monkeypatch):
        """When no DB config exists, uses env var HA_URL."""
        get_settings.cache_clear()
        settings = make_test_settings(auth_password=SecretStr(""), ha_url="http://env-ha:8123")
        _patch_settings(monkeypatch, settings)

        with (
            patch("src.api.routes.auth.get_session", _make_mock_session(None)),
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
        ):
            mock_verify.return_value = {"message": "API running."}

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/login/ha-token",
                    json={
                        "ha_token": "valid-token",
                    },
                )

        assert resp.status_code == 200
        # Should have used the env var HA URL
        mock_verify.assert_awaited_once_with("http://env-ha:8123", "valid-token")
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_ha_token_login_is_exempt_from_auth(self, monkeypatch):
        """The HA token login endpoint doesn't require prior authentication."""
        get_settings.cache_clear()
        # Enable API key auth to verify this endpoint is exempt
        settings = make_test_settings(
            auth_password=SecretStr(""), api_key=SecretStr("required-key")
        )
        _patch_settings(monkeypatch, settings)

        with (
            patch("src.api.routes.auth.get_session", _make_mock_session(None)),
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
        ):
            mock_verify.return_value = {"message": "API running."}

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # No API key or JWT, should still work
                resp = await client.post(
                    "/api/v1/auth/login/ha-token",
                    json={
                        "ha_token": "valid-token",
                    },
                )

        assert resp.status_code == 200
        get_settings.cache_clear()
