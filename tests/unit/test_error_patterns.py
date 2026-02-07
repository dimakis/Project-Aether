"""Unit tests for HA error pattern matching.

TDD: Tests written FIRST to define the API contract for
KNOWN_ERROR_PATTERNS, match_known_errors, and analyze_errors.
"""

import pytest

from src.diagnostics.error_patterns import (
    analyze_errors,
    match_known_errors,
)
from src.diagnostics.log_parser import ErrorLogEntry


def _make_entry(
    message: str,
    level: str = "ERROR",
    logger: str = "homeassistant.components.test",
) -> ErrorLogEntry:
    """Helper to create a log entry."""
    return ErrorLogEntry(
        timestamp="2026-02-06 10:00:00.000",
        level=level,
        logger=logger,
        message=message,
    )


class TestMatchKnownErrors:
    """Tests for match_known_errors function."""

    def test_matches_connection_timeout(self):
        """Test matching connection timeout errors."""
        entry = _make_entry("Unable to connect to host 192.168.1.100: Connection timed out")
        matches = match_known_errors(entry)

        assert len(matches) >= 1
        assert any("connection" in m["category"].lower() for m in matches)
        assert any(m.get("suggestion") for m in matches)

    def test_matches_auth_failure(self):
        """Test matching authentication failure errors."""
        entry = _make_entry("Authentication failed: invalid credentials")
        matches = match_known_errors(entry)

        assert len(matches) >= 1
        assert any("auth" in m["category"].lower() for m in matches)

    def test_matches_device_unavailable(self):
        """Test matching device unavailable errors."""
        entry = _make_entry("Device sensor.bathroom_motion is unavailable")
        matches = match_known_errors(entry)

        assert len(matches) >= 1
        assert any("unavailable" in m["category"].lower() or "device" in m["category"].lower()
                    for m in matches)

    def test_matches_config_error(self):
        """Test matching configuration/schema errors."""
        entry = _make_entry("Invalid config for integration 'sensor': expected int for 'scan_interval'")
        matches = match_known_errors(entry)

        assert len(matches) >= 1
        assert any("config" in m["category"].lower() for m in matches)

    def test_matches_setup_failed(self):
        """Test matching integration setup failure errors."""
        entry = _make_entry("Error setting up entry for mqtt: ConfigEntryNotReady")
        matches = match_known_errors(entry)

        assert len(matches) >= 1

    def test_matches_database_error(self):
        """Test matching database/recorder errors."""
        entry = _make_entry("Error in database recorder: disk I/O error")
        matches = match_known_errors(entry)

        assert len(matches) >= 1

    def test_no_match_for_unknown_error(self):
        """Test that unrecognized errors return empty matches."""
        entry = _make_entry("Something completely unique happened xyz123")
        matches = match_known_errors(entry)

        assert matches == []

    def test_match_includes_suggestion(self):
        """Test that matches include a fix suggestion."""
        entry = _make_entry("Connection refused by host: 10.0.0.1")
        matches = match_known_errors(entry)

        for m in matches:
            assert "suggestion" in m
            assert len(m["suggestion"]) > 10  # Non-trivial suggestion


class TestAnalyzeErrors:
    """Tests for analyze_errors batch analysis."""

    def test_batch_analysis_returns_issues(self):
        """Test batch analysis of multiple entries."""
        entries = [
            _make_entry("Unable to connect to host: timeout", logger="homeassistant.components.zha"),
            _make_entry("Unable to connect to host: timeout", logger="homeassistant.components.zha"),
            _make_entry("Authentication failed", logger="homeassistant.components.nest"),
            _make_entry("Something unique xyz", logger="homeassistant.components.sensor"),
        ]

        issues = analyze_errors(entries)

        assert len(issues) >= 1
        # Should group the 2 ZHA timeout errors
        assert any(i.get("count", 0) >= 2 for i in issues)

    def test_empty_input(self):
        """Test empty entries returns empty list."""
        assert analyze_errors([]) == []

    def test_deduplicates_similar_issues(self):
        """Test that similar errors are grouped, not listed separately."""
        entries = [
            _make_entry("Unable to connect to host: timeout", logger="homeassistant.components.zha"),
            _make_entry("Unable to connect to host: timeout", logger="homeassistant.components.zha"),
            _make_entry("Unable to connect to host: timeout", logger="homeassistant.components.zha"),
        ]

        issues = analyze_errors(entries)

        # Should produce 1 issue, not 3
        assert len(issues) == 1
        assert issues[0]["count"] == 3

    def test_includes_integration_name(self):
        """Test that issues include the integration name."""
        entries = [
            _make_entry("Connection lost", logger="homeassistant.components.mqtt"),
        ]

        issues = analyze_errors(entries)

        if issues:  # May or may not match a pattern
            for issue in issues:
                assert "integration" in issue
