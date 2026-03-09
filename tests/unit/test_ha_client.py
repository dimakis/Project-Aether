"""Unit tests for src/ha/client.py (HAClient factory + caching)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ha.client import (
    HAClient,
    HAClientConfig,
    close_all_ha_clients,
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
        with patch("src.ha.base._try_get_db_config", return_value=None):
            client = HAClient()
        assert client is not None


class TestGetHAClient:
    def test_returns_default_client(self):
        with (
            patch("src.ha.client._resolve_zone_config", return_value=None),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            client = get_ha_client()
            assert isinstance(client, HAClient)

    def test_caches_client(self):
        with (
            patch("src.ha.client._resolve_zone_config", return_value=None),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
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
        with (
            patch("src.ha.client._resolve_zone_config", return_value=None),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            client = get_ha_client(zone_id="zone-missing")
            assert isinstance(client, HAClient)

    def test_different_zones_different_clients(self):
        with (
            patch("src.ha.client._resolve_zone_config", return_value=None),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            c1 = get_ha_client(zone_id="zone-1")
            c2 = get_ha_client(zone_id="zone-2")
            assert c1 is not c2


class TestResetHAClient:
    @pytest.mark.asyncio
    async def test_reset_specific_zone(self):
        with (
            patch("src.ha.client._resolve_zone_config", return_value=None),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            get_ha_client(zone_id="zone-1")
            await reset_ha_client(zone_id="zone-1")
            from src.ha.client import _clients

            assert "zone-1" not in _clients

    @pytest.mark.asyncio
    async def test_reset_all(self):
        with (
            patch("src.ha.client._resolve_zone_config", return_value=None),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            get_ha_client()
            get_ha_client(zone_id="zone-1")
            await reset_ha_client()
            from src.ha.client import _clients

            assert len(_clients) == 0


class TestGetHAClientAsync:
    @pytest.mark.asyncio
    async def test_returns_cached_client(self):
        with (
            patch(
                "src.ha.client._resolve_zone_config_async",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.ha.base._try_get_db_config_async", new_callable=AsyncMock, return_value=None
            ),
        ):
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
    @pytest.mark.asyncio
    async def test_returns_none_in_async_context(self):
        """When running inside an async loop, returns None."""
        from src.ha.client import _resolve_zone_config

        # In async context, get_running_loop() succeeds and we return None immediately
        result = _resolve_zone_config("__default__")
        assert result is None

    def test_returns_none_on_error(self):
        from src.ha.client import _resolve_zone_config

        with patch("src.settings.get_settings", side_effect=ConnectionError("No settings")):
            result = _resolve_zone_config("zone-1")
            assert result is None


class TestCloseAllHAClients:
    @pytest.mark.asyncio
    async def test_closes_all_cached_clients(self):
        """close_all_ha_clients() calls close() on every cached client."""
        from src.ha import client as _mod

        mock_client_1 = MagicMock(spec=HAClient)
        mock_client_1.close = AsyncMock()
        mock_client_2 = MagicMock(spec=HAClient)
        mock_client_2.close = AsyncMock()

        _mod._clients["zone-1"] = mock_client_1
        _mod._clients["zone-2"] = mock_client_2

        await close_all_ha_clients()

        mock_client_1.close.assert_awaited_once()
        mock_client_2.close.assert_awaited_once()
        assert len(_mod._clients) == 0

    @pytest.mark.asyncio
    async def test_noop_when_empty(self):
        """close_all_ha_clients() is a no-op when cache is empty."""
        from src.ha import client as _mod

        _mod._clients.clear()
        await close_all_ha_clients()
        assert len(_mod._clients) == 0

    @pytest.mark.asyncio
    async def test_tolerates_close_failure(self):
        """close_all_ha_clients() logs but does not raise if a client.close() fails."""
        from src.ha import client as _mod

        mock_ok = MagicMock(spec=HAClient)
        mock_ok.close = AsyncMock()
        mock_bad = MagicMock(spec=HAClient)
        mock_bad.close = AsyncMock(side_effect=ConnectionError("boom"))

        _mod._clients["ok"] = mock_ok
        _mod._clients["bad"] = mock_bad

        await close_all_ha_clients()

        mock_ok.close.assert_awaited_once()
        mock_bad.close.assert_awaited_once()
        assert len(_mod._clients) == 0


class TestResetHAClientCloses:
    @pytest.mark.asyncio
    async def test_reset_specific_zone_closes_client(self):
        """reset_ha_client() closes the evicted client when a zone_id is given."""
        from src.ha import client as _mod

        mock_client = MagicMock(spec=HAClient)
        mock_client.close = AsyncMock()

        _mod._clients["zone-1"] = mock_client

        await reset_ha_client(zone_id="zone-1")

        mock_client.close.assert_awaited_once()
        assert "zone-1" not in _mod._clients

    @pytest.mark.asyncio
    async def test_reset_all_closes_all_clients(self):
        """reset_ha_client() without zone_id closes all cached clients."""
        from src.ha import client as _mod

        mock_client_1 = MagicMock(spec=HAClient)
        mock_client_1.close = AsyncMock()
        mock_client_2 = MagicMock(spec=HAClient)
        mock_client_2.close = AsyncMock()

        _mod._clients["zone-1"] = mock_client_1
        _mod._clients["zone-2"] = mock_client_2

        await reset_ha_client()

        mock_client_1.close.assert_awaited_once()
        mock_client_2.close.assert_awaited_once()
        assert len(_mod._clients) == 0

    @pytest.mark.asyncio
    async def test_reset_tolerates_close_failure(self):
        """reset_ha_client() clears the cache even if close() raises."""
        from src.ha import client as _mod

        mock_client = MagicMock(spec=HAClient)
        mock_client.close = AsyncMock(side_effect=ConnectionError("fail"))

        _mod._clients["zone-1"] = mock_client

        await reset_ha_client(zone_id="zone-1")

        mock_client.close.assert_awaited_once()
        assert "zone-1" not in _mod._clients


class TestGetHADependency:
    @pytest.mark.asyncio
    async def test_returns_cached_client(self):
        """get_ha() DI dependency returns the cached HA client."""
        from src.api.deps import get_ha
        from src.ha import client as _mod

        mock_client = MagicMock(spec=HAClient)
        _mod._clients["__default__"] = mock_client

        result = await get_ha()
        assert result is mock_client

    @pytest.mark.asyncio
    async def test_returns_zone_specific_client(self):
        """get_ha() with zone_id returns the zone-specific client."""
        from src.api.deps import get_ha
        from src.ha import client as _mod

        mock_client = MagicMock(spec=HAClient)
        _mod._clients["zone-42"] = mock_client

        result = await get_ha(zone_id="zone-42")
        assert result is mock_client
