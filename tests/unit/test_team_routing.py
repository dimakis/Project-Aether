"""Tests for the consult_data_science_team smart routing logic.

Verifies:
- Keyword-based specialist selection from query text
- Explicit specialist override via 'specialists' param
- Fallback to all three when query is ambiguous
- Multi-keyword matching selects multiple specialists
- Team tool invokes correct runners based on routing
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.tools.specialist_tools import (
    _select_specialists,
    consult_data_science_team,
    SPECIALIST_TRIGGERS,
)


# ---------------------------------------------------------------------------
# Keyword routing
# ---------------------------------------------------------------------------


class TestSelectSpecialists:
    """Unit tests for _select_specialists routing logic."""

    def test_energy_keywords(self):
        """Energy-related queries select at least the energy analyst."""
        assert _select_specialists("Check power consumption overnight") == ["energy"]
        assert _select_specialists("Solar battery analysis") == ["energy"]
        assert _select_specialists("What's my kwh cost?") == ["energy"]
        assert "energy" in _select_specialists("Why is energy high?")

    def test_behavioral_keywords(self):
        """Behavioral-related queries select at least the behavioral analyst."""
        assert _select_specialists("Show automation patterns") == ["behavioral"]
        assert _select_specialists("What are my daily habits?") == ["behavioral"]
        assert _select_specialists("How often is the good night scene activated?") == [
            "behavioral"
        ]
        assert _select_specialists("Find automation gaps") == ["behavioral"]

    def test_diagnostic_keywords(self):
        """Diagnostic-related queries select at least the diagnostic analyst."""
        assert _select_specialists("My sensor is offline") == ["diagnostic"]
        assert _select_specialists("Diagnose the unavailable entities") == [
            "diagnostic"
        ]
        assert _select_specialists("Check integration health") == ["diagnostic"]
        assert _select_specialists("Fix the broken thermostat") == ["diagnostic"]

    def test_multi_domain_query(self):
        """Queries spanning domains select multiple specialists."""
        result = _select_specialists("Energy cost vs behavior patterns")
        assert "energy" in result
        assert "behavioral" in result

    def test_ambiguous_query_selects_all(self):
        """Ambiguous or generic queries fall back to all three."""
        result = _select_specialists("Optimize my home")
        assert sorted(result) == ["behavioral", "diagnostic", "energy"]

    def test_empty_query_selects_all(self):
        """Empty query falls back to all three."""
        result = _select_specialists("")
        assert sorted(result) == ["behavioral", "diagnostic", "energy"]

    def test_explicit_override(self):
        """Explicit specialists param overrides keyword matching."""
        result = _select_specialists(
            "Optimize my home", specialists=["diagnostic"]
        )
        assert result == ["diagnostic"]

    def test_explicit_override_multiple(self):
        """Explicit multi-specialist override is honored."""
        result = _select_specialists(
            "anything", specialists=["energy", "behavioral"]
        )
        assert sorted(result) == ["behavioral", "energy"]

    def test_explicit_override_ignores_query(self):
        """When specialists are explicit, query keywords are irrelevant."""
        result = _select_specialists(
            "energy power cost consumption", specialists=["diagnostic"]
        )
        assert result == ["diagnostic"]

    def test_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        assert _select_specialists("ENERGY CONSUMPTION") == ["energy"]
        assert _select_specialists("Sensor Offline") == ["diagnostic"]


class TestSpecialistTriggers:
    """Verify SPECIALIST_TRIGGERS has the expected structure."""

    def test_has_three_domains(self):
        assert set(SPECIALIST_TRIGGERS.keys()) == {
            "energy",
            "behavioral",
            "diagnostic",
        }

    def test_each_domain_has_keywords(self):
        for domain, keywords in SPECIALIST_TRIGGERS.items():
            assert isinstance(keywords, (set, frozenset)), f"{domain} keywords not a set"
            assert len(keywords) >= 5, f"{domain} has too few keywords"


# ---------------------------------------------------------------------------
# Team tool integration (mocked specialists)
# ---------------------------------------------------------------------------


class TestConsultDataScienceTeam:
    """Test that consult_data_science_team invokes the right runners."""

    @pytest.fixture(autouse=True)
    def _patch_runners(self):
        """Patch the internal runners so no real analysts are created."""
        with (
            patch(
                "src.tools.specialist_tools._run_energy",
                new_callable=AsyncMock,
                return_value="Energy OK",
            ) as self.mock_energy,
            patch(
                "src.tools.specialist_tools._run_behavioral",
                new_callable=AsyncMock,
                return_value="Behavioral OK",
            ) as self.mock_behavioral,
            patch(
                "src.tools.specialist_tools._run_diagnostic",
                new_callable=AsyncMock,
                return_value="Diagnostic OK",
            ) as self.mock_diagnostic,
        ):
            yield

    async def test_energy_query_calls_energy_only(self):
        """An energy-specific query only invokes the energy runner."""
        result = await consult_data_science_team.ainvoke(
            {"query": "Check power consumption", "hours": 24}
        )
        self.mock_energy.assert_awaited_once()
        self.mock_behavioral.assert_not_awaited()
        self.mock_diagnostic.assert_not_awaited()
        assert "Energy OK" in result

    async def test_explicit_override_respected(self):
        """Explicit specialists param overrides keyword routing."""
        result = await consult_data_science_team.ainvoke(
            {
                "query": "Check power consumption",
                "specialists": ["diagnostic"],
            }
        )
        self.mock_energy.assert_not_awaited()
        self.mock_diagnostic.assert_awaited_once()
        assert "Diagnostic OK" in result

    async def test_broad_query_calls_all(self):
        """A broad query invokes all three specialists."""
        result = await consult_data_science_team.ainvoke(
            {"query": "Optimize my home"}
        )
        self.mock_energy.assert_awaited_once()
        self.mock_behavioral.assert_awaited_once()
        self.mock_diagnostic.assert_awaited_once()
        assert "Data Science Team Report" in result
        assert "3 specialist(s)" in result

    async def test_custom_query_used_for_routing(self):
        """When custom_query is provided, it drives routing instead of query."""
        result = await consult_data_science_team.ainvoke(
            {
                "query": "general question",
                "custom_query": "Check power consumption",
            }
        )
        self.mock_energy.assert_awaited_once()
        self.mock_behavioral.assert_not_awaited()

    async def test_response_includes_header(self):
        """Response always includes the team report header."""
        result = await consult_data_science_team.ainvoke(
            {"query": "Check power consumption"}
        )
        assert "Data Science Team Report" in result
        assert "1 specialist(s)" in result
