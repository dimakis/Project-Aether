"""Tests for the BaseAnalyst shared functionality.

TDD: Red phase — tests define the contract for the base analyst class
that all DS team specialists inherit from.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.graph.state import (
    AgentRole,
    AnalysisState,
    AnalysisType,
    SpecialistFinding,
    TeamAnalysis,
)
from src.agents.base_analyst import BaseAnalyst


# ---------------------------------------------------------------------------
# Concrete subclass for testing (BaseAnalyst is abstract)
# ---------------------------------------------------------------------------

class StubAnalyst(BaseAnalyst):
    """Concrete analyst for testing abstract base."""

    ROLE = AgentRole.ENERGY_ANALYST
    NAME = "StubAnalyst"

    async def collect_data(self, state: AnalysisState) -> dict:
        return {"test_data": [1, 2, 3]}

    async def generate_script(self, state: AnalysisState, data: dict) -> str:
        return "print('hello')"

    def extract_findings(self, result, state: AnalysisState) -> list[SpecialistFinding]:
        return [
            SpecialistFinding(
                specialist="energy_analyst",
                finding_type="insight",
                title="Test finding",
                description="Test description",
                confidence=0.8,
                entities=state.entity_ids[:1] if state.entity_ids else [],
            )
        ]

    async def invoke(self, state, **kwargs):
        """Stub invoke for testing."""
        return {}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBaseAnalystInit:
    """Test BaseAnalyst initialization."""

    def test_init_with_defaults(self):
        """BaseAnalyst creates with default HA client and sandbox."""
        with patch("src.agents.base_analyst.get_ha_client") as mock_get:
            mock_get.return_value = MagicMock()
            analyst = StubAnalyst()
            assert analyst.role == AgentRole.ENERGY_ANALYST
            assert analyst.name == "StubAnalyst"

    def test_init_with_explicit_ha_client(self):
        """Can provide an explicit HA client."""
        mock_client = MagicMock()
        analyst = StubAnalyst(ha_client=mock_client)
        assert analyst.ha is mock_client


class TestBaseAnalystHAProperty:
    """Test lazy HA client creation."""

    def test_ha_property_creates_client_lazily(self):
        """HA client is created on first access, not at init."""
        analyst = StubAnalyst()
        with patch("src.agents.base_analyst.get_ha_client") as mock_get:
            mock_get.return_value = MagicMock()
            _ = analyst.ha
            mock_get.assert_called_once()


class TestBaseAnalystExecuteScript:
    """Test shared sandbox script execution."""

    @pytest.mark.asyncio
    async def test_execute_script_delegates_to_sandbox(self):
        """execute_script should delegate to SandboxRunner."""
        mock_sandbox = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "output"
        mock_sandbox.run = AsyncMock(return_value=mock_result)

        analyst = StubAnalyst(ha_client=MagicMock())
        analyst._sandbox = mock_sandbox

        result = await analyst.execute_script("print('hello')", {"data": [1]})
        assert result.success is True
        mock_sandbox.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_script_passes_data_as_context(self):
        """Data dict should be available to the script as context."""
        mock_sandbox = MagicMock()
        mock_result = MagicMock(success=True, stdout="ok")
        mock_sandbox.run = AsyncMock(return_value=mock_result)

        analyst = StubAnalyst(ha_client=MagicMock())
        analyst._sandbox = mock_sandbox

        data = {"sensor_readings": [1, 2, 3]}
        await analyst.execute_script("print(data)", data)

        call_args = mock_sandbox.run.call_args
        # The script content should include the data injection
        script_content = call_args.args[0] if call_args.args else call_args.kwargs.get("script", "")
        assert "sensor_readings" in script_content or data == call_args.kwargs.get("data")


class TestBaseAnalystCrossConsultation:
    """Test reading prior findings from TeamAnalysis."""

    def test_get_prior_findings_returns_empty_when_no_team_analysis(self):
        """No team analysis means no prior findings."""
        analyst = StubAnalyst(ha_client=MagicMock())
        state = AnalysisState()
        prior = analyst.get_prior_findings(state)
        assert prior == []

    def test_get_prior_findings_returns_other_specialists_findings(self):
        """Should return findings from OTHER specialists, not self."""
        analyst = StubAnalyst(ha_client=MagicMock())

        behavioral_finding = SpecialistFinding(
            specialist="behavioral_analyst",
            finding_type="insight",
            title="Pattern detected",
            description="Users come home at 18:00",
            confidence=0.9,
        )
        own_finding = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="insight",
            title="Own finding",
            description="Own previous finding",
            confidence=0.7,
        )
        ta = TeamAnalysis(
            request_id="test-001",
            request_summary="Test",
            findings=[behavioral_finding, own_finding],
        )
        state = AnalysisState(team_analysis=ta)

        prior = analyst.get_prior_findings(state)
        # Should only return the behavioral finding (not own)
        assert len(prior) == 1
        assert prior[0].specialist == "behavioral_analyst"

    def test_get_prior_findings_for_entity_filters_by_entity(self):
        """Filter prior findings to a specific entity."""
        analyst = StubAnalyst(ha_client=MagicMock())

        finding_hvac = SpecialistFinding(
            specialist="behavioral_analyst",
            finding_type="insight",
            title="HVAC pattern",
            description="Scheduled heating",
            entities=["climate.main_hvac"],
        )
        finding_light = SpecialistFinding(
            specialist="diagnostic_analyst",
            finding_type="concern",
            title="Light flickering",
            description="Light flickers intermittently",
            entities=["light.living_room"],
        )
        ta = TeamAnalysis(
            request_id="test-002",
            request_summary="Test",
            findings=[finding_hvac, finding_light],
        )
        state = AnalysisState(team_analysis=ta)

        prior = analyst.get_prior_findings(state, entity_id="climate.main_hvac")
        assert len(prior) == 1
        assert prior[0].title == "HVAC pattern"


class TestBaseAnalystAddFinding:
    """Test adding findings to TeamAnalysis."""

    def test_add_finding_creates_team_analysis_if_absent(self):
        """If state has no team_analysis, create one with the finding."""
        analyst = StubAnalyst(ha_client=MagicMock())
        state = AnalysisState()
        finding = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="insight",
            title="Test",
            description="Test",
        )
        updated = analyst.add_finding(state, finding)
        assert updated.team_analysis is not None
        assert len(updated.team_analysis.findings) == 1

    def test_add_finding_appends_to_existing(self):
        """If state has team_analysis, append the finding."""
        analyst = StubAnalyst(ha_client=MagicMock())
        ta = TeamAnalysis(
            request_id="test-003",
            request_summary="Test",
            findings=[
                SpecialistFinding(
                    specialist="behavioral_analyst",
                    finding_type="insight",
                    title="Prior",
                    description="Prior finding",
                ),
            ],
        )
        state = AnalysisState(team_analysis=ta)
        finding = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="insight",
            title="New",
            description="New finding",
        )
        updated = analyst.add_finding(state, finding)
        assert len(updated.team_analysis.findings) == 2


class TestBaseAnalystPersistInsights:
    """Test insight persistence to database."""

    @pytest.mark.asyncio
    async def test_persist_insights_calls_repository(self):
        """Findings should be persisted via InsightRepository."""
        analyst = StubAnalyst(ha_client=MagicMock())
        findings = [
            SpecialistFinding(
                specialist="energy_analyst",
                finding_type="insight",
                title="High usage",
                description="High energy usage detected",
                confidence=0.85,
                entities=["sensor.energy"],
            ),
        ]
        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=MagicMock(id=str(uuid4())))

        with patch("src.agents.base_analyst.InsightRepository", return_value=mock_repo):
            await analyst.persist_findings(findings, mock_session)

        mock_repo.create.assert_called_once()
