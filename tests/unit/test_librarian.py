"""Unit tests for Librarian agent.

Tests Librarian agent logic with mocked HA client.
Constitution: Reliability & Quality - agent logic validation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents import BaseAgent, LibrarianAgent
from src.agents.librarian import LibrarianWorkflow
from src.graph.state import AgentRole, DiscoveryState, DiscoveryStatus


@pytest.fixture
def mock_ha_client():
    """Create mock HA client."""
    client = MagicMock()

    # Mock list_entities
    client.list_entities = AsyncMock(
        return_value=[
            {
                "entity_id": "light.living_room",
                "state": "off",
                "name": "Living Room",
                "area_id": "living_room",
            },
            {
                "entity_id": "switch.kitchen",
                "state": "on",
                "name": "Kitchen Switch",
                "area_id": "kitchen",
            },
        ]
    )

    # Mock list_automations
    client.list_automations = AsyncMock(
        return_value=[
            {"id": "auto_1", "alias": "Morning Lights", "state": "on"},
        ]
    )

    return client


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_agent_initialization(self):
        """Test agent basic initialization."""
        agent = LibrarianAgent()

        assert agent.role == AgentRole.LIBRARIAN
        assert agent.name == "Librarian"

    def test_agent_custom_name(self):
        """Test agent with custom name."""

        class TestAgent(BaseAgent):
            role = AgentRole.LIBRARIAN

            async def invoke(self, state, **kwargs):
                return {}

        agent = TestAgent(role=AgentRole.LIBRARIAN, name="Custom Librarian")

        assert agent.name == "Custom Librarian"


class TestLibrarianAgent:
    """Tests for LibrarianAgent class."""

    def test_librarian_role(self):
        """Test Librarian has correct role."""
        agent = LibrarianAgent()

        assert agent.role == AgentRole.LIBRARIAN

    @pytest.mark.asyncio
    async def test_librarian_invoke_calls_workflow(self):
        """Test invoke delegates to workflow."""
        agent = LibrarianAgent()
        state = DiscoveryState()

        with patch("src.graph.nodes.run_discovery_node", new_callable=AsyncMock) as mock_node:
            mock_node.return_value = {
                "entities_found": [],
                "status": DiscoveryStatus.COMPLETED,
            }

            await agent.invoke(state)

            mock_node.assert_called_once()


class TestLibrarianWorkflow:
    """Tests for LibrarianWorkflow class."""

    @pytest.fixture
    def workflow(self, mock_ha_client):
        """Create workflow with mock client."""
        return LibrarianWorkflow(ha_client=mock_ha_client)

    def test_workflow_initialization(self, mock_ha_client):
        """Test workflow initialization."""
        workflow = LibrarianWorkflow(ha_client=mock_ha_client)

        assert workflow._ha_client == mock_ha_client

    def test_workflow_creates_mcp_if_needed(self):
        """Test workflow creates HA client if not provided."""
        workflow = LibrarianWorkflow()

        assert workflow._ha_client is None

        with patch("src.ha.get_ha_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            _ = workflow.ha

            mock_get_client.assert_called_once()


class TestDiscoveryState:
    """Tests for DiscoveryState."""

    def test_initial_state(self):
        """Test default discovery state values."""
        state = DiscoveryState()

        assert state.status == DiscoveryStatus.RUNNING
        assert state.entities_found == []
        assert state.entities_added == 0
        assert state.entities_updated == 0
        assert state.entities_removed == 0
        assert state.devices_found == 0
        assert state.areas_found == 0
        assert state.errors == []

    def test_state_with_agent(self):
        """Test state tracks current agent."""
        state = DiscoveryState(current_agent=AgentRole.LIBRARIAN)

        assert state.current_agent == AgentRole.LIBRARIAN

    def test_state_mlflow_run_id(self):
        """Test state can store MLflow run ID."""
        state = DiscoveryState(mlflow_run_id="run_abc123")

        assert state.mlflow_run_id == "run_abc123"

    def test_state_domains(self):
        """Test state tracks domains."""
        state = DiscoveryState(
            domains_to_scan=["light", "switch"],
            domains_scanned=["light"],
        )

        assert "light" in state.domains_to_scan
        assert "light" in state.domains_scanned
        assert "switch" not in state.domains_scanned


class TestDiscoveryStatus:
    """Tests for DiscoveryStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert DiscoveryStatus.RUNNING == "running"
        assert DiscoveryStatus.COMPLETED == "completed"
        assert DiscoveryStatus.FAILED == "failed"

    def test_status_comparison(self):
        """Test status can be compared."""
        assert DiscoveryStatus.RUNNING != DiscoveryStatus.COMPLETED
        assert DiscoveryStatus.COMPLETED == DiscoveryStatus.COMPLETED
