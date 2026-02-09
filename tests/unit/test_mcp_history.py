"""Unit tests for MCP energy history module.

Tests EnergyHistoryClient with mocked HA client.
Constitution: Reliability & Quality - comprehensive testing.

TDD: T106 - History data parsing tests.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.ha.history import (
    EnergyDataPoint,
    EnergyHistory,
    EnergyHistoryClient,
    EnergyStats,
    discover_energy_sensors,
    get_energy_history,
)


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client."""
    client = AsyncMock()
    client.get_history = AsyncMock()
    client.get_entity = AsyncMock()
    client.list_entities = AsyncMock()
    return client


@pytest.fixture
def energy_client(mock_ha_client):
    """Create EnergyHistoryClient with mock HA client."""
    return EnergyHistoryClient(mock_ha_client)


@pytest.fixture
def sample_history_states():
    """Create sample history states from HA."""
    now = datetime.now(UTC)
    return [
        {"state": "1.5", "last_changed": (now - timedelta(hours=3)).isoformat()},
        {"state": "2.0", "last_changed": (now - timedelta(hours=2)).isoformat()},
        {"state": "1.8", "last_changed": (now - timedelta(hours=1)).isoformat()},
        {"state": "2.5", "last_changed": now.isoformat()},
    ]


@pytest.fixture
def sample_entity_info():
    """Create sample entity info matching HAClient.get_entity(detailed=True) format."""
    return {
        "entity_id": "sensor.grid_power",
        "state": "2.5",
        "attributes": {
            "friendly_name": "Grid Power",
            "device_class": "energy",
            "unit_of_measurement": "kWh",
        },
    }


class TestEnergyDataPoint:
    """Tests for EnergyDataPoint dataclass."""

    def test_create_datapoint(self):
        """Test creating an energy data point."""
        now = datetime.now(UTC)
        dp = EnergyDataPoint(timestamp=now, value=1.5, unit="kWh")

        assert dp.timestamp == now
        assert dp.value == 1.5
        assert dp.unit == "kWh"

    def test_to_dict(self):
        """Test converting datapoint to dict."""
        now = datetime.now(UTC)
        dp = EnergyDataPoint(timestamp=now, value=2.0, unit="kWh")

        result = dp.to_dict()

        assert result["value"] == 2.0
        assert result["unit"] == "kWh"
        assert "timestamp" in result


class TestEnergyStats:
    """Tests for EnergyStats dataclass."""

    def test_default_stats(self):
        """Test default stats values."""
        stats = EnergyStats()

        assert stats.total == 0.0
        assert stats.average == 0.0
        assert stats.count == 0
        assert stats.unit == "kWh"

    def test_to_dict(self):
        """Test converting stats to dict."""
        stats = EnergyStats(
            total=10.0,
            average=2.5,
            min_value=1.0,
            max_value=4.0,
            count=4,
            peak_value=4.0,
        )

        result = stats.to_dict()

        assert result["total"] == 10.0
        assert result["average"] == 2.5
        assert result["min"] == 1.0
        assert result["max"] == 4.0
        assert result["count"] == 4


class TestEnergyHistoryClientParsing:
    """Tests for history parsing methods."""

    def test_parse_history_to_datapoints(self, energy_client, sample_history_states):
        """Test parsing raw history to datapoints."""
        datapoints = energy_client._parse_history_to_datapoints(sample_history_states, "kWh")

        assert len(datapoints) == 4
        assert all(isinstance(dp, EnergyDataPoint) for dp in datapoints)
        assert datapoints[0].value == 1.5
        assert datapoints[3].value == 2.5

    def test_parse_skips_unavailable(self, energy_client):
        """Test that unavailable states are skipped."""
        states = [
            {"state": "1.5", "last_changed": datetime.now(UTC).isoformat()},
            {"state": "unavailable", "last_changed": datetime.now(UTC).isoformat()},
            {"state": "unknown", "last_changed": datetime.now(UTC).isoformat()},
            {"state": "2.0", "last_changed": datetime.now(UTC).isoformat()},
        ]

        datapoints = energy_client._parse_history_to_datapoints(states, "kWh")

        assert len(datapoints) == 2

    def test_parse_skips_invalid_values(self, energy_client):
        """Test that invalid numeric values are skipped."""
        states = [
            {"state": "1.5", "last_changed": datetime.now(UTC).isoformat()},
            {"state": "not_a_number", "last_changed": datetime.now(UTC).isoformat()},
            {"state": "2.0", "last_changed": datetime.now(UTC).isoformat()},
        ]

        datapoints = energy_client._parse_history_to_datapoints(states, "kWh")

        assert len(datapoints) == 2


class TestEnergyHistoryClientStats:
    """Tests for statistics calculation."""

    def test_calculate_stats_basic(self, energy_client):
        """Test basic statistics calculation."""
        now = datetime.now(UTC)
        datapoints = [
            EnergyDataPoint(timestamp=now - timedelta(hours=2), value=1.0, unit="kWh"),
            EnergyDataPoint(timestamp=now - timedelta(hours=1), value=2.0, unit="kWh"),
            EnergyDataPoint(timestamp=now, value=3.0, unit="kWh"),
        ]

        stats = energy_client._calculate_stats(datapoints)

        assert stats.total == 6.0
        assert stats.average == 2.0
        assert stats.min_value == 1.0
        assert stats.max_value == 3.0
        assert stats.count == 3
        assert stats.peak_value == 3.0

    def test_calculate_stats_empty(self, energy_client):
        """Test stats with empty datapoints."""
        stats = energy_client._calculate_stats([])

        assert stats.total == 0.0
        assert stats.count == 0

    def test_calculate_stats_daily_totals(self, energy_client):
        """Test daily totals calculation."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)

        datapoints = [
            EnergyDataPoint(timestamp=yesterday, value=1.0, unit="kWh"),
            EnergyDataPoint(timestamp=yesterday + timedelta(hours=1), value=1.5, unit="kWh"),
            EnergyDataPoint(timestamp=now, value=2.0, unit="kWh"),
        ]

        stats = energy_client._calculate_stats(datapoints)

        assert len(stats.daily_totals) == 2

    def test_calculate_stats_hourly_averages(self, energy_client):
        """Test hourly averages calculation."""
        now = datetime.now(UTC).replace(hour=14, minute=0, second=0)

        datapoints = [
            EnergyDataPoint(timestamp=now, value=1.0, unit="kWh"),
            EnergyDataPoint(timestamp=now + timedelta(minutes=30), value=2.0, unit="kWh"),
        ]

        stats = energy_client._calculate_stats(datapoints)

        assert 14 in stats.hourly_averages
        assert stats.hourly_averages[14] == 1.5


class TestEnergyHistoryClientGetHistory:
    """Tests for get_energy_history method."""

    @pytest.mark.asyncio
    async def test_get_energy_history(
        self, energy_client, mock_ha_client, sample_history_states, sample_entity_info
    ):
        """Test getting energy history for an entity."""
        mock_ha_client.get_entity.return_value = sample_entity_info
        mock_ha_client.get_history.return_value = {
            "entity_id": "sensor.grid_power",
            "states": sample_history_states,
            "count": 4,
        }

        result = await energy_client.get_energy_history("sensor.grid_power", hours=24)

        assert isinstance(result, EnergyHistory)
        assert result.entity_id == "sensor.grid_power"
        assert result.friendly_name == "Grid Power"
        assert result.device_class == "energy"
        assert len(result.data_points) == 4
        assert result.stats.count == 4


class TestEnergyHistoryClientDiscovery:
    """Tests for energy sensor discovery."""

    @pytest.mark.asyncio
    async def test_get_energy_sensors(self, energy_client, mock_ha_client):
        """Test discovering energy sensors."""
        mock_ha_client.list_entities.return_value = [
            {
                "entity_id": "sensor.grid_power",
                "state": "1.5",
                "attributes": {
                    "friendly_name": "Grid Power",
                    "device_class": "energy",
                    "unit_of_measurement": "kWh",
                },
            },
            {
                "entity_id": "sensor.temperature",
                "state": "22",
                "attributes": {
                    "friendly_name": "Temperature",
                    "device_class": "temperature",
                    "unit_of_measurement": "°C",
                },
            },
            {
                "entity_id": "sensor.solar_power",
                "state": "0.5",
                "attributes": {
                    "friendly_name": "Solar Power",
                    "device_class": "power",
                    "unit_of_measurement": "W",
                },
            },
        ]

        result = await energy_client.get_energy_sensors()

        # Should find grid_power (energy) and solar_power (power), not temperature
        assert len(result) == 2
        entity_ids = [e["entity_id"] for e in result]
        assert "sensor.grid_power" in entity_ids
        assert "sensor.solar_power" in entity_ids
        assert "sensor.temperature" not in entity_ids


class TestEnergyHistoryClientAggregation:
    """Tests for aggregation methods."""

    @pytest.mark.asyncio
    async def test_get_aggregated_energy(
        self, energy_client, mock_ha_client, sample_history_states, sample_entity_info
    ):
        """Test aggregating energy across multiple entities."""
        mock_ha_client.get_entity.return_value = sample_entity_info
        mock_ha_client.get_history.return_value = {
            "entity_id": "sensor.grid_power",
            "states": sample_history_states,
            "count": 4,
        }

        result = await energy_client.get_aggregated_energy(
            ["sensor.grid_power", "sensor.solar_power"],
            hours=24,
        )

        assert "total_kwh" in result
        assert "entities" in result
        assert result["hours"] == 24

    @pytest.mark.asyncio
    async def test_get_daily_breakdown(
        self, energy_client, mock_ha_client, sample_history_states, sample_entity_info
    ):
        """Test getting daily breakdown."""
        mock_ha_client.get_entity.return_value = sample_entity_info
        mock_ha_client.get_history.return_value = {
            "entity_id": "sensor.grid_power",
            "states": sample_history_states,
            "count": 4,
        }

        result = await energy_client.get_daily_breakdown("sensor.grid_power", days=7)

        assert result["entity_id"] == "sensor.grid_power"
        assert result["days"] == 7
        assert "daily_totals" in result

    @pytest.mark.asyncio
    async def test_get_peak_usage(
        self, energy_client, mock_ha_client, sample_history_states, sample_entity_info
    ):
        """Test getting peak usage information."""
        mock_ha_client.get_entity.return_value = sample_entity_info
        mock_ha_client.get_history.return_value = {
            "entity_id": "sensor.grid_power",
            "states": sample_history_states,
            "count": 4,
        }

        result = await energy_client.get_peak_usage("sensor.grid_power", hours=24)

        assert result["entity_id"] == "sensor.grid_power"
        assert "peak_value" in result
        assert "peak_timestamp" in result
        assert "peak_to_average_ratio" in result


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_get_energy_history_function(
        self, mock_ha_client, sample_history_states, sample_entity_info
    ):
        """Test get_energy_history convenience function."""
        mock_ha_client.get_entity.return_value = sample_entity_info
        mock_ha_client.get_history.return_value = {
            "entity_id": "sensor.grid_power",
            "states": sample_history_states,
            "count": 4,
        }

        result = await get_energy_history(mock_ha_client, "sensor.grid_power", hours=24)

        assert isinstance(result, EnergyHistory)
        assert result.entity_id == "sensor.grid_power"

    @pytest.mark.asyncio
    async def test_discover_energy_sensors_function(self, mock_ha_client):
        """Test discover_energy_sensors convenience function."""
        mock_ha_client.list_entities.return_value = [
            {
                "entity_id": "sensor.grid_power",
                "state": "1.5",
                "attributes": {
                    "device_class": "energy",
                    "unit_of_measurement": "kWh",
                },
            },
        ]

        result = await discover_energy_sensors(mock_ha_client)

        assert len(result) == 1
        assert result[0]["entity_id"] == "sensor.grid_power"
