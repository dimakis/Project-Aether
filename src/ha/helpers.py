"""Input helper management for Home Assistant.

Provides methods for creating, listing, and deleting HA input helpers
(input_boolean, input_number, input_text, input_select, input_datetime,
input_button, counter, timer).

Uses the HA WebSocket API ({domain}/create, {domain}/delete, {domain}/list)
which is the same transport HA's own frontend uses.  The REST config storage
endpoints (/api/config/{domain}/config/{id}) silently return 404 for helpers
and should not be used.
"""

from typing import Any

from src.exceptions import HAClientError
from src.ha.base import _trace_ha_call
from src.ha.websocket import ws_command

HELPER_DOMAINS = frozenset(
    {
        "input_boolean",
        "input_number",
        "input_text",
        "input_select",
        "input_datetime",
        "input_button",
        "counter",
        "timer",
    }
)


class HelperMixin:
    """Mixin providing input helper operations via HA WebSocket API."""

    async def _ws(self, command_type: str, **params: Any) -> Any:
        """Send a WebSocket command to HA.

        Convenience wrapper that pulls ws_url and token from BaseHAClient.
        """
        return await ws_command(
            self._get_ws_url(),  # type: ignore[attr-defined]
            self.config.ha_token,  # type: ignore[attr-defined]
            command_type,
            **params,
        )

    @_trace_ha_call("ha.create_input_boolean")
    async def create_input_boolean(
        self,
        input_id: str,
        name: str,
        initial: bool = False,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create an input_boolean helper.

        Args:
            input_id: Unique ID (slug)
            name: Display name
            initial: Initial state
            icon: Optional MDI icon

        Returns:
            Result dict with success, input_id, entity_id.
        """
        config: dict[str, Any] = {"name": name, "initial": initial}
        if icon:
            config["icon"] = icon

        try:
            result = await self._ws("input_boolean/create", **config)
            slug = result.get("id", input_id) if isinstance(result, dict) else input_id
            return {
                "success": True,
                "input_id": slug,
                "entity_id": f"input_boolean.{slug}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.create_input_number")
    async def create_input_number(
        self,
        input_id: str,
        name: str,
        min: float,
        max: float,
        initial: float | None = None,
        step: float = 1.0,
        unit_of_measurement: str | None = None,
        mode: str = "slider",
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create an input_number helper.

        Args:
            input_id: Unique ID (slug)
            name: Display name
            min: Minimum value
            max: Maximum value
            initial: Initial value
            step: Step increment
            unit_of_measurement: Unit label
            mode: "slider" or "box"
            icon: Optional MDI icon

        Returns:
            Result dict with success, input_id, entity_id.
        """
        config: dict[str, Any] = {
            "name": name,
            "min": min,
            "max": max,
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
            result = await self._ws("input_number/create", **config)
            slug = result.get("id", input_id) if isinstance(result, dict) else input_id
            return {
                "success": True,
                "input_id": slug,
                "entity_id": f"input_number.{slug}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.create_input_text")
    async def create_input_text(
        self,
        input_id: str,
        name: str,
        min_length: int = 0,
        max_length: int = 100,
        pattern: str | None = None,
        mode: str = "text",
        initial: str | None = None,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create an input_text helper.

        Args:
            input_id: Unique ID (slug)
            name: Display name
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regex pattern for validation
            mode: "text" or "password"
            initial: Initial value
            icon: Optional MDI icon

        Returns:
            Result dict with success, input_id, entity_id.
        """
        config: dict[str, Any] = {
            "name": name,
            "min": min_length,
            "max": max_length,
            "mode": mode,
        }
        if pattern is not None:
            config["pattern"] = pattern
        if initial is not None:
            config["initial"] = initial
        if icon:
            config["icon"] = icon

        try:
            result = await self._ws("input_text/create", **config)
            slug = result.get("id", input_id) if isinstance(result, dict) else input_id
            return {
                "success": True,
                "input_id": slug,
                "entity_id": f"input_text.{slug}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.create_input_select")
    async def create_input_select(
        self,
        input_id: str,
        name: str,
        options: list[str],
        initial: str | None = None,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create an input_select helper.

        Args:
            input_id: Unique ID (slug)
            name: Display name
            options: List of selectable options
            initial: Initial selected option
            icon: Optional MDI icon

        Returns:
            Result dict with success, input_id, entity_id.
        """
        config: dict[str, Any] = {"name": name, "options": options}
        if initial is not None:
            config["initial"] = initial
        if icon:
            config["icon"] = icon

        try:
            result = await self._ws("input_select/create", **config)
            slug = result.get("id", input_id) if isinstance(result, dict) else input_id
            return {
                "success": True,
                "input_id": slug,
                "entity_id": f"input_select.{slug}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.create_input_datetime")
    async def create_input_datetime(
        self,
        input_id: str,
        name: str,
        has_date: bool = True,
        has_time: bool = True,
        initial: str | None = None,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create an input_datetime helper.

        Args:
            input_id: Unique ID (slug)
            name: Display name
            has_date: Whether to include date
            has_time: Whether to include time
            initial: Initial datetime string
            icon: Optional MDI icon

        Returns:
            Result dict with success, input_id, entity_id.
        """
        config: dict[str, Any] = {
            "name": name,
            "has_date": has_date,
            "has_time": has_time,
        }
        if initial is not None:
            config["initial"] = initial
        if icon:
            config["icon"] = icon

        try:
            result = await self._ws("input_datetime/create", **config)
            slug = result.get("id", input_id) if isinstance(result, dict) else input_id
            return {
                "success": True,
                "input_id": slug,
                "entity_id": f"input_datetime.{slug}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.create_input_button")
    async def create_input_button(
        self,
        input_id: str,
        name: str,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create an input_button helper.

        Args:
            input_id: Unique ID (slug)
            name: Display name
            icon: Optional MDI icon

        Returns:
            Result dict with success, input_id, entity_id.
        """
        config: dict[str, Any] = {"name": name}
        if icon:
            config["icon"] = icon

        try:
            result = await self._ws("input_button/create", **config)
            slug = result.get("id", input_id) if isinstance(result, dict) else input_id
            return {
                "success": True,
                "input_id": slug,
                "entity_id": f"input_button.{slug}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.create_counter")
    async def create_counter(
        self,
        input_id: str,
        name: str,
        initial: int = 0,
        minimum: int | None = None,
        maximum: int | None = None,
        step: int = 1,
        restore: bool = True,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create a counter helper.

        Args:
            input_id: Unique ID (slug)
            name: Display name
            initial: Initial count value
            minimum: Minimum allowed value
            maximum: Maximum allowed value
            step: Increment/decrement step
            restore: Restore state on restart
            icon: Optional MDI icon

        Returns:
            Result dict with success, input_id, entity_id.
        """
        config: dict[str, Any] = {
            "name": name,
            "initial": initial,
            "step": step,
            "restore": restore,
        }
        if minimum is not None:
            config["minimum"] = minimum
        if maximum is not None:
            config["maximum"] = maximum
        if icon:
            config["icon"] = icon

        try:
            result = await self._ws("counter/create", **config)
            slug = result.get("id", input_id) if isinstance(result, dict) else input_id
            return {
                "success": True,
                "input_id": slug,
                "entity_id": f"counter.{slug}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.create_timer")
    async def create_timer(
        self,
        input_id: str,
        name: str,
        duration: str | None = None,
        restore: bool = True,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create a timer helper.

        Args:
            input_id: Unique ID (slug)
            name: Display name
            duration: Default duration (HH:MM:SS format)
            restore: Restore state on restart
            icon: Optional MDI icon

        Returns:
            Result dict with success, input_id, entity_id.
        """
        config: dict[str, Any] = {"name": name, "restore": restore}
        if duration is not None:
            config["duration"] = duration
        if icon:
            config["icon"] = icon

        try:
            result = await self._ws("timer/create", **config)
            slug = result.get("id", input_id) if isinstance(result, dict) else input_id
            return {
                "success": True,
                "input_id": slug,
                "entity_id": f"timer.{slug}",
            }
        except HAClientError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_ha_call("ha.delete_helper")
    async def delete_helper(
        self,
        domain: str,
        input_id: str,
    ) -> dict[str, Any]:
        """Delete a helper entity.

        Uses the WS {domain}/list to find the storage collection ID,
        then {domain}/delete to remove it.  HA's delete command requires
        the internal storage UUID, not the user-facing slug.

        Args:
            domain: Helper domain (e.g., "input_boolean", "counter")
            input_id: Helper ID (slug) to delete

        Returns:
            Result dict with success and entity_id.
        """
        entity_id = f"{domain}.{input_id}"

        if domain not in HELPER_DOMAINS:
            return {
                "success": False,
                "entity_id": entity_id,
                "error": f"'{domain}' is not a valid helper domain",
            }

        try:
            items: list[dict[str, Any]] = await self._ws(f"{domain}/list")
            storage_id: str | None = None
            for item in items:
                if item.get("id") == input_id or item.get("name") == input_id:
                    storage_id = item["id"]
                    break

            if not storage_id:
                return {
                    "success": False,
                    "entity_id": entity_id,
                    "error": f"Helper '{entity_id}' not found in HA storage",
                }

            id_key = f"{domain}_id"
            await self._ws(f"{domain}/delete", **{id_key: storage_id})
            return {"success": True, "entity_id": entity_id}
        except HAClientError as e:
            return {"success": False, "entity_id": entity_id, "error": str(e)}

    @_trace_ha_call("ha.list_helpers")
    async def list_helpers(self) -> list[dict[str, Any]]:
        """List all helper entities from Home Assistant.

        Fetches all entities and filters to helper domains.

        Returns:
            List of helper entity dicts with domain, entity_id,
            name, state, and attributes.
        """
        entities = await self.list_entities(detailed=True)  # type: ignore[attr-defined]

        helpers = []
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            domain = entity_id.split(".")[0] if "." in entity_id else ""
            if domain not in HELPER_DOMAINS:
                continue

            attrs = entity.get("attributes", {})
            helpers.append(
                {
                    "entity_id": entity_id,
                    "domain": domain,
                    "name": attrs.get("friendly_name", entity.get("name", "")),
                    "state": entity.get("state", ""),
                    "attributes": attrs,
                }
            )

        return helpers
