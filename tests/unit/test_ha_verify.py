"""Tests for HA token verification helper."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx


class TestVerifyHAConnection:
    """Tests for verify_ha_connection()."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_ha_info(self):
        """A valid HA token returns the HA API response body."""
        from src.api.ha_verify import verify_ha_connection

        mock_response = httpx.Response(
            200,
            json={"message": "API running."},
            request=httpx.Request("GET", "http://ha.local:8123/api/"),
        )

        with patch("src.api.ha_verify.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await verify_ha_connection("http://ha.local:8123", "valid-token")

        assert result == {"message": "API running."}
        mock_client.get.assert_awaited_once_with(
            "http://ha.local:8123/api/",
            headers={"Authorization": "Bearer valid-token"},
        )

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """An invalid token (401 response) raises HTTPException."""
        from fastapi import HTTPException

        from src.api.ha_verify import verify_ha_connection

        mock_response = httpx.Response(
            401,
            json={"message": "Invalid access token or password"},
            request=httpx.Request("GET", "http://ha.local:8123/api/"),
        )

        with patch("src.api.ha_verify.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await verify_ha_connection("http://ha.local:8123", "bad-token")

        assert exc_info.value.status_code == 401
        assert "Invalid HA token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_unreachable_host_raises_502(self):
        """An unreachable HA host raises HTTPException with 502."""
        from fastapi import HTTPException

        from src.api.ha_verify import verify_ha_connection

        with patch("src.api.ha_verify.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await verify_ha_connection("http://192.168.1.99:8123", "token")

        assert exc_info.value.status_code == 502
        assert "Cannot connect" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_timeout_raises_504(self):
        """A timeout contacting HA raises HTTPException with 504."""
        from fastapi import HTTPException

        from src.api.ha_verify import verify_ha_connection

        with patch("src.api.ha_verify.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await verify_ha_connection("http://ha.local:8123", "token")

        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_strips_trailing_slash_from_url(self):
        """HA URL trailing slash is handled correctly."""
        from src.api.ha_verify import verify_ha_connection

        mock_response = httpx.Response(
            200,
            json={"message": "API running."},
            request=httpx.Request("GET", "http://ha.local:8123/api/"),
        )

        with patch("src.api.ha_verify.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            # URL with trailing slash
            await verify_ha_connection("http://ha.local:8123/", "valid-token")

        # Should strip trailing slash so it doesn't double up
        mock_client.get.assert_awaited_once_with(
            "http://ha.local:8123/api/",
            headers={"Authorization": "Bearer valid-token"},
        )

    @pytest.mark.asyncio
    async def test_non_200_non_401_raises_502(self):
        """An unexpected HTTP status (e.g. 500) raises 502."""
        from fastapi import HTTPException

        from src.api.ha_verify import verify_ha_connection

        mock_response = httpx.Response(
            500,
            text="Internal Server Error",
            request=httpx.Request("GET", "http://ha.local:8123/api/"),
        )

        with patch("src.api.ha_verify.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await verify_ha_connection("http://ha.local:8123", "token")

        assert exc_info.value.status_code == 502
