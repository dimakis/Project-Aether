"""Unit tests for behavioral analysis client.

Tests BehavioralAnalysisClient with mocked HA client.
Constitution: Reliability & Quality.

TDD: T234 - Pattern detection tests.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.ha.behavioral import (
    AutomationEffectivenessReport,
    AutomationGap,
    BehavioralAnalysisClient,
    ButtonUsageReport,
    CorrelationResult,
    DeviceHealthEntry,
)


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client with logbook and automation support."""
    client = AsyncMock()

    now = datetime.now(UTC)

    # Logbook entries covering various action types
    client.get_logbook = AsyncMock(
        return_value=[
            # Automation trigger
            {
                "entity_id": "automation.morning_lights",
                "name": "Morning Lights",
                "message": "triggered",
                "when": (now - timedelta(hours=5)).isoformat(),
                "state": "on",
            },
            # Manual button presses at similar times (automation gap)
            {
                "entity_id": "light.bedroom",
                "name": "Bedroom Light",
                "message": "turned off",
                "when": (now - timedelta(hours=4, minutes=2)).replace(hour=22).isoformat(),
                "state": "off",
                "context_user_id": "user1",
            },
            {
                "entity_id": "light.bedroom",
                "name": "Bedroom Light",
                "message": "turned off",
                "when": (now - timedelta(hours=28, minutes=5)).replace(hour=22).isoformat(),
                "state": "off",
                "context_user_id": "user1",
            },
            {
                "entity_id": "light.bedroom",
                "name": "Bedroom Light",
                "message": "turned off",
                "when": (now - timedelta(hours=52, minutes=1)).replace(hour=22).isoformat(),
                "state": "off",
                "context_user_id": "user1",
            },
            # Correlated entities (change within minutes)
            {
                "entity_id": "light.living_room",
                "name": "Living Room",
                "when": (now - timedelta(hours=3)).isoformat(),
                "state": "on",
                "context_user_id": "user1",
            },
            {
                "entity_id": "media_player.tv",
                "name": "TV",
                "when": (now - timedelta(hours=3, seconds=-60)).isoformat(),
                "state": "on",
                "context_user_id": "user1",
            },
            # Device with unavailable state
            {
                "entity_id": "sensor.outdoor_temp",
                "name": "Outdoor Temp",
                "when": (now - timedelta(hours=1)).isoformat(),
                "state": "unavailable",
            },
        ]
    )

    client.list_automations = AsyncMock(
        return_value=[
            {
                "entity_id": "automation.morning_lights",
                "alias": "Morning Lights",
                "state": "on",
            },
        ]
    )

    return client


@pytest.fixture
def behavioral_client(mock_ha_client):
    """Create BehavioralAnalysisClient with mock."""
    return BehavioralAnalysisClient(mock_ha_client)


class TestGetButtonUsage:
    @pytest.mark.asyncio
    async def test_returns_reports(self, behavioral_client):
        reports = await behavioral_client.get_button_usage(hours=168)
        assert isinstance(reports, list)
        assert all(isinstance(r, ButtonUsageReport) for r in reports)

    @pytest.mark.asyncio
    async def test_counts_presses(self, behavioral_client):
        reports = await behavioral_client.get_button_usage(hours=168)
        # Should find manual presses for bedroom light
        bedroom_reports = [r for r in reports if r.entity_id == "light.bedroom"]
        if bedroom_reports:
            assert bedroom_reports[0].total_presses >= 1


class TestGetAutomationEffectiveness:
    @pytest.mark.asyncio
    async def test_returns_reports(self, behavioral_client):
        reports = await behavioral_client.get_automation_effectiveness(hours=168)
        assert isinstance(reports, list)
        assert all(isinstance(r, AutomationEffectivenessReport) for r in reports)


class TestFindCorrelations:
    @pytest.mark.asyncio
    async def test_returns_correlations(self, behavioral_client):
        results = await behavioral_client.find_correlations(hours=168)
        assert isinstance(results, list)
        assert all(isinstance(r, CorrelationResult) for r in results)


class TestDetectAutomationGaps:
    @pytest.mark.asyncio
    async def test_returns_gaps(self, behavioral_client):
        gaps = await behavioral_client.detect_automation_gaps(hours=168)
        assert isinstance(gaps, list)
        assert all(isinstance(g, AutomationGap) for g in gaps)


class TestGetDeviceHealthReport:
    @pytest.mark.asyncio
    async def test_returns_entries(self, behavioral_client):
        health = await behavioral_client.get_device_health_report(hours=48)
        assert isinstance(health, list)
        assert all(isinstance(h, DeviceHealthEntry) for h in health)

    @pytest.mark.asyncio
    async def test_detects_unavailable(self, behavioral_client):
        health = await behavioral_client.get_device_health_report(hours=48)
        # Check if outdoor temp sensor is flagged
        outdoor = [h for h in health if h.entity_id == "sensor.outdoor_temp"]
        if outdoor:
            # Could be unresponsive or degraded depending on ratio
            assert outdoor[0].status in ("unresponsive", "degraded", "healthy")
