"""Unit tests for A3: Wire report lifecycle into consult_data_science_team.

Tests that consult_data_science_team creates a report at start,
completes it after synthesis, and fails it on exception.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.execution_context import (
    ExecutionContext,
    clear_execution_context,
    set_execution_context,
)


@pytest.fixture(autouse=True)
def _clean_ctx():
    """Ensure execution context is clean before and after each test."""
    clear_execution_context()
    yield
    clear_execution_context()


def _make_session_factory():
    """Create a mock session factory returning an async context manager."""
    from contextlib import asynccontextmanager

    mock_session = AsyncMock()

    @asynccontextmanager
    async def factory():
        yield mock_session

    return factory, mock_session


class TestReportCreation:
    """consult_data_science_team creates a report at start."""

    @pytest.mark.asyncio
    async def test_creates_report_when_session_available(self):
        """A running report is created via create_analysis_report()."""
        factory, _mock_session = _make_session_factory()
        ctx = ExecutionContext(
            session_factory=factory,
            conversation_id="conv-123",
        )
        set_execution_context(ctx)

        mock_report = MagicMock()
        mock_report.id = "rpt-001"

        with (
            patch(
                "src.tools.ds_team_tool.create_analysis_report",
                new_callable=AsyncMock,
                return_value=mock_report,
            ) as mock_create,
            patch(
                "src.tools.ds_team_tool.complete_analysis_report",
                new_callable=AsyncMock,
            ),
            patch(
                "src.tools.ds_team_tool._select_specialists",
                return_value=["energy"],
            ),
            patch(
                "src.tools.ds_team_tool._run_parallel",
                new_callable=AsyncMock,
                return_value=["Energy results"],
            ),
            patch(
                "src.tools.ds_team_runners.is_agent_enabled",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke(
                {"query": "test energy", "depth": "deep", "strategy": "parallel"}
            )

        mock_create.assert_awaited_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs[1]["depth"] == "deep" or call_kwargs[0][2] == "deep"

    @pytest.mark.asyncio
    async def test_degrades_gracefully_without_session(self):
        """No report is created when there's no session factory."""
        ctx = ExecutionContext()
        set_execution_context(ctx)

        with (
            patch(
                "src.tools.ds_team_tool.create_analysis_report",
                new_callable=AsyncMock,
            ) as mock_create,
            patch(
                "src.tools.ds_team_tool._select_specialists",
                return_value=["energy"],
            ),
            patch(
                "src.tools.ds_team_tool._run_parallel",
                new_callable=AsyncMock,
                return_value=["Energy results"],
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            result = await consult_data_science_team.ainvoke({"query": "test energy"})

        # Should not have tried to create a report
        mock_create.assert_not_awaited()
        assert "Data Science Team Report" in result


class TestReportCompletion:
    """consult_data_science_team completes the report after synthesis."""

    @pytest.mark.asyncio
    async def test_completes_report_with_communication_log(self):
        factory, _mock_session = _make_session_factory()
        ctx = ExecutionContext(session_factory=factory)
        set_execution_context(ctx)

        mock_report = MagicMock()
        mock_report.id = "rpt-001"

        with (
            patch(
                "src.tools.ds_team_tool.create_analysis_report",
                new_callable=AsyncMock,
                return_value=mock_report,
            ),
            patch(
                "src.tools.ds_team_tool.complete_analysis_report",
                new_callable=AsyncMock,
            ) as mock_complete,
            patch(
                "src.tools.ds_team_tool._select_specialists",
                return_value=["energy"],
            ),
            patch(
                "src.tools.ds_team_tool._run_parallel",
                new_callable=AsyncMock,
                return_value=["Energy results"],
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke({"query": "test energy"})

        mock_complete.assert_awaited_once()
        call_kwargs = mock_complete.call_args
        assert call_kwargs[1]["report_id"] == "rpt-001"


class TestReportFailure:
    """consult_data_science_team marks report failed on exception."""

    @pytest.mark.asyncio
    async def test_fails_report_on_exception(self):
        factory, _mock_session = _make_session_factory()
        ctx = ExecutionContext(session_factory=factory)
        set_execution_context(ctx)

        mock_report = MagicMock()
        mock_report.id = "rpt-001"

        with (
            patch(
                "src.tools.ds_team_tool.create_analysis_report",
                new_callable=AsyncMock,
                return_value=mock_report,
            ),
            patch(
                "src.tools.ds_team_tool.fail_analysis_report",
                new_callable=AsyncMock,
            ) as mock_fail,
            patch(
                "src.tools.ds_team_tool._select_specialists",
                return_value=["energy"],
            ),
            patch(
                "src.tools.ds_team_tool._run_parallel",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ),
        ):
            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke({"query": "test energy"})

        mock_fail.assert_awaited_once()
        call_kwargs = mock_fail.call_args
        assert call_kwargs[1]["report_id"] == "rpt-001"
        assert "boom" in (call_kwargs[1].get("summary") or "")
