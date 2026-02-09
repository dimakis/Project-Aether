"""Home Assistant error log parser.

Parses raw HA error log text into structured entries for analysis.
Provides categorization by integration, pattern detection, and summaries.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

# HA log line format: "YYYY-MM-DD HH:MM:SS.mmm LEVEL (Thread) [logger] message"
_LOG_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"  # timestamp
    r"(ERROR|WARNING|INFO|DEBUG|CRITICAL)\s+"  # level
    r"\([^)]*\)\s+"  # thread (ignored)
    r"\[([^\]]+)\]\s+"  # logger
    r"(.+)$"  # message
)

# Extract integration name from logger path like "homeassistant.components.zha"
_INTEGRATION_RE = re.compile(r"homeassistant\.components\.(\w+)")


@dataclass
class ErrorLogEntry:
    """A single parsed log entry from the HA error log."""

    timestamp: str
    level: str
    logger: str
    message: str
    exception: str | None = None


def parse_error_log(log_text: str) -> list[ErrorLogEntry]:
    """Parse raw HA error log text into structured entries.

    Handles multiline entries where tracebacks follow an error line.

    Args:
        log_text: Raw log text from HA /api/error_log

    Returns:
        List of parsed ErrorLogEntry objects
    """
    if not log_text or not log_text.strip():
        return []

    entries: list[ErrorLogEntry] = []
    current_entry: ErrorLogEntry | None = None
    exception_lines: list[str] = []

    for line in log_text.splitlines():
        match = _LOG_LINE_RE.match(line)

        if match:
            # Flush previous entry with any accumulated exception
            if current_entry is not None:
                if exception_lines:
                    current_entry.exception = "\n".join(exception_lines)
                    exception_lines = []
                entries.append(current_entry)

            current_entry = ErrorLogEntry(
                timestamp=match.group(1),
                level=match.group(2),
                logger=match.group(3),
                message=match.group(4),
            )
        elif current_entry is not None and line.strip():
            # Continuation line (traceback or multiline message)
            exception_lines.append(line)

    # Flush last entry
    if current_entry is not None:
        if exception_lines:
            current_entry.exception = "\n".join(exception_lines)
        entries.append(current_entry)

    return entries


def categorize_by_integration(
    entries: list[ErrorLogEntry],
) -> dict[str, list[ErrorLogEntry]]:
    """Group log entries by integration name.

    Extracts integration name from the logger path
    (e.g., 'homeassistant.components.zha' -> 'zha').

    Args:
        entries: Parsed log entries

    Returns:
        Dict mapping integration name to list of entries
    """
    if not entries:
        return {}

    categorized: dict[str, list[ErrorLogEntry]] = {}

    for entry in entries:
        integration = _extract_integration(entry.logger)
        categorized.setdefault(integration, []).append(entry)

    return categorized


def _extract_integration(logger: str) -> str:
    """Extract integration name from logger path.

    Args:
        logger: Logger name (e.g., 'homeassistant.components.zha')

    Returns:
        Integration name (e.g., 'zha') or the last segment of the logger
    """
    match = _INTEGRATION_RE.search(logger)
    if match:
        return match.group(1)
    # Fallback: use last segment
    parts = logger.rsplit(".", maxsplit=1)
    return parts[-1] if parts else logger


def find_patterns(
    entries: list[ErrorLogEntry],
    min_occurrences: int = 2,
) -> list[dict]:
    """Detect recurring error patterns.

    Groups entries by message similarity and returns those appearing
    more than min_occurrences times.

    Args:
        entries: Parsed log entries
        min_occurrences: Minimum count to be considered a pattern

    Returns:
        List of pattern dicts with message, count, level, logger
    """
    if not entries:
        return []

    # Count by (level, message) pairs
    message_counts: Counter[tuple[str, str, str]] = Counter()
    for entry in entries:
        message_counts[(entry.level, entry.logger, entry.message)] += 1

    patterns = []
    for (level, logger, message), count in message_counts.most_common():
        if count >= min_occurrences:
            patterns.append(
                {
                    "level": level,
                    "logger": logger,
                    "message": message,
                    "count": count,
                    "integration": _extract_integration(logger),
                }
            )

    return patterns


def get_error_summary(entries: list[ErrorLogEntry]) -> dict:
    """Get a summary of log entries.

    Args:
        entries: Parsed log entries

    Returns:
        Summary dict with total, counts_by_level, top_integrations
    """
    if not entries:
        return {
            "total": 0,
            "counts_by_level": {},
            "top_integrations": [],
        }

    # Count by level
    level_counts: Counter[str] = Counter()
    integration_counts: Counter[str] = Counter()

    for entry in entries:
        level_counts[entry.level] += 1
        integration = _extract_integration(entry.logger)
        integration_counts[integration] += 1

    return {
        "total": len(entries),
        "counts_by_level": dict(level_counts),
        "top_integrations": integration_counts.most_common(10),
    }
