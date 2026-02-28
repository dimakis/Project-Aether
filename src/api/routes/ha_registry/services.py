"""Service registry endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rate_limit import limiter
from src.api.schemas import (
    ServiceCallRequest,
    ServiceCallResponse,
    ServiceListResponse,
    ServiceResponse,
)
from src.dal import ServiceRepository

from ._common import _is_valid_uuid, get_db

router = APIRouter(tags=["HA Registry"])


@router.get("/services", response_model=ServiceListResponse)
async def list_services(
    domain: str | None = None,
    limit: int = 500,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
) -> ServiceListResponse:
    """List all services.

    Args:
        domain: Optional filter by domain
        limit: Maximum number of results
        offset: Number of results to skip
        session: Database session

    Returns:
        List of services with metadata
    """
    repo = ServiceRepository(session)

    services = await repo.list_all(domain=domain, limit=limit, offset=offset)
    total = await repo.count(domain=domain)
    domains = await repo.get_domains()

    # Count seeded vs discovered
    seeded = [s for s in services if s.is_seeded]
    discovered = [s for s in services if not s.is_seeded]

    return ServiceListResponse(
        services=[ServiceResponse.model_validate(s) for s in services],
        total=total,
        domains=domains,
        seeded_count=len(seeded),
        discovered_count=len(discovered),
    )


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: str,
    session: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Get a specific service.

    Args:
        service_id: Internal UUID or full service name (domain.service)
        session: Database session

    Returns:
        Service details

    Raises:
        HTTPException: If service not found
    """
    repo = ServiceRepository(session)

    # Try internal UUID first (only if value looks like a UUID)
    service = await repo.get_by_id(service_id) if _is_valid_uuid(service_id) else None

    # Try full service name
    if not service:
        service = await repo.get_service_info(service_id)

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return ServiceResponse.model_validate(service)


@router.post("/services/call", response_model=ServiceCallResponse)
@limiter.limit("10/minute")
async def call_service(
    request: Request,
    body: ServiceCallRequest,
    session: AsyncSession = Depends(get_db),
) -> ServiceCallResponse:
    """Call a Home Assistant service via MCP.

    Rate limited to 10/minute. Domain validation prevents calls to
    dangerous domains that should only go through the HITL approval flow.

    Args:
        request: FastAPI/Starlette request (for rate limiter)
        body: Service call request body
        session: Database session

    Returns:
        Service call result
    """
    from src.api.utils import sanitize_error
    from src.ha import get_ha_client_async

    # Block dangerous domains that must go through HITL approval
    BLOCKED_DOMAINS = frozenset(
        {
            "homeassistant",  # restart, stop, reload
            "persistent_notification",  # handled via notification system
            "system_log",  # log manipulation
            "recorder",  # DB manipulation
            "hassio",  # supervisor control
        }
    )
    if body.domain in BLOCKED_DOMAINS:
        raise HTTPException(
            status_code=403,
            detail=f"Domain '{body.domain}' is restricted. Use the chat interface for this operation.",
        )

    try:
        ha = await get_ha_client_async()
        await ha.call_service(
            domain=body.domain,
            service=body.service,
            data=body.data or {},
        )

        return ServiceCallResponse(
            success=True,
            domain=body.domain,
            service=body.service,
            message=f"Successfully called {body.domain}.{body.service}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=sanitize_error(e, context="Service call"),
        ) from e


@router.post("/services/seed")
@limiter.limit("5/minute")
async def seed_services(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Seed common services into the database.

    This populates the service registry with known common services
    that agents can use for automation proposals.

    Args:
        session: Database session

    Returns:
        Seeding statistics
    """
    from src.dal import seed_services

    stats = await seed_services(session)
    await session.commit()
    return stats
