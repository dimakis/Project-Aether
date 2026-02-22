"""A2A Agent Card endpoint (Feature 30).

Serves a JSON Agent Card at ``/.well-known/agent.json`` per the A2A
protocol specification.  In monolith mode this is a single card that
aggregates all routable agents as skills.  When agents are extracted
to separate services, each service will serve its own card.

Spec: https://google.github.io/A2A/specification/agent-card/
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

if TYPE_CHECKING:
    from src.storage.entities.agent import Agent

logger = logging.getLogger(__name__)

router = APIRouter()

_CARD_URL = "/api/v1/chat/completions"


@router.get("/.well-known/agent.json")
async def get_agent_card() -> dict[str, Any]:
    """Return the A2A Agent Card for this Aether instance.

    The card describes the instance as a single A2A agent with
    multiple skills — one per routable domain agent.
    """
    agents = await _fetch_routable_agents()

    skills = [
        {
            "id": a.name,
            "name": a.name.replace("_", " ").title(),
            "description": a.description,
            "inputModes": ["text"],
            "outputModes": ["text"],
        }
        for a in agents
    ]

    return {
        "name": "Aether",
        "description": "Multi-domain AI home assistant with intent routing",
        "url": _CARD_URL,
        "version": "0.3.0",
        "skills": skills,
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    }


async def _fetch_routable_agents() -> list[Agent]:
    """Fetch routable agents from the database.

    Returns an empty list if the DB is unavailable (best-effort).
    """
    try:
        from src.dal.agents import AgentRepository
        from src.storage import get_session

        async with get_session() as session:
            repo = AgentRepository(session)
            all_agents = await repo.list_all()
            return [a for a in all_agents if a.is_routable and a.status != "disabled"]
    except Exception:
        logger.warning("Failed to fetch agents for Agent Card", exc_info=True)
        return []
