"""Unit tests for analysis tools module.

Tests run_custom_analysis tool with mocked dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import AnalysisState, AnalysisType


@pytest.fixture
def mock_analysis_state():
    """Create a mock analysis state."""
    state = MagicMock(spec=AnalysisState)
    state.insights = [
        {
            "title": "Energy Spike Detected",
            "description": "Unusual energy consumption detected during off-peak hours",
            "confidence": 0.85,
            "impact": "high",
        },
        {
            "title": "Device Efficiency",
            "description": "HVAC system operating efficiently",
            "confidence": 0.92,
            "impact": "medium",
        },
    ]
    state.recommendations = [
        "Check for devices left on overnight",
        "Consider scheduling HVAC during off-peak hours",
    ]
    return state


class TestRunCustomAnalysis:
    """Tests for run_custom_analysis tool."""

    @pytest.mark.asyncio
    async def test_run_custom_analysis_success(self, mock_analysis_state):
        """Test successful custom analysis execution."""
        from src.tools.analysis_tools import run_custom_analysis

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_analysis_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.agents.model_context.get_model_context", return_value=None),
            patch("src.tracing.get_active_span", return_value=None),
            patch("src.agents.model_context.model_context", MagicMock()),
        ):
            result = await run_custom_analysis.ainvoke(
                {
                    "description": "Check if HVAC is short-cycling",
                    "hours": 24,
                    "entity_ids": ["climate.living_room"],
                    "analysis_type": "custom",
                }
            )

        assert "Energy Spike Detected" in result
        assert "HVAC system operating efficiently" in result
        assert "Check for devices left on overnight" in result
        mock_workflow.run_analysis.assert_called_once()
        call_kwargs = mock_workflow.run_analysis.call_args[1]
        assert call_kwargs["analysis_type"] == AnalysisType.CUSTOM
        assert call_kwargs["hours"] == 24
        assert call_kwargs["entity_ids"] == ["climate.living_room"]
        assert call_kwargs["custom_query"] == "Check if HVAC is short-cycling"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_custom_analysis_with_defaults(self, mock_analysis_state):
        """Test custom analysis with default parameters."""
        from src.tools.analysis_tools import run_custom_analysis

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_analysis_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.agents.model_context.get_model_context", return_value=None),
            patch("src.tracing.get_active_span", return_value=None),
            patch("src.agents.model_context.model_context", MagicMock()),
        ):
            result = await run_custom_analysis.ainvoke(
                {
                    "description": "Analyze energy usage patterns",
                }
            )

        assert "Energy Spike Detected" in result
        call_kwargs = mock_workflow.run_analysis.call_args[1]
        assert call_kwargs["hours"] == 24  # default
        assert call_kwargs["entity_ids"] is None  # default
        assert call_kwargs["analysis_type"] == AnalysisType.CUSTOM

    @pytest.mark.asyncio
    async def test_run_custom_analysis_with_different_types(self, mock_analysis_state):
        """Test custom analysis with different analysis types."""
        from src.tools.analysis_tools import run_custom_analysis

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_analysis_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        type_mappings = [
            ("energy_optimization", AnalysisType.ENERGY_OPTIMIZATION),
            ("anomaly_detection", AnalysisType.ANOMALY_DETECTION),
            ("usage_patterns", AnalysisType.USAGE_PATTERNS),
            ("device_health", AnalysisType.DEVICE_HEALTH),
            ("behavior_analysis", AnalysisType.BEHAVIOR_ANALYSIS),
        ]

        for analysis_type_str, expected_enum in type_mappings:
            with (
                patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
                patch("src.storage.get_session", return_value=mock_session),
                patch("src.tools.analysis_tools.get_model_context", return_value=None),
                patch("src.tracing.get_active_span", return_value=None),
                patch("src.tools.analysis_tools.model_context", MagicMock()),
            ):
                await run_custom_analysis.ainvoke(
                    {
                        "description": "Test analysis",
                        "analysis_type": analysis_type_str,
                    }
                )

                call_kwargs = mock_workflow.run_analysis.call_args[1]
                assert call_kwargs["analysis_type"] == expected_enum

    @pytest.mark.asyncio
    async def test_run_custom_analysis_hours_capped(self, mock_analysis_state):
        """Test that hours are capped to reasonable limits."""
        from src.tools.analysis_tools import run_custom_analysis

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_analysis_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.agents.model_context.get_model_context", return_value=None),
            patch("src.tracing.get_active_span", return_value=None),
            patch("src.agents.model_context.model_context", MagicMock()),
        ):
            # Test max cap (168 hours)
            await run_custom_analysis.ainvoke(
                {
                    "description": "Test",
                    "hours": 500,  # Should be capped to 168
                }
            )
            call_kwargs = mock_workflow.run_analysis.call_args[1]
            assert call_kwargs["hours"] == 168

            # Test min cap (1 hour)
            await run_custom_analysis.ainvoke(
                {
                    "description": "Test",
                    "hours": 0,  # Should be capped to 1
                }
            )
            call_kwargs = mock_workflow.run_analysis.call_args[1]
            assert call_kwargs["hours"] == 1

    @pytest.mark.asyncio
    async def test_run_custom_analysis_no_insights(self):
        """Test custom analysis when no insights are found."""
        from src.tools.analysis_tools import run_custom_analysis

        mock_state = MagicMock(spec=AnalysisState)
        mock_state.insights = []
        mock_state.recommendations = []

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.agents.model_context.get_model_context", return_value=None),
            patch("src.tracing.get_active_span", return_value=None),
            patch("src.agents.model_context.model_context", MagicMock()),
        ):
            result = await run_custom_analysis.ainvoke(
                {
                    "description": "Find anomalies",
                    "hours": 24,
                }
            )

        assert "didn't find any significant patterns" in result.lower()
        assert "extending the lookback window" in result.lower()

    @pytest.mark.asyncio
    async def test_run_custom_analysis_with_model_context(self, mock_analysis_state):
        """Test custom analysis with model context propagation."""
        from src.agents.model_context import ModelContext
        from src.tools.analysis_tools import run_custom_analysis

        mock_context = ModelContext(model_name="test-model", temperature=0.7)

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_analysis_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_span = MagicMock()
        mock_span.span_id = "test-span-id"

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.tools.analysis_tools.get_model_context", return_value=mock_context),
            patch("src.tracing.get_active_span", return_value=mock_span),
            patch("src.tools.analysis_tools.model_context", MagicMock()) as mock_model_ctx,
        ):
            await run_custom_analysis.ainvoke(
                {
                    "description": "Test analysis",
                }
            )

        # Verify model context was used
        mock_model_ctx.assert_called()

    @pytest.mark.asyncio
    async def test_run_custom_analysis_error_handling(self):
        """Test error handling in custom analysis."""
        from src.tools.analysis_tools import run_custom_analysis

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(side_effect=Exception("Analysis failed"))

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.agents.model_context.get_model_context", return_value=None),
            patch("src.tracing.get_active_span", return_value=None),
            patch("src.agents.model_context.model_context", MagicMock()),
        ):
            result = await run_custom_analysis.ainvoke(
                {
                    "description": "Test analysis",
                }
            )

        assert "wasn't able to complete the analysis" in result.lower()
        assert "Analysis failed" in result

    @pytest.mark.asyncio
    async def test_run_custom_analysis_formatting(self, mock_analysis_state):
        """Test that results are properly formatted."""
        from src.tools.analysis_tools import run_custom_analysis

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_analysis_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.agents.model_context.get_model_context", return_value=None),
            patch("src.tracing.get_active_span", return_value=None),
            patch("src.agents.model_context.model_context", MagicMock()),
        ):
            result = await run_custom_analysis.ainvoke(
                {
                    "description": "Test analysis",
                    "hours": 48,
                }
            )

        # Check formatting includes key elements
        assert "48h lookback" in result or "48" in result
        assert "2 insight(s)" in result or "2" in result
        assert "Energy Spike Detected" in result
        assert "85% confidence" in result or "85" in result
        assert "Recommendations:" in result
        assert "Check for devices left on overnight" in result
        assert "Insights" in result and "page" in result

    @pytest.mark.asyncio
    async def test_run_custom_analysis_limits_insights(self, mock_analysis_state):
        """Test that only top insights are shown."""
        from src.tools.analysis_tools import run_custom_analysis

        # Create state with many insights
        mock_state = MagicMock(spec=AnalysisState)
        mock_state.insights = [
            {
                "title": f"Insight {i}",
                "description": f"Description {i}",
                "confidence": 0.8,
                "impact": "medium",
            }
            for i in range(10)
        ]
        mock_state.recommendations = []

        mock_workflow = MagicMock()
        mock_workflow.run_analysis = AsyncMock(return_value=mock_state)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        with (
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.agents.model_context.get_model_context", return_value=None),
            patch("src.tracing.get_active_span", return_value=None),
            patch("src.agents.model_context.model_context", MagicMock()),
        ):
            result = await run_custom_analysis.ainvoke(
                {
                    "description": "Test",
                }
            )

        # Should only show first 5 insights
        assert "Insight 0" in result
        assert "Insight 4" in result
        # Should not show insight 5+
        assert "Insight 5" not in result


class TestGetAnalysisTools:
    """Tests for get_analysis_tools."""

    def test_get_analysis_tools_returns_list(self):
        """Test that get_analysis_tools returns a list."""
        from src.tools.analysis_tools import get_analysis_tools

        tools = get_analysis_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_get_analysis_tools_includes_run_custom_analysis(self):
        """Test that run_custom_analysis is included."""
        from src.tools.analysis_tools import get_analysis_tools, run_custom_analysis

        tools = get_analysis_tools()
        assert run_custom_analysis in tools
