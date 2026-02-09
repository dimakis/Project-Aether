"""Tests for the Behavioral Analyst specialist.

TDD: Red phase — tests define the contract for the Behavioral Analyst,
which handles user behavior patterns, automation effectiveness,
script/scene usage, and automation gap detection.

Enhanced data sources: scripts, scenes, call frequency, trigger source
(automation vs human input).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.behavioral_analyst import BehavioralAnalyst
from src.graph.state import (
    AgentRole,
    AnalysisState,
    AnalysisType,
    SpecialistFinding,
    TeamAnalysis,
)


class TestBehavioralAnalystInit:
    """Test Behavioral Analyst initialization."""

    def test_has_correct_role(self):
        analyst = BehavioralAnalyst(ha_client=MagicMock())
        assert analyst.role == AgentRole.BEHAVIORAL_ANALYST

    def test_has_correct_name(self):
        analyst = BehavioralAnalyst(ha_client=MagicMock())
        assert analyst.name == "BehavioralAnalyst"


class TestBehavioralAnalystCollectData:
    """Test behavioral data collection including scripts/scenes."""

    @pytest.mark.asyncio
    async def test_collects_behavior_analysis_data(self):
        """Should collect button usage data for behavior analysis."""
        mock_ha = MagicMock()
        analyst = BehavioralAnalyst(ha_client=mock_ha)

        mock_behavioral = MagicMock()
        mock_behavioral.get_button_usage = AsyncMock(return_value=[])

        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
            time_range_hours=24,
        )

        with patch(
            "src.agents.behavioral_analyst.BehavioralAnalysisClient",
            return_value=mock_behavioral,
        ):
            data = await analyst.collect_data(state)

        assert "analysis_type" in data
        assert data["analysis_type"] == "behavior_analysis"

    @pytest.mark.asyncio
    async def test_collects_automation_gap_data(self):
        """Should detect automation gaps."""
        mock_ha = MagicMock()
        analyst = BehavioralAnalyst(ha_client=mock_ha)

        mock_behavioral = MagicMock()
        mock_behavioral.detect_automation_gaps = AsyncMock(return_value=[])

        state = AnalysisState(
            analysis_type=AnalysisType.AUTOMATION_GAP_DETECTION,
            time_range_hours=48,
        )

        with patch(
            "src.agents.behavioral_analyst.BehavioralAnalysisClient",
            return_value=mock_behavioral,
        ):
            data = await analyst.collect_data(state)

        assert data["analysis_type"] == "automation_gap_detection"

    @pytest.mark.asyncio
    async def test_collects_script_and_scene_usage(self):
        """Enhanced: should collect script and scene usage frequency and trigger source."""
        mock_ha = MagicMock()
        mock_ha.list_automations = AsyncMock(
            return_value=[
                {"entity_id": "automation.lights_on", "alias": "Lights On", "state": "on"},
            ]
        )

        analyst = BehavioralAnalyst(ha_client=mock_ha)

        mock_behavioral = MagicMock()
        mock_behavioral.get_button_usage = AsyncMock(return_value=[])

        # Mock logbook for script/scene usage
        mock_logbook = MagicMock()
        mock_logbook.get_stats = AsyncMock(
            return_value=MagicMock(
                total_entries=100,
                by_domain={"script": 15, "scene": 8, "automation": 50},
                automation_triggers=50,
                manual_actions=30,
                by_action_type={"triggered": 50, "turned_on": 30},
                unique_entities=20,
                by_hour={},
            )
        )
        mock_behavioral._logbook = mock_logbook

        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
            time_range_hours=168,  # 7 days
        )

        with patch(
            "src.agents.behavioral_analyst.BehavioralAnalysisClient",
            return_value=mock_behavioral,
        ):
            data = await analyst.collect_data(state)

        # Should include script/scene usage data
        assert "script_scene_usage" in data
        assert "automation_vs_human" in data

    @pytest.mark.asyncio
    async def test_includes_trigger_source_breakdown(self):
        """Should distinguish automation-triggered vs human-triggered calls."""
        mock_ha = MagicMock()
        analyst = BehavioralAnalyst(ha_client=mock_ha)

        mock_behavioral = MagicMock()
        mock_behavioral.get_automation_effectiveness = AsyncMock(
            return_value=[
                MagicMock(
                    automation_id="automation.morning",
                    alias="Morning Routine",
                    trigger_count=30,
                    manual_override_count=5,
                    efficiency_score=0.85,
                ),
            ]
        )

        state = AnalysisState(
            analysis_type=AnalysisType.AUTOMATION_ANALYSIS,
            time_range_hours=168,
        )

        with patch(
            "src.agents.behavioral_analyst.BehavioralAnalysisClient",
            return_value=mock_behavioral,
        ):
            data = await analyst.collect_data(state)

        assert "automation_effectiveness" in data
        # Effectiveness data includes manual_overrides for trigger source analysis
        assert data["automation_effectiveness"][0]["manual_overrides"] == 5


class TestBehavioralAnalystExtractFindings:
    """Test finding extraction from sandbox results."""

    def test_extracts_findings_from_json(self):
        """Should parse behavioral insights from sandbox output."""
        analyst = BehavioralAnalyst(ha_client=MagicMock())

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = '{"insights": [{"title": "Manual override pattern", "description": "User overrides bedroom lights automation 3x daily", "confidence": 0.9, "entities": ["light.bedroom"]}]}'

        state = AnalysisState(
            analysis_type=AnalysisType.BEHAVIOR_ANALYSIS,
        )
        findings = analyst.extract_findings(mock_result, state)
        assert len(findings) >= 1
        assert findings[0].specialist == "behavioral_analyst"

    def test_returns_empty_on_failure(self):
        """Failed execution returns empty findings."""
        analyst = BehavioralAnalyst(ha_client=MagicMock())

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "Error"

        state = AnalysisState()
        findings = analyst.extract_findings(mock_result, state)
        assert findings == []


class TestBehavioralAnalystCrossConsultation:
    """Test cross-consultation with other specialists."""

    def test_reads_energy_findings_for_context(self):
        """Should see energy findings to correlate behavior with usage."""
        analyst = BehavioralAnalyst(ha_client=MagicMock())

        energy_finding = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="insight",
            title="Peak at 18:00",
            description="Energy peaks when everyone arrives home.",
            confidence=0.9,
            entities=["sensor.grid_consumption"],
        )
        ta = TeamAnalysis(
            request_id="cross-002",
            request_summary="Cross-consult test",
            findings=[energy_finding],
        )
        state = AnalysisState(team_analysis=ta)

        prior = analyst.get_prior_findings(state)
        assert len(prior) == 1
        assert prior[0].specialist == "energy_analyst"
