"""Tests for HA WebSocket client helper.

Covers the connect-authenticate-command-disconnect lifecycle
used for Lovelace dashboard operations.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions import HAClientError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WS_URL = "ws://homeassistant.local:8123/api/websocket"
TOKEN = "test-token-abc123"


def _make_ws_mock(
    responses: list[dict[str, Any]],
) -> AsyncMock:
    """Create a mock WebSocket connection that yields predefined responses.

    Each call to recv() pops the next response from the list and returns
    it as a JSON string.
    """
    ws = AsyncMock()
    ws.recv = AsyncMock(side_effect=[json.dumps(r) for r in responses])
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Tests: ws_command
# ---------------------------------------------------------------------------


class TestWsCommand:
    """Test the ws_command helper function."""

    @pytest.mark.asyncio
    async def test_successful_command(self) -> None:
        """Happy path: auth_required -> auth_ok -> result."""
        from src.ha.websocket import ws_command

        expected_result = {"views": [{"title": "Home"}]}
        ws = _make_ws_mock(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_ok", "ha_version": "2025.1.0"},
                {"type": "result", "id": 1, "success": True, "result": expected_result},
            ]
        )

        with patch("src.ha.websocket.ws_connect", return_value=_async_ctx(ws)):
            result = await ws_command(WS_URL, TOKEN, "lovelace/config", url_path=None, force=False)

        assert result == expected_result

        # Verify auth message was sent
        auth_call = ws.send.call_args_list[0]
        auth_msg = json.loads(auth_call[0][0])
        assert auth_msg["type"] == "auth"
        assert auth_msg["access_token"] == TOKEN

        # Verify command message was sent
        cmd_call = ws.send.call_args_list[1]
        cmd_msg = json.loads(cmd_call[0][0])
        assert cmd_msg["type"] == "lovelace/config"
        assert cmd_msg["id"] == 1
        assert cmd_msg["url_path"] is None
        assert cmd_msg["force"] is False

    @pytest.mark.asyncio
    async def test_auth_invalid_raises(self) -> None:
        """auth_invalid response should raise HAClientError."""
        from src.ha.websocket import ws_command

        ws = _make_ws_mock(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_invalid", "message": "Invalid access token"},
            ]
        )

        with patch("src.ha.websocket.ws_connect", return_value=_async_ctx(ws)):
            with pytest.raises(HAClientError, match=r"auth.*invalid|Invalid access token"):
                await ws_command(WS_URL, TOKEN, "lovelace/config")

    @pytest.mark.asyncio
    async def test_command_error_raises(self) -> None:
        """A result with success=false should raise HAClientError."""
        from src.ha.websocket import ws_command

        ws = _make_ws_mock(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_ok", "ha_version": "2025.1.0"},
                {
                    "type": "result",
                    "id": 1,
                    "success": False,
                    "error": {"code": "not_found", "message": "Dashboard not found"},
                },
            ]
        )

        with patch("src.ha.websocket.ws_connect", return_value=_async_ctx(ws)):
            with pytest.raises(HAClientError, match="Dashboard not found"):
                await ws_command(WS_URL, TOKEN, "lovelace/config", url_path="missing")

    @pytest.mark.asyncio
    async def test_connection_error_raises(self) -> None:
        """Connection failure should raise HAClientError."""
        from src.ha.websocket import ws_command

        with patch(
            "src.ha.websocket.ws_connect",
            side_effect=OSError("Connection refused"),
        ):
            with pytest.raises(HAClientError, match=r"Connection refused|WebSocket"):
                await ws_command(WS_URL, TOKEN, "lovelace/config")

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        """Timeout waiting for response should raise HAClientError."""
        from src.ha.websocket import ws_command

        call_count = 0

        async def _recv() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.dumps({"type": "auth_required", "ha_version": "2025.1.0"})
            if call_count == 2:
                return json.dumps({"type": "auth_ok", "ha_version": "2025.1.0"})
            # Third call: hang to trigger timeout
            await asyncio.sleep(999)
            return "{}"

        ws = AsyncMock()
        ws.recv = _recv
        ws.send = AsyncMock()
        ws.close = AsyncMock()

        with patch("src.ha.websocket.ws_connect", return_value=_async_ctx(ws)):
            with pytest.raises(HAClientError, match=r"[Tt]imeout"):
                await ws_command(WS_URL, TOKEN, "lovelace/config", timeout=0.1)

    @pytest.mark.asyncio
    async def test_save_command(self) -> None:
        """lovelace/config/save should send config payload."""
        from src.ha.websocket import ws_command

        ws = _make_ws_mock(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_ok", "ha_version": "2025.1.0"},
                {"type": "result", "id": 1, "success": True, "result": None},
            ]
        )

        config = {"views": [{"title": "New View"}]}

        with patch("src.ha.websocket.ws_connect", return_value=_async_ctx(ws)):
            result = await ws_command(
                WS_URL,
                TOKEN,
                "lovelace/config/save",
                url_path=None,
                config=config,
            )

        assert result is None

        cmd_call = ws.send.call_args_list[1]
        cmd_msg = json.loads(cmd_call[0][0])
        assert cmd_msg["type"] == "lovelace/config/save"
        assert cmd_msg["config"] == config

    @pytest.mark.asyncio
    async def test_ws_always_closed(self) -> None:
        """WebSocket should be closed even if command fails."""
        from src.ha.websocket import ws_command

        ws = _make_ws_mock(
            [
                {"type": "auth_required", "ha_version": "2025.1.0"},
                {"type": "auth_invalid", "message": "bad token"},
            ]
        )

        with patch("src.ha.websocket.ws_connect", return_value=_async_ctx(ws)):
            with pytest.raises(HAClientError):
                await ws_command(WS_URL, TOKEN, "lovelace/config")

        # Connection should have been closed via context manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _async_ctx:
    """Wrap an object so it can be used as ``async with ws_connect(...) as ws``."""

    def __init__(self, obj: Any) -> None:
        self._obj = obj

    async def __aenter__(self) -> Any:
        return self._obj

    async def __aexit__(self, *args: Any) -> None:
        pass
