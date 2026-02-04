"""Home Assistant tools for agents.

Provides LangChain-compatible tools that wrap MCP client calls
for common Home Assistant interactions.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.mcp import get_mcp_client
from src.tracing import trace_with_uri


def _extract_results(payload: Any) -> list[dict[str, Any]]:
    """Normalize MCP response payload to a list of entities."""
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
    mcp = get_mcp_client()
    entity = await mcp.get_entity(entity_id)
    if not entity:
        return f"Entity '{entity_id}' not found."

    state = entity.get("state", "unknown")
    attrs = entity.get("attributes") or {}
    friendly_name = attrs.get("friendly_name", entity_id)

    return f"{entity_id} ({friendly_name}) is {state}."


@tool("list_entities_by_domain")
@trace_with_uri(name="ha.list_entities_by_domain", span_type="TOOL")
async def list_entities_by_domain(domain: str, state_filter: str | None = None) -> str:
    """List entities for a given domain, optionally filtered by state."""
    mcp = get_mcp_client()
    payload = await mcp.list_entities(domain=domain)
    entities = _extract_results(payload)

    if state_filter:
        entities = [
            e for e in entities if str(e.get("state", "")).lower() == state_filter.lower()
        ]

    if not entities:
        return f"No entities found for domain '{domain}'."

    lines = [e.get("entity_id", "unknown") for e in entities]
    return "\n".join(lines)


@tool("search_entities")
@trace_with_uri(name="ha.search_entities", span_type="TOOL")
async def search_entities(query: str) -> str:
    """Search entities by name or ID."""
    mcp = get_mcp_client()

    if hasattr(mcp, "search_entities"):
        payload = await mcp.search_entities(query=query)
        entities = _extract_results(payload)
    else:
        payload = await mcp.list_entities(search_query=query)
        entities = _extract_results(payload)

    if not entities:
        return f"No entities found for query '{query}'."

    lines = [e.get("entity_id", "unknown") for e in entities]
    return "\n".join(lines)


@tool("get_domain_summary")
@trace_with_uri(name="ha.get_domain_summary", span_type="TOOL")
async def get_domain_summary(domain: str) -> str:
    """Get a summary of entity counts and states for a domain."""
    mcp = get_mcp_client()
    summary = await mcp.domain_summary(domain=domain)
    if not summary:
        return f"No summary available for domain '{domain}'."

    total = summary.get("total_count", 0)
    states = summary.get("state_distribution", {})
    return f"Domain '{domain}' has {total} entities. States: {states}"


@tool("control_entity")
@trace_with_uri(name="ha.control_entity", span_type="TOOL")
async def control_entity(entity_id: str, action: str) -> str:
    """Control an entity (on/off/toggle)."""
    mcp = get_mcp_client()
    try:
        await mcp.entity_action(entity_id=entity_id, action=action)
    except Exception as exc:  # pragma: no cover - defensive
        return f"Failed to control {entity_id}: {exc}"

    return f"Action '{action}' sent to {entity_id}."


def get_ha_tools() -> list[Any]:
    """Return all Home Assistant tools."""
    return [
        get_entity_state,
        list_entities_by_domain,
        search_entities,
        get_domain_summary,
        control_entity,
    ]


__all__ = [
    "get_entity_state",
    "list_entities_by_domain",
    "search_entities",
    "get_domain_summary",
    "control_entity",
    "get_ha_tools",
]
