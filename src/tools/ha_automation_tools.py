"""Automation management tools for Home Assistant."""

from __future__ import annotations

from typing import Any

import yaml
from langchain_core.tools import tool

from src.dal.automations import AutomationRepository
from src.ha import get_ha_client
from src.storage import get_session
from src.tracing import trace_with_uri


@tool("deploy_automation")
@trace_with_uri(name="ha.deploy_automation", span_type="TOOL")
async def deploy_automation(
    automation_id: str,
    alias: str,
    trigger: list[dict[str, Any]],
    action: list[dict[str, Any]],
    condition: list[dict[str, Any]] | None = None,
    description: str | None = None,
    mode: str = "single",
) -> str:
    """Deploy an automation directly to Home Assistant.

    Creates or updates an automation via HA's REST API.
    The automation becomes active immediately after creation.

    Args:
        automation_id: Unique ID for the automation (e.g., "motion_lights_kitchen")
        alias: Human-readable name shown in HA UI
        trigger: List of trigger configs (e.g., [{"platform": "state", "entity_id": "..."}])
        action: List of action configs (e.g., [{"service": "light.turn_on", "target": {...}}])
        condition: Optional list of conditions
        description: Optional description
        mode: Execution mode: single, restart, queued, parallel

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_automation(
            automation_id=automation_id,
            alias=alias,
            trigger=trigger,
            action=action,
            condition=condition,
            description=description,
            mode=mode,
        )

        if result.get("success"):
            entity_id = result.get("entity_id", f"automation.{automation_id}")
            return f"✅ Automation '{alias}' deployed successfully. Entity: {entity_id}"
        else:
            error = result.get("error", "Unknown error")
            return f"❌ Failed to deploy automation: {error}"

    except Exception as exc:
        return f"❌ Failed to deploy automation: {exc}"


@tool("delete_automation")
@trace_with_uri(name="ha.delete_automation", span_type="TOOL")
async def delete_automation(automation_id: str) -> str:
    """Delete an automation from Home Assistant.

    Args:
        automation_id: ID of the automation to delete

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.delete_automation(automation_id)
        if result.get("success"):
            return f"✅ Automation '{automation_id}' deleted."
        else:
            return f"❌ Failed to delete automation: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to delete automation: {exc}"


@tool("list_automations")
@trace_with_uri(name="ha.list_automations", span_type="TOOL")
async def list_automations() -> str:
    """List all automations in Home Assistant.

    Reads from the discovery database. Use get_automation_config to
    retrieve the full trigger/condition/action YAML for a specific
    automation.

    Returns:
        Formatted list of automations with their status
    """
    try:
        async with get_session() as session:
            repo = AutomationRepository(session)
            automations = await repo.list_all(limit=500)

        if not automations:
            return "No automations found."

        lines = []
        for auto in automations:
            status_emoji = "🟢" if auto.state == "on" else "🔴"
            config_tag = " [config ✓]" if auto.config else ""
            lines.append(
                f"{status_emoji} {auto.alias} ({auto.entity_id}) - {auto.state}{config_tag}"
            )

        return "\n".join(lines)
    except Exception as exc:
        return f"Failed to list automations: {exc}"


@tool("get_automation_config")
@trace_with_uri(name="ha.get_automation_config", span_type="TOOL")
async def get_automation_config(entity_id: str) -> str:
    """Get the full trigger/condition/action YAML for an automation.

    Reads the cached config from the discovery database. If the config
    is not yet available, advises running a discovery sync.

    Args:
        entity_id: Automation entity ID (e.g., 'automation.sunset_lights')

    Returns:
        YAML string of the automation config, or guidance message
    """
    async with get_session() as session:
        repo = AutomationRepository(session)
        auto = await repo.get_by_entity_id(entity_id)

    if auto is None:
        return f"Automation '{entity_id}' not found in discovery DB."

    if auto.config is None:
        return (
            f"Automation '{entity_id}' exists but its config hasn't been "
            "synced yet. Run a discovery sync to populate it."
        )

    return yaml.dump(auto.config, default_flow_style=False, sort_keys=False)
