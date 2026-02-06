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
    mcp = get_mcp_client()
    try:
        result = await mcp.create_automation(
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
    mcp = get_mcp_client()
    try:
        result = await mcp.delete_automation(automation_id)
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

    Returns:
        Formatted list of automations with their status
    """
    mcp = get_mcp_client()
    try:
        automations = await mcp.list_automations()
        if not automations:
            return "No automations found."

        lines = []
        for auto in automations:
            state = auto.get("state", "unknown")
            alias = auto.get("alias", auto.get("entity_id", "unnamed"))
            entity_id = auto.get("entity_id", "")
            status_emoji = "🟢" if state == "on" else "🔴"
            lines.append(f"{status_emoji} {alias} ({entity_id}) - {state}")

        return "\n".join(lines)
    except Exception as exc:
        return f"Failed to list automations: {exc}"


@tool("create_script")
@trace_with_uri(name="ha.create_script", span_type="TOOL")
async def create_script(
    script_id: str,
    alias: str,
    sequence: list[dict[str, Any]],
    description: str | None = None,
    mode: str = "single",
) -> str:
    """Create a reusable script in Home Assistant.

    Scripts are sequences of actions that can be called from automations
    or executed manually.

    Args:
        script_id: Unique ID (e.g., "morning_routine")
        alias: Human-readable name
        sequence: List of actions (e.g., [{"service": "light.turn_on", ...}])
        description: Optional description
        mode: Execution mode: single, restart, queued, parallel

    Returns:
        Success or error message
    """
    mcp = get_mcp_client()
    try:
        result = await mcp.create_script(
            script_id=script_id,
            alias=alias,
            sequence=sequence,
            description=description,
            mode=mode,
        )

        if result.get("success"):
            return f"✅ Script '{alias}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create script: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create script: {exc}"


@tool("create_scene")
@trace_with_uri(name="ha.create_scene", span_type="TOOL")
async def create_scene(
    scene_id: str,
    name: str,
    entities: dict[str, dict[str, Any]],
) -> str:
    """Create a scene that captures entity states.

    Scenes save a snapshot of entity states that can be activated later.
    Useful for "movie mode", "bedtime", etc.

    Args:
        scene_id: Unique ID (e.g., "movie_mode")
        name: Human-readable name
        entities: Dict of entity states, e.g.:
            {
                "light.living_room": {"state": "on", "brightness": 50},
                "light.kitchen": {"state": "off"}
            }

    Returns:
        Success or error message
    """
    mcp = get_mcp_client()
    try:
        result = await mcp.create_scene(
            scene_id=scene_id,
            name=name,
            entities=entities,
        )

        if result.get("success"):
            return f"✅ Scene '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create scene: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create scene: {exc}"


@tool("create_input_boolean")
@trace_with_uri(name="ha.create_input_boolean", span_type="TOOL")
async def create_input_boolean(
    input_id: str,
    name: str,
    initial: bool = False,
) -> str:
    """Create a virtual on/off switch (input_boolean).

    Useful for creating mode toggles like "guest_mode", "vacation_mode".
    The agent can then use these in automations.

    Args:
        input_id: Unique ID (e.g., "vacation_mode")
        name: Display name
        initial: Initial state (on/off)

    Returns:
        Success or error message
    """
    mcp = get_mcp_client()
    try:
        result = await mcp.create_input_boolean(
            input_id=input_id,
            name=name,
            initial=initial,
        )

        if result.get("success"):
            return f"✅ Input boolean '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create input_boolean: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create input_boolean: {exc}"


@tool("create_input_number")
@trace_with_uri(name="ha.create_input_number", span_type="TOOL")
async def create_input_number(
    input_id: str,
    name: str,
    min_value: float,
    max_value: float,
    initial: float | None = None,
    step: float = 1.0,
    unit_of_measurement: str | None = None,
) -> str:
    """Create a configurable number input (input_number).

    Useful for thresholds like "motion_timeout_minutes", "brightness_level".
    The agent can create and adjust these values.

    Args:
        input_id: Unique ID (e.g., "motion_timeout")
        name: Display name
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        initial: Starting value
        step: Increment step
        unit_of_measurement: Unit label (e.g., "minutes", "%")

    Returns:
        Success or error message
    """
    mcp = get_mcp_client()
    try:
        result = await mcp.create_input_number(
            input_id=input_id,
            name=name,
            min_value=min_value,
            max_value=max_value,
            initial=initial,
            step=step,
            unit_of_measurement=unit_of_measurement,
        )

        if result.get("success"):
            return f"✅ Input number '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create input_number: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create input_number: {exc}"


@tool("fire_event")
@trace_with_uri(name="ha.fire_event", span_type="TOOL")
async def fire_event(
    event_type: str,
    event_data: dict[str, Any] | None = None,
) -> str:
    """Fire a custom event in Home Assistant.

    Events can trigger automations. Useful for signaling state changes
    or coordinating between automations.

    Args:
        event_type: Event name (e.g., "aether_analysis_complete")
        event_data: Optional data to include with the event

    Returns:
        Success or error message
    """
    mcp = get_mcp_client()
    try:
        result = await mcp.fire_event(event_type, event_data)

        if result.get("success"):
            return f"✅ Event '{event_type}' fired."
        else:
            return f"❌ Failed to fire event: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to fire event: {exc}"


@tool("render_template")
@trace_with_uri(name="ha.render_template", span_type="TOOL")
async def render_template(template: str) -> str:
    """Render a Jinja2 template using Home Assistant's engine.

    Useful for complex calculations involving entity states.

    Args:
        template: Jinja2 template, e.g.:
            "{{ states('sensor.temperature') | float + 5 }}"
            "{{ state_attr('light.living_room', 'brightness') }}"

    Returns:
        Rendered result or error message
    """
    mcp = get_mcp_client()
    try:
        result = await mcp.render_template(template)
        if result is not None:
            return f"Result: {result}"
        else:
            return "❌ Failed to render template"
    except Exception as exc:
        return f"❌ Failed to render template: {exc}"


@tool("get_ha_logs")
@trace_with_uri(name="ha.get_ha_logs", span_type="TOOL")
async def get_ha_logs() -> str:
    """Get the Home Assistant error log for diagnostics.

    Use this when troubleshooting issues like:
    - Missing sensor data or entity unavailability
    - Integration errors or connection failures
    - Automation failures or unexpected behavior
    - Device disconnections

    Returns:
        Recent error/warning log entries (truncated to ~4000 chars)
    """
    mcp = get_mcp_client()
    try:
        log_text = await mcp.get_error_log()
        if not log_text:
            return "No errors found in the Home Assistant log."

        # Truncate for LLM context window
        if len(log_text) > 4000:
            log_text = log_text[-4000:]
            return f"**HA Error Log** (last ~4000 chars):\n\n{log_text}"

        return f"**HA Error Log**:\n\n{log_text}"
    except Exception as exc:
        return f"Failed to retrieve HA logs: {exc}"


@tool("check_ha_config")
@trace_with_uri(name="ha.check_ha_config", span_type="TOOL")
async def check_ha_config() -> str:
    """Check Home Assistant configuration validity.

    Use this when diagnosing:
    - Configuration errors after changes
    - Integration setup problems
    - YAML syntax issues

    Returns:
        Configuration check result with any errors or warnings
    """
    mcp = get_mcp_client()
    try:
        result = await mcp.check_config()
        status = result.get("result", "unknown")

        if status == "valid":
            return "HA configuration is valid. No errors found."

        errors = result.get("errors", "")
        return f"HA configuration check result: {status}\n\nDetails:\n{errors}"
    except Exception as exc:
        return f"Failed to check HA config: {exc}"


def get_ha_tools() -> list[Any]:
    """Return all Home Assistant tools."""
    return [
        # Entity queries
        get_entity_state,
        list_entities_by_domain,
        search_entities,
        get_domain_summary,
        # Entity control
        control_entity,
        # Automations
        deploy_automation,
        delete_automation,
        list_automations,
        # Scripts & Scenes
        create_script,
        create_scene,
        # Input helpers
        create_input_boolean,
        create_input_number,
        # Events & Templates
        fire_event,
        render_template,
        # Diagnostics
        get_ha_logs,
        check_ha_config,
    ]


__all__ = [
    "get_entity_state",
    "list_entities_by_domain",
    "search_entities",
    "get_domain_summary",
    "control_entity",
    "deploy_automation",
    "delete_automation",
    "list_automations",
    "create_script",
    "create_scene",
    "create_input_boolean",
    "create_input_number",
    "fire_event",
    "render_template",
    "get_ha_logs",
    "check_ha_config",
    "get_ha_tools",
]
