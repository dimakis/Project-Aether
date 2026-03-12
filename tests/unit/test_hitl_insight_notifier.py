"""Tests for InsightNotifier proactive notification logic.

Feature 37: Proactive Insight Notifications.
Covers threshold filtering, quiet hours, batch vs single
notification, disabled state, from_settings factory, and
graceful failure when push service is unavailable.
"""

from __future__ import annotations

from datetime import time as dt_time
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, patch

import pytest

from src.hitl.insight_notifier import InsightNotifier

if TYPE_CHECKING:
    from src.storage.entities.insight import Insight


def _insight(
    impact: str = "high",
    title: str = "Test insight",
    confidence: float = 0.9,
    insight_id: str = "ins-1",
) -> Insight:
    """Create a minimal Insight-like object for testing."""
    return cast(
        "Insight",
        SimpleNamespace(
            id=insight_id,
            title=title,
            impact=impact,
            confidence=confidence,
        ),
    )


class TestThresholdFiltering:
    """Tests for _passes_threshold impact filtering."""

    def test_high_passes_high(self) -> None:
        n = InsightNotifier(min_impact="high")
        assert n._passes_threshold("high") is True

    def test_critical_passes_high(self) -> None:
        n = InsightNotifier(min_impact="high")
        assert n._passes_threshold("critical") is True

    def test_medium_fails_high(self) -> None:
        n = InsightNotifier(min_impact="high")
        assert n._passes_threshold("medium") is False

    def test_low_fails_high(self) -> None:
        n = InsightNotifier(min_impact="high")
        assert n._passes_threshold("low") is False

    def test_low_passes_low(self) -> None:
        n = InsightNotifier(min_impact="low")
        assert n._passes_threshold("low") is True

    def test_medium_passes_medium(self) -> None:
        n = InsightNotifier(min_impact="medium")
        assert n._passes_threshold("medium") is True

    def test_high_fails_critical(self) -> None:
        n = InsightNotifier(min_impact="critical")
        assert n._passes_threshold("high") is False

    def test_unknown_impact_treated_as_zero(self) -> None:
        n = InsightNotifier(min_impact="high")
        assert n._passes_threshold("unknown") is False


class TestQuietHours:
    """Tests for _is_quiet_hours logic."""

    def test_no_quiet_hours_configured(self) -> None:
        n = InsightNotifier()
        assert n._is_quiet_hours() is False

    def test_within_same_day_window(self) -> None:
        n = InsightNotifier(quiet_start="09:00", quiet_end="17:00")
        with patch("src.hitl.insight_notifier.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = dt_time(12, 0)
            assert n._is_quiet_hours() is True

    def test_outside_same_day_window(self) -> None:
        n = InsightNotifier(quiet_start="09:00", quiet_end="17:00")
        with patch("src.hitl.insight_notifier.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = dt_time(20, 0)
            assert n._is_quiet_hours() is False

    def test_midnight_crossing_late_night(self) -> None:
        """22:00-07:00 window, time is 23:30 -> quiet."""
        n = InsightNotifier(quiet_start="22:00", quiet_end="07:00")
        with patch("src.hitl.insight_notifier.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = dt_time(23, 30)
            assert n._is_quiet_hours() is True

    def test_midnight_crossing_early_morning(self) -> None:
        """22:00-07:00 window, time is 05:00 -> quiet."""
        n = InsightNotifier(quiet_start="22:00", quiet_end="07:00")
        with patch("src.hitl.insight_notifier.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = dt_time(5, 0)
            assert n._is_quiet_hours() is True

    def test_midnight_crossing_afternoon(self) -> None:
        """22:00-07:00 window, time is 14:00 -> not quiet."""
        n = InsightNotifier(quiet_start="22:00", quiet_end="07:00")
        with patch("src.hitl.insight_notifier.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = dt_time(14, 0)
            assert n._is_quiet_hours() is False


class TestNotifyIfActionable:
    """Tests for notify_if_actionable method."""

    @pytest.mark.asyncio
    async def test_disabled_returns_zero(self) -> None:
        n = InsightNotifier(enabled=False)
        result = await n.notify_if_actionable([_insight()])
        assert result == 0

    @pytest.mark.asyncio
    async def test_quiet_hours_returns_zero(self) -> None:
        n = InsightNotifier(quiet_start="00:00", quiet_end="23:59")
        with patch("src.hitl.insight_notifier.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = dt_time(12, 0)
            result = await n.notify_if_actionable([_insight()])
        assert result == 0

    @pytest.mark.asyncio
    async def test_no_actionable_returns_zero(self) -> None:
        n = InsightNotifier(min_impact="critical")
        result = await n.notify_if_actionable([_insight(impact="low")])
        assert result == 0

    @pytest.mark.asyncio
    async def test_single_insight_sends_detailed(self) -> None:
        n = InsightNotifier(min_impact="high")
        mock_send = AsyncMock(return_value={"success": True})

        with patch(
            "src.hitl.push_notification.send_insight_notification",
            mock_send,
        ):
            result = await n.notify_if_actionable([_insight(title="Energy spike")])

        assert result == 1
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["title"] == "Energy spike"
        assert "90%" in call_kwargs["message"]
        assert call_kwargs["insight_id"] == "ins-1"

    @pytest.mark.asyncio
    async def test_multiple_insights_sends_batch(self) -> None:
        n = InsightNotifier(min_impact="high")
        mock_send = AsyncMock(return_value={"success": True})
        insights = [
            _insight(impact="high", insight_id="a"),
            _insight(impact="critical", insight_id="b"),
            _insight(impact="high", insight_id="c"),
        ]

        with patch(
            "src.hitl.push_notification.send_insight_notification",
            mock_send,
        ):
            result = await n.notify_if_actionable(insights)

        assert result == 3
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "3 new insights" in call_kwargs["title"]
        assert call_kwargs["insight_id"] is None

    @pytest.mark.asyncio
    async def test_mixed_impacts_filters_correctly(self) -> None:
        """Only insights meeting threshold are counted and notified."""
        n = InsightNotifier(min_impact="high")
        mock_send = AsyncMock(return_value={"success": True})
        insights = [
            _insight(impact="low"),
            _insight(impact="high"),
            _insight(impact="medium"),
        ]

        with patch(
            "src.hitl.push_notification.send_insight_notification",
            mock_send,
        ):
            result = await n.notify_if_actionable(insights)

        assert result == 1  # only "high" passes threshold

    @pytest.mark.asyncio
    async def test_send_failure_returns_zero(self) -> None:
        """If push notification fails, return 0 gracefully."""
        n = InsightNotifier(min_impact="high")

        with patch(
            "src.hitl.push_notification.send_insight_notification",
            side_effect=RuntimeError("push failed"),
        ):
            result = await n.notify_if_actionable([_insight()])

        assert result == 0


class TestFromSettings:
    """Tests for the from_settings class method."""

    @pytest.mark.asyncio
    async def test_loads_from_db_settings(self) -> None:
        mock_merged = {
            "notifications": {
                "enabled": False,
                "min_impact": "critical",
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "07:00",
            }
        }

        with patch(
            "src.dal.app_settings.get_app_settings_merged",
            new_callable=AsyncMock,
            return_value=mock_merged,
        ):
            notifier = await InsightNotifier.from_settings()

        assert notifier.enabled is False
        assert notifier.min_impact == "critical"
        assert notifier.quiet_start == dt_time(22, 0)
        assert notifier.quiet_end == dt_time(7, 0)

    @pytest.mark.asyncio
    async def test_falls_back_to_defaults_on_error(self) -> None:
        with patch(
            "src.dal.app_settings.get_app_settings_merged",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB down"),
        ):
            notifier = await InsightNotifier.from_settings()

        assert notifier.enabled is True
        assert notifier.min_impact == "high"
        assert notifier.quiet_start is None
        assert notifier.quiet_end is None


class TestParseTime:
    """Tests for _parse_time helper."""

    def test_valid_time(self) -> None:
        assert InsightNotifier._parse_time("22:30") == dt_time(22, 30)

    def test_midnight(self) -> None:
        assert InsightNotifier._parse_time("00:00") == dt_time(0, 0)

    def test_none_returns_none(self) -> None:
        assert InsightNotifier._parse_time(None) is None

    def test_empty_returns_none(self) -> None:
        assert InsightNotifier._parse_time("") is None
