"""Tests for DS team shared analysis state models.

TDD: Red phase — tests define the contract for SpecialistFinding,
TeamAnalysis, and their integration into AnalysisState.
"""

import pytest
from pydantic import ValidationError

from src.graph.state import (
    AgentRole,
    AnalysisState,
    AutomationSuggestion,
    SpecialistFinding,
    TeamAnalysis,
)


class TestSpecialistFinding:
    """Test SpecialistFinding model validation and defaults."""

    def test_minimal_finding(self):
        """A finding requires specialist, finding_type, title, description."""
        finding = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="insight",
            title="High overnight HVAC usage",
            description="HVAC runs 8h overnight at full power.",
        )
        assert finding.specialist == "energy_analyst"
        assert finding.finding_type == "insight"
        assert finding.confidence == 0.0  # default
        assert finding.entities == []
        assert finding.evidence == {}
        assert finding.automation_suggestion is None
        assert finding.cross_references == []

    def test_full_finding_with_all_fields(self):
        """All optional fields can be populated."""
        suggestion = AutomationSuggestion(
            pattern="HVAC runs overnight",
            entities=["climate.main_hvac"],
            proposed_trigger="time: 23:00",
            proposed_action="set HVAC to eco mode",
            confidence=0.85,
            evidence={"avg_hours": 8},
            source_insight_type="energy_optimization",
        )
        finding = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="recommendation",
            title="Reduce HVAC overnight",
            description="Switching to eco mode would save ~30% energy.",
            confidence=0.85,
            entities=["climate.main_hvac"],
            evidence={"savings_pct": 30, "avg_kwh": 4.2},
            automation_suggestion=suggestion,
            cross_references=["finding_behavioral_001"],
        )
        assert finding.confidence == 0.85
        assert finding.automation_suggestion is not None
        assert "climate.main_hvac" in finding.entities
        assert len(finding.cross_references) == 1

    def test_confidence_must_be_0_to_1(self):
        """Confidence outside [0, 1] should fail validation."""
        with pytest.raises(ValidationError):
            SpecialistFinding(
                specialist="energy_analyst",
                finding_type="insight",
                title="Test",
                description="Test",
                confidence=1.5,
            )
        with pytest.raises(ValidationError):
            SpecialistFinding(
                specialist="energy_analyst",
                finding_type="insight",
                title="Test",
                description="Test",
                confidence=-0.1,
            )

    def test_finding_id_auto_generated(self):
        """Each finding should have a unique auto-generated ID."""
        f1 = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="insight",
            title="A",
            description="A",
        )
        f2 = SpecialistFinding(
            specialist="behavioral_analyst",
            finding_type="insight",
            title="B",
            description="B",
        )
        assert f1.id != f2.id
        assert len(f1.id) > 0


class TestTeamAnalysis:
    """Test TeamAnalysis shared state model."""

    def test_minimal_team_analysis(self):
        """TeamAnalysis requires request_id and request_summary."""
        ta = TeamAnalysis(
            request_id="req-001",
            request_summary="Analyze energy usage patterns",
        )
        assert ta.request_id == "req-001"
        assert ta.findings == []
        assert ta.consensus is None
        assert ta.conflicts == []
        assert ta.holistic_recommendations == []

    def test_accumulate_findings(self):
        """Findings from multiple specialists accumulate in the list."""
        ta = TeamAnalysis(
            request_id="req-002",
            request_summary="Full home analysis",
        )
        energy_finding = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="insight",
            title="Peak usage at 6PM",
            description="Energy peaks daily at 18:00.",
            confidence=0.9,
            entities=["sensor.grid_consumption"],
        )
        behavioral_finding = SpecialistFinding(
            specialist="behavioral_analyst",
            finding_type="insight",
            title="Occupancy at 6PM",
            description="All household members arrive home by 18:00.",
            confidence=0.95,
            entities=["binary_sensor.presence"],
            cross_references=[energy_finding.id],
        )
        ta.findings.append(energy_finding)
        ta.findings.append(behavioral_finding)

        assert len(ta.findings) == 2
        assert ta.findings[0].specialist == "energy_analyst"
        assert ta.findings[1].specialist == "behavioral_analyst"
        # Cross-reference links
        assert energy_finding.id in ta.findings[1].cross_references

    def test_consensus_and_conflicts(self):
        """TeamAnalysis can record consensus and conflicts."""
        ta = TeamAnalysis(
            request_id="req-003",
            request_summary="Investigate high HVAC usage",
            findings=[],
            consensus="HVAC usage is expected due to winter schedule",
            conflicts=["Energy sees waste; Behavioral sees scheduled heating"],
            holistic_recommendations=[
                "Add eco-mode schedule for 23:00-06:00",
                "Install smart thermostat in bedroom",
            ],
        )
        assert ta.consensus is not None
        assert len(ta.conflicts) == 1
        assert len(ta.holistic_recommendations) == 2

    def test_synthesis_strategy_field(self):
        """TeamAnalysis tracks which synthesizer produced the consensus."""
        ta = TeamAnalysis(
            request_id="req-004",
            request_summary="Test synthesis tracking",
            synthesis_strategy="programmatic",
        )
        assert ta.synthesis_strategy == "programmatic"

        ta_llm = TeamAnalysis(
            request_id="req-005",
            request_summary="Test LLM synthesis",
            synthesis_strategy="llm",
        )
        assert ta_llm.synthesis_strategy == "llm"

    def test_default_synthesis_strategy_is_none(self):
        """Before synthesis runs, strategy is None."""
        ta = TeamAnalysis(
            request_id="req-006",
            request_summary="Pre-synthesis",
        )
        assert ta.synthesis_strategy is None


class TestAgentRoleEnum:
    """Test that new agent roles are defined."""

    def test_energy_analyst_role(self):
        assert AgentRole.ENERGY_ANALYST == "energy_analyst"

    def test_behavioral_analyst_role(self):
        assert AgentRole.BEHAVIORAL_ANALYST == "behavioral_analyst"

    def test_diagnostic_analyst_role(self):
        assert AgentRole.DIAGNOSTIC_ANALYST == "diagnostic_analyst"

    def test_dashboard_designer_role(self):
        assert AgentRole.DASHBOARD_DESIGNER == "dashboard_designer"

    def test_existing_roles_preserved(self):
        """Existing roles must not break."""
        assert AgentRole.ARCHITECT == "architect"
        assert AgentRole.DEVELOPER == "developer"
        assert AgentRole.LIBRARIAN == "librarian"
        assert AgentRole.DATA_SCIENTIST == "data_scientist"


class TestAnalysisStateIntegration:
    """Test TeamAnalysis integration into AnalysisState."""

    def test_analysis_state_has_team_analysis(self):
        """AnalysisState should have an optional team_analysis field."""
        state = AnalysisState()
        assert state.team_analysis is None

    def test_analysis_state_with_team_analysis(self):
        """AnalysisState can carry a populated TeamAnalysis."""
        ta = TeamAnalysis(
            request_id="req-int-001",
            request_summary="Integration test",
            findings=[
                SpecialistFinding(
                    specialist="diagnostic_analyst",
                    finding_type="concern",
                    title="Sensor offline",
                    description="sensor.temperature_bedroom offline for 3h",
                    confidence=1.0,
                    entities=["sensor.temperature_bedroom"],
                ),
            ],
        )
        state = AnalysisState(team_analysis=ta)
        assert state.team_analysis is not None
        assert len(state.team_analysis.findings) == 1
        assert state.team_analysis.findings[0].specialist == "diagnostic_analyst"
