"""Tests for distributed streaming through the A2A chain.

Verifies that the A2ARemoteClient.stream() method correctly consumes
SSE events, translates them via translate_a2a_event(), and yields
StreamEvent dicts. Also tests the AetherAgentExecutor streaming path
and the _reconstruct_a2a_event() helper.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestA2ARemoteClientStream:
    """A2ARemoteClient.stream() consumes SSE and yields StreamEvents."""

    @pytest.mark.asyncio()
    async def test_stream_yields_token_events(self):
        """Token artifacts in the SSE stream become token StreamEvents."""
        from src.agents.a2a_client import A2ARemoteClient

        sse_events = [
            _make_sse({"kind": "status-update", "taskId": "t1", "contextId": "c1", "final": False, "status": {"state": "working"}}),
            _make_sse({"kind": "artifact-update", "taskId": "t1", "contextId": "c1", "artifact": {"artifactId": "a1", "parts": [{"kind": "text", "text": "Hello "}]}}),
            _make_sse({"kind": "artifact-update", "taskId": "t1", "contextId": "c1", "artifact": {"artifactId": "a2", "parts": [{"kind": "text", "text": "world"}]}}),
            _make_sse({"kind": "status-update", "taskId": "t1", "contextId": "c1", "final": True, "status": {"state": "completed"}}),
        ]

        client = A2ARemoteClient("http://test:8000")
        events = await _collect_stream_events(client, sse_events)

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "Hello "
        assert token_events[1]["content"] == "world"

    @pytest.mark.asyncio()
    async def test_stream_yields_tool_events_from_data_parts(self):
        """DataPart artifacts with a 'type' key are forwarded as-is."""
        from src.agents.a2a_client import A2ARemoteClient

        tool_event = {
            "type": "tool_start",
            "tool": "get_entities",
            "agent": "architect",
        }
        sse_events = [
            _make_sse({"kind": "artifact-update", "taskId": "t1", "contextId": "c1", "artifact": {"artifactId": "e1", "parts": [{"kind": "data", "data": tool_event}]}}),
            _make_sse({"kind": "status-update", "taskId": "t1", "contextId": "c1", "final": True, "status": {"state": "completed"}}),
        ]

        client = A2ARemoteClient("http://test:8000")
        events = await _collect_stream_events(client, sse_events)

        tool_events = [e for e in events if e["type"] == "tool_start"]
        assert len(tool_events) == 1
        assert tool_events[0]["tool"] == "get_entities"

    @pytest.mark.asyncio()
    async def test_stream_handles_error_status(self):
        """Failed task status becomes an error StreamEvent."""
        from src.agents.a2a_client import A2ARemoteClient

        sse_events = [
            _make_sse({"kind": "status-update", "taskId": "t1", "contextId": "c1", "final": True, "status": {"state": "failed"}}),
        ]

        client = A2ARemoteClient("http://test:8000")
        events = await _collect_stream_events(client, sse_events)

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1

    @pytest.mark.asyncio()
    async def test_stream_skips_unparseable_sse(self):
        """Malformed SSE data is logged and skipped."""
        from src.agents.a2a_client import A2ARemoteClient

        sse_events = [
            _make_sse_raw("not-valid-json"),
            _make_sse({"kind": "artifact-update", "taskId": "t1", "contextId": "c1", "artifact": {"artifactId": "a1", "parts": [{"kind": "text", "text": "ok"}]}}),
            _make_sse({"kind": "status-update", "taskId": "t1", "contextId": "c1", "final": True, "status": {"state": "completed"}}),
        ]

        client = A2ARemoteClient("http://test:8000")
        events = await _collect_stream_events(client, sse_events)

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 1


class TestReconstructA2AEvent:
    """_reconstruct_a2a_event() rebuilds typed A2A events from JSON."""

    def test_status_update_reconstruction(self):
        from a2a.types import TaskStatusUpdateEvent

        from src.agents.a2a_client import _reconstruct_a2a_event

        data = {
            "kind": "status-update",
            "taskId": "t1",
            "contextId": "c1",
            "final": True,
            "status": {"state": "completed"},
        }
        event = _reconstruct_a2a_event(data)
        assert isinstance(event, TaskStatusUpdateEvent)

    def test_artifact_update_with_text(self):
        from a2a.types import TaskArtifactUpdateEvent

        from src.agents.a2a_client import _reconstruct_a2a_event

        data = {
            "kind": "artifact-update",
            "taskId": "t1",
            "contextId": "c1",
            "artifact": {
                "artifactId": "a1",
                "parts": [{"kind": "text", "text": "Hello"}],
            },
        }
        event = _reconstruct_a2a_event(data)
        assert isinstance(event, TaskArtifactUpdateEvent)

    def test_unknown_kind_returns_none(self):
        from src.agents.a2a_client import _reconstruct_a2a_event

        assert _reconstruct_a2a_event({"kind": "unknown"}) is None

    def test_no_kind_returns_none(self):
        from src.agents.a2a_client import _reconstruct_a2a_event

        assert _reconstruct_a2a_event({"foo": "bar"}) is None


class TestAetherAgentExecutorStreaming:
    """AetherAgentExecutor routes to streaming when available."""

    @pytest.mark.asyncio()
    async def test_execute_uses_streaming_when_available(self):
        """When agent has stream_conversation(), the streaming path is used."""
        from src.agents.a2a_service import AetherAgentExecutor
        from src.agents.streaming.events import StreamEvent

        token_events = [
            StreamEvent(type="token", content="Hi"),
            StreamEvent(type="state"),
        ]

        agent = MagicMock()

        async def _fake_stream(**kwargs: Any):
            for e in token_events:
                yield e

        agent.stream_conversation = _fake_stream
        agent.invoke = AsyncMock()

        executor = AetherAgentExecutor(agent)

        event_queue = AsyncMock()
        context = MagicMock()
        context.task_id = "t1"
        context.context_id = "c1"
        context.message = MagicMock()
        context.message.parts = []

        await executor.execute(context, event_queue)

        agent.invoke.assert_not_called()
        assert event_queue.enqueue_event.call_count >= 3

    @pytest.mark.asyncio()
    async def test_execute_falls_back_to_invoke(self):
        """When agent lacks stream_conversation(), invoke() is called."""
        from src.agents.a2a_service import AetherAgentExecutor

        agent = MagicMock()
        agent.invoke = AsyncMock(return_value={"response": "ok"})
        del agent.stream_conversation

        executor = AetherAgentExecutor(agent)

        event_queue = AsyncMock()
        context = MagicMock()
        context.task_id = "t1"
        context.context_id = "c1"
        context.message = MagicMock()
        context.message.parts = []

        await executor.execute(context, event_queue)

        agent.invoke.assert_called_once()


class TestTranslateArtifactWithForwardedEvents:
    """Artifact DataParts with a 'type' key are forwarded as StreamEvents."""

    def test_data_part_with_type_key_is_forwarded(self):
        from a2a.types import Artifact, DataPart, Part, TaskArtifactUpdateEvent

        from src.agents.a2a_streaming import translate_a2a_event

        event = TaskArtifactUpdateEvent(
            task_id="t1",
            context_id="c1",
            artifact=Artifact(
                artifact_id="e1",
                parts=[
                    Part(
                        root=DataPart(
                            data={
                                "type": "tool_start",
                                "tool": "list_entities",
                                "agent": "architect",
                            }
                        )
                    )
                ],
            ),
        )
        result = translate_a2a_event(event)
        assert result is not None
        assert result["type"] == "tool_start"
        assert result["tool"] == "list_entities"

    def test_data_part_without_type_remains_tool_result(self):
        from a2a.types import Artifact, DataPart, Part, TaskArtifactUpdateEvent

        from src.agents.a2a_streaming import translate_a2a_event

        event = TaskArtifactUpdateEvent(
            task_id="t1",
            context_id="c1",
            artifact=Artifact(
                artifact_id="a1",
                parts=[Part(root=DataPart(data={"active_agent": "architect"}))],
            ),
        )
        result = translate_a2a_event(event)
        assert result is not None
        assert result["type"] == "_tool_result"


# ── Helpers ──────────────────────────────────────────────────────────


def _make_sse(data: dict[str, Any]) -> MagicMock:
    """Create a mock SSE event with JSON data."""
    mock = MagicMock()
    mock.data = json.dumps(data)
    return mock


def _make_sse_raw(raw: str) -> MagicMock:
    """Create a mock SSE event with raw string data."""
    mock = MagicMock()
    mock.data = raw
    return mock


async def _collect_stream_events(
    client: Any,
    sse_events: list[MagicMock],
) -> list[dict[str, Any]]:
    """Patch httpx and collect all events from client.stream()."""

    async def _fake_aiter_sse():
        for evt in sse_events:
            yield evt

    mock_event_source = MagicMock()
    mock_event_source.aiter_sse = _fake_aiter_sse

    class _FakeAsyncCtx:
        async def __aenter__(self):
            return mock_event_source

        async def __aexit__(self, *args: Any):
            pass

    fake_state = MagicMock()
    fake_state.model_dump = MagicMock(return_value={})
    fake_state.messages = []

    with patch("src.agents.a2a_client.aconnect_sse", return_value=_FakeAsyncCtx()):
        events = []
        async for event in client.stream(fake_state):
            events.append(dict(event))
        return events
