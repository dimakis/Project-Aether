"""MCP client wrapper for hass-mcp tool invocation.

Provides a typed, async interface to the MCP tools available
via the hass-mcp server. Handles errors and provides consistent
response parsing.

Note: This client wraps the MCP tools that Cursor has access to.
In production, this would use the MCP protocol directly.

All public methods are traced via MLflow for observability.
"""

import time
from typing import Any

from pydantic import BaseModel, Field

from src.settings import get_settings


class MCPError(Exception):
    """Error from MCP tool invocation."""

    def __init__(self, message: str, tool: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.tool = tool
        self.details = details or {}


class MCPClientConfig(BaseModel):
    """Configuration for MCP client."""

    ha_url: str = Field(..., description="Home Assistant URL (primary/local)")
    ha_url_remote: str | None = Field(
        None, description="Home Assistant remote URL (fallback)"
    )
    ha_token: str = Field(..., description="Home Assistant token")
    timeout: int = Field(default=30, description="Request timeout in seconds")


def _trace_mcp_call(name: str):
    """Decorator to trace MCP client methods.

    Creates an MLflow span for the decorated method, capturing timing,
    parameters, and errors.

    Args:
        name: Name for the span (e.g., "mcp.list_entities")
    """
    from src.tracing import trace_with_uri

    return trace_with_uri(name=name, span_type="RETRIEVER")


class MCPClient:
    """Client for invoking hass-mcp tools.

    This class provides a typed interface to the MCP tools.
    In the Cursor environment, these tools are available directly.
    In production, this would connect to the MCP server.

    All public methods are traced via MLflow for observability.

    Usage:
        client = MCPClient()
        overview = await client.system_overview()
        entities = await client.list_entities(domain="light")
    """

    def __init__(self, config: MCPClientConfig | None = None):
        """Initialize MCP client.

        Args:
            config: Optional configuration (uses settings if not provided)
        """
        if config is None:
            settings = get_settings()
            config = MCPClientConfig(
                ha_url=settings.ha_url,
                ha_url_remote=settings.ha_url_remote,
                ha_token=settings.ha_token.get_secret_value(),
            )
        self.config = config
        self._connected = False
        self._active_url: str | None = None  # Which URL is currently working

    @_trace_mcp_call("mcp.connect")
    async def connect(self) -> None:
        """Verify connection to Home Assistant.

        Tries local URL first, falls back to remote if configured.
        """
        import httpx

        urls_to_try = [self.config.ha_url]
        if self.config.ha_url_remote:
            urls_to_try.append(self.config.ha_url_remote)

        errors = []
        for url in urls_to_try:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(
                        f"{url}/api/",
                        headers={"Authorization": f"Bearer {self.config.ha_token}"},
                    )
                    if response.status_code == 200:
                        self._active_url = url
                        self._connected = True
                        return
                    errors.append(f"{url}: HTTP {response.status_code}")
            except Exception as e:
                errors.append(f"{url}: {type(e).__name__}")

        raise MCPError(
            f"All connection attempts failed: {'; '.join(errors)}",
            "connect",
        )

    def _get_url(self) -> str:
        """Get the active HA URL."""
        return self._active_url or self.config.ha_url

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        """Make a request to HA, with automatic URL fallback.

        Args:
            method: HTTP method
            path: API path (without base URL)
            json: JSON body
            params: Query parameters

        Returns:
            Response JSON
        """
        import httpx

        from src.tracing import log_metric

        start_time = time.perf_counter()

        # Build list of URLs to try
        urls_to_try = []
        if self._active_url:
            urls_to_try.append(self._active_url)
        if self.config.ha_url not in urls_to_try:
            urls_to_try.append(self.config.ha_url)
        if self.config.ha_url_remote and self.config.ha_url_remote not in urls_to_try:
            urls_to_try.append(self.config.ha_url_remote)

        errors = []
        for url in urls_to_try:
            try:
                async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                    response = await client.request(
                        method,
                        f"{url}{path}",
                        headers={"Authorization": f"Bearer {self.config.ha_token}"},
                        json=json,
                        params=params,
                    )
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    log_metric(f"mcp.request.{method.lower()}.duration_ms", duration_ms)

                    if response.status_code in (200, 201):
                        self._active_url = url  # Remember working URL
                        return response.json() if response.content else {}
                    elif response.status_code == 404:
                        return None
                    errors.append(f"{url}: HTTP {response.status_code}")
            except httpx.ConnectError:
                errors.append(f"{url}: Connection failed")
            except httpx.TimeoutException:
                errors.append(f"{url}: Timeout")
            except Exception as e:
                errors.append(f"{url}: {type(e).__name__}")

        raise MCPError(
            f"All connection attempts failed: {'; '.join(errors)}",
            "request",
        )

    @_trace_mcp_call("mcp.get_version")
    async def get_version(self) -> str:
        """Get Home Assistant version.

        Returns:
            Version string (e.g., "2024.1.0")
        """
        data = await self._request("GET", "/api/")
        if data:
            return data.get("version", "unknown")
        raise MCPError("Failed to get HA version", "get_version")

    @_trace_mcp_call("mcp.system_overview")
    async def system_overview(self) -> dict[str, Any]:
        """Get comprehensive system overview.

        Returns:
            Dictionary with total_entities, domains, domain_samples, etc.
        """
        states = await self._request("GET", "/api/states")
        if not states:
            raise MCPError("Failed to get states", "system_overview")

        # Build overview from states
        domains: dict[str, dict[str, Any]] = {}
        for state in states:
            entity_id = state.get("entity_id", "")
            domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
            entity_state = state.get("state", "unknown")

            if domain not in domains:
                domains[domain] = {"count": 0, "states": {}}

            domains[domain]["count"] += 1
            if entity_state not in domains[domain]["states"]:
                domains[domain]["states"][entity_state] = 0
            domains[domain]["states"][entity_state] += 1

        return {
            "total_entities": len(states),
            "domains": domains,
            "domain_samples": {},  # Would need additional logic
        }

    @_trace_mcp_call("mcp.list_entities")
    async def list_entities(
        self,
        domain: str | None = None,
        search_query: str | None = None,
        limit: int = 1000,
        detailed: bool = False,
    ) -> list[dict[str, Any]]:
        """List entities with optional filtering.

        Args:
            domain: Filter by domain (e.g., "light")
            search_query: Search term for filtering
            limit: Maximum entities to return
            detailed: Include full attributes

        Returns:
            List of entity dictionaries
        """
        from src.tracing import log_param

        # Log query parameters
        if domain:
            log_param("mcp.list_entities.domain", domain)
        if search_query:
            log_param("mcp.list_entities.search_query", search_query)

        states = await self._request("GET", "/api/states")
        if not states:
            raise MCPError("Failed to list entities", "list_entities")

        entities = []

        for state in states:
            entity_id = state.get("entity_id", "")
            entity_domain = entity_id.split(".")[0] if "." in entity_id else ""

            # Filter by domain
            if domain and entity_domain != domain:
                continue

            # Filter by search query
            if search_query:
                name = state.get("attributes", {}).get("friendly_name", entity_id)
                if (
                    search_query.lower() not in name.lower()
                    and search_query.lower() not in entity_id.lower()
                ):
                    continue

            entity = {
                "entity_id": entity_id,
                "state": state.get("state"),
                "name": state.get("attributes", {}).get("friendly_name", entity_id),
                "domain": entity_domain,
            }

            if detailed:
                entity["attributes"] = state.get("attributes", {})
                entity["last_changed"] = state.get("last_changed")
                entity["last_updated"] = state.get("last_updated")

            # Try to extract area_id from attributes
            attrs = state.get("attributes", {})
            if "area_id" in attrs:
                entity["area_id"] = attrs["area_id"]

            entities.append(entity)

            if len(entities) >= limit:
                break

        return entities

    @_trace_mcp_call("mcp.get_entity")
    async def get_entity(
        self,
        entity_id: str,
        detailed: bool = True,
    ) -> dict[str, Any] | None:
        """Get a specific entity by ID.

        Args:
            entity_id: Entity ID (e.g., "light.living_room")
            detailed: Include full attributes

        Returns:
            Entity dictionary or None if not found
        """
        from src.tracing import log_param

        log_param("mcp.get_entity.entity_id", entity_id)

        state = await self._request("GET", f"/api/states/{entity_id}")
        if not state:
            return None

        domain = entity_id.split(".")[0] if "." in entity_id else ""

        entity = {
            "entity_id": entity_id,
            "state": state.get("state"),
            "name": state.get("attributes", {}).get("friendly_name", entity_id),
            "domain": domain,
        }

        if detailed:
            entity["attributes"] = state.get("attributes", {})
            entity["last_changed"] = state.get("last_changed")
            entity["last_updated"] = state.get("last_updated")

        return entity

    @_trace_mcp_call("mcp.domain_summary")
    async def domain_summary(
        self,
        domain: str,
        example_limit: int = 3,
    ) -> dict[str, Any]:
        """Get summary of entities in a domain.

        Args:
            domain: Domain to summarize (e.g., "light")
            example_limit: Max examples per state

        Returns:
            Dictionary with count, state distribution, examples
        """
        from src.tracing import log_param

        log_param("mcp.domain_summary.domain", domain)

        entities = await self.list_entities(domain=domain, detailed=True)

        state_distribution: dict[str, int] = {}
        examples: dict[str, list[dict[str, Any]]] = {}
        common_attributes: set[str] = set()

        for entity in entities:
            state = entity.get("state", "unknown")
            state_distribution[state] = state_distribution.get(state, 0) + 1

            if state not in examples:
                examples[state] = []
            if len(examples[state]) < example_limit:
                examples[state].append(
                    {
                        "entity_id": entity["entity_id"],
                        "name": entity["name"],
                    }
                )

            if entity.get("attributes"):
                common_attributes.update(entity["attributes"].keys())

        return {
            "total_count": len(entities),
            "state_distribution": state_distribution,
            "examples": examples,
            "common_attributes": list(common_attributes)[:20],
        }

    @_trace_mcp_call("mcp.list_automations")
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

    @_trace_mcp_call("mcp.entity_action")
    async def entity_action(
        self,
        entity_id: str,
        action: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform action on an entity.

        Args:
            entity_id: Entity to act on
            action: Action (on, off, toggle)
            params: Additional parameters

        Returns:
            Response from HA
        """
        from src.tracing import log_param

        log_param("mcp.entity_action.entity_id", entity_id)
        log_param("mcp.entity_action.action", action)

        domain = entity_id.split(".")[0] if "." in entity_id else ""
        service = f"turn_{action}" if action in ("on", "off") else action

        data = {"entity_id": entity_id}
        if params:
            data.update(params)

        await self._request("POST", f"/api/services/{domain}/{service}", json=data)
        return {"success": True}

    @_trace_mcp_call("mcp.call_service")
    async def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call any Home Assistant service.

        Args:
            domain: Service domain
            service: Service name
            data: Service data

        Returns:
            Response from HA
        """
        from src.tracing import log_param

        log_param("mcp.call_service.domain", domain)
        log_param("mcp.call_service.service", service)

        result = await self._request(
            "POST", f"/api/services/{domain}/{service}", json=data or {}
        )
        return result or {}

    @_trace_mcp_call("mcp.get_history")
    async def get_history(
        self,
        entity_id: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get entity history.

        Args:
            entity_id: Entity to get history for
            hours: Hours of history

        Returns:
            History data
        """
        from datetime import datetime, timedelta, timezone

        from src.tracing import log_param

        log_param("mcp.get_history.entity_id", entity_id)
        log_param("mcp.get_history.hours", hours)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        history = await self._request(
            "GET",
            f"/api/history/period/{start_time.isoformat()}",
            params={
                "filter_entity_id": entity_id,
                "end_time": end_time.isoformat(),
            },
        )

        if not history or not history[0]:
            return {"entity_id": entity_id, "states": [], "count": 0}

        states = history[0]
        return {
            "entity_id": entity_id,
            "states": [
                {"state": s.get("state"), "last_changed": s.get("last_changed")}
                for s in states
            ],
            "count": len(states),
            "first_changed": states[0].get("last_changed") if states else None,
            "last_changed": states[-1].get("last_changed") if states else None,
        }

    @_trace_mcp_call("mcp.get_logbook")
    async def get_logbook(
        self,
        hours: int = 24,
        entity_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get logbook entries from Home Assistant.

        Fetches logbook data for behavioral analysis, including
        user actions, automation triggers, and state changes.

        Args:
            hours: Hours of history to fetch
            entity_id: Optional entity to filter by

        Returns:
            List of logbook entry dicts
        """
        from datetime import datetime, timedelta, timezone

        from src.tracing import log_param

        log_param("mcp.get_logbook.hours", hours)
        if entity_id:
            log_param("mcp.get_logbook.entity_id", entity_id)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        params: dict[str, Any] = {
            "end_time": end_time.isoformat(),
        }
        if entity_id:
            params["entity"] = entity_id

        result = await self._request(
            "GET",
            f"/api/logbook/{start_time.isoformat()}",
            params=params,
        )

        if not result:
            return []

        # HA logbook returns a flat list of entries
        if isinstance(result, list):
            return result

        return []

    @_trace_mcp_call("mcp.search_entities")
    async def search_entities(
        self,
        query: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search for entities matching a query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Search results with count and domain breakdown
        """
        from src.tracing import log_param

        log_param("mcp.search_entities.query", query)

        entities = await self.list_entities(search_query=query, limit=limit)

        # Build domain counts
        domains: dict[str, int] = {}
        for entity in entities:
            domain = entity.get("domain", "unknown")
            domains[domain] = domains.get(domain, 0) + 1

        return {
            "count": len(entities),
            "results": entities,
            "domains": domains,
        }

    # =========================================================================
    # AUTOMATION MANAGEMENT (Direct REST API - no MCP gap!)
    # =========================================================================

    @_trace_mcp_call("mcp.create_automation")
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

        This bypasses the MCP gap by using HA's config API directly.

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
        from src.tracing import log_param

        log_param("mcp.create_automation.id", automation_id)
        log_param("mcp.create_automation.alias", alias)

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
        except MCPError as e:
            return {
                "success": False,
                "automation_id": automation_id,
                "error": str(e),
                "method": "rest_api",
            }

    @_trace_mcp_call("mcp.get_automation_config")
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

    @_trace_mcp_call("mcp.delete_automation")
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
        from src.tracing import log_param

        log_param("mcp.delete_automation.id", automation_id)

        try:
            await self._request(
                "DELETE",
                f"/api/config/automation/config/{automation_id}",
            )
            return {"success": True, "automation_id": automation_id}
        except MCPError as e:
            return {"success": False, "automation_id": automation_id, "error": str(e)}

    @_trace_mcp_call("mcp.list_automation_configs")
    async def list_automation_configs(self) -> list[dict[str, Any]]:
        """List all automation configurations.

        Returns:
            List of automation config dicts
        """
        result = await self._request("GET", "/api/config/automation/config")
        return result if result else []

    # =========================================================================
    # SCRIPTS (Create reusable action sequences)
    # =========================================================================

    @_trace_mcp_call("mcp.create_script")
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
        from src.tracing import log_param

        log_param("mcp.create_script.id", script_id)

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
        except MCPError as e:
            return {"success": False, "script_id": script_id, "error": str(e)}

    @_trace_mcp_call("mcp.delete_script")
    async def delete_script(self, script_id: str) -> dict[str, Any]:
        """Delete a script."""
        try:
            await self._request("DELETE", f"/api/config/script/config/{script_id}")
            return {"success": True, "script_id": script_id}
        except MCPError as e:
            return {"success": False, "script_id": script_id, "error": str(e)}

    # =========================================================================
    # SCENES (Capture and restore entity states)
    # =========================================================================

    @_trace_mcp_call("mcp.create_scene")
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
        from src.tracing import log_param

        log_param("mcp.create_scene.id", scene_id)

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
        except MCPError as e:
            return {"success": False, "scene_id": scene_id, "error": str(e)}

    @_trace_mcp_call("mcp.delete_scene")
    async def delete_scene(self, scene_id: str) -> dict[str, Any]:
        """Delete a scene."""
        try:
            await self._request("DELETE", f"/api/config/scene/config/{scene_id}")
            return {"success": True, "scene_id": scene_id}
        except MCPError as e:
            return {"success": False, "scene_id": scene_id, "error": str(e)}

    # =========================================================================
    # INPUT HELPERS (User-configurable state holders)
    # =========================================================================

    @_trace_mcp_call("mcp.create_input_boolean")
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
        except MCPError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    @_trace_mcp_call("mcp.create_input_number")
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
        except MCPError as e:
            return {"success": False, "input_id": input_id, "error": str(e)}

    # =========================================================================
    # TEMPLATES & EVENTS
    # =========================================================================

    @_trace_mcp_call("mcp.render_template")
    async def render_template(self, template: str) -> str | None:
        """Render a Jinja2 template using HA's template engine.

        Useful for complex state calculations.

        Args:
            template: Jinja2 template string

        Returns:
            Rendered result or None on error
        """
        try:
            result = await self._request(
                "POST",
                "/api/template",
                json={"template": template},
            )
            return result if isinstance(result, str) else str(result)
        except MCPError:
            return None

    @_trace_mcp_call("mcp.fire_event")
    async def fire_event(
        self,
        event_type: str,
        event_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fire a custom event.

        Useful for triggering automations or signaling state changes.

        Args:
            event_type: Event type name
            event_data: Optional event data

        Returns:
            Result dict
        """
        from src.tracing import log_param

        log_param("mcp.fire_event.type", event_type)

        try:
            await self._request(
                "POST",
                f"/api/events/{event_type}",
                json=event_data or {},
            )
            return {"success": True, "event_type": event_type}
        except MCPError as e:
            return {"success": False, "event_type": event_type, "error": str(e)}

    @_trace_mcp_call("mcp.get_error_log")
    async def get_error_log(self) -> str:
        """Get Home Assistant error log.

        Useful for debugging issues.

        Returns:
            Error log contents
        """
        try:
            result = await self._request("GET", "/api/error_log")
            return result if isinstance(result, str) else ""
        except MCPError:
            return ""

    @_trace_mcp_call("mcp.check_config")
    async def check_config(self) -> dict[str, Any]:
        """Check Home Assistant configuration validity.

        Returns:
            Config check result with errors/warnings
        """
        try:
            result = await self._request("POST", "/api/config/core/check_config")
            return result or {"result": "unknown"}
        except MCPError as e:
            return {"result": "error", "error": str(e)}

    # =========================================================================
    # DIAGNOSTIC METHODS (Feature 06: HA Diagnostics & Troubleshooting)
    # =========================================================================

    @_trace_mcp_call("mcp.list_config_entries")
    async def list_config_entries(
        self,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all integration config entries.

        Args:
            domain: Optional domain to filter by (e.g., "zha", "mqtt")

        Returns:
            List of config entry dicts with entry_id, domain, title, state, etc.
        """
        result = await self._request("GET", "/api/config/config_entries")
        entries = result if isinstance(result, list) else []
        if domain:
            entries = [e for e in entries if e.get("domain") == domain]
        return entries

    @_trace_mcp_call("mcp.get_config_entry_diagnostics")
    async def get_config_entry_diagnostics(
        self,
        entry_id: str,
    ) -> dict[str, Any] | None:
        """Get diagnostics for a specific integration config entry.

        Not all integrations support diagnostics. Returns None if the
        integration doesn't provide diagnostic data (404 response).

        Args:
            entry_id: The config entry ID

        Returns:
            Diagnostic data dict, or None if unsupported
        """
        return await self._request(
            "GET", f"/api/config/config_entries/{entry_id}/diagnostics"
        )

    @_trace_mcp_call("mcp.reload_config_entry")
    async def reload_config_entry(self, entry_id: str) -> dict[str, Any]:
        """Reload a specific integration config entry.

        WARNING: This mutates HA state. Should be HITL-gated at the tool level.

        Args:
            entry_id: The config entry ID to reload

        Returns:
            Reload result (may include require_restart flag)
        """
        result = await self._request(
            "POST", f"/api/config/config_entries/entry/{entry_id}/reload"
        )
        return result or {}

    @_trace_mcp_call("mcp.list_services")
    async def list_services(self) -> list[dict[str, Any]]:
        """List all available Home Assistant services.

        Returns:
            List of service domain dicts, each containing domain name
            and a services dict with service names and descriptions.
        """
        result = await self._request("GET", "/api/services")
        return result if isinstance(result, list) else []

    @_trace_mcp_call("mcp.list_event_types")
    async def list_event_types(self) -> list[dict[str, Any]]:
        """List all available event types in Home Assistant.

        Returns:
            List of event type dicts with event_type and listener_count.
        """
        result = await self._request("GET", "/api/events")
        return result if isinstance(result, list) else []


# Singleton client (thread-safe via double-checked locking, T186)
_client: MCPClient | None = None
_client_lock = __import__("threading").Lock()


def get_mcp_client() -> MCPClient:
    """Get or create the MCP client singleton.

    Thread-safe: Uses double-checked locking to prevent concurrent
    client creation in multi-threaded environments.

    Returns:
        MCPClient instance
    """
    global _client  # noqa: PLW0603
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = MCPClient()
    return _client
