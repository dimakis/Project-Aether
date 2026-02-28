"""Proactive insight notifications.

Feature 37: Proactive Insight Notifications.

Filters insights by user preferences (impact threshold, quiet hours)
and sends push notifications for actionable findings.
"""

from __future__ import annotations

import logging
from datetime import datetime
from datetime import time as dt_time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.storage.entities.insight import Insight

logger = logging.getLogger(__name__)

_IMPACT_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class InsightNotifier:
    """Sends push notifications for actionable insights."""

    def __init__(
        self,
        min_impact: str = "high",
        quiet_start: str | None = None,
        quiet_end: str | None = None,
        enabled: bool = True,
    ):
        self.min_impact = min_impact
        self.quiet_start = self._parse_time(quiet_start)
        self.quiet_end = self._parse_time(quiet_end)
        self.enabled = enabled

    @staticmethod
    def _parse_time(t: str | None) -> dt_time | None:
        if not t:
            return None
        parts = t.split(":")
        return dt_time(int(parts[0]), int(parts[1]))

    def _passes_threshold(self, impact: str) -> bool:
        return _IMPACT_ORDER.get(impact, 0) >= _IMPACT_ORDER.get(self.min_impact, 2)

    def _is_quiet_hours(self) -> bool:
        if not self.quiet_start or not self.quiet_end:
            return False
        now = datetime.now().time()
        if self.quiet_start <= self.quiet_end:
            return self.quiet_start <= now <= self.quiet_end
        # Wraps midnight (e.g. 22:00 - 07:00)
        return now >= self.quiet_start or now <= self.quiet_end

    async def notify_if_actionable(self, insights: list[Insight]) -> int:
        """Filter insights and send notifications for actionable ones.

        Returns the number of notifications sent.
        """
        if not self.enabled:
            return 0

        if self._is_quiet_hours():
            logger.debug("Quiet hours active, skipping insight notifications")
            return 0

        actionable = [i for i in insights if self._passes_threshold(i.impact or "low")]
        if not actionable:
            return 0

        try:
            from src.hitl.push_notification import send_insight_notification

            if len(actionable) == 1:
                insight = actionable[0]
                await send_insight_notification(
                    title=insight.title,
                    message=f"Confidence: {int((insight.confidence or 0) * 100)}%. Tap to investigate.",
                    insight_id=str(insight.id),
                )
            else:
                await send_insight_notification(
                    title=f"{len(actionable)} new insights found",
                    message="Tap to review actionable findings.",
                    insight_id=None,
                )
            return len(actionable)
        except Exception:
            logger.warning("Failed to send insight notification", exc_info=True)
            return 0

    @classmethod
    async def from_settings(cls) -> InsightNotifier:
        """Create notifier from AppSettings notification preferences."""
        try:
            from src.dal.app_settings import get_app_settings_merged

            merged = await get_app_settings_merged()
            notifications = merged.get("notifications", {})
            return cls(
                min_impact=notifications.get("min_impact", "high"),
                quiet_start=notifications.get("quiet_hours_start"),
                quiet_end=notifications.get("quiet_hours_end"),
                enabled=notifications.get("enabled", True),
            )
        except Exception:
            logger.debug("Could not load notification settings, using defaults")
            return cls()
