"""Unit tests for A4: Depth-aware sandbox policy in BaseAnalyst.execute_script().

Verifies that execute_script uses get_policy_for_depth() to build a
depth-appropriate sandbox policy and passes it to SandboxRunner.run().
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
from src.graph.state import AgentRole
from src.sandbox.runner import SandboxResult


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


def _make_sandbox_result(exit_code: int = 0) -> SandboxResult:
    return SandboxResult(
        stdout="ok",
        stderr="",
        exit_code=exit_code,
        success=exit_code == 0,
        duration_seconds=1.0,
        policy_name="test",
    )


@pytest.fixture(autouse=True)
def _clean_ctx():
    clear_execution_context()
    yield
    clear_execution_context()


class TestDepthPolicyWiring:
    """execute_script passes the depth-aware policy to the sandbox runner."""

    @pytest.mark.asyncio
    async def test_passes_deep_policy_to_sandbox(self):
        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()
        mock_result = _make_sandbox_result()
        analyst._sandbox = MagicMock()
        analyst._sandbox.run = AsyncMock(return_value=mock_result)

        mock_policy = MagicMock()
        with patch(
            "src.agents.base_analyst.get_policy_for_depth",
            return_value=mock_policy,
        ) as mock_gpfd:
            await analyst.execute_script("print('hi')", {}, depth="deep")

        mock_gpfd.assert_called_once()
        assert mock_gpfd.call_args[0][0] == "deep"
        # Policy should have been passed to sandbox.run
        analyst._sandbox.run.assert_awaited_once()
        call_kwargs = analyst._sandbox.run.call_args
        assert call_kwargs.kwargs.get("policy") is mock_policy

    @pytest.mark.asyncio
    async def test_passes_quick_policy_to_sandbox(self):
        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()
        mock_result = _make_sandbox_result()
        analyst._sandbox = MagicMock()
        analyst._sandbox.run = AsyncMock(return_value=mock_result)

        mock_policy = MagicMock()
        with patch(
            "src.agents.base_analyst.get_policy_for_depth",
            return_value=mock_policy,
        ) as mock_gpfd:
            await analyst.execute_script("print('hi')", {}, depth="quick")

        mock_gpfd.assert_called_once()
        assert mock_gpfd.call_args[0][0] == "quick"

    @pytest.mark.asyncio
    async def test_default_depth_uses_standard(self):
        """When no depth is provided, default 'standard' policy is used."""
        ctx = ExecutionContext()
        set_execution_context(ctx)

        analyst = _make_analyst()
        mock_result = _make_sandbox_result()
        analyst._sandbox = MagicMock()
        analyst._sandbox.run = AsyncMock(return_value=mock_result)

        mock_policy = MagicMock()
        with patch(
            "src.agents.base_analyst.get_policy_for_depth",
            return_value=mock_policy,
        ) as mock_gpfd:
            await analyst.execute_script("print('hi')", {})

        mock_gpfd.assert_called_once()
        assert mock_gpfd.call_args[0][0] == "standard"
