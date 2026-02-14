"""Data collection for Data Scientist agent."""

import logging
from typing import TYPE_CHECKING, cast

from src.dal import EntityRepository
from src.graph.state import AnalysisState, AnalysisType
from src.ha import EnergyHistoryClient, HAClient
from src.ha.behavioral import BehavioralAnalysisClient
from src.tracing import log_metric, log_param

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def discover_energy_sensors_from_db(
    session: "AsyncSession | None",
) -> list[str]:
    """Discover energy sensors from the local database.

    Queries the synced entities table instead of making MCP calls.
    Much faster and doesn't require HA to be available.

    Args:
        session: Database session

    Returns:
        List of energy sensor entity IDs
    """
    if not session:
        return []

    try:
        repo = EntityRepository(session)

        # Get all sensor entities
        sensors = await repo.list_all(domain="sensor", limit=500)

        # Filter for energy-related sensors
        # Energy device classes: energy, power
        # Energy units: kWh, Wh, MWh, W, kW, MW
        energy_device_classes = {"energy", "power"}
        energy_units = {"kWh", "Wh", "MWh", "W", "kW", "MW"}

        energy_sensors = []
        for entity in sensors:
            attrs = entity.attributes or {}
            device_class = attrs.get("device_class", "")
            unit = attrs.get("unit_of_measurement", "")

            is_energy = device_class in energy_device_classes or unit in energy_units

            if is_energy:
                energy_sensors.append(entity.entity_id)

        return energy_sensors[:20]  # Limit to 20

    except Exception as e:
        # Log but don't fail - will fall back to MCP
        logger.warning(f"Failed to discover energy sensors from DB: {e}")
        return []


async def collect_energy_data(
    state: AnalysisState,
    ha_client: HAClient,
    session: "AsyncSession | None" = None,
) -> dict[str, object]:
    """Collect energy data for analysis.

    Uses local database for entity discovery (faster, no MCP overhead),
    then falls back to MCP only for historical data which isn't stored locally.

    In diagnostic mode, entity_ids are expected to be pre-supplied by the
    Architect, and diagnostic_context is included in the returned data.

    Args:
        state: Analysis state with entity IDs and time range
        ha_client: Home Assistant client
        session: Database session for entity lookups

    Returns:
        Energy data for analysis
    """
    entity_ids = state.entity_ids

    # If no specific entities, discover energy sensors from DB first
    if not entity_ids:
        entity_ids = await discover_energy_sensors_from_db(session)
        log_param("discovered_sensors", len(entity_ids))
        log_param("discovery_source", "database" if entity_ids else "mcp")

    # If DB discovery failed or returned nothing, fall back to MCP
    if not entity_ids:
        energy_client = EnergyHistoryClient(ha_client)
        sensors = await energy_client.get_energy_sensors()
        entity_ids = [s["entity_id"] for s in sensors[:20]]
        log_param("discovered_sensors", len(entity_ids))
        log_param("discovery_source", "mcp_fallback")

    # Collect historical data via MCP (not stored locally)
    energy_client = EnergyHistoryClient(ha_client)
    data = await energy_client.get_aggregated_energy(
        entity_ids,
        hours=state.time_range_hours,
    )

    log_metric("energy.total_kwh", data.get("total_kwh", 0.0))
    log_metric("energy.sensor_count", float(len(entity_ids)))

    # In diagnostic mode, include the Architect's evidence in the data
    if state.analysis_type == AnalysisType.DIAGNOSTIC and state.diagnostic_context:
        data["diagnostic_context"] = state.diagnostic_context
        log_param("diagnostic_mode", True)

    return data


async def collect_behavioral_data(
    state: AnalysisState,
    ha_client: HAClient,
) -> dict[str, object]:
    """Collect behavioral data from logbook for analysis.

    Uses the BehavioralAnalysisClient to gather button usage,
    automation effectiveness, correlations, gaps, and device health.

    Args:
        state: Analysis state with type and time range
        ha_client: Home Assistant client

    Returns:
        Behavioral data for analysis
    """
    behavioral = BehavioralAnalysisClient(ha_client)
    hours = state.time_range_hours
    # Collect entities list to maintain consistent top-level structure
    # with energy data (scripts expect data['entities']).
    entities: list[dict[str, object]] = []
    data: dict[str, object] = {
        "analysis_type": state.analysis_type.value,
        "hours": hours,
    }

    try:
        if state.analysis_type == AnalysisType.BEHAVIOR_ANALYSIS:
            button_usage = await behavioral.get_button_usage(hours=hours)
            entities = [
                {
                    "entity_id": r.entity_id,
                    "total_presses": r.total_presses,
                    "avg_daily": r.avg_daily_presses,
                    "by_hour": dict(r.by_hour),
                }
                for r in button_usage[:30]
            ]
            data["button_usage"] = entities
            data["entity_count"] = len(button_usage)

        elif state.analysis_type == AnalysisType.AUTOMATION_ANALYSIS:
            effectiveness = await behavioral.get_automation_effectiveness(hours=hours)
            entities = [
                {
                    "automation_id": r.automation_id,
                    "alias": r.alias,
                    "trigger_count": r.trigger_count,
                    "manual_overrides": r.manual_override_count,
                    "efficiency_score": r.efficiency_score,
                }
                for r in effectiveness
            ]
            data["automation_effectiveness"] = entities
            data["entity_count"] = len(effectiveness)

        elif state.analysis_type == AnalysisType.AUTOMATION_GAP_DETECTION:
            gaps = await behavioral.detect_automation_gaps(hours=hours)
            entities = [
                {
                    "description": g.pattern_description,
                    "entities": g.entities,
                    "occurrences": g.occurrence_count,
                    "typical_time": g.typical_time,
                    "confidence": g.confidence,
                }
                for g in gaps
            ]
            data["automation_gaps"] = entities
            data["entity_count"] = len(gaps)

        elif state.analysis_type == AnalysisType.CORRELATION_DISCOVERY:
            correlations = await behavioral.find_correlations(
                entity_ids=state.entity_ids or None,
                hours=hours,
            )
            entities = [
                {
                    "entity_a": c.entity_a,
                    "entity_b": c.entity_b,
                    "co_occurrences": c.co_occurrence_count,
                    "avg_delta_seconds": c.avg_time_delta_seconds,
                    "confidence": c.confidence,
                }
                for c in correlations
            ]
            data["correlations"] = entities
            data["entity_count"] = len(correlations)

        elif state.analysis_type == AnalysisType.DEVICE_HEALTH:
            health = await behavioral.get_device_health_report(hours=hours)
            entities = [
                {
                    "entity_id": h.entity_id,
                    "status": h.status,
                    "last_seen": h.last_seen,
                    "issue": h.issue,
                    "state_changes": h.state_change_count,
                }
                for h in health
            ]
            data["device_health"] = entities
            data["entity_count"] = len(health)

        else:
            # Cost optimization or generic behavioral - gather everything
            stats = await behavioral._logbook.get_stats(hours=hours)
            data["logbook_stats"] = {
                "total_entries": stats.total_entries,
                "by_action_type": stats.by_action_type,
                "by_domain": stats.by_domain,
                "automation_triggers": stats.automation_triggers,
                "manual_actions": stats.manual_actions,
                "unique_entities": stats.unique_entities,
                "by_hour": dict(stats.by_hour),
            }
            data["entity_count"] = stats.unique_entities

        log_metric("behavioral.entity_count", float(cast("float", data.get("entity_count", 0))))
        log_param("behavioral.analysis_type", state.analysis_type.value)

    except Exception as e:
        logger.warning(f"Error collecting behavioral data: {e}")
        data["error"] = str(e)

    # Always provide top-level 'entities' key for consistency with
    # energy data structure — scripts rely on data['entities'].
    data["entities"] = entities
    return data
