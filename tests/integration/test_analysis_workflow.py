"""Integration tests for Data Scientist analysis workflow.

Tests the full analysis pipeline with mocked dependencies.
Constitution: Reliability & Quality - workflow integration testing.

T111: Analysis workflow integration tests.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_energy_data():
    """Create mock energy sensor data."""
    return {
        "entities": [
            {
                "entity_id": "sensor.grid_power",
                "data_points": [
                    {"state": "1500", "last_changed": "2026-02-04T00:00:00Z"},
                    {"state": "2200", "last_changed": "2026-02-04T06:00:00Z"},
                    {"state": "1800", "last_changed": "2026-02-04T12:00:00Z"},
                    {"state": "3500", "last_changed": "2026-02-04T18:00:00Z"},
                ],
                "stats": {
                    "total": 9.0,
                    "average": 2.25,
                    "min": 1.5,
                    "max": 3.5,
                },
            },
            {
                "entity_id": "sensor.solar_power",
                "data_points": [
                    {"state": "0", "last_changed": "2026-02-04T00:00:00Z"},
                    {"state": "500", "last_changed": "2026-02-04T06:00:00Z"},
                    {"state": "2000", "last_changed": "2026-02-04T12:00:00Z"},
                    {"state": "300", "last_changed": "2026-02-04T18:00:00Z"},
                ],
                "stats": {
                    "total": 2.8,
                    "average": 0.7,
                    "min": 0,
                    "max": 2.0,
                },
            },
        ],
        "total_kwh": 11.8,
        "entity_count": 2,
        "hours": 24,
    }


@pytest.fixture
def mock_ha_client_analysis(mock_energy_data):
    """Create mock HA client for analysis workflow testing."""
    client = MagicMock()

    # Configure list_entities for energy sensor discovery
    client.list_entities = AsyncMock(
        return_value=[
            {
                "entity_id": "sensor.grid_power",
                "state": "1500",
                "name": "Grid Power",
                "domain": "sensor",
                "attributes": {
                    "device_class": "energy",
                    "unit_of_measurement": "W",
                    "state_class": "measurement",
                },
            },
            {
                "entity_id": "sensor.solar_power",
                "state": "1200",
                "name": "Solar Power",
                "domain": "sensor",
                "attributes": {
                    "device_class": "power",
                    "unit_of_measurement": "W",
                    "state_class": "measurement",
                },
            },
        ]
    )

    # Configure get_history
    client.get_history = AsyncMock(
        return_value={
            "entity_id": "sensor.grid_power",
            "states": mock_energy_data["entities"][0]["data_points"],
            "count": 4,
        }
    )

    client.connect = AsyncMock()

    return client


@pytest.fixture
def mock_sandbox_result_success():
    """Create successful sandbox execution result."""
    from src.sandbox.runner import SandboxResult

    return SandboxResult(
        success=True,
        exit_code=0,
        stdout=json.dumps(
            {
                "insights": [
                    {
                        "type": "energy_optimization",
                        "title": "Peak Usage at Evening",
                        "description": "Grid consumption peaks at 6PM (3.5 kW). Consider load shifting.",
                        "confidence": 0.85,
                        "impact": "high",
                        "evidence": {"peak_hour": 18, "peak_value": 3.5},
                        "entities": ["sensor.grid_power"],
                    },
                    {
                        "type": "usage_pattern",
                        "title": "Solar Production Pattern",
                        "description": "Solar peaks at noon. Battery storage could capture excess.",
                        "confidence": 0.9,
                        "impact": "medium",
                        "evidence": {"peak_hour": 12, "peak_value": 2.0},
                        "entities": ["sensor.solar_power"],
                    },
                ],
                "recommendations": [
                    "Shift high-power appliances (dishwasher, laundry) to midday",
                    "Consider battery storage to capture solar excess",
                ],
                "summary": "Energy analysis reveals opportunity for load shifting",
            }
        ),
        stderr="",
        duration_seconds=2.5,
        policy_name="standard",
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnalysisWorkflowPipeline:
    """Integration tests for the full analysis pipeline."""

    async def test_data_scientist_invoke_with_mocks(
        self,
        mock_ha_client_analysis,
        mock_energy_data,
        mock_sandbox_result_success,
    ):
        """Test DataScientistAgent.invoke with full mock pipeline."""
        from src.agents import DataScientistAgent
        from src.graph.state import AgentRole, AnalysisState, AnalysisType

        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=["sensor.grid_power", "sensor.solar_power"],
            time_range_hours=24,
        )

        # Create agent with mocked dependencies
        agent = DataScientistAgent(ha_client=mock_ha_client_analysis)

        # Mock the internal methods
        with patch.object(agent, "_collect_energy_data", new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = mock_energy_data

            with patch.object(agent, "_generate_script", new_callable=AsyncMock) as mock_script:
                mock_script.return_value = "print('analysis')"

                with patch.object(agent, "_execute_script", new_callable=AsyncMock) as mock_exec:
                    mock_exec.return_value = mock_sandbox_result_success

                    result = await agent.invoke(state)

                    assert "insights" in result
                    assert len(result["insights"]) == 2
                    assert result["insights"][0]["type"] == "energy_optimization"

    async def test_workflow_nodes_sequence(
        self,
        mock_ha_client_analysis,
        mock_energy_data,
        mock_sandbox_result_success,
    ):
        """Test that workflow nodes execute in correct sequence."""
        from src.graph.nodes import (
            collect_energy_data_node,
            extract_insights_node,
        )
        from src.graph.state import AgentRole, AnalysisState, AnalysisType, ScriptExecution

        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=["sensor.grid_power"],
            time_range_hours=24,
        )

        # Test collect_energy_data_node
        with patch("src.ha.get_ha_client", return_value=mock_ha_client_analysis):
            with patch("src.ha.EnergyHistoryClient") as MockClient:
                mock_history = AsyncMock()
                mock_history.get_energy_sensors = AsyncMock(
                    return_value=[{"entity_id": "sensor.grid_power"}]
                )
                mock_history.get_aggregated_energy = AsyncMock(return_value=mock_energy_data)
                MockClient.return_value = mock_history

                collect_result = await collect_energy_data_node(
                    state, ha_client=mock_ha_client_analysis
                )

                assert "entity_ids" in collect_result
                assert "messages" in collect_result

        # Test extract_insights_node with execution result
        state_with_execution = state.model_copy(
            update={
                "script_executions": [
                    ScriptExecution(
                        script_content="print('test')",
                        stdout=mock_sandbox_result_success.stdout,
                        stderr="",
                        exit_code=0,
                    )
                ]
            }
        )

        extract_result = await extract_insights_node(state_with_execution)

        assert "insights" in extract_result
        assert len(extract_result["insights"]) == 2
        assert "recommendations" in extract_result


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnalysisWorkflowGraph:
    """Integration tests for the compiled analysis graph."""

    async def test_build_analysis_graph(self):
        """Test that analysis graph builds without errors."""
        from src.graph.workflows import build_analysis_graph

        graph = build_analysis_graph()

        # Verify nodes exist
        assert graph is not None

    async def test_graph_compilation(self):
        """Test that analysis graph compiles correctly."""
        from src.graph.workflows import build_analysis_graph

        graph = build_analysis_graph()
        compiled = graph.compile()

        assert compiled is not None


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
class TestAnalysisWithDatabase:
    """Integration tests with database persistence."""

    async def test_insights_persisted_to_db(
        self,
        integration_session,
        mock_sandbox_result_success,
    ):
        """Test that insights are persisted to database."""
        from src.agents import DataScientistAgent
        from src.dal import InsightRepository
        from src.graph.state import AgentRole, AnalysisState, AnalysisType

        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=["sensor.grid_power"],
            time_range_hours=24,
        )

        # Parse insights from mock result
        agent = DataScientistAgent()
        insights = agent._extract_insights(mock_sandbox_result_success, state)

        # Persist insights
        await agent._persist_insights(insights, integration_session, state)
        await integration_session.commit()

        # Verify persistence
        repo = InsightRepository(integration_session)
        persisted = await repo.list_all(limit=10)

        assert len(persisted) == 2
        assert any(i.title == "Peak Usage at Evening" for i in persisted)

    async def test_analysis_workflow_full_with_db(
        self,
        integration_session,
        mock_ha_client_analysis,
        mock_energy_data,
        mock_sandbox_result_success,
    ):
        """Test full workflow execution with database integration."""
        from src.agents import DataScientistWorkflow
        from src.dal import InsightRepository
        from src.graph.state import AnalysisType

        workflow = DataScientistWorkflow(ha_client=mock_ha_client_analysis)

        # Mock internal dependencies
        with patch.object(
            workflow.agent, "_collect_energy_data", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = mock_energy_data

            with patch.object(
                workflow.agent, "_generate_script", new_callable=AsyncMock
            ) as mock_script:
                mock_script.return_value = "print('test')"

                with patch.object(
                    workflow.agent, "_execute_script", new_callable=AsyncMock
                ) as mock_exec:
                    mock_exec.return_value = mock_sandbox_result_success

                    # Disable MLflow - mock returns a context manager with string run_id
                    mock_run = MagicMock()
                    mock_run.info.run_id = "test-run-id"
                    mock_ctx = MagicMock()
                    mock_ctx.__enter__ = MagicMock(return_value=mock_run)
                    mock_ctx.__exit__ = MagicMock(return_value=False)
                    with patch(
                        "src.agents.data_scientist.start_experiment_run",
                        return_value=mock_ctx,
                    ):
                        state = await workflow.run_analysis(
                            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
                            hours=24,
                            session=integration_session,
                        )
                        await integration_session.commit()

        # Verify workflow completed
        assert len(state.insights) == 2

        # Verify database persistence
        repo = InsightRepository(integration_session)
        persisted = await repo.list_all(limit=10)

        # Insights should be persisted
        assert len(persisted) >= 2


@pytest.mark.integration
class TestAnalysisStateManagement:
    """Tests for analysis state flow through workflow."""

    def test_analysis_state_initialization(self):
        """Test AnalysisState initializes with correct defaults."""
        from src.graph.state import AnalysisState, AnalysisType

        state = AnalysisState(
            analysis_type=AnalysisType.ANOMALY_DETECTION,
            entity_ids=["sensor.test"],
            time_range_hours=48,
        )

        assert state.analysis_type == AnalysisType.ANOMALY_DETECTION
        assert state.time_range_hours == 48
        assert state.generated_script is None
        assert state.insights == []
        assert state.script_executions == []

    def test_analysis_state_update(self):
        """Test that state updates correctly through workflow."""
        from src.graph.state import AnalysisState, AnalysisType, ScriptExecution

        state = AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=[],
            time_range_hours=24,
        )

        # Simulate workflow updates
        state_update_1 = {"entity_ids": ["sensor.discovered"]}
        state = state.model_copy(update=state_update_1)

        assert state.entity_ids == ["sensor.discovered"]

        state_update_2 = {"generated_script": "import pandas"}
        state = state.model_copy(update=state_update_2)

        assert state.generated_script == "import pandas"

        state_update_3 = {
            "script_executions": [
                ScriptExecution(
                    script_content="print('hello')",
                    stdout="output",
                    stderr="",
                    exit_code=0,
                )
            ]
        }
        state = state.model_copy(update=state_update_3)

        assert len(state.script_executions) == 1
