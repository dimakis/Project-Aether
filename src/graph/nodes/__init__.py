"""Graph nodes for LangGraph workflows.

Each node is an async function that takes state and returns state updates.
Nodes are composable building blocks for agent workflows.

This module re-exports all node functions from domain-specific modules
for backward compatibility with existing imports.
"""

# Discovery workflow nodes
# Analysis workflow nodes
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

# Conversation workflow nodes
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
    # Conversation nodes
    "architect_propose_node",
    "architect_refine_node",
    "architect_review_node",
    # Optimization nodes
    "collect_behavioral_data_node",
    # Analysis nodes
    "collect_energy_data_node",
    "conversation_error_node",
    # Review nodes
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
    "generate_script_node",
    "infer_areas_node",
    "infer_devices_node",
    # Discovery nodes
    "initialize_discovery_node",
    "persist_entities_node",
    "present_recommendations_node",
    "process_approval_node",
    "resolve_targets_node",
    "run_discovery_node",
    "sync_automations_node",
]
