"""Dashboard operations for Home Assistant.

Provides methods for listing Lovelace dashboards and fetching/saving
their full configuration.  Uses the HA WebSocket API as the primary
transport (same as HA's own frontend) with REST fallback.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from src.ha.base import _trace_ha_call
from src.ha.websocket import ws_command

logger = logging.getLogger(__name__)


class DashboardMixin:
    """Mixin providing Lovelace dashboard operations."""

    @_trace_ha_call("ha.list_dashboards")
    async def list_dashboards(self) -> list[dict[str, Any]]:
        """List all Lovelace dashboards configured in Home Assistant.

        Uses the REST API (reliable for listing).

        Returns:
            List of dashboard dicts with id, title, mode, url_path, etc.
            Returns empty list on failure.
        """
        try:
            result = await self._request("GET", "/api/lovelace/dashboards")  # type: ignore[attr-defined]
            if not result or not isinstance(result, list):
                return []
            return cast("list[dict[str, Any]]", result)
        except Exception as exc:
            logger.warning("Failed to list dashboards from HA: %s", exc)
            return []

    @_trace_ha_call("ha.get_dashboard_config")
    async def get_dashboard_config(
        self,
        url_path: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch the full Lovelace config for a dashboard.

        Primary: HA WebSocket API (``lovelace/config`` command).
        Fallback: REST ``GET /api/lovelace/config[/{url_path}]``.

        The WebSocket path is used because the REST endpoint returns 404
        for the default dashboard when it hasn't been explicitly saved to
        storage mode, while the WebSocket command works for all modes.

        Args:
            url_path: URL path of the dashboard (from list_dashboards).
                      None fetches the default/overview dashboard config.

        Returns:
            Dashboard config dict with title, views, etc.
            None if the dashboard is not found.

        Raises:
            HAClientError: On connection or server errors (when both
                           WebSocket and REST fail).
        """
        # ── Primary: WebSocket ──────────────────────────────────────
        try:
            result = await ws_command(
                self._get_ws_url(),  # type: ignore[attr-defined]
                self.config.ha_token,  # type: ignore[attr-defined]
                "lovelace/config",
                url_path=url_path,
                force=False,
            )
            return cast("dict[str, Any] | None", result)
        except Exception as ws_exc:
            logger.debug(
                "WebSocket lovelace/config failed, falling back to REST: %s",
                ws_exc,
            )

        # ── Fallback: REST ──────────────────────────────────────────
        rest_path = "/api/lovelace/config"
        if url_path:
            rest_path = f"/api/lovelace/config/{url_path}"

        result = await self._request("GET", rest_path)  # type: ignore[attr-defined]
        return cast("dict[str, Any] | None", result)

    @_trace_ha_call("ha.save_dashboard_config")
    async def save_dashboard_config(
        self,
        url_path: str | None,
        config: dict[str, Any],
    ) -> None:
        """Save (deploy) a Lovelace config to a dashboard in HA.

        Uses the HA WebSocket API ``lovelace/config/save`` command,
        which is the same method HA's frontend uses.

        Args:
            url_path: URL path of the target dashboard, or None for default.
            config: Full Lovelace config dict (must include ``views``).

        Raises:
            HAClientError: On connection, auth, or save errors.
        """
        await ws_command(
            self._get_ws_url(),  # type: ignore[attr-defined]
            self.config.ha_token,  # type: ignore[attr-defined]
            "lovelace/config/save",
            url_path=url_path,
            config=config,
        )
