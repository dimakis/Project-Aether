"""Approval tools for the Architect agent.

Provides the seek_approval tool that routes all mutating actions
(entity commands, automations, scripts, scenes) through the
Proposals page for HITL review before execution.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml
from langchain_core.tools import tool
from sqlalchemy.exc import SQLAlchemyError

from src.dal import ProposalRepository
from src.schema import validate_yaml, validate_yaml_semantic
from src.storage import get_session
from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)

VALID_ACTION_TYPES = {"entity_command", "automation", "script", "scene", "dashboard", "helper"}

PROPOSAL_TYPE_TO_SCHEMA: dict[str, str] = {
    "entity_command": "ha.entity_command",
    "automation": "ha.automation",
    "script": "ha.script",
    "scene": "ha.scene",
    "dashboard": "ha.dashboard",
    "helper": "ha.helper",
}


async def _validate_before_create(
    proposal_type: str,
    config: dict[str, Any],
    name: str,
) -> str | None:
    """Structurally and semantically validate a proposal config before persisting it.

    Runs structural validation first. If that passes, attempts semantic
    validation against the live HA registry (entity existence, service
    validity). Semantic validation is best-effort: if the HA client is
    unreachable, it is silently skipped.

    Returns an error string for the LLM on failure, or None on success.
    """
    schema_name = PROPOSAL_TYPE_TO_SCHEMA.get(proposal_type)
    if not schema_name:
        return None

    yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
    result = validate_yaml(yaml_content, schema_name)

    if not result.valid:
        return _format_validation_errors(proposal_type, name, result)

    try:
        from src.ha import get_ha_client_async

        ha_client = await get_ha_client_async()
        semantic_result = await validate_yaml_semantic(
            yaml_content, schema_name, ha_client=ha_client
        )
        if not semantic_result.valid:
            return _format_validation_errors(proposal_type, name, semantic_result)
    except Exception:
        logger.debug(
            "Semantic validation skipped for %s '%s' (HA unavailable)",
            proposal_type,
            name,
        )

    return None


def _format_validation_errors(
    proposal_type: str,
    name: str,
    result: Any,
) -> str:
    """Format validation errors into a string the LLM can act on."""
    error_lines = [
        f"- {e.path}: {e.message}" if e.path else f"- {e.message}" for e in result.errors
    ]
    return (
        f"Validation failed for {proposal_type} '{name}'.\n\n"
        f"**Errors:**\n" + "\n".join(error_lines) + "\n\n"
        "Please fix the issues and call seek_approval again."
    )


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

    service_call: dict[str, Any] = {
        "domain": service_domain,
        "service": service_action,
        "entity_id": entity_id,
    }
    if service_data:
        service_call["data"] = service_data

    validation_error = await _validate_before_create("entity_command", service_call, name)
    if validation_error:
        return validation_error

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
    except SQLAlchemyError as e:
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
    # If yaml_content provided, validate structurally then extract fields
    if yaml_content:
        validation_result = validate_yaml(yaml_content, "ha.automation")
        if not validation_result.valid:
            error_lines = [
                f"- {e.path}: {e.message}" if e.path else f"- {e.message}"
                for e in validation_result.errors
            ]
            return (
                f"Validation failed for automation '{name}'.\n\n"
                f"**Errors:**\n" + "\n".join(error_lines) + "\n\n"
                "Please fix the issues and call seek_approval again."
            )

        from src.schema import parse_ha_yaml

        parsed, _parse_errors = parse_ha_yaml(yaml_content)
        if not _parse_errors:
            trigger = trigger or parsed.get("trigger", {})
            actions = actions or parsed.get("action", {})
            conditions = conditions or parsed.get("condition")
            mode = parsed.get("mode", mode)

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

    # Validate the assembled config (only when not already validated via yaml_content)
    if not yaml_content:
        auto_config: dict[str, Any] = {"trigger": trigger, "action": actions, "mode": mode}
        if conditions:
            auto_config["condition"] = conditions
        validation_error = await _validate_before_create("automation", auto_config, name)
        if validation_error:
            return validation_error

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
    except SQLAlchemyError as e:
        logger.error("Failed to create automation proposal: %s", e)
        return f"Failed to create proposal: {e}"


async def _create_script_proposal(
    name: str,
    description: str,
    actions: dict | list | None,
    mode: str,
    original_yaml: str | None = None,
) -> str:
    if not actions:
        return (
            "actions is required for script proposals. Please provide the full "
            f"action sequence for '{name}' and call seek_approval again."
        )

    script_config: dict[str, Any] = {
        "alias": name,
        "sequence": actions if isinstance(actions, list) else [actions],
        "mode": mode,
    }
    validation_error = await _validate_before_create("script", script_config, name)
    if validation_error:
        return validation_error

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
    except SQLAlchemyError as e:
        logger.error("Failed to create script proposal: %s", e)
        return f"Failed to create proposal: {e}"


async def _create_scene_proposal(
    name: str,
    description: str,
    actions: dict | list | None,
    original_yaml: str | None = None,
) -> str:
    scene_config: dict[str, Any] = {"name": name, "entities": actions or {}}
    validation_error = await _validate_before_create("scene", scene_config, name)
    if validation_error:
        return validation_error

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
    except SQLAlchemyError as e:
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

    validation_error = await _validate_before_create("dashboard", dashboard_config, name)
    if validation_error:
        return validation_error

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
    except SQLAlchemyError as e:
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

    validation_error = await _validate_before_create("helper", helper_config, name)
    if validation_error:
        return validation_error

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
    except SQLAlchemyError as e:
        logger.error("Failed to create helper proposal: %s", e)
        return f"Failed to create proposal: {e}"


def get_approval_tools() -> list:
    return [seek_approval]
