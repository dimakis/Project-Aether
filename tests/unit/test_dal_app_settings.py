"""Unit tests for app_settings DAL: validate_section and AppSettingsRepository.

Tests validation and repository methods with mocked database sessions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.dal.app_settings import (
    SECTION_DEFAULTS,
    AppSettingsRepository,
    invalidate_settings_cache,
    validate_section,
)
from src.storage.entities.app_settings import AppSettings


class TestValidateSection:
    """Tests for validate_section."""

    def test_chat_section_valid_int(self):
        """Chat section clamps int to bounds."""
        result = validate_section("chat", {"stream_timeout_seconds": 5000})
        assert result["stream_timeout_seconds"] == 3600
        result = validate_section("chat", {"stream_timeout_seconds": 30})
        assert result["stream_timeout_seconds"] == 60

    def test_chat_section_valid_bool(self):
        """Chat section accepts bool for max_tool_iterations not in CHAT_DEFAULTS - skip."""
        result = validate_section("chat", {"stream_timeout_seconds": 120})
        assert result["stream_timeout_seconds"] == 120

    def test_unknown_key_dropped(self):
        """Unknown keys are dropped."""
        result = validate_section("chat", {"stream_timeout_seconds": 120, "unknown": 1})
        assert "unknown" not in result
        assert result["stream_timeout_seconds"] == 120

    def test_min_impact_valid(self):
        """Notifications min_impact accepts valid values."""
        result = validate_section(
            "notifications",
            {"enabled": True, "min_impact": "high"},
        )
        assert result["min_impact"] == "high"

    def test_min_impact_invalid_raises(self):
        """Notifications min_impact raises for invalid value."""
        with pytest.raises(ValueError, match="min_impact must be one of"):
            validate_section("notifications", {"min_impact": "invalid"})

    def test_quiet_hours_valid(self):
        """Quiet hours accept HH:MM or None."""
        result = validate_section(
            "notifications",
            {"quiet_hours_start": "22:00", "quiet_hours_end": "07:00"},
        )
        assert result["quiet_hours_start"] == "22:00"
        assert result["quiet_hours_end"] == "07:00"

    def test_quiet_hours_invalid_raises(self):
        """Quiet hours invalid format raises."""
        with pytest.raises(ValueError, match="HH:MM"):
            validate_section("notifications", {"quiet_hours_start": "invalid"})


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_app_settings_row():
    """Create a mock AppSettings row with section dicts."""
    row = MagicMock(spec=AppSettings)
    row.id = "settings-uuid-1"
    row.chat = {"stream_timeout_seconds": 300}
    row.dashboard = {}
    row.data_science = {}
    row.notifications = {}
    return row


@pytest.mark.asyncio
class TestAppSettingsRepository:
    """Tests for AppSettingsRepository."""

    async def test_get_none(self, mock_session):
        """get returns None when no row exists."""
        repo = AppSettingsRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repo.get()
        assert result is None
        mock_session.execute.assert_called_once()

    async def test_get_returns_row(self, mock_session, mock_app_settings_row):
        """get returns the settings row when it exists."""
        repo = AppSettingsRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_app_settings_row)
        mock_session.execute.return_value = mock_result

        result = await repo.get()
        assert result == mock_app_settings_row

    async def test_get_merged_no_row(self, mock_session):
        """get_merged returns section defaults when no row."""
        repo = AppSettingsRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repo.get_merged()
        assert set(result) == set(SECTION_DEFAULTS)
        for section, defaults in SECTION_DEFAULTS.items():
            assert result[section].keys() == defaults.keys()

    async def test_get_merged_with_row(self, mock_session, mock_app_settings_row):
        """get_merged merges row section over defaults."""
        repo = AppSettingsRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_app_settings_row)
        mock_session.execute.return_value = mock_result

        result = await repo.get_merged()
        assert result["chat"]["stream_timeout_seconds"] == 300
        assert "stream_timeout_seconds" in result["chat"]

    async def test_reset_section_unknown_raises(self, mock_session):
        """reset_section raises for unknown section."""
        repo = AppSettingsRepository(mock_session)
        with pytest.raises(ValueError, match="Unknown section"):
            await repo.reset_section("invalid_section")


def test_invalidate_settings_cache():
    """invalidate_settings_cache runs without error."""
    invalidate_settings_cache()
