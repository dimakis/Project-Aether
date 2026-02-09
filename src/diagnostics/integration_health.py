"""Integration health diagnostics.

Monitors Home Assistant integration statuses, identifies unhealthy
integrations, and provides detailed diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_HEALTHY_STATES = {"loaded"}


@dataclass
class IntegrationHealth:
    """Health status for a single integration config entry."""

    entry_id: str
    domain: str
    title: str
    state: str
    reason: str | None = None
    disabled_by: str | None = None


async def get_integration_statuses(ha: Any) -> list[IntegrationHealth]:
    """Get health status for all integrations.

    Args:
        ha: HAClient instance

    Returns:
        List of IntegrationHealth for all config entries
    """
    entries = await ha.list_config_entries()
    if not entries:
        return []

    return [
        IntegrationHealth(
            entry_id=entry.get("entry_id", ""),
            domain=entry.get("domain", "unknown"),
            title=entry.get("title", ""),
            state=entry.get("state", "unknown"),
            reason=entry.get("reason"),
            disabled_by=entry.get("disabled_by"),
        )
        for entry in entries
    ]


async def find_unhealthy_integrations(ha: Any) -> list[IntegrationHealth]:
    """Find integrations that are not in a healthy state.

    Healthy = 'loaded'. Everything else (setup_error, not_loaded,
    failed_unload, etc.) is considered unhealthy.

    Args:
        ha: HAClient instance

    Returns:
        List of IntegrationHealth for unhealthy integrations
    """
    statuses = await get_integration_statuses(ha)
    return [s for s in statuses if s.state not in _HEALTHY_STATES]


async def diagnose_integration(
    ha: Any,
    entry_id: str,
) -> dict[str, Any] | None:
    """Run a full diagnosis on a specific integration.

    Combines config entry info, diagnostics data (if supported),
    and entity health into a comprehensive report.

    Args:
        ha: HAClient instance
        entry_id: The config entry ID to diagnose

    Returns:
        Diagnosis dict, or None if entry not found
    """
    # Find the config entry
    entries = await ha.list_config_entries()
    entry = next((e for e in entries if e.get("entry_id") == entry_id), None)

    if entry is None:
        return None

    domain = entry.get("domain", "unknown")

    # Get integration-specific diagnostics (may be None)
    diagnostics = await ha.get_config_entry_diagnostics(entry_id)

    # Find unavailable entities for this integration's domain
    from src.diagnostics.entity_health import (
        _UNHEALTHY_STATES,
        _entities_from_response,
    )

    all_entities = await ha.list_entities()
    entities = _entities_from_response(all_entities)
    unavailable = [
        e.get("entity_id")
        for e in entities
        if (
            e.get("entity_id", "").startswith(f"{domain}.")
            or (
                e.get("entity_id", "").split(".", 1)[0]
                in ("sensor", "binary_sensor", "switch", "light")
                and domain in e.get("entity_id", "")
            )
        )
        and str(e.get("state", "")).lower() in _UNHEALTHY_STATES
    ]

    return {
        "entry_id": entry_id,
        "domain": domain,
        "title": entry.get("title", ""),
        "state": entry.get("state", "unknown"),
        "reason": entry.get("reason"),
        "disabled_by": entry.get("disabled_by"),
        "diagnostics": diagnostics,
        "unavailable_entities": unavailable,
    }
