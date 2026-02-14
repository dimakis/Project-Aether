"""Dashboard operations for Home Assistant.

Provides methods for listing Lovelace dashboards and fetching
their full configuration via the HA REST API.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from src.ha.base import _trace_ha_call

logger = logging.getLogger(__name__)


class DashboardMixin:
    """Mixin providing Lovelace dashboard operations."""

    @_trace_ha_call("ha.list_dashboards")
    async def list_dashboards(self) -> list[dict[str, Any]]:
        """List all Lovelace dashboards configured in Home Assistant.

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

        Args:
            url_path: URL path of the dashboard (from list_dashboards).
                      None fetches the default/overview dashboard config.

        Returns:
            Dashboard config dict with title, views, etc.
            None if the dashboard is not found (404).

        Raises:
            HAClientError: On connection or server errors.
        """
        path = "/api/lovelace/config"
        if url_path:
            path = f"/api/lovelace/config/{url_path}"

        result = await self._request("GET", path)  # type: ignore[attr-defined]
        return cast("dict[str, Any] | None", result)
