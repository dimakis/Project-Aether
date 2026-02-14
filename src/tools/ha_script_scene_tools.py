"""Script and scene creation tools for Home Assistant."""

from __future__ import annotations

from typing import Any

import yaml
from langchain_core.tools import tool

from src.dal.automations import ScriptRepository
from src.ha import get_ha_client
from src.storage import get_session
from src.tracing import trace_with_uri


@tool("get_script_config")
@trace_with_uri(name="ha.get_script_config", span_type="TOOL")
async def get_script_config(entity_id: str) -> str:
    """Get the full sequence/fields YAML for a script.

    Reads the cached config from the discovery database. If the config
    is not yet available, advises running a discovery sync.

    Args:
        entity_id: Script entity ID (e.g., 'script.movie_mode')

    Returns:
        YAML string of the script config, or guidance message
    """
    async with get_session() as session:
        repo = ScriptRepository(session)
        script = await repo.get_by_entity_id(entity_id)

    if script is None:
        return f"Script '{entity_id}' not found in discovery DB."

    if script.sequence is None:
        return (
            f"Script '{entity_id}' exists but its sequence hasn't been "
            "synced yet. Run a discovery sync to populate it."
        )

    config_data: dict[str, Any] = {
        "alias": script.alias,
        "sequence": script.sequence,
    }
    if script.fields:
        config_data["fields"] = script.fields

    return yaml.dump(config_data, default_flow_style=False, sort_keys=False)


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
    ha = get_ha_client()
    try:
        result = await ha.create_script(
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
    ha = get_ha_client()
    try:
        result = await ha.create_scene(
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
