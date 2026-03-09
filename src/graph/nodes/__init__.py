"""Graph nodes for LangGraph workflows.

Each node is an async function that takes state and returns state updates.
Nodes are composable building blocks for agent workflows.

Uses lazy imports to avoid loading all node implementations at import time.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    "analysis_error_node": "src.graph.nodes.analysis",
    "analyze_and_suggest_node": "src.graph.nodes.analysis",
    "architect_review_node": "src.graph.nodes.analysis",
    "collect_behavioral_data_node": "src.graph.nodes.analysis",
    "collect_energy_data_node": "src.graph.nodes.analysis",
    "execute_sandbox_node": "src.graph.nodes.analysis",
    "extract_insights_node": "src.graph.nodes.analysis",
    "generate_script_node": "src.graph.nodes.analysis",
    "present_recommendations_node": "src.graph.nodes.analysis",
    "check_duplicates_node": "src.graph.nodes.automation_builder",
    "gather_intent_node": "src.graph.nodes.automation_builder",
    "generate_yaml_node": "src.graph.nodes.automation_builder",
    "preview_node": "src.graph.nodes.automation_builder",
    "validate_entities_node": "src.graph.nodes.automation_builder",
    "validate_yaml_node": "src.graph.nodes.automation_builder",
    "approval_gate_node": "src.graph.nodes.conversation",
    "architect_propose_node": "src.graph.nodes.conversation",
    "architect_refine_node": "src.graph.nodes.conversation",
    "conversation_error_node": "src.graph.nodes.conversation",
    "developer_deploy_node": "src.graph.nodes.conversation",
    "developer_rollback_node": "src.graph.nodes.conversation",
    "process_approval_node": "src.graph.nodes.conversation",
    "error_handler_node": "src.graph.nodes.discovery",
    "fetch_entities_node": "src.graph.nodes.discovery",
    "finalize_discovery_node": "src.graph.nodes.discovery",
    "infer_areas_node": "src.graph.nodes.discovery",
    "infer_devices_node": "src.graph.nodes.discovery",
    "initialize_discovery_node": "src.graph.nodes.discovery",
    "persist_entities_node": "src.graph.nodes.discovery",
    "run_discovery_node": "src.graph.nodes.discovery",
    "sync_automations_node": "src.graph.nodes.discovery",
    "create_review_proposals_node": "src.graph.nodes.review",
    "fetch_configs_node": "src.graph.nodes.review",
    "gather_context_node": "src.graph.nodes.review",
    "resolve_targets_node": "src.graph.nodes.review",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]
    if name in _EXPORTS:
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr
    raise AttributeError(f"module 'src.graph.nodes' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
    from src.graph.nodes.analysis import (
        analysis_error_node,
        analyze_and_suggest_node,
        architect_review_node,
        collect_behavioral_data_node,
        collect_energy_data_node,
        execute_sandbox_node,
        extract_insights_node,
        generate_script_node,
        present_recommendations_node,
    )
    from src.graph.nodes.automation_builder import (
        check_duplicates_node,
        gather_intent_node,
        generate_yaml_node,
        preview_node,
        validate_entities_node,
        validate_yaml_node,
    )
    from src.graph.nodes.conversation import (
        approval_gate_node,
        architect_propose_node,
        architect_refine_node,
        conversation_error_node,
        developer_deploy_node,
        developer_rollback_node,
        process_approval_node,
    )
    from src.graph.nodes.discovery import (
        error_handler_node,
        fetch_entities_node,
        finalize_discovery_node,
        infer_areas_node,
        infer_devices_node,
        initialize_discovery_node,
        persist_entities_node,
        run_discovery_node,
        sync_automations_node,
    )
    from src.graph.nodes.review import (
        create_review_proposals_node,
        fetch_configs_node,
        gather_context_node,
        resolve_targets_node,
    )

__all__ = [
    "analysis_error_node",
    "analyze_and_suggest_node",
    "approval_gate_node",
    "architect_propose_node",
    "architect_refine_node",
    "architect_review_node",
    "check_duplicates_node",
    "collect_behavioral_data_node",
    "collect_energy_data_node",
    "conversation_error_node",
    "create_review_proposals_node",
    "developer_deploy_node",
    "developer_rollback_node",
    "error_handler_node",
    "execute_sandbox_node",
    "extract_insights_node",
    "fetch_configs_node",
    "fetch_entities_node",
    "finalize_discovery_node",
    "gather_context_node",
    "gather_intent_node",
    "generate_script_node",
    "generate_yaml_node",
    "infer_areas_node",
    "infer_devices_node",
    "initialize_discovery_node",
    "persist_entities_node",
    "present_recommendations_node",
    "preview_node",
    "process_approval_node",
    "resolve_targets_node",
    "run_discovery_node",
    "sync_automations_node",
    "validate_entities_node",
    "validate_yaml_node",
]
