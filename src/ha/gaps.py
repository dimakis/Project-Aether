"""HA capability gap tracking.

Tracks known gaps in HA functionality and provides
a registry for reporting and prioritization.
"""

from typing import Any

# Registry of known HA capability gaps
MCP_GAPS: list[dict[str, Any]] = [
    {
        "tool": "list_devices",
        "priority": "P1",
        "impact": "No access to device registry - cannot get manufacturer, model, or firmware info",
        "workaround": "Infer device_id from entity attributes",
        "affects": ["Device model", "Entity grouping"],
        "data_model_impact": ["Device.manufacturer", "Device.model", "Device.sw_version"],
    },
    {
        "tool": "list_areas",
        "priority": "P1",
        "impact": "No access to area registry - cannot get floor associations or area icons",
        "workaround": "Extract unique area_id values from entities",
        "affects": ["Area model", "Floor hierarchy"],
        "data_model_impact": ["Area.floor_id", "Area.icon", "Floor entity"],
    },
    {
        "tool": "list_services",
        "priority": "P2",
        "impact": "Cannot dynamically discover available services",
        "workaround": "Seed common services from constants, expand during discovery",
        "affects": ["Service registry", "Agent action validation"],
        "data_model_impact": ["Service completeness"],
    },
    # get_script_config gap closed — implemented in src/ha/automations.py
    {
        "tool": "get_scene_config",
        "priority": "P2",
        "impact": "Cannot retrieve scene entity states",
        "workaround": "Store scene entity with null entity_states",
        "affects": ["Scene analysis", "Scene recommendations"],
        "data_model_impact": ["Scene.entity_states"],
    },
    {
        "tool": "list_floors",
        "priority": "P3",
        "impact": "Cannot access floor hierarchy",
        "workaround": "None - skip Floor entity for MVP",
        "affects": ["Building hierarchy", "Spatial organization"],
        "data_model_impact": ["Floor entity skipped"],
    },
    {
        "tool": "list_labels",
        "priority": "P3",
        "impact": "Cannot access custom entity labels/tags",
        "workaround": "None - skip Label entity for MVP",
        "affects": ["Entity tagging", "Custom grouping"],
        "data_model_impact": ["Entity.labels nullable"],
    },
    {
        "tool": "list_categories",
        "priority": "P3",
        "impact": "Cannot access entity categories",
        "workaround": "None - skip Category entity for MVP",
        "affects": ["Entity organization"],
        "data_model_impact": ["Category entity skipped"],
    },
    {
        "tool": "list_config_entries",
        "priority": "P3",
        "impact": "Cannot access integration configurations",
        "workaround": "None - skip ConfigEntry for MVP",
        "affects": ["Integration status", "Device sources"],
        "data_model_impact": ["ConfigEntry entity skipped"],
    },
    {
        "tool": "subscribe_events",
        "priority": "P3",
        "impact": "No real-time entity state updates",
        "workaround": "Periodic polling via list_entities",
        "affects": ["Live dashboards", "Real-time sync"],
        "data_model_impact": ["Event streaming unavailable"],
    },
    {
        "tool": "create_automation",
        "priority": "P2",
        "impact": "Cannot directly create automations in HA",
        "workaround": "Generate YAML for manual import or use automation.reload",
        "affects": ["Automation deployment"],
        "data_model_impact": ["AutomationProposal export mode"],
    },
    # lovelace/config read+write gap CLOSED — implemented via WebSocket API
    # in src/ha/websocket.py and src/ha/dashboards.py (get/save_dashboard_config).
    # Dashboard changes go through HITL proposals before deployment.
]


def get_all_gaps() -> list[dict[str, Any]]:
    """Get all known HA capability gaps.

    Returns:
        List of gap dictionaries
    """
    return MCP_GAPS


def get_gaps_by_priority(priority: str) -> list[dict[str, Any]]:
    """Get gaps filtered by priority.

    Args:
        priority: Priority level (P1, P2, P3)

    Returns:
        Filtered list of gaps
    """
    return [g for g in MCP_GAPS if g["priority"] == priority]


def get_gap_by_tool(tool: str) -> dict[str, Any] | None:
    """Get gap info for a specific tool.

    Args:
        tool: Tool name

    Returns:
        Gap dictionary or None
    """
    for gap in MCP_GAPS:
        if gap["tool"] == tool:
            return gap
    return None


def get_gaps_report() -> dict[str, Any]:
    """Generate a summary report of HA gaps.

    Returns:
        Report dictionary with counts and categorization
    """
    priority_counts: dict[str, int] = {}
    for gap in MCP_GAPS:
        p = gap["priority"]
        priority_counts[p] = priority_counts.get(p, 0) + 1

    return {
        "total_gaps": len(MCP_GAPS),
        "priority_counts": priority_counts,
        "high_priority_tools": [g["tool"] for g in MCP_GAPS if g["priority"] == "P1"],
        "medium_priority_tools": [g["tool"] for g in MCP_GAPS if g["priority"] == "P2"],
        "low_priority_tools": [g["tool"] for g in MCP_GAPS if g["priority"] == "P3"],
    }


def log_gap_encounter(
    tool: str,
    context: str | None = None,
) -> dict[str, Any] | None:
    """Log when a gap is encountered during operation.

    This can be used to track which gaps are actually being hit.

    Args:
        tool: Tool name that was needed
        context: Optional context about what was being attempted

    Returns:
        Gap info if found, None otherwise
    """
    gap = get_gap_by_tool(tool)
    if gap:
        # In a full implementation, this would log to MLflow or a database
        return {
            "gap": gap,
            "context": context,
            "workaround_applied": gap["workaround"],
        }
    return None


def get_gaps_affecting_entity(entity_type: str) -> list[dict[str, Any]]:
    """Get gaps that affect a specific entity type.

    Args:
        entity_type: Entity type name (e.g., "Device", "Area")

    Returns:
        List of gaps affecting that entity
    """
    result = []
    for gap in MCP_GAPS:
        for impact in gap.get("data_model_impact", []):
            if entity_type.lower() in impact.lower():
                result.append(gap)
                break
    return result


__all__ = [
    "MCP_GAPS",
    "get_all_gaps",
    "get_gap_by_tool",
    "get_gaps_affecting_entity",
    "get_gaps_by_priority",
    "get_gaps_report",
    "log_gap_encounter",
]
