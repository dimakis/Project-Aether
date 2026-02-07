"""Tests for WorkflowPreset model and presets API.

Validates the WorkflowPreset Pydantic model and the GET /api/v1/workflows/presets
endpoint that returns available workflow presets for task flow customization.
"""

import pytest
from unittest.mock import patch


class TestWorkflowPresetModel:
    """Tests for the WorkflowPreset Pydantic model."""

    def test_preset_has_required_fields(self):
        """WorkflowPreset has id, name, description, agents, workflow_key."""
        from src.graph.state import WorkflowPreset

        preset = WorkflowPreset(
            id="full-analysis",
            name="Full Analysis",
            description="Run all DS team specialists with programmatic synthesis.",
            agents=["energy_analyst", "behavioral_analyst", "diagnostic_analyst"],
            workflow_key="team_analysis",
        )
        assert preset.id == "full-analysis"
        assert preset.name == "Full Analysis"
        assert len(preset.agents) == 3
        assert preset.workflow_key == "team_analysis"

    def test_preset_agents_is_list_of_strings(self):
        """agents field stores a list of agent identifiers."""
        from src.graph.state import WorkflowPreset

        preset = WorkflowPreset(
            id="energy-only",
            name="Energy Only",
            description="Run energy analyst only.",
            agents=["energy_analyst"],
            workflow_key="team_analysis",
        )
        assert isinstance(preset.agents, list)
        assert all(isinstance(a, str) for a in preset.agents)

    def test_preset_optional_icon_field(self):
        """WorkflowPreset can have an optional icon hint."""
        from src.graph.state import WorkflowPreset

        preset = WorkflowPreset(
            id="dashboard-design",
            name="Dashboard Design",
            description="Design dashboards.",
            agents=["dashboard_designer", "energy_analyst", "behavioral_analyst"],
            workflow_key="dashboard",
            icon="layout-dashboard",
        )
        assert preset.icon == "layout-dashboard"

    def test_preset_icon_defaults_to_none(self):
        """icon field defaults to None when not provided."""
        from src.graph.state import WorkflowPreset

        preset = WorkflowPreset(
            id="test",
            name="Test",
            description="Test.",
            agents=["architect"],
            workflow_key="conversation",
        )
        assert preset.icon is None

    def test_preset_in_state_all_exports(self):
        """WorkflowPreset is in state module __all__."""
        from src.graph import state

        assert "WorkflowPreset" in state.__all__


class TestDefaultPresets:
    """Tests for the default workflow presets collection."""

    def test_default_presets_exist(self):
        """DEFAULT_WORKFLOW_PRESETS is a non-empty list."""
        from src.graph.state import DEFAULT_WORKFLOW_PRESETS

        assert isinstance(DEFAULT_WORKFLOW_PRESETS, list)
        assert len(DEFAULT_WORKFLOW_PRESETS) >= 4

    def test_full_analysis_preset_exists(self):
        """A 'full-analysis' preset is in the defaults."""
        from src.graph.state import DEFAULT_WORKFLOW_PRESETS

        ids = [p.id for p in DEFAULT_WORKFLOW_PRESETS]
        assert "full-analysis" in ids

    def test_dashboard_design_preset_exists(self):
        """A 'dashboard-design' preset is in the defaults."""
        from src.graph.state import DEFAULT_WORKFLOW_PRESETS

        ids = [p.id for p in DEFAULT_WORKFLOW_PRESETS]
        assert "dashboard-design" in ids

    def test_energy_only_preset_exists(self):
        """An 'energy-only' preset is in the defaults."""
        from src.graph.state import DEFAULT_WORKFLOW_PRESETS

        ids = [p.id for p in DEFAULT_WORKFLOW_PRESETS]
        assert "energy-only" in ids


class TestWorkflowPresetsAPI:
    """Tests for the /api/v1/workflows/presets endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the API."""
        from src.api.main import create_app
        from httpx import ASGITransport, AsyncClient

        app = create_app()
        return AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": "test-key"},
        )

    @pytest.mark.asyncio
    async def test_get_presets_returns_list(self, client):
        """GET /api/v1/workflows/presets returns a list of presets."""
        with patch("src.api.auth.verify_api_key", return_value="test-user"):
            resp = await client.get("/api/v1/workflows/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "presets" in data
        assert isinstance(data["presets"], list)
        assert len(data["presets"]) >= 4

    @pytest.mark.asyncio
    async def test_presets_have_required_fields(self, client):
        """Each preset in the response has required fields."""
        with patch("src.api.auth.verify_api_key", return_value="test-user"):
            resp = await client.get("/api/v1/workflows/presets")
        data = resp.json()
        for preset in data["presets"]:
            assert "id" in preset
            assert "name" in preset
            assert "description" in preset
            assert "agents" in preset
            assert "workflow_key" in preset
