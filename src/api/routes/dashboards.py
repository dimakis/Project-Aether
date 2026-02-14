"""API routes for Lovelace dashboard management.

Provides endpoints for listing HA dashboards and fetching
their full Lovelace configuration (views, cards, etc.).
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException

from src.ha import get_ha_client

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


@router.get("")
async def list_dashboards() -> list[dict[str, Any]]:
    """List all Lovelace dashboards configured in Home Assistant.

    Returns a list of dashboard metadata including id, title,
    mode, and url_path.
    """
    ha = get_ha_client()
    return cast("list[dict[str, Any]]", await ha.list_dashboards())


@router.get("/{url_path}/config")
async def get_dashboard_config(url_path: str) -> dict[str, Any]:
    """Fetch the full Lovelace config for a dashboard.

    Args:
        url_path: URL path of the dashboard. Use "default" for the
                  default/overview dashboard.

    Returns:
        Full Lovelace config dict with title, views, cards, etc.

    Raises:
        404: Dashboard not found.
    """
    ha = get_ha_client()

    # Map "default" to None so the client fetches /api/lovelace/config
    actual_path = None if url_path == "default" else url_path

    config = await ha.get_dashboard_config(actual_path)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{url_path}' not found")

    return cast("dict[str, Any]", config)
