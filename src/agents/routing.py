"""Agent routing for the Orchestrator (Feature 30).

Resolves the ``agent`` field from a ChatCompletionRequest into a
concrete routing decision: which agent handles the request, which
workflow to use, and whether the Orchestrator needs to classify intent.

This module is intentionally free of I/O — it makes routing decisions
from the request parameters alone.  The Orchestrator's LLM-based
classification happens separately when ``needs_orchestrator`` is True.
"""

from __future__ import annotations

import logging
import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.storage.entities.agent import AgentName

if TYPE_CHECKING:
    from src.graph.state import ConversationState

KNOWN_AGENTS: frozenset[str] = frozenset(typing.get_args(AgentName))

DEFAULT_AGENT = "architect"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoutingDecision:
    """Result of resolving the ``agent`` field from a request."""

    active_agent: str
    workflow_agent: str
    channel: str = "api"
    # TODO(feat-30): When the Orchestrator is wired into the handler's
    # workflow selection, check this flag to run classify_intent() before
    # dispatching.  Currently "auto" defaults to architect.
    needs_orchestrator: bool = False


def resolve_agent_routing(
    agent: str,
    channel: str = "api",
) -> RoutingDecision:
    """Determine routing from the request's ``agent`` field.

    Args:
        agent: Value of the ``agent`` field ("auto" or a specific name).
        channel: Request channel ("api", "text", "voice").

    Returns:
        A RoutingDecision with the resolved agent and workflow.
    """
    if agent == "auto":
        return RoutingDecision(
            active_agent=DEFAULT_AGENT,
            workflow_agent=DEFAULT_AGENT,
            channel=channel,
            needs_orchestrator=True,
        )

    if agent not in KNOWN_AGENTS:
        logger.warning("Unknown agent %r requested, falling back to %s", agent, DEFAULT_AGENT)
        return RoutingDecision(
            active_agent=DEFAULT_AGENT,
            workflow_agent=DEFAULT_AGENT,
            channel=channel,
            needs_orchestrator=False,
        )

    return RoutingDecision(
        active_agent=agent,
        workflow_agent=agent,
        channel=channel,
        needs_orchestrator=False,
    )


def apply_routing_to_state(
    state: ConversationState,
    routing: RoutingDecision,
) -> None:
    """Apply a routing decision to a ConversationState (mutates in place).

    Args:
        state: The conversation state to update.
        routing: The resolved routing decision.
    """
    state.active_agent = routing.active_agent
    state.channel = routing.channel
