"""Unit tests for MCP logbook module.

Tests LogbookHistoryClient and logbook parsers with mocked HA client.
Constitution: Reliability & Quality.

TDD: T233 - Logbook client and parsing.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.ha.logbook import (
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_BUTTON,
    ACTION_TYPE_STATE_CHANGE,
    LogbookHistoryClient,
    LogbookStats,
    classify_action,
)
from src.ha.parsers import (
    ParsedLogbookEntry,
    parse_logbook_entry,
    parse_logbook_list,
)


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client."""
    client = AsyncMock()
    client.get_logbook = AsyncMock()
    return client


@pytest.fixture
def logbook_client(mock_ha_client):
    """Create LogbookHistoryClient with mock HA client."""
    return LogbookHistoryClient(mock_ha_client)


@pytest.fixture
def sample_logbook_entries():
    """Create sample logbook entries from HA."""
    now = datetime.now(timezone.utc)
    return [
        {
            "entity_id": "automation.morning_lights",
            "name": "Morning Lights",
            "message": "triggered",
            "when": (now - timedelta(hours=2)).isoformat(),
            "state": "on",
            "context_user_id": None,
        },
        {
            "entity_id": "light.living_room",
            "name": "Living Room Light",
            "message": "turned on",
            "when": (now - timedelta(hours=1)).isoformat(),
            "state": "on",
            "context_user_id": "user123",
        },
        {
            "entity_id": "switch.garden_lights",
            "name": "Garden Lights",
            "message": "turned off",
            "when": now.isoformat(),
            "state": "off",
            "context_user_id": "user123",
        },
    ]


# === Parser Tests ===


class TestParseLogbookEntry:
    def test_parse_basic_entry(self):
        data = {
            "entity_id": "light.living_room",
            "name": "Living Room",
            "message": "turned on",
            "when": "2026-02-07T10:00:00+00:00",
            "state": "on",
        }
        entry = parse_logbook_entry(data)
        assert entry.entity_id == "light.living_room"
        assert entry.domain == "light"
        assert entry.name == "Living Room"
        assert entry.state == "on"

    def test_parse_automation_entry(self):
        data = {
            "entity_id": "automation.morning_lights",
            "name": "Morning Lights",
            "message": "triggered",
            "when": "2026-02-07T06:00:00+00:00",
        }
        entry = parse_logbook_entry(data)
        assert entry.domain == "automation"

    def test_parse_empty_entry(self):
        entry = parse_logbook_entry({})
        assert entry.entity_id is None
        assert entry.domain is None

    def test_parse_logbook_list(self, sample_logbook_entries):
        entries = parse_logbook_list(sample_logbook_entries)
        assert len(entries) == 3
        assert entries[0].domain == "automation"
        assert entries[1].domain == "light"


# === Action Classification Tests ===


class TestClassifyAction:
    def test_automation_trigger(self):
        entry = ParsedLogbookEntry(
            entity_id="automation.test",
            domain="automation",
        )
        assert classify_action(entry) == ACTION_TYPE_AUTOMATION

    def test_manual_button_press(self):
        entry = ParsedLogbookEntry(
            entity_id="light.living_room",
            domain="light",
            context_user_id="user123",
        )
        assert classify_action(entry) == ACTION_TYPE_BUTTON

    def test_state_change_no_user(self):
        entry = ParsedLogbookEntry(
            entity_id="sensor.temperature",
            domain="sensor",
            context_user_id=None,
        )
        assert classify_action(entry) == ACTION_TYPE_STATE_CHANGE

    def test_script_action(self):
        entry = ParsedLogbookEntry(
            entity_id="script.bedtime",
            domain="script",
        )
        action = classify_action(entry)
        assert action == "script_run"


# === LogbookHistoryClient Tests ===


class TestLogbookHistoryClient:
    @pytest.mark.asyncio
    async def test_get_entries(self, logbook_client, mock_ha_client, sample_logbook_entries):
        mock_ha_client.get_logbook.return_value = sample_logbook_entries

        entries = await logbook_client.get_entries(hours=24)
        assert len(entries) == 3
        mock_ha_client.get_logbook.assert_called_once_with(hours=24, entity_id=None)

    @pytest.mark.asyncio
    async def test_get_entries_by_domain(self, logbook_client, mock_ha_client, sample_logbook_entries):
        mock_ha_client.get_logbook.return_value = sample_logbook_entries

        entries = await logbook_client.get_entries_by_domain("automation", hours=24)
        assert len(entries) == 1
        assert entries[0].domain == "automation"

    @pytest.mark.asyncio
    async def test_get_stats(self, logbook_client, mock_ha_client, sample_logbook_entries):
        mock_ha_client.get_logbook.return_value = sample_logbook_entries

        stats = await logbook_client.get_stats(hours=24)
        assert isinstance(stats, LogbookStats)
        assert stats.total_entries == 3
        assert stats.automation_triggers >= 1
        assert stats.manual_actions >= 1
        assert stats.unique_entities == 3

    @pytest.mark.asyncio
    async def test_get_manual_actions(self, logbook_client, mock_ha_client, sample_logbook_entries):
        mock_ha_client.get_logbook.return_value = sample_logbook_entries

        manual = await logbook_client.get_manual_actions(hours=24)
        # light and switch with context_user_id should be manual
        assert len(manual) >= 1

    @pytest.mark.asyncio
    async def test_empty_logbook(self, logbook_client, mock_ha_client):
        mock_ha_client.get_logbook.return_value = []

        stats = await logbook_client.get_stats(hours=24)
        assert stats.total_entries == 0

    @pytest.mark.asyncio
    async def test_aggregate_by_action_type(self, logbook_client, mock_ha_client, sample_logbook_entries):
        mock_ha_client.get_logbook.return_value = sample_logbook_entries
        entries = await logbook_client.get_entries(hours=24)

        grouped = logbook_client.aggregate_by_action_type(entries)
        assert isinstance(grouped, dict)
        assert ACTION_TYPE_AUTOMATION in grouped
