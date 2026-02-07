"""Tests for HA client DB config resolution and reset.

Tests:
- reset_ha_client() clears the singleton
- HA client falls back to env vars when no DB config
- HA client resolution logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import SecretStr

from src.settings import Settings


def _make_settings(**overrides) -> Settings:
    """Create test settings."""
    defaults = dict(
        environment="testing",
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/aether_test",
        ha_url="http://env-ha:8123",
        ha_token=SecretStr("env-token"),
        openai_api_key=SecretStr("test-key"),
        mlflow_tracking_uri="http://localhost:5000",
        sandbox_enabled=False,
        jwt_secret=SecretStr("test-jwt-secret-key-for-testing-minimum-32bytes"),
    )
    defaults.update(overrides)
    return Settings(**defaults)


class TestResetHAClient:
    """Tests for reset_ha_client()."""

    def test_reset_clears_singleton(self):
        """reset_ha_client sets the internal _client to None."""
        from src.ha import client as client_mod

        # Set a fake client
        client_mod._client = MagicMock()
        assert client_mod._client is not None

        client_mod.reset_ha_client()
        assert client_mod._client is None

    def test_get_ha_client_after_reset_creates_new(self, monkeypatch):
        """After reset, get_ha_client() creates a new instance."""
        from src.ha import client as client_mod
        from src.ha.base import BaseHAClient

        # Patch _resolve_config to avoid DB access
        settings = _make_settings()
        monkeypatch.setattr(
            "src.ha.base.get_settings", lambda: settings
        )
        monkeypatch.setattr(
            "src.ha.base._try_get_db_config", lambda s: None
        )

        # Reset
        client_mod.reset_ha_client()
        assert client_mod._client is None

        # Get a new one
        new_client = client_mod.get_ha_client()
        assert new_client is not None
        assert new_client.config.ha_url == "http://env-ha:8123"

        # Clean up
        client_mod._client = None


class TestTryGetDBConfig:
    """Tests for _try_get_db_config helper."""

    def test_returns_none_when_db_raises(self):
        """Returns None when DB raises an exception."""
        import asyncio as real_asyncio
        from src.ha.base import _try_get_db_config

        settings = _make_settings()

        # Patch get_session to raise an error (no DB available)
        with patch.dict("sys.modules", {}), \
             patch("src.storage.get_session", side_effect=Exception("no DB")):
            result = _try_get_db_config(settings)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_inside_event_loop(self):
        """Returns None when called from within an async context."""
        from src.ha.base import _try_get_db_config

        settings = _make_settings()

        # Inside async context - get_running_loop() returns a loop,
        # so the function should return None
        result = _try_get_db_config(settings)
        assert result is None


class TestResolveConfig:
    """Tests for BaseHAClient._resolve_config."""

    def test_fallback_to_env_vars(self, monkeypatch):
        """When DB config is unavailable, uses env vars."""
        from src.ha.base import BaseHAClient

        settings = _make_settings(
            ha_url="http://fallback-ha:8123",
            ha_token=SecretStr("fallback-token"),
        )
        monkeypatch.setattr("src.ha.base.get_settings", lambda: settings)
        monkeypatch.setattr("src.ha.base._try_get_db_config", lambda s: None)

        config = BaseHAClient._resolve_config()
        assert config.ha_url == "http://fallback-ha:8123"
        assert config.ha_token == "fallback-token"

    def test_uses_db_config_when_available(self, monkeypatch):
        """When DB config is available, uses it."""
        from src.ha.base import BaseHAClient

        settings = _make_settings(
            ha_url="http://env-ha:8123",
            ha_token=SecretStr("env-token"),
        )
        monkeypatch.setattr("src.ha.base.get_settings", lambda: settings)
        monkeypatch.setattr(
            "src.ha.base._try_get_db_config",
            lambda s: ("http://db-ha:8123", "db-token"),
        )

        config = BaseHAClient._resolve_config()
        assert config.ha_url == "http://db-ha:8123"
        assert config.ha_token == "db-token"
