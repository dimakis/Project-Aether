"""Proposal API routes for automation approval workflow.

User Story 2: HITL approval for automation proposals.
"""

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

from src.api.rate_limit import limiter
from src.api.schemas import (
    ApprovalRequest,
    DeploymentRequest,
    DeploymentResponse,
    ErrorResponse,
    ProposalCreate,
    ProposalListResponse,
    ProposalResponse,
    ProposalYAMLResponse,
    RejectionRequest,
    RollbackRequest,
    RollbackResponse,
)
from src.dal import ProposalRepository
from src.ha import get_ha_client
from src.storage import get_session
from src.storage.entities import AutomationProposal, ProposalStatus, ProposalType

router = APIRouter(prefix="/proposals", tags=["Proposals"])


def _proposal_to_response(p: AutomationProposal) -> ProposalResponse:
    """Convert an AutomationProposal model to a ProposalResponse schema."""
    return ProposalResponse(
        id=p.id,
        proposal_type=p.proposal_type
        if isinstance(p.proposal_type, str)
        else (p.proposal_type.value if hasattr(p.proposal_type, "value") else "automation"),
        conversation_id=p.conversation_id,
        name=p.name,
        description=p.description,
        trigger=p.trigger,
        conditions=p.conditions,
        actions=p.actions,
        mode=p.mode,
        service_call=p.service_call,
        status=p.status.value,
        ha_automation_id=p.ha_automation_id,
        proposed_at=p.proposed_at,
        approved_at=p.approved_at,
        approved_by=p.approved_by,
        deployed_at=p.deployed_at,
        rolled_back_at=p.rolled_back_at,
        rejection_reason=p.rejection_reason,
        created_at=p.created_at,
        updated_at=p.updated_at,
        # Review fields (Feature 28: Smart Config Review)
        original_yaml=p.original_yaml,
        review_notes=p.review_notes,
        review_session_id=p.review_session_id,
        parent_proposal_id=p.parent_proposal_id,
        # Dashboard fields
        dashboard_config=p.dashboard_config,
    )


@router.get(
    "",
    response_model=ProposalListResponse,
    summary="List proposals",
    description="List automation proposals with optional status filter.",
)
async def list_proposals(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ProposalListResponse:
    """List all proposals."""
    async with get_session() as session:
        repo = ProposalRepository(session)

        # Parse status filter
        status_filter = None
        if status:
            with contextlib.suppress(ValueError):
                status_filter = ProposalStatus(status.lower())

        if status_filter:
            proposals = await repo.list_by_status(status_filter, limit=limit)
        else:
            # Get all proposals (combine multiple statuses)
            proposals = []
            for s in ProposalStatus:
                proposals.extend(await repo.list_by_status(s, limit=limit))
            proposals = sorted(proposals, key=lambda p: p.created_at, reverse=True)[:limit]

        total = await repo.count(status=status_filter)

        return ProposalListResponse(
            items=[_proposal_to_response(p) for p in proposals],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get(
    "/pending",
    response_model=ProposalListResponse,
    summary="List pending proposals",
    description="List proposals awaiting approval.",
)
async def list_pending_proposals(limit: int = 50) -> ProposalListResponse:
    """List proposals pending approval."""
    async with get_session() as session:
        repo = ProposalRepository(session)
        proposals = await repo.list_pending_approval(limit=limit)
        total = await repo.count(status=ProposalStatus.PROPOSED)

        return ProposalListResponse(
            items=[_proposal_to_response(p) for p in proposals],
            total=total,
            limit=limit,
            offset=0,
        )


@router.get(
    "/{proposal_id}",
    response_model=ProposalYAMLResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get proposal details",
    description="Get a proposal with its YAML content.",
)
async def get_proposal(proposal_id: str) -> ProposalYAMLResponse:
    """Get proposal by ID."""
    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # Generate YAML
        yaml_content = _generate_yaml(proposal)

        base = _proposal_to_response(proposal)
        return ProposalYAMLResponse(
            **base.model_dump(),
            yaml_content=yaml_content,
        )


@router.post(
    "",
    response_model=ProposalResponse,
    summary="Create proposal",
    description="Create a new automation proposal directly (without conversation).",
)
@limiter.limit("10/minute")
async def create_proposal(request: Request, body: ProposalCreate) -> ProposalResponse:
    """Create a new proposal.

    When ``yaml_content`` is provided, the server parses, normalizes,
    and extracts trigger/action/condition/mode/name from the YAML using
    the canonical schema pipeline.  Explicit body fields override
    extracted values.
    """
    # ── Parse yaml_content if provided ──────────────────────────────
    name = body.name
    trigger: dict | list = body.trigger
    actions: dict | list = body.actions
    conditions = body.conditions
    mode = body.mode
    proposal_type = body.proposal_type

    if body.yaml_content:
        from src.schema import detect_proposal_type, parse_ha_yaml

        data, errors = parse_ha_yaml(body.yaml_content)
        if errors:
            raise HTTPException(
                status_code=422,
                detail=[str(e) for e in errors],
            )
        # Extract fields; explicit body values take precedence
        name = name or data.get("alias") or data.get("name") or "Proposal from YAML"
        trigger = trigger or data.get("trigger", {})
        actions = actions or data.get("action", data.get("sequence", {}))
        conditions = conditions or data.get("condition")
        mode = mode if mode != "single" else data.get("mode", "single")
        proposal_type = (
            proposal_type if proposal_type != "automation" else detect_proposal_type(data)
        )

    if not name:
        name = "Untitled Proposal"

    async with get_session() as session:
        repo = ProposalRepository(session)

        proposal = await repo.create(
            name=name,
            trigger=trigger if isinstance(trigger, dict) else {"triggers": trigger},
            actions=actions if isinstance(actions, dict) else {"actions": actions},
            description=body.description,
            conditions=cast("dict[str, Any] | None", conditions)
            if isinstance(conditions, dict)
            else conditions,
            mode=mode,
            proposal_type=proposal_type,
            service_call=body.service_call,
            dashboard_config=body.dashboard_config,
        )

        # Submit for approval
        await repo.propose(proposal.id)
        await session.commit()

        # Refresh
        proposal = await repo.get_by_id(proposal.id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Proposal not found")

        return _proposal_to_response(proposal)


@router.post(
    "/{proposal_id}/approve",
    response_model=ProposalResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
    summary="Approve proposal",
    description="Approve a pending automation proposal.",
)
@limiter.limit("5/minute")
async def approve_proposal(
    request: Request,
    proposal_id: str,
    data: ApprovalRequest,
) -> ProposalResponse:
    """Approve a proposal.

    When trace_id is provided, logs the approval as ground-truth feedback
    and an expectation to MLflow's assessment system.
    """
    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal.status != ProposalStatus.PROPOSED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve proposal in status {proposal.status.value}",
            )

        await repo.approve(proposal_id, data.approved_by)
        await session.commit()

        # Bridge approval to MLflow 3.x assessment system (best-effort)
        _log_proposal_assessment(
            trace_id=data.trace_id,
            proposal_name=proposal.name,
            outcome="approved",
            rationale=data.comment,
            source_id=data.approved_by,
        )

        proposal = await repo.get_by_id(proposal_id)

        return _proposal_to_response(proposal)


@router.post(
    "/{proposal_id}/reject",
    response_model=ProposalResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
    summary="Reject proposal",
    description="Reject a pending automation proposal.",
)
@limiter.limit("5/minute")
async def reject_proposal(
    request: Request,
    proposal_id: str,
    data: RejectionRequest,
) -> ProposalResponse:
    """Reject a proposal.

    When trace_id is provided, logs the rejection as ground-truth feedback
    and an expectation to MLflow's assessment system.
    """
    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal.status not in (ProposalStatus.PROPOSED, ProposalStatus.APPROVED):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject proposal in status {proposal.status.value}",
            )

        await repo.reject(proposal_id, data.reason)
        await session.commit()

        # Bridge rejection to MLflow 3.x assessment system (best-effort)
        _log_proposal_assessment(
            trace_id=data.trace_id,
            proposal_name=proposal.name,
            outcome="rejected",
            rationale=data.reason,
            source_id=data.rejected_by,
        )

        proposal = await repo.get_by_id(proposal_id)

        return _proposal_to_response(proposal)


@router.post(
    "/{proposal_id}/deploy",
    response_model=DeploymentResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
    summary="Deploy proposal",
    description="Deploy an approved automation to Home Assistant.",
)
@limiter.limit("5/minute")
async def deploy_proposal(
    request: Request,
    proposal_id: str,
    deploy_data: DeploymentRequest | None = None,
) -> DeploymentResponse:
    """Deploy an approved proposal.

    Rate limited to 5/minute (critical HA state change).
    """
    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        force = deploy_data.force if deploy_data else False

        if proposal.status == ProposalStatus.DEPLOYED and not force:
            raise HTTPException(
                status_code=400,
                detail="Proposal already deployed. Use force=true to redeploy.",
            )

        if proposal.status not in (ProposalStatus.APPROVED, ProposalStatus.DEPLOYED):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot deploy proposal in status {proposal.status.value}. Must be approved first.",
            )

        # Dispatch based on proposal type
        try:
            if proposal.proposal_type == ProposalType.ENTITY_COMMAND.value:
                result = await _deploy_entity_command(proposal, repo)
            elif proposal.proposal_type == ProposalType.DASHBOARD.value:
                result = await _deploy_dashboard(proposal, repo)
            elif proposal.proposal_type == ProposalType.HELPER.value:
                result = await _deploy_helper(proposal, repo)
            else:
                # Deploy via Developer agent (automations, scripts, scenes)
                from src.agents import DeveloperWorkflow

                workflow = DeveloperWorkflow()
                result = await workflow.deploy(proposal_id, session)

            await session.commit()

            # Check if deployment actually succeeded
            deploy_error = result.get("error")
            deploy_success = not deploy_error and result.get("ha_automation_id") is not None

            return DeploymentResponse(
                success=deploy_success,
                proposal_id=proposal_id,
                ha_automation_id=result.get("ha_automation_id"),
                method=result.get("deployment_method", "manual"),
                yaml_content=result.get("yaml_content", ""),
                instructions=result.get("instructions"),
                deployed_at=datetime.now(UTC) if deploy_success else None,
                error=deploy_error,
            )

        except Exception as e:
            from src.api.utils import sanitize_error

            raise HTTPException(
                status_code=500,
                detail=sanitize_error(e, context="Deploy proposal"),
            ) from e


@router.post(
    "/{proposal_id}/rollback",
    response_model=RollbackResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
    summary="Rollback proposal",
    description="Rollback a deployed automation from Home Assistant.",
)
@limiter.limit("5/minute")
async def rollback_proposal(
    request: Request,
    proposal_id: str,
    rollback_data: RollbackRequest | None = None,
) -> RollbackResponse:
    """Rollback a deployed proposal.

    Rate limited to 5/minute (critical HA state change).
    """
    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal.status != ProposalStatus.DEPLOYED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot rollback proposal in status {proposal.status.value}. Must be deployed.",
            )

        # Rollback via Developer agent
        from src.agents import DeveloperWorkflow

        workflow = DeveloperWorkflow()

        try:
            result = await workflow.rollback(proposal_id, session)
            await session.commit()

            return RollbackResponse(
                success=cast("bool", result.get("rolled_back", False)),
                proposal_id=proposal_id,
                ha_automation_id=cast("str | None", result.get("ha_automation_id")),
                ha_disabled=cast("bool", result.get("ha_disabled", False)),
                ha_error=cast("str | None", result.get("ha_error")),
                rolled_back_at=datetime.now(UTC),
                note=cast("str | None", result.get("note")),
            )

        except Exception as e:
            from src.api.utils import sanitize_error

            raise HTTPException(
                status_code=500,
                detail=sanitize_error(e, context="Rollback proposal"),
            ) from e


@router.delete(
    "/{proposal_id}",
    status_code=204,
    summary="Delete proposal",
    description="Delete a proposal. Cannot delete deployed proposals (rollback first).",
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def delete_proposal(proposal_id: str) -> None:
    """Delete a proposal."""
    async with get_session() as session:
        repo = ProposalRepository(session)
        proposal = await repo.get_by_id(proposal_id)

        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if proposal.status == ProposalStatus.DEPLOYED:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete a deployed proposal. Rollback first.",
            )

        deleted = await repo.delete(proposal_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Proposal not found")

        await session.commit()


def _log_proposal_assessment(
    trace_id: str | None,
    proposal_name: str,
    outcome: str,
    rationale: str | None,
    source_id: str,
) -> None:
    """Log a proposal approval/rejection to MLflow's assessment system.

    Records both feedback (the human decision) and an expectation
    (the ground-truth outcome) on the originating trace.

    Args:
        trace_id: MLflow trace ID (skips logging if None)
        proposal_name: Name of the proposal for context
        outcome: "approved" or "rejected"
        rationale: Human-provided reason for the decision
        source_id: Who made the decision
    """
    if not trace_id:
        return

    from src.tracing import log_expectation, log_human_feedback

    log_human_feedback(
        trace_id=trace_id,
        name="proposal_decision",
        value=outcome,
        source_id=source_id,
        rationale=rationale or f"Proposal '{proposal_name}' {outcome}",
    )

    log_expectation(
        trace_id=trace_id,
        name="expected_proposal_outcome",
        value={
            "proposal_name": proposal_name,
            "expected_outcome": outcome,
            "rationale": rationale,
        },
        source_id=source_id,
    )


async def _deploy_entity_command(
    proposal: AutomationProposal, repo: ProposalRepository
) -> dict[str, Any]:
    """Execute an entity command proposal via MCP.

    Args:
        proposal: The AutomationProposal with proposal_type=entity_command
        repo: ProposalRepository for state updates

    Returns:
        Deployment result dict
    """
    sc = proposal.service_call or {}
    domain = sc.get("domain", "homeassistant")
    service = sc.get("service", "turn_on")
    entity_id = sc.get("entity_id")
    data = sc.get("data", {})

    if entity_id:
        data["entity_id"] = entity_id

    ha = get_ha_client()
    await ha.call_service(domain=domain, service=service, data=data)

    # Mark as deployed (use a descriptive ID since there's no HA automation)
    command_id = f"cmd_{proposal.id[:8]}_{domain}_{service}"
    await repo.deploy(proposal.id, command_id)

    import yaml as yaml_lib

    yaml_content = yaml_lib.dump(
        proposal.to_ha_yaml_dict(), default_flow_style=False, sort_keys=False
    )

    return {
        "ha_automation_id": command_id,
        "deployment_method": "mcp_service_call",
        "yaml_content": yaml_content,
        "instructions": f"Executed {domain}.{service} on {entity_id or 'target'}",
    }


async def _deploy_dashboard(
    proposal: AutomationProposal, repo: ProposalRepository
) -> dict[str, Any]:
    """Deploy a dashboard proposal via WebSocket lovelace/config/save.

    Args:
        proposal: The AutomationProposal with proposal_type=dashboard
        repo: ProposalRepository for state updates

    Returns:
        Deployment result dict
    """
    config = proposal.dashboard_config or {}
    url_path = (proposal.service_call or {}).get("url_path")

    ha = get_ha_client()

    # Snapshot current config before overwriting (enables rollback)
    try:
        current_config = await ha.get_dashboard_config(url_path)
        if current_config is not None:
            proposal.previous_dashboard_config = current_config
    except Exception:
        logger.warning(
            "Failed to snapshot current dashboard config for '%s' before deploy; "
            "rollback will not be available.",
            url_path or "default",
        )

    await ha.save_dashboard_config(url_path, config)

    # Mark as deployed
    deploy_id = f"dash_{proposal.id[:8]}_{url_path or 'default'}"
    await repo.deploy(proposal.id, deploy_id)

    import yaml as yaml_lib

    yaml_content = yaml_lib.dump(config, default_flow_style=False, sort_keys=False)

    return {
        "ha_automation_id": deploy_id,
        "deployment_method": "ws_lovelace_save",
        "yaml_content": yaml_content,
        "instructions": f"Deployed Lovelace config to dashboard '{url_path or 'default'}'",
    }


_HELPER_DISPATCH: dict[str, str] = {
    "input_boolean": "create_input_boolean",
    "input_number": "create_input_number",
    "input_text": "create_input_text",
    "input_select": "create_input_select",
    "input_datetime": "create_input_datetime",
    "input_button": "create_input_button",
    "counter": "create_counter",
    "timer": "create_timer",
}

# Keys that are metadata, not HA client kwargs
_HELPER_META_KEYS = {"helper_type"}


async def _deploy_helper(proposal: AutomationProposal, repo: ProposalRepository) -> dict[str, Any]:
    """Deploy a helper proposal by calling the HA create_* method.

    Args:
        proposal: The AutomationProposal with proposal_type=helper and
                  helper config stored in service_call.
        repo: ProposalRepository for state updates.

    Returns:
        Deployment result dict.
    """
    config = proposal.service_call or {}
    helper_type = config.get("helper_type", "")
    method_name = _HELPER_DISPATCH.get(helper_type)

    if not method_name:
        return {
            "ha_automation_id": None,
            "deployment_method": "ha_helper_create",
            "yaml_content": "",
            "error": f"Unknown helper type: {helper_type}",
        }

    ha = get_ha_client()
    method = getattr(ha, method_name)

    # Build kwargs from config, excluding metadata keys
    kwargs = {k: v for k, v in config.items() if k not in _HELPER_META_KEYS}
    result = await method(**kwargs)

    entity_id = result.get("entity_id", "")
    deploy_id = entity_id or f"helper_{proposal.id[:8]}_{helper_type}"
    await repo.deploy(proposal.id, deploy_id)

    import yaml as yaml_lib

    yaml_content = yaml_lib.dump(config, default_flow_style=False, sort_keys=False)

    return {
        "ha_automation_id": deploy_id,
        "deployment_method": "ha_helper_create",
        "yaml_content": yaml_content,
        "instructions": f"Created {helper_type} helper: {entity_id}",
    }


def _generate_yaml(proposal: AutomationProposal) -> str:
    """Generate YAML content for a proposal.

    Args:
        proposal: AutomationProposal instance

    Returns:
        YAML string
    """
    import yaml

    automation = proposal.to_ha_yaml_dict()

    header = f"""# Project Aether Automation
# Proposal ID: {proposal.id}
# Status: {proposal.status.value}
# ---
"""
    return header + yaml.dump(automation, default_flow_style=False, sort_keys=False)
