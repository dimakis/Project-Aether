"""Unit tests for A2: BaseAnalyst emit_communication() instrumentation.

Verifies that get_prior_findings(), add_finding(), and execute_script()
log communication entries to the execution context.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base_analyst import BaseAnalyst
from src.agents.execution_context import (
    ExecutionContext,
    clear_execution_context,
    set_execution_context,
)
from src.graph.state import AgentRole, AnalysisState, SpecialistFinding, TeamAnalysis

# ---------------------------------------------------------------------------
# Shared concrete subclass (satisfies all ABCs)
# ---------------------------------------------------------------------------


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
    """Create a FakeAnalyst without calling __init__ (no HA/LLM deps)."""
    analyst = _FakeAnalyst.__new__(_FakeAnalyst)
    analyst.ROLE = AgentRole.ENERGY_ANALYST
    analyst.NAME = "test_energy_analyst"
    return analyst


@pytest.fixture(autouse=True)
def _clean_ctx():
    """Ensure execution context is clean before and after each test."""
    clear_execution_context()
    yield
    clear_execution_context()


# ---------------------------------------------------------------------------
# get_prior_findings
# ---------------------------------------------------------------------------


class TestGetPriorFindingsCommunication:
    """get_prior_findings emits a cross_reference communication."""

    def test_emits_cross_reference_when_prior_findings_exist(self):
        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()
        finding = SpecialistFinding(
            specialist="behavioral_analyst",
            finding_type="insight",
            title="Test finding",
            description="Test",
            confidence=0.9,
        )
        ta = TeamAnalysis(
            request_id="test",
            request_summary="test",
            findings=[finding],
        )
        state = AnalysisState(team_analysis=ta)

        results = analyst.get_prior_findings(state)
        assert len(results) == 1

        # Check communication log
        assert len(ctx.communication_log) == 1
        entry = ctx.communication_log[0]
        assert entry["from_agent"] == "test_energy_analyst"
        assert entry["message_type"] == "cross_reference"
        assert "1" in entry["content"]  # mentions count

    def test_no_communication_when_no_prior_findings(self):
        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()
        ta = TeamAnalysis(request_id="test", request_summary="test")
        state = AnalysisState(team_analysis=ta)

        results = analyst.get_prior_findings(state)
        assert len(results) == 0
        assert len(ctx.communication_log) == 0


# ---------------------------------------------------------------------------
# add_finding
# ---------------------------------------------------------------------------


class TestAddFindingCommunication:
    """add_finding emits a finding communication."""

    def test_emits_finding_communication(self):
        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()
        state = AnalysisState()
        finding = SpecialistFinding(
            specialist="energy_analyst",
            finding_type="concern",
            title="High consumption",
            description="High consumption found in kitchen",
            confidence=0.85,
            entities=["sensor.kitchen_power"],
        )

        analyst.add_finding(state, finding)

        assert len(ctx.communication_log) == 1
        entry = ctx.communication_log[0]
        assert entry["from_agent"] == "test_energy_analyst"
        assert entry["to_agent"] == "team"
        assert entry["message_type"] == "finding"
        assert "High consumption" in entry["content"]
        assert entry["metadata"]["confidence"] == 0.85


# ---------------------------------------------------------------------------
# execute_script
# ---------------------------------------------------------------------------


class TestExecuteScriptCommunication:
    """execute_script emits status communications on start and completion."""

    @pytest.mark.asyncio
    async def test_emits_status_on_start_and_completion(self):
        from src.sandbox.runner import SandboxResult

        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()
        mock_result = SandboxResult(
            stdout="ok",
            stderr="",
            exit_code=0,
            success=True,
            duration_seconds=1.0,
            policy_name="test",
        )
        analyst._sandbox = MagicMock()
        analyst._sandbox.run = AsyncMock(return_value=mock_result)

        result = await analyst.execute_script("print('hello')", {"key": "value"})

        assert result.exit_code == 0
        assert len(ctx.communication_log) == 2

        start_entry = ctx.communication_log[0]
        assert start_entry["message_type"] == "status"
        assert (
            "start" in start_entry["content"].lower()
            or "executing" in start_entry["content"].lower()
        )

        end_entry = ctx.communication_log[1]
        assert end_entry["message_type"] == "status"
        assert end_entry["metadata"].get("exit_code") == 0

    @pytest.mark.asyncio
    async def test_emits_status_on_failure(self):
        from src.sandbox.runner import SandboxResult

        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()
        mock_result = SandboxResult(
            stdout="",
            stderr="error",
            exit_code=1,
            success=False,
            duration_seconds=0.5,
            policy_name="test",
        )
        analyst._sandbox = MagicMock()
        analyst._sandbox.run = AsyncMock(return_value=mock_result)

        result = await analyst.execute_script("print('hello')", {})

        assert result.exit_code == 1
        assert len(ctx.communication_log) == 2
        end_entry = ctx.communication_log[1]
        assert end_entry["metadata"]["exit_code"] == 1
