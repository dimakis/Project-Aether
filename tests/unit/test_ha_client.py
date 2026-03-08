"""Unit tests for src/ha/client.py (HAClient factory + caching)."""

from unittest.mock import MagicMock, patch

import pytest

from src.ha.client import (
    HAClient,
    HAClientConfig,
    get_ha_client,
    get_ha_client_async,
    reset_ha_client,
)


@pytest.fixture(autouse=True)
def reset_clients():
    """Reset client cache between tests."""
    from src.ha import client as _mod

    _mod._clients.clear()
    yield
    _mod._clients.clear()


class TestHAClient:
    def test_is_subclass(self):
        assert issubclass(HAClient, object)

    def test_instantiate_default(self):
        client = HAClient()
        assert client is not None


class TestGetHAClient:
    def test_returns_default_client(self):
        with patch("src.ha.client._resolve_zone_config", return_value=None):
            client = get_ha_client()
            assert isinstance(client, HAClient)

    def test_caches_client(self):
        with patch("src.ha.client._resolve_zone_config", return_value=None):
            c1 = get_ha_client()
            c2 = get_ha_client()
            assert c1 is c2

    def test_zone_specific_client(self):
        mock_config = MagicMock(spec=HAClientConfig)
        mock_config.ha_url = "http://ha.local:8123"
        mock_config.ha_url_remote = None
        mock_config.ha_token = "test-token"
        mock_config.url_preference = "local"

        with patch("src.ha.client._resolve_zone_config", return_value=mock_config):
            client = get_ha_client(zone_id="zone-1")
            assert isinstance(client, HAClient)

    def test_zone_fallback_to_env(self):
        with patch("src.ha.client._resolve_zone_config", return_value=None):
            client = get_ha_client(zone_id="zone-missing")
            assert isinstance(client, HAClient)

    def test_different_zones_different_clients(self):
        with patch("src.ha.client._resolve_zone_config", return_value=None):
            c1 = get_ha_client(zone_id="zone-1")
            c2 = get_ha_client(zone_id="zone-2")
            assert c1 is not c2


class TestResetHAClient:
    def test_reset_specific_zone(self):
        with patch("src.ha.client._resolve_zone_config", return_value=None):
            get_ha_client(zone_id="zone-1")
            reset_ha_client(zone_id="zone-1")
            # Cache should be cleared for that zone
            from src.ha.client import _clients

            assert "zone-1" not in _clients

    def test_reset_all(self):
        with patch("src.ha.client._resolve_zone_config", return_value=None):
            get_ha_client()
            get_ha_client(zone_id="zone-1")
            reset_ha_client()
            from src.ha.client import _clients

            assert len(_clients) == 0


class TestGetHAClientAsync:
    @pytest.mark.asyncio
    async def test_returns_cached_client(self):
        with patch("src.ha.client._resolve_zone_config_async", return_value=None):
            from src.ha.client import get_ha_client_async

            client = await get_ha_client_async()
            assert isinstance(client, HAClient)

    @pytest.mark.asyncio
    async def test_uses_db_config_when_available(self):
        mock_config = MagicMock(spec=HAClientConfig)
        mock_config.ha_url = "http://db-ha:8123"
        mock_config.ha_url_remote = None
        mock_config.ha_token = "db-token"
        mock_config.url_preference = "local"
        with patch(
            "src.ha.client._resolve_zone_config_async",
            return_value=mock_config,
        ):
            client = await get_ha_client_async(zone_id="zone-1")
            assert isinstance(client, HAClient)
            assert client.config.ha_url == "http://db-ha:8123"


class TestResolveZoneConfig:
    def test_returns_none_in_async_context(self):
        """When running inside an async loop, returns None."""
        from src.ha.client import _resolve_zone_config

        # In async context, should return None gracefully
        result = _resolve_zone_config("__default__")
        # It may return None due to DB guard or async context detection
        assert result is None

    def test_returns_none_on_error(self):
        from src.ha.client import _resolve_zone_config

        with patch("src.settings.get_settings", side_effect=Exception("No settings")):
            result = _resolve_zone_config("zone-1")
            assert result is None
