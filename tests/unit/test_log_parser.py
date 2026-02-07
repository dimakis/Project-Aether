"""Unit tests for HA error log parser.

TDD: Tests written FIRST to define the API contract for
ErrorLogEntry, parse_error_log, categorize_by_integration,
find_patterns, and get_error_summary.
"""

import pytest

from src.diagnostics.log_parser import (
    ErrorLogEntry,
    categorize_by_integration,
    find_patterns,
    get_error_summary,
    parse_error_log,
)

# Realistic HA log sample
SAMPLE_LOG = """\
2026-02-06 10:15:23.456 ERROR (MainThread) [homeassistant.components.zha] Failed to connect to ZHA coordinator
2026-02-06 10:15:24.789 WARNING (MainThread) [homeassistant.components.mqtt] MQTT broker connection lost
2026-02-06 10:16:00.123 ERROR (MainThread) [homeassistant.components.zha] Failed to connect to ZHA coordinator
2026-02-06 10:17:45.456 ERROR (MainThread) [homeassistant.components.sensor] Timeout fetching data from sensor.temperature
2026-02-06 10:18:00.000 INFO (MainThread) [homeassistant.core] Bus:Handling <Event state_changed>
2026-02-06 10:20:00.000 ERROR (MainThread) [homeassistant.components.zha] Failed to connect to ZHA coordinator
"""

MULTILINE_LOG = """\
2026-02-06 10:15:23.456 ERROR (MainThread) [homeassistant.components.zha] Error setting up entry
Traceback (most recent call last):
  File "/usr/lib/python3.11/site-packages/homeassistant/config_entries.py", line 123
    raise ConfigEntryNotReady
homeassistant.exceptions.ConfigEntryNotReady: Unable to connect
2026-02-06 10:16:00.000 WARNING (MainThread) [homeassistant.components.mqtt] Connection lost
"""


class TestParseErrorLog:
    """Tests for parse_error_log function."""

    def test_parses_standard_log_entries(self):
        """Test parsing standard HA log format."""
        entries = parse_error_log(SAMPLE_LOG)

        assert len(entries) >= 5
        assert all(isinstance(e, ErrorLogEntry) for e in entries)

    def test_entry_has_required_fields(self):
        """Test each entry has timestamp, level, logger, message."""
        entries = parse_error_log(SAMPLE_LOG)
        first = entries[0]

        assert first.timestamp is not None
        assert first.level == "ERROR"
        assert "zha" in first.logger.lower()
        assert "connect" in first.message.lower()

    def test_handles_empty_input(self):
        """Test empty log string returns empty list."""
        assert parse_error_log("") == []
        assert parse_error_log("   \n  ") == []

    def test_handles_malformed_lines(self):
        """Test graceful handling of non-log lines."""
        log = "This is not a log line\nNeither is this\n"
        entries = parse_error_log(log)
        assert entries == []

    def test_parses_all_levels(self):
        """Test parsing ERROR, WARNING, INFO levels."""
        entries = parse_error_log(SAMPLE_LOG)
        levels = {e.level for e in entries}

        assert "ERROR" in levels
        assert "WARNING" in levels
        assert "INFO" in levels

    def test_parses_multiline_exceptions(self):
        """Test that multiline tracebacks are captured in exception field."""
        entries = parse_error_log(MULTILINE_LOG)

        error_entry = entries[0]
        assert error_entry.level == "ERROR"
        assert error_entry.exception is not None
        assert "Traceback" in error_entry.exception
        assert "ConfigEntryNotReady" in error_entry.exception


class TestCategorizeByIntegration:
    """Tests for categorize_by_integration function."""

    def test_groups_by_integration(self):
        """Test entries are grouped by integration name."""
        entries = parse_error_log(SAMPLE_LOG)
        categorized = categorize_by_integration(entries)

        assert "zha" in categorized
        assert "mqtt" in categorized
        assert len(categorized["zha"]) == 3  # 3 ZHA errors

    def test_empty_input(self):
        """Test empty entries returns empty dict."""
        assert categorize_by_integration([]) == {}

    def test_extracts_integration_from_logger(self):
        """Test integration name is extracted from logger path."""
        entries = parse_error_log(SAMPLE_LOG)
        categorized = categorize_by_integration(entries)

        # Should extract 'zha' from 'homeassistant.components.zha'
        for integration in categorized:
            assert "homeassistant" not in integration


class TestFindPatterns:
    """Tests for find_patterns function."""

    def test_detects_recurring_errors(self):
        """Test detection of recurring error messages."""
        entries = parse_error_log(SAMPLE_LOG)
        patterns = find_patterns(entries)

        assert len(patterns) >= 1
        # ZHA connect error appears 3 times
        zha_pattern = next(
            (p for p in patterns if "zha" in p.get("message", "").lower()
             or "connect" in p.get("message", "").lower()),
            None,
        )
        assert zha_pattern is not None
        assert zha_pattern["count"] >= 3

    def test_returns_empty_for_unique_errors(self):
        """Test no patterns when all errors are unique."""
        log = "2026-02-06 10:00:00.000 ERROR (MainThread) [ha.comp.a] Error A\n"
        entries = parse_error_log(log)
        patterns = find_patterns(entries)
        assert patterns == []

    def test_empty_input(self):
        """Test empty entries returns empty list."""
        assert find_patterns([]) == []


class TestGetErrorSummary:
    """Tests for get_error_summary function."""

    def test_summary_has_counts_by_level(self):
        """Test summary includes error/warning/info counts."""
        entries = parse_error_log(SAMPLE_LOG)
        summary = get_error_summary(entries)

        assert "counts_by_level" in summary
        assert summary["counts_by_level"]["ERROR"] >= 3
        assert summary["counts_by_level"]["WARNING"] >= 1

    def test_summary_has_top_integrations(self):
        """Test summary includes top error-producing integrations."""
        entries = parse_error_log(SAMPLE_LOG)
        summary = get_error_summary(entries)

        assert "top_integrations" in summary
        # ZHA should be top (3 errors)
        assert summary["top_integrations"][0][0] == "zha"

    def test_summary_has_total_count(self):
        """Test summary includes total entry count."""
        entries = parse_error_log(SAMPLE_LOG)
        summary = get_error_summary(entries)

        assert "total" in summary
        assert summary["total"] == len(entries)

    def test_empty_input(self):
        """Test empty entries returns zeroed summary."""
        summary = get_error_summary([])
        assert summary["total"] == 0
