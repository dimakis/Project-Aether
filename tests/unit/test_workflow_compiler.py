"""Tests for WorkflowCompiler (Feature 29).

The compiler validates a WorkflowDefinition, resolves node references
from the NodeManifest, and produces a LangGraph StateGraph.
"""

from __future__ import annotations

import pytest

from src.graph.workflows.definition import (
    ConditionalEdge,
    WorkflowDefinition,
)
from src.graph.workflows.manifest import NodeManifest


async def _dummy_a(state: object) -> dict:
    return {"step": "a"}


async def _dummy_b(state: object) -> dict:
    return {"step": "b"}


async def _dummy_gate(state: object) -> dict:
    return {"decision": "yes"}


@pytest.fixture()
def manifest():
    m = NodeManifest()
    m.register(name="node_a", function=_dummy_a, state_type="ConversationState")
    m.register(name="node_b", function=_dummy_b, state_type="ConversationState")
    m.register(name="gate", function=_dummy_gate, state_type="ConversationState")
    return m


class TestWorkflowCompiler:
    """WorkflowCompiler validates and compiles definitions to StateGraph."""

    def test_compile_simple_linear_workflow(self, manifest):
        from src.graph.workflows.compiler import WorkflowCompiler

        defn = WorkflowDefinition(
            name="simple",
            description="A -> B",
            state_type="ConversationState",
            nodes=[
                {"id": "a", "function": "node_a"},
                {"id": "b", "function": "node_b"},
            ],
            edges=[
                {"source": "__start__", "target": "a"},
                {"source": "a", "target": "b"},
                {"source": "b", "target": "__end__"},
            ],
        )

        compiler = WorkflowCompiler(manifest)
        graph = compiler.compile(defn)
        assert graph is not None

    def test_compile_rejects_missing_node_function(self, manifest):
        from src.graph.workflows.compiler import CompilationError, WorkflowCompiler

        defn = WorkflowDefinition(
            name="bad",
            description="References missing function",
            state_type="ConversationState",
            nodes=[{"id": "a", "function": "nonexistent_function"}],
            edges=[{"source": "__start__", "target": "a"}],
        )

        compiler = WorkflowCompiler(manifest)
        with pytest.raises(CompilationError, match="nonexistent_function"):
            compiler.compile(defn)

    def test_compile_rejects_orphan_node(self, manifest):
        from src.graph.workflows.compiler import CompilationError, WorkflowCompiler

        defn = WorkflowDefinition(
            name="orphan",
            description="Node c has no edges",
            state_type="ConversationState",
            nodes=[
                {"id": "a", "function": "node_a"},
                {"id": "orphan", "function": "node_b"},
            ],
            edges=[
                {"source": "__start__", "target": "a"},
                {"source": "a", "target": "__end__"},
            ],
        )

        compiler = WorkflowCompiler(manifest)
        with pytest.raises(CompilationError, match="orphan"):
            compiler.compile(defn)

    def test_compile_rejects_unknown_state_type(self, manifest):
        from src.graph.workflows.compiler import CompilationError, WorkflowCompiler

        defn = WorkflowDefinition(
            name="bad-state",
            description="Unknown state",
            state_type="NonexistentState",
            nodes=[{"id": "a", "function": "node_a"}],
            edges=[{"source": "__start__", "target": "a"}],
        )

        compiler = WorkflowCompiler(manifest)
        with pytest.raises(CompilationError, match="NonexistentState"):
            compiler.compile(defn)

    def test_compile_with_conditional_edge(self, manifest):
        from src.graph.workflows.compiler import WorkflowCompiler

        defn = WorkflowDefinition(
            name="conditional",
            description="Gate with branching",
            state_type="ConversationState",
            nodes=[
                {"id": "a", "function": "node_a"},
                {"id": "check", "function": "gate"},
                {"id": "b", "function": "node_b"},
            ],
            edges=[
                {"source": "__start__", "target": "a"},
                {"source": "a", "target": "check"},
            ],
            conditional_edges=[
                ConditionalEdge(
                    source="check",
                    conditions={"yes": "b", "no": "__end__"},
                    default="__end__",
                ),
            ],
        )

        compiler = WorkflowCompiler(manifest)
        graph = compiler.compile(defn)
        assert graph is not None

    def test_validate_returns_errors_list(self, manifest):
        from src.graph.workflows.compiler import WorkflowCompiler

        defn = WorkflowDefinition(
            name="bad",
            description="Multiple issues",
            state_type="ConversationState",
            nodes=[{"id": "a", "function": "nonexistent_function"}],
            edges=[{"source": "__start__", "target": "a"}],
        )

        compiler = WorkflowCompiler(manifest)
        errors = compiler.validate(defn)
        assert len(errors) > 0
        assert any("nonexistent_function" in e for e in errors)
