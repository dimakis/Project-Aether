"""Unit tests for B1: Discussion round in teamwork mode.

Verifies:
- BaseAnalyst.discuss() sends a discussion prompt and returns CommunicationEntry list
- _run_teamwork appends a discussion round when findings exist
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base_analyst import BaseAnalyst
from src.agents.execution_context import (
    ExecutionContext,
    clear_execution_context,
    set_execution_context,
)
from src.graph.state import (
    AgentRole,
    CommunicationEntry,
    SpecialistFinding,
    TeamAnalysis,
)


class _FakeAnalyst(BaseAnalyst):
    ROLE = AgentRole.ENERGY_ANALYST
    NAME = "test_energy_analyst"

    async def collect_data(self, state):
        return {}

    async def generate_script(self, state, data):
        return ""

    def extract_findings(self, result, state):
        return []

    async def invoke(self, state, **kwargs):
        return {}


def _make_analyst() -> _FakeAnalyst:
    analyst = _FakeAnalyst.__new__(_FakeAnalyst)
    analyst.ROLE = AgentRole.ENERGY_ANALYST
    analyst.NAME = "test_energy_analyst"
    return analyst


@pytest.fixture(autouse=True)
def _clean_ctx():
    clear_execution_context()
    yield
    clear_execution_context()


class TestBaseAnalystDiscuss:
    """BaseAnalyst.discuss() produces CommunicationEntry objects."""

    @pytest.mark.asyncio
    async def test_discuss_returns_communication_entries(self):
        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()

        # Mock the LLM to return a discussion response
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = (
            '{"cross_references": ["Energy spike correlates with HVAC pattern"], '
            '"agreements": ["High consumption confirmed"], '
            '"disagreements": []}'
        )
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        analyst._llm = mock_llm

        findings_summary = (
            "Energy Analyst: High consumption in kitchen\n"
            "Behavioral Analyst: Manual HVAC overrides detected"
        )

        entries = await analyst.discuss(findings_summary)

        assert isinstance(entries, list)
        assert len(entries) >= 1
        for entry in entries:
            assert isinstance(entry, CommunicationEntry)
            assert entry.from_agent == "test_energy_analyst"
            assert entry.message_type == "discussion"

    @pytest.mark.asyncio
    async def test_discuss_handles_llm_error_gracefully(self):
        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))
        analyst._llm = mock_llm

        entries = await analyst.discuss("test summary")

        # Should return empty on error, not raise
        assert entries == []


class TestTeamworkDiscussionRound:
    """_run_teamwork runs a discussion round after specialists complete."""

    @pytest.mark.asyncio
    async def test_discussion_round_called_when_findings_exist(self):
        ctx = ExecutionContext()
        set_execution_context(ctx)

        # Set up team analysis with findings
        ta = TeamAnalysis(
            request_id="test",
            request_summary="test query",
            findings=[
                SpecialistFinding(
                    specialist="energy_analyst",
                    finding_type="insight",
                    title="High energy",
                    description="High energy use",
                    confidence=0.9,
                ),
            ],
        )
        ctx.team_analysis = ta

        # Mock runners that succeed
        async def mock_runner(query, hours, entity_ids, *, depth="standard"):
            return "Found 1 insight(s)"

        runners = {
            "energy": mock_runner,
            "behavioral": mock_runner,
        }

        with patch(
            "src.tools.specialist_tools._run_discussion_round",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_disc:
            from src.tools.specialist_tools import _run_teamwork

            await _run_teamwork(
                ["energy", "behavioral"],
                runners,
                "test query",
                24,
                None,
                "deep",
            )

        mock_disc.assert_awaited_once()
