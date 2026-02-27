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

from src.agents.registry import AGENT_REGISTRY
from src.storage.entities.agent import AgentName

if TYPE_CHECKING:
    from src.graph.state import ConversationState

KNOWN_AGENTS: frozenset[str] = frozenset(typing.get_args(AgentName)) | frozenset(
    AGENT_REGISTRY.keys()
)

DEFAULT_AGENT = "architect"

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Result of resolving the ``agent`` field from a request."""

    active_agent: str
    workflow_agent: str
    channel: str = "api"
    needs_orchestrator: bool = False
    workflow_preset: str | None = None
    disabled_agents: tuple[str, ...] = ()


def resolve_agent_routing(
    agent: str,
    channel: str = "api",
    workflow_preset: str | None = None,
    disabled_agents: list[str] | None = None,
) -> RoutingDecision:
    """Determine routing from the request's ``agent`` field.

    Args:
        agent: Value of the ``agent`` field ("auto" or a specific name).
        channel: Request channel ("api", "text", "voice").
        workflow_preset: Optional workflow preset ID from the UI.
        disabled_agents: Agent names excluded from the workflow preset.

    Returns:
        A RoutingDecision with the resolved agent and workflow.
    """
    frozen_disabled = tuple(disabled_agents) if disabled_agents else ()

    if agent == "auto":
        return RoutingDecision(
            active_agent="orchestrator",
            workflow_agent="orchestrator",
            channel=channel,
            needs_orchestrator=True,
            workflow_preset=workflow_preset,
            disabled_agents=frozen_disabled,
        )

    if agent not in KNOWN_AGENTS:
        logger.warning("Unknown agent %r requested, falling back to %s", agent, DEFAULT_AGENT)
        return RoutingDecision(
            active_agent=DEFAULT_AGENT,
            workflow_agent=DEFAULT_AGENT,
            channel=channel,
            needs_orchestrator=False,
            workflow_preset=workflow_preset,
            disabled_agents=frozen_disabled,
        )

    return RoutingDecision(
        active_agent=agent,
        workflow_agent=agent,
        channel=channel,
        needs_orchestrator=False,
        workflow_preset=workflow_preset,
        disabled_agents=frozen_disabled,
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
    state.workflow_preset = routing.workflow_preset
    state.disabled_agents = list(routing.disabled_agents)
