"""HA client wrapper for Home Assistant integration.

Provides a typed interface to the hass-ha tools with
parsing, error handling, and workarounds for HA gaps.

Uses lazy imports to avoid loading httpx/HA clients at import time.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    # automation_deploy
    "AutomationDeployer": "src.ha.automation_deploy",
    "build_condition": "src.ha.automation_deploy",
    "build_delay_action": "src.ha.automation_deploy",
    "build_service_action": "src.ha.automation_deploy",
    "build_state_trigger": "src.ha.automation_deploy",
    "build_sun_trigger": "src.ha.automation_deploy",
    "build_time_trigger": "src.ha.automation_deploy",
    # behavioral
    "BehavioralAnalysisClient": "src.ha.behavioral",
    # client
    "HAClient": "src.ha.client",
    "close_all_ha_clients": "src.ha.client",
    "get_ha_client": "src.ha.client",
    "get_ha_client_async": "src.ha.client",
    # constants
    "COMMON_SERVICES": "src.ha.constants",
    # dashboards
    "DashboardMixin": "src.ha.dashboards",
    # event_handler
    "EventHandler": "src.ha.event_handler",
    # event_stream
    "HAEventStream": "src.ha.event_stream",
    # history
    "EnergyDataPoint": "src.ha.history",
    "EnergyHistory": "src.ha.history",
    "EnergyHistoryClient": "src.ha.history",
    "EnergyStats": "src.ha.history",
    "discover_energy_sensors": "src.ha.history",
    "get_energy_history": "src.ha.history",
    # logbook
    "LogbookHistoryClient": "src.ha.logbook",
    "LogbookStats": "src.ha.logbook",
    "get_logbook_stats": "src.ha.logbook",
    # parsers
    "ParsedLogbookEntry": "src.ha.parsers",
    "parse_automation_list": "src.ha.parsers",
    "parse_domain_summary": "src.ha.parsers",
    "parse_entity": "src.ha.parsers",
    "parse_entity_list": "src.ha.parsers",
    "parse_logbook_entry": "src.ha.parsers",
    "parse_logbook_list": "src.ha.parsers",
    "parse_system_overview": "src.ha.parsers",
    # workarounds
    "infer_areas_from_entities": "src.ha.workarounds",
    "infer_devices_from_entities": "src.ha.workarounds",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]

    if name in _EXPORTS:
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr

    raise AttributeError(f"module 'src.ha' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
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
    from src.ha.client import HAClient, close_all_ha_clients, get_ha_client, get_ha_client_async
    from src.ha.constants import COMMON_SERVICES
    from src.ha.dashboards import DashboardMixin
    from src.ha.event_handler import EventHandler
    from src.ha.event_stream import HAEventStream
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
    "COMMON_SERVICES",
    "AutomationDeployer",
    "BehavioralAnalysisClient",
    "DashboardMixin",
    "EnergyDataPoint",
    "EnergyHistory",
    "EnergyHistoryClient",
    "EnergyStats",
    "EventHandler",
    "HAClient",
    "HAEventStream",
    "LogbookHistoryClient",
    "LogbookStats",
    "ParsedLogbookEntry",
    "build_condition",
    "build_delay_action",
    "build_service_action",
    "build_state_trigger",
    "build_sun_trigger",
    "build_time_trigger",
    "close_all_ha_clients",
    "discover_energy_sensors",
    "get_energy_history",
    "get_ha_client",
    "get_ha_client_async",
    "get_logbook_stats",
    "infer_areas_from_entities",
    "infer_devices_from_entities",
    "parse_automation_list",
    "parse_domain_summary",
    "parse_entity",
    "parse_entity_list",
    "parse_logbook_entry",
    "parse_logbook_list",
    "parse_system_overview",
]
