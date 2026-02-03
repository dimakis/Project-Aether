"""MCP client wrapper for hass-mcp tool invocation.

Provides a typed, async interface to the MCP tools available
via the hass-mcp server. Handles errors and provides consistent
response parsing.

Note: This client wraps the MCP tools that Cursor has access to.
In production, this would use the MCP protocol directly.
"""

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

    ha_url: str = Field(..., description="Home Assistant URL")
    ha_token: str = Field(..., description="Home Assistant token")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class MCPClient:
    """Client for invoking hass-mcp tools.

    This class provides a typed interface to the MCP tools.
    In the Cursor environment, these tools are available directly.
    In production, this would connect to the MCP server.

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
                ha_token=settings.ha_token.get_secret_value(),
            )
        self.config = config
        self._connected = False

    async def connect(self) -> None:
        """Verify connection to Home Assistant."""
        # In Cursor, tools are always available
        # In production, this would verify the MCP server connection
        self._connected = True

    async def get_version(self) -> str:
        """Get Home Assistant version.

        Returns:
            Version string (e.g., "2024.1.0")
        """
        # This would invoke mcp_hass-mcp_get_version
        # For now, we'll use httpx to call HA directly as fallback
        import httpx

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                f"{self.config.ha_url}/api/",
                headers={"Authorization": f"Bearer {self.config.ha_token}"},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("version", "unknown")
            raise MCPError("Failed to get HA version", "get_version")

    async def system_overview(self) -> dict[str, Any]:
        """Get comprehensive system overview.

        Returns:
            Dictionary with total_entities, domains, domain_samples, etc.
        """
        import httpx

        # Fallback: call HA API directly
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                f"{self.config.ha_url}/api/states",
                headers={"Authorization": f"Bearer {self.config.ha_token}"},
            )
            if response.status_code != 200:
                raise MCPError("Failed to get states", "system_overview")

            states = response.json()

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
        import httpx

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                f"{self.config.ha_url}/api/states",
                headers={"Authorization": f"Bearer {self.config.ha_token}"},
            )
            if response.status_code != 200:
                raise MCPError("Failed to list entities", "list_entities")

            states = response.json()
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
                    if search_query.lower() not in name.lower() and search_query.lower() not in entity_id.lower():
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
        import httpx

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                f"{self.config.ha_url}/api/states/{entity_id}",
                headers={"Authorization": f"Bearer {self.config.ha_token}"},
            )
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                raise MCPError(f"Failed to get entity {entity_id}", "get_entity")

            state = response.json()
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
                examples[state].append({
                    "entity_id": entity["entity_id"],
                    "name": entity["name"],
                })

            if entity.get("attributes"):
                common_attributes.update(entity["attributes"].keys())

        return {
            "total_count": len(entities),
            "state_distribution": state_distribution,
            "examples": examples,
            "common_attributes": list(common_attributes)[:20],
        }

    async def list_automations(self) -> list[dict[str, Any]]:
        """List all automations.

        Returns:
            List of automation dictionaries
        """
        entities = await self.list_entities(domain="automation", detailed=True)

        automations = []
        for entity in entities:
            attrs = entity.get("attributes", {})
            automations.append({
                "id": attrs.get("id", entity["entity_id"]),
                "entity_id": entity["entity_id"],
                "state": entity["state"],
                "alias": attrs.get("friendly_name", entity["name"]),
                "last_triggered": attrs.get("last_triggered"),
                "mode": attrs.get("mode", "single"),
            })

        return automations

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
        import httpx

        domain = entity_id.split(".")[0] if "." in entity_id else ""
        service = f"turn_{action}" if action in ("on", "off") else action

        data = {"entity_id": entity_id}
        if params:
            data.update(params)

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.ha_url}/api/services/{domain}/{service}",
                headers={"Authorization": f"Bearer {self.config.ha_token}"},
                json=data,
            )
            if response.status_code not in (200, 201):
                raise MCPError(
                    f"Failed to execute {action} on {entity_id}",
                    "entity_action",
                    {"status": response.status_code},
                )

            return {"success": True}

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
        import httpx

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.ha_url}/api/services/{domain}/{service}",
                headers={"Authorization": f"Bearer {self.config.ha_token}"},
                json=data or {},
            )
            if response.status_code not in (200, 201):
                raise MCPError(
                    f"Failed to call {domain}.{service}",
                    "call_service",
                    {"status": response.status_code},
                )

            return response.json() if response.content else {}

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
        import httpx
        from datetime import datetime, timedelta, timezone

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                f"{self.config.ha_url}/api/history/period/{start_time.isoformat()}",
                params={
                    "filter_entity_id": entity_id,
                    "end_time": end_time.isoformat(),
                },
                headers={"Authorization": f"Bearer {self.config.ha_token}"},
            )
            if response.status_code != 200:
                raise MCPError(f"Failed to get history for {entity_id}", "get_history")

            history = response.json()
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


# Singleton client
_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """Get or create the MCP client singleton.

    Returns:
        MCPClient instance
    """
    global _client
    if _client is None:
        _client = MCPClient()
    return _client
