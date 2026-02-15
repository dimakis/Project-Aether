"""Unit tests for the real LLM token streaming pipeline.

Tests the StreamEvent, ArchitectWorkflow.stream_conversation(),
the TOOL_AGENT_MAP module-level constant, and proposal extraction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from src.agents.architect import ArchitectAgent, ArchitectWorkflow, StreamEvent
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
    """Verify the module-level TOOL_AGENT_MAP has the expected mappings.

    After the architect tool reduction, the map only covers tools that
    the Architect can actually invoke (12 tools).
    """

    def test_ds_team_tool_mapped(self):
        assert TOOL_AGENT_MAP["consult_data_science_team"] == "data_science_team"

    def test_librarian_tools_mapped(self):
        assert TOOL_AGENT_MAP["discover_entities"] == "librarian"

    def test_system_tools_mapped(self):
        assert TOOL_AGENT_MAP["create_insight_schedule"] == "system"
        assert TOOL_AGENT_MAP["seek_approval"] == "system"

    def test_ha_query_tools_mapped_to_architect(self):
        for tool_name in [
            "get_entity_state",
            "list_entities_by_domain",
            "search_entities",
            "get_domain_summary",
            "list_automations",
            "render_template",
            "get_ha_logs",
            "check_ha_config",
        ]:
            assert TOOL_AGENT_MAP[tool_name] == "architect", f"{tool_name} not mapped"

    def test_old_tools_removed(self):
        """Old tools should no longer be in the map."""
        for old_tool in [
            "analyze_energy",
            "run_custom_analysis",
            "diagnose_issue",
            "consult_energy_analyst",
            "consult_behavioral_analyst",
            "consult_diagnostic_analyst",
            "deploy_automation",
        ]:
            assert old_tool not in TOOL_AGENT_MAP, f"{old_tool} should be removed"


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
        with patch.object(workflow.agent, "_get_entity_context", return_value=(None, None)):
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

        with patch.object(workflow.agent, "_get_entity_context", return_value=(None, None)):
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

        with patch.object(workflow.agent, "_get_entity_context", return_value=(None, None)):
            with patch.object(workflow.agent, "_get_ha_tools", return_value=[]):
                state = ConversationState(messages=[])
                events = []
                async for ev in workflow.stream_conversation(state, "Hi"):
                    events.append(ev)

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 1
        assert token_events[0]["content"] == "Real content"


# ---------------------------------------------------------------------------
# _extract_proposals (multi-proposal extraction)
# ---------------------------------------------------------------------------


class TestExtractProposals:
    """Test the new _extract_proposals method that returns ALL proposals."""

    def setup_method(self):
        self.agent = ArchitectAgent(model_name="test")

    def test_single_proposal(self):
        response = """Here's a proposal:
```json
{"proposal": {"name": "Sunset Lights", "trigger": [{"platform": "sun"}], "actions": []}}
```"""
        proposals = self.agent._extract_proposals(response)
        assert len(proposals) == 1
        assert proposals[0]["name"] == "Sunset Lights"

    def test_multiple_proposals(self):
        response = """Here are 3 proposals:

```json
{"proposal": {"name": "Morning Lights", "trigger": [{"platform": "time"}], "actions": []}}
```

```json
{"proposal": {"name": "Evening Routine", "trigger": [{"platform": "sun"}], "actions": []}}
```

```json
{"proposal": {"name": "Night Lock", "trigger": [{"platform": "time"}], "actions": []}}
```"""
        proposals = self.agent._extract_proposals(response)
        assert len(proposals) == 3
        assert proposals[0]["name"] == "Morning Lights"
        assert proposals[1]["name"] == "Evening Routine"
        assert proposals[2]["name"] == "Night Lock"

    def test_no_proposals(self):
        response = "I don't have any proposals yet."
        proposals = self.agent._extract_proposals(response)
        assert len(proposals) == 0

    def test_non_proposal_json_blocks_ignored(self):
        response = """Here's some data:
```json
{"data": "not a proposal"}
```"""
        proposals = self.agent._extract_proposals(response)
        assert len(proposals) == 0

    def test_malformed_json_skipped(self):
        response = """Proposals:
```json
{"proposal": {"name": "Good One", "trigger": [], "actions": []}}
```

```json
{"proposal": {"name": truncated
```

```json
{"proposal": {"name": "Also Good", "trigger": [], "actions": []}}
```"""
        proposals = self.agent._extract_proposals(response)
        assert len(proposals) == 2
        assert proposals[0]["name"] == "Good One"
        assert proposals[1]["name"] == "Also Good"

    def test_extract_proposal_returns_first(self):
        """The singular _extract_proposal returns only the first."""
        response = """
```json
{"proposal": {"name": "First", "trigger": [], "actions": []}}
```

```json
{"proposal": {"name": "Second", "trigger": [], "actions": []}}
```"""
        result = self.agent._extract_proposal(response)
        assert result is not None
        assert result["name"] == "First"


# ---------------------------------------------------------------------------
# Truncated tool call handling
# ---------------------------------------------------------------------------


class TestTruncatedToolCalls:
    """Test that stream_conversation gracefully handles truncated tool calls."""

    @pytest.mark.asyncio
    async def test_empty_name_tool_call_skipped(self):
        """Tool calls with empty name (truncated output) should be skipped."""
        # Simulate LLM generating a tool call with empty name (truncated output)
        chunk_with_tool = AIMessageChunk(
            content="",
            tool_call_chunks=[
                {"name": "", "args": '{"action_type": "automation"}', "id": "call_1", "index": 0}
            ],
        )
        # Follow-up produces text
        follow_up_chunk = AIMessageChunk(content="Here's the result")

        call_count = 0

        async def mock_astream(msgs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield chunk_with_tool
            else:
                yield follow_up_chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        workflow = ArchitectWorkflow(model_name="test-model")
        workflow.agent._llm = mock_llm

        # Create a mock tool so the tool lookup isn't empty
        mock_tool = MagicMock()
        mock_tool.name = "seek_approval"
        mock_tool.ainvoke = AsyncMock(return_value="Proposal submitted")

        with patch.object(workflow.agent, "_get_entity_context", return_value=(None, None)):
            with patch.object(workflow.agent, "_get_ha_tools", return_value=[mock_tool]):
                state = ConversationState(messages=[])
                events = []
                async for ev in workflow.stream_conversation(state, "Create automation"):
                    events.append(ev)

        # The empty-name tool call should NOT have triggered tool_start
        tool_start_events = [e for e in events if e["type"] == "tool_start"]
        assert len(tool_start_events) == 0

        # The mock tool should not have been called
        mock_tool.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_bad_json_args_tool_call_skipped(self):
        """Tool calls with unparseable JSON args should be skipped."""
        chunk_with_tool = AIMessageChunk(
            content="",
            tool_call_chunks=[
                {
                    "name": "seek_approval",
                    "args": '{"action_type": "automation", "name": "Test", "trigger": {"platfor',
                    "id": "call_1",
                    "index": 0,
                }
            ],
        )
        follow_up_chunk = AIMessageChunk(content="I'll try again")

        call_count = 0

        async def mock_astream(msgs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield chunk_with_tool
            else:
                yield follow_up_chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        workflow = ArchitectWorkflow(model_name="test-model")
        workflow.agent._llm = mock_llm

        mock_tool = MagicMock()
        mock_tool.name = "seek_approval"
        mock_tool.ainvoke = AsyncMock(return_value="Proposal submitted")

        with patch.object(workflow.agent, "_get_entity_context", return_value=(None, None)):
            with patch.object(workflow.agent, "_get_ha_tools", return_value=[mock_tool]):
                state = ConversationState(messages=[])
                events = []
                async for ev in workflow.stream_conversation(state, "Create automation"):
                    events.append(ev)

        # The tool should not have been called with corrupt args
        mock_tool.ainvoke.assert_not_called()


# ---------------------------------------------------------------------------
# Fallback response when no visible content
# ---------------------------------------------------------------------------


class TestFallbackResponse:
    """Test that empty visible content produces a fallback message."""

    @pytest.mark.asyncio
    async def test_fallback_when_tools_produce_no_text(self):
        """If tool iterations produce no visible content, emit a fallback."""
        # First call: LLM generates a tool call (no text)
        chunk_with_tool = AIMessageChunk(
            content="",
            tool_call_chunks=[
                {
                    "name": "get_entity_state",
                    "args": '{"entity_id": "light.living_room"}',
                    "id": "call_1",
                    "index": 0,
                }
            ],
        )
        # Follow-up: LLM generates empty content (simulating truncated/empty response)
        follow_up_chunk = AIMessageChunk(content="")

        call_count = 0

        async def mock_astream(msgs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield chunk_with_tool
            else:
                yield follow_up_chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        workflow = ArchitectWorkflow(model_name="test-model")
        workflow.agent._llm = mock_llm

        mock_tool = MagicMock()
        mock_tool.name = "get_entity_state"
        mock_tool.ainvoke = AsyncMock(return_value="light is on")

        with patch.object(workflow.agent, "_get_entity_context", return_value=(None, None)):
            with patch.object(workflow.agent, "_get_ha_tools", return_value=[mock_tool]):
                state = ConversationState(messages=[])
                events = []
                async for ev in workflow.stream_conversation(state, "Check light"):
                    events.append(ev)

        # Should have a fallback token event
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) > 0
        fallback_text = "".join(e["content"] for e in token_events)
        assert "try rephrasing" in fallback_text.lower() or "processed" in fallback_text.lower()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _async_iter(items):
    """Create an async iterator from a list."""
    for item in items:
        yield item
