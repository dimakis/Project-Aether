"""Automation builder workflow.

Feature 36: Natural Language Automation Builder.

A conversational workflow that guides users through automation creation
with live validation, duplicate detection, and HITL approval.
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver

from src.graph import END, START, StateGraph, create_graph
from src.graph.state.automation_builder import AutomationBuilderState

logger = logging.getLogger(__name__)


def _route_after_intent(
    state: AutomationBuilderState,
) -> Literal["gather_intent", "validate_entities"]:
    if state.get("needs_clarification"):
        return "gather_intent"
    return "validate_entities"


def _route_after_entities(
    state: AutomationBuilderState,
) -> Literal["gather_intent", "check_duplicates"]:
    if state.get("entity_errors"):
        return "gather_intent"
    return "check_duplicates"


def _route_after_validation(
    state: AutomationBuilderState,
) -> Literal["generate_yaml", "preview"]:
    if state.get("validation_errors") and state.get("iteration_count", 0) < 3:
        return "generate_yaml"
    return "preview"


def build_automation_builder_graph() -> StateGraph:
    """Build the automation builder workflow graph.

    Graph structure::

        START
          |
          v
        gather_intent  <-----+
          |                   |
          v                   |
        [needs_clarification?]|
          |       |           |
          N       Y ----------+
          |
          v
        validate_entities
          |
          v
        [entity_errors?]
          |       |
          N       Y --> gather_intent
          |
          v
        check_duplicates
          |
          v
        generate_yaml  <--+
          |                |
          v                |
        validate_yaml      |
          |                |
          v                |
        [valid?]           |
          |       |        |
          Y       N (< 3) -+
          |
          v
        preview (HITL interrupt)
          |
          v
        END
    """
    from src.graph.nodes.automation_builder import (
        check_duplicates_node,
        gather_intent_node,
        generate_yaml_node,
        preview_node,
        validate_entities_node,
        validate_yaml_node,
    )
    from src.tracing import traced_node

    graph = create_graph(AutomationBuilderState)

    graph.add_node("gather_intent", traced_node("gather_intent", gather_intent_node))
    graph.add_node(
        "validate_entities",
        traced_node("validate_entities", validate_entities_node),
    )
    graph.add_node(
        "check_duplicates",
        traced_node("check_duplicates", check_duplicates_node),
    )
    graph.add_node(
        "generate_yaml",
        traced_node("generate_yaml", generate_yaml_node),
    )
    graph.add_node(
        "validate_yaml",
        traced_node("validate_yaml", validate_yaml_node),
    )
    graph.add_node("preview", traced_node("preview", preview_node))

    graph.add_edge(START, "gather_intent")
    graph.add_conditional_edges("gather_intent", _route_after_intent)
    graph.add_conditional_edges("validate_entities", _route_after_entities)
    graph.add_edge("check_duplicates", "generate_yaml")
    graph.add_edge("generate_yaml", "validate_yaml")
    graph.add_conditional_edges("validate_yaml", _route_after_validation)
    graph.add_edge("preview", END)

    return graph


def compile_automation_builder_graph() -> object:
    """Compile the automation builder graph with HITL interrupt.

    Constitution: Safety First — interrupt_before at preview
    ensures human approval before any deployment.

    Returns:
        Compiled graph with checkpointing and HITL interrupts.
    """
    checkpointer = MemorySaver()
    graph = build_automation_builder_graph()
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["preview"],
    )
