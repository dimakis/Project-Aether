"""Workflow composer for dynamic orchestration (Feature 30).

Bridges the Orchestrator's ``plan_response()`` with the
``WorkflowCompiler``.  When the Orchestrator decides a task
requires multi-step coordination, it produces a
``WorkflowDefinition`` which the composer validates, compiles,
and optionally persists for future reuse.
"""

from __future__ import annotations

import logging
from typing import Any

from src.graph.workflows.compiler import CompilationError, WorkflowCompiler
from src.graph.workflows.definition import (
    EdgeDefinition,
    NodeDefinition,
    WorkflowDefinition,
)
from src.graph.workflows.manifest import get_default_manifest

logger = logging.getLogger(__name__)


def compose_workflow(definition: WorkflowDefinition) -> Any:
    """Validate and compile a WorkflowDefinition into a runnable StateGraph.

    Args:
        definition: The declarative workflow specification.

    Returns:
        A compiled LangGraph StateGraph.

    Raises:
        CompilationError: If validation or compilation fails.
    """
    manifest = get_default_manifest()
    compiler = WorkflowCompiler(manifest)

    errors = compiler.validate(definition)
    if errors:
        logger.warning("Workflow validation failed: %s", errors)
        raise CompilationError(errors)

    graph = compiler.compile(definition)
    logger.info(
        "Compiled workflow '%s' with %d nodes, %d edges",
        definition.name,
        len(definition.nodes),
        len(definition.edges) + len(definition.conditional_edges),
    )
    return graph


def build_sequential_workflow(
    name: str,
    description: str,
    steps: list[dict[str, str]],
    state_type: str = "ConversationState",
) -> WorkflowDefinition:
    """Build a simple linear workflow from a list of step descriptions.

    Each step is a dict with ``id`` and ``function`` (matching a node
    in the manifest).  Steps are connected sequentially: START -> s1 -> s2 -> ... -> END.

    Args:
        name: Workflow name.
        description: Human-readable workflow description.
        steps: List of dicts with 'id' and 'function' keys.
        state_type: The state class name (default: ConversationState).

    Returns:
        A WorkflowDefinition ready for compilation.
    """
    nodes = [
        NodeDefinition(
            id=step["id"],
            function=step["function"],
            description=step.get("description", ""),
        )
        for step in steps
    ]

    edges: list[EdgeDefinition] = []
    if nodes:
        edges.append(EdgeDefinition(source="__start__", target=nodes[0].id))
        for i in range(len(nodes) - 1):
            edges.append(EdgeDefinition(source=nodes[i].id, target=nodes[i + 1].id))
        edges.append(EdgeDefinition(source=nodes[-1].id, target="__end__"))

    return WorkflowDefinition(
        name=name,
        description=description,
        state_type=state_type,
        nodes=nodes,
        edges=edges,
    )


async def persist_workflow(definition: WorkflowDefinition) -> str | None:
    """Save a workflow definition to the database for future reuse.

    Returns the workflow ID if persisted successfully, None otherwise.
    """
    try:
        from src.dal.workflows import WorkflowDefinitionRepository
        from src.storage import get_session

        async with get_session() as session:
            repo = WorkflowDefinitionRepository(session)
            record = await repo.create(
                name=definition.name,
                description=definition.description,
                definition=definition.model_dump(),
                status=definition.status,
            )
            await session.commit()
            logger.info("Persisted workflow '%s' as %s", definition.name, record.id)
            return str(record.id)
    except Exception:
        logger.warning("Failed to persist workflow '%s'", definition.name, exc_info=True)
        return None
