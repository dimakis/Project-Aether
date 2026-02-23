"""Declarative workflow definition schema (Feature 29).

Provides Pydantic models for describing workflow graphs as data rather
than code.  A ``WorkflowDefinition`` can be serialized to JSON, stored
in the database, and compiled into a LangGraph ``StateGraph`` by the
``WorkflowCompiler``.

This is the declarative counterpart to the imperative ``build_*_graph``
functions in the existing workflow modules.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

_MAX_NODES = 100
_MAX_EDGES = 200
_MAX_CONDITIONAL_EDGES = 50
_MAX_INTENT_PATTERNS = 30


class NodeDefinition(BaseModel):
    """A single node in a declarative workflow graph."""

    id: str = Field(
        ..., min_length=1, max_length=100, description="Unique node identifier within this workflow"
    )
    function: str = Field(
        ..., min_length=1, max_length=200, description="Node function name in the NodeManifest"
    )
    description: str = Field(default="", description="Human-readable purpose")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Runtime dependencies to inject (e.g., 'session', 'ha_client')",
    )


class EdgeDefinition(BaseModel):
    """A directed edge between two nodes."""

    source: str = Field(..., max_length=100, description="Source node ID (or '__start__')")
    target: str = Field(..., max_length=100, description="Target node ID (or '__end__')")


class ConditionalEdge(BaseModel):
    """A conditional branching edge from a node."""

    source: str = Field(..., max_length=100, description="Source node ID")
    conditions: dict[str, str] = Field(
        ...,
        description="Mapping of condition value -> target node ID",
    )
    default: str = Field(
        default="__end__",
        max_length=100,
        description="Target node when no condition matches",
    )
    routing_field: str = Field(
        default="decision",
        max_length=100,
        description="State field to read the routing decision from",
    )


class WorkflowDefinition(BaseModel):
    """Declarative specification of a workflow graph.

    Describes the topology (nodes, edges, conditional routing), the
    state type, and metadata for discovery and versioning.
    """

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    state_type: str = Field(
        ...,
        description="Name of the Pydantic state class (e.g., 'ConversationState')",
    )
    version: int = Field(default=1, ge=1)
    status: str = Field(default="draft", pattern="^(draft|active|archived)$")

    nodes: list[NodeDefinition] = Field(..., min_length=1, max_length=_MAX_NODES)
    edges: list[EdgeDefinition] = Field(default_factory=list, max_length=_MAX_EDGES)
    conditional_edges: list[ConditionalEdge] = Field(
        default_factory=list, max_length=_MAX_CONDITIONAL_EDGES
    )

    intent_patterns: list[str] = Field(
        default_factory=list,
        max_length=_MAX_INTENT_PATTERNS,
        description="Intent patterns for Orchestrator auto-routing to this workflow",
    )
