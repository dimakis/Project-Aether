"""Proposal extraction, creation, and YAML conversion utilities."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.storage.entities import AutomationProposal

from src.dal import ProposalRepository

logger = logging.getLogger(__name__)


def extract_proposal(response: str) -> dict[str, Any] | None:
    """Extract the first proposal JSON from response if present.

    Args:
        response: LLM response text

    Returns:
        Proposal dict or None
    """
    proposals = extract_proposals(response)
    return proposals[0] if proposals else None


def extract_proposals(response: str) -> list[dict[str, Any]]:
    """Extract all proposal JSON blocks from response.

    Uses ``re.finditer`` to find ALL ```json code blocks, then
    attempts to parse each as JSON containing a ``"proposal"`` key.

    The regex uses ``(.*?)`` (not ``\\{.*?\\}``) to prevent a
    truncated JSON block from consuming the *next* block when
    ``re.DOTALL`` causes ``.*?`` to cross ````` boundaries.

    Args:
        response: LLM response text

    Returns:
        List of proposal dicts (may be empty)
    """
    proposals: list[dict[str, Any]] = []
    for block_match in re.finditer(r"```json\s*(.*?)\s*```", response, re.DOTALL):
        raw = block_match.group(1).strip()
        if not raw.startswith("{"):
            continue
        try:
            data = json.loads(raw)
            if "proposal" in data and isinstance(data["proposal"], dict):
                proposals.append(data["proposal"])
        except json.JSONDecodeError:
            continue
    return proposals


async def create_proposal(
    session: AsyncSession,
    conversation_id: str,
    proposal_data: dict[str, Any],
) -> AutomationProposal:
    """Create an automation proposal from parsed data.

    Args:
        session: Database session
        conversation_id: Source conversation
        proposal_data: Parsed proposal data

    Returns:
        Created proposal
    """
    repo = ProposalRepository(session)

    proposal = await repo.create(
        name=proposal_data.get("name", "Untitled Automation"),
        trigger=proposal_data.get("trigger", []),
        actions=proposal_data.get("actions", []),
        conversation_id=conversation_id,
        description=proposal_data.get("description"),
        conditions=proposal_data.get("conditions"),
        mode=proposal_data.get("mode", "single"),
        proposal_type=proposal_data.get("proposal_type", "automation"),
    )

    # Submit for approval
    await repo.propose(proposal.id)

    return proposal


def proposal_to_yaml(proposal_data: dict[str, Any]) -> str:
    """Convert proposal to YAML string for display.

    Supports automation, script, and scene proposal types.

    Args:
        proposal_data: Proposal data dict

    Returns:
        YAML string
    """
    import yaml

    proposal_type = proposal_data.get("proposal_type", "automation")

    if proposal_type == "script":
        # HA script format: alias, sequence, mode
        script = {
            "alias": proposal_data.get("name"),
            "description": proposal_data.get("description", ""),
            "sequence": proposal_data.get("actions", []),
            "mode": proposal_data.get("mode", "single"),
        }
        return yaml.dump(script, default_flow_style=False, sort_keys=False)

    if proposal_type == "scene":
        # HA scene format: name, entities
        entities = {}
        for action in proposal_data.get("actions", []):
            entity_id = action.get("entity_id")
            if entity_id:
                entity_state = {k: v for k, v in action.items() if k != "entity_id"}
                entities[entity_id] = entity_state
        scene = {
            "name": proposal_data.get("name"),
            "entities": entities,
        }
        return yaml.dump(scene, default_flow_style=False, sort_keys=False)

    # Default: automation format
    automation = {
        "alias": proposal_data.get("name"),
        "description": proposal_data.get("description", ""),
        "trigger": proposal_data.get("trigger", []),
        "action": proposal_data.get("actions", []),
        "mode": proposal_data.get("mode", "single"),
    }

    if proposal_data.get("conditions"):
        automation["condition"] = proposal_data["conditions"]

    return yaml.dump(automation, default_flow_style=False, sort_keys=False)
