"""Unit tests for BehavioralAnalysisClient.

Tests behavioral analysis patterns, automation gaps, correlations, etc.
All tests mock HA client responses.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ha.behavioral import BehavioralAnalysisClient
from src.ha.parsers import ParsedLogbookEntry


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client."""
    client = MagicMock()
    client.list_automations = AsyncMock(return_value=[])
    client.get_logbook = AsyncMock(return_value=[])
    return client


@pytest.fixture
def behavioral_client(mock_ha_client):
    """Create a BehavioralAnalysisClient with mocked HA client."""
    return BehavioralAnalysisClient(mock_ha_client)


@pytest.fixture
def sample_logbook_entry():
    """Create a sample parsed logbook entry."""
    entry = ParsedLogbookEntry(
        entity_id="light.living_room",
        domain="light",
        name="Living Room Light",
        state="on",
        when=datetime.now(UTC).isoformat(),
        message="turned on",
        context_user_id="user-123",
    )
    return entry


@pytest.mark.asyncio
class TestGetButtonUsage:
    """Tests for get_button_usage method."""

    async def test_get_button_usage_groups_by_entity(
        self, behavioral_client, mock_ha_client, sample_logbook_entry
    ):
        """Test that button usage groups entries by entity."""
        mock_logbook = MagicMock()
        mock_logbook.get_manual_actions = AsyncMock(return_value=[sample_logbook_entry])

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            reports = await behavioral_client.get_button_usage(hours=168)

            assert len(reports) == 1
            assert reports[0].entity_id == "light.living_room"
            assert reports[0].total_presses == 1

    async def test_get_button_usage_calculates_avg_daily(self, behavioral_client, mock_ha_client):
        """Test that button usage calculates average daily presses."""
        entries = [
            ParsedLogbookEntry(
                entity_id="button.kitchen",
                domain="input_button",
                name="Kitchen Button",
                state="pressed",
                when=datetime.now(UTC).isoformat(),
                message="pressed",
                context_user_id="user-123",
            )
            for _ in range(14)
        ]  # 14 presses over 7 days = 2/day

        mock_logbook = MagicMock()
        mock_logbook.get_manual_actions = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            reports = await behavioral_client.get_button_usage(hours=168)

            assert len(reports) == 1
            assert reports[0].avg_daily_presses == 2.0

    async def test_get_button_usage_tracks_by_hour(self, behavioral_client, mock_ha_client):
        """Test that button usage tracks presses by hour."""
        entry = ParsedLogbookEntry(
            entity_id="button.test",
            domain="input_button",
            name="Test Button",
            state="pressed",
            when=datetime(2026, 2, 9, 14, 30, 0, tzinfo=UTC).isoformat(),
            message="pressed",
            context_user_id="user-123",
        )

        mock_logbook = MagicMock()
        mock_logbook.get_manual_actions = AsyncMock(return_value=[entry])

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            reports = await behavioral_client.get_button_usage(hours=24)

            assert reports[0].by_hour[14] == 1

    async def test_get_button_usage_sorts_by_most_active(self, behavioral_client, mock_ha_client):
        """Test that button usage sorts by most active."""
        entries = [
            ParsedLogbookEntry(
                entity_id="button.low",
                domain="input_button",
                name="Low",
                state="pressed",
                when=datetime.now(UTC).isoformat(),
                message="pressed",
                context_user_id="user-123",
            ),
            ParsedLogbookEntry(
                entity_id="button.high",
                domain="input_button",
                name="High",
                state="pressed",
                when=datetime.now(UTC).isoformat(),
                message="pressed",
                context_user_id="user-123",
            ),
        ] * 5

        mock_logbook = MagicMock()
        mock_logbook.get_manual_actions = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            reports = await behavioral_client.get_button_usage(hours=24)

            assert len(reports) == 2
            assert reports[0].total_presses >= reports[1].total_presses


@pytest.mark.asyncio
class TestGetAutomationEffectiveness:
    """Tests for get_automation_effectiveness method."""

    async def test_get_automation_effectiveness_calculates_score(
        self, behavioral_client, mock_ha_client
    ):
        """Test that automation effectiveness calculates efficiency score."""
        automation_entry = ParsedLogbookEntry(
            entity_id="automation.test",
            domain="automation",
            name="Test Automation",
            state="triggered",
            when=datetime.now(UTC).isoformat(),
            message="triggered",
            context_user_id=None,
        )
        button_entry = ParsedLogbookEntry(
            entity_id="automation.test",
            domain="button",
            name="Test Button",
            state="pressed",
            when=datetime.now(UTC).isoformat(),
            message="pressed",
            context_user_id="user-123",
        )

        entries = [automation_entry] * 8 + [button_entry] * 2  # 80% efficiency

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=entries)
        mock_ha_client.list_automations = AsyncMock(
            return_value=[{"entity_id": "automation.test", "alias": "Test Automation"}]
        )

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            reports = await behavioral_client.get_automation_effectiveness(hours=168)

            assert len(reports) == 1
            assert reports[0].automation_id == "automation.test"
            assert reports[0].trigger_count == 8
            assert reports[0].manual_override_count == 2
            assert reports[0].efficiency_score == 0.8

    async def test_get_automation_effectiveness_handles_no_overrides(
        self, behavioral_client, mock_ha_client
    ):
        """Test automation effectiveness with no manual overrides."""
        automation_entry = ParsedLogbookEntry(
            entity_id="automation.perfect",
            domain="automation",
            name="Perfect Automation",
            state="triggered",
            when=datetime.now(UTC).isoformat(),
            message="triggered",
            context_user_id=None,
        )

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=[automation_entry] * 10)
        mock_ha_client.list_automations = AsyncMock(
            return_value=[{"entity_id": "automation.perfect", "alias": "Perfect"}]
        )

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            reports = await behavioral_client.get_automation_effectiveness(hours=168)

            assert len(reports) == 1
            assert reports[0].efficiency_score == 1.0
            assert reports[0].manual_override_count == 0

    async def test_get_automation_effectiveness_sorts_by_score(
        self, behavioral_client, mock_ha_client
    ):
        """Test that automation effectiveness sorts by efficiency score."""
        # Create entries for two automations with different scores
        auto1_entry = ParsedLogbookEntry(
            entity_id="automation.low",
            domain="automation",
            name="Low Score",
            state="triggered",
            when=datetime.now(UTC).isoformat(),
            message="triggered",
            context_user_id=None,
        )
        auto2_entry = ParsedLogbookEntry(
            entity_id="automation.high",
            domain="automation",
            name="High Score",
            state="triggered",
            when=datetime.now(UTC).isoformat(),
            message="triggered",
            context_user_id=None,
        )
        override1 = ParsedLogbookEntry(
            entity_id="automation.low",
            domain="button",
            name="Override",
            state="pressed",
            when=datetime.now(UTC).isoformat(),
            message="pressed",
            context_user_id="user-123",
        )

        entries = [auto1_entry] * 2 + [override1] * 8 + [auto2_entry] * 10

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=entries)
        mock_ha_client.list_automations = AsyncMock(
            return_value=[
                {"entity_id": "automation.low", "alias": "Low"},
                {"entity_id": "automation.high", "alias": "High"},
            ]
        )

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            reports = await behavioral_client.get_automation_effectiveness(hours=168)

            assert len(reports) == 2
            # Should be sorted by efficiency score (ascending)
            assert reports[0].efficiency_score <= reports[1].efficiency_score


@pytest.mark.asyncio
class TestFindCorrelations:
    """Tests for find_correlations method."""

    async def test_find_correlations_detects_co_occurrences(
        self, behavioral_client, mock_ha_client
    ):
        """Test that find_correlations detects entities that change together."""
        # Create entries where two entities change within time window
        base_time = datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC)
        entry1 = ParsedLogbookEntry(
            entity_id="light.kitchen",
            domain="light",
            name="Kitchen Light",
            state="on",
            when=(base_time).isoformat(),
            message="turned on",
            context_user_id="user-123",
        )
        entry2 = ParsedLogbookEntry(
            entity_id="switch.kitchen",
            domain="switch",
            name="Kitchen Switch",
            state="on",
            when=(base_time.replace(second=30)).isoformat(),  # 30 seconds later
            message="turned on",
            context_user_id="user-123",
        )

        entries = [entry1, entry2] * 5  # 5 co-occurrences

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            results = await behavioral_client.find_correlations(hours=168, time_window_seconds=300)

            assert len(results) == 1
            assert results[0].entity_a in ("light.kitchen", "switch.kitchen")
            assert results[0].entity_b in ("light.kitchen", "switch.kitchen")
            assert results[0].entity_a != results[0].entity_b
            assert results[0].co_occurrence_count == 25

    async def test_find_correlations_filters_by_entity_ids(self, behavioral_client, mock_ha_client):
        """Test that find_correlations filters by entity_ids parameter."""
        entry1 = ParsedLogbookEntry(
            entity_id="light.kitchen",
            domain="light",
            name="Kitchen Light",
            state="on",
            when=datetime.now(UTC).isoformat(),
            message="turned on",
            context_user_id="user-123",
        )
        entry2 = ParsedLogbookEntry(
            entity_id="light.bedroom",
            domain="light",
            name="Bedroom Light",
            state="on",
            when=datetime.now(UTC).isoformat(),
            message="turned on",
            context_user_id="user-123",
        )

        entries = [entry1, entry2] * 5

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            results = await behavioral_client.find_correlations(
                entity_ids=["light.kitchen"], hours=168
            )

            # Should only find correlations involving light.kitchen
            # Since we filtered to only kitchen, no correlations should be found
            # (need at least 2 different entities)
            assert len(results) == 0

    async def test_find_correlations_requires_minimum_co_occurrences(
        self, behavioral_client, mock_ha_client
    ):
        """Test that find_correlations requires minimum 3 co-occurrences."""
        base_time = datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC)
        entry1 = ParsedLogbookEntry(
            entity_id="light.a",
            domain="light",
            name="Light A",
            state="on",
            when=base_time.isoformat(),
            message="turned on",
            context_user_id="user-123",
        )
        entry2 = ParsedLogbookEntry(
            entity_id="light.b",
            domain="light",
            name="Light B",
            state="on",
            when=(base_time.replace(second=10)).isoformat(),
            message="turned on",
            context_user_id="user-123",
        )

        # Only 2 co-occurrences - should not be included
        entries = [entry1, entry2]

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            results = await behavioral_client.find_correlations(hours=168)

            assert len(results) == 0


@pytest.mark.asyncio
class TestDetectAutomationGaps:
    """Tests for detect_automation_gaps method."""

    async def test_detect_automation_gaps_finds_recurring_patterns(
        self, behavioral_client, mock_ha_client
    ):
        """Test that detect_automation_gaps finds recurring manual patterns."""
        # Create entries for same entity at same hour multiple times
        base_time = datetime(2026, 2, 9, 22, 0, 0, tzinfo=UTC)
        entries = [
            ParsedLogbookEntry(
                entity_id="light.bedroom",
                domain="light",
                name="Bedroom Light",
                state="off",
                when=(base_time.replace(day=day)).isoformat(),
                message="turned off",
                context_user_id="user-123",
            )
            for day in range(1, 6)  # 5 occurrences
        ]

        mock_logbook = MagicMock()
        mock_logbook.get_manual_actions = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            gaps = await behavioral_client.detect_automation_gaps(hours=168, min_occurrences=3)

            assert len(gaps) == 1
            assert gaps[0].entities == ["light.bedroom"]
            assert gaps[0].occurrence_count == 5
            assert gaps[0].typical_time == "22:00"
            assert "light.bedroom" in gaps[0].pattern_description

    async def test_detect_automation_gaps_filters_by_min_occurrences(
        self, behavioral_client, mock_ha_client
    ):
        """Test that detect_automation_gaps filters by minimum occurrences."""
        base_time = datetime(2026, 2, 9, 22, 0, 0, tzinfo=UTC)
        entries = [
            ParsedLogbookEntry(
                entity_id="light.test",
                domain="light",
                name="Test Light",
                state="off",
                when=(base_time.replace(day=day)).isoformat(),
                message="turned off",
                context_user_id="user-123",
            )
            for day in range(1, 3)  # Only 2 occurrences
        ]

        mock_logbook = MagicMock()
        mock_logbook.get_manual_actions = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            gaps = await behavioral_client.detect_automation_gaps(hours=168, min_occurrences=3)

            assert len(gaps) == 0

    async def test_detect_automation_gaps_sorts_by_occurrence_count(
        self, behavioral_client, mock_ha_client
    ):
        """Test that detect_automation_gaps sorts by occurrence count."""
        base_time = datetime(2026, 2, 9, 22, 0, 0, tzinfo=UTC)
        entries = [
            ParsedLogbookEntry(
                entity_id="light.low",
                domain="light",
                name="Low",
                state="off",
                when=(base_time.replace(day=day)).isoformat(),
                message="turned off",
                context_user_id="user-123",
            )
            for day in range(1, 4)  # 3 occurrences
        ] + [
            ParsedLogbookEntry(
                entity_id="light.high",
                domain="light",
                name="High",
                state="off",
                when=(base_time.replace(day=day)).isoformat(),
                message="turned off",
                context_user_id="user-123",
            )
            for day in range(1, 6)  # 5 occurrences
        ]

        mock_logbook = MagicMock()
        mock_logbook.get_manual_actions = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            gaps = await behavioral_client.detect_automation_gaps(hours=168, min_occurrences=3)

            assert len(gaps) == 2
            assert gaps[0].occurrence_count >= gaps[1].occurrence_count


@pytest.mark.asyncio
class TestGetDeviceHealthReport:
    """Tests for get_device_health_report method."""

    async def test_get_device_health_report_identifies_healthy_devices(
        self, behavioral_client, mock_ha_client
    ):
        """Test that device health report identifies healthy devices."""
        entries = [
            ParsedLogbookEntry(
                entity_id="sensor.temperature",
                domain="sensor",
                name="Temperature",
                state="20.5",
                when=datetime.now(UTC).isoformat(),
                message="changed",
                context_user_id=None,
            )
            for _ in range(10)  # Healthy: many state changes
        ]

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            health_entries = await behavioral_client.get_device_health_report(hours=48)

            assert len(health_entries) == 1
            assert health_entries[0].status == "healthy"
            assert health_entries[0].state_change_count == 10

    async def test_get_device_health_report_identifies_degraded_devices(
        self, behavioral_client, mock_ha_client
    ):
        """Test that device health report identifies degraded devices."""
        # Only 1 state change in 48 hours - degraded
        entry = ParsedLogbookEntry(
            entity_id="sensor.stuck",
            domain="sensor",
            name="Stuck Sensor",
            state="20.0",
            when=datetime.now(UTC).isoformat(),
            message="changed",
            context_user_id=None,
        )

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=[entry])

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            health_entries = await behavioral_client.get_device_health_report(hours=48)

            assert len(health_entries) == 1
            assert health_entries[0].status == "degraded"
            assert (
                "Only 1 state change" in health_entries[0].issue or health_entries[0].issue is None
            )

    async def test_get_device_health_report_identifies_unresponsive_devices(
        self, behavioral_client, mock_ha_client
    ):
        """Test that device health report identifies unresponsive devices."""
        entries = [
            ParsedLogbookEntry(
                entity_id="sensor.bad",
                domain="sensor",
                name="Bad Sensor",
                state="unavailable",
                when=datetime.now(UTC).isoformat(),
                message="changed",
                context_user_id=None,
            )
            for _ in range(5)
        ] + [
            ParsedLogbookEntry(
                entity_id="sensor.bad",
                domain="sensor",
                name="Bad Sensor",
                state="20.0",
                when=datetime.now(UTC).isoformat(),
                message="changed",
                context_user_id=None,
            )
            for _ in range(5)
        ]  # 50% unavailable

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            health_entries = await behavioral_client.get_device_health_report(hours=48)

            assert len(health_entries) == 1
            assert health_entries[0].status == "unresponsive"
            assert "unavailable" in health_entries[0].issue.lower()

    async def test_get_device_health_report_sorts_unhealthy_first(
        self, behavioral_client, mock_ha_client
    ):
        """Test that device health report sorts unhealthy devices first."""
        healthy_entry = ParsedLogbookEntry(
            entity_id="sensor.healthy",
            domain="sensor",
            name="Healthy",
            state="20.0",
            when=datetime.now(UTC).isoformat(),
            message="changed",
            context_user_id=None,
        )
        degraded_entry = ParsedLogbookEntry(
            entity_id="sensor.degraded",
            domain="sensor",
            name="Degraded",
            state="20.0",
            when=datetime.now(UTC).isoformat(),
            message="changed",
            context_user_id=None,
        )

        entries = [healthy_entry] * 10 + [degraded_entry]

        mock_logbook = MagicMock()
        mock_logbook.get_entries = AsyncMock(return_value=entries)

        with patch.object(behavioral_client, "_logbook", mock_logbook):
            health_entries = await behavioral_client.get_device_health_report(hours=48)

            assert len(health_entries) == 2
            # Unhealthy should come first (degraded < healthy in priority)
            priority = {"unresponsive": 0, "anomalous": 1, "degraded": 2, "healthy": 3}
            assert priority.get(health_entries[0].status, 99) <= priority.get(
                health_entries[1].status, 99
            )
