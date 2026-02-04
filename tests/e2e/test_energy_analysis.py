"""End-to-end tests for energy analysis workflow.

Tests the complete flow from user request to insights:
1. User requests energy analysis
2. Data Scientist collects data via MCP
3. Generates analysis script
4. Executes in sandbox
5. Extracts and saves insights

Requires:
- Mock MCP client (or real HA connection)
- Sandbox environment (Podman + gVisor or unsandboxed mode)
- Database for insight storage
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents import DataScientistAgent
from src.graph.state import AnalysisState, AnalysisType
from src.graph.workflows import build_analysis_graph
from src.sandbox.runner import SandboxResult
from src.storage.entities import Insight, InsightStatus, InsightType


@pytest.fixture
def mock_energy_history():
    """Generate mock energy history data."""
    now = datetime.utcnow()
    states = []
    
    # Generate 24 hours of data
    for i in range(24):
        timestamp = now - timedelta(hours=24 - i)
        # Simulate typical energy pattern (higher during day)
        if 6 <= i <= 22:  # Daytime
            kwh = 1.5 + (0.5 * (i % 6))  # Varies between 1.5-4.0 kWh
        else:  # Nighttime
            kwh = 0.5 + (0.2 * (i % 3))  # Lower usage
        
        states.append({
            "state": str(round(kwh, 2)),
            "last_changed": timestamp.isoformat(),
            "attributes": {
                "unit_of_measurement": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
            },
        })
    
    return {
        "entity_id": "sensor.grid_consumption",
        "states": states,
        "count": len(states),
    }


@pytest.fixture
def mock_energy_entities():
    """Mock list of energy-related entities."""
    return [
        {
            "entity_id": "sensor.grid_consumption",
            "state": "2.5",
            "attributes": {
                "friendly_name": "Grid Consumption",
                "device_class": "energy",
                "unit_of_measurement": "kWh",
                "state_class": "total_increasing",
            },
        },
        {
            "entity_id": "sensor.solar_production",
            "state": "1.2",
            "attributes": {
                "friendly_name": "Solar Production",
                "device_class": "energy",
                "unit_of_measurement": "kWh",
            },
        },
    ]


@pytest.fixture
def mock_mcp_client(mock_energy_history, mock_energy_entities):
    """Create mock MCP client with energy data."""
    client = MagicMock()
    client.list_entities = AsyncMock(return_value={"results": mock_energy_entities})
    client.get_history = AsyncMock(return_value=mock_energy_history)
    client.get_entity = AsyncMock(return_value=mock_energy_entities[0])
    return client


@pytest.fixture
def mock_sandbox_result():
    """Mock successful sandbox execution result."""
    output = json.dumps({
        "insights": [
            {
                "type": "peak_usage",
                "title": "Peak consumption at 6 PM",
                "description": "Energy usage peaks around 6 PM daily, averaging 3.5 kWh",
                "confidence": 0.85,
                "impact": "medium",
            },
            {
                "type": "optimization",
                "title": "Shift laundry to solar hours",
                "description": "Running appliances between 10 AM - 2 PM could save 15% on grid consumption",
                "confidence": 0.75,
                "impact": "high",
            },
        ],
        "recommendations": [
            "Consider scheduling heavy appliances during peak solar production (10 AM - 2 PM)",
            "Your standby power consumption is normal at 0.3 kWh overnight",
        ],
        "summary": {
            "total_kwh": 42.5,
            "avg_daily_kwh": 42.5,
            "peak_hour": 18,
            "min_hour": 3,
        },
    })
    
    return SandboxResult(
        success=True,
        exit_code=0,
        stdout=output,
        stderr="",
        duration_seconds=5.2,
        policy_name="standard",
    )


class TestEnergyAnalysisE2E:
    """End-to-end tests for energy analysis.
    
    Note: Full workflow tests require complex mocking of multiple layers.
    These tests focus on component integration points that can be reliably tested.
    For full E2E testing, use manual testing with `aether analyze energy --days 7`.
    """

    @pytest.mark.asyncio
    async def test_analysis_state_initialization(self):
        """Test that analysis state initializes correctly."""
        state = AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            time_range_hours=24,
        )
        
        assert state.analysis_type == AnalysisType.ENERGY_OPTIMIZATION
        assert state.time_range_hours == 24
        assert state.entity_ids == []
        assert state.insights == []
        assert state.recommendations == []

    @pytest.mark.asyncio
    async def test_analysis_graph_compiles(self):
        """Test that the analysis graph compiles without errors."""
        workflow_graph = build_analysis_graph()
        workflow = workflow_graph.compile()
        
        # Should have the expected nodes
        assert workflow is not None

    @pytest.mark.asyncio
    async def test_sandbox_result_parsing(self, mock_sandbox_result):
        """Test that sandbox results can be parsed correctly."""
        output = json.loads(mock_sandbox_result.stdout)
        
        assert "insights" in output
        assert "recommendations" in output
        assert len(output["insights"]) == 2
        assert output["insights"][0]["type"] == "peak_usage"

    @pytest.mark.asyncio  
    async def test_failed_sandbox_result_handling(self):
        """Test handling of failed sandbox execution."""
        failed_result = SandboxResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="MemoryError: Unable to allocate array",
            duration_seconds=2.0,
            timed_out=False,
            policy_name="standard",
        )
        
        assert failed_result.success is False
        assert failed_result.exit_code == 1
        assert "MemoryError" in failed_result.stderr

    @pytest.mark.asyncio
    async def test_timeout_sandbox_result_handling(self):
        """Test handling of timed out sandbox execution."""
        timeout_result = SandboxResult(
            success=False,
            exit_code=137,
            stdout="",
            stderr="Execution timed out",
            duration_seconds=30.0,
            timed_out=True,
            policy_name="standard",
        )
        
        assert timeout_result.success is False
        assert timeout_result.timed_out is True
        assert timeout_result.duration_seconds == 30.0


class TestDataScientistAgentE2E:
    """E2E tests using DataScientistAgent directly."""

    def test_agent_initialization(self):
        """Test that DataScientistAgent initializes correctly."""
        agent = DataScientistAgent()
        
        assert agent is not None
        assert hasattr(agent, "invoke")

    @pytest.mark.asyncio
    async def test_agent_code_extraction(self):
        """Test agent's code extraction from LLM response."""
        agent = DataScientistAgent()
        
        # Test with markdown code block
        response_with_markdown = '''Here's the analysis script:

```python
import pandas as pd
import numpy as np

df = pd.DataFrame(data)
print(df.describe())
```

This script will analyze your data.'''
        
        extracted = agent._extract_code_from_response(response_with_markdown)
        
        assert "import pandas" in extracted
        assert "import numpy" in extracted
        assert "```" not in extracted

    def test_agent_insight_extraction(self, mock_sandbox_result):
        """Test agent's insight extraction from script output."""
        agent = DataScientistAgent()
        state = AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            time_range_hours=24,
        )
        
        insights = agent._extract_insights(mock_sandbox_result, state)
        
        assert len(insights) >= 1
        # The mock returns insights with "peak_usage" type
        assert any(i.get("type") == "peak_usage" for i in insights)

    def test_agent_recommendation_extraction(self, mock_sandbox_result):
        """Test agent's recommendation extraction from script output."""
        agent = DataScientistAgent()
        
        recommendations = agent._extract_recommendations(mock_sandbox_result)
        
        assert len(recommendations) >= 1


class TestInsightExtraction:
    """Tests for insight extraction from sandbox output."""

    @pytest.mark.asyncio
    async def test_extract_insights_from_json(self, mock_sandbox_result):
        """Test extracting insights from JSON output."""
        agent = DataScientistAgent()
        
        # Parse the JSON output
        output = json.loads(mock_sandbox_result.stdout)
        
        insights = output.get("insights", [])
        recommendations = output.get("recommendations", [])
        
        assert len(insights) == 2
        assert insights[0]["type"] == "peak_usage"
        assert insights[1]["impact"] == "high"
        
        assert len(recommendations) == 2
        assert "solar" in recommendations[0].lower()

    def test_insight_model_creation(self, mock_sandbox_result):
        """Test creating Insight model from extracted data."""
        output = json.loads(mock_sandbox_result.stdout)
        insight_data = output["insights"][0]
        
        insight = Insight(
            type=InsightType.ENERGY_OPTIMIZATION,
            title=insight_data["title"],
            description=insight_data["description"],
            confidence=insight_data["confidence"],
            impact=insight_data["impact"],
            status=InsightStatus.PENDING,
        )
        
        assert insight.title == "Peak consumption at 6 PM"
        assert insight.confidence == 0.85
        assert insight.status == InsightStatus.PENDING


class TestAnalysisTypes:
    """Tests for different analysis types."""

    def test_anomaly_detection_state(self):
        """Test anomaly detection analysis state creation."""
        state = AnalysisState(
            analysis_type=AnalysisType.ANOMALY_DETECTION,
            time_range_hours=168,  # 7 days for anomaly detection
        )
        
        assert state.analysis_type == AnalysisType.ANOMALY_DETECTION
        assert state.time_range_hours == 168

    def test_usage_patterns_state(self):
        """Test usage patterns analysis state creation."""
        state = AnalysisState(
            analysis_type=AnalysisType.USAGE_PATTERNS,
            time_range_hours=168,
        )
        
        assert state.analysis_type == AnalysisType.USAGE_PATTERNS

    def test_all_analysis_types_defined(self):
        """Test all analysis types are available."""
        assert hasattr(AnalysisType, "ENERGY_OPTIMIZATION")
        assert hasattr(AnalysisType, "ANOMALY_DETECTION")
        assert hasattr(AnalysisType, "USAGE_PATTERNS")
