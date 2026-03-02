"""Review workflow nodes for Smart Config Review (Feature 28).

These nodes handle the config review lifecycle:
resolve targets -> fetch configs -> gather context -> consult DS team ->
architect synthesize -> create review proposals.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import yaml

from src.storage.entities.automation_proposal import (
    AutomationProposal,
    ProposalStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.graph.state import ReviewState
    from src.ha.client import HAClient

logger = logging.getLogger(__name__)


async def resolve_targets_node(
    state: ReviewState,
    ha_client: HAClient | None = None,
) -> dict[str, Any]:
    """Resolve review targets to concrete entity IDs.

    Handles special values like 'all_automations', 'all_scripts', 'all_scenes'
    by querying HA for the full list. Individual entity IDs are passed through.

    Args:
        state: Current review state with targets
        ha_client: HA client for listing entities

    Returns:
        State updates with resolved target list
    """
    if not state.targets:
        return {"error": "No review targets specified"}

    resolved: list[str] = []
    batch_specifiers = {"all_automations", "all_scripts", "all_scenes"}

    for target in state.targets:
        if target in batch_specifiers:
            if ha_client is None:
                from src.ha import get_ha_client_async

                ha_client = await get_ha_client_async()

            if target == "all_automations":
                entities = await ha_client.list_entities(domain="automation")
                resolved.extend(e.get("entity_id", "") for e in entities if e.get("entity_id"))
            elif target == "all_scripts":
                entities = await ha_client.list_entities(domain="script")
                resolved.extend(e.get("entity_id", "") for e in entities if e.get("entity_id"))
            elif target == "all_scenes":
                entities = await ha_client.list_entities(domain="scene")
                resolved.extend(e.get("entity_id", "") for e in entities if e.get("entity_id"))
        else:
            resolved.append(target)

    if not resolved:
        return {"error": f"No entities found for targets: {state.targets}"}

    # Assign a session ID for batch reviews (>1 target)
    session_id = state.review_session_id
    if len(resolved) > 1 and not session_id:
        session_id = str(uuid4())

    return {"targets": resolved, "review_session_id": session_id}


async def fetch_configs_node(
    state: ReviewState,
    ha_client: HAClient | None = None,
) -> dict[str, Any]:
    """Fetch current YAML configs for each review target.

    Retrieves automation/script configurations from HA REST API.

    Args:
        state: Current review state with resolved targets
        ha_client: HA client for fetching configs

    Returns:
        State updates with entity_id -> YAML config mapping
    """
    if ha_client is None:
        from src.ha import get_ha_client_async

        ha_client = await get_ha_client_async()

    configs: dict[str, str] = {}

    for entity_id in state.targets:
        try:
            domain = entity_id.split(".")[0]
            # Extract the object_id (part after domain.)
            object_id = entity_id.split(".", 1)[1] if "." in entity_id else entity_id

            if domain in ("automation", "script"):
                config = await ha_client.get_automation_config(object_id)
                if config:
                    configs[entity_id] = yaml.dump(
                        config, default_flow_style=False, sort_keys=False
                    )
                else:
                    logger.warning("No config found for %s", entity_id)
            else:
                logger.warning("Unsupported domain for review: %s", domain)
        except Exception:
            logger.exception("Failed to fetch config for %s", entity_id)

    if not configs:
        return {"error": f"Could not fetch configs for any targets: {state.targets}"}

    return {"configs": configs}


async def gather_context_node(
    state: ReviewState,
    ha_client: HAClient | None = None,
) -> dict[str, Any]:
    """Gather entity context for DS team analysis.

    Collects all entities and registry data to give the DS team
    a comprehensive picture of the smart home environment.

    Args:
        state: Current review state
        ha_client: HA client for entity queries

    Returns:
        State updates with entity_context dict
    """
    if ha_client is None:
        from src.ha import get_ha_client_async

        ha_client = await get_ha_client_async()

    context: dict[str, Any] = {}

    try:
        entities = await ha_client.list_entities()
        context["entities"] = entities
    except Exception:
        logger.exception("Failed to list entities")
        context["entities"] = []

    # Include the configs being reviewed for reference
    context["configs_under_review"] = state.configs

    return {"entity_context": context}


async def create_review_proposals_node(
    state: ReviewState,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Create review proposals from architect suggestions.

    Each suggestion becomes an AutomationProposal with original_yaml set,
    enabling diff view in the UI.

    Args:
        state: Current review state with suggestions
        session: Database session for persisting proposals

    Returns:
        State updates (empty on success, error on failure)
    """
    if not state.suggestions:
        return {"error": "No suggestions to create proposals from"}

    if session is None:
        from src.storage import get_session

        async with get_session() as db_session:
            return await _create_proposals(state, db_session)

    return await _create_proposals(state, session)


async def _create_proposals(
    state: ReviewState,
    session: Any,
) -> dict[str, Any]:
    """Internal helper to create proposals within a session context."""
    proposal_ids: list[str] = []

    for suggestion in state.suggestions:
        entity_id = suggestion.get("entity_id", "unknown")
        original_yaml = state.configs.get(entity_id, "")

        proposal = AutomationProposal(
            id=str(uuid4()),
            name=suggestion.get("name", f"Review: {entity_id}"),
            description=suggestion.get("description", f"Smart review of {entity_id}"),
            trigger=suggestion.get("suggested_trigger", []),
            actions=suggestion.get("suggested_actions", []),
            conditions=suggestion.get("suggested_conditions"),
            mode=suggestion.get("mode", "single"),
            status=ProposalStatus.PROPOSED,
            proposal_type=_infer_proposal_type(entity_id),
            original_yaml=original_yaml,
            review_notes=suggestion.get("review_notes", []),
            review_session_id=state.review_session_id,
        )

        session.add(proposal)
        proposal_ids.append(proposal.id)

    await session.commit()

    logger.info(
        "Created %d review proposals (session=%s)",
        len(proposal_ids),
        state.review_session_id,
    )
    return {}


def _infer_proposal_type(entity_id: str) -> str:
    """Infer proposal type from entity_id domain."""
    domain = entity_id.split(".")[0] if "." in entity_id else "automation"
    type_map = {
        "automation": "automation",
        "script": "script",
        "scene": "scene",
    }
    return type_map.get(domain, "automation")
