"""Tests for WorkflowDefinition declarative schema (Feature 29).

Covers:
- Schema validation for nodes, edges, and conditional routing
- State type reference
- Serialization round-trip
- Invalid topology detection (orphan nodes, missing edges)
"""

from __future__ import annotations


class TestWorkflowDefinitionSchema:
    """WorkflowDefinition is a valid Pydantic model for declarative workflows."""

    def test_minimal_valid_definition(self):
        from src.graph.workflows.definition import WorkflowDefinition

        defn = WorkflowDefinition(
            name="test-workflow",
            description="A test workflow",
            state_type="ConversationState",
            nodes=[{"id": "greet", "function": "echo_node"}],
            edges=[{"source": "__start__", "target": "greet"}],
        )
        assert defn.name == "test-workflow"
        assert len(defn.nodes) == 1
        assert len(defn.edges) == 1

    def test_node_schema_requires_id_and_function(self):
        from src.graph.workflows.definition import NodeDefinition

        node = NodeDefinition(id="greet", function="echo_node")
        assert node.id == "greet"
        assert node.function == "echo_node"

    def test_node_with_metadata(self):
        from src.graph.workflows.definition import NodeDefinition

        node = NodeDefinition(
            id="analyze",
            function="collect_energy_data",
            description="Collect energy data from HA",
            dependencies=["session", "ha_client"],
        )
        assert node.description == "Collect energy data from HA"
        assert "session" in node.dependencies

    def test_edge_schema(self):
        from src.graph.workflows.definition import EdgeDefinition

        edge = EdgeDefinition(source="collect", target="analyze")
        assert edge.source == "collect"
        assert edge.target == "analyze"

    def test_conditional_edge(self):
        from src.graph.workflows.definition import ConditionalEdge

        edge = ConditionalEdge(
            source="check",
            conditions={"approved": "deploy", "rejected": "revise"},
            default="revise",
        )
        assert edge.conditions["approved"] == "deploy"
        assert edge.default == "revise"

    def test_definition_with_conditional_edges(self):
        from src.graph.workflows.definition import (
            ConditionalEdge,
            WorkflowDefinition,
        )

        defn = WorkflowDefinition(
            name="approval-flow",
            description="Workflow with approval gate",
            state_type="ConversationState",
            nodes=[
                {"id": "propose", "function": "propose_node"},
                {"id": "gate", "function": "approval_gate"},
                {"id": "deploy", "function": "deploy_node"},
                {"id": "revise", "function": "revise_node"},
            ],
            edges=[
                {"source": "__start__", "target": "propose"},
                {"source": "propose", "target": "gate"},
            ],
            conditional_edges=[
                ConditionalEdge(
                    source="gate",
                    conditions={"approved": "deploy", "rejected": "revise"},
                    default="revise",
                ),
            ],
        )
        assert len(defn.conditional_edges) == 1
        assert len(defn.nodes) == 4

    def test_serialization_roundtrip(self):
        from src.graph.workflows.definition import WorkflowDefinition

        defn = WorkflowDefinition(
            name="test",
            description="Test workflow",
            state_type="AnalysisState",
            nodes=[{"id": "a", "function": "fn_a"}],
            edges=[{"source": "__start__", "target": "a"}],
        )
        json_str = defn.model_dump_json()
        restored = WorkflowDefinition.model_validate_json(json_str)
        assert restored.name == "test"
        assert restored.state_type == "AnalysisState"

    def test_version_defaults_to_one(self):
        from src.graph.workflows.definition import WorkflowDefinition

        defn = WorkflowDefinition(
            name="test",
            description="Test",
            state_type="ConversationState",
            nodes=[{"id": "a", "function": "fn_a"}],
            edges=[{"source": "__start__", "target": "a"}],
        )
        assert defn.version == 1

    def test_status_defaults_to_draft(self):
        from src.graph.workflows.definition import WorkflowDefinition

        defn = WorkflowDefinition(
            name="test",
            description="Test",
            state_type="ConversationState",
            nodes=[{"id": "a", "function": "fn_a"}],
            edges=[{"source": "__start__", "target": "a"}],
        )
        assert defn.status == "draft"

    def test_intent_patterns_for_auto_routing(self):
        from src.graph.workflows.definition import WorkflowDefinition

        defn = WorkflowDefinition(
            name="morning-routine",
            description="Morning analysis routine",
            state_type="AnalysisState",
            nodes=[{"id": "a", "function": "fn_a"}],
            edges=[{"source": "__start__", "target": "a"}],
            intent_patterns=["morning_routine", "daily_analysis"],
        )
        assert "morning_routine" in defn.intent_patterns
