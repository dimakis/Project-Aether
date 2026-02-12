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
from src.ha.diagnostics import DiagnosticMixin
from src.ha.entities import EntityMixin
from src.ha.helpers import HelperMixin

# Re-export for backward compatibility
__all__ = ["HAClient", "HAClientConfig", "HAClientError", "get_ha_client", "reset_ha_client"]


class HAClient(BaseHAClient, EntityMixin, AutomationMixin, HelperMixin, DiagnosticMixin):
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


def _resolve_zone_config(zone_id: str) -> HAClientConfig | None:
    """Try to resolve HA config from a specific zone in the DB.

    Returns HAClientConfig if found, None otherwise.
    Runs synchronously (for singleton init outside async context).
    """
    import asyncio

    import structlog

    logger = structlog.get_logger(__name__)
    try:
        from src.api.auth import _get_jwt_secret
        from src.dal.ha_zones import HAZoneRepository
        from src.settings import get_settings
        from src.storage import get_session

        settings = get_settings()
        jwt_secret = _get_jwt_secret(settings)

        async def _fetch() -> HAClientConfig | None:
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

        try:
            asyncio.get_running_loop()
            # Inside async context — can't use asyncio.run()
            return None
        except RuntimeError:
            result = asyncio.run(_fetch())
            return result  # type: ignore[no-untyped-call]
    except Exception as exc:
        logger.debug("zone_config_resolution_failed", zone_id=zone_id, reason=str(exc))
        return None


def get_ha_client(zone_id: str | None = None) -> HAClient:
    """Get or create an HA client for a specific zone.

    If zone_id is None, returns the default zone's client.
    Falls back to environment variables if zone DB lookup fails.

    Thread-safe: Uses double-checked locking per zone.

    Args:
        zone_id: UUID of the zone, or None for the default.

    Returns:
        HAClient instance for the specified zone.
    """
    key = zone_id or _DEFAULT_KEY
    if key not in _clients:
        with _client_lock:
            if key not in _clients:
                # Try zone-specific config from DB first
                config = _resolve_zone_config(key)
                if config:
                    _clients[key] = HAClient(config=config)
                else:
                    # Fallback: resolve from env vars / system_config
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
