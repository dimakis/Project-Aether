"""Unit tests for get_committing_session wrapper.

Verifies that the wrapper commits on successful exit and
does NOT commit (allows rollback) on exception.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestGetCommittingSession:
    """get_committing_session commits on successful exit."""

    @pytest.mark.asyncio
    async def test_commits_on_success(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_get_session():
            yield mock_session

        with patch("src.storage.get_session", fake_get_session):
            from src.storage import get_committing_session

            async with get_committing_session() as session:
                assert session is mock_session

        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_commit_on_exception(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_get_session():
            yield mock_session

        with patch("src.storage.get_session", fake_get_session):
            from src.storage import get_committing_session

            with pytest.raises(ValueError, match="test error"):
                async with get_committing_session() as _session:
                    raise ValueError("test error")

        mock_session.commit.assert_not_awaited()


class TestDispatcherSessionFactory:
    """dispatch_tool_calls threads session_factory into execution_context."""

    @pytest.mark.asyncio
    async def test_session_factory_reaches_execution_context(self):
        """session_factory passed to dispatch is available in execution_context."""
        from contextlib import asynccontextmanager

        from src.agents.execution_context import get_execution_context

        captured_factory = None

        class FakeTool:
            async def ainvoke(self, args):
                nonlocal captured_factory
                ctx = get_execution_context()
                captured_factory = ctx.session_factory if ctx else None
                return "ok"

        @asynccontextmanager
        async def dummy_factory():
            yield AsyncMock()

        from src.agents.streaming.parser import ParsedToolCall

        tc = ParsedToolCall(name="test_tool", args={}, id="tc-1", is_mutating=False)

        from src.agents.streaming.dispatcher import dispatch_tool_calls

        events = []
        async for event in dispatch_tool_calls(
            tool_calls=[tc],
            tool_lookup={"test_tool": FakeTool()},
            conversation_id="conv-1",
            session_factory=dummy_factory,
        ):
            events.append(event)

        assert captured_factory is dummy_factory
