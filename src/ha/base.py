"""Base HA client with HTTP request handling and connection management.

Provides the core HTTP client functionality including URL fallback,
connection management, and tracing decorators.
"""

import time
from typing import Any

from pydantic import BaseModel, Field

from src.exceptions import HAClientError
from src.settings import get_settings


class HAClientConfig(BaseModel):
    """Configuration for HA client."""

    ha_url: str = Field(..., description="Home Assistant URL (primary/local)")
    ha_url_remote: str | None = Field(
        None, description="Home Assistant remote URL (fallback)"
    )
    ha_token: str = Field(..., description="Home Assistant token")
    timeout: int = Field(default=30, description="Request timeout in seconds")


def _try_get_db_config(settings) -> tuple[str, str] | None:
    """Try to read HA config from DB (non-blocking best effort).

    Returns (ha_url, ha_token) if successful, None otherwise.
    Gracefully handles missing DB, no config, or event loop issues.
    """
    import asyncio
    import structlog

    logger = structlog.get_logger(__name__)

    try:
        from src.api.auth import _get_jwt_secret
        from src.dal.system_config import SystemConfigRepository
        from src.storage import get_session

        jwt_secret = _get_jwt_secret(settings)

        async def _fetch():
            async with get_session() as session:
                repo = SystemConfigRepository(session)
                return await repo.get_ha_connection(jwt_secret)

        # Try to run in existing event loop or create a new one
        try:
            loop = asyncio.get_running_loop()
            # If already in an async context, we can't use asyncio.run().
            # Return None and let the env var fallback be used.
            # The setup endpoint calls reset_ha_client() after storing
            # config, so next access will re-init with DB config.
            return None
        except RuntimeError:
            # No event loop running - safe to use asyncio.run()
            return asyncio.run(_fetch())
    except Exception as exc:
        logger.debug("mcp_db_config_fallback", reason=str(exc))
        return None


def _trace_ha_call(name: str):
    """Decorator to trace HA client methods.

    Creates an MLflow span for the decorated method, capturing timing,
    parameters, and errors.

    Args:
        name: Name for the span (e.g., "ha.list_entities")
    """
    from src.tracing import trace_with_uri

    return trace_with_uri(name=name, span_type="RETRIEVER")


class BaseHAClient:
    """Base HTTP client for Home Assistant API.

    Handles connection management, URL fallback, and HTTP requests.
    Domain-specific functionality is added via mixins or inheritance.
    """

    def __init__(self, config: HAClientConfig | None = None):
        """Initialize base HA client.

        Tries to read HA config from DB first (set via setup wizard),
        then falls back to environment variables.

        Args:
            config: Optional configuration (uses settings if not provided)
        """
        if config is None:
            config = self._resolve_config()
        self.config = config
        self._connected = False
        self._active_url: str | None = None  # Which URL is currently working

    @staticmethod
    def _resolve_config() -> HAClientConfig:
        """Resolve HA config from DB (primary) or env vars (fallback).

        Attempts to read HA URL and decrypted token from the system_config
        DB table. If unavailable (no setup, DB error, or no event loop),
        falls back to settings from environment variables.
        """
        settings = get_settings()

        # Try DB config
        db_config = _try_get_db_config(settings)
        if db_config:
            ha_url, ha_token = db_config
            return HAClientConfig(
                ha_url=ha_url,
                ha_url_remote=settings.ha_url_remote,
                ha_token=ha_token,
            )

        # Fallback to env vars
        return HAClientConfig(
            ha_url=settings.ha_url,
            ha_url_remote=settings.ha_url_remote,
            ha_token=settings.ha_token.get_secret_value(),
        )

    @_trace_ha_call("ha.connect")
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

        raise HAClientError(
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
                    log_metric(f"ha.request.{method.lower()}.duration_ms", duration_ms)

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

        raise HAClientError(
            f"All connection attempts failed: {'; '.join(errors)}",
            "request",
        )

    @_trace_ha_call("ha.get_version")
    async def get_version(self) -> str:
        """Get Home Assistant version.

        Returns:
            Version string (e.g., "2024.1.0")
        """
        data = await self._request("GET", "/api/")
        if data:
            return data.get("version", "unknown")
        raise HAClientError("Failed to get HA version", "get_version")

    @_trace_ha_call("ha.system_overview")
    async def system_overview(self) -> dict[str, Any]:
        """Get comprehensive system overview.

        Returns:
            Dictionary with total_entities, domains, domain_samples, etc.
        """
        states = await self._request("GET", "/api/states")
        if not states:
            raise HAClientError("Failed to get states", "system_overview")

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
