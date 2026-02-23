"""Tests for A2A streaming proxy (Phase 4).

Translates A2A TaskStatusUpdateEvent / TaskArtifactUpdateEvent
into StreamEvent dicts that the existing SSE handler understands.
"""

from __future__ import annotations

from a2a.types import (
    Artifact,
    DataPart,
    Part,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)


class TestTranslateA2AEvent:
    """translate_a2a_event() maps A2A events to StreamEvents."""

    def test_working_status_becomes_status_event(self):
        from src.agents.a2a_streaming import translate_a2a_event

        event = TaskStatusUpdateEvent(
            task_id="t1",
            context_id="c1",
            final=False,
            status=TaskStatus(state=TaskState.working),
        )
        result = translate_a2a_event(event)
        assert result is not None
        assert result["type"] == "status"
        assert "working" in result["content"].lower()

    def test_completed_status_becomes_state_event(self):
        from src.agents.a2a_streaming import translate_a2a_event

        event = TaskStatusUpdateEvent(
            task_id="t1",
            context_id="c1",
            final=True,
            status=TaskStatus(state=TaskState.completed),
        )
        result = translate_a2a_event(event)
        assert result is not None
        assert result["type"] == "state"

    def test_failed_status_becomes_error_event(self):
        from src.agents.a2a_streaming import translate_a2a_event

        event = TaskStatusUpdateEvent(
            task_id="t1",
            context_id="c1",
            final=True,
            status=TaskStatus(state=TaskState.failed),
        )
        result = translate_a2a_event(event)
        assert result is not None
        assert result["type"] == "error"

    def test_artifact_with_text_becomes_token_event(self):
        from src.agents.a2a_streaming import translate_a2a_event

        event = TaskArtifactUpdateEvent(
            task_id="t1",
            context_id="c1",
            artifact=Artifact(
                artifact_id="a1",
                parts=[Part(root=TextPart(text="Hello "))],
            ),
        )
        result = translate_a2a_event(event)
        assert result is not None
        assert result["type"] == "token"
        assert result["content"] == "Hello "

    def test_artifact_with_data_becomes_tool_result(self):
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

    def test_none_for_unknown_event(self):
        from src.agents.a2a_streaming import translate_a2a_event

        result = translate_a2a_event("not-an-event")
        assert result is None
