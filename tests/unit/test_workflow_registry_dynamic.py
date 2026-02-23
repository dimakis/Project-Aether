"""Tests for dynamic workflow integration into WORKFLOW_REGISTRY (Feature 29).

Covers:
- Static workflows remain accessible
- Dynamic workflows can be registered from WorkflowDefinition
- get_workflow resolves dynamic workflows alongside static ones
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.graph.workflows.definition import WorkflowDefinition
from src.graph.workflows.manifest import NodeManifest


async def _dummy_node(state: object) -> dict:
    return {}


class TestDynamicWorkflowRegistration:
    """WORKFLOW_REGISTRY supports dynamic workflows from definitions."""

    def test_static_workflows_still_available(self):
        from src.graph.workflows._registry import WORKFLOW_REGISTRY

        assert "conversation" in WORKFLOW_REGISTRY
        assert "team_analysis" in WORKFLOW_REGISTRY

    def test_register_dynamic_workflow(self):
        from src.graph.workflows._registry import (
            register_dynamic_workflow,
            unregister_dynamic_workflow,
        )

        register_dynamic_workflow("my-custom", MagicMock())
        from src.graph.workflows._registry import WORKFLOW_REGISTRY

        assert "my-custom" in WORKFLOW_REGISTRY
        unregister_dynamic_workflow("my-custom")
        assert "my-custom" not in WORKFLOW_REGISTRY

    def test_get_workflow_resolves_dynamic(self):
        from src.graph.workflows._registry import (
            get_workflow,
            register_dynamic_workflow,
            unregister_dynamic_workflow,
        )

        mock_builder = MagicMock(return_value=MagicMock())
        register_dynamic_workflow("test-dynamic", mock_builder)

        get_workflow("test-dynamic")
        mock_builder.assert_called_once()
        unregister_dynamic_workflow("test-dynamic")

    def test_dynamic_does_not_override_static(self):
        from src.graph.workflows._registry import (
            WORKFLOW_REGISTRY,
            register_dynamic_workflow,
            unregister_dynamic_workflow,
        )

        original = WORKFLOW_REGISTRY.get("conversation")
        register_dynamic_workflow("conversation", MagicMock())
        assert WORKFLOW_REGISTRY["conversation"] is not original
        unregister_dynamic_workflow("conversation")
        assert WORKFLOW_REGISTRY.get("conversation") is None

    def test_compile_and_register_from_definition(self):
        from src.graph.workflows._registry import (
            compile_and_register,
            unregister_dynamic_workflow,
        )

        manifest = NodeManifest()
        manifest.register(name="node_a", function=_dummy_node, state_type="ConversationState")

        defn = WorkflowDefinition(
            name="compiled-wf",
            description="Test compiled workflow",
            state_type="ConversationState",
            nodes=[{"id": "a", "function": "node_a"}],
            edges=[
                {"source": "__start__", "target": "a"},
                {"source": "a", "target": "__end__"},
            ],
        )

        compile_and_register(defn, manifest)
        from src.graph.workflows._registry import WORKFLOW_REGISTRY

        assert "compiled-wf" in WORKFLOW_REGISTRY
        unregister_dynamic_workflow("compiled-wf")
