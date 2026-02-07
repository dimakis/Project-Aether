"""Unit tests for the real LLM token streaming pipeline.

Tests the StreamEvent, ArchitectWorkflow.stream_conversation(),
and the TOOL_AGENT_MAP module-level constant.
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from src.agents.architect import ArchitectWorkflow, StreamEvent
from src.api.routes.openai_compat import TOOL_AGENT_MAP
from src.graph.state import ConversationState


# ---------------------------------------------------------------------------
# StreamEvent
# ---------------------------------------------------------------------------


class TestStreamEvent:
    """Verify StreamEvent construction and dict-like behaviour."""

    def test_token_event(self):
        ev = StreamEvent(type="token", content="Hello")
        assert ev["type"] == "token"
        assert ev["content"] == "Hello"
        assert ev["tool"] is None

    def test_tool_start_event(self):
        ev = StreamEvent(type="tool_start", tool="analyze_energy", agent="data_scientist")
        assert ev["type"] == "tool_start"
        assert ev["tool"] == "analyze_energy"
        assert ev["agent"] == "data_scientist"

    def test_tool_end_event(self):
        ev = StreamEvent(type="tool_end", tool="analyze_energy", result="ok")
        assert ev["type"] == "tool_end"
        assert ev["result"] == "ok"

    def test_state_event(self):
        state = ConversationState(messages=[])
        ev = StreamEvent(type="state", state=state)
        assert ev["type"] == "state"
        assert ev["state"] is state

    def test_approval_event(self):
        ev = StreamEvent(type="approval_required", tool="execute_service", content="Need approval")
        assert ev["type"] == "approval_required"
        assert ev["tool"] == "execute_service"
        assert ev["content"] == "Need approval"


# ---------------------------------------------------------------------------
# TOOL_AGENT_MAP
# ---------------------------------------------------------------------------


class TestToolAgentMap:
    """Verify the module-level TOOL_AGENT_MAP has all expected mappings."""

    def test_specialist_tools_mapped(self):
        assert TOOL_AGENT_MAP["consult_energy_analyst"] == "energy_analyst"
        assert TOOL_AGENT_MAP["consult_behavioral_analyst"] == "behavioral_analyst"
        assert TOOL_AGENT_MAP["consult_diagnostic_analyst"] == "diagnostic_analyst"

    def test_dashboard_tools_mapped(self):
        assert TOOL_AGENT_MAP["generate_dashboard_yaml"] == "dashboard_designer"
        assert TOOL_AGENT_MAP["validate_dashboard_yaml"] == "dashboard_designer"
        assert TOOL_AGENT_MAP["list_dashboards"] == "dashboard_designer"

    def test_developer_tools_mapped(self):
        assert TOOL_AGENT_MAP["deploy_automation"] == "developer"
        assert TOOL_AGENT_MAP["create_script"] == "developer"

    def test_librarian_tools_mapped(self):
        assert TOOL_AGENT_MAP["discover_entities"] == "librarian"

    def test_system_tools_mapped(self):
        assert TOOL_AGENT_MAP["create_insight_schedule"] == "system"
        assert TOOL_AGENT_MAP["seek_approval"] == "system"

    def test_data_scientist_tools_mapped(self):
        assert TOOL_AGENT_MAP["analyze_energy"] == "data_scientist"
        assert TOOL_AGENT_MAP["run_custom_analysis"] == "data_scientist"


# ---------------------------------------------------------------------------
# ArchitectWorkflow.stream_conversation
# ---------------------------------------------------------------------------


class TestStreamConversation:
    """Test the streaming generator with mocked LLM."""

    @pytest.mark.asyncio
    async def test_simple_token_streaming(self):
        """Tokens from astream() should yield StreamEvent(type='token')."""
        # Create mock chunks that the LLM would yield
        chunks = [
            AIMessageChunk(content="Hello"),
            AIMessageChunk(content=" world"),
            AIMessageChunk(content="!"),
        ]

        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(return_value=_async_iter(chunks))
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        workflow = ArchitectWorkflow(model_name="test-model")
        workflow.agent._llm = mock_llm

        # Mock entity context
        with patch.object(workflow.agent, "_get_entity_context", return_value=None):
            with patch.object(workflow.agent, "_get_ha_tools", return_value=[]):
                state = ConversationState(messages=[])
                events = []
                async for ev in workflow.stream_conversation(state, "Hi"):
                    events.append(ev)

        # Should have 3 token events + 1 state event
        token_events = [e for e in events if e["type"] == "token"]
        state_events = [e for e in events if e["type"] == "state"]
        assert len(token_events) == 3
        assert token_events[0]["content"] == "Hello"
        assert token_events[1]["content"] == " world"
        assert token_events[2]["content"] == "!"
        assert len(state_events) == 1

    @pytest.mark.asyncio
    async def test_final_state_has_messages(self):
        """The final state event should have the AI response in messages."""
        chunks = [AIMessageChunk(content="Response text")]

        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(return_value=_async_iter(chunks))
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        workflow = ArchitectWorkflow(model_name="test-model")
        workflow.agent._llm = mock_llm

        with patch.object(workflow.agent, "_get_entity_context", return_value=None):
            with patch.object(workflow.agent, "_get_ha_tools", return_value=[]):
                state = ConversationState(messages=[])
                events = []
                async for ev in workflow.stream_conversation(state, "Hello"):
                    events.append(ev)

        final_state = events[-1]["state"]
        assert final_state is not None
        # Should have: HumanMessage("Hello") + AIMessage("Response text")
        assert len(final_state.messages) == 2
        assert isinstance(final_state.messages[0], HumanMessage)
        assert isinstance(final_state.messages[1], AIMessage)
        assert final_state.messages[1].content == "Response text"

    @pytest.mark.asyncio
    async def test_empty_content_chunks_ignored(self):
        """Chunks with empty content should not yield token events."""
        chunks = [
            AIMessageChunk(content=""),
            AIMessageChunk(content="Real content"),
            AIMessageChunk(content=""),
        ]

        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(return_value=_async_iter(chunks))
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        workflow = ArchitectWorkflow(model_name="test-model")
        workflow.agent._llm = mock_llm

        with patch.object(workflow.agent, "_get_entity_context", return_value=None):
            with patch.object(workflow.agent, "_get_ha_tools", return_value=[]):
                state = ConversationState(messages=[])
                events = []
                async for ev in workflow.stream_conversation(state, "Hi"):
                    events.append(ev)

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 1
        assert token_events[0]["content"] == "Real content"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _async_iter(items):
    """Create an async iterator from a list."""
    for item in items:
        yield item
