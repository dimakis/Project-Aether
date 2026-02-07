"""Tests for the multi-specialist team analysis workflow.

TDD: Red phase — tests define the contract for the team analysis
workflow that runs all three specialists and synthesizes findings.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.graph.state import (
    AnalysisState,
    AnalysisType,
    SpecialistFinding,
    TeamAnalysis,
)


class TestBuildTeamAnalysisGraph:
    """Test team analysis graph construction."""

    def test_graph_builds_without_error(self):
        """Should build a valid graph with specialist and synthesis nodes."""
        from src.graph.workflows import build_team_analysis_graph

        graph = build_team_analysis_graph()
        assert graph is not None


class TestTeamAnalysisWorkflow:
    """Test the TeamAnalysisWorkflow helper class."""

    def test_workflow_init(self):
        """Workflow should initialize with all three specialists."""
        from src.graph.workflows import TeamAnalysisWorkflow

        workflow = TeamAnalysisWorkflow()
        assert workflow is not None

    @pytest.mark.asyncio
    async def test_workflow_run_returns_team_analysis(self):
        """Running the workflow should return a synthesized TeamAnalysis."""
        from src.graph.workflows import TeamAnalysisWorkflow

        mock_energy = MagicMock()
        mock_energy.invoke = AsyncMock(return_value={
            "insights": [{"title": "Energy insight", "description": "Test"}],
            "team_analysis": TeamAnalysis(
                request_id="test-001",
                request_summary="Test",
                findings=[
                    SpecialistFinding(
                        specialist="energy_analyst",
                        finding_type="insight",
                        title="Energy insight",
                        description="Test",
                        confidence=0.8,
                    ),
                ],
            ),
        })

        mock_behavioral = MagicMock()
        mock_behavioral.invoke = AsyncMock(return_value={
            "insights": [],
            "team_analysis": TeamAnalysis(
                request_id="test-001",
                request_summary="Test",
                findings=[
                    SpecialistFinding(
                        specialist="energy_analyst",
                        finding_type="insight",
                        title="Energy insight",
                        description="Test",
                        confidence=0.8,
                    ),
                    SpecialistFinding(
                        specialist="behavioral_analyst",
                        finding_type="insight",
                        title="Behavioral insight",
                        description="Test",
                        confidence=0.9,
                    ),
                ],
            ),
        })

        mock_diagnostic = MagicMock()
        mock_diagnostic.invoke = AsyncMock(return_value={
            "insights": [],
            "team_analysis": TeamAnalysis(
                request_id="test-001",
                request_summary="Test",
                findings=[
                    SpecialistFinding(
                        specialist="energy_analyst",
                        finding_type="insight",
                        title="Energy insight",
                        description="Test",
                    ),
                    SpecialistFinding(
                        specialist="behavioral_analyst",
                        finding_type="insight",
                        title="Behavioral insight",
                        description="Test",
                    ),
                    SpecialistFinding(
                        specialist="diagnostic_analyst",
                        finding_type="concern",
                        title="Diagnostic concern",
                        description="Test",
                    ),
                ],
            ),
        })

        with patch(
            "src.agents.energy_analyst.EnergyAnalyst",
            return_value=mock_energy,
        ), patch(
            "src.agents.behavioral_analyst.BehavioralAnalyst",
            return_value=mock_behavioral,
        ), patch(
            "src.agents.diagnostic_analyst.DiagnosticAnalyst",
            return_value=mock_diagnostic,
        ):
            workflow = TeamAnalysisWorkflow()
            result = await workflow.run(
                query="Full home analysis",
                hours=24,
            )

        assert result is not None
        assert isinstance(result, TeamAnalysis)
        assert result.synthesis_strategy == "programmatic"
        assert result.consensus is not None
