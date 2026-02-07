"""Known HA error patterns and fix suggestions.

Matches log entries against a database of common Home Assistant
errors and provides actionable fix suggestions.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from src.diagnostics.log_parser import ErrorLogEntry, _extract_integration


@dataclass
class _Pattern:
    """A known error pattern with a fix suggestion."""

    regex: re.Pattern
    category: str
    suggestion: str


# Known error patterns covering common HA issues
KNOWN_ERROR_PATTERNS: list[_Pattern] = [
    # Connection / timeout errors
    _Pattern(
        regex=re.compile(r"(?:unable to connect|connection (?:timed out|refused|lost|error|reset)|timeout|timed?\s*out)", re.IGNORECASE),
        category="connection",
        suggestion="Check network connectivity to the device/service. Verify the host is reachable, firewall rules allow traffic, and the service is running. If using IP addresses, confirm they haven't changed (consider using hostnames or static IPs).",
    ),
    # Authentication failures
    _Pattern(
        regex=re.compile(r"(?:auth(?:entication|orization)\s+failed|invalid\s+credentials|access\s+denied|unauthorized|401)", re.IGNORECASE),
        category="authentication",
        suggestion="Re-authenticate the integration. Check that API keys, passwords, or tokens are correct and haven't expired. For cloud integrations, try re-linking the account.",
    ),
    # Device unavailable
    _Pattern(
        regex=re.compile(r"(?:device\s+.*?(?:is\s+)?unavailable|unavailable\s+(?:device|entity|sensor)|not\s+responding)", re.IGNORECASE),
        category="device_unavailable",
        suggestion="Check the device is powered on and within range. For battery devices, check battery level. For Zigbee/Z-Wave, ensure the device is within mesh range. Try power-cycling the device.",
    ),
    # Config / schema validation errors
    _Pattern(
        regex=re.compile(r"(?:invalid\s+config|schema\s+validation|expected\s+\w+\s+for|configuration\s+error|yaml\s+error|invalid\s+(?:entry|value|type))", re.IGNORECASE),
        category="config_error",
        suggestion="Review the configuration file for syntax errors. Check YAML indentation, data types (strings vs numbers), and required fields. Use the HA config check tool before restarting.",
    ),
    # Integration setup failures
    _Pattern(
        regex=re.compile(r"(?:error\s+setting\s+up|setup\s+(?:failed|error)|ConfigEntryNotReady|failed\s+to\s+(?:set\s*up|initialize|load))", re.IGNORECASE),
        category="setup_failure",
        suggestion="The integration failed to initialize. Try reloading the integration from Settings > Integrations. If it persists, check the integration's configuration and dependencies. A HA restart may help.",
    ),
    # Database / recorder errors
    _Pattern(
        regex=re.compile(r"(?:database|recorder|sqlite|disk\s+I/O|journal\s+mode|corrupt|migration\s+failed)", re.IGNORECASE),
        category="database",
        suggestion="Check available disk space. If using SQLite, the database may be corrupted -- try stopping HA, backing up, and deleting home-assistant_v2.db (it will be recreated). Consider switching to MariaDB/PostgreSQL for reliability.",
    ),
]


def match_known_errors(entry: ErrorLogEntry) -> list[dict]:
    """Match a log entry against known error patterns.

    Args:
        entry: A parsed log entry

    Returns:
        List of matching pattern dicts with category and suggestion.
        Empty list if no patterns match.
    """
    matches = []
    text = f"{entry.message} {entry.exception or ''}"

    for pattern in KNOWN_ERROR_PATTERNS:
        if pattern.regex.search(text):
            matches.append({
                "category": pattern.category,
                "suggestion": pattern.suggestion,
                "pattern": pattern.regex.pattern[:80],
            })

    return matches


def analyze_errors(entries: list[ErrorLogEntry]) -> list[dict]:
    """Batch-analyze log entries for known issues.

    Groups similar errors, matches against known patterns, and
    returns deduplicated issues with counts and suggestions.

    Args:
        entries: List of parsed log entries

    Returns:
        List of issue dicts, each with message, count, integration,
        category, and suggestion.
    """
    if not entries:
        return []

    # Group by (message, logger) to find repeated errors
    groups: dict[tuple[str, str], list[ErrorLogEntry]] = {}
    for entry in entries:
        key = (entry.message, entry.logger)
        groups.setdefault(key, []).append(entry)

    issues = []
    for (message, logger), group in groups.items():
        integration = _extract_integration(logger)
        representative = group[0]
        matches = match_known_errors(representative)

        if matches:
            # Use the first matching pattern
            best_match = matches[0]
            issues.append({
                "message": message,
                "count": len(group),
                "integration": integration,
                "level": representative.level,
                "category": best_match["category"],
                "suggestion": best_match["suggestion"],
            })

    # Sort by count descending
    issues.sort(key=lambda x: x["count"], reverse=True)
    return issues
