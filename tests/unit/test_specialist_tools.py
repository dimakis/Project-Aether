"""Tests for specialist delegation tools.

TDD: Red phase — tests define the contract for tools that let the
Architect delegate to DS team specialists and request synthesis.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.specialist_tools import (
    consult_energy_analyst,
    consult_behavioral_analyst,
    consult_diagnostic_analyst,
    request_synthesis_review,
    get_specialist_tools,
)


class TestConsultEnergyAnalyst:
    """Test energy specialist delegation."""

    @pytest.mark.asyncio
    async def test_returns_findings_summary(self):
        """Tool should return a summary of energy findings."""
        mock_analyst = MagicMock()
        mock_analyst.invoke = AsyncMock(return_value={
            "insights": [
                {"title": "High peak usage", "description": "Peak at 18:00"},
            ],
            "team_analysis": MagicMock(findings=[]),
        })

        with patch(
            "src.tools.specialist_tools.EnergyAnalyst",
            return_value=mock_analyst,
        ):
            result = await consult_energy_analyst.ainvoke({
                "query": "Analyze my energy usage",
                "hours": 24,
            })

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_handles_errors_gracefully(self):
        """Tool should return error message on failure."""
        mock_analyst = MagicMock()
        mock_analyst.invoke = AsyncMock(side_effect=Exception("HA unavailable"))

        with patch(
            "src.tools.specialist_tools.EnergyAnalyst",
            return_value=mock_analyst,
        ):
            result = await consult_energy_analyst.ainvoke({
                "query": "Analyze energy",
            })

        assert "error" in result.lower() or "failed" in result.lower()


class TestConsultBehavioralAnalyst:
    """Test behavioral specialist delegation."""

    @pytest.mark.asyncio
    async def test_returns_findings_summary(self):
        mock_analyst = MagicMock()
        mock_analyst.invoke = AsyncMock(return_value={
            "insights": [
                {"title": "Manual override pattern", "description": "High override rate"},
            ],
            "team_analysis": MagicMock(findings=[]),
        })

        with patch(
            "src.tools.specialist_tools.BehavioralAnalyst",
            return_value=mock_analyst,
        ):
            result = await consult_behavioral_analyst.ainvoke({
                "query": "Analyze user behavior patterns",
                "hours": 168,
            })

        assert isinstance(result, str)
        assert len(result) > 0


class TestConsultDiagnosticAnalyst:
    """Test diagnostic specialist delegation."""

    @pytest.mark.asyncio
    async def test_returns_findings_summary(self):
        mock_analyst = MagicMock()
        mock_analyst.invoke = AsyncMock(return_value={
            "insights": [
                {"title": "Sensor offline", "description": "Temp sensor offline 3h"},
            ],
            "team_analysis": MagicMock(findings=[]),
        })

        with patch(
            "src.tools.specialist_tools.DiagnosticAnalyst",
            return_value=mock_analyst,
        ):
            result = await consult_diagnostic_analyst.ainvoke({
                "query": "Check system health",
                "entity_ids": ["sensor.temperature_bedroom"],
            })

        assert isinstance(result, str)


class TestRequestSynthesisReview:
    """Test LLM synthesis review tool."""

    @pytest.mark.asyncio
    async def test_returns_synthesis_result(self):
        """Should invoke LLM synthesizer and return enhanced consensus."""
        from src.graph.state import SpecialistFinding, TeamAnalysis

        ta = TeamAnalysis(
            request_id="synth-001",
            request_summary="Test synthesis",
            findings=[
                SpecialistFinding(
                    specialist="energy_analyst",
                    finding_type="insight",
                    title="High usage",
                    description="High energy usage detected",
                ),
            ],
            consensus="Programmatic: 1 finding from 1 specialist.",
            synthesis_strategy="programmatic",
        )

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=ta.model_copy(
            update={
                "consensus": "LLM: Enhanced synthesis with reasoning",
                "synthesis_strategy": "llm",
            }
        ))

        with patch(
            "src.tools.specialist_tools.LLMSynthesizer",
            return_value=mock_synth,
        ):
            result = await request_synthesis_review.ainvoke({
                "reason": "Conflicting findings need deeper analysis",
            })

        assert isinstance(result, str)


class TestGetSpecialistTools:
    """Test that all specialist tools are registered."""

    def test_returns_all_four_tools(self):
        tools = get_specialist_tools()
        tool_names = {t.name for t in tools}
        assert "consult_energy_analyst" in tool_names
        assert "consult_behavioral_analyst" in tool_names
        assert "consult_diagnostic_analyst" in tool_names
        assert "request_synthesis_review" in tool_names
