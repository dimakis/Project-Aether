"""Dashboard tools for the Dashboard Designer agent.

Provides LangChain-compatible tools for generating, validating,
and managing Lovelace dashboard configurations.
"""

from __future__ import annotations

import yaml
from langchain_core.tools import tool

from src.ha import get_ha_client
from src.tracing import trace_with_uri


@tool("generate_dashboard_yaml")
@trace_with_uri(name="dashboard.generate_yaml", span_type="TOOL")
async def generate_dashboard_yaml(title: str, areas: list[str] | None = None) -> str:
    """Generate a Lovelace dashboard YAML config for the given areas.

    Args:
        title: Dashboard title.
        areas: Optional list of HA area IDs to include.
               If omitted, generates a generic overview.

    Returns:
        A Lovelace YAML configuration string.
    """
    ha = get_ha_client()

    views: list[dict] = []

    if areas:
        # Fetch all entities once, then filter by area in memory
        try:
            all_entities = await ha.list_entities()
        except Exception:
            all_entities = []

        for area_id in areas:
            entities = [
                e
                for e in all_entities
                if e.get("area_id") == area_id or e.get("attributes", {}).get("area_id") == area_id
            ]

            cards: list[dict] = []
            entity_ids = [e["entity_id"] for e in entities]

            if entity_ids:
                cards.append(
                    {
                        "type": "entities",
                        "title": f"{area_id.replace('_', ' ').title()} Entities",
                        "entities": entity_ids,
                    }
                )

            views.append(
                {
                    "title": area_id.replace("_", " ").title(),
                    "cards": cards
                    if cards
                    else [{"type": "markdown", "content": "No entities found."}],
                }
            )
    else:
        # Default overview view
        views.append(
            {
                "title": "Overview",
                "cards": [
                    {
                        "type": "markdown",
                        "content": f"# {title}\n\nAdd areas and entities to populate this dashboard.",
                    }
                ],
            }
        )

    dashboard_config = {
        "title": title,
        "views": views,
    }

    return yaml.dump(dashboard_config, default_flow_style=False, sort_keys=False)


@tool("validate_dashboard_yaml")
@trace_with_uri(name="dashboard.validate_yaml", span_type="TOOL")
async def validate_dashboard_yaml(yaml_content: str) -> str:
    """Validate a Lovelace YAML configuration string.

    Uses the schema validator (Feature 26) for structural validation.

    Args:
        yaml_content: The YAML string to validate.

    Returns:
        A validation result string (success or error details).
    """
    from src.schema import validate_yaml

    result = validate_yaml(yaml_content, "ha.dashboard")

    if result.valid:
        return "Valid: Lovelace YAML structure looks correct."

    issues = [f"{e.path}: {e.message}" if e.path else e.message for e in result.errors]
    return "Validation issues:\n" + "\n".join(f"- {i}" for i in issues)


@tool("list_dashboards")
@trace_with_uri(name="dashboard.list", span_type="TOOL")
async def list_dashboards() -> str:
    """List all Lovelace dashboards configured in Home Assistant.

    Returns:
        A formatted string with dashboard IDs, titles, and modes.
    """
    ha = get_ha_client()
    try:
        dashboards = await ha._request("GET", "/api/lovelace/dashboards")
    except Exception as exc:
        return f"Failed to list dashboards: {exc}"

    if not dashboards or not isinstance(dashboards, list):
        return "No dashboards found or API not available."

    lines: list[str] = ["Dashboards in Home Assistant:", ""]
    for db in dashboards:
        db_id = db.get("id", "unknown")
        db_title = db.get("title", "Untitled")
        db_mode = db.get("mode", "unknown")
        lines.append(f"- **{db_title}** (id: `{db_id}`, mode: {db_mode})")

    return "\n".join(lines)


def get_dashboard_tools() -> list:
    """Return all dashboard tools for agent registration."""
    return [
        generate_dashboard_yaml,
        validate_dashboard_yaml,
        list_dashboards,
    ]
