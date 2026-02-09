"""Entity health diagnostics.

Identifies unavailable, stale, or problematic entities and
correlates issues to find common root causes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class EntityDiagnostic:
    """Diagnostic information for a single entity."""

    entity_id: str
    state: str
    available: bool
    last_changed: str | None
    integration: str
    issues: list[str] = field(default_factory=list)


_UNHEALTHY_STATES = {"unavailable", "unknown"}


def _entities_from_response(response: Any) -> list[dict]:
    """Normalize MCP list_entities response to a flat list."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict) and "results" in response:
        return response.get("results", [])
    return []


def _extract_integration(entity_id: str) -> str:
    """Extract domain/integration from entity_id.

    Args:
        entity_id: e.g., 'sensor.zha_temp'

    Returns:
        Domain string, e.g., 'sensor'
    """
    return entity_id.split(".", 1)[0] if "." in entity_id else "unknown"


async def find_unavailable_entities(ha: Any) -> list[EntityDiagnostic]:
    """Find all entities in 'unavailable' or 'unknown' state.

    Args:
        ha: HAClient instance

    Returns:
        List of EntityDiagnostic for unhealthy entities
    """
    raw = await ha.list_entities()
    entities = _entities_from_response(raw)

    diagnostics = []
    for entity in entities:
        state = str(entity.get("state", "")).lower()
        if state in _UNHEALTHY_STATES:
            diagnostics.append(
                EntityDiagnostic(
                    entity_id=entity.get("entity_id", "unknown"),
                    state=state,
                    available=False,
                    last_changed=entity.get("last_changed"),
                    integration=_extract_integration(entity.get("entity_id", "")),
                    issues=[f"Entity is {state}"],
                )
            )

    return diagnostics


async def find_stale_entities(
    ha: Any,
    hours: int = 24,
) -> list[EntityDiagnostic]:
    """Find entities that haven't been updated within the threshold.

    Args:
        ha: HAClient instance
        hours: Hours threshold -- entities not updated since are "stale"

    Returns:
        List of EntityDiagnostic for stale entities
    """
    raw = await ha.list_entities()
    entities = _entities_from_response(raw)

    now = datetime.now(UTC)
    diagnostics = []

    for entity in entities:
        last_changed_str = entity.get("last_changed", "")
        if not last_changed_str:
            continue

        try:
            last_changed = datetime.fromisoformat(last_changed_str.replace("Z", "+00:00"))
            delta_hours = (now - last_changed).total_seconds() / 3600

            if delta_hours > hours:
                diagnostics.append(
                    EntityDiagnostic(
                        entity_id=entity.get("entity_id", "unknown"),
                        state=entity.get("state", "unknown"),
                        available=entity.get("state", "").lower() not in _UNHEALTHY_STATES,
                        last_changed=last_changed_str,
                        integration=_extract_integration(entity.get("entity_id", "")),
                        issues=[f"Not updated for {delta_hours:.1f} hours"],
                    )
                )
        except (ValueError, TypeError):
            continue

    return diagnostics


def correlate_unavailability(
    diagnostics: list[EntityDiagnostic],
    common_cause_threshold: int = 3,
) -> list[dict]:
    """Group unavailable entities by integration to find common causes.

    If many entities from the same integration are unavailable,
    the integration itself is likely the root cause.

    Args:
        diagnostics: List of EntityDiagnostic (usually unavailable ones)
        common_cause_threshold: Number of entities that suggests a common cause

    Returns:
        List of correlation dicts with integration, count, entity_ids,
        and likely_common_cause flag.
    """
    if not diagnostics:
        return []

    # Group by integration
    groups: dict[str, list[str]] = {}
    for diag in diagnostics:
        groups.setdefault(diag.integration, []).append(diag.entity_id)

    correlations = []
    for integration, entity_ids in sorted(groups.items(), key=lambda x: -len(x[1])):
        correlations.append(
            {
                "integration": integration,
                "count": len(entity_ids),
                "entity_ids": entity_ids,
                "likely_common_cause": len(entity_ids) >= common_cause_threshold,
            }
        )

    return correlations
