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

VALID_ACTION_TYPES = {"entity_command", "automation", "script", "scene", "dashboard", "helper"}


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
    original_yaml: str | None = None,
    dashboard_config: dict | None = None,
    dashboard_url_path: str | None = None,
    helper_config: dict | None = None,
) -> str:
    """Submit an action for user approval before execution.

    Args:
        action_type: entity_command, automation, script, scene, or helper
        name: Short name
        description: What and why
        yaml_content: Raw YAML (optional)
        entity_id: Entity ID for entity_command
        service_domain: Service domain for entity_command
        service_action: Service action for entity_command
        service_data: Extra service data
        trigger: Trigger config (required for automation)
        actions: Action config (required for automation/script)
        conditions: Condition config (optional)
        mode: Execution mode (default "single")
        original_yaml: Current config for diff view
        helper_config: Helper creation config with helper_type and input_id
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
            original_yaml=original_yaml,
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
            original_yaml=original_yaml,
        )
    elif action_type == "script":
        return await _create_script_proposal(
            name=name,
            description=description,
            actions=actions,
            mode=mode,
            original_yaml=original_yaml,
        )
    elif action_type == "scene":
        return await _create_scene_proposal(
            name=name,
            description=description,
            actions=actions,
            original_yaml=original_yaml,
        )
    elif action_type == "dashboard":
        return await _create_dashboard_proposal(
            name=name,
            description=description,
            dashboard_config=dashboard_config,
            dashboard_url_path=dashboard_url_path,
        )
    elif action_type == "helper":
        return await _create_helper_proposal(
            name=name,
            description=description,
            helper_config=helper_config,
        )

    return f"Unknown action type: {action_type}"


async def _create_entity_command_proposal(
    name: str,
    description: str,
    entity_id: str | None,
    service_domain: str | None,
    service_action: str | None,
    service_data: dict | None,
    original_yaml: str | None = None,
) -> str:
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
                original_yaml=original_yaml,
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
    original_yaml: str | None = None,
) -> str:
    # If yaml_content provided, parse using the canonical schema pipeline
    if yaml_content:
        from src.schema import parse_ha_yaml

        parsed, errors = parse_ha_yaml(yaml_content)
        if not errors:
            trigger = trigger or parsed.get("trigger", {})
            actions = actions or parsed.get("action", {})
            conditions = conditions or parsed.get("condition")
            mode = parsed.get("mode", mode)
        else:
            logger.debug(
                "Failed to parse YAML content, falling back to explicit params: %s",
                [str(e) for e in errors],
            )

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
                original_yaml=original_yaml,
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
    original_yaml: str | None = None,
) -> str:
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
                original_yaml=original_yaml,
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
    original_yaml: str | None = None,
) -> str:
    try:
        async with get_session() as session:
            repo = ProposalRepository(session)
            proposal = await repo.create(
                name=name,
                description=description,
                trigger={},
                actions=actions or {},  # type: ignore[arg-type]
                proposal_type="scene",
                original_yaml=original_yaml,
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


async def _create_dashboard_proposal(
    name: str,
    description: str,
    dashboard_config: dict | None,
    dashboard_url_path: str | None,
) -> str:
    """Create a dashboard proposal for Lovelace config changes."""
    if not dashboard_config or not isinstance(dashboard_config, dict):
        return "dashboard_config is required for dashboard proposals."

    try:
        async with get_session() as session:
            repo = ProposalRepository(session)
            proposal = await repo.create(
                name=name,
                description=description,
                trigger={},
                actions={},
                proposal_type="dashboard",
                dashboard_config=dashboard_config,
                service_call={"url_path": dashboard_url_path or None},
            )
            await repo.propose(proposal.id)
            await session.commit()

            logger.info("Created dashboard proposal %s: %s", proposal.id, name)
            return (
                f"I've submitted a dashboard proposal for your approval: **{name}**\n\n"
                f"- **Type**: Dashboard\n"
                f"- **Description**: {description}\n"
                f"- **Target**: {dashboard_url_path or 'default'}\n"
                f"- **Proposal ID**: `{proposal.id[:8]}...`\n\n"
                f"Please review and approve it on the **Proposals** page."
            )
    except Exception as e:
        logger.error("Failed to create dashboard proposal: %s", e)
        return f"Failed to create proposal: {e}"


async def _create_helper_proposal(
    name: str,
    description: str,
    helper_config: dict | None,
) -> str:
    if not helper_config or "helper_type" not in helper_config:
        return (
            "helper_config with 'helper_type' is required for helper proposals. "
            "Provide a dict with helper_type (e.g., 'input_boolean'), input_id, "
            "name, and any type-specific parameters."
        )

    helper_type = helper_config["helper_type"]
    input_id = helper_config.get("input_id", "")

    try:
        async with get_session() as session:
            repo = ProposalRepository(session)
            proposal = await repo.create(
                name=name,
                description=description,
                trigger={},
                actions={},
                proposal_type="helper",
                service_call=helper_config,
            )
            await repo.propose(proposal.id)
            await session.commit()

            logger.info("Created helper proposal %s: %s", proposal.id, name)
            return (
                f"I've submitted a helper proposal for your approval: **{name}**\n\n"
                f"- **Type**: Helper ({helper_type})\n"
                f"- **ID**: `{input_id}`\n"
                f"- **Description**: {description}\n"
                f"- **Proposal ID**: `{proposal.id[:8]}...`\n\n"
                f"Please review and approve it on the **Proposals** page."
            )
    except Exception as e:
        logger.error("Failed to create helper proposal: %s", e)
        return f"Failed to create proposal: {e}"


def get_approval_tools() -> list:
    return [seek_approval]
