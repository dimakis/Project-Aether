"""Tests for the dual synthesizer module.

TDD: Red phase — tests define contracts for:
1. ProgrammaticSynthesizer (deterministic, rule-based)
2. LLMSynthesizer (LLM-backed, on-demand)
3. synthesize() dispatcher
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.synthesis import (
    LLMSynthesizer,
    ProgrammaticSynthesizer,
    SynthesisStrategy,
    synthesize,
)
from src.graph.state import (
    AutomationSuggestion,
    SpecialistFinding,
    TeamAnalysis,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _energy_finding(**overrides) -> SpecialistFinding:
    defaults = {
        "specialist": "energy_analyst",
        "finding_type": "insight",
        "title": "High overnight HVAC usage",
        "description": "HVAC runs 8h overnight at full power.",
        "confidence": 0.85,
        "entities": ["climate.main_hvac"],
        "evidence": {"avg_kwh": 4.2, "hours": 8},
    }
    defaults.update(overrides)
    return SpecialistFinding(**defaults)


def _behavioral_finding(**overrides) -> SpecialistFinding:
    defaults = {
        "specialist": "behavioral_analyst",
        "finding_type": "insight",
        "title": "Scheduled heating pattern",
        "description": "Heating runs on winter schedule, occupancy normal.",
        "confidence": 0.90,
        "entities": ["climate.main_hvac", "binary_sensor.presence"],
        "evidence": {"schedule": "winter", "occupancy_ratio": 0.95},
    }
    defaults.update(overrides)
    return SpecialistFinding(**defaults)


def _diagnostic_finding(**overrides) -> SpecialistFinding:
    defaults = {
        "specialist": "diagnostic_analyst",
        "finding_type": "concern",
        "title": "Temperature sensor drift",
        "description": "Bedroom sensor shows 2°C drift over 7 days.",
        "confidence": 0.75,
        "entities": ["sensor.temperature_bedroom"],
        "evidence": {"drift_celsius": 2.0, "period_days": 7},
    }
    defaults.update(overrides)
    return SpecialistFinding(**defaults)


def _team_analysis_with_findings() -> TeamAnalysis:
    """TeamAnalysis populated by three specialists with cross-references."""
    energy = _energy_finding()
    behavioral = _behavioral_finding(
        cross_references=[energy.id],
    )
    diagnostic = _diagnostic_finding()
    return TeamAnalysis(
        request_id="test-001",
        request_summary="Analyze home energy and health",
        findings=[energy, behavioral, diagnostic],
    )


# ---------------------------------------------------------------------------
# ProgrammaticSynthesizer
# ---------------------------------------------------------------------------


class TestProgrammaticSynthesizer:
    """Test the deterministic, rule-based synthesizer."""

    def test_empty_findings_produces_empty_synthesis(self):
        """No findings should produce a minimal synthesis."""
        ta = TeamAnalysis(
            request_id="empty-001",
            request_summary="Empty analysis",
        )
        synth = ProgrammaticSynthesizer()
        result = synth.synthesize(ta)

        assert result.consensus is not None
        assert result.synthesis_strategy == "programmatic"
        assert result.conflicts == []
        assert result.holistic_recommendations == []

    def test_single_specialist_produces_consensus(self):
        """One specialist's findings should still produce a consensus."""
        ta = TeamAnalysis(
            request_id="single-001",
            request_summary="Energy-only analysis",
            findings=[_energy_finding()],
        )
        synth = ProgrammaticSynthesizer()
        result = synth.synthesize(ta)

        assert result.synthesis_strategy == "programmatic"
        assert result.consensus is not None
        assert len(result.consensus) > 0

    def test_multi_specialist_groups_by_entity(self):
        """Findings from multiple specialists on the same entity should be grouped."""
        ta = _team_analysis_with_findings()
        synth = ProgrammaticSynthesizer()
        result = synth.synthesize(ta)

        assert result.synthesis_strategy == "programmatic"
        # climate.main_hvac appears in both energy and behavioral findings
        assert result.consensus is not None
        # Should mention multi-specialist corroboration
        assert len(result.holistic_recommendations) > 0

    def test_cross_referenced_findings_boost_recommendations(self):
        """Findings confirmed by 2+ specialists should rank higher."""
        energy = _energy_finding(confidence=0.7)
        behavioral = _behavioral_finding(
            confidence=0.9,
            cross_references=[energy.id],
        )
        ta = TeamAnalysis(
            request_id="boost-001",
            request_summary="Cross-ref test",
            findings=[energy, behavioral],
        )
        synth = ProgrammaticSynthesizer()
        result = synth.synthesize(ta)

        assert result.synthesis_strategy == "programmatic"
        # Should have recommendations since there are findings
        assert len(result.holistic_recommendations) >= 1

    def test_conflicting_findings_are_detected(self):
        """Conflicting findings on the same entity should be flagged."""
        energy = _energy_finding(
            finding_type="concern",
            title="Wasteful HVAC usage",
            description="HVAC runs unnecessarily overnight — waste.",
        )
        behavioral = _behavioral_finding(
            finding_type="insight",
            title="Expected heating pattern",
            description="HVAC follows scheduled winter heating — not waste.",
            entities=["climate.main_hvac"],  # Same entity
        )
        ta = TeamAnalysis(
            request_id="conflict-001",
            request_summary="Conflict test",
            findings=[energy, behavioral],
        )
        synth = ProgrammaticSynthesizer()
        result = synth.synthesize(ta)

        assert len(result.conflicts) >= 1

    def test_automation_suggestions_are_merged(self):
        """Automation suggestions from findings should appear in recommendations."""
        suggestion = AutomationSuggestion(
            pattern="HVAC waste overnight",
            entities=["climate.main_hvac"],
            proposed_trigger="time: 23:00",
            proposed_action="set HVAC to eco mode",
            confidence=0.85,
            evidence={"savings_pct": 30},
            source_insight_type="energy_optimization",
        )
        energy = _energy_finding(
            automation_suggestion=suggestion,
        )
        ta = TeamAnalysis(
            request_id="auto-001",
            request_summary="Suggestion test",
            findings=[energy],
        )
        synth = ProgrammaticSynthesizer()
        result = synth.synthesize(ta)

        # Recommendations should include the automation suggestion
        assert any(
            "eco" in r.lower() or "hvac" in r.lower() for r in result.holistic_recommendations
        )

    def test_does_not_mutate_input(self):
        """Synthesizer should return a new TeamAnalysis, not mutate the input."""
        ta = _team_analysis_with_findings()
        original_consensus = ta.consensus
        synth = ProgrammaticSynthesizer()
        result = synth.synthesize(ta)

        assert ta.consensus == original_consensus  # Input unchanged
        assert result.consensus is not None  # Output has consensus
        assert result is not ta  # Different objects


# ---------------------------------------------------------------------------
# LLMSynthesizer
# ---------------------------------------------------------------------------


class TestLLMSynthesizer:
    """Test the LLM-backed synthesizer."""

    @pytest.mark.asyncio
    async def test_calls_llm_with_findings_context(self):
        """LLMSynthesizer should call the LLM with all findings as context."""
        ta = _team_analysis_with_findings()

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content=(
                '{"consensus": "Agreed analysis", '
                '"conflicts": [], '
                '"holistic_recommendations": ["Install eco timer"]}'
            )
        )
        synth = LLMSynthesizer(llm=mock_llm)
        result = await synth.synthesize(ta)

        assert result.synthesis_strategy == "llm"
        assert result.consensus == "Agreed analysis"
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_llm_failure_gracefully(self):
        """If the LLM fails, synthesizer should return a sensible fallback."""
        ta = _team_analysis_with_findings()

        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("LLM unavailable")

        synth = LLMSynthesizer(llm=mock_llm)
        result = await synth.synthesize(ta)

        assert result.synthesis_strategy == "llm"
        assert result.consensus is not None
        assert "error" in result.consensus.lower() or "failed" in result.consensus.lower()

    @pytest.mark.asyncio
    async def test_preserves_original_findings(self):
        """LLM synthesis should preserve the original findings."""
        ta = _team_analysis_with_findings()
        original_count = len(ta.findings)

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content=('{"consensus": "OK", "conflicts": [], "holistic_recommendations": []}')
        )
        synth = LLMSynthesizer(llm=mock_llm)
        result = await synth.synthesize(ta)

        assert len(result.findings) == original_count


# ---------------------------------------------------------------------------
# synthesize() dispatcher
# ---------------------------------------------------------------------------


class TestSynthesizeDispatcher:
    """Test the top-level synthesize() function."""

    def test_programmatic_strategy(self):
        """synthesize() with programmatic strategy uses ProgrammaticSynthesizer."""
        ta = _team_analysis_with_findings()
        result = synthesize(ta, strategy=SynthesisStrategy.PROGRAMMATIC)

        assert result.synthesis_strategy == "programmatic"

    @pytest.mark.asyncio
    async def test_default_strategy_is_programmatic(self):
        """Without a strategy, synthesize() defaults to programmatic."""
        ta = _team_analysis_with_findings()
        result = synthesize(ta)

        assert result.synthesis_strategy == "programmatic"
