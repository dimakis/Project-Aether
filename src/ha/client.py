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
    _trace_ha_call,
)
from src.ha.diagnostics import DiagnosticMixin
from src.ha.entities import EntityMixin

# Re-export for backward compatibility
__all__ = ["HAClient", "HAClientConfig", "HAClientError", "get_ha_client", "reset_ha_client"]


class HAClient(BaseHAClient, EntityMixin, AutomationMixin, DiagnosticMixin):
    """Client for invoking hass-ha tools.

    This class provides a typed interface to the HA tools.
    In the Cursor environment, these tools are available directly.
    In production, this would connect to the HA server.

    All public methods are traced via MLflow for observability.

    Usage:
        client = HAClient()
        overview = await client.system_overview()
        entities = await client.list_entities(domain="light")
    """

    pass


# Singleton client (thread-safe via double-checked locking, T186)
_client: HAClient | None = None
_client_lock = __import__("threading").Lock()


def get_ha_client() -> HAClient:
    """Get or create the HA client singleton.

    Thread-safe: Uses double-checked locking to prevent concurrent
    client creation in multi-threaded environments.

    Returns:
        HAClient instance
    """
    global _client  # noqa: PLW0603
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = HAClient()
    return _client


def reset_ha_client() -> None:
    """Reset the HA client singleton.

    Called after first-time setup stores HA config in DB, so the
    HA client re-initializes with the new connection details on
    next access.

    Thread-safe: Acquires lock before modifying singleton.
    """
    global _client  # noqa: PLW0603
    with _client_lock:
        _client = None
