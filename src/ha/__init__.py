"""HA client wrapper for Home Assistant integration.

Provides a typed interface to the hass-ha tools with
parsing, error handling, and workarounds for HA gaps.
"""

from src.ha.automation_deploy import (
    AutomationDeployer,
    build_condition,
    build_delay_action,
    build_service_action,
    build_state_trigger,
    build_sun_trigger,
    build_time_trigger,
)
from src.ha.behavioral import BehavioralAnalysisClient
from src.ha.client import HAClient, get_ha_client
from src.ha.constants import COMMON_SERVICES
from src.ha.dashboards import DashboardMixin
from src.ha.history import (
    EnergyDataPoint,
    EnergyHistory,
    EnergyHistoryClient,
    EnergyStats,
    discover_energy_sensors,
    get_energy_history,
)
from src.ha.logbook import (
    LogbookHistoryClient,
    LogbookStats,
    get_logbook_stats,
)
from src.ha.parsers import (
    ParsedLogbookEntry,
    parse_automation_list,
    parse_domain_summary,
    parse_entity,
    parse_entity_list,
    parse_logbook_entry,
    parse_logbook_list,
    parse_system_overview,
)
from src.ha.workarounds import infer_areas_from_entities, infer_devices_from_entities

__all__ = [
    # Constants
    "COMMON_SERVICES",
    # Automation Deployment
    "AutomationDeployer",
    # Behavioral Analysis (US5 / Feature 03)
    "BehavioralAnalysisClient",
    # Client
    "DashboardMixin",
    "EnergyDataPoint",
    "EnergyHistory",
    # Energy History (US3)
    "EnergyHistoryClient",
    "EnergyStats",
    "HAClient",
    # Logbook (US5 / Feature 03)
    "LogbookHistoryClient",
    "LogbookStats",
    "ParsedLogbookEntry",
    "build_condition",
    "build_delay_action",
    "build_service_action",
    "build_state_trigger",
    "build_sun_trigger",
    "build_time_trigger",
    "discover_energy_sensors",
    "get_energy_history",
    "get_ha_client",
    "get_logbook_stats",
    "infer_areas_from_entities",
    # Workarounds
    "infer_devices_from_entities",
    "parse_automation_list",
    "parse_domain_summary",
    "parse_entity",
    "parse_entity_list",
    "parse_logbook_entry",
    "parse_logbook_list",
    # Parsers
    "parse_system_overview",
]
