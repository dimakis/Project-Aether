"""State definition for the automation builder workflow.

Feature 36: Natural Language Automation Builder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage


class AutomationBuilderState(TypedDict, total=False):
    """State for the automation builder workflow.

    Tracks the progression from natural language intent to validated
    YAML and deployment via HITL approval.
    """

    messages: list[BaseMessage]

    # Intent extraction
    user_intent: str
    trigger_type: str | None
    trigger_config: dict[str, Any] | None
    action_config: dict[str, Any] | None
    condition_config: dict[str, Any] | None
    entity_ids: list[str]

    # Validation
    validated_entities: list[dict[str, Any]]
    entity_errors: list[str]

    # Duplicate detection
    similar_automations: list[dict[str, Any]]

    # YAML generation
    yaml_draft: str | None
    validation_errors: list[str]

    # Proposal
    proposal_id: str | None

    # Control flow
    needs_clarification: bool
    iteration_count: int
