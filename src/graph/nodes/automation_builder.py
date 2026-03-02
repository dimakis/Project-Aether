"""Node implementations for the automation builder workflow.

Feature 36: Natural Language Automation Builder.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage

if TYPE_CHECKING:
    from src.graph.state.automation_builder import AutomationBuilderState

logger = logging.getLogger(__name__)


async def gather_intent_node(state: AutomationBuilderState) -> dict[str, Any]:
    """Extract automation intent from user messages using the LLM."""
    from src.llm import get_llm

    messages = state.get("messages", [])
    if not messages:
        return {"needs_clarification": True}

    llm = get_llm()

    prompt = (
        "Extract the automation intent from the user's message. Identify:\n"
        "1. Trigger type (time, state, event, sun, zone, etc.)\n"
        "2. Trigger configuration\n"
        "3. Entity IDs involved\n"
        "4. Actions to perform\n"
        "5. Any conditions\n\n"
        "If the intent is unclear, ask a clarifying question.\n"
        "Respond with JSON: {trigger_type, trigger_config, entity_ids, "
        "action_config, condition_config, needs_clarification, clarification_question}"
    )

    response = await llm.ainvoke([HumanMessage(content=prompt), *messages])
    content = response.content if hasattr(response, "content") else str(response)

    try:
        data = _extract_json(str(content))
        return {
            "trigger_type": data.get("trigger_type"),
            "trigger_config": data.get("trigger_config"),
            "entity_ids": data.get("entity_ids", []),
            "action_config": data.get("action_config"),
            "condition_config": data.get("condition_config"),
            "needs_clarification": data.get("needs_clarification", False),
            "messages": [*list(messages), AIMessage(content=str(content))],
        }
    except Exception:
        logger.debug("Failed to parse intent JSON, requesting clarification")
        return {
            "needs_clarification": True,
            "messages": [*list(messages), AIMessage(content=str(content))],
        }


async def validate_entities_node(state: AutomationBuilderState) -> dict[str, Any]:
    """Validate that all entity IDs exist in the HA registry."""
    from src.tools.automation_builder_tools import check_entity_exists

    entity_ids = state.get("entity_ids", [])
    errors: list[str] = []
    validated: list[dict[str, Any]] = []

    for entity_id in entity_ids:
        result = json.loads(await check_entity_exists.ainvoke(entity_id))
        if result["exists"]:
            validated.append(result)
        else:
            suggestions = result.get("suggestions", [])
            if suggestions:
                names = ", ".join(s["entity_id"] for s in suggestions[:3])
                errors.append(f"Entity '{entity_id}' not found. Did you mean: {names}")
            else:
                errors.append(f"Entity '{entity_id}' not found in HA registry.")

    return {
        "validated_entities": validated,
        "entity_errors": errors,
    }


async def check_duplicates_node(state: AutomationBuilderState) -> dict[str, Any]:
    """Check for existing automations that might conflict."""
    from src.tools.automation_builder_tools import find_similar_automations

    entity_ids = state.get("entity_ids", [])
    trigger_type = state.get("trigger_type", "")

    result = json.loads(
        await find_similar_automations.ainvoke(
            {
                "entity_ids": entity_ids,
                "trigger_type": trigger_type or "",
            }
        )
    )

    return {"similar_automations": result.get("similar", [])}


async def generate_yaml_node(state: AutomationBuilderState) -> dict[str, Any]:
    """Generate HA automation YAML from the validated intent."""
    from src.llm import get_llm

    llm = get_llm()

    context = {
        "trigger_type": state.get("trigger_type"),
        "trigger_config": state.get("trigger_config"),
        "entity_ids": state.get("entity_ids"),
        "action_config": state.get("action_config"),
        "condition_config": state.get("condition_config"),
        "validated_entities": state.get("validated_entities"),
        "previous_errors": state.get("validation_errors", []),
    }

    prompt = (
        "Generate valid Home Assistant automation YAML for this intent:\n"
        f"{json.dumps(context, indent=2)}\n\n"
        "Return ONLY the YAML content, no markdown fences."
    )

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = response.content if hasattr(response, "content") else str(response)

    return {
        "yaml_draft": str(content).strip(),
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def validate_yaml_node(state: AutomationBuilderState) -> dict[str, Any]:
    """Validate the generated YAML structurally and semantically."""
    from src.tools.automation_builder_tools import validate_automation_draft

    yaml_draft = state.get("yaml_draft", "")
    if not yaml_draft:
        return {"validation_errors": ["No YAML draft to validate"]}

    result = json.loads(await validate_automation_draft.ainvoke(yaml_draft))
    return {"validation_errors": result.get("errors", [])}


async def preview_node(state: AutomationBuilderState) -> dict[str, Any]:
    """Create an AutomationProposal for HITL approval."""
    yaml_draft = state.get("yaml_draft", "")
    similar = state.get("similar_automations", [])

    messages = list(state.get("messages", []))

    preview_msg = f"Here's the automation I've generated:\n\n```yaml\n{yaml_draft}\n```\n\n"
    if similar:
        preview_msg += f"Note: {len(similar)} similar automation(s) already exist.\n"
    preview_msg += "\nWould you like to deploy this automation?"

    messages.append(AIMessage(content=preview_msg))

    return {
        "messages": messages,
        "proposal_id": str(uuid4()),
    }


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response text.

    Tries direct parse, then looks for fenced JSON blocks,
    then falls back to the first ``{…}`` substring.
    """
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

    return {}
