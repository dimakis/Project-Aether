"""Unit tests for teamwork execution strategy in consult_data_science_team.

Tests T3324-T3327: depth/strategy parameters, sequential execution in
teamwork mode, and parallel (default) preservation.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Helper to build a mock execution context
def _make_mock_ctx(team_analysis=None):
    ctx = MagicMock()
    ctx.team_analysis = team_analysis
    ctx.conversation_id = "test-conv"
    ctx.session_factory = None
    return ctx


# =============================================================================
# T3324: consult_data_science_team accepts depth and strategy params
# =============================================================================


class TestConsultDSTeamParams:
    """Test that the tool function accepts depth/strategy params."""

    def test_tool_has_depth_param(self):
        """consult_data_science_team should accept a `depth` parameter."""
        import inspect

        from src.tools.specialist_tools import consult_data_science_team

        # The @tool decorator wraps the func; check the underlying function
        func = consult_data_science_team
        # The tool's args_schema or the underlying func should list depth
        sig = inspect.signature(func.coroutine)
        assert "depth" in sig.parameters

    def test_tool_has_strategy_param(self):
        """consult_data_science_team should accept a `strategy` parameter."""
        import inspect

        from src.tools.specialist_tools import consult_data_science_team

        sig = inspect.signature(consult_data_science_team.coroutine)
        assert "strategy" in sig.parameters

    def test_depth_default_is_standard(self):
        """depth should default to 'standard'."""
        import inspect

        from src.tools.specialist_tools import consult_data_science_team

        sig = inspect.signature(consult_data_science_team.coroutine)
        assert sig.parameters["depth"].default == "standard"

    def test_strategy_default_is_parallel(self):
        """strategy should default to 'parallel'."""
        import inspect

        from src.tools.specialist_tools import consult_data_science_team

        sig = inspect.signature(consult_data_science_team.coroutine)
        assert sig.parameters["strategy"].default == "parallel"


# =============================================================================
# T3325: Parallel mode preserves current behavior
# =============================================================================


class TestParallelMode:
    """Parallel mode should use asyncio.gather (current behavior)."""

    @pytest.mark.asyncio
    async def test_parallel_runs_all_specialists_concurrently(self):
        """In parallel mode, all specialists should start before any finishes."""
        execution_order: list[str] = []

        async def mock_energy(*a, **kw):
            execution_order.append("energy_start")
            await asyncio.sleep(0.01)
            execution_order.append("energy_end")
            return "Energy: ok"

        async def mock_behavioral(*a, **kw):
            execution_order.append("behavioral_start")
            await asyncio.sleep(0.01)
            execution_order.append("behavioral_end")
            return "Behavioral: ok"

        with (
            patch("src.tools.specialist_tools._run_energy", side_effect=mock_energy),
            patch("src.tools.specialist_tools._run_behavioral", side_effect=mock_behavioral),
            patch("src.tools.specialist_tools._run_diagnostic", AsyncMock(return_value="Diag: ok")),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch(
                "src.tools.specialist_tools._select_specialists",
                return_value=["energy", "behavioral"],
            ),
            patch("src.tools.specialist_tools.reset_team_analysis"),
            patch(
                "src.tools.specialist_tools._get_or_create_team_analysis", return_value=MagicMock()
            ),
            patch("src.tools.specialist_tools._set_team_analysis"),
            patch(
                "src.agents.execution_context.get_execution_context",
                return_value=_make_mock_ctx(),
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke({"query": "test", "strategy": "parallel"})

            # In parallel mode, both should start before either ends
            assert "energy_start" in execution_order
            assert "behavioral_start" in execution_order
            # The starts should come before any ends in parallel
            first_end = min(
                execution_order.index("energy_end"),
                execution_order.index("behavioral_end"),
            )
            assert execution_order.index("energy_start") < first_end
            assert execution_order.index("behavioral_start") < first_end


# =============================================================================
# T3326: Teamwork mode runs specialists sequentially
# =============================================================================


class TestTeamworkMode:
    """Teamwork mode should run specialists sequentially."""

    @pytest.mark.asyncio
    async def test_teamwork_runs_sequentially(self):
        """In teamwork mode, each specialist should complete before the next starts."""
        execution_order: list[str] = []

        async def mock_energy(*a, **kw):
            execution_order.append("energy_start")
            await asyncio.sleep(0.01)
            execution_order.append("energy_end")
            return "Energy: ok"

        async def mock_behavioral(*a, **kw):
            execution_order.append("behavioral_start")
            await asyncio.sleep(0.01)
            execution_order.append("behavioral_end")
            return "Behavioral: ok"

        with (
            patch("src.tools.specialist_tools._run_energy", side_effect=mock_energy),
            patch("src.tools.specialist_tools._run_behavioral", side_effect=mock_behavioral),
            patch("src.tools.specialist_tools._run_diagnostic", AsyncMock(return_value="Diag: ok")),
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch(
                "src.tools.specialist_tools._select_specialists",
                return_value=["energy", "behavioral"],
            ),
            patch("src.tools.specialist_tools.reset_team_analysis"),
            patch(
                "src.tools.specialist_tools._get_or_create_team_analysis", return_value=MagicMock()
            ),
            patch("src.tools.specialist_tools._set_team_analysis"),
            patch(
                "src.agents.execution_context.get_execution_context",
                return_value=_make_mock_ctx(),
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke({"query": "test", "strategy": "teamwork"})

            # In teamwork mode, energy should finish before behavioral starts
            assert execution_order.index("energy_end") < execution_order.index("behavioral_start")


# =============================================================================
# T3327: Depth parameter propagates to AnalysisState
# =============================================================================


class TestDepthPropagation:
    """Depth param should be propagated to runner AnalysisState."""

    @pytest.mark.asyncio
    async def test_depth_passed_to_runner(self):
        """The depth parameter should reach the AnalysisState in runners."""
        from src.graph.state import TeamAnalysis

        captured_states: list[Any] = []
        ta = TeamAnalysis(request_id="test-req", request_summary="test")

        with (
            patch("src.tools.specialist_tools.emit_delegation"),
            patch("src.tools.specialist_tools.emit_progress"),
            patch("src.tools.specialist_tools.is_agent_enabled", AsyncMock(return_value=True)),
            patch("src.tools.specialist_tools._select_specialists", return_value=["energy"]),
            patch("src.tools.specialist_tools.reset_team_analysis"),
            patch("src.tools.specialist_tools._get_or_create_team_analysis", return_value=ta),
            patch("src.tools.specialist_tools._set_team_analysis"),
            patch(
                "src.tools.specialist_tools._capture_parent_span_context",
                return_value=(None, None, None),
            ),
            patch("src.tools.specialist_tools.model_context"),
            patch("src.tools.specialist_tools.EnergyAnalyst") as MockAnalyst,
            patch(
                "src.agents.execution_context.get_execution_context",
                return_value=_make_mock_ctx(),
            ),
        ):
            # We need to capture the state passed to the analyst
            async def capture_side_effect(state, **kw):
                captured_states.append(state)
                return {"team_analysis": state.team_analysis, "insights": []}

            mock_instance = AsyncMock()
            mock_instance.invoke = AsyncMock(side_effect=capture_side_effect)
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke({"query": "test", "depth": "deep"})

            # Check that the state had depth=deep
            assert len(captured_states) >= 1
            assert captured_states[0].depth == "deep"
