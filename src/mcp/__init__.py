"""MCP client wrapper for Home Assistant integration.

Provides a typed interface to the hass-mcp tools with
parsing, error handling, and workarounds for MCP gaps.
"""

from src.mcp.automation_deploy import (
    AutomationDeployer,
    build_condition,
    build_delay_action,
    build_service_action,
    build_state_trigger,
    build_sun_trigger,
    build_time_trigger,
)
from src.mcp.client import MCPClient, get_mcp_client
from src.mcp.constants import COMMON_SERVICES
from src.mcp.history import (
    EnergyDataPoint,
    EnergyHistory,
    EnergyHistoryClient,
    EnergyStats,
    discover_energy_sensors,
    get_energy_history,
)
from src.mcp.parsers import (
    parse_automation_list,
    parse_domain_summary,
    parse_entity,
    parse_entity_list,
    parse_system_overview,
)
from src.mcp.workarounds import infer_areas_from_entities, infer_devices_from_entities

__all__ = [
    # Client
    "MCPClient",
    "get_mcp_client",
    # Parsers
    "parse_system_overview",
    "parse_entity_list",
    "parse_entity",
    "parse_domain_summary",
    "parse_automation_list",
    # Workarounds
    "infer_devices_from_entities",
    "infer_areas_from_entities",
    # Automation Deployment
    "AutomationDeployer",
    "build_state_trigger",
    "build_time_trigger",
    "build_sun_trigger",
    "build_service_action",
    "build_delay_action",
    "build_condition",
    # Energy History (US3)
    "EnergyHistoryClient",
    "EnergyHistory",
    "EnergyDataPoint",
    "EnergyStats",
    "get_energy_history",
    "discover_energy_sensors",
    # Constants
    "COMMON_SERVICES",
]
