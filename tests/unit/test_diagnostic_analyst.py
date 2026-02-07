"""Tests for the Diagnostic Analyst specialist.

TDD: Red phase — tests define the contract for the Diagnostic Analyst,
which handles HA system health, entity diagnostics, integration health,
config validation, and error log analysis.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.graph.state import (
    AgentRole,
    AnalysisState,
    AnalysisType,
    SpecialistFinding,
    TeamAnalysis,
)
from src.agents.diagnostic_analyst import DiagnosticAnalyst


class TestDiagnosticAnalystInit:
    """Test Diagnostic Analyst initialization."""

    def test_has_correct_role(self):
        analyst = DiagnosticAnalyst(ha_client=MagicMock())
        assert analyst.role == AgentRole.DIAGNOSTIC_ANALYST

    def test_has_correct_name(self):
        analyst = DiagnosticAnalyst(ha_client=MagicMock())
        assert analyst.name == "DiagnosticAnalyst"


class TestDiagnosticAnalystCollectData:
    """Test diagnostic data collection."""

    @pytest.mark.asyncio
    async def test_collects_entity_health_data(self):
        """Should find unavailable/unhealthy entities."""
        mock_ha = MagicMock()
        analyst = DiagnosticAnalyst(ha_client=mock_ha)

        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=["sensor.temperature_bedroom"],
            time_range_hours=24,
        )

        with patch(
            "src.agents.diagnostic_analyst.find_unavailable_entities",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.agents.diagnostic_analyst.find_unhealthy_integrations",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.agents.diagnostic_analyst.run_config_check",
            new_callable=AsyncMock,
            return_value=MagicMock(valid=True, errors=[], warnings=[]),
        ):
            data = await analyst.collect_data(state)

        assert "unavailable_entities" in data
        assert "unhealthy_integrations" in data
        assert "config_check" in data

    @pytest.mark.asyncio
    async def test_includes_error_log_analysis(self):
        """Should analyze the HA error log."""
        mock_ha = MagicMock()
        mock_ha.get_error_log = AsyncMock(return_value="2026-01-01 ERROR test error")
        analyst = DiagnosticAnalyst(ha_client=mock_ha)

        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            time_range_hours=24,
        )

        with patch(
            "src.agents.diagnostic_analyst.find_unavailable_entities",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.agents.diagnostic_analyst.find_unhealthy_integrations",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.agents.diagnostic_analyst.run_config_check",
            new_callable=AsyncMock,
            return_value=MagicMock(valid=True, errors=[], warnings=[]),
        ), patch(
            "src.agents.diagnostic_analyst.parse_error_log",
            return_value=[],
        ), patch(
            "src.agents.diagnostic_analyst.get_error_summary",
            return_value={"total": 0, "counts_by_level": {}},
        ):
            data = await analyst.collect_data(state)

        assert "error_log" in data

    @pytest.mark.asyncio
    async def test_includes_diagnostic_context_from_architect(self):
        """Should include pre-collected context from Architect."""
        mock_ha = MagicMock()
        mock_ha.get_error_log = AsyncMock(return_value="")
        analyst = DiagnosticAnalyst(ha_client=mock_ha)

        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=["sensor.broken"],
            diagnostic_context="Sensor stopped reporting 3 hours ago",
            time_range_hours=24,
        )

        with patch(
            "src.agents.diagnostic_analyst.find_unavailable_entities",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.agents.diagnostic_analyst.find_unhealthy_integrations",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.agents.diagnostic_analyst.run_config_check",
            new_callable=AsyncMock,
            return_value=MagicMock(valid=True, errors=[], warnings=[]),
        ), patch(
            "src.agents.diagnostic_analyst.parse_error_log",
            return_value=[],
        ), patch(
            "src.agents.diagnostic_analyst.get_error_summary",
            return_value={"total": 0, "counts_by_level": {}},
        ):
            data = await analyst.collect_data(state)

        assert data.get("diagnostic_context") == "Sensor stopped reporting 3 hours ago"


class TestDiagnosticAnalystExtractFindings:
    """Test finding extraction from diagnostics."""

    def test_extracts_findings_from_json(self):
        """Should parse diagnostic insights from sandbox output."""
        analyst = DiagnosticAnalyst(ha_client=MagicMock())

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = '{"insights": [{"title": "Sensor drift detected", "description": "Temperature sensor drifting 2C over 7 days", "confidence": 0.8, "entities": ["sensor.temp"], "type": "concern"}]}'

        state = AnalysisState()
        findings = analyst.extract_findings(mock_result, state)
        assert len(findings) >= 1
        assert findings[0].specialist == "diagnostic_analyst"
        assert findings[0].finding_type == "concern"

    def test_returns_empty_on_failure(self):
        analyst = DiagnosticAnalyst(ha_client=MagicMock())
        mock_result = MagicMock()
        mock_result.success = False
        state = AnalysisState()
        assert analyst.extract_findings(mock_result, state) == []


class TestDiagnosticAnalystCrossConsultation:
    """Test that diagnostic analyst reads findings from other specialists."""

    def test_reads_energy_and_behavioral_findings(self):
        """Should see both energy and behavioral findings."""
        analyst = DiagnosticAnalyst(ha_client=MagicMock())

        energy = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="concern",
            title="Anomalous consumption",
            description="Unexpected spike at 03:00",
            entities=["sensor.energy_grid"],
        )
        behavioral = SpecialistFinding(
            specialist="behavioral_analyst",
            finding_type="insight",
            title="No activity at 03:00",
            description="No human activity detected at 03:00",
            entities=["binary_sensor.presence"],
        )
        ta = TeamAnalysis(
            request_id="cross-003",
            request_summary="Investigate 3AM spike",
            findings=[energy, behavioral],
        )
        state = AnalysisState(team_analysis=ta)

        prior = analyst.get_prior_findings(state)
        assert len(prior) == 2
