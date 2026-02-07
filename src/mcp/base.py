"""Base MCP client with HTTP request handling and connection management.

Provides the core HTTP client functionality including URL fallback,
connection management, and tracing decorators.
"""

import time
from typing import Any

from pydantic import BaseModel, Field

from src.exceptions import MCPError
from src.settings import get_settings


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


class BaseMCPClient:
    """Base HTTP client for Home Assistant API.

    Handles connection management, URL fallback, and HTTP requests.
    Domain-specific functionality is added via mixins or inheritance.
    """

    def __init__(self, config: MCPClientConfig | None = None):
        """Initialize base MCP client.

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
