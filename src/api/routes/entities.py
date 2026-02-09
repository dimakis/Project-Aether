"""Entity API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rate_limit import limiter
from src.api.schemas.entities import (
    EntityListResponse,
    EntityQueryRequest,
    EntityQueryResult,
    EntityResponse,
    EntitySyncRequest,
    EntitySyncResponse,
)
from src.dal.entities import EntityRepository
from src.dal.sync import run_discovery
from src.storage import get_session

router = APIRouter(prefix="/entities", tags=["Entities"])


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with get_session() as session:
        yield session


@router.get("", response_model=EntityListResponse)
async def list_entities(
    domain: str | None = Query(None, description="Filter by domain"),
    area_id: str | None = Query(None, description="Filter by area"),
    state: str | None = Query(None, description="Filter by state"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> EntityListResponse:
    """List all entities with optional filtering."""
    repo = EntityRepository(session)
    entities = await repo.list_all(
        domain=domain,
        area_id=area_id,
        state=state,
        limit=limit,
        offset=offset,
    )
    total = await repo.count(domain=domain)

    return EntityListResponse(
        entities=[EntityResponse.model_validate(e) for e in entities],
        total=total,
        domain=domain,
    )


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    session: AsyncSession = Depends(get_db),
) -> EntityResponse:
    """Get a specific entity by HA entity_id."""
    repo = EntityRepository(session)
    entity = await repo.get_by_entity_id(entity_id)

    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    return EntityResponse.model_validate(entity)


@router.post("/query", response_model=EntityQueryResult)
@limiter.limit("10/minute")
async def query_entities(
    request: Request,
    data: EntityQueryRequest,
    session: AsyncSession = Depends(get_db),
) -> EntityQueryResult:
    """Query entities using natural language.

    Rate limited to 10/minute (LLM-backed).

    Examples:
    - "all lights in the living room"
    - "temperature sensors"
    - "devices that are on"
    """
    repo = EntityRepository(session)

    # Simple search for now - would use LLM for NL parsing
    entities = await repo.search(data.query, limit=data.limit)

    return EntityQueryResult(
        entities=[EntityResponse.model_validate(e) for e in entities],
        query=data.query,
        interpreted_as=f"Search for '{data.query}'",
    )


@router.post("/sync", response_model=EntitySyncResponse)
@limiter.limit("5/minute")
async def sync_entities(
    request: Request,
    data: EntitySyncRequest,
    session: AsyncSession = Depends(get_db),
) -> EntitySyncResponse:
    """Trigger entity discovery and sync from Home Assistant.

    Rate limited to 5/minute (expensive MCP + DB operation).
    """
    try:
        discovery = await run_discovery(
            session=session,
            triggered_by="api",
        )

        return EntitySyncResponse(
            session_id=discovery.id,
            status=discovery.status,
            entities_found=discovery.entities_found,
            entities_added=discovery.entities_added,
            entities_updated=discovery.entities_updated,
            entities_removed=discovery.entities_removed,
            duration_seconds=discovery.duration_seconds,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Discovery failed: {e!s}",
        ) from e


@router.get("/domains/summary")
async def get_domain_summary(
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Get entity count per domain."""
    repo = EntityRepository(session)
    return await repo.get_domain_counts()
