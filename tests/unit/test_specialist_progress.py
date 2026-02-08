"""Unit tests for specialist runner phase-level progress emission.

Tests that the _run_energy, _run_behavioral, _run_diagnostic runners
emit status progress events via the execution context.

TDD: Specialist runners emit phase-level progress.
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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

        with patch("src.tools.specialist_tools.is_agent_enabled", return_value=True), \
             patch("src.tools.specialist_tools.EnergyAnalyst") as MockAnalyst:
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
        assert len(status_events) >= 1, \
            f"Expected at least 1 status event, got {len(status_events)}: {[e.type for e in events]}"
        # Status should mention energy
        assert any("energy" in e.message.lower() for e in status_events), \
            f"Expected 'energy' in status messages: {[e.message for e in status_events]}"

    @pytest.mark.asyncio
    async def test_behavioral_runner_emits_status(self):
        """_run_behavioral should emit a status event before running."""
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()

        with patch("src.tools.specialist_tools.is_agent_enabled", return_value=True), \
             patch("src.tools.specialist_tools.BehavioralAnalyst") as MockAnalyst:
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

        with patch("src.tools.specialist_tools.is_agent_enabled", return_value=True), \
             patch("src.tools.specialist_tools.DiagnosticAnalyst") as MockAnalyst:
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
