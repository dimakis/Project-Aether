"""Config review synthesis methods for the Architect agent.

Used by the config review workflow to convert DS team findings
into concrete YAML improvement suggestions.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.graph.state import AutomationSuggestion, ConversationState

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.architect.proposals import (
    create_proposal,
    extract_proposal,
    proposal_to_yaml,
)
from src.agents.prompts import load_prompt
from src.dal import ProposalRepository
from src.graph.state import HITLApproval

logger = logging.getLogger(__name__)


async def synthesize_review(
    llm: BaseChatModel,
    configs: dict[str, str],
    ds_findings: list[dict[str, Any]],
    entity_context: dict[str, Any] | None = None,
    focus: str | None = None,
) -> list[dict[str, Any]]:
    """Synthesize DS team findings into concrete YAML improvement suggestions.

    Called by the config review workflow after the DS team has analyzed
    the configs. The Architect combines findings with its understanding
    of HA best practices to produce actionable YAML suggestions.

    Args:
        llm: LLM instance to use.
        configs: Mapping of entity_id -> original YAML config.
        ds_findings: Findings from DS team specialists.
        entity_context: Optional context (areas, entities, etc.).
        focus: Optional focus area (energy, behavioral, efficiency, security).

    Returns:
        List of suggestion dicts with entity_id, suggested_yaml, review_notes.
    """
    configs_block = "\n---\n".join(f"# {eid}\n{yaml_str}" for eid, yaml_str in configs.items())
    findings_block = json.dumps(ds_findings, indent=2, default=str)
    context_block = json.dumps(entity_context or {}, default=str)[:2000]

    focus_instruction = ""
    if focus:
        focus_instruction = f"\nFocus area: {focus}. Prioritize improvements related to {focus}.\n"

    system_prompt = (
        "You are the Architect agent. Synthesize the Data Science team's "
        "findings into concrete YAML improvement suggestions for Home "
        "Assistant configurations.\n\n"
        "For each entity that needs changes, produce a suggestion with:\n"
        '  "entity_id": the HA entity ID,\n'
        '  "suggested_yaml": the improved YAML configuration,\n'
        '  "review_notes": explanation of what changed and why\n\n'
        "Return ONLY a JSON array of suggestion objects. "
        "No markdown fencing."
        f"{focus_instruction}"
    )

    user_prompt = (
        f"Original configurations:\n```yaml\n{configs_block}\n```\n\n"
        f"DS team findings:\n{findings_block}\n\n"
        f"Entity context:\n{context_block}"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        response = await llm.ainvoke(messages)
        content_raw = response.content
        content = content_raw.strip() if isinstance(content_raw, str) else str(content_raw).strip()
        # Strip markdown fencing if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        suggestions = json.loads(content.strip())
        if not isinstance(suggestions, list):
            suggestions = []
    except json.JSONDecodeError:
        logger.warning("Architect: failed to parse synthesize_review response (JSON decode error)")
        suggestions = []
    except Exception:
        logger.warning("Architect: failed to parse synthesize_review response")
        suggestions = []

    return suggestions


async def refine_proposal(
    llm: BaseChatModel,
    build_messages_fn: Any,
    state: ConversationState,
    feedback: str,
    proposal_id: str,
    session: AsyncSession,
) -> dict[str, object]:
    """Refine a proposal based on user feedback.

    Args:
        llm: LLM instance to use.
        build_messages_fn: Function to build message list from state.
        state: Current conversation state.
        feedback: User's feedback.
        proposal_id: ID of proposal to refine.
        session: Database session.

    Returns:
        State updates.
    """
    # Get existing proposal
    proposal_repo = ProposalRepository(session)
    proposal = await proposal_repo.get_by_id(proposal_id)
    if not proposal:
        return {"messages": [AIMessage(content="I couldn't find that proposal to refine.")]}

    # Build context with current proposal
    current_yaml = proposal.to_ha_yaml_dict()

    messages = build_messages_fn(state)
    messages.append(
        SystemMessage(
            content=f"The user wants to refine this proposal:\n```yaml\n"
            f"{proposal_to_yaml(current_yaml)}\n```\n"
            f"User feedback: {feedback}"
        )
    )

    # Generate refined response
    response = await llm.ainvoke(messages)
    response_text = str(response.content)

    # Check for new proposal
    proposal_data = extract_proposal(response_text)
    updates: dict[str, object] = {
        "messages": [
            HumanMessage(content=feedback),
            AIMessage(content=response_text),
        ]
    }

    if proposal_data:
        # Archive old proposal and create new one
        await proposal_repo.reject(proposal_id, "Replaced with refined version")

        new_proposal = await create_proposal(
            session,
            state.conversation_id,
            proposal_data,
        )
        updates["pending_approvals"] = [
            HITLApproval(
                id=new_proposal.id,
                request_type="automation",
                description=new_proposal.description or new_proposal.name,
                yaml_content=proposal_to_yaml(proposal_data),
            )
        ]
        updates["architect_design"] = proposal_data

    return updates


async def receive_suggestion(
    llm: BaseChatModel,
    trace_span_fn: Any,
    suggestion: AutomationSuggestion,
    session: AsyncSession,
) -> dict[str, object]:
    """Receive an AutomationSuggestion from the DS Team and create a proposal.

    Converts the DS Team suggestion into a structured prompt, generates a full
    automation proposal, and returns it for HITL approval.

    Feature 03: Intelligent Optimization -- DS Team-to-Architect suggestion flow.

    Args:
        llm: LLM instance to use.
        trace_span_fn: Trace span context manager function.
        suggestion: AutomationSuggestion model from the DS Team.
        session: Database session for proposal persistence.

    Returns:
        Dict with proposal data and formatted response.
    """
    # Build a structured prompt from the suggestion
    prompt = (
        f"The Data Science team has identified a pattern that could be automated:\n\n"
        f"**Pattern:** {suggestion.pattern}\n"
        f"**Entities:** {', '.join(suggestion.entities[:10])}\n"
        f"**Proposed Trigger:** {suggestion.proposed_trigger}\n"
        f"**Proposed Action:** {suggestion.proposed_action}\n"
        f"**Confidence:** {suggestion.confidence:.0%}\n"
        f"**Source Analysis:** {suggestion.source_insight_type}\n"
    )

    if suggestion.evidence:
        evidence_str = json.dumps(suggestion.evidence, indent=2, default=str)[:500]
        prompt += f"\n**Evidence:**\n```json\n{evidence_str}\n```\n"

    prompt += (
        "\nPlease design a complete Home Assistant automation based on this suggestion. "
        "Include the full trigger, conditions (if needed), and actions in a JSON proposal block."
    )

    messages = [
        SystemMessage(content=load_prompt("architect_system")),
        HumanMessage(content=prompt),
    ]

    async with trace_span_fn("receive_suggestion", None) as span:
        response = await llm.ainvoke(messages)
        response_text = str(response.content)

        span["outputs"] = {"response_length": len(response_text)}

        # Try to extract a proposal
        proposal_data = extract_proposal(response_text)

        result: dict[str, object] = {
            "response": response_text,
            "proposal_data": proposal_data,
        }

        if proposal_data and session:
            try:
                proposal = await create_proposal(
                    session,
                    conversation_id="ds_suggestion",
                    proposal_data=proposal_data,
                )
                result["proposal_id"] = proposal.id
                result["proposal_name"] = proposal.name
                result["proposal_yaml"] = proposal_to_yaml(proposal_data)
            except Exception as e:
                logger.warning(f"Failed to create proposal from suggestion: {e}")
                result["error"] = str(e)

        return result
