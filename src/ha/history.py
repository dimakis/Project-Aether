"""Energy-specific history aggregation for Data Science team analysis.

User Story 3: Energy Optimization Suggestions.

Wraps the base HA get_history with energy-specific filtering,
aggregation, and statistical calculations.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from src.ha.client import HAClient

logger = logging.getLogger(__name__)


@dataclass
class EnergyDataPoint:
    """Single energy reading."""

    timestamp: datetime
    value: float
    unit: str = "kWh"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "unit": self.unit,
        }


@dataclass
class EnergyStats:
    """Statistical summary of energy data."""

    total: float = 0.0
    average: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    count: int = 0
    unit: str = "kWh"

    # Peak usage tracking
    peak_value: float = 0.0
    peak_timestamp: datetime | None = None

    # Daily aggregates
    daily_totals: dict[str, float] = field(default_factory=dict)
    hourly_averages: dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total": self.total,
            "average": self.average,
            "min": self.min_value,
            "max": self.max_value,
            "count": self.count,
            "unit": self.unit,
            "peak_value": self.peak_value,
            "peak_timestamp": self.peak_timestamp.isoformat() if self.peak_timestamp else None,
            "daily_totals": self.daily_totals,
            "hourly_averages": self.hourly_averages,
        }


@dataclass
class EnergyHistory:
    """Complete energy history with data points and statistics."""

    entity_id: str
    friendly_name: str | None
    device_class: str | None
    unit: str
    data_points: list[EnergyDataPoint]
    stats: EnergyStats
    start_time: datetime
    end_time: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entity_id": self.entity_id,
            "friendly_name": self.friendly_name,
            "device_class": self.device_class,
            "unit": self.unit,
            "data_points": [dp.to_dict() for dp in self.data_points],
            "stats": self.stats.to_dict(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }


class EnergyHistoryClient:
    """Client for fetching and aggregating energy sensor history.

    Wraps HAClient.get_history with energy-specific functionality:
    - Filtering by device_class (energy, power)
    - Unit conversion (W, kW, Wh, kWh)
    - Statistical aggregation (sum, average, peak)
    - Daily/hourly breakdowns
    """

    # Energy-related device classes (excluding battery - those are percentages, not power)
    ENERGY_DEVICE_CLASSES = {"energy", "power"}

    # Energy units and their conversions to kWh
    UNIT_CONVERSIONS = {
        "kWh": 1.0,
        "Wh": 0.001,
        "MWh": 1000.0,
        "W": None,  # Power, needs time integration
        "kW": None,
        "MW": None,
    }

    def __init__(self, ha_client: HAClient):
        """Initialize with HA client.

        Args:
            ha_client: HA client for HA communication
        """
        self.ha = ha_client

    async def get_energy_history(
        self,
        entity_id: str,
        hours: int = 24,
    ) -> EnergyHistory:
        """Get energy history for a specific entity.

        Args:
            entity_id: Energy sensor entity ID
            hours: Hours of history to fetch

        Returns:
            EnergyHistory with data points and statistics
        """
        # Get entity details for metadata
        entity_info = await self.ha.get_entity(entity_id, detailed=True)

        # Get raw history
        history = await self.ha.get_history(entity_id, hours=hours)

        # HAClient uses "attributes" key for detailed entity info
        attrs = entity_info.get("attributes", {})

        # Parse into data points
        data_points = self._parse_history_to_datapoints(
            history.get("states", []),
            attrs.get("unit_of_measurement", "kWh"),
        )

        # Calculate statistics
        stats = self._calculate_stats(data_points)

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=hours)

        return EnergyHistory(
            entity_id=entity_id,
            friendly_name=attrs.get("friendly_name"),
            device_class=attrs.get("device_class"),
            unit=attrs.get("unit_of_measurement", "kWh"),
            data_points=data_points,
            stats=stats,
            start_time=start_time,
            end_time=end_time,
        )

    async def get_energy_sensors(
        self,
        domain: str = "sensor",
    ) -> list[dict[str, Any]]:
        """Discover all energy sensors.

        Args:
            domain: Domain to search (default: sensor)

        Returns:
            List of energy sensor entities
        """
        # Get all sensors (list_entities returns a list directly)
        entities = await self.ha.list_entities(domain=domain, detailed=True, limit=500)

        # Filter for energy-related sensors
        energy_sensors = []
        for entity in entities:
            # HAClient uses "attributes" key for detailed entity info
            attrs = entity.get("attributes", {})
            device_class = attrs.get("device_class", "")
            unit = attrs.get("unit_of_measurement", "")

            # Check if it's an energy sensor
            is_energy = device_class in self.ENERGY_DEVICE_CLASSES or unit in self.UNIT_CONVERSIONS

            if is_energy:
                energy_sensors.append(
                    {
                        "entity_id": entity.get("entity_id"),
                        "friendly_name": attrs.get("friendly_name"),
                        "device_class": device_class,
                        "unit": unit,
                        "state": entity.get("state"),
                    }
                )

        return energy_sensors

    async def get_aggregated_energy(
        self,
        entity_ids: list[str],
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get aggregated energy data for multiple entities.

        Args:
            entity_ids: List of entity IDs to aggregate
            hours: Hours of history

        Returns:
            Aggregated energy data with per-entity and total stats
        """
        histories = []
        for entity_id in entity_ids:
            try:
                history = await self.get_energy_history(entity_id, hours)
                histories.append(history)
            except Exception:
                logger.debug(
                    "Failed to get energy history for entity %s, skipping", entity_id, exc_info=True
                )
                continue

        if not histories:
            return {
                "entities": [],
                "total_kwh": 0.0,
                "average_kwh": 0.0,
                "hours": hours,
            }

        # Aggregate totals
        total_kwh = sum(h.stats.total for h in histories)

        return {
            "entities": [h.to_dict() for h in histories],
            "total_kwh": total_kwh,
            "average_kwh": total_kwh / len(histories) if histories else 0.0,
            "entity_count": len(histories),
            "hours": hours,
            "by_entity": {h.entity_id: h.stats.total for h in histories},
        }

    async def get_daily_breakdown(
        self,
        entity_id: str,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get daily energy breakdown.

        Args:
            entity_id: Energy sensor entity ID
            days: Number of days to analyze

        Returns:
            Daily breakdown with totals per day
        """
        history = await self.get_energy_history(entity_id, hours=days * 24)

        return {
            "entity_id": entity_id,
            "days": days,
            "daily_totals": history.stats.daily_totals,
            "total": history.stats.total,
            "average_daily": history.stats.total / days if days > 0 else 0.0,
        }

    async def get_peak_usage(
        self,
        entity_id: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get peak usage information.

        Args:
            entity_id: Energy sensor entity ID
            hours: Hours to analyze

        Returns:
            Peak usage data
        """
        history = await self.get_energy_history(entity_id, hours)

        return {
            "entity_id": entity_id,
            "peak_value": history.stats.peak_value,
            "peak_timestamp": history.stats.peak_timestamp.isoformat()
            if history.stats.peak_timestamp
            else None,
            "average": history.stats.average,
            "peak_to_average_ratio": (
                history.stats.peak_value / history.stats.average
                if history.stats.average > 0
                else 0.0
            ),
        }

    def _parse_history_to_datapoints(
        self,
        states: list[dict[str, Any]],
        unit: str,
    ) -> list[EnergyDataPoint]:
        """Parse raw history states into EnergyDataPoints.

        Args:
            states: Raw state list from history
            unit: Unit of measurement

        Returns:
            List of EnergyDataPoints
        """
        data_points = []

        for state in states:
            state_value = state.get("state")
            timestamp_str = state.get("last_changed")

            # Skip unavailable/unknown states
            if state_value in ("unavailable", "unknown", None):
                continue

            try:
                value = float(state_value)
                if timestamp_str is not None:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    data_points.append(
                        EnergyDataPoint(
                            timestamp=timestamp,
                            value=value,
                            unit=unit,
                        )
                    )
            except (ValueError, TypeError):
                # Skip invalid values
                continue

        return data_points

    def _calculate_stats(
        self,
        data_points: list[EnergyDataPoint],
    ) -> EnergyStats:
        """Calculate statistics from data points.

        Args:
            data_points: List of energy data points

        Returns:
            EnergyStats with aggregated values
        """
        if not data_points:
            return EnergyStats()

        values = [dp.value for dp in data_points]
        unit = data_points[0].unit if data_points else "kWh"

        # Basic stats
        total = sum(values)
        average = total / len(values)
        min_value = min(values)
        max_value = max(values)

        # Find peak
        peak_idx = values.index(max_value)
        peak_timestamp = data_points[peak_idx].timestamp

        # Daily aggregates
        daily_totals: dict[str, float] = {}
        for dp in data_points:
            day_key = dp.timestamp.strftime("%Y-%m-%d")
            daily_totals[day_key] = daily_totals.get(day_key, 0.0) + dp.value

        # Hourly averages
        hourly_sums: dict[int, list[float]] = {}
        for dp in data_points:
            hour = dp.timestamp.hour
            if hour not in hourly_sums:
                hourly_sums[hour] = []
            hourly_sums[hour].append(dp.value)

        hourly_averages = {hour: sum(vals) / len(vals) for hour, vals in hourly_sums.items()}

        return EnergyStats(
            total=total,
            average=average,
            min_value=min_value,
            max_value=max_value,
            count=len(values),
            unit=unit,
            peak_value=max_value,
            peak_timestamp=peak_timestamp,
            daily_totals=daily_totals,
            hourly_averages=hourly_averages,
        )


# Convenience function for quick access
async def get_energy_history(
    ha_client: HAClient,
    entity_id: str,
    hours: int = 24,
) -> EnergyHistory:
    """Get energy history for an entity.

    Args:
        ha_client: HA client instance
        entity_id: Energy sensor entity ID
        hours: Hours of history

    Returns:
        EnergyHistory with data and statistics
    """
    client = EnergyHistoryClient(ha_client)
    return await client.get_energy_history(entity_id, hours)


async def discover_energy_sensors(
    ha_client: HAClient,
) -> list[dict[str, Any]]:
    """Discover all energy sensors.

    Args:
        ha_client: HA client instance

    Returns:
        List of energy sensor details
    """
    client = EnergyHistoryClient(ha_client)
    return await client.get_energy_sensors()
