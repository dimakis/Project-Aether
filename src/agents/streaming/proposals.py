"""Proposal tracking — fallback content and inline proposal extraction.

Extracts the proposal-related logic from the tail of stream_conversation:
- Fallback content when no visible text was streamed but proposals exist
- Generic fallback when tools ran but produced no output
- Inline proposal extraction when the LLM writes proposals as ```json blocks
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.agents.streaming.events import StreamEvent

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def generate_fallback_events(
    *,
    collected_content: str,
    proposal_summaries: list[str],
    iteration: int,
) -> Generator[StreamEvent, None, None]:
    """Generate fallback token events when no content was streamed.

    Three cases:
    1. Proposals exist but no text → emit proposal summaries
    2. Tools ran (iteration > 0) but no proposals and no text → generic fallback
    3. Content exists or no iterations → no fallback needed

    Args:
        collected_content: Accumulated text content from the stream.
        proposal_summaries: Successful seek_approval result strings.
        iteration: Number of tool loop iterations completed.

    Yields:
        StreamEvent(type="token") fallback events (0 or 1).
    """
    if collected_content:
        return

    if proposal_summaries:
        fallback = "\n\n---\n\n".join(proposal_summaries)
        yield StreamEvent(type="token", content=fallback)
    elif iteration > 0:
        fallback = (
            "I processed your request using several tools but wasn't able to "
            "generate a complete response. Please try rephrasing or breaking "
            "your request into smaller steps."
        )
        yield StreamEvent(type="token", content=fallback)


async def extract_inline_proposals(
    *,
    agent: Any,
    session: AsyncSession | None,
    conversation_id: str,
    collected_content: str,
    proposal_summaries: list[str],
) -> None:
    """Extract and persist inline proposals from streamed content.

    When the LLM writes proposals as ```json blocks instead of using
    seek_approval, and no proposals were already created via tools,
    extract and persist them.

    Args:
        agent: ArchitectAgent instance with _extract_proposals and _create_proposal.
        session: Database session (None → skip).
        conversation_id: Conversation ID for proposal creation.
        collected_content: Full accumulated text content.
        proposal_summaries: Already-tracked proposal summaries (non-empty → skip).
    """
    if not session or not collected_content or proposal_summaries:
        return

    inline_proposals = agent._extract_proposals(collected_content)
    for prop_data in inline_proposals:
        try:
            proposal = await agent._create_proposal(
                session,
                conversation_id,
                prop_data,
            )
            logger.info(
                "Created inline proposal %s from streamed content",
                proposal.id,
            )
        except Exception as e:
            logger.warning("Failed to create inline proposal: %s", e)
