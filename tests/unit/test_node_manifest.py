"""Tests for NodeManifest registry (Feature 29).

The NodeManifest registers available node functions with metadata
so the WorkflowCompiler can resolve WorkflowDefinition node references
to actual callable functions.
"""

from __future__ import annotations


async def _echo_node(state: object) -> dict:
    """Dummy node for testing."""
    return {"echoed": True}


async def _analyze_node(state: object, session: object = None) -> dict:
    """Dummy node with dependency."""
    return {"analyzed": True}


class TestNodeManifestRegistration:
    """NodeManifest supports registering and looking up node functions."""

    def test_register_and_lookup(self):
        from src.graph.workflows.manifest import NodeManifest

        manifest = NodeManifest()
        manifest.register(
            name="echo",
            function=_echo_node,
            description="Echo node for testing",
            state_type="ConversationState",
        )

        entry = manifest.get("echo")
        assert entry is not None
        assert entry.name == "echo"
        assert entry.function is _echo_node

    def test_lookup_missing_returns_none(self):
        from src.graph.workflows.manifest import NodeManifest

        manifest = NodeManifest()
        assert manifest.get("nonexistent") is None

    def test_register_with_dependencies(self):
        from src.graph.workflows.manifest import NodeManifest

        manifest = NodeManifest()
        manifest.register(
            name="analyze",
            function=_analyze_node,
            description="Analysis node",
            state_type="AnalysisState",
            dependencies=["session"],
        )

        entry = manifest.get("analyze")
        assert entry is not None
        assert "session" in entry.dependencies

    def test_list_all_returns_registered_nodes(self):
        from src.graph.workflows.manifest import NodeManifest

        manifest = NodeManifest()
        manifest.register(name="a", function=_echo_node, state_type="ConversationState")
        manifest.register(name="b", function=_analyze_node, state_type="AnalysisState")

        all_nodes = manifest.list_all()
        names = [n.name for n in all_nodes]
        assert "a" in names
        assert "b" in names
        assert len(all_nodes) == 2

    def test_contains_check(self):
        from src.graph.workflows.manifest import NodeManifest

        manifest = NodeManifest()
        manifest.register(name="echo", function=_echo_node, state_type="ConversationState")

        assert "echo" in manifest
        assert "missing" not in manifest

    def test_duplicate_register_overwrites(self):
        from src.graph.workflows.manifest import NodeManifest

        manifest = NodeManifest()
        manifest.register(
            name="echo", function=_echo_node, state_type="ConversationState", description="v1"
        )
        manifest.register(
            name="echo", function=_analyze_node, state_type="AnalysisState", description="v2"
        )

        entry = manifest.get("echo")
        assert entry is not None
        assert entry.description == "v2"
        assert entry.function is _analyze_node


class TestNodeManifestEntry:
    """NodeManifestEntry holds metadata about a node function."""

    def test_entry_has_required_fields(self):
        from src.graph.workflows.manifest import NodeManifestEntry

        entry = NodeManifestEntry(
            name="test",
            function=_echo_node,
            state_type="ConversationState",
        )
        assert entry.name == "test"
        assert entry.state_type == "ConversationState"
        assert entry.function is _echo_node
        assert entry.description == ""
        assert entry.dependencies == []


class TestDefaultManifest:
    """get_default_manifest() returns a pre-populated manifest."""

    def test_default_manifest_has_builtin_nodes(self):
        from src.graph.workflows.manifest import get_default_manifest

        manifest = get_default_manifest()
        assert len(manifest.list_all()) > 0

    def test_default_manifest_includes_conversation_nodes(self):
        from src.graph.workflows.manifest import get_default_manifest

        manifest = get_default_manifest()
        assert "architect_propose" in manifest
