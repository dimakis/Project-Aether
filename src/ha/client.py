"""HA client wrapper for hass-ha tool invocation.

Provides a typed, async interface to the HA tools available
via the hass-ha server. Handles errors and provides consistent
response parsing.

Note: This client wraps the HA tools that Cursor has access to.
In production, this would use the HA REST API directly.

All public methods are traced via MLflow for observability.

This module acts as a thin facade that combines domain-specific
functionality from base, entities, automations, and diagnostics modules.
"""

from src.ha.automations import AutomationMixin
from src.ha.base import (
    BaseHAClient,
    HAClientConfig,
    HAClientError,
)
from src.ha.dashboards import DashboardMixin
from src.ha.diagnostics import DiagnosticMixin
from src.ha.entities import EntityMixin
from src.ha.helpers import HelperMixin

__all__ = [
    "HAClient",
    "HAClientConfig",
    "HAClientError",
    "get_ha_client",
    "get_ha_client_async",
    "reset_ha_client",
]


class HAClient(
    BaseHAClient, EntityMixin, AutomationMixin, HelperMixin, DiagnosticMixin, DashboardMixin
):
    """Client for invoking hass-ha tools.

    This class provides a typed interface to the HA tools.
    In the Cursor environment, these tools are available directly.
    In production, this would connect to the HA server.

    All public methods are traced via MLflow for observability.

    Usage:
        client = get_ha_client()  # default zone
        client = get_ha_client(zone_id="...")  # specific zone
        overview = await client.system_overview()
        entities = await client.list_entities(domain="light")
    """

    pass


# ─── Multi-zone client cache ─────────────────────────────────────────────────

# Key: zone_id (or "__default__" for the legacy/env-var fallback)
_clients: dict[str, HAClient] = {}
_client_lock = __import__("threading").Lock()
_DEFAULT_KEY = "__default__"


async def _resolve_zone_config_async(zone_id: str) -> HAClientConfig | None:
    """Resolve HA config from a specific zone in the DB. Use from async context only."""
    import structlog

    logger = structlog.get_logger(__name__)
    try:
        from src.api.auth import _get_jwt_secret
        from src.dal.ha_zones import HAZoneRepository
        from src.settings import get_settings
        from src.storage import get_session

        settings = get_settings()
        jwt_secret = _get_jwt_secret(settings)
        async with get_session() as session:
            repo = HAZoneRepository(session)
            if zone_id == _DEFAULT_KEY:
                zone = await repo.get_default()
            else:
                zone = await repo.get_by_id(zone_id)
            if not zone:
                return None
            conn = await repo.get_connection(zone.id, jwt_secret)
            if not conn:
                return None
            ha_url, ha_url_remote, ha_token, url_preference = conn
            return HAClientConfig(
                ha_url=ha_url,
                ha_url_remote=ha_url_remote,
                ha_token=ha_token,
                url_preference=url_preference,
            )
    except Exception as exc:
        logger.warning("zone_config_resolution_failed", zone_id=zone_id, reason=str(exc))
        return None


def _resolve_zone_config(zone_id: str) -> HAClientConfig | None:
    """Resolve HA config from DB (sync). Use only when no event loop is running."""
    import asyncio

    try:
        asyncio.get_running_loop()
        return None
    except RuntimeError:
        pass
    try:
        return asyncio.run(_resolve_zone_config_async(zone_id))
    except Exception:
        return None


def get_ha_client(zone_id: str | None = None) -> HAClient:
    """Get or create an HA client (sync). Prefer get_ha_client_async in async code.

    In async context DB config cannot be resolved here; use get_ha_client_async
    so the first request gets DB-backed config when available.
    """
    key = zone_id or _DEFAULT_KEY
    if key not in _clients:
        with _client_lock:
            if key not in _clients:
                config = _resolve_zone_config(key)
                if config:
                    _clients[key] = HAClient(config=config)
                else:
                    _clients[key] = HAClient()
    return _clients[key]


async def get_ha_client_async(zone_id: str | None = None) -> HAClient:
    """Get or create an HA client for a zone, resolving config from DB when in async context."""
    key = zone_id or _DEFAULT_KEY
    if key in _clients:
        return _clients[key]
    config = await _resolve_zone_config_async(key)
    with _client_lock:
        if key not in _clients:
            if config:
                _clients[key] = HAClient(config=config)
            else:
                _clients[key] = HAClient()
    return _clients[key]


def reset_ha_client(zone_id: str | None = None) -> None:
    """Reset HA client(s).

    If zone_id is provided, resets only that zone's client.
    If None, resets ALL cached clients (e.g. after setup).

    Thread-safe: Acquires lock before modifying cache.

    Args:
        zone_id: UUID of a specific zone to reset, or None for all.
    """
    with _client_lock:
        if zone_id is not None:
            _clients.pop(zone_id, None)
        else:
            _clients.clear()
