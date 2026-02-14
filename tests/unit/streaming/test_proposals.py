"""Unit tests for ProposalTracker.

Tests fallback content generation and inline proposal extraction from
the tail of stream_conversation.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestGenerateFallback:
    """Tests for generate_fallback_events()."""

    def test_proposal_summaries_emitted_when_no_content(self):
        from src.agents.streaming.proposals import generate_fallback_events

        events = list(
            generate_fallback_events(
                collected_content="",
                proposal_summaries=["Proposal submitted: Night Lock"],
                iteration=1,
            )
        )
        assert len(events) == 1
        assert events[0]["type"] == "token"
        assert "Night Lock" in events[0]["content"]

    def test_multiple_proposals_joined(self):
        from src.agents.streaming.proposals import generate_fallback_events

        events = list(
            generate_fallback_events(
                collected_content="",
                proposal_summaries=["Proposal A", "Proposal B"],
                iteration=1,
            )
        )
        assert len(events) == 1
        assert "Proposal A" in events[0]["content"]
        assert "Proposal B" in events[0]["content"]

    def test_generic_fallback_when_no_proposals_no_content(self):
        from src.agents.streaming.proposals import generate_fallback_events

        events = list(
            generate_fallback_events(
                collected_content="",
                proposal_summaries=[],
                iteration=1,
            )
        )
        assert len(events) == 1
        assert (
            "try rephrasing" in events[0]["content"].lower()
            or "processed" in events[0]["content"].lower()
        )

    def test_no_fallback_when_content_present(self):
        from src.agents.streaming.proposals import generate_fallback_events

        events = list(
            generate_fallback_events(
                collected_content="Here is the response.",
                proposal_summaries=[],
                iteration=1,
            )
        )
        assert len(events) == 0

    def test_no_fallback_when_no_iteration(self):
        from src.agents.streaming.proposals import generate_fallback_events

        events = list(
            generate_fallback_events(
                collected_content="",
                proposal_summaries=[],
                iteration=0,
            )
        )
        assert len(events) == 0


class TestExtractInlineProposals:
    """Tests for extract_inline_proposals()."""

    @pytest.mark.asyncio
    async def test_extracts_inline_proposals(self):
        from src.agents.streaming.proposals import extract_inline_proposals

        mock_agent = MagicMock()
        mock_agent._extract_proposals.return_value = [
            {"name": "Sunset Lights", "trigger": [], "actions": []}
        ]
        mock_proposal = MagicMock()
        mock_proposal.id = "p-123"
        mock_agent._create_proposal = AsyncMock(return_value=mock_proposal)

        mock_session = MagicMock()

        await extract_inline_proposals(
            agent=mock_agent,
            session=mock_session,
            conversation_id="conv-1",
            collected_content='```json\n{"proposal": {"name": "Sunset Lights"}}\n```',
            proposal_summaries=[],
        )

        mock_agent._extract_proposals.assert_called_once()
        mock_agent._create_proposal.assert_called_once_with(
            mock_session,
            "conv-1",
            {"name": "Sunset Lights", "trigger": [], "actions": []},
        )

    @pytest.mark.asyncio
    async def test_skipped_when_proposals_already_exist(self):
        from src.agents.streaming.proposals import extract_inline_proposals

        mock_agent = MagicMock()
        mock_session = MagicMock()

        await extract_inline_proposals(
            agent=mock_agent,
            session=mock_session,
            conversation_id="conv-1",
            collected_content="some content",
            proposal_summaries=["already has proposals"],
        )

        mock_agent._extract_proposals.assert_not_called()

    @pytest.mark.asyncio
    async def test_skipped_when_no_session(self):
        from src.agents.streaming.proposals import extract_inline_proposals

        mock_agent = MagicMock()

        await extract_inline_proposals(
            agent=mock_agent,
            session=None,
            conversation_id="conv-1",
            collected_content="some content",
            proposal_summaries=[],
        )

        mock_agent._extract_proposals.assert_not_called()

    @pytest.mark.asyncio
    async def test_skipped_when_no_content(self):
        from src.agents.streaming.proposals import extract_inline_proposals

        mock_agent = MagicMock()
        mock_session = MagicMock()

        await extract_inline_proposals(
            agent=mock_agent,
            session=mock_session,
            conversation_id="conv-1",
            collected_content="",
            proposal_summaries=[],
        )

        mock_agent._extract_proposals.assert_not_called()

    @pytest.mark.asyncio
    async def test_creation_failure_logged_not_raised(self):
        from src.agents.streaming.proposals import extract_inline_proposals

        mock_agent = MagicMock()
        mock_agent._extract_proposals.return_value = [{"name": "Bad", "trigger": [], "actions": []}]
        mock_agent._create_proposal = AsyncMock(side_effect=ValueError("DB error"))

        mock_session = MagicMock()

        # Should not raise
        await extract_inline_proposals(
            agent=mock_agent,
            session=mock_session,
            conversation_id="conv-1",
            collected_content="some content",
            proposal_summaries=[],
        )
