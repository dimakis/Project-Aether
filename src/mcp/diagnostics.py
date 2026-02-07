"""Diagnostic operations for Home Assistant.

Provides methods for diagnostics, configuration validation,
service/event listing, and template rendering.
"""

from typing import Any

from src.mcp.base import MCPError, _trace_mcp_call
from src.tracing import log_param


class DiagnosticMixin:
    """Mixin providing diagnostic and utility operations."""

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
