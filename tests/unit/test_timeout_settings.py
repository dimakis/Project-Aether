"""Unit tests for tool timeout settings.

TDD: Timeout configuration for tool execution.
"""

import pytest

from src.settings import Settings


class TestTimeoutSettings:
    """Tests for tool timeout configuration."""

    def test_default_tool_timeout(self):
        """Default tool timeout should be 30 seconds."""
        settings = Settings(
            _env_file=None,  # Don't load .env in tests
            ha_url="http://test:8123",
            ha_token="test",
        )
        assert settings.tool_timeout_seconds == 30

    def test_default_analysis_timeout(self):
        """Default analysis tool timeout should be 180 seconds."""
        settings = Settings(
            _env_file=None,
            ha_url="http://test:8123",
            ha_token="test",
        )
        assert settings.analysis_tool_timeout_seconds == 180

    def test_analysis_tools_set_exists(self):
        """ANALYSIS_TOOLS set should list the long-running analysis tools."""
        from src.settings import ANALYSIS_TOOLS

        assert isinstance(ANALYSIS_TOOLS, frozenset)
        assert "consult_data_science_team" in ANALYSIS_TOOLS
        assert "consult_energy_analyst" in ANALYSIS_TOOLS
        assert "consult_behavioral_analyst" in ANALYSIS_TOOLS
        assert "consult_diagnostic_analyst" in ANALYSIS_TOOLS
        # HA query tools should NOT be in the set
        assert "get_entity_state" not in ANALYSIS_TOOLS
        assert "search_entities" not in ANALYSIS_TOOLS
