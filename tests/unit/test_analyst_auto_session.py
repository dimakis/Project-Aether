"""Unit tests for BaseAnalyst auto-session from execution context.

Tests that analysts can persist findings even when no explicit session
kwarg is provided, by falling back to the execution context's session factory
via the new _persist_with_fallback helper.

TDD: Analyst auto-session for insight persistence via any invocation path.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.base_analyst import BaseAnalyst
from src.agents.execution_context import (
    clear_execution_context,
    execution_context,
)
from src.graph.state import (
    AgentRole,
    AnalysisState,
    AnalysisType,
    SpecialistFinding,
)


class StubAnalyst(BaseAnalyst):
    """Concrete analyst for testing the auto-session fallback."""

    ROLE = AgentRole.ENERGY_ANALYST
    NAME = "StubAnalyst"

    async def collect_data(self, state):
        return {"data": True}

    async def generate_script(self, state, data):
        return "print('hello')"

    def extract_findings(self, result, state):
        return [
            SpecialistFinding(
                specialist="energy_analyst",
                finding_type="insight",
                title="Test finding",
                description="Found something",
                confidence=0.9,
                entities=["sensor.test"],
            )
        ]

    async def invoke(self, state, **kwargs):
        """Minimal invoke that exercises _persist_with_fallback."""
        findings = self.extract_findings(None, state)
        for f in findings:
            state = self.add_finding(state, f)
        await self._persist_with_fallback(findings, kwargs.get("session"))
        return {"insights": [{"title": f.title} for f in findings]}


class TestPersistWithFallback:
    """Tests for BaseAnalyst._persist_with_fallback()."""

    @pytest.fixture
    def analyst(self):
        return StubAnalyst()

    @pytest.fixture
    def state(self):
        return AnalysisState(
            analysis_type=AnalysisType.ENERGY_OPTIMIZATION,
            entity_ids=["sensor.test"],
            time_range_hours=24,
        )

    @pytest.mark.asyncio
    async def test_persists_with_explicit_session(self, analyst, state):
        """When session is passed explicitly, persist_findings should use it."""
        mock_session = AsyncMock()

        with patch.object(analyst, "persist_findings", new_callable=AsyncMock) as mock_persist:
            await analyst.invoke(state, session=mock_session)

        mock_persist.assert_called_once()
        args = mock_persist.call_args
        assert args[0][1] is mock_session

    @pytest.mark.asyncio
    async def test_persists_with_execution_context_session(self, analyst, state):
        """When no explicit session, analyst should use execution context factory."""
        mock_session = AsyncMock()

        @asynccontextmanager
        async def mock_session_factory():
            yield mock_session

        with patch.object(analyst, "persist_findings", new_callable=AsyncMock) as mock_persist:
            async with execution_context(
                session_factory=mock_session_factory,
                conversation_id="test-conv",
            ):
                await analyst.invoke(state)  # No session kwarg!

        mock_persist.assert_called_once()
        args = mock_persist.call_args
        assert args[0][1] is mock_session

    @pytest.mark.asyncio
    async def test_no_persist_without_session_or_context(self, analyst, state):
        """When no session and no context, findings should not be persisted."""
        clear_execution_context()

        with patch.object(analyst, "persist_findings", new_callable=AsyncMock) as mock_persist:
            await analyst.invoke(state)  # No session, no context

        mock_persist.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_persist_with_context_but_no_factory(self, analyst, state):
        """When context has no session_factory, findings should not be persisted."""
        with patch.object(analyst, "persist_findings", new_callable=AsyncMock) as mock_persist:
            async with execution_context(conversation_id="no-factory"):
                await analyst.invoke(state)  # Context but no session_factory

        mock_persist.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_persist_with_empty_findings(self, analyst, state):
        """When findings list is empty, persist should not be called."""
        mock_session = AsyncMock()

        with (
            patch.object(analyst, "extract_findings", return_value=[]),
            patch.object(analyst, "persist_findings", new_callable=AsyncMock) as mock_persist,
        ):
            await analyst.invoke(state, session=mock_session)

        mock_persist.assert_not_called()
