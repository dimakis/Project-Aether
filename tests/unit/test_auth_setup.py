"""Tests for HA-verified setup endpoints.

Tests:
- GET /auth/setup-status returns setup state
- POST /auth/setup validates HA, stores config, returns JWT
- POST /auth/setup returns 409 if already set up
- Invalid HA token rejected during setup
- Password is optional during setup
"""

from unittest.mock import AsyncMock, MagicMock, patch

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
        "auth_password": SecretStr(""),
        "jwt_secret": SecretStr("test-jwt-secret-key-for-testing-minimum-32bytes"),
        "jwt_expiry_hours": 72,
        "api_key": SecretStr(""),
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _patch_settings(monkeypatch, settings: Settings) -> None:
    """Monkeypatch get_settings() on the settings module."""
    from src import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: settings)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_get_session(mock_session):
    """Patch get_session to yield mock_session."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _mock_get_session():
        yield mock_session

    return _mock_get_session


# =============================================================================
# Setup Status Tests
# =============================================================================


class TestSetupStatus:
    """Tests for GET /auth/setup-status."""

    @pytest.mark.asyncio
    async def test_setup_not_complete(self, monkeypatch, mock_get_session):
        """Returns setup_complete=false when no config exists."""
        get_settings.cache_clear()
        settings = _make_settings()
        _patch_settings(monkeypatch, settings)

        with (
            patch("src.api.routes.auth.get_session", mock_get_session),
            patch("src.api.routes.auth.SystemConfigRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo.is_setup_complete.return_value = False
            mock_repo_cls.return_value = mock_repo

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/auth/setup-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["setup_complete"] is False
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_setup_complete(self, monkeypatch, mock_get_session):
        """Returns setup_complete=true when config exists."""
        get_settings.cache_clear()
        settings = _make_settings()
        _patch_settings(monkeypatch, settings)

        with (
            patch("src.api.routes.auth.get_session", mock_get_session),
            patch("src.api.routes.auth.SystemConfigRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo.is_setup_complete.return_value = True
            mock_repo_cls.return_value = mock_repo

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/auth/setup-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["setup_complete"] is True
        get_settings.cache_clear()


# =============================================================================
# Setup Endpoint Tests
# =============================================================================


class TestSetupEndpoint:
    """Tests for POST /auth/setup."""

    @pytest.mark.asyncio
    async def test_valid_setup_stores_config_and_returns_jwt(
        self, monkeypatch, mock_session, mock_get_session
    ):
        """Valid HA token + optional password stores config and returns JWT."""
        get_settings.cache_clear()
        settings = _make_settings()
        _patch_settings(monkeypatch, settings)

        mock_config = MagicMock()
        mock_config.id = "config-id"

        with (
            patch("src.api.routes.auth.get_session", mock_get_session),
            patch("src.api.routes.auth.SystemConfigRepository") as mock_repo_cls,
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
            patch("src.dal.ha_zones.HAZoneRepository", return_value=AsyncMock()),
        ):
            mock_repo = AsyncMock()
            mock_repo.is_setup_complete.return_value = False
            mock_repo.create_config.return_value = mock_config
            mock_repo_cls.return_value = mock_repo
            mock_verify.return_value = {"message": "API running."}

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/setup",
                    json={
                        "ha_url": "http://ha.local:8123",
                        "ha_token": "valid-ha-token",
                        "password": "my-fallback-pass",
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["message"] == "Setup complete"
        # Verify HA was validated
        mock_verify.assert_awaited_once_with("http://ha.local:8123", "valid-ha-token")
        # Verify config was stored
        mock_repo.create_config.assert_awaited_once()
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_setup_already_complete_returns_409(self, monkeypatch, mock_get_session):
        """POST /auth/setup returns 409 if already configured."""
        get_settings.cache_clear()
        settings = _make_settings()
        _patch_settings(monkeypatch, settings)

        with (
            patch("src.api.routes.auth.get_session", mock_get_session),
            patch("src.api.routes.auth.SystemConfigRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo.is_setup_complete.return_value = True
            mock_repo_cls.return_value = mock_repo

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/setup",
                    json={
                        "ha_url": "http://ha.local:8123",
                        "ha_token": "valid-ha-token",
                    },
                )

        assert resp.status_code == 409
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_invalid_ha_token_rejected(self, monkeypatch, mock_get_session):
        """POST /auth/setup with invalid HA token returns error."""
        from fastapi import HTTPException

        get_settings.cache_clear()
        settings = _make_settings()
        _patch_settings(monkeypatch, settings)

        with (
            patch("src.api.routes.auth.get_session", mock_get_session),
            patch("src.api.routes.auth.SystemConfigRepository") as mock_repo_cls,
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
        ):
            mock_repo = AsyncMock()
            mock_repo.is_setup_complete.return_value = False
            mock_repo_cls.return_value = mock_repo
            mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid HA token")

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/setup",
                    json={
                        "ha_url": "http://ha.local:8123",
                        "ha_token": "bad-token",
                    },
                )

        assert resp.status_code == 401
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_password_optional_in_setup(self, monkeypatch, mock_session, mock_get_session):
        """Setup works without a password (password field absent or null)."""
        get_settings.cache_clear()
        settings = _make_settings()
        _patch_settings(monkeypatch, settings)

        mock_config = MagicMock()
        mock_config.id = "config-id"

        with (
            patch("src.api.routes.auth.get_session", mock_get_session),
            patch("src.api.routes.auth.SystemConfigRepository") as mock_repo_cls,
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
            patch("src.dal.ha_zones.HAZoneRepository", return_value=AsyncMock()),
        ):
            mock_repo = AsyncMock()
            mock_repo.is_setup_complete.return_value = False
            mock_repo.create_config.return_value = mock_config
            mock_repo_cls.return_value = mock_repo
            mock_verify.return_value = {"message": "API running."}

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/setup",
                    json={
                        "ha_url": "http://ha.local:8123",
                        "ha_token": "valid-ha-token",
                        # No password field
                    },
                )

        assert resp.status_code == 200
        # Verify password_hash was None
        call_args = mock_repo.create_config.call_args
        assert call_args.kwargs.get("password_hash") is None or (
            len(call_args.args) > 2 and call_args.args[2] is None
        )
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_setup_stores_encrypted_token(self, monkeypatch, mock_session, mock_get_session):
        """Setup encrypts the HA token before storing."""
        get_settings.cache_clear()
        settings = _make_settings()
        _patch_settings(monkeypatch, settings)

        mock_config = MagicMock()
        mock_config.id = "config-id"

        with (
            patch("src.api.routes.auth.get_session", mock_get_session),
            patch("src.api.routes.auth.SystemConfigRepository") as mock_repo_cls,
            patch("src.api.routes.auth.verify_ha_connection") as mock_verify,
            patch("src.dal.ha_zones.HAZoneRepository", return_value=AsyncMock()),
        ):
            mock_repo = AsyncMock()
            mock_repo.is_setup_complete.return_value = False
            mock_repo.create_config.return_value = mock_config
            mock_repo_cls.return_value = mock_repo
            mock_verify.return_value = {"message": "API running."}

            app = create_app(settings)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/setup",
                    json={
                        "ha_url": "http://ha.local:8123",
                        "ha_token": "my-secret-ha-token",
                    },
                )

        assert resp.status_code == 200
        # Verify encrypted token was passed (not plaintext)
        call_kwargs = mock_repo.create_config.call_args.kwargs
        assert call_kwargs["ha_token_encrypted"] != "my-secret-ha-token"
        assert len(call_kwargs["ha_token_encrypted"]) > 0
        get_settings.cache_clear()
