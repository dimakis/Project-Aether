"""Unit tests for automation gap detection logic.

Tests the gap detection algorithm in BehavioralAnalysisClient.
Constitution: Reliability & Quality.

TDD: T235 - Gap detection logic tests.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.ha.behavioral import AutomationGap, BehavioralAnalysisClient


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client."""
    return AsyncMock()


@pytest.fixture
def behavioral_client(mock_ha_client):
    """Create BehavioralAnalysisClient."""
    return BehavioralAnalysisClient(mock_ha_client)


class TestDetectAutomationGaps:
    @pytest.mark.asyncio
    async def test_detects_recurring_pattern(self, behavioral_client, mock_ha_client):
        """A light turned off at 22:00 every night should be detected as a gap."""
        now = datetime.now(timezone.utc)
        entries = []

        # Create 5 days of turning off bedroom light at ~22:00
        for day_offset in range(5):
            dt = (now - timedelta(days=day_offset)).replace(
                hour=22, minute=0, second=0
            )
            entries.append({
                "entity_id": "light.bedroom",
                "name": "Bedroom Light",
                "message": "turned off",
                "when": dt.isoformat(),
                "state": "off",
                "context_user_id": "user1",
            })

        mock_ha_client.get_logbook = AsyncMock(return_value=entries)

        gaps = await behavioral_client.detect_automation_gaps(
            hours=168, min_occurrences=3
        )

        assert len(gaps) >= 1
        bedroom_gaps = [g for g in gaps if "light.bedroom" in g.entities]
        assert len(bedroom_gaps) >= 1
        assert bedroom_gaps[0].occurrence_count >= 3
        assert bedroom_gaps[0].typical_time == "22:00"

    @pytest.mark.asyncio
    async def test_ignores_infrequent_actions(self, behavioral_client, mock_ha_client):
        """Actions that happen less than min_occurrences should not be gaps."""
        now = datetime.now(timezone.utc)
        entries = [
            {
                "entity_id": "light.kitchen",
                "name": "Kitchen Light",
                "message": "turned off",
                "when": (now - timedelta(days=1)).replace(hour=23).isoformat(),
                "state": "off",
                "context_user_id": "user1",
            },
        ]

        mock_ha_client.get_logbook = AsyncMock(return_value=entries)

        gaps = await behavioral_client.detect_automation_gaps(
            hours=168, min_occurrences=3
        )

        kitchen_gaps = [g for g in gaps if "light.kitchen" in g.entities]
        assert len(kitchen_gaps) == 0

    @pytest.mark.asyncio
    async def test_empty_logbook_returns_no_gaps(self, behavioral_client, mock_ha_client):
        """Empty logbook should return no gaps."""
        mock_ha_client.get_logbook = AsyncMock(return_value=[])

        gaps = await behavioral_client.detect_automation_gaps(hours=168)
        assert gaps == []

    @pytest.mark.asyncio
    async def test_gap_confidence_increases_with_frequency(self, behavioral_client, mock_ha_client):
        """More occurrences should result in higher confidence."""
        now = datetime.now(timezone.utc)
        entries = []

        # 10 days of consistent pattern
        for day_offset in range(10):
            dt = (now - timedelta(days=day_offset)).replace(
                hour=7, minute=30, second=0
            )
            entries.append({
                "entity_id": "switch.coffee_maker",
                "name": "Coffee Maker",
                "message": "turned on",
                "when": dt.isoformat(),
                "state": "on",
                "context_user_id": "user1",
            })

        mock_ha_client.get_logbook = AsyncMock(return_value=entries)

        gaps = await behavioral_client.detect_automation_gaps(
            hours=240, min_occurrences=3
        )

        coffee_gaps = [g for g in gaps if "switch.coffee_maker" in g.entities]
        assert len(coffee_gaps) >= 1
        assert coffee_gaps[0].confidence > 0.5
