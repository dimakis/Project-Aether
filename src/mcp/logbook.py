"""Logbook history client for behavioral analysis.

Wraps the MCPClient.get_logbook() method with parsing,
filtering, and aggregation for behavioral pattern detection.

Feature 03: Intelligent Optimization & Multi-Agent Collaboration.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.mcp.parsers import ParsedLogbookEntry, parse_logbook_list


# Action type classification
ACTION_TYPE_AUTOMATION = "automation_triggered"
ACTION_TYPE_BUTTON = "button_press"
ACTION_TYPE_SCRIPT = "script_run"
ACTION_TYPE_STATE_CHANGE = "state_change"
ACTION_TYPE_SERVICE = "service_call"
ACTION_TYPE_UNKNOWN = "unknown"


def classify_action(entry: ParsedLogbookEntry) -> str:
    """Classify a logbook entry into an action type.

    Args:
        entry: Parsed logbook entry

    Returns:
        Action type string
    """
    domain = entry.domain or ""
    context_id = entry.context_user_id

    if domain == "automation":
        return ACTION_TYPE_AUTOMATION
    if domain == "script":
        return ACTION_TYPE_SCRIPT
    if domain in ("input_button", "button"):
        return ACTION_TYPE_BUTTON
    if domain in ("input_boolean", "switch", "light", "cover", "fan", "lock"):
        # If a user triggered it (not an automation), it's a manual action
        if context_id:
            return ACTION_TYPE_BUTTON
        return ACTION_TYPE_STATE_CHANGE
    if entry.message and "triggered by" in entry.message.lower():
        return ACTION_TYPE_AUTOMATION

    return ACTION_TYPE_STATE_CHANGE


@dataclass
class LogbookStats:
    """Aggregated statistics from logbook entries."""

    total_entries: int = 0
    by_action_type: dict[str, int] = field(default_factory=dict)
    by_domain: dict[str, int] = field(default_factory=dict)
    by_entity: dict[str, int] = field(default_factory=dict)
    by_hour: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    time_range_hours: int = 0
    automation_triggers: int = 0
    manual_actions: int = 0
    unique_entities: int = 0


class LogbookHistoryClient:
    """Client for logbook-based behavioral analysis.

    Wraps MCPClient.get_logbook() with parsing, filtering,
    and aggregation capabilities for behavioral pattern detection.
    """

    def __init__(self, mcp_client: Any) -> None:
        """Initialize with an MCP client.

        Args:
            mcp_client: MCPClient instance
        """
        self._mcp = mcp_client

    async def get_entries(
        self,
        hours: int = 24,
        entity_id: str | None = None,
    ) -> list[ParsedLogbookEntry]:
        """Get parsed logbook entries.

        Args:
            hours: Hours of history to fetch
            entity_id: Optional entity filter

        Returns:
            List of parsed logbook entries
        """
        raw = await self._mcp.get_logbook(hours=hours, entity_id=entity_id)
        return parse_logbook_list(raw)

    async def get_entries_by_domain(
        self,
        domain: str,
        hours: int = 24,
    ) -> list[ParsedLogbookEntry]:
        """Get logbook entries filtered by domain.

        Args:
            domain: Domain to filter (e.g., 'automation', 'light')
            hours: Hours of history

        Returns:
            Filtered entries
        """
        entries = await self.get_entries(hours=hours)
        return [e for e in entries if e.domain == domain]

    async def get_stats(
        self,
        hours: int = 24,
        entity_id: str | None = None,
    ) -> LogbookStats:
        """Get aggregated logbook statistics.

        Args:
            hours: Hours of history
            entity_id: Optional entity filter

        Returns:
            Aggregated statistics
        """
        entries = await self.get_entries(hours=hours, entity_id=entity_id)
        return self._calculate_stats(entries, hours)

    async def get_automation_entries(
        self,
        hours: int = 24,
    ) -> list[ParsedLogbookEntry]:
        """Get automation-related logbook entries.

        Args:
            hours: Hours of history

        Returns:
            Automation entries
        """
        return await self.get_entries_by_domain("automation", hours=hours)

    async def get_manual_actions(
        self,
        hours: int = 24,
    ) -> list[ParsedLogbookEntry]:
        """Get manually triggered actions (user-initiated).

        Args:
            hours: Hours of history

        Returns:
            Manual action entries
        """
        entries = await self.get_entries(hours=hours)
        return [
            e for e in entries
            if classify_action(e) == ACTION_TYPE_BUTTON
        ]

    def _calculate_stats(
        self,
        entries: list[ParsedLogbookEntry],
        hours: int,
    ) -> LogbookStats:
        """Calculate statistics from entries.

        Args:
            entries: Parsed logbook entries
            hours: Time range in hours

        Returns:
            Aggregated statistics
        """
        stats = LogbookStats(
            total_entries=len(entries),
            time_range_hours=hours,
        )

        action_counts: dict[str, int] = defaultdict(int)
        domain_counts: dict[str, int] = defaultdict(int)
        entity_counts: dict[str, int] = defaultdict(int)
        hour_counts: dict[int, int] = defaultdict(int)

        for entry in entries:
            action = classify_action(entry)
            action_counts[action] += 1
            if entry.domain:
                domain_counts[entry.domain] += 1
            if entry.entity_id:
                entity_counts[entry.entity_id] += 1
            if entry.when:
                try:
                    dt = datetime.fromisoformat(
                        entry.when.replace("Z", "+00:00")
                    )
                    hour_counts[dt.hour] += 1
                except (ValueError, AttributeError):
                    pass

        stats.by_action_type = dict(action_counts)
        stats.by_domain = dict(domain_counts)
        stats.by_entity = dict(entity_counts)
        stats.by_hour = dict(hour_counts)
        stats.automation_triggers = action_counts.get(ACTION_TYPE_AUTOMATION, 0)
        stats.manual_actions = action_counts.get(ACTION_TYPE_BUTTON, 0)
        stats.unique_entities = len(entity_counts)

        return stats

    def aggregate_by_action_type(
        self,
        entries: list[ParsedLogbookEntry],
    ) -> dict[str, list[ParsedLogbookEntry]]:
        """Group entries by action type.

        Args:
            entries: Parsed logbook entries

        Returns:
            Dict mapping action type to entries
        """
        grouped: dict[str, list[ParsedLogbookEntry]] = defaultdict(list)
        for entry in entries:
            action = classify_action(entry)
            grouped[action].append(entry)
        return dict(grouped)


# Convenience functions
async def get_logbook_stats(
    mcp_client: Any,
    hours: int = 24,
) -> LogbookStats:
    """Quick access to logbook statistics.

    Args:
        mcp_client: MCPClient instance
        hours: Hours of history

    Returns:
        Aggregated statistics
    """
    client = LogbookHistoryClient(mcp_client)
    return await client.get_stats(hours=hours)


__all__ = [
    "LogbookHistoryClient",
    "LogbookStats",
    "classify_action",
    "get_logbook_stats",
    "ACTION_TYPE_AUTOMATION",
    "ACTION_TYPE_BUTTON",
    "ACTION_TYPE_SCRIPT",
    "ACTION_TYPE_STATE_CHANGE",
    "ACTION_TYPE_SERVICE",
    "ACTION_TYPE_UNKNOWN",
]
