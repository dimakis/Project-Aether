"""Node manifest registry (Feature 29).

Registers available node functions with metadata so the
``WorkflowCompiler`` can resolve ``WorkflowDefinition`` node
references to actual callable functions.

``get_default_manifest()`` returns a pre-populated manifest with
all built-in node functions from ``src.graph.nodes``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class NodeManifestEntry:
    """Metadata about a registered node function."""

    name: str
    function: Callable[..., Any]
    state_type: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)


class NodeManifest:
    """Registry of available node functions for workflow composition."""

    def __init__(self) -> None:
        self._entries: dict[str, NodeManifestEntry] = {}

    def register(
        self,
        name: str,
        function: Callable[..., Any],
        state_type: str = "",
        description: str = "",
        dependencies: list[str] | None = None,
    ) -> None:
        """Register a node function.

        Args:
            name: Unique node name (used in WorkflowDefinition).
            function: The async node function.
            state_type: State class name this node operates on.
            description: Human-readable purpose.
            dependencies: Runtime dependencies (e.g., 'session').
        """
        self._entries[name] = NodeManifestEntry(
            name=name,
            function=function,
            state_type=state_type,
            description=description,
            dependencies=dependencies or [],
        )

    def get(self, name: str) -> NodeManifestEntry | None:
        """Look up a node by name."""
        return self._entries.get(name)

    def list_all(self) -> list[NodeManifestEntry]:
        """Return all registered entries."""
        return list(self._entries.values())

    def __contains__(self, name: str) -> bool:
        return name in self._entries


def get_default_manifest() -> NodeManifest:
    """Build and return the default manifest with all built-in nodes."""
    from src.graph.nodes.analysis import (
        analyze_and_suggest_node,
        architect_review_node,
        collect_behavioral_data_node,
        collect_energy_data_node,
        execute_sandbox_node,
        extract_insights_node,
        generate_script_node,
        present_recommendations_node,
    )
    from src.graph.nodes.conversation import (
        approval_gate_node,
        architect_propose_node,
        architect_refine_node,
        developer_deploy_node,
        process_approval_node,
    )

    manifest = NodeManifest()

    # Conversation nodes
    manifest.register(
        name="architect_propose",
        function=architect_propose_node,
        state_type="ConversationState",
        description="Generate automation proposal from user request",
        dependencies=["session"],
    )
    manifest.register(
        name="architect_refine",
        function=architect_refine_node,
        state_type="ConversationState",
        description="Refine an existing proposal based on feedback",
        dependencies=["session"],
    )
    manifest.register(
        name="approval_gate",
        function=approval_gate_node,
        state_type="ConversationState",
        description="HITL approval gate for proposals",
    )
    manifest.register(
        name="process_approval",
        function=process_approval_node,
        state_type="ConversationState",
        description="Process user approval/rejection decision",
    )
    manifest.register(
        name="developer_deploy",
        function=developer_deploy_node,
        state_type="ConversationState",
        description="Deploy approved automation to Home Assistant",
        dependencies=["session", "ha_client"],
    )

    # Analysis nodes
    manifest.register(
        name="collect_energy_data",
        function=collect_energy_data_node,
        state_type="AnalysisState",
        description="Collect energy consumption data from HA",
        dependencies=["ha_client"],
    )
    manifest.register(
        name="collect_behavioral_data",
        function=collect_behavioral_data_node,
        state_type="AnalysisState",
        description="Collect behavioral usage pattern data from HA",
        dependencies=["ha_client"],
    )
    manifest.register(
        name="generate_script",
        function=generate_script_node,
        state_type="AnalysisState",
        description="Generate analysis script from collected data",
    )
    manifest.register(
        name="execute_sandbox",
        function=execute_sandbox_node,
        state_type="AnalysisState",
        description="Execute analysis script in gVisor sandbox",
    )
    manifest.register(
        name="extract_insights",
        function=extract_insights_node,
        state_type="AnalysisState",
        description="Extract actionable insights from analysis results",
    )
    manifest.register(
        name="analyze_and_suggest",
        function=analyze_and_suggest_node,
        state_type="AnalysisState",
        description="Analyze patterns and generate automation suggestions",
    )
    manifest.register(
        name="architect_review",
        function=architect_review_node,
        state_type="AnalysisState",
        description="Architect reviews DS team suggestions",
        dependencies=["session"],
    )
    manifest.register(
        name="present_recommendations",
        function=present_recommendations_node,
        state_type="AnalysisState",
        description="Present final recommendations to user",
    )

    return manifest
