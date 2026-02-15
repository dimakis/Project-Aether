"""Unit tests for error surfacing in the streaming pipeline.

Part 3a-b: entity_context returns (context, warning) and workflow yields error events
Part 3c-d: session.commit timeout and overall stream timeout
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage

from src.agents.architect.entity_context import _invalidate_entity_context_cache
from src.graph.state import ConversationState


@pytest.fixture(autouse=True)
def _clear_cache():
    _invalidate_entity_context_cache()
    yield
    _invalidate_entity_context_cache()


async def _empty_astream():
    yield AIMessageChunk(content="Hello")


def _make_workflow():
    from src.agents.architect.workflow import ArchitectWorkflow

    w = ArchitectWorkflow.__new__(ArchitectWorkflow)
    w.agent = MagicMock()
    w.agent.model_name = "test-model"
    w.agent._build_messages.return_value = [HumanMessage(content="test")]
    w.agent._get_ha_tools.return_value = []
    w.agent._is_mutating_tool.return_value = False
    w.agent._extract_proposals.return_value = []
    w.agent.get_tool_llm.return_value = MagicMock(astream=MagicMock(return_value=_empty_astream()))
    return w


class TestEntityContextWarning:
    """get_entity_context returns (context, warning) tuple."""

    @pytest.mark.asyncio
    async def test_returns_tuple_with_none_warning_on_success(self):
        """Successful context returns (context_str, None)."""
        from src.agents.architect.entity_context import get_entity_context

        mock_factory = MagicMock(side_effect=lambda: AsyncMock())

        with (
            patch(
                "src.agents.architect.entity_context.get_session_factory", return_value=mock_factory
            ),
            patch("src.agents.architect.entity_context.EntityRepository") as MockEntityRepo,
            patch("src.agents.architect.entity_context.AreaRepository") as MockAreaRepo,
            patch("src.agents.architect.entity_context.DeviceRepository") as MockDeviceRepo,
            patch("src.agents.architect.entity_context.ServiceRepository") as MockServiceRepo,
        ):
            MockEntityRepo.return_value.get_domain_counts = AsyncMock(return_value={"light": 1})
            MockEntityRepo.return_value.list_by_domains = AsyncMock(return_value={})
            MockAreaRepo.return_value.list_all = AsyncMock(return_value=[])
            MockDeviceRepo.return_value.list_all = AsyncMock(return_value=[])
            MockServiceRepo.return_value.list_all = AsyncMock(return_value=[])

            state = MagicMock()
            state.entities_mentioned = []
            context, warning = await get_entity_context(state)

        assert context is not None
        assert "Available entities" in context
        assert warning is None

    @pytest.mark.asyncio
    async def test_returns_warning_on_failure(self):
        """Failed context returns (None, warning_string)."""
        from src.agents.architect.entity_context import get_entity_context

        mock_factory = MagicMock(side_effect=RuntimeError("DB exploded"))

        with patch(
            "src.agents.architect.entity_context.get_session_factory",
            return_value=mock_factory,
        ):
            state = MagicMock()
            state.entities_mentioned = []
            context, warning = await get_entity_context(state)

        assert context is None
        assert warning is not None
        assert "DB exploded" in warning


class TestWorkflowYieldsErrorEvents:
    """stream_conversation yields error events for degraded states."""

    @pytest.mark.asyncio
    async def test_yields_recoverable_error_on_entity_context_failure(self):
        """When entity context fails, yield a recoverable error event."""
        workflow = _make_workflow()
        # _get_entity_context returns (None, warning)
        workflow.agent._get_entity_context = AsyncMock(
            return_value=(None, "Entity context unavailable: DB error")
        )

        state = ConversationState(messages=[])
        events = []

        with patch("src.agents.architect.workflow.mlflow", None):
            async for event in workflow.stream_conversation(state=state, user_message="hi"):
                events.append(event)

        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1
        assert error_events[0].get("recoverable") is True
        assert "entity_context" in error_events[0].get("error_code", "")
