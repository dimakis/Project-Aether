"""Graph nodes for LangGraph workflows.

Each node is an async function that takes state and returns state updates.
Nodes are composable building blocks for agent workflows.

This module re-exports all node functions from domain-specific modules
for backward compatibility with existing imports.
"""

# Discovery workflow nodes
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

__all__ = [
    # Discovery nodes
    "initialize_discovery_node",
    "fetch_entities_node",
    "infer_areas_node",
    "infer_devices_node",
    "persist_entities_node",
    "sync_automations_node",
    "finalize_discovery_node",
    "error_handler_node",
    "run_discovery_node",
    # Conversation nodes
    "architect_propose_node",
    "architect_refine_node",
    "approval_gate_node",
    "process_approval_node",
    "developer_deploy_node",
    "developer_rollback_node",
    "conversation_error_node",
    # Analysis nodes
    "collect_energy_data_node",
    "generate_script_node",
    "execute_sandbox_node",
    "extract_insights_node",
    "analysis_error_node",
    # Optimization nodes
    "collect_behavioral_data_node",
    "analyze_and_suggest_node",
    "architect_review_node",
    "present_recommendations_node",
]
