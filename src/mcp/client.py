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
