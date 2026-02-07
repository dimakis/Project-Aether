"""Proposal API routes for automation approval workflow.

User Story 2: HITL approval for automation proposals.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

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
from src.storage.entities import ProposalStatus, ProposalType

router = APIRouter(prefix="/proposals", tags=["Proposals"])


def _proposal_to_response(p) -> ProposalResponse:
    """Convert an AutomationProposal model to a ProposalResponse schema."""
    return ProposalResponse(
        id=p.id,
        proposal_type=p.proposal_type if isinstance(p.proposal_type, str) else (p.proposal_type.value if hasattr(p.proposal_type, "value") else "automation"),
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
            try:
                status_filter = ProposalStatus(status.lower())
            except ValueError:
                pass

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
    """Create a new proposal."""
    async with get_session() as session:
        repo = ProposalRepository(session)

        proposal = await repo.create(
            name=body.name,
            trigger=body.trigger if isinstance(body.trigger, dict) else {"triggers": body.trigger},
            actions=body.actions if isinstance(body.actions, dict) else {"actions": body.actions},
            description=body.description,
            conditions=body.conditions,
            mode=body.mode,
            proposal_type=body.proposal_type,
            service_call=body.service_call,
        )

        # Submit for approval
        await repo.propose(proposal.id)
        await session.commit()

        # Refresh
        proposal = await repo.get_by_id(proposal.id)

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
async def approve_proposal(
    proposal_id: str,
    request: ApprovalRequest,
) -> ProposalResponse:
    """Approve a proposal."""
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

        await repo.approve(proposal_id, request.approved_by)
        await session.commit()

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
async def reject_proposal(
    proposal_id: str,
    request: RejectionRequest,
) -> ProposalResponse:
    """Reject a proposal."""
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

        await repo.reject(proposal_id, request.reason)
        await session.commit()

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
                deployed_at=datetime.now(timezone.utc) if deploy_success else None,
                error=deploy_error,
            )

        except Exception as e:
            from src.api.utils import sanitize_error

            return DeploymentResponse(
                success=False,
                proposal_id=proposal_id,
                ha_automation_id=None,
                method="failed",
                yaml_content=_generate_yaml(proposal),
                instructions=None,
                deployed_at=None,
                error=sanitize_error(e, context="Deploy proposal"),
            )


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
                success=result.get("rolled_back", False),
                proposal_id=proposal_id,
                ha_automation_id=result.get("ha_automation_id"),
                ha_disabled=result.get("ha_disabled", False),
                ha_error=result.get("ha_error"),
                rolled_back_at=datetime.now(timezone.utc),
                note=result.get("note"),
            )

        except Exception as e:
            from src.api.utils import sanitize_error

            raise HTTPException(
                status_code=500,
                detail=sanitize_error(e, context="Rollback proposal"),
            )


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


async def _deploy_entity_command(proposal, repo: ProposalRepository) -> dict:
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
    yaml_content = yaml_lib.dump(proposal.to_ha_yaml_dict(), default_flow_style=False, sort_keys=False)

    return {
        "ha_automation_id": command_id,
        "deployment_method": "mcp_service_call",
        "yaml_content": yaml_content,
        "instructions": f"Executed {domain}.{service} on {entity_id or 'target'}",
    }


def _generate_yaml(proposal) -> str:
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
