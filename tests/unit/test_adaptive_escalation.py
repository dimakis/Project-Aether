"""Unit tests for B2: Adaptive strategy escalation on conflict detection.

Verifies that consult_data_science_team auto-escalates from parallel
to teamwork when conflicts are detected and depth is not quick.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.execution_context import (
    ExecutionContext,
    clear_execution_context,
    set_execution_context,
)
from src.graph.state import SpecialistFinding, TeamAnalysis


@pytest.fixture(autouse=True)
def _clean_ctx():
    clear_execution_context()
    yield
    clear_execution_context()


class TestAdaptiveEscalation:
    """Parallel mode escalates to teamwork when conflicts exist."""

    @pytest.mark.asyncio
    async def test_escalates_on_conflicts(self):
        """When parallel synthesis finds conflicts, escalation runs a discussion."""
        ctx = ExecutionContext()
        set_execution_context(ctx)

        # After parallel run, synthesizer produces conflicts
        ta_with_conflicts = TeamAnalysis(
            request_id="test",
            request_summary="test query",
            findings=[
                SpecialistFinding(
                    specialist="energy_analyst",
                    finding_type="insight",
                    title="Low energy",
                    description="Energy is low",
                    confidence=0.8,
                ),
                SpecialistFinding(
                    specialist="behavioral_analyst",
                    finding_type="concern",
                    title="High energy",
                    description="Energy is high from behavior",
                    confidence=0.7,
                ),
            ],
            conflicts=["Energy assessment contradicts behavioral assessment"],
        )

        # _run_parallel mock sets team_analysis (simulating what runners do)
        async def mock_run_parallel(selected, runners, query, hours, entity_ids, depth):
            ctx.team_analysis = ta_with_conflicts
            return ["Energy results", "Behavioral results"]

        with (
            patch(
                "src.tools.specialist_tools._select_specialists",
                return_value=["energy", "behavioral"],
            ),
            patch(
                "src.tools.specialist_tools._run_parallel",
                side_effect=mock_run_parallel,
            ),
            patch(
                "src.tools.specialist_tools.ProgrammaticSynthesizer",
            ) as mock_synth_cls,
            patch(
                "src.tools.specialist_tools._run_discussion_round",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_discussion,
        ):
            # Synthesizer returns the TA with conflicts
            mock_synth = MagicMock()
            mock_synth.synthesize.return_value = ta_with_conflicts
            mock_synth_cls.return_value = mock_synth

            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke(
                {"query": "test energy", "depth": "standard", "strategy": "parallel"}
            )

        # Discussion round should have been called as escalation
        mock_discussion.assert_awaited_once()
        # Communication log should contain the escalation status message
        escalation_msgs = [
            e for e in ctx.communication_log if "escalat" in e.get("content", "").lower()
        ]
        assert len(escalation_msgs) >= 1

    @pytest.mark.asyncio
    async def test_no_escalation_on_quick_depth(self):
        """Quick depth never escalates, even with conflicts."""
        ctx = ExecutionContext()
        set_execution_context(ctx)

        ta_with_conflicts = TeamAnalysis(
            request_id="test",
            request_summary="test query",
            findings=[
                SpecialistFinding(
                    specialist="energy_analyst",
                    finding_type="insight",
                    title="Low energy",
                    description="Energy is low",
                    confidence=0.8,
                ),
            ],
            conflicts=["Some conflict"],
        )

        async def mock_run_parallel(selected, runners, query, hours, entity_ids, depth):
            ctx.team_analysis = ta_with_conflicts
            return ["Energy results"]

        with (
            patch(
                "src.tools.specialist_tools._select_specialists",
                return_value=["energy"],
            ),
            patch(
                "src.tools.specialist_tools._run_parallel",
                side_effect=mock_run_parallel,
            ),
            patch(
                "src.tools.specialist_tools.ProgrammaticSynthesizer",
            ) as mock_synth_cls,
            patch(
                "src.tools.specialist_tools._run_discussion_round",
                new_callable=AsyncMock,
            ) as mock_discussion,
        ):
            mock_synth = MagicMock()
            mock_synth.synthesize.return_value = ta_with_conflicts
            mock_synth_cls.return_value = mock_synth

            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke(
                {"query": "test energy", "depth": "quick", "strategy": "parallel"}
            )

        # No escalation for quick depth
        mock_discussion.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_escalation_without_conflicts(self):
        """No conflicts = no escalation."""
        ctx = ExecutionContext()
        set_execution_context(ctx)

        ta_no_conflicts = TeamAnalysis(
            request_id="test",
            request_summary="test query",
            findings=[
                SpecialistFinding(
                    specialist="energy_analyst",
                    finding_type="insight",
                    title="Normal energy",
                    description="Energy is normal",
                    confidence=0.9,
                ),
            ],
            conflicts=[],
        )

        async def mock_run_parallel(selected, runners, query, hours, entity_ids, depth):
            ctx.team_analysis = ta_no_conflicts
            return ["Energy results"]

        with (
            patch(
                "src.tools.specialist_tools._select_specialists",
                return_value=["energy"],
            ),
            patch(
                "src.tools.specialist_tools._run_parallel",
                side_effect=mock_run_parallel,
            ),
            patch(
                "src.tools.specialist_tools._run_discussion_round",
                new_callable=AsyncMock,
            ) as mock_discussion,
        ):
            from src.tools.specialist_tools import consult_data_science_team

            await consult_data_science_team.ainvoke(
                {"query": "test energy", "depth": "standard", "strategy": "parallel"}
            )

        mock_discussion.assert_not_awaited()
