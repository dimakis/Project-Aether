"""Unit tests for src/ha/base.py (BaseHAClient, config, URL handling)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.exceptions import HAClientError
from src.ha.base import BaseHAClient, HAClientConfig, _try_get_db_config


class TestHAClientConfig:
    def test_required_fields(self):
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        assert cfg.ha_url == "http://ha.local:8123"
        assert cfg.ha_token == "tok"
        assert cfg.timeout == 30
        assert cfg.url_preference == "auto"

    def test_optional_remote(self):
        cfg = HAClientConfig(
            ha_url="http://ha.local:8123",
            ha_url_remote="https://remote.ha.io",
            ha_token="tok",
        )
        assert cfg.ha_url_remote == "https://remote.ha.io"

    def test_custom_timeout(self):
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok", timeout=60)
        assert cfg.timeout == 60


class TestBaseHAClientInit:
    def test_init_with_config(self):
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)
        assert client.config is cfg
        assert client._connected is False

    def test_init_without_config_uses_settings(self):
        mock_settings = MagicMock()
        mock_settings.ha_url = "http://ha.local:8123"
        mock_settings.ha_url_remote = None
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value.return_value = "test-token"

        with (
            patch("src.ha.base.get_settings", return_value=mock_settings),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            client = BaseHAClient()
            assert client.config.ha_url == "http://ha.local:8123"


class TestBuildUrlsToTry:
    def _client_with_pref(self, pref, remote=None):
        cfg = HAClientConfig(
            ha_url="http://local:8123",
            ha_url_remote=remote,
            ha_token="tok",
            url_preference=pref,
        )
        return BaseHAClient(config=cfg)

    def test_auto_local_only(self):
        c = self._client_with_pref("auto")
        urls = c._build_urls_to_try()
        assert urls == ["http://local:8123"]

    def test_auto_with_remote(self):
        c = self._client_with_pref("auto", remote="https://remote:443")
        urls = c._build_urls_to_try()
        assert urls == ["http://local:8123", "https://remote:443"]

    def test_local_preference(self):
        c = self._client_with_pref("local", remote="https://remote:443")
        urls = c._build_urls_to_try()
        assert urls == ["http://local:8123"]

    def test_remote_preference(self):
        c = self._client_with_pref("remote", remote="https://remote:443")
        urls = c._build_urls_to_try()
        assert urls == ["https://remote:443"]

    def test_remote_preference_no_remote(self):
        c = self._client_with_pref("remote")
        urls = c._build_urls_to_try()
        assert urls == ["http://local:8123"]  # fallback


class TestGetUrl:
    def test_uses_active_url(self):
        cfg = HAClientConfig(ha_url="http://local:8123", ha_token="tok")
        c = BaseHAClient(config=cfg)
        c._active_url = "https://remote:443"
        assert c._get_url() == "https://remote:443"

    def test_fallback_to_config(self):
        cfg = HAClientConfig(ha_url="http://local:8123", ha_token="tok")
        c = BaseHAClient(config=cfg)
        assert c._get_url() == "http://local:8123"


class TestGetWsUrl:
    def test_derives_ws_from_http(self):
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        c = BaseHAClient(config=cfg)
        assert c._get_ws_url() == "ws://ha.local:8123/api/websocket"

    def test_derives_wss_from_https(self):
        cfg = HAClientConfig(ha_url="https://ha.local:8123", ha_token="tok")
        c = BaseHAClient(config=cfg)
        assert c._get_ws_url() == "wss://ha.local:8123/api/websocket"

    def test_strips_trailing_slash_from_url(self):
        cfg = HAClientConfig(ha_url="http://ha.local:8123/", ha_token="tok")
        c = BaseHAClient(config=cfg)
        assert c._get_ws_url() == "ws://ha.local:8123/api/websocket"


class TestTryGetDbConfig:
    def test_returns_none_on_error(self):
        with patch("src.storage.get_session", side_effect=SQLAlchemyError("no DB")):
            result = _try_get_db_config(MagicMock())
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_in_async_context(self):
        # In async context, get_running_loop() succeeds and we return None immediately
        result = _try_get_db_config(MagicMock())
        assert result is None


class TestResolveConfig:
    def test_fallback_to_env(self):
        mock_settings = MagicMock()
        mock_settings.ha_url = "http://local:8123"
        mock_settings.ha_url_remote = None
        mock_settings.ha_token = MagicMock()
        mock_settings.ha_token.get_secret_value.return_value = "env-token"

        with (
            patch("src.ha.base.get_settings", return_value=mock_settings),
            patch("src.ha.base._try_get_db_config", return_value=None),
        ):
            cfg = BaseHAClient._resolve_config()
            assert cfg.ha_token == "env-token"

    def test_uses_db_config_when_available(self):
        mock_settings = MagicMock()
        mock_settings.ha_url_remote = "https://remote.ha.io"

        with (
            patch("src.ha.base.get_settings", return_value=mock_settings),
            patch(
                "src.ha.base._try_get_db_config",
                return_value=("http://db-url:8123", "db-token"),
            ),
        ):
            cfg = BaseHAClient._resolve_config()
            assert cfg.ha_url == "http://db-url:8123"
            assert cfg.ha_token == "db-token"


class TestConnectionPooling:
    """Test that BaseHAClient reuses a shared httpx.AsyncClient."""

    def test_client_has_http_client_attribute(self):
        """BaseHAClient should expose an _http_client for connection reuse."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)
        # Client should have an _http_client attribute (None initially or a client)
        assert hasattr(client, "_http_client")

    @pytest.mark.asyncio
    async def test_request_reuses_http_client(self):
        """Multiple _request calls should reuse the same httpx.AsyncClient."""
        import httpx

        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"result": "ok"}'
        mock_response.json.return_value = {"result": "ok"}

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(return_value=mock_response)

        client._http_client = mock_http

        with patch("src.tracing.log_metric", MagicMock()):
            await client._request("GET", "/api/states")
            await client._request("GET", "/api/config")

        # The same client should have been used for both calls
        assert mock_http.request.call_count == 2

    @pytest.mark.asyncio
    async def test_close_closes_http_client(self):
        """close() should close the underlying httpx.AsyncClient."""
        import httpx

        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        client._http_client = mock_http

        await client.close()

        mock_http.aclose.assert_called_once()
        assert client._http_client is None


class TestConnectErrorPaths:
    """Tests for connect() exception handling."""

    @pytest.mark.asyncio
    async def test_connect_raises_haclient_error_on_connection_error(self) -> None:
        """connect() raises HAClientError when all URLs fail with ConnectionError."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=ConnectionError("connection refused"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HAClientError) as exc_info:
                await client.connect()
        assert "ConnectionError" in str(exc_info.value)
        assert "All connection attempts failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_raises_haclient_error_on_timeout(self) -> None:
        """connect() raises HAClientError when all URLs fail with TimeoutError."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=TimeoutError("timed out"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HAClientError) as exc_info:
                await client.connect()
        assert "TimeoutError" in str(exc_info.value)
        assert "All connection attempts failed" in str(exc_info.value)


class TestGetVersionAndSystemOverview:
    """Tests for get_version and system_overview error paths."""

    @pytest.mark.asyncio
    async def test_get_version_raises_when_no_data(self) -> None:
        """get_version raises HAClientError when _request returns None (e.g. 404)."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)
        client._request = AsyncMock(return_value=None)

        with pytest.raises(HAClientError, match="Failed to get HA version"):
            await client.get_version()

    @pytest.mark.asyncio
    async def test_system_overview_raises_when_no_states(self) -> None:
        """system_overview raises HAClientError when _request returns None."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)
        client._request = AsyncMock(return_value=None)

        with pytest.raises(HAClientError, match="Failed to get states"):
            await client.system_overview()

    @pytest.mark.asyncio
    async def test_get_version_returns_version_from_data(self) -> None:
        """get_version returns version string when _request returns data."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)
        client._request = AsyncMock(return_value={"version": "2024.1.0"})

        result = await client.get_version()
        assert result == "2024.1.0"

    @pytest.mark.asyncio
    async def test_system_overview_returns_overview_from_states(self) -> None:
        """system_overview builds overview from states."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)
        client._request = AsyncMock(
            return_value=[
                {"entity_id": "light.living", "state": "on"},
                {"entity_id": "light.bedroom", "state": "off"},
            ]
        )

        result = await client.system_overview()
        assert result["total_entities"] == 2
        assert "light" in result["domains"]
        assert result["domains"]["light"]["count"] == 2
        assert "on" in result["domains"]["light"]["states"]
        assert "off" in result["domains"]["light"]["states"]


class TestRequestHttpxErrorPaths:
    """Tests for _request() httpx exception handling (ConnectError, Timeout, HTTPError)."""

    @pytest.mark.asyncio
    async def test_request_connect_error_raises_haclient_error(self) -> None:
        """httpx.ConnectError is accumulated and HAClientError is raised."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        client._http_client = mock_http

        with patch("src.tracing.log_metric", MagicMock()):
            with pytest.raises(HAClientError) as exc_info:
                await client._request("GET", "/api/")
        assert "Connection failed" in str(exc_info.value)
        assert "All connection attempts failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_timeout_exception_raises_haclient_error(self) -> None:
        """httpx.TimeoutException is accumulated and HAClientError is raised."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        client._http_client = mock_http

        with patch("src.tracing.log_metric", MagicMock()):
            with pytest.raises(HAClientError) as exc_info:
                await client._request("GET", "/api/")
        assert "Timeout" in str(exc_info.value)
        assert "All connection attempts failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_http_error_raises_haclient_error(self) -> None:
        """Generic httpx.HTTPError is accumulated and HAClientError is raised."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(side_effect=httpx.HTTPError("generic http error"))
        client._http_client = mock_http

        with patch("src.tracing.log_metric", MagicMock()):
            with pytest.raises(HAClientError) as exc_info:
                await client._request("GET", "/api/")
        assert "HTTPError" in str(exc_info.value)
        assert "All connection attempts failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_timeout_error_raises_haclient_error(self) -> None:
        """Built-in TimeoutError is accumulated and HAClientError is raised."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(side_effect=TimeoutError("timed out"))
        client._http_client = mock_http

        with patch("src.tracing.log_metric", MagicMock()):
            with pytest.raises(HAClientError) as exc_info:
                await client._request("GET", "/api/")
        assert "TimeoutError" in str(exc_info.value)
        assert "All connection attempts failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_connection_error_raises_haclient_error(self) -> None:
        """Built-in ConnectionError is accumulated and HAClientError is raised."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(side_effect=ConnectionError("connection refused"))
        client._http_client = mock_http

        with patch("src.tracing.log_metric", MagicMock()):
            with pytest.raises(HAClientError) as exc_info:
                await client._request("GET", "/api/")
        assert "ConnectionError" in str(exc_info.value)
        assert "All connection attempts failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_returns_json_on_200(self) -> None:
        """_request returns parsed JSON on 200 response."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"version": "2024.1.0"}'
        mock_response.json = MagicMock(return_value={"version": "2024.1.0"})

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(return_value=mock_response)
        client._http_client = mock_http

        with patch("src.tracing.log_metric", MagicMock()):
            result = await client._request("GET", "/api/")
        assert result == {"version": "2024.1.0"}
        assert client._active_url == "http://ha.local:8123"

    @pytest.mark.asyncio
    async def test_request_returns_none_on_404(self) -> None:
        """_request returns None on 404 response."""
        cfg = HAClientConfig(ha_url="http://ha.local:8123", ha_token="tok")
        client = BaseHAClient(config=cfg)

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(return_value=mock_response)
        client._http_client = mock_http

        with patch("src.tracing.log_metric", MagicMock()):
            result = await client._request("GET", "/api/missing")
        assert result is None
