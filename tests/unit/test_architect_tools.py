"""Unit tests for Architect HA tools and context retrieval.

Validates tool usage, approval gating for mutating actions, and
rich context assembly from the database.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.agents.architect import ArchitectAgent
from src.graph.state import ConversationState, ConversationStatus


@pytest.fixture
def mock_session():
    """Create a mock DB session."""
    return MagicMock()


@pytest.fixture
def architect():
    """Create Architect agent."""
    return ArchitectAgent()


class TestArchitectContext:
    """Tests for DB context retrieval."""

    @pytest.mark.asyncio
    async def test_context_includes_entities_devices_services(self, architect, mock_session):
        """Ensure context includes entities, devices, areas, and services."""
        with patch("src.agents.architect.EntityRepository") as entity_repo_cls, \
            patch("src.agents.architect.DeviceRepository") as device_repo_cls, \
            patch("src.agents.architect.AreaRepository") as area_repo_cls, \
            patch("src.agents.architect.ServiceRepository") as service_repo_cls:
            entity_repo = entity_repo_cls.return_value
            device_repo = device_repo_cls.return_value
            area_repo = area_repo_cls.return_value
            service_repo = service_repo_cls.return_value

            entity_repo.get_domain_counts = AsyncMock(return_value={"light": 1})
            entity_repo.list_all = AsyncMock(return_value=[
                MagicMock(entity_id="light.living_room", name="Living Room", state="on", area=None),
            ])
            area_repo.list_all = AsyncMock(return_value=[
                MagicMock(name="Living Room", ha_area_id="living_room"),
            ])
            device_repo.list_all = AsyncMock(return_value=[
                MagicMock(name="Hue Bridge", ha_device_id="device_1", area=None),
            ])
            service_repo.list_all = AsyncMock(return_value=[
                MagicMock(domain="light", service="turn_on"),
            ])

            state = ConversationState()
            context = await architect._get_entity_context(mock_session, state)

            assert context is not None
            assert "Available entities" in context
            assert "Areas" in context
            assert "Devices" in context
            assert "Services" in context


class TestArchitectToolCalls:
    """Tests for tool call handling."""

    @pytest.mark.asyncio
    async def test_read_only_tool_executes(self, architect):
        """Read-only tool calls should execute without approval."""
        tools = [MagicMock(name="get_entity_state", ainvoke=AsyncMock(return_value="ok"))]
        response = AIMessage(
            content="",
            tool_calls=[{"id": "1", "name": "get_entity_state", "args": {"entity_id": "light.test"}}],
        )

        # Mock the LLM to avoid real API call for follow-up
        mock_follow_up = MagicMock()
        mock_follow_up.content = "The light is on."
        architect._llm = MagicMock()
        architect._llm.ainvoke = AsyncMock(return_value=mock_follow_up)

        updates = await architect._handle_tool_calls(
            response=response,
            messages=[],
            tools=tools,
            state=ConversationState(),
        )

        assert updates is not None
        assert "messages" in updates

    @pytest.mark.asyncio
    async def test_mutating_tool_requires_approval(self, architect):
        """Mutating tools should require explicit approval."""
        tools = [MagicMock(name="control_entity", ainvoke=AsyncMock(return_value="ok"))]
        response = AIMessage(
            content="",
            tool_calls=[{"id": "1", "name": "control_entity", "args": {"entity_id": "light.test", "action": "on"}}],
        )

        updates = await architect._handle_tool_calls(
            response=response,
            messages=[],
            tools=tools,
            state=ConversationState(),
        )

        assert updates is not None
        assert updates["status"] == ConversationStatus.WAITING_APPROVAL
        assert "pending_approvals" in updates
