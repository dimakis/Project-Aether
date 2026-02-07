"""MCP client wrapper for hass-mcp tool invocation.

Provides a typed, async interface to the MCP tools available
via the hass-mcp server. Handles errors and provides consistent
response parsing.

Note: This client wraps the MCP tools that Cursor has access to.
In production, this would use the MCP protocol directly.

All public methods are traced via MLflow for observability.

This module acts as a thin facade that combines domain-specific
functionality from base, entities, automations, and diagnostics modules.
"""

from src.mcp.automations import AutomationMixin
from src.mcp.base import (
    BaseMCPClient,
    MCPClientConfig,
    MCPError,
    _trace_mcp_call,
)
from src.mcp.diagnostics import DiagnosticMixin
from src.mcp.entities import EntityMixin

# Re-export for backward compatibility
__all__ = ["MCPClient", "MCPClientConfig", "MCPError", "get_mcp_client", "reset_mcp_client"]


class MCPClient(BaseMCPClient, EntityMixin, AutomationMixin, DiagnosticMixin):
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

    pass


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


def reset_mcp_client() -> None:
    """Reset the MCP client singleton.

    Called after first-time setup stores HA config in DB, so the
    MCP client re-initializes with the new connection details on
    next access.

    Thread-safe: Acquires lock before modifying singleton.
    """
    global _client  # noqa: PLW0603
    with _client_lock:
        _client = None
