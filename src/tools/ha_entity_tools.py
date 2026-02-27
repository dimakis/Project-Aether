"""Entity query and control tools for Home Assistant.

Listing/search/summary tools read from the discovery database for speed;
get_entity_state stays live for real-time state. control_entity calls HA directly.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.dal.entities import EntityRepository
from src.ha import get_ha_client
from src.storage import get_session
from src.tracing import trace_with_uri


def _extract_results(payload: Any) -> list[dict[str, Any]]:
    """Normalize HA response payload to a list of entities."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "results" in payload:
        results = payload.get("results")
        return results if isinstance(results, list) else []
    return []


@tool("get_entity_state")
@trace_with_uri(name="ha.get_entity_state", span_type="TOOL")
async def get_entity_state(entity_id: str) -> str:
    """Get the current state and key attributes for an entity."""
    ha = get_ha_client()
    entity = await ha.get_entity(entity_id)
    if not entity:
        return f"Entity '{entity_id}' not found."

    state = entity.get("state", "unknown")
    attrs = entity.get("attributes") or {}
    friendly_name = attrs.get("friendly_name", entity_id)

    return f"{entity_id} ({friendly_name}) is {state}."


@tool("list_entities_by_domain")
@trace_with_uri(name="ha.list_entities_by_domain", span_type="TOOL")
async def list_entities_by_domain(domain: str, state_filter: str | None = None) -> str:
    """List entities in a domain, optionally filtered by state.

    Args:
        domain: HA domain (e.g. "light", "sensor")
        state_filter: Filter by state value
    """
    async with get_session() as session:
        repo = EntityRepository(session)
        entities = await repo.list_by_domain(domain)

    if state_filter:
        entities = [e for e in entities if str(e.state or "").lower() == state_filter.lower()]

    if not entities:
        return f"No entities found for domain '{domain}'."

    lines = [e.entity_id for e in entities]
    return "\n".join(lines)


@tool("search_entities")
@trace_with_uri(name="ha.search_entities", span_type="TOOL")
async def search_entities(query: str) -> str:
    """Search entities by name or ID.

    Args:
        query: Search term
    """
    async with get_session() as session:
        repo = EntityRepository(session)
        entities = await repo.search(query)

    if not entities:
        return f"No entities found for query '{query}'."

    lines = [e.entity_id for e in entities]
    return "\n".join(lines)


@tool("get_domain_summary")
@trace_with_uri(name="ha.get_domain_summary", span_type="TOOL")
async def get_domain_summary(domain: str) -> str:
    """Get entity counts and state distribution for a domain.

    Args:
        domain: HA domain
    """
    async with get_session() as session:
        repo = EntityRepository(session)
        state_counts = await repo.get_state_distribution(domain)
        if not state_counts:
            return f"No entities found for domain '{domain}'."

        total = sum(state_counts.values())
    return f"Domain '{domain}' has {total} entities. States: {state_counts}"


@tool("control_entity")
@trace_with_uri(name="ha.control_entity", span_type="TOOL")
async def control_entity(entity_id: str, action: str) -> str:
    """Control an entity (on/off/toggle)."""
    ha = get_ha_client()
    try:
        await ha.entity_action(entity_id=entity_id, action=action)
    except Exception as exc:  # pragma: no cover - defensive
        return f"Failed to control {entity_id}: {exc}"

    return f"Action '{action}' sent to {entity_id}."
