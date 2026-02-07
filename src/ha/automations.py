"""Automation, script, scene, and input helper management.

Provides methods for creating, managing, and deleting automations,
scripts, scenes, and input helpers.
"""

from typing import Any

from src.ha.base import HAClientError, _trace_ha_call
from src.tracing import log_param


class AutomationMixin:
    """Mixin providing automation, script, scene, and input helper operations."""

    @_trace_ha_call("ha.list_automations")
    async def list_automations(self) -> list[dict[str, Any]]:
        """List all automations.

        Returns:
            List of automation dictionaries
        """
        entities = await self.list_entities(domain="automation", detailed=True)

        automations = []
        for entity in entities:
            attrs = entity.get("attributes", {})
            automations.append(
                {
                    "id": attrs.get("id", entity["entity_id"]),
                    "entity_id": entity["entity_id"],
                    "state": entity["state"],
                    "alias": attrs.get("friendly_name", entity["name"]),
                    "last_triggered": attrs.get("last_triggered"),
                    "mode": attrs.get("mode", "single"),
                }
            )

        return automations

    @_trace_ha_call("ha.create_automation")
    async def create_automation(
        self,
        automation_id: str,
        alias: str,
        trigger: list[dict[str, Any]],
        action: list[dict[str, Any]],
        condition: list[dict[str, Any]] | None = None,
        description: str | None = None,
        mode: str = "single",
    ) -> dict[str, Any]:
        """Create or update an automation via HA REST API.

        This bypasses the HA gap by using HA's config API directly.

        Args:
            automation_id: Unique automation ID (e.g., "aether_motion_lights")
            alias: Human-readable name
            trigger: List of trigger configurations
            action: List of action configurations
            condition: Optional list of conditions
            description: Optional description
            mode: Execution mode (single, restart, queued, parallel)

        Returns:
            Result dict with success status
        """
        log_param("ha.create_automation.id", automation_id)
        log_param("ha.create_automation.alias", alias)

        # Build automation config
        config: dict[str, Any] = {
            "id": automation_id,
            "alias": alias,
            "trigger": trigger,
            "action": action,
            "mode": mode,
        }

        if description:
            config["description"] = description
        if condition:
            config["condition"] = condition

        try:
            # POST to config API creates or updates the automation
            result = await self._request(
                "POST",
                f"/api/config/automation/config/{automation_id}",
                json=config,
            )

            return {
                "success": True,
                "automation_id": automation_id,
                "entity_id": f"automation.{automation_id}",
                "method": "rest_api",
                "config": config,
            }
        except HAClientError as e:
            return {
                "success": False,
                "automation_id": automation_id,
                "error": str(e),
                "method": "rest_api",
            }

    @_trace_ha_call("ha.get_automation_config")
    async def get_automation_config(
        self,
        automation_id: str,
    ) -> dict[str, Any] | None:
        """Get an automation's configuration.

        Args:
            automation_id: Automation ID

        Returns:
            Automation config or None if not found
        """
        return await self._request(
            "GET",
            f"/api/config/automation/config/{automation_id}",
        )

    @_trace_ha_call("ha.delete_automation")
    async def delete_automation(
        self,
        automation_id: str,
    ) -> dict[str, Any]:
        """Delete an automation.

        Args:
            automation_id: Automation ID to delete

        Returns:
            Result dict
        """
        log_param("ha.delete_automation.id", automation_id)

        try:
            await self._request(
                "DELETE",
                f"/api/config/automation/config/{automation_id}",
            )
            return {"success": True, "automation_id": automation_id}
        except HAClientError as e:
            return {"success": False, "automation_id": automation_id, "error": str(e)}

    @_trace_ha_call("ha.list_automation_configs")
    async def list_automation_configs(self) -> list[dict[str, Any]]:
        """List all automation configurations.

        Returns:
            List of automation config dicts
        """
        result = await self._request("GET", "/api/config/automation/config")
        return result if result else []

    @_trace_ha_call("ha.create_script")
    async def create_script(
        self,
        script_id: str,
        alias: str,
        sequence: list[dict[str, Any]],
        description: str | None = None,
        mode: str = "single",
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a script via REST API.

        Scripts are reusable action sequences that can be called from
        automations or manually.

        Args:
            script_id: Unique script ID
            alias: Human-readable name
            sequence: List of action configurations
            description: Optional description
            mode: Execution mode (single, restart, queued, parallel)
            icon: Optional MDI icon (e.g., "mdi:lightbulb")

        Returns:
            Result dict with success status
        """
        log_param("ha.create_script.id", script_id)

        config: dict[str, Any] = {
            "alias": alias,
            "sequence": sequence,
            "mode": mode,
        }

        if description:
            config["description"] = description
        if icon:
            config["icon"] = icon

        try:
            await self._request(
                "POST",
                f"/api/config/script/config/{script_id}",
                json=config,
            )
            return {
                "success": True,
                "script_id": script_id,
                "entity_id": f"script.{script_id}",
            }
        except HAClientError as e:
            return {"success": False, "script_id": script_id, "error": str(e)}

    @_trace_ha_call("ha.delete_script")
    async def delete_script(self, script_id: str) -> dict[str, Any]:
        """Delete a script."""
        try:
            await self._request("DELETE", f"/api/config/script/config/{script_id}")
            return {"success": True, "script_id": script_id}
        except HAClientError as e:
            return {"success": False, "script_id": script_id, "error": str(e)}

    @_trace_ha_call("ha.create_scene")
    async def create_scene(
        self,
        scene_id: str,
        name: str,
        entities: dict[str, dict[str, Any]],
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a scene via REST API.

        Scenes capture a snapshot of entity states that can be activated later.

        Args:
            scene_id: Unique scene ID
            name: Human-readable name
            entities: Dict of entity_id -> state/attributes to set
            icon: Optional MDI icon

        Returns:
            Result dict
        """
        log_param("ha.create_scene.id", scene_id)

        config: dict[str, Any] = {
            "id": scene_id,
            "name": name,
            "entities": entities,
        }

        if icon:
            config["icon"] = icon

        try:
            await self._request(
                "POST",
                f"/api/config/scene/config/{scene_id}",
                json=config,
            )
            return {
                "success": True,
                "scene_id": scene_id,
                "entity_id": f"scene.{scene_id}",
            }
        except HAClientError as e:
            return {"success": False, "scene_id": scene_id, "error": str(e)}

    @_trace_ha_call("ha.delete_scene")
    async def delete_scene(self, scene_id: str) -> dict[str, Any]:
        """Delete a scene."""
        try:
            await self._request("DELETE", f"/api/config/scene/config/{scene_id}")
            return {"success": True, "scene_id": scene_id}
        except HAClientError as e:
            return {"success": False, "scene_id": scene_id, "error": str(e)}

    @_trace_ha_call("ha.create_input_boolean")
    async def create_input_boolean(
        self,
        input_id: str,
        name: str,
        initial: bool = False,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create an input_boolean helper.

        Useful for creating virtual switches the agent can toggle.

        Args:
            input_id: Unique ID
            name: Display name
            initial: Initial state
            icon: Optional MDI icon

        Returns:
            Result dict
        """
        config: dict[str, Any] = {"name": name, "initial": initial}
        if icon:
            config["icon"] = icon

        try:
            await self._request(
                "POST",
                f"/api/config/input_boolean/config/{input_id}",
                json=config,
            )
            return {
                "success": True,
                "input_id": input_id,
                "entity_id": f"input_boolean.{input_id}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.create_input_number")
    async def create_input_number(
        self,
        input_id: str,
        name: str,
        min_value: float,
        max_value: float,
        initial: float | None = None,
        step: float = 1.0,
        unit_of_measurement: str | None = None,
        mode: str = "slider",
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create an input_number helper.

        Useful for creating configurable thresholds the agent can adjust.

        Args:
            input_id: Unique ID
            name: Display name
            min_value: Minimum value
            max_value: Maximum value
            initial: Initial value
            step: Step increment
            unit_of_measurement: Unit label
            mode: "slider" or "box"
            icon: Optional MDI icon

        Returns:
            Result dict
        """
        config: dict[str, Any] = {
            "name": name,
            "min": min_value,
            "max": max_value,
            "step": step,
            "mode": mode,
        }
        if initial is not None:
            config["initial"] = initial
        if unit_of_measurement:
            config["unit_of_measurement"] = unit_of_measurement
        if icon:
            config["icon"] = icon

        try:
            await self._request(
                "POST",
                f"/api/config/input_number/config/{input_id}",
                json=config,
            )
            return {
                "success": True,
                "input_id": input_id,
                "entity_id": f"input_number.{input_id}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}
