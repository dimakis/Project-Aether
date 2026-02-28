"""Review workflow - smart config review pipeline.

Feature 28: Smart Config Review - reactive review of existing HA configs.
Constitution: Safety First - review suggestions go through HITL approval.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.ha.client import HAClient

from src.graph import END, START, StateGraph, create_graph
from src.graph.nodes import (
    create_review_proposals_node,
    fetch_configs_node,
    gather_context_node,
    resolve_targets_node,
)
from src.graph.state import ReviewState
from src.tracing import traced_node

logger = logging.getLogger(__name__)


def build_review_graph(
    ha_client: HAClient | None = None,
    session: AsyncSession | None = None,
) -> StateGraph:
    """Build the config review workflow graph.

    Graph structure:
    ```
    START
      |
      v
    resolve_targets
      |
      v
    fetch_configs
      |
      v
    gather_context
      |
      v
    consult_ds_team
      |
      v
    architect_synthesize
      |
      v
    create_review_proposals
      |
      v
    END
    ```

    Feature 28: Smart Config Review - reactive review of existing HA configs.
    Constitution: Safety First - review suggestions go through HITL approval.

    Args:
        ha_client: Optional HA client to inject
        session: Optional database session for proposal persistence

    Returns:
        Configured StateGraph
    """
    graph = create_graph(ReviewState)

    # Node wrappers with dependency injection
    async def _resolve_targets(state: ReviewState) -> dict:
        return await resolve_targets_node(state, ha_client=ha_client)

    async def _fetch_configs(state: ReviewState) -> dict:
        return await fetch_configs_node(state, ha_client=ha_client)

    async def _gather_context(state: ReviewState) -> dict:
        return await gather_context_node(state, ha_client=ha_client)

    async def _consult_ds_team(state: ReviewState) -> dict:
        """Consult DS team specialists for analysis findings."""
        from src.agents.behavioral_analyst import BehavioralAnalyst
        from src.agents.diagnostic_analyst import DiagnosticAnalyst
        from src.agents.energy_analyst import EnergyAnalyst

        findings: list[dict] = []
        analysts = [
            ("energy", EnergyAnalyst),
            ("behavioral", BehavioralAnalyst),
            ("diagnostic", DiagnosticAnalyst),
        ]

        # Filter analysts by focus if specified
        if state.focus:
            analysts = [(name, cls) for name, cls in analysts if name == state.focus]

        for name, analyst_cls in analysts:
            try:
                analyst = analyst_cls()
                result = await analyst.analyze_config(
                    configs=state.configs,
                    entity_context=state.entity_context,
                )
                findings.extend(result.get("findings", []))
            except Exception:
                logger.exception("DS team analyst '%s' failed", name)

        return {"ds_findings": findings}

    async def _architect_synthesize(state: ReviewState) -> dict:
        """Architect synthesizes DS findings into YAML suggestions."""
        from src.agents.architect import ArchitectAgent

        architect = ArchitectAgent()
        suggestions = await architect.synthesize_review(
            configs=state.configs,
            ds_findings=state.ds_findings,
            entity_context=state.entity_context,
            focus=state.focus,
        )
        return {"suggestions": suggestions}

    async def _create_proposals(state: ReviewState) -> dict:
        return await create_review_proposals_node(state, session=session)

    # Wire up nodes (traced for MLflow per-node spans)
    graph.add_node("resolve_targets", traced_node("resolve_targets", _resolve_targets))
    graph.add_node("fetch_configs", traced_node("fetch_configs", _fetch_configs))
    graph.add_node("gather_context", traced_node("gather_context", _gather_context))
    graph.add_node("consult_ds_team", traced_node("consult_ds_team", _consult_ds_team))
    graph.add_node(
        "architect_synthesize",
        traced_node("architect_synthesize", _architect_synthesize),
    )
    graph.add_node(
        "create_review_proposals",
        traced_node("create_review_proposals", _create_proposals),
    )

    # Linear flow
    graph.add_edge(START, "resolve_targets")
    graph.add_edge("resolve_targets", "fetch_configs")
    graph.add_edge("fetch_configs", "gather_context")
    graph.add_edge("gather_context", "consult_ds_team")
    graph.add_edge("consult_ds_team", "architect_synthesize")
    graph.add_edge("architect_synthesize", "create_review_proposals")
    graph.add_edge("create_review_proposals", END)

    return graph
