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


class TestConsultDashboardDesigner:
    """Test dashboard designer delegation tool."""

    @pytest.mark.asyncio
    async def test_returns_designer_response(self):
        """Tool should delegate to DashboardDesignerAgent and return its response."""
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Here is the Lovelace YAML for your energy dashboard.")],
        })

        with (
            patch(
                "src.tools.specialist_tools.DashboardDesignerAgent",
                return_value=mock_agent,
            ),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
        ):
            from src.tools.specialist_tools import consult_dashboard_designer

            result = await consult_dashboard_designer.ainvoke({
                "query": "Update my energy dashboard",
            })

        assert isinstance(result, str)
        assert "Lovelace YAML" in result or "energy dashboard" in result

    @pytest.mark.asyncio
    async def test_handles_errors_gracefully(self):
        """Tool should return error message on failure."""
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(side_effect=Exception("Dashboard generation failed"))

        with (
            patch(
                "src.tools.specialist_tools.DashboardDesignerAgent",
                return_value=mock_agent,
            ),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
        ):
            from src.tools.specialist_tools import consult_dashboard_designer

            result = await consult_dashboard_designer.ainvoke({
                "query": "Update my energy dashboard",
            })

        assert "failed" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_disabled_message_when_agent_disabled(self):
        """Tool should return disabled message when agent is not enabled."""
        with (
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=False)),
        ):
            from src.tools.specialist_tools import consult_dashboard_designer

            result = await consult_dashboard_designer.ainvoke({
                "query": "Update my dashboard",
            })

        assert "disabled" in result.lower()

    @pytest.mark.asyncio
    async def test_emits_delegation_events(self):
        """Tool should emit delegation events for topology tracking."""
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Dashboard ready.")],
        })

        with (
            patch(
                "src.tools.specialist_tools.DashboardDesignerAgent",
                return_value=mock_agent,
            ),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools.emit_delegation") as mock_deleg,
            patch("src.tools.specialist_tools.emit_progress") as mock_prog,
        ):
            from src.tools.specialist_tools import consult_dashboard_designer

            await consult_dashboard_designer.ainvoke({
                "query": "Update my energy dashboard",
            })

        # Should delegate architect -> dashboard_designer
        mock_deleg.assert_any_call(
            "architect", "dashboard_designer", "Update my energy dashboard",
        )
        # Should emit agent_start and agent_end
        mock_prog.assert_any_call(
            "agent_start", "dashboard_designer", "Dashboard Designer started",
        )
        mock_prog.assert_any_call(
            "agent_end", "dashboard_designer", "Dashboard Designer completed",
        )


class TestGetSpecialistTools:
    """Test that all specialist tools are registered."""

    def test_returns_all_tools_including_dashboard(self):
        tools = get_specialist_tools()
        tool_names = {t.name for t in tools}
        assert "consult_energy_analyst" in tool_names
        assert "consult_behavioral_analyst" in tool_names
        assert "consult_diagnostic_analyst" in tool_names
        assert "request_synthesis_review" in tool_names
        assert "consult_dashboard_designer" in tool_names
        assert "consult_data_science_team" in tool_names
