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
from src.storage import get_session
from src.storage.entities import ProposalStatus

router = APIRouter(prefix="/proposals", tags=["Proposals"])


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
                status_filter = ProposalStatus(status.upper())
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
            items=[
                ProposalResponse(
                    id=p.id,
                    conversation_id=p.conversation_id,
                    name=p.name,
                    description=p.description,
                    trigger=p.trigger,
                    conditions=p.conditions,
                    actions=p.actions,
                    mode=p.mode,
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
                for p in proposals
            ],
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
            items=[
                ProposalResponse(
                    id=p.id,
                    conversation_id=p.conversation_id,
                    name=p.name,
                    description=p.description,
                    trigger=p.trigger,
                    conditions=p.conditions,
                    actions=p.actions,
                    mode=p.mode,
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
                for p in proposals
            ],
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

        return ProposalYAMLResponse(
            id=proposal.id,
            conversation_id=proposal.conversation_id,
            name=proposal.name,
            description=proposal.description,
            trigger=proposal.trigger,
            conditions=proposal.conditions,
            actions=proposal.actions,
            mode=proposal.mode,
            status=proposal.status.value,
            ha_automation_id=proposal.ha_automation_id,
            proposed_at=proposal.proposed_at,
            approved_at=proposal.approved_at,
            approved_by=proposal.approved_by,
            deployed_at=proposal.deployed_at,
            rolled_back_at=proposal.rolled_back_at,
            rejection_reason=proposal.rejection_reason,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            yaml_content=yaml_content,
        )


@router.post(
    "",
    response_model=ProposalResponse,
    summary="Create proposal",
    description="Create a new automation proposal directly (without conversation).",
)
async def create_proposal(request: ProposalCreate) -> ProposalResponse:
    """Create a new proposal."""
    async with get_session() as session:
        repo = ProposalRepository(session)

        proposal = await repo.create(
            name=request.name,
            trigger=request.trigger if isinstance(request.trigger, dict) else {"triggers": request.trigger},
            actions=request.actions if isinstance(request.actions, dict) else {"actions": request.actions},
            description=request.description,
            conditions=request.conditions,
            mode=request.mode,
        )

        # Submit for approval
        await repo.propose(proposal.id)
        await session.commit()

        # Refresh
        proposal = await repo.get_by_id(proposal.id)

        return ProposalResponse(
            id=proposal.id,
            conversation_id=proposal.conversation_id,
            name=proposal.name,
            description=proposal.description,
            trigger=proposal.trigger,
            conditions=proposal.conditions,
            actions=proposal.actions,
            mode=proposal.mode,
            status=proposal.status.value,
            ha_automation_id=proposal.ha_automation_id,
            proposed_at=proposal.proposed_at,
            approved_at=proposal.approved_at,
            approved_by=proposal.approved_by,
            deployed_at=proposal.deployed_at,
            rolled_back_at=proposal.rolled_back_at,
            rejection_reason=proposal.rejection_reason,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
        )


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

        return ProposalResponse(
            id=proposal.id,
            conversation_id=proposal.conversation_id,
            name=proposal.name,
            description=proposal.description,
            trigger=proposal.trigger,
            conditions=proposal.conditions,
            actions=proposal.actions,
            mode=proposal.mode,
            status=proposal.status.value,
            ha_automation_id=proposal.ha_automation_id,
            proposed_at=proposal.proposed_at,
            approved_at=proposal.approved_at,
            approved_by=proposal.approved_by,
            deployed_at=proposal.deployed_at,
            rolled_back_at=proposal.rolled_back_at,
            rejection_reason=proposal.rejection_reason,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
        )


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

        return ProposalResponse(
            id=proposal.id,
            conversation_id=proposal.conversation_id,
            name=proposal.name,
            description=proposal.description,
            trigger=proposal.trigger,
            conditions=proposal.conditions,
            actions=proposal.actions,
            mode=proposal.mode,
            status=proposal.status.value,
            ha_automation_id=proposal.ha_automation_id,
            proposed_at=proposal.proposed_at,
            approved_at=proposal.approved_at,
            approved_by=proposal.approved_by,
            deployed_at=proposal.deployed_at,
            rolled_back_at=proposal.rolled_back_at,
            rejection_reason=proposal.rejection_reason,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
        )


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

        # Deploy via Developer agent
        from src.agents import DeveloperWorkflow

        workflow = DeveloperWorkflow()

        try:
            result = await workflow.deploy(proposal_id, session)
            await session.commit()

            return DeploymentResponse(
                success=True,
                proposal_id=proposal_id,
                ha_automation_id=result.get("ha_automation_id"),
                method=result.get("deployment_method", "manual"),
                yaml_content=result.get("yaml_content", ""),
                instructions=result.get("instructions"),
                deployed_at=datetime.now(timezone.utc),
                error=None,
            )

        except Exception as e:
            return DeploymentResponse(
                success=False,
                proposal_id=proposal_id,
                ha_automation_id=None,
                method="failed",
                yaml_content=_generate_yaml(proposal),
                instructions=None,
                deployed_at=None,
                error=str(e),
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
                rolled_back_at=datetime.now(timezone.utc),
                note=result.get("note"),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


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
