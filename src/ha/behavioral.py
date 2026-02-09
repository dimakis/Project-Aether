"""Behavioral analysis client for intelligent optimization.

Combines logbook and history data to detect behavioral patterns,
automation gaps, entity correlations, and device health issues.

Feature 03: Intelligent Optimization & Multi-Agent Collaboration.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.ha.logbook import (
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_BUTTON,
    LogbookHistoryClient,
    classify_action,
)

if TYPE_CHECKING:
    from src.ha.parsers import ParsedLogbookEntry

logger = logging.getLogger(__name__)


@dataclass
class ButtonUsageReport:
    """Report on button/switch press frequency and timing."""

    entity_id: str
    total_presses: int = 0
    by_hour: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    last_press: str | None = None
    avg_daily_presses: float = 0.0


@dataclass
class AutomationEffectivenessReport:
    """Report on automation effectiveness."""

    automation_id: str
    alias: str = ""
    trigger_count: int = 0
    manual_override_count: int = 0
    efficiency_score: float = 0.0  # 0.0-1.0
    last_triggered: str | None = None


@dataclass
class CorrelationResult:
    """A discovered correlation between entities."""

    entity_a: str
    entity_b: str
    co_occurrence_count: int = 0
    avg_time_delta_seconds: float = 0.0
    confidence: float = 0.0


@dataclass
class AutomationGap:
    """A detected manual pattern that could be automated."""

    pattern_description: str
    entities: list[str] = field(default_factory=list)
    occurrence_count: int = 0
    typical_time: str | None = None  # e.g., "22:00"
    confidence: float = 0.0


@dataclass
class DeviceHealthEntry:
    """Health status of a device/entity."""

    entity_id: str
    status: str = "healthy"  # healthy, degraded, unresponsive, anomalous
    last_seen: str | None = None
    issue: str | None = None
    state_change_count: int = 0


class BehavioralAnalysisClient:
    """Client for behavioral pattern analysis.

    Combines logbook and history data to detect patterns,
    automation gaps, correlations, and device health issues.
    """

    def __init__(self, ha_client: Any) -> None:
        """Initialize with an HA client.

        Args:
            ha_client: HAClient instance
        """
        self._ha_client = ha_client
        self._logbook = LogbookHistoryClient(ha_client)

    async def get_button_usage(
        self,
        hours: int = 168,
    ) -> list[ButtonUsageReport]:
        """Analyze button/switch press frequency and timing.

        Args:
            hours: Hours of history to analyze (default: 1 week)

        Returns:
            List of ButtonUsageReport per entity
        """
        manual_actions = await self._logbook.get_manual_actions(hours=hours)

        # Group by entity
        by_entity: dict[str, list[ParsedLogbookEntry]] = defaultdict(list)
        for entry in manual_actions:
            if entry.entity_id:
                by_entity[entry.entity_id].append(entry)

        reports = []
        days = max(hours / 24, 1)

        for entity_id, entries in by_entity.items():
            report = ButtonUsageReport(
                entity_id=entity_id,
                total_presses=len(entries),
                avg_daily_presses=len(entries) / days,
            )

            for entry in entries:
                if entry.when:
                    try:
                        dt = datetime.fromisoformat(entry.when.replace("Z", "+00:00"))
                        report.by_hour[dt.hour] += 1
                        report.last_press = entry.when
                    except (ValueError, AttributeError):
                        pass

            reports.append(report)

        # Sort by most active
        reports.sort(key=lambda r: r.total_presses, reverse=True)
        return reports

    async def get_automation_effectiveness(
        self,
        hours: int = 168,
    ) -> list[AutomationEffectivenessReport]:
        """Score automation effectiveness.

        Measures how often automations fire vs how often users
        manually override the same entities.

        Args:
            hours: Hours of history to analyze

        Returns:
            List of effectiveness reports per automation
        """
        entries = await self._logbook.get_entries(hours=hours)

        # Get automation triggers
        auto_triggers: dict[str, list[ParsedLogbookEntry]] = defaultdict(list)
        manual_overrides: dict[str, int] = defaultdict(int)

        # Track which entities are controlled by automations
        defaultdict(set)

        for entry in entries:
            action = classify_action(entry)
            if action == ACTION_TYPE_AUTOMATION and entry.entity_id:
                auto_triggers[entry.entity_id].append(entry)
            elif action == ACTION_TYPE_BUTTON and entry.entity_id:
                manual_overrides[entry.entity_id] += 1

        # Get automation list for names
        try:
            automations = await self._ha_client.list_automations()
            auto_map = {}
            if isinstance(automations, list):
                for a in automations:
                    eid = a.get("entity_id", "")
                    auto_map[eid] = a.get("alias", eid)
        except Exception:
            auto_map = {}

        reports = []
        for auto_id, triggers in auto_triggers.items():
            overrides = manual_overrides.get(auto_id, 0)
            total = len(triggers) + overrides
            efficiency = len(triggers) / total if total > 0 else 0.0

            report = AutomationEffectivenessReport(
                automation_id=auto_id,
                alias=auto_map.get(auto_id, auto_id),
                trigger_count=len(triggers),
                manual_override_count=overrides,
                efficiency_score=efficiency,
                last_triggered=triggers[-1].when if triggers else None,
            )
            reports.append(report)

        reports.sort(key=lambda r: r.efficiency_score)
        return reports

    async def find_correlations(
        self,
        entity_ids: list[str] | None = None,
        hours: int = 168,
        time_window_seconds: int = 300,
    ) -> list[CorrelationResult]:
        """Discover entity correlations from timing patterns.

        Finds entities that change state within a time window of each other,
        suggesting they're related (used together).

        Args:
            entity_ids: Specific entities to check (None = all)
            hours: Hours of history
            time_window_seconds: Co-occurrence window (default: 5 min)

        Returns:
            List of correlation results
        """
        entries = await self._logbook.get_entries(hours=hours)

        # Filter to specific entities if provided
        if entity_ids:
            entity_set = set(entity_ids)
            entries = [e for e in entries if e.entity_id in entity_set]

        # Parse timestamps and sort
        timed_entries: list[tuple[datetime, ParsedLogbookEntry]] = []
        for entry in entries:
            if entry.when and entry.entity_id:
                try:
                    dt = datetime.fromisoformat(entry.when.replace("Z", "+00:00"))
                    timed_entries.append((dt, entry))
                except (ValueError, AttributeError):
                    pass

        timed_entries.sort(key=lambda x: x[0])

        # Find co-occurrences within the time window
        co_occurrences: dict[tuple[str, str], list[float]] = defaultdict(list)

        for i, (dt_a, entry_a) in enumerate(timed_entries):
            for j in range(i + 1, len(timed_entries)):
                dt_b, entry_b = timed_entries[j]
                delta = (dt_b - dt_a).total_seconds()

                if delta > time_window_seconds:
                    break  # Beyond window

                if entry_a.entity_id != entry_b.entity_id:
                    pair = tuple(sorted([entry_a.entity_id, entry_b.entity_id]))
                    co_occurrences[pair].append(delta)

        # Build results
        results = []
        for (entity_a, entity_b), deltas in co_occurrences.items():
            if len(deltas) >= 3:  # Minimum 3 co-occurrences
                avg_delta = sum(deltas) / len(deltas)
                # Confidence based on frequency
                confidence = min(1.0, len(deltas) / 20)
                results.append(
                    CorrelationResult(
                        entity_a=entity_a,
                        entity_b=entity_b,
                        co_occurrence_count=len(deltas),
                        avg_time_delta_seconds=avg_delta,
                        confidence=confidence,
                    )
                )

        results.sort(key=lambda r: r.co_occurrence_count, reverse=True)
        return results[:20]  # Top 20

    async def detect_automation_gaps(
        self,
        hours: int = 168,
        min_occurrences: int = 3,
    ) -> list[AutomationGap]:
        """Find repeating manual patterns that could be automated.

        Detects patterns like "user turns off lights at ~22:00 every night"
        by analyzing manual actions and their timing.

        Args:
            hours: Hours of history to analyze
            min_occurrences: Minimum repetitions to consider a pattern

        Returns:
            List of detected automation gaps
        """
        manual_actions = await self._logbook.get_manual_actions(hours=hours)

        # Group by entity + approximate hour
        patterns: dict[tuple[str, int], list[ParsedLogbookEntry]] = defaultdict(list)

        for entry in manual_actions:
            if entry.entity_id and entry.when:
                try:
                    dt = datetime.fromisoformat(entry.when.replace("Z", "+00:00"))
                    # Group by entity and hour of day
                    key = (entry.entity_id, dt.hour)
                    patterns[key].append(entry)
                except (ValueError, AttributeError):
                    pass

        # Find recurring patterns
        gaps = []
        for (entity_id, hour), entries in patterns.items():
            if len(entries) >= min_occurrences:
                days = max(hours / 24, 1)
                confidence = min(1.0, len(entries) / (days * 0.8))

                # Determine likely action from most recent
                last_state = entries[-1].state or "toggled"

                gap = AutomationGap(
                    pattern_description=(
                        f"'{entity_id}' is manually {last_state} "
                        f"around {hour:02d}:00 approximately "
                        f"{len(entries)} times in {days:.0f} days"
                    ),
                    entities=[entity_id],
                    occurrence_count=len(entries),
                    typical_time=f"{hour:02d}:00",
                    confidence=confidence,
                )
                gaps.append(gap)

        gaps.sort(key=lambda g: g.occurrence_count, reverse=True)
        return gaps

    async def get_device_health_report(
        self,
        hours: int = 48,
    ) -> list[DeviceHealthEntry]:
        """Identify devices with unusual or missing activity.

        Args:
            hours: Hours to check for activity

        Returns:
            List of device health entries
        """
        entries = await self._logbook.get_entries(hours=hours)

        # Count state changes per entity
        entity_activity: dict[str, list[ParsedLogbookEntry]] = defaultdict(list)
        for entry in entries:
            if entry.entity_id:
                entity_activity[entry.entity_id].append(entry)

        health_entries = []
        for entity_id, activity in entity_activity.items():
            last_entry = activity[-1]

            # Check for potential issues
            status = "healthy"
            issue = None

            # Very few state changes might indicate a stuck device
            if len(activity) <= 1 and hours >= 24:
                status = "degraded"
                issue = f"Only {len(activity)} state change(s) in {hours}h"

            # Check for unavailable/unknown states
            unavailable_count = sum(1 for e in activity if e.state in ("unavailable", "unknown"))
            if unavailable_count > len(activity) * 0.3:
                status = "unresponsive"
                issue = f"{unavailable_count}/{len(activity)} states are unavailable/unknown"

            health_entries.append(
                DeviceHealthEntry(
                    entity_id=entity_id,
                    status=status,
                    last_seen=last_entry.when,
                    issue=issue,
                    state_change_count=len(activity),
                )
            )

        # Sort: unhealthy first
        priority = {"unresponsive": 0, "anomalous": 1, "degraded": 2, "healthy": 3}
        health_entries.sort(key=lambda h: priority.get(h.status, 3))
        return health_entries


__all__ = [
    "AutomationEffectivenessReport",
    "AutomationGap",
    "BehavioralAnalysisClient",
    "ButtonUsageReport",
    "CorrelationResult",
    "DeviceHealthEntry",
]
