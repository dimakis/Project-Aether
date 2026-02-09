"""Unit tests for Data Scientist agent.

Tests script generation, sandbox execution, and insight extraction.
Constitution: Reliability & Quality - comprehensive agent testing.

TDD: T108 - Data Scientist script generation tests.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.data_scientist import (
    DataScientistAgent,
    DataScientistWorkflow,
)
from src.agents.prompts import load_prompt

DATA_SCIENTIST_SYSTEM_PROMPT = load_prompt("data_scientist_system")
from src.graph.state import AgentRole, AnalysisState, AnalysisType
from src.sandbox.runner import SandboxResult


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def mock_sandbox():
    """Create a mock sandbox runner."""
    sandbox = AsyncMock()
    sandbox.run = AsyncMock()
    return sandbox


@pytest.fixture
def data_scientist(mock_ha_client):
    """Create DataScientistAgent with mock HA client."""
    agent = DataScientistAgent(ha_client=mock_ha_client)
    return agent


@pytest.fixture
def sample_analysis_state():
    """Create a sample analysis state."""
    return AnalysisState(
        current_agent=AgentRole.DATA_SCIENTIST,
        analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
        entity_ids=["sensor.grid_power", "sensor.solar_power"],
        time_range_hours=24,
    )


@pytest.fixture
def sample_energy_data():
    """Create sample energy data."""
    return {
        "entities": [
            {
                "entity_id": "sensor.grid_power",
                "stats": {"total": 10.5, "average": 0.44},
            }
        ],
        "total_kwh": 10.5,
        "entity_count": 1,
        "hours": 24,
    }


@pytest.fixture
def sample_sandbox_result():
    """Create a successful sandbox result."""
    return SandboxResult(
        success=True,
        exit_code=0,
        stdout=json.dumps(
            {
                "insights": [
                    {
                        "type": "energy_optimization",
                        "title": "High Usage Detected",
                        "description": "Grid power usage is higher than average",
                        "confidence": 0.85,
                        "impact": "medium",
                        "evidence": {"peak_hour": 14},
                        "entities": ["sensor.grid_power"],
                    }
                ],
                "recommendations": ["Shift usage to off-peak hours"],
            }
        ),
        stderr="",
        duration_seconds=2.5,
        policy_name="standard",
    )


class TestDataScientistAgentInit:
    """Tests for agent initialization."""

    def test_init_default(self):
        """Test default initialization."""
        agent = DataScientistAgent()

        assert agent.role == AgentRole.DATA_SCIENTIST
        assert agent.name == "DataScientist"

    def test_init_with_mcp(self, mock_ha_client):
        """Test initialization with HA client."""
        agent = DataScientistAgent(ha_client=mock_ha_client)

        assert agent._ha_client == mock_ha_client


class TestDataScientistPrompt:
    """Tests for the system prompt."""

    def test_prompt_exists(self):
        """Test system prompt is defined."""
        assert DATA_SCIENTIST_SYSTEM_PROMPT is not None
        assert len(DATA_SCIENTIST_SYSTEM_PROMPT) > 100

    def test_prompt_mentions_sandbox(self):
        """Test prompt mentions sandbox constraints."""
        assert "sandbox" in DATA_SCIENTIST_SYSTEM_PROMPT.lower()
        assert "pandas" in DATA_SCIENTIST_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_json_output(self):
        """Test prompt specifies JSON output format."""
        assert "json" in DATA_SCIENTIST_SYSTEM_PROMPT.lower()
        assert "insights" in DATA_SCIENTIST_SYSTEM_PROMPT.lower()


class TestDataScientistCodeExtraction:
    """Tests for code extraction from LLM responses."""

    def test_extract_python_block(self, data_scientist):
        """Test extracting code from python block."""
        content = """Here's the analysis:

```python
import pandas as pd
print("hello")
```

This will analyze the data.
"""
        result = data_scientist._extract_code_from_response(content)

        assert "import pandas as pd" in result
        assert "print" in result
        assert "```" not in result

    def test_extract_generic_block(self, data_scientist):
        """Test extracting code from generic code block."""
        content = """
```
import json
data = json.load(open('/workspace/data.json'))
print(data)
```
"""
        result = data_scientist._extract_code_from_response(content)

        assert "import json" in result
        assert "```" not in result

    def test_extract_no_block(self, data_scientist):
        """Test handling response without code blocks."""
        content = "import pandas\ndf = pd.DataFrame()"

        result = data_scientist._extract_code_from_response(content)

        assert "import pandas" in result


class TestDataScientistInsightExtraction:
    """Tests for insight extraction from sandbox output."""

    def test_extract_valid_insights(
        self, data_scientist, sample_analysis_state, sample_sandbox_result
    ):
        """Test extracting valid insights from JSON output."""
        insights = data_scientist._extract_insights(sample_sandbox_result, sample_analysis_state)

        assert len(insights) == 1
        assert insights[0]["type"] == "energy_optimization"
        assert insights[0]["title"] == "High Usage Detected"
        assert insights[0]["confidence"] == 0.85

    def test_extract_from_failed_execution(self, data_scientist, sample_analysis_state):
        """Test handling failed script execution."""
        failed_result = SandboxResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="SyntaxError: invalid syntax",
            duration_seconds=0.1,
            policy_name="standard",
        )

        insights = data_scientist._extract_insights(failed_result, sample_analysis_state)

        assert len(insights) == 1
        assert insights[0]["type"] == "error"
        assert "failed" in insights[0]["title"].lower()

    def test_extract_from_invalid_json(self, data_scientist, sample_analysis_state):
        """Test handling non-JSON output."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout="Energy analysis complete. Usage is normal.",
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = data_scientist._extract_insights(result, sample_analysis_state)

        assert len(insights) == 1
        assert insights[0]["confidence"] == 0.5  # Default confidence
        assert "Energy analysis" in insights[0]["description"]

    def test_extract_normalizes_confidence(self, data_scientist, sample_analysis_state):
        """Test confidence is clamped to 0.0-1.0."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps(
                {"insights": [{"confidence": 1.5, "title": "Test", "description": "Test"}]}
            ),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        insights = data_scientist._extract_insights(result, sample_analysis_state)

        assert insights[0]["confidence"] == 1.0  # Clamped


class TestDataScientistRecommendations:
    """Tests for recommendation extraction."""

    def test_extract_recommendations(self, data_scientist, sample_sandbox_result):
        """Test extracting recommendations from output."""
        recs = data_scientist._extract_recommendations(sample_sandbox_result)

        assert len(recs) == 1
        assert "off-peak" in recs[0].lower()

    def test_extract_no_recommendations(self, data_scientist):
        """Test handling output without recommendations."""
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout=json.dumps({"insights": []}),
            stderr="",
            duration_seconds=1.0,
            policy_name="standard",
        )

        recs = data_scientist._extract_recommendations(result)

        assert recs == []


class TestDataScientistPromptBuilding:
    """Tests for analysis prompt building."""

    def test_energy_optimization_prompt(
        self, data_scientist, sample_analysis_state, sample_energy_data
    ):
        """Test prompt for energy optimization analysis."""
        sample_analysis_state.analysis_type = AnalysisType.ENERGY_OPTIMIZATION

        prompt = data_scientist._build_analysis_prompt(sample_analysis_state, sample_energy_data)

        assert "energy" in prompt.lower()
        assert "optimization" in prompt.lower() or "savings" in prompt.lower()

    def test_anomaly_detection_prompt(
        self, data_scientist, sample_analysis_state, sample_energy_data
    ):
        """Test prompt for anomaly detection analysis."""
        sample_analysis_state.analysis_type = AnalysisType.ANOMALY_DETECTION

        prompt = data_scientist._build_analysis_prompt(sample_analysis_state, sample_energy_data)

        assert "anomal" in prompt.lower()
        assert "baseline" in prompt.lower() or "detect" in prompt.lower()

    def test_usage_patterns_prompt(self, data_scientist, sample_analysis_state, sample_energy_data):
        """Test prompt for usage patterns analysis."""
        sample_analysis_state.analysis_type = AnalysisType.USAGE_PATTERNS

        prompt = data_scientist._build_analysis_prompt(sample_analysis_state, sample_energy_data)

        assert "pattern" in prompt.lower()

    def test_custom_query_prompt(self, data_scientist, sample_analysis_state, sample_energy_data):
        """Test prompt with custom query."""
        sample_analysis_state.analysis_type = AnalysisType.CUSTOM
        sample_analysis_state.custom_query = "Find the most efficient appliances"

        prompt = data_scientist._build_analysis_prompt(sample_analysis_state, sample_energy_data)

        assert "efficient appliances" in prompt.lower()


class TestDataScientistDiagnosticMode:
    """Tests for diagnostic analysis mode."""

    def test_diagnostic_prompt_includes_context(self, data_scientist, sample_energy_data):
        """Test DIAGNOSTIC prompt includes Architect's evidence."""
        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=["sensor.charger_energy"],
            time_range_hours=72,
            custom_query="Look for data gaps and identify root cause",
            diagnostic_context="HA log: ERROR sensor.charger_energy - Connection timeout",
        )

        prompt = data_scientist._build_analysis_prompt(state, sample_energy_data)

        assert "DIAGNOSTIC MODE" in prompt
        assert "Connection timeout" in prompt
        assert "data gaps" in prompt.lower()
        assert "root cause" in prompt.lower()

    def test_diagnostic_prompt_without_context(self, data_scientist, sample_energy_data):
        """Test DIAGNOSTIC prompt handles missing context gracefully."""
        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=["sensor.test"],
            time_range_hours=24,
            custom_query="Check for issues",
            diagnostic_context=None,
        )

        prompt = data_scientist._build_analysis_prompt(state, sample_energy_data)

        assert "DIAGNOSTIC MODE" in prompt
        assert "No additional diagnostic context" in prompt

    def test_diagnostic_prompt_includes_instructions(self, data_scientist, sample_energy_data):
        """Test DIAGNOSTIC prompt includes investigation instructions."""
        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=["sensor.energy"],
            time_range_hours=168,
            custom_query="Analyze integration stability over the past week",
            diagnostic_context="Config check: valid",
        )

        prompt = data_scientist._build_analysis_prompt(state, sample_energy_data)

        assert "integration stability" in prompt.lower()
        assert "Config check: valid" in prompt

    def test_system_prompt_mentions_diagnostics(self):
        """Test system prompt includes diagnostic capabilities."""
        assert "diagnostic" in DATA_SCIENTIST_SYSTEM_PROMPT.lower()
        assert "troubleshoot" in DATA_SCIENTIST_SYSTEM_PROMPT.lower()


class TestDataScientistDiagnosticDataCollection:
    """Tests for diagnostic data collection."""

    @pytest.mark.asyncio
    async def test_diagnostic_mode_includes_context_in_data(self, mock_ha_client):
        """Test that diagnostic context is added to energy data."""
        agent = DataScientistAgent(ha_client=mock_ha_client)

        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=AnalysisType.DIAGNOSTIC,
            entity_ids=["sensor.charger"],
            time_range_hours=72,
            diagnostic_context="Logs show connection errors at 2am",
        )

        with patch("src.agents.data_scientist.EnergyHistoryClient") as MockEnergyClient:
            mock_energy = AsyncMock()
            mock_energy.get_aggregated_energy = AsyncMock(
                return_value={
                    "entities": [],
                    "total_kwh": 0.0,
                    "entity_count": 1,
                    "hours": 72,
                }
            )
            MockEnergyClient.return_value = mock_energy

            data = await agent._collect_energy_data(state)

        assert "diagnostic_context" in data
        assert "connection errors at 2am" in data["diagnostic_context"]

    @pytest.mark.asyncio
    async def test_non_diagnostic_mode_no_context_in_data(self, mock_ha_client):
        """Test that non-diagnostic mode doesn't add context to data."""
        agent = DataScientistAgent(ha_client=mock_ha_client)

        state = AnalysisState(
            current_agent=AgentRole.DATA_SCIENTIST,
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=["sensor.grid"],
            time_range_hours=24,
        )

        with patch("src.agents.data_scientist.EnergyHistoryClient") as MockEnergyClient:
            mock_energy = AsyncMock()
            mock_energy.get_aggregated_energy = AsyncMock(
                return_value={
                    "entities": [],
                    "total_kwh": 5.0,
                    "entity_count": 1,
                    "hours": 24,
                }
            )
            MockEnergyClient.return_value = mock_energy

            data = await agent._collect_energy_data(state)

        assert "diagnostic_context" not in data


class TestDataScientistWorkflow:
    """Tests for DataScientistWorkflow."""

    def test_workflow_init(self):
        """Test workflow initialization."""
        workflow = DataScientistWorkflow()

        assert workflow.agent is not None
        assert isinstance(workflow.agent, DataScientistAgent)

    def test_workflow_init_with_mcp(self, mock_ha_client):
        """Test workflow initialization with HA client."""
        workflow = DataScientistWorkflow(ha_client=mock_ha_client)

        assert workflow.agent._ha_client == mock_ha_client

    @pytest.mark.asyncio
    async def test_run_analysis_creates_state(self, mock_ha_client):
        """Test that run_analysis creates proper state."""
        workflow = DataScientistWorkflow(ha_client=mock_ha_client)

        # Mock the agent invoke to avoid actual execution
        with patch.object(workflow.agent, "invoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {
                "insights": [{"type": "test", "title": "Test"}],
                "recommendations": [],
            }

            # Mock MLflow
            with patch("src.agents.data_scientist.start_experiment_run"):
                state = await workflow.run_analysis(
                    analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
                    hours=48,
                )

                assert state.analysis_type == AnalysisType.ENERGY_OPTIMIZATION
                assert state.time_range_hours == 48


class TestDataScientistIntegration:
    """Integration-style tests with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_invoke_full_flow(
        self,
        data_scientist,
        mock_ha_client,
        sample_analysis_state,
        sample_energy_data,
        sample_sandbox_result,
    ):
        """Test full invoke flow with mocks."""
        # Mock energy client
        with patch("src.agents.data_scientist.EnergyHistoryClient") as MockEnergyClient:
            mock_energy = AsyncMock()
            mock_energy.get_aggregated_energy = AsyncMock(return_value=sample_energy_data)
            MockEnergyClient.return_value = mock_energy

            # Mock LLM
            mock_response = MagicMock()
            mock_response.content = "```python\nprint('hello')\n```"
            data_scientist._llm = AsyncMock()
            data_scientist._llm.ainvoke = AsyncMock(return_value=mock_response)

            # Mock sandbox
            data_scientist._sandbox = AsyncMock()
            data_scientist._sandbox.run = AsyncMock(return_value=sample_sandbox_result)

            # Run invoke
            updates = await data_scientist.invoke(sample_analysis_state)

            assert "insights" in updates
            assert len(updates["insights"]) > 0
            assert "generated_script" in updates
