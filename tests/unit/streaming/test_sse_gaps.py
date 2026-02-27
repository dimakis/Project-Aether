"""Tests closing identified SSE streaming coverage gaps.

Phase 3 of Feature 31: Streaming Tool Executor Refactor.
Covers: approval_required, delegation, thinking filter, mid-stream
errors, and [DONE] sentinel.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.streaming.events import StreamEvent
from src.graph.state import ConversationState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect_sse_lines(
    events: list[StreamEvent],
    *,
    is_background: bool = False,
) -> list[str]:
    """Run _stream_chat_completion with mocked workflow yielding given events.

    Returns raw SSE lines as a list of strings.
    """
    from src.api.routes.openai_compat import ChatCompletionRequest, _stream_chat_completion

    async def mock_stream_conversation(state, user_message, session=None):
        for ev in events:
            yield ev

    mock_workflow = MagicMock()
    mock_workflow.stream_conversation = mock_stream_conversation

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()

    request = ChatCompletionRequest(
        model="test",
        messages=[{"role": "user", "content": "test"}],
        stream=True,
        agent="architect",
    )

    # Mock mlflow at the module level to prevent real MLflow calls
    mock_mlflow = MagicMock()
    mock_mlflow.set_tag = MagicMock()
    mock_mlflow.get_current_active_span.return_value = None

    lines = []
    with (
        patch("src.api.routes.openai_compat.handlers.get_session") as mock_get_session,
        patch("src.api.routes.openai_compat.handlers.start_experiment_run") as mock_run,
        patch("src.api.routes.openai_compat.handlers.session_context"),
        patch("src.api.routes.openai_compat.handlers.model_context"),
        patch(
            "src.api.routes.openai_compat.handlers.ArchitectWorkflow", return_value=mock_workflow
        ),
        patch("src.api.routes.openai_compat.handlers.log_param"),
        patch.dict("sys.modules", {"mlflow": mock_mlflow}),
    ):
        mock_run.return_value.__enter__ = MagicMock()
        mock_run.return_value.__exit__ = MagicMock(return_value=False)

        # get_session as async context manager
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get_session.return_value = mock_ctx

        async for line in _stream_chat_completion(request):
            lines.append(line)

    return lines


def _parse_sse_data(lines: list[str]) -> list[dict | str]:
    """Parse SSE data: lines into JSON dicts or raw strings."""
    results = []
    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line.removeprefix("data: ").strip()
        if payload == "[DONE]":
            results.append("[DONE]")
        else:
            try:
                results.append(json.loads(payload))
            except json.JSONDecodeError:
                results.append(payload)
    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApprovalRequiredSSE:
    """Verify approval_required events are emitted as text chunks."""

    @pytest.mark.asyncio
    async def test_approval_required_emitted_as_text_chunk(self):
        events = [
            StreamEvent(
                type="approval_required",
                tool="execute_service",
                content="Approval needed: execute_service({action: on})",
            ),
            StreamEvent(type="state", state=ConversationState(messages=[])),
        ]

        lines = await _collect_sse_lines(events)
        parsed = _parse_sse_data(lines)

        # Find the chunk that carries the approval text
        text_chunks = [
            p
            for p in parsed
            if isinstance(p, dict) and "choices" in p and p["choices"][0]["delta"].get("content")
        ]
        assert len(text_chunks) >= 1
        content = text_chunks[0]["choices"][0]["delta"]["content"]
        assert "approval" in content.lower()


class TestDelegationSSE:
    """Verify delegation events are forwarded as SSE delegation events."""

    @pytest.mark.asyncio
    async def test_delegation_event_emitted(self):
        events = [
            StreamEvent(type="token", content="Hello"),
            StreamEvent(
                type="delegation",
                agent="architect",
                content="Please analyze energy data",
                target="energy_analyst",
            ),
            StreamEvent(type="state", state=ConversationState(messages=[])),
        ]

        lines = await _collect_sse_lines(events)
        parsed = _parse_sse_data(lines)

        delegation_events = [
            p for p in parsed if isinstance(p, dict) and p.get("type") == "delegation"
        ]
        assert len(delegation_events) >= 1
        assert delegation_events[0]["from"] == "architect"
        assert delegation_events[0]["to"] == "energy_analyst"
        assert "analyze energy" in delegation_events[0]["content"].lower()


class TestThinkingFilter:
    """Verify _StreamingTagFilter separates thinking from visible content."""

    def test_thinking_tags_separated(self):
        from src.api.routes.openai_compat.streaming_filter import _StreamingTagFilter

        f = _StreamingTagFilter()

        # Feed tokens that include thinking tags
        results = []
        for token in ["<thinking>", "I need to think", "</thinking>", "Here is the answer"]:
            for ft in f.feed(token):
                results.append((ft.text, ft.is_thinking))
        for ft in f.flush():
            results.append((ft.text, ft.is_thinking))

        # Concatenate thinking and visible content
        thinking_text = "".join(text for text, is_t in results if is_t and text)
        visible_text = "".join(text for text, is_t in results if not is_t and text)

        # Thinking content should contain the inner text
        assert "need to think" in thinking_text.lower()
        # Visible content should contain the answer
        assert "answer" in visible_text.lower()

    def test_no_thinking_tags_passthrough(self):
        from src.api.routes.openai_compat.streaming_filter import _StreamingTagFilter

        f = _StreamingTagFilter()
        results = []
        for token in ["Hello", " world", "!"]:
            for ft in f.feed(token):
                results.append(ft)
        for ft in f.flush():
            results.append(ft)

        # All content should be non-thinking
        assert all(not ft.is_thinking for ft in results)
        full_text = "".join(ft.text for ft in results)
        assert full_text == "Hello world!"

    @pytest.mark.asyncio
    async def test_thinking_events_in_sse_stream(self):
        """Thinking content inside tokens should produce SSE thinking events."""
        events = [
            StreamEvent(type="token", content="<thinking>Let me reason</thinking>The answer is 42"),
            StreamEvent(type="state", state=ConversationState(messages=[])),
        ]

        lines = await _collect_sse_lines(events)
        parsed = _parse_sse_data(lines)

        thinking_events = [p for p in parsed if isinstance(p, dict) and p.get("type") == "thinking"]
        text_chunks = [
            p
            for p in parsed
            if isinstance(p, dict) and "choices" in p and p["choices"][0]["delta"].get("content")
        ]

        # Should have at least one thinking event
        assert len(thinking_events) >= 1
        # Should have visible text
        visible_text = "".join(c["choices"][0]["delta"]["content"] for c in text_chunks)
        assert "42" in visible_text


class TestDoneSentinel:
    """Verify [DONE] sentinel is emitted at end of stream."""

    @pytest.mark.asyncio
    async def test_done_sentinel_emitted(self):
        events = [
            StreamEvent(type="token", content="Hello"),
            StreamEvent(type="state", state=ConversationState(messages=[])),
        ]

        lines = await _collect_sse_lines(events)
        parsed = _parse_sse_data(lines)

        assert "[DONE]" in parsed
        # [DONE] should be the last item
        assert parsed[-1] == "[DONE]"

    @pytest.mark.asyncio
    async def test_metadata_before_done(self):
        """Metadata event should appear before [DONE]."""
        events = [
            StreamEvent(type="token", content="Hello"),
            StreamEvent(type="state", state=ConversationState(messages=[])),
        ]

        lines = await _collect_sse_lines(events)
        parsed = _parse_sse_data(lines)

        # Find metadata and DONE positions
        metadata_indices = [
            i for i, p in enumerate(parsed) if isinstance(p, dict) and p.get("type") == "metadata"
        ]
        done_index = parsed.index("[DONE]")

        assert len(metadata_indices) >= 1
        assert metadata_indices[-1] < done_index


class TestMidStreamError:
    """Verify mid-stream errors produce error SSE events."""

    @pytest.mark.asyncio
    async def test_exception_produces_error_sse(self):
        """An exception during streaming should produce an SSE error event."""
        from src.api.routes.openai_compat import ChatCompletionRequest, _stream_chat_completion

        async def failing_stream(state, user_message, session=None):
            yield StreamEvent(type="token", content="Hello")
            raise RuntimeError("LLM connection lost")

        mock_workflow = MagicMock()
        mock_workflow.stream_conversation = failing_stream

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        mock_mlflow = MagicMock()
        mock_mlflow.set_tag = MagicMock()
        mock_mlflow.get_current_active_span.return_value = None

        request = ChatCompletionRequest(
            model="test",
            messages=[{"role": "user", "content": "test"}],
            stream=True,
            agent="architect",
        )

        lines = []
        with (
            patch("src.api.routes.openai_compat.handlers.get_session") as mock_get_session,
            patch("src.api.routes.openai_compat.handlers.start_experiment_run") as mock_run,
            patch("src.api.routes.openai_compat.handlers.session_context"),
            patch("src.api.routes.openai_compat.handlers.model_context"),
            patch(
                "src.api.routes.openai_compat.handlers.ArchitectWorkflow",
                return_value=mock_workflow,
            ),
            patch("src.api.routes.openai_compat.handlers.log_param"),
            patch.dict("sys.modules", {"mlflow": mock_mlflow}),
        ):
            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            async for line in _stream_chat_completion(request):
                lines.append(line)

        parsed = _parse_sse_data(lines)

        # Should have a generic error event (not leaking exception details)
        error_events = [p for p in parsed if isinstance(p, dict) and p.get("error")]
        assert len(error_events) >= 1
        error_msg = str(error_events[0]).lower()
        assert "internal error" in error_msg or "server logs" in error_msg
