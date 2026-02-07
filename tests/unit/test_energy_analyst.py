"""Tests for the Energy Analyst specialist.

TDD: Red phase — tests define the contract for the Energy Analyst,
which handles energy optimization, cost analysis, and usage patterns.
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
from src.agents.energy_analyst import EnergyAnalyst


class TestEnergyAnalystInit:
    """Test Energy Analyst initialization."""

    def test_has_correct_role(self):
        """Energy Analyst should have the ENERGY_ANALYST role."""
        analyst = EnergyAnalyst(ha_client=MagicMock())
        assert analyst.role == AgentRole.ENERGY_ANALYST

    def test_has_correct_name(self):
        analyst = EnergyAnalyst(ha_client=MagicMock())
        assert analyst.name == "EnergyAnalyst"


class TestEnergyAnalystCollectData:
    """Test energy data collection."""

    @pytest.mark.asyncio
    async def test_collects_energy_data_with_entity_ids(self):
        """When entity IDs are provided, uses them directly."""
        mock_ha = MagicMock()
        analyst = EnergyAnalyst(ha_client=mock_ha)

        mock_energy_client = MagicMock()
        mock_energy_client.get_aggregated_energy = AsyncMock(
            return_value={"total_kwh": 42.5, "entities": []}
        )

        state = AnalysisState(
            entity_ids=["sensor.energy_grid"],
            time_range_hours=24,
        )

        with patch(
            "src.agents.energy_analyst.EnergyHistoryClient",
            return_value=mock_energy_client,
        ):
            data = await analyst.collect_data(state)

        assert "total_kwh" in data
        mock_energy_client.get_aggregated_energy.assert_called_once()

    @pytest.mark.asyncio
    async def test_discovers_sensors_when_no_entity_ids(self):
        """When no entity IDs, discovers energy sensors."""
        mock_ha = MagicMock()
        analyst = EnergyAnalyst(ha_client=mock_ha)

        mock_energy_client = MagicMock()
        mock_energy_client.get_energy_sensors = AsyncMock(
            return_value=[{"entity_id": "sensor.energy_grid"}]
        )
        mock_energy_client.get_aggregated_energy = AsyncMock(
            return_value={"total_kwh": 10.0, "entities": []}
        )

        state = AnalysisState(
            entity_ids=[],
            time_range_hours=24,
        )

        with patch(
            "src.agents.energy_analyst.EnergyHistoryClient",
            return_value=mock_energy_client,
        ):
            data = await analyst.collect_data(state)

        assert "total_kwh" in data

    @pytest.mark.asyncio
    async def test_includes_diagnostic_context_when_diagnostic_mode(self):
        """In diagnostic mode, includes pre-collected context."""
        mock_ha = MagicMock()
        analyst = EnergyAnalyst(ha_client=mock_ha)

        mock_energy_client = MagicMock()
        mock_energy_client.get_aggregated_energy = AsyncMock(
            return_value={"total_kwh": 5.0}
        )

        state = AnalysisState(
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=["sensor.energy_grid"],
            time_range_hours=24,
            diagnostic_context="HVAC shows intermittent failures",
        )

        with patch(
            "src.agents.energy_analyst.EnergyHistoryClient",
            return_value=mock_energy_client,
        ):
            data = await analyst.collect_data(state)

        assert data.get("diagnostic_context") == "HVAC shows intermittent failures"


class TestEnergyAnalystGenerateScript:
    """Test energy analysis script generation."""

    @pytest.mark.asyncio
    async def test_generates_python_script(self):
        """Should generate a Python analysis script via LLM."""
        mock_ha = MagicMock()
        analyst = EnergyAnalyst(ha_client=mock_ha)

        # Mock LLM response
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="```python\nimport json\ndata = json.load(open('/workspace/data.json'))\nprint(json.dumps({'insights': []}))\n```"
            )
        )
        analyst._llm = mock_llm

        state = AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=["sensor.energy_grid"],
            time_range_hours=24,
        )
        data = {"total_kwh": 42.5, "entity_count": 3}

        script = await analyst.generate_script(state, data)
        assert "json" in script.lower()
        mock_llm.ainvoke.assert_called_once()


class TestEnergyAnalystExtractFindings:
    """Test finding extraction from sandbox results."""

    def test_extracts_findings_from_json_output(self):
        """Should parse JSON insights from sandbox stdout."""
        analyst = EnergyAnalyst(ha_client=MagicMock())

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = '{"insights": [{"title": "High peak usage", "description": "Peak at 18:00 is 40% above average", "confidence": 0.85, "entities": ["sensor.grid"]}]}'

        state = AnalysisState(
            entity_ids=["sensor.grid"],
            time_range_hours=24,
        )

        findings = analyst.extract_findings(mock_result, state)
        assert len(findings) >= 1
        assert findings[0].specialist == "energy_analyst"
        assert findings[0].confidence > 0

    def test_handles_empty_output(self):
        """Empty or no output should return empty findings."""
        analyst = EnergyAnalyst(ha_client=MagicMock())

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = ""

        state = AnalysisState()
        findings = analyst.extract_findings(mock_result, state)
        assert findings == []

    def test_handles_failed_execution(self):
        """Failed sandbox execution should return empty findings."""
        analyst = EnergyAnalyst(ha_client=MagicMock())

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "SyntaxError"

        state = AnalysisState()
        findings = analyst.extract_findings(mock_result, state)
        assert findings == []


class TestEnergyAnalystCrossConsultation:
    """Test that energy analyst reads prior findings from other specialists."""

    def test_considers_behavioral_findings_for_context(self):
        """Energy analyst should be able to read behavioral findings."""
        analyst = EnergyAnalyst(ha_client=MagicMock())

        behavioral_finding = SpecialistFinding(
            specialist="behavioral_analyst",
            finding_type="insight",
            title="Occupancy drops at 23:00",
            description="All occupants leave or sleep by 23:00.",
            confidence=0.95,
            entities=["binary_sensor.presence"],
        )
        ta = TeamAnalysis(
            request_id="cross-001",
            request_summary="Cross-consult test",
            findings=[behavioral_finding],
        )
        state = AnalysisState(team_analysis=ta)

        prior = analyst.get_prior_findings(state)
        assert len(prior) == 1
        assert prior[0].specialist == "behavioral_analyst"
