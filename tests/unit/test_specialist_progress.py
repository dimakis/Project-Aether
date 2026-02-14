"""Unit tests for specialist runner phase-level progress emission.

Tests that the _run_energy, _run_behavioral, _run_diagnostic runners
emit status progress events via the execution context, and that
consult_data_science_team emits delegation events.

TDD: Specialist runners emit phase-level progress + delegation events.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.execution_context import (
    ProgressEvent,
    execution_context,
)


class TestSpecialistProgress:
    """Tests for emit_progress calls in specialist runners."""

    @pytest.mark.asyncio
    async def test_energy_runner_emits_status(self):
        """_run_energy should emit a status event before running."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.EnergyAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import _run_energy

            async with execution_context(progress_queue=queue):
                await _run_energy("test query", 24, ["sensor.test"])

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        # Should have at least one status event from the runner
        status_events = [e for e in events if e.type == "status"]
        assert len(status_events) >= 1, (
            f"Expected at least 1 status event, got {len(status_events)}: {[e.type for e in events]}"
        )
        # Status should mention energy
        assert any("energy" in e.message.lower() for e in status_events), (
            f"Expected 'energy' in status messages: {[e.message for e in status_events]}"
        )


class TestSpecialistLifecycleEvents:
    """Tests that specialist runners emit agent_start/agent_end events."""

    @pytest.mark.asyncio
    async def test_energy_runner_emits_lifecycle_events(self):
        """_run_energy should emit agent_start and agent_end for energy_analyst."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.EnergyAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import _run_energy

            async with execution_context(progress_queue=queue):
                await _run_energy("test query", 24, None)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        types = [e.type for e in events]
        [e.agent for e in events]

        assert "agent_start" in types, f"Expected agent_start, got types: {types}"
        assert "agent_end" in types, f"Expected agent_end, got types: {types}"

        start_idx = types.index("agent_start")
        end_idx = types.index("agent_end")
        assert events[start_idx].agent == "energy_analyst"
        assert events[end_idx].agent == "energy_analyst"
        assert start_idx < end_idx, "agent_start should come before agent_end"

    @pytest.mark.asyncio
    async def test_energy_runner_emits_agent_end_on_failure(self):
        """agent_end should still fire even if the analyst raises."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.EnergyAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.side_effect = RuntimeError("boom")
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import _run_energy

            async with execution_context(progress_queue=queue):
                await _run_energy("test query", 24, None)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        types = [e.type for e in events]
        # agent_end should fire even on failure (via try/finally)
        assert "agent_end" in types, f"Expected agent_end on failure, got: {types}"

    @pytest.mark.asyncio
    async def test_behavioral_runner_emits_lifecycle_events(self):
        """_run_behavioral should emit agent_start/agent_end."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.BehavioralAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import _run_behavioral

            async with execution_context(progress_queue=queue):
                await _run_behavioral("test query", 24, None)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        types = [e.type for e in events]
        assert "agent_start" in types
        assert "agent_end" in types

    @pytest.mark.asyncio
    async def test_diagnostic_runner_emits_lifecycle_events(self):
        """_run_diagnostic should emit agent_start/agent_end."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.DiagnosticAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import _run_diagnostic

            async with execution_context(progress_queue=queue):
                await _run_diagnostic("test query", 24, None)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        types = [e.type for e in events]
        assert "agent_start" in types
        assert "agent_end" in types

    @pytest.mark.asyncio
    async def test_behavioral_runner_emits_status(self):
        """_run_behavioral should emit a status event before running."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.BehavioralAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import _run_behavioral

            async with execution_context(progress_queue=queue):
                await _run_behavioral("test query", 24, ["sensor.test"])

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        status_events = [e for e in events if e.type == "status"]
        assert len(status_events) >= 1
        assert any("behavioral" in e.message.lower() for e in status_events)

    @pytest.mark.asyncio
    async def test_diagnostic_runner_emits_status(self):
        """_run_diagnostic should emit a status event before running."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.DiagnosticAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import _run_diagnostic

            async with execution_context(progress_queue=queue):
                await _run_diagnostic("test query", 24, ["sensor.test"])

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        status_events = [e for e in events if e.type == "status"]
        assert len(status_events) >= 1
        assert any("diagnostic" in e.message.lower() for e in status_events)


class TestDelegationEvents:
    """Tests that consult_data_science_team emits delegation events."""

    @pytest.mark.asyncio
    async def test_consult_emits_delegation_to_ds_team(self):
        """consult_data_science_team should emit a delegation from architect to DS team."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.EnergyAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import consult_data_science_team

            async with execution_context(progress_queue=queue):
                await consult_data_science_team.ainvoke(
                    {"query": "test query", "hours": 24, "specialists": ["energy"]}
                )

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        delegation_events = [e for e in events if e.type == "delegation"]
        assert len(delegation_events) >= 2, (
            f"Expected at least 2 delegation events, got {len(delegation_events)}: {[(e.agent, e.target) for e in delegation_events]}"
        )

        # First delegation: architect -> data_science_team
        first = delegation_events[0]
        assert first.agent == "architect"
        assert first.target == "data_science_team"

        # Last delegation: data_science_team -> architect (report)
        last = delegation_events[-1]
        assert last.agent == "data_science_team"
        assert last.target == "architect"

    @pytest.mark.asyncio
    async def test_consult_emits_analyst_conclusion_delegation(self):
        """Each analyst's findings should be emitted as a delegation back to DS team."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.EnergyAnalyst") as MockEnergy,
            patch("src.tools.ds_team_runners.BehavioralAnalyst") as MockBehavioral,
        ):
            for MockAnalyst in [MockEnergy, MockBehavioral]:
                mock_instance = AsyncMock()
                mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
                MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import consult_data_science_team

            async with execution_context(progress_queue=queue):
                await consult_data_science_team.ainvoke(
                    {"query": "test query", "hours": 24, "specialists": ["energy", "behavioral"]}
                )

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        delegation_events = [e for e in events if e.type == "delegation"]
        # architect -> ds_team, energy -> ds_team, behavioral -> ds_team, ds_team -> architect
        analyst_delegations = [
            e
            for e in delegation_events
            if e.target == "data_science_team" and e.agent != "architect"
        ]
        assert len(analyst_delegations) >= 2, (
            f"Expected analyst->ds_team delegations, got: {[(e.agent, e.target) for e in delegation_events]}"
        )


class TestTeamAnalysisIsolation:
    """Tests that team analysis state uses ExecutionContext, not globals."""

    @pytest.mark.asyncio
    async def test_team_analysis_stored_in_context_not_global(self):
        """_get_or_create_team_analysis should use ExecutionContext.team_analysis."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with (
            patch("src.tools.ds_team_runners.is_agent_enabled", return_value=True),
            patch("src.tools.ds_team_runners.EnergyAnalyst") as MockAnalyst,
        ):
            mock_instance = AsyncMock()
            mock_instance.invoke.return_value = {"insights": [], "team_analysis": None}
            MockAnalyst.return_value = mock_instance

            from src.tools.specialist_tools import _get_or_create_team_analysis

            async with execution_context(progress_queue=queue) as ctx:
                ta = _get_or_create_team_analysis("test query")
                assert ctx.team_analysis is ta, (
                    "team_analysis should be stored in the ExecutionContext"
                )

    @pytest.mark.asyncio
    async def test_concurrent_contexts_are_isolated(self):
        """Two concurrent execution contexts should have independent team_analysis."""
        queue1: asyncio.Queue[ProgressEvent] = asyncio.Queue()
        queue2: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        from src.tools.specialist_tools import _get_or_create_team_analysis

        results = {}

        async def run_in_context(name: str, queue: asyncio.Queue) -> None:
            async with execution_context(progress_queue=queue) as ctx:
                ta = _get_or_create_team_analysis(f"query for {name}")
                results[name] = ta
                # Verify the context's team_analysis is ours
                assert ctx.team_analysis is ta

        await asyncio.gather(
            run_in_context("ctx1", queue1),
            run_in_context("ctx2", queue2),
        )

        # Each context should have created its own TeamAnalysis
        assert results["ctx1"] is not results["ctx2"], (
            "Concurrent contexts should have independent TeamAnalysis instances"
        )
