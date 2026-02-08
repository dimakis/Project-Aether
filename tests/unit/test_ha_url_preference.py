"""Tests for HA client URL preference logic.

Tests:
- connect() builds urls_to_try based on url_preference
- _request() builds urls_to_try based on url_preference
- HAClientConfig accepts url_preference field
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.ha.base import HAClientConfig, BaseHAClient


# ─── HAClientConfig ──────────────────────────────────────────────────────────


class TestHAClientConfigUrlPreference:
    """url_preference field on HAClientConfig."""

    def test_default_is_auto(self):
        """url_preference defaults to 'auto'."""
        config = HAClientConfig(ha_url="http://local:8123", ha_token="tok")
        assert config.url_preference == "auto"

    def test_accepts_local(self):
        """url_preference accepts 'local'."""
        config = HAClientConfig(
            ha_url="http://local:8123", ha_token="tok", url_preference="local"
        )
        assert config.url_preference == "local"

    def test_accepts_remote(self):
        """url_preference accepts 'remote'."""
        config = HAClientConfig(
            ha_url="http://local:8123",
            ha_token="tok",
            ha_url_remote="https://remote.example.com",
            url_preference="remote",
        )
        assert config.url_preference == "remote"


# ─── URL list building helper ────────────────────────────────────────────────


class TestBuildUrlsToTry:
    """_build_urls_to_try returns the correct URL list based on preference."""

    def _make_client(self, url_preference="auto", ha_url_remote=None):
        config = HAClientConfig(
            ha_url="http://local:8123",
            ha_url_remote=ha_url_remote,
            ha_token="tok",
            url_preference=url_preference,
        )
        return BaseHAClient(config=config)

    def test_auto_local_only(self):
        """auto with no remote → [local]."""
        client = self._make_client("auto")
        assert client._build_urls_to_try() == ["http://local:8123"]

    def test_auto_with_remote(self):
        """auto with remote → [local, remote]."""
        client = self._make_client("auto", ha_url_remote="https://remote:8123")
        assert client._build_urls_to_try() == [
            "http://local:8123",
            "https://remote:8123",
        ]

    def test_local_preference(self):
        """local → [local] even when remote is configured."""
        client = self._make_client("local", ha_url_remote="https://remote:8123")
        assert client._build_urls_to_try() == ["http://local:8123"]

    def test_remote_preference(self):
        """remote → [remote] only."""
        client = self._make_client("remote", ha_url_remote="https://remote:8123")
        assert client._build_urls_to_try() == ["https://remote:8123"]

    def test_remote_preference_no_remote_url_falls_back_to_local(self):
        """remote preference but no remote URL configured → [local]."""
        client = self._make_client("remote", ha_url_remote=None)
        assert client._build_urls_to_try() == ["http://local:8123"]


# ─── connect() ───────────────────────────────────────────────────────────────


class TestConnectUrlPreference:
    """connect() respects url_preference when choosing URLs."""

    @pytest.mark.asyncio
    async def test_connect_auto_tries_local_first(self):
        """With auto, connect tries local URL first."""
        config = HAClientConfig(
            ha_url="http://local:8123",
            ha_url_remote="https://remote:8123",
            ha_token="tok",
            url_preference="auto",
        )
        client = BaseHAClient(config=config)

        # Mock httpx to succeed on local
        mock_response = MagicMock(status_code=200)
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_http):
            await client.connect()

        assert client._active_url == "http://local:8123"

    @pytest.mark.asyncio
    async def test_connect_remote_only_tries_remote(self):
        """With remote preference, connect skips local and goes to remote."""
        config = HAClientConfig(
            ha_url="http://local:8123",
            ha_url_remote="https://remote:8123",
            ha_token="tok",
            url_preference="remote",
        )
        client = BaseHAClient(config=config)

        mock_response = MagicMock(status_code=200)
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_http):
            await client.connect()

        assert client._active_url == "https://remote:8123"
        # Should only have called with the remote URL
        call_args = mock_http.get.call_args
        assert "remote:8123" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_connect_local_only_skips_remote(self):
        """With local preference, connect does not try remote."""
        config = HAClientConfig(
            ha_url="http://local:8123",
            ha_url_remote="https://remote:8123",
            ha_token="tok",
            url_preference="local",
        )
        client = BaseHAClient(config=config)

        # Make local fail
        mock_response = MagicMock(status_code=500)
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_http), \
             pytest.raises(Exception, match="All connection attempts failed"):
            await client.connect()

        # All get() calls must have been to local URL, never remote
        for call in mock_http.get.call_args_list:
            url_arg = call[0][0]
            assert "local:8123" in url_arg, f"Unexpected URL tried: {url_arg}"
            assert "remote" not in url_arg, f"Remote URL should not be tried: {url_arg}"
