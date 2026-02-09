"""Approval tools for the Architect agent.

Provides the seek_approval tool that routes all mutating actions
(entity commands, automations, scripts, scenes) through the
Proposals page for HITL review before execution.
"""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.dal import ProposalRepository
from src.storage import get_session
from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)

VALID_ACTION_TYPES = {"entity_command", "automation", "script", "scene"}


@tool("seek_approval")
@trace_with_uri(name="approval.seek_approval", span_type="TOOL")
async def seek_approval(
    action_type: str,
    name: str,
    description: str,
    yaml_content: str | None = None,
    entity_id: str | None = None,
    service_domain: str | None = None,
    service_action: str | None = None,
    service_data: dict | None = None,
    trigger: dict | list | None = None,
    actions: dict | list | None = None,
    conditions: dict | list | None = None,
    mode: str = "single",
) -> str:
    """Submit an action for user approval before execution.

    Use this tool whenever you want to perform any action that modifies
    Home Assistant state. The action will appear in the Proposals page
    for the user to review, approve, and deploy.

    Args:
        action_type: Type of action - must be one of:
            - "entity_command": Turn on/off/toggle an entity or call a service
            - "automation": Create a new HA automation
            - "script": Create a new HA script
            - "scene": Create a new HA scene
        name: Short descriptive name for the action
        description: What this action does and why
        yaml_content: Raw YAML content (optional, for automation/script/scene)
        entity_id: Entity ID for entity_command type (e.g., "light.living_room")
        service_domain: Service domain for entity_command (e.g., "light", "switch")
        service_action: Service action for entity_command (e.g., "turn_on", "toggle")
        service_data: Additional service call data (e.g., {"brightness": 255})
        trigger: Trigger config for automation type.
            REQUIRED for "automation" — must be a non-empty dict or list
            describing what triggers the automation (e.g., sun event, state
            change, time pattern). Do NOT omit this.
        actions: Action config for automation/script type.
            REQUIRED for "automation" and "script" — must be a non-empty dict
            or list describing what the automation/script does (service calls,
            delays, conditions, etc.). Do NOT omit this.
        conditions: Condition config for automation type (optional)
        mode: Execution mode for automation/script (default: "single")

    Returns:
        Confirmation message with the proposal details
    """
    if action_type not in VALID_ACTION_TYPES:
        return (
            f"Invalid action_type '{action_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ACTION_TYPES))}"
        )

    # Build the proposal based on type
    if action_type == "entity_command":
        return await _create_entity_command_proposal(
            name=name,
            description=description,
            entity_id=entity_id,
            service_domain=service_domain,
            service_action=service_action,
            service_data=service_data,
        )
    elif action_type == "automation":
        return await _create_automation_proposal(
            name=name,
            description=description,
            yaml_content=yaml_content,
            trigger=trigger,
            actions=actions,
            conditions=conditions,
            mode=mode,
        )
    elif action_type == "script":
        return await _create_script_proposal(
            name=name,
            description=description,
            actions=actions,
            mode=mode,
        )
    elif action_type == "scene":
        return await _create_scene_proposal(
            name=name,
            description=description,
            actions=actions,
        )

    return f"Unknown action type: {action_type}"


async def _create_entity_command_proposal(
    name: str,
    description: str,
    entity_id: str | None,
    service_domain: str | None,
    service_action: str | None,
    service_data: dict | None,
) -> str:
    """Create an entity command proposal."""
    if not entity_id:
        return "entity_id is required for entity_command proposals."

    # Infer domain/action from entity_id if not provided
    if not service_domain:
        service_domain = entity_id.split(".")[0] if "." in entity_id else "homeassistant"
    if not service_action:
        service_action = "turn_on"

    service_call = {
        "domain": service_domain,
        "service": service_action,
        "entity_id": entity_id,
    }
    if service_data:
        service_call["data"] = service_data

    try:
        async with get_session() as session:
            repo = ProposalRepository(session)
            proposal = await repo.create(
                name=name,
                description=description,
                trigger={},
                actions={},
                proposal_type="entity_command",
                service_call=service_call,
            )
            await repo.propose(proposal.id)
            await session.commit()

            logger.info("Created entity_command proposal %s: %s", proposal.id, name)
            return (
                f"I've submitted a proposal for your approval: **{name}**\n\n"
                f"- **Type**: Entity Command\n"
                f"- **Action**: `{service_domain}.{service_action}` on `{entity_id}`\n"
                f"- **Proposal ID**: `{proposal.id[:8]}...`\n\n"
                f"Please review and approve it on the **Proposals** page before it takes effect."
            )
    except Exception as e:
        logger.error("Failed to create entity_command proposal: %s", e)
        return f"Failed to create proposal: {e}"


async def _create_automation_proposal(
    name: str,
    description: str,
    yaml_content: str | None,
    trigger: dict | list | None,
    actions: dict | list | None,
    conditions: dict | list | None,
    mode: str,
) -> str:
    """Create an automation proposal."""
    # If yaml_content provided, try to parse it
    if yaml_content:
        try:
            import yaml

            parsed = yaml.safe_load(yaml_content)
            if isinstance(parsed, dict):
                trigger = trigger or parsed.get("trigger", parsed.get("triggers", {}))
                actions = actions or parsed.get("action", parsed.get("actions", {}))
                conditions = conditions or parsed.get("condition", parsed.get("conditions"))
                mode = parsed.get("mode", mode)
        except Exception:
            pass  # Fall through to use explicit params

    # Validate required fields — reject early so the LLM retries with full data
    missing: list[str] = []
    if not trigger:
        missing.append("trigger")
    if not actions:
        missing.append("actions")
    if missing:
        fields = " and ".join(missing)
        return (
            f"{fields} {'are' if len(missing) > 1 else 'is'} required for automation "
            f"proposals. Please provide the full trigger/condition/action configuration "
            f"for '{name}' and call seek_approval again."
        )

    try:
        async with get_session() as session:
            repo = ProposalRepository(session)
            proposal = await repo.create(
                name=name,
                description=description,
                trigger=trigger if isinstance(trigger, dict) else {"triggers": trigger or []},
                actions=actions if isinstance(actions, dict) else {"actions": actions or []},
                conditions=conditions,  # type: ignore[arg-type]
                mode=mode,
                proposal_type="automation",
            )
            await repo.propose(proposal.id)
            await session.commit()

            logger.info("Created automation proposal %s: %s", proposal.id, name)
            return (
                f"I've submitted an automation proposal for your approval: **{name}**\n\n"
                f"- **Type**: Automation\n"
                f"- **Description**: {description}\n"
                f"- **Proposal ID**: `{proposal.id[:8]}...`\n\n"
                f"Please review the YAML and approve it on the **Proposals** page."
            )
    except Exception as e:
        logger.error("Failed to create automation proposal: %s", e)
        return f"Failed to create proposal: {e}"


async def _create_script_proposal(
    name: str,
    description: str,
    actions: dict | list | None,
    mode: str,
) -> str:
    """Create a script proposal."""
    # Validate required fields — reject early so the LLM retries with full data
    if not actions:
        return (
            "actions is required for script proposals. Please provide the full "
            f"action sequence for '{name}' and call seek_approval again."
        )

    try:
        async with get_session() as session:
            repo = ProposalRepository(session)
            proposal = await repo.create(
                name=name,
                description=description,
                trigger={},
                actions=actions if isinstance(actions, dict) else {"sequence": actions or []},
                mode=mode,
                proposal_type="script",
            )
            await repo.propose(proposal.id)
            await session.commit()

            logger.info("Created script proposal %s: %s", proposal.id, name)
            return (
                f"I've submitted a script proposal for your approval: **{name}**\n\n"
                f"- **Type**: Script\n"
                f"- **Description**: {description}\n"
                f"- **Proposal ID**: `{proposal.id[:8]}...`\n\n"
                f"Please review and approve it on the **Proposals** page."
            )
    except Exception as e:
        logger.error("Failed to create script proposal: %s", e)
        return f"Failed to create proposal: {e}"


async def _create_scene_proposal(
    name: str,
    description: str,
    actions: dict | list | None,
) -> str:
    """Create a scene proposal."""
    try:
        async with get_session() as session:
            repo = ProposalRepository(session)
            proposal = await repo.create(
                name=name,
                description=description,
                trigger={},
                actions=actions or {},  # type: ignore[arg-type]
                proposal_type="scene",
            )
            await repo.propose(proposal.id)
            await session.commit()

            logger.info("Created scene proposal %s: %s", proposal.id, name)
            return (
                f"I've submitted a scene proposal for your approval: **{name}**\n\n"
                f"- **Type**: Scene\n"
                f"- **Description**: {description}\n"
                f"- **Proposal ID**: `{proposal.id[:8]}...`\n\n"
                f"Please review and approve it on the **Proposals** page."
            )
    except Exception as e:
        logger.error("Failed to create scene proposal: %s", e)
        return f"Failed to create proposal: {e}"


def get_approval_tools() -> list:
    """Return approval tools for the Architect agent."""
    return [seek_approval]
