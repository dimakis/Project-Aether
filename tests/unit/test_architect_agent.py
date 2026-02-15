"""Unit tests for the Architect agent.

T092: Tests for ArchitectAgent proposal generation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage


class TestArchitectAgent:
    """Test ArchitectAgent functionality."""

    @pytest.fixture
    def mock_llm_response(self):
        """Create mock LLM response."""
        content = """I understand you want to turn on the lights when you get home.

Here's my proposal:

```json
{
  "proposal": {
    "name": "Turn on lights when arriving home",
    "description": "Automatically turns on the living room lights when your phone connects to home WiFi",
    "trigger": [{"platform": "state", "entity_id": "device_tracker.phone", "to": "home"}],
    "conditions": [],
    "actions": [{"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}],
    "mode": "single"
  }
}
```

Would you like me to adjust anything?"""

        response = MagicMock()
        response.content = content
        response.response_metadata = {"token_usage": {"total_tokens": 150}}
        return response

    @pytest.mark.asyncio
    async def test_architect_invoke_generates_proposal(self, mock_llm_response):
        """Test that Architect generates proposals from user input."""
        from src.agents.architect import ArchitectAgent
        from src.graph.state import ConversationState

        # Create mock that handles bind_tools chain
        mock_bound_llm = MagicMock()
        mock_bound_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_bound_llm)
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        with patch.object(ArchitectAgent, "llm", new=mock_llm):
            agent = ArchitectAgent()
            state = ConversationState(
                messages=[HumanMessage(content="Turn on lights when I get home")]
            )

            result = await agent.invoke(state)

            assert "messages" in result
            assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_extract_proposal_from_response(self):
        """Test proposal extraction from LLM response."""
        from src.agents.architect import ArchitectAgent

        agent = ArchitectAgent()

        # Response with valid proposal JSON
        response_with_proposal = """Here's my proposal:

```json
{
  "proposal": {
    "name": "Test Automation",
    "trigger": [{"platform": "time", "at": "08:00"}],
    "actions": [{"service": "light.turn_on"}],
    "mode": "single"
  }
}
```"""

        result = agent._extract_proposal(response_with_proposal)
        assert result is not None
        assert result["name"] == "Test Automation"
        assert result["trigger"][0]["platform"] == "time"

    @pytest.mark.asyncio
    async def test_extract_proposal_no_json(self):
        """Test proposal extraction when no JSON present."""
        from src.agents.architect import ArchitectAgent

        agent = ArchitectAgent()

        response_no_proposal = "Let me understand your requirements better. What time would you like the lights to turn on?"

        result = agent._extract_proposal(response_no_proposal)
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_proposal_invalid_json(self):
        """Test proposal extraction with invalid JSON."""
        from src.agents.architect import ArchitectAgent

        agent = ArchitectAgent()

        response_invalid = """Here's my proposal:

```json
{ invalid json }
```"""

        result = agent._extract_proposal(response_invalid)
        assert result is None

    @pytest.mark.asyncio
    async def test_proposal_to_yaml(self):
        """Test YAML generation from proposal data."""
        from src.agents.architect import ArchitectAgent

        agent = ArchitectAgent()

        proposal_data = {
            "name": "Morning Lights",
            "description": "Turn on lights at 7am",
            "trigger": [{"platform": "time", "at": "07:00:00"}],
            "actions": [{"service": "light.turn_on", "target": {"entity_id": "light.bedroom"}}],
            "mode": "single",
        }

        yaml_str = agent._proposal_to_yaml(proposal_data)

        assert "alias: Morning Lights" in yaml_str
        assert "trigger:" in yaml_str
        assert "action:" in yaml_str
        assert "mode: single" in yaml_str

    @pytest.mark.asyncio
    async def test_proposal_to_yaml_script(self):
        """Test YAML generation for script proposals."""
        from src.agents.architect import ArchitectAgent

        agent = ArchitectAgent()

        proposal_data = {
            "name": "Good Night Routine",
            "description": "Turn off all lights and lock doors",
            "proposal_type": "script",
            "actions": [
                {"service": "light.turn_off", "target": {"entity_id": "all"}},
                {"service": "lock.lock", "target": {"entity_id": "lock.front_door"}},
            ],
            "mode": "single",
        }

        yaml_str = agent._proposal_to_yaml(proposal_data)

        assert "alias: Good Night Routine" in yaml_str
        assert "sequence:" in yaml_str
        assert "mode: single" in yaml_str
        # Scripts should NOT have triggers
        assert "trigger:" not in yaml_str

    @pytest.mark.asyncio
    async def test_proposal_to_yaml_scene(self):
        """Test YAML generation for scene proposals."""
        from src.agents.architect import ArchitectAgent

        agent = ArchitectAgent()

        proposal_data = {
            "name": "Movie Time",
            "description": "Set lights for watching movies",
            "proposal_type": "scene",
            "actions": [
                {"entity_id": "light.living_room", "state": "on", "brightness": 50},
                {"entity_id": "light.ceiling", "state": "off"},
            ],
        }

        yaml_str = agent._proposal_to_yaml(proposal_data)

        assert "name: Movie Time" in yaml_str
        assert "entities:" in yaml_str
        # Scenes should NOT have triggers or sequences
        assert "trigger:" not in yaml_str
        assert "sequence:" not in yaml_str

    @pytest.mark.asyncio
    async def test_extract_proposal_with_type(self):
        """Test proposal extraction preserves proposal_type field."""
        from src.agents.architect import ArchitectAgent

        agent = ArchitectAgent()

        response = """Here's a script proposal:

```json
{
  "proposal": {
    "name": "Good Night",
    "proposal_type": "script",
    "actions": [{"service": "light.turn_off"}],
    "mode": "single"
  }
}
```"""

        result = agent._extract_proposal(response)
        assert result is not None
        assert result["name"] == "Good Night"
        assert result["proposal_type"] == "script"

    @pytest.mark.asyncio
    async def test_build_messages_includes_system_prompt(self):
        """Test that message building includes system prompt."""
        from src.agents.architect import ArchitectAgent
        from src.agents.prompts import load_prompt
        from src.graph.state import ConversationState

        agent = ArchitectAgent()
        state = ConversationState(messages=[HumanMessage(content="Test message")])

        messages = agent._build_messages(state)

        # First message should be system prompt
        ARCHITECT_SYSTEM_PROMPT = load_prompt("architect_system")
        assert len(messages) >= 2
        assert messages[0].content == ARCHITECT_SYSTEM_PROMPT
        assert messages[1].content == "Test message"


class TestArchitectWorkflow:
    """Test ArchitectWorkflow functionality."""

    @staticmethod
    def _make_mock_mlflow():
        """Create a mock mlflow module with trace as a passthrough decorator."""
        from unittest.mock import MagicMock

        mock_mlflow = MagicMock()

        def noop_trace(**kwargs):
            def decorator(fn):
                return fn

            return decorator

        mock_mlflow.trace = noop_trace
        return mock_mlflow

    @pytest.mark.asyncio
    async def test_start_conversation(self):
        """Test starting a new conversation."""
        from unittest.mock import AsyncMock, patch

        from src.agents.architect import ArchitectWorkflow

        mock_mlflow = self._make_mock_mlflow()

        with (
            patch("src.agents.architect.ArchitectAgent") as MockAgent,
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
        ):
            mock_agent = MockAgent.return_value
            mock_agent.invoke = AsyncMock(
                return_value={"messages": [AIMessage(content="Hello! How can I help?")]}
            )

            workflow = ArchitectWorkflow()
            workflow.agent = mock_agent

            state = await workflow.start_conversation("I want to automate my lights")

            assert state is not None
            assert len(state.messages) > 0
            mock_agent.invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_continue_conversation(self):
        """Test continuing an existing conversation."""
        from unittest.mock import AsyncMock, patch

        from src.agents.architect import ArchitectWorkflow
        from src.graph.state import ConversationState

        mock_mlflow = self._make_mock_mlflow()

        with (
            patch("src.agents.architect.ArchitectAgent") as MockAgent,
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
        ):
            mock_agent = MockAgent.return_value
            mock_agent.invoke = AsyncMock(
                return_value={"messages": [AIMessage(content="I understand, let me help")]}
            )

            workflow = ArchitectWorkflow()
            workflow.agent = mock_agent

            initial_state = ConversationState(messages=[HumanMessage(content="Initial message")])

            state = await workflow.continue_conversation(
                state=initial_state,
                user_message="Follow up message",
            )

            assert state is not None
            # State should have at least the response
            assert len(state.messages) >= 1
            mock_agent.invoke.assert_called_once()


class TestHandleToolCallsParallel:
    """Test that _handle_tool_calls runs independent read-only tools in parallel."""

    @pytest.mark.asyncio
    async def test_read_only_tools_run_concurrently(self):
        """Multiple read-only tool calls should execute concurrently."""
        from src.agents.architect import ArchitectAgent
        from src.graph.state import ConversationState

        call_times: list[tuple[str, float, float]] = []

        def _make_slow_ainvoke(name: str):
            async def _ainvoke(args):
                start = asyncio.get_event_loop().time()
                await asyncio.sleep(0.1)
                end = asyncio.get_event_loop().time()
                call_times.append((name, start, end))
                return f"{name} result"

            return _ainvoke

        tool_a = MagicMock()
        tool_a.name = "get_entity_state"
        tool_a.ainvoke = AsyncMock(side_effect=_make_slow_ainvoke("a"))

        tool_b = MagicMock()
        tool_b.name = "list_entities_by_domain"
        tool_b.ainvoke = AsyncMock(side_effect=_make_slow_ainvoke("b"))

        tool_c = MagicMock()
        tool_c.name = "search_entities"
        tool_c.ainvoke = AsyncMock(side_effect=_make_slow_ainvoke("c"))

        response = AIMessage(
            content="",
            tool_calls=[
                {"name": "get_entity_state", "args": {"entity_id": "light.a"}, "id": "call_1"},
                {"name": "list_entities_by_domain", "args": {"domain": "light"}, "id": "call_2"},
                {"name": "search_entities", "args": {"query": "temp"}, "id": "call_3"},
            ],
        )

        mock_llm = MagicMock()
        follow_up = AIMessage(content="Here are the results.")
        mock_llm.ainvoke = AsyncMock(return_value=follow_up)

        with patch("src.agents.architect.agent.get_llm", return_value=mock_llm):
            agent = ArchitectAgent.__new__(ArchitectAgent)
            agent._llm = mock_llm

            state = ConversationState(messages=[])

            result = await agent._handle_tool_calls(
                response=response,
                messages=[HumanMessage(content="test")],
                tools=[tool_a, tool_b, tool_c],
                state=state,
            )

        assert len(call_times) == 3

        # If parallel: wall_time ~ 0.1s. If sequential: wall_time ~ 0.3s.
        starts = [t[1] for t in call_times]
        ends = [t[2] for t in call_times]
        wall_time = max(ends) - min(starts)
        assert wall_time < 0.25, (
            f"Tools ran sequentially (wall_time={wall_time:.3f}s). "
            "Expected parallel execution with wall_time < 0.25s."
        )

        # Should still produce ToolMessages and a follow-up
        assert result is not None
        messages = result["messages"]
        assert len(messages) >= 4  # response + 3 ToolMessages + follow-up


class TestGetEntityContextParallel:
    """Test that _get_entity_context runs DB queries in parallel."""

    @pytest.mark.asyncio
    async def test_independent_queries_run_concurrently(self):
        """Domain counts, areas, devices, services should be fetched in parallel."""
        from src.agents.architect import ArchitectAgent
        from src.agents.architect.entity_context import _invalidate_entity_context_cache
        from src.graph.state import ConversationState

        _invalidate_entity_context_cache()

        call_log: list[tuple[str, float]] = []

        def _make_tracked_coro(name: str, result):
            """Create an async function that tracks when it's called."""

            async def _fn(*args, **kwargs):
                call_log.append((name, asyncio.get_event_loop().time()))
                await asyncio.sleep(0.05)
                return result

            return _fn

        mock_entity_repo = MagicMock()
        mock_entity_repo.get_domain_counts = AsyncMock(
            side_effect=_make_tracked_coro("counts", {"light": 5, "switch": 2})
        )
        mock_entity_repo.list_by_domains = AsyncMock(side_effect=_make_tracked_coro("entities", {}))

        mock_area_repo = MagicMock()
        mock_area_repo.list_all = AsyncMock(side_effect=_make_tracked_coro("areas", []))

        mock_device_repo = MagicMock()
        mock_device_repo.list_all = AsyncMock(side_effect=_make_tracked_coro("devices", []))

        mock_service_repo = MagicMock()
        mock_service_repo.list_all = AsyncMock(side_effect=_make_tracked_coro("services", []))

        # Mock session factory to return a fresh mock session each time
        mock_factory = MagicMock(side_effect=lambda: AsyncMock())

        with (
            patch(
                "src.agents.architect.entity_context.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "src.agents.architect.entity_context.EntityRepository",
                return_value=mock_entity_repo,
            ),
            patch(
                "src.agents.architect.entity_context.DeviceRepository",
                return_value=mock_device_repo,
            ),
            patch(
                "src.agents.architect.entity_context.AreaRepository", return_value=mock_area_repo
            ),
            patch(
                "src.agents.architect.entity_context.ServiceRepository",
                return_value=mock_service_repo,
            ),
        ):
            agent = ArchitectAgent.__new__(ArchitectAgent)
            state = ConversationState(messages=[])

            await agent._get_entity_context(state)

        # All repos should have been called
        assert len(call_log) >= 4
        # Check that calls overlapped (started before others finished)
        times = [t[1] for t in call_log]
        spread = max(times) - min(times)
        # If parallel: spread ~ 0 (all start nearly together)
        # If sequential: spread ~ 0.15+ (each waits for previous)
        assert spread < 0.1, (
            f"Queries ran sequentially (time spread={spread:.3f}s). "
            "Expected parallel execution with spread < 0.1s."
        )

        _invalidate_entity_context_cache()
