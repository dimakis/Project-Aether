"""Tests for specialist delegation tools.

TDD: Red phase — tests define the contract for tools that let the
Architect delegate to DS team specialists and request synthesis.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.specialist_tools import (
    _select_specialists,
    consult_behavioral_analyst,
    consult_diagnostic_analyst,
    consult_energy_analyst,
    get_specialist_tools,
    request_synthesis_review,
)


class TestConsultEnergyAnalyst:
    """Test energy specialist delegation."""

    @pytest.mark.asyncio
    async def test_returns_findings_summary(self):
        """Tool should return a summary of energy findings."""
        mock_analyst = MagicMock()
        mock_analyst.invoke = AsyncMock(
            return_value={
                "insights": [
                    {"title": "High peak usage", "description": "Peak at 18:00"},
                ],
                "team_analysis": MagicMock(findings=[]),
            }
        )

        with patch(
            "src.tools.specialist_tools.EnergyAnalyst",
            return_value=mock_analyst,
        ):
            result = await consult_energy_analyst.ainvoke(
                {
                    "query": "Analyze my energy usage",
                    "hours": 24,
                }
            )

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
            result = await consult_energy_analyst.ainvoke(
                {
                    "query": "Analyze energy",
                }
            )

        assert "error" in result.lower() or "failed" in result.lower()


class TestConsultBehavioralAnalyst:
    """Test behavioral specialist delegation."""

    @pytest.mark.asyncio
    async def test_returns_findings_summary(self):
        mock_analyst = MagicMock()
        mock_analyst.invoke = AsyncMock(
            return_value={
                "insights": [
                    {"title": "Manual override pattern", "description": "High override rate"},
                ],
                "team_analysis": MagicMock(findings=[]),
            }
        )

        with patch(
            "src.tools.specialist_tools.BehavioralAnalyst",
            return_value=mock_analyst,
        ):
            result = await consult_behavioral_analyst.ainvoke(
                {
                    "query": "Analyze user behavior patterns",
                    "hours": 168,
                }
            )

        assert isinstance(result, str)
        assert len(result) > 0


class TestConsultDiagnosticAnalyst:
    """Test diagnostic specialist delegation."""

    @pytest.mark.asyncio
    async def test_returns_findings_summary(self):
        mock_analyst = MagicMock()
        mock_analyst.invoke = AsyncMock(
            return_value={
                "insights": [
                    {"title": "Sensor offline", "description": "Temp sensor offline 3h"},
                ],
                "team_analysis": MagicMock(findings=[]),
            }
        )

        with patch(
            "src.tools.specialist_tools.DiagnosticAnalyst",
            return_value=mock_analyst,
        ):
            result = await consult_diagnostic_analyst.ainvoke(
                {
                    "query": "Check system health",
                    "entity_ids": ["sensor.temperature_bedroom"],
                }
            )

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
        mock_synth.synthesize = AsyncMock(
            return_value=ta.model_copy(
                update={
                    "consensus": "LLM: Enhanced synthesis with reasoning",
                    "synthesis_strategy": "llm",
                }
            )
        )

        with patch(
            "src.tools.specialist_tools.LLMSynthesizer",
            return_value=mock_synth,
        ):
            result = await request_synthesis_review.ainvoke(
                {
                    "reason": "Conflicting findings need deeper analysis",
                }
            )

        assert isinstance(result, str)


class TestConsultDashboardDesigner:
    """Test dashboard designer delegation tool."""

    @pytest.mark.asyncio
    async def test_returns_designer_response(self):
        """Tool should delegate to DashboardDesignerAgent and return its response."""
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(
            return_value={
                "messages": [
                    MagicMock(content="Here is the Lovelace YAML for your energy dashboard.")
                ],
            }
        )

        with (
            patch(
                "src.agents.dashboard_designer.DashboardDesignerAgent",
                return_value=mock_agent,
            ),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
        ):
            from src.tools.specialist_tools import consult_dashboard_designer

            result = await consult_dashboard_designer.ainvoke(
                {
                    "query": "Update my energy dashboard",
                }
            )

        assert isinstance(result, str)
        assert "Lovelace YAML" in result or "energy dashboard" in result

    @pytest.mark.asyncio
    async def test_handles_errors_gracefully(self):
        """Tool should return error message on failure."""
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(side_effect=Exception("Dashboard generation failed"))

        with (
            patch(
                "src.agents.dashboard_designer.DashboardDesignerAgent",
                return_value=mock_agent,
            ),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
        ):
            from src.tools.specialist_tools import consult_dashboard_designer

            result = await consult_dashboard_designer.ainvoke(
                {
                    "query": "Update my energy dashboard",
                }
            )

        assert "failed" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_disabled_message_when_agent_disabled(self):
        """Tool should return disabled message when agent is not enabled."""
        with (
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=False)),
        ):
            from src.tools.specialist_tools import consult_dashboard_designer

            result = await consult_dashboard_designer.ainvoke(
                {
                    "query": "Update my dashboard",
                }
            )

        assert "disabled" in result.lower()

    @pytest.mark.asyncio
    async def test_emits_delegation_events(self):
        """Tool should emit delegation events for topology tracking."""
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(
            return_value={
                "messages": [MagicMock(content="Dashboard ready.")],
            }
        )

        with (
            patch(
                "src.agents.dashboard_designer.DashboardDesignerAgent",
                return_value=mock_agent,
            ),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools.emit_delegation") as mock_deleg,
            patch("src.tools.specialist_tools.emit_progress") as mock_prog,
        ):
            from src.tools.specialist_tools import consult_dashboard_designer

            await consult_dashboard_designer.ainvoke(
                {
                    "query": "Update my energy dashboard",
                }
            )

        # Should delegate architect -> dashboard_designer
        mock_deleg.assert_any_call(
            "architect",
            "dashboard_designer",
            "Update my energy dashboard",
        )
        # Should emit agent_start and agent_end
        mock_prog.assert_any_call(
            "agent_start",
            "dashboard_designer",
            "Dashboard Designer started",
        )
        mock_prog.assert_any_call(
            "agent_end",
            "dashboard_designer",
            "Dashboard Designer completed",
        )


class TestConsultDataScienceTeamParallel:
    """Test that consult_data_science_team runs specialists in parallel."""

    @pytest.mark.asyncio
    async def test_specialists_run_concurrently(self):
        """Specialists should run in parallel via asyncio.gather, not sequentially."""
        call_times: list[tuple[str, float, float]] = []

        async def _slow_runner(name: str):
            """Simulate a specialist that takes ~0.1s."""

            async def _run(query: str, hours: int, entity_ids: list | None) -> str:
                start = asyncio.get_event_loop().time()
                await asyncio.sleep(0.1)
                end = asyncio.get_event_loop().time()
                call_times.append((name, start, end))
                return f"{name} findings"

            return _run

        with (
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch(
                "src.tools.specialist_tools._run_energy",
                await _slow_runner("energy"),
            ),
            patch(
                "src.tools.specialist_tools._run_behavioral",
                await _slow_runner("behavioral"),
            ),
            patch(
                "src.tools.specialist_tools._run_diagnostic",
                await _slow_runner("diagnostic"),
            ),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
            patch("src.tools.specialist_tools.reset_team_analysis"),
            patch("src.tools.specialist_tools._get_or_create_team_analysis"),
            patch("src.tools.specialist_tools._set_team_analysis"),
            patch(
                "src.agents.execution_context.get_execution_context",
                return_value=MagicMock(team_analysis=None),
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke(
                {"query": "energy patterns and health issues and automation gaps"}
            )

        # All 3 should have been called
        assert len(call_times) == 3

        # If parallel, total wall time should be ~0.1s (not ~0.3s)
        # Check that their start times overlap (they started before others finished)
        starts = [t[1] for t in call_times]
        ends = [t[2] for t in call_times]
        wall_time = max(ends) - min(starts)
        # Parallel: wall_time ~ 0.1s. Sequential: wall_time ~ 0.3s.
        assert wall_time < 0.25, (
            f"Specialists ran sequentially (wall_time={wall_time:.3f}s). "
            "Expected parallel execution with wall_time < 0.25s."
        )

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_block_others(self):
        """If one specialist fails, others should still complete."""

        async def _failing_runner(query: str, hours: int, entity_ids: list | None) -> str:
            raise Exception("Energy analyst exploded")

        async def _ok_runner(query: str, hours: int, entity_ids: list | None) -> str:
            return "Found 1 insight(s):\n1. **Test**: OK"

        with (
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools._run_energy", _failing_runner),
            patch("src.tools.specialist_tools._run_behavioral", _ok_runner),
            patch("src.tools.specialist_tools._run_diagnostic", _ok_runner),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
            patch("src.tools.specialist_tools.reset_team_analysis"),
            patch("src.tools.specialist_tools._get_or_create_team_analysis"),
            patch("src.tools.specialist_tools._set_team_analysis"),
            patch(
                "src.agents.execution_context.get_execution_context",
                return_value=MagicMock(team_analysis=None),
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            result = await consult_data_science_team.ainvoke(
                {"query": "energy patterns and health issues and automation gaps"}
            )

        # Result should contain successful findings and the failure message
        assert "Behavioral" in result or "Diagnostic" in result
        assert "failed" in result.lower() or "Energy" in result

    @pytest.mark.asyncio
    async def test_report_includes_all_specialist_results(self):
        """Report should include results from all selected specialists."""

        async def _make_runner(name: str):
            async def _run(query: str, hours: int, entity_ids: list | None) -> str:
                return f"Found 1 insight(s):\n1. **{name} finding**: Details"

            return _run

        with (
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools._run_energy", await _make_runner("Energy")),
            patch("src.tools.specialist_tools._run_behavioral", await _make_runner("Behavioral")),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
            patch("src.tools.specialist_tools.reset_team_analysis"),
            patch("src.tools.specialist_tools._get_or_create_team_analysis"),
            patch("src.tools.specialist_tools._set_team_analysis"),
            patch(
                "src.agents.execution_context.get_execution_context",
                return_value=MagicMock(team_analysis=None),
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            result = await consult_data_science_team.ainvoke(
                {
                    "query": "energy costs and automation gaps",
                    "specialists": ["energy", "behavioral"],
                }
            )

        assert "Energy" in result
        assert "Behavioral" in result


class TestSelectSpecialists:
    """Test keyword-based specialist routing."""

    def test_energy_keywords(self):
        selected = _select_specialists("Why is my energy consumption so high?")
        assert "energy" in selected

    def test_behavioral_keywords(self):
        selected = _select_specialists("Find automation gaps in my routines")
        assert "behavioral" in selected

    def test_diagnostic_keywords(self):
        selected = _select_specialists("My sensor is offline and showing errors")
        assert "diagnostic" in selected

    def test_explicit_override(self):
        selected = _select_specialists("anything", specialists=["diagnostic"])
        assert selected == ["diagnostic"]

    def test_fallback_to_all(self):
        selected = _select_specialists("tell me about my home")
        assert sorted(selected) == ["behavioral", "diagnostic", "energy"]


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
