"""Lightweight HA WebSocket client for one-shot commands.

Provides a single ``ws_command`` helper that connects to HA's WebSocket API,
authenticates, sends one command, and returns the result.  Used for Lovelace
dashboard operations where the REST API is unreliable (e.g. default dashboard
returns 404 via REST but works via WebSocket).

Protocol reference:
    https://developers.home-assistant.io/docs/api/websocket
    https://github.com/home-assistant/frontend/blob/dev/src/data/lovelace/config/types.ts
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from websockets.asyncio.client import connect as ws_connect

from src.exceptions import HAClientError

__all__ = ["_authenticate", "ws_command", "ws_connect"]

logger = logging.getLogger(__name__)

# Default timeout for the entire connect-auth-command cycle (seconds).
DEFAULT_TIMEOUT = 15.0


async def ws_command(
    ws_url: str,
    token: str,
    command_type: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    **params: Any,
) -> Any:
    """Execute a single WebSocket command against Home Assistant.

    Opens a connection, authenticates, sends the command, reads the
    result, and closes.  This is intentionally not a persistent
    connection — each call is self-contained.

    Args:
        ws_url: Full WebSocket URL, e.g. ``ws://ha.local:8123/api/websocket``.
        token: Long-lived access token for HA authentication.
        command_type: HA WebSocket message type, e.g. ``"lovelace/config"``.
        timeout: Maximum seconds for the entire operation.
        **params: Additional parameters merged into the command message
                  (e.g. ``url_path=None``, ``config={...}``).

    Returns:
        The ``result`` field from the HA response (can be dict, list, or None).

    Raises:
        HAClientError: On authentication failure, command error, timeout,
                       or connection issues.
    """
    try:
        async with asyncio.timeout(timeout):
            return await _execute(ws_url, token, command_type, params)
    except TimeoutError as exc:
        raise HAClientError(
            f"Timeout after {timeout}s waiting for HA WebSocket response",
            tool="ws_command",
        ) from exc
    except HAClientError:
        raise  # Already wrapped
    except Exception as exc:
        raise HAClientError(
            f"WebSocket error: {exc}",
            tool="ws_command",
        ) from exc


async def _authenticate(ws: Any, token: str) -> None:
    """Authenticate a WebSocket connection to Home Assistant.

    Performs the HA WebSocket auth handshake: waits for ``auth_required``,
    sends the token, and validates ``auth_ok``.  Reusable by both the
    one-shot :func:`ws_command` and the persistent :class:`HAEventStream`.

    Args:
        ws: An open ``websockets`` connection.
        token: Long-lived access token for HA.

    Raises:
        HAClientError: On unexpected messages or authentication failure.
    """
    raw = await ws.recv()
    msg = json.loads(raw)
    if msg.get("type") != "auth_required":
        raise HAClientError(
            f"Expected auth_required, got {msg.get('type')}",
            tool="ws_auth",
        )

    await ws.send(json.dumps({"type": "auth", "access_token": token}))

    raw = await ws.recv()
    msg = json.loads(raw)
    if msg.get("type") == "auth_invalid":
        raise HAClientError(
            msg.get("message", "Authentication failed"),
            tool="ws_auth",
        )
    if msg.get("type") != "auth_ok":
        raise HAClientError(
            f"Expected auth_ok, got {msg.get('type')}",
            tool="ws_auth",
        )


async def _execute(
    ws_url: str,
    token: str,
    command_type: str,
    params: dict[str, Any],
) -> Any:
    """Internal: run the connect -> auth -> command -> close cycle."""
    async with ws_connect(ws_url) as ws:
        await _authenticate(ws, token)

        command: dict[str, Any] = {"id": 1, "type": command_type, **params}
        await ws.send(json.dumps(command))

        raw = await ws.recv()
        msg = json.loads(raw)

        if not msg.get("success"):
            error = msg.get("error", {})
            error_msg = error.get("message", "Unknown WebSocket command error")
            raise HAClientError(error_msg, tool="ws_command")

        return msg.get("result")
