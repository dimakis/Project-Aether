"""Area API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.schemas.areas import AreaListResponse, AreaResponse
from src.dal.areas import AreaRepository

router = APIRouter(prefix="/areas", tags=["Areas"])


@router.get("", response_model=AreaListResponse)
async def list_areas(
    floor_id: str | None = Query(None, description="Filter by floor"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> AreaListResponse:
    """List all areas."""
    repo = AreaRepository(session)
    areas = await repo.list_all(floor_id=floor_id, limit=limit, offset=offset)
    total = await repo.count()

    return AreaListResponse(
        areas=[AreaResponse.model_validate(a) for a in areas],
        total=total,
    )


@router.get("/{area_id}", response_model=AreaResponse)
async def get_area(
    area_id: str,
    session: AsyncSession = Depends(get_db),
) -> AreaResponse:
    """Get a specific area."""
    repo = AreaRepository(session)
    area = await repo.get_by_ha_area_id(area_id)

    if not area:
        # Try by internal ID
        area = await repo.get_by_id(area_id)

    if not area:
        raise HTTPException(status_code=404, detail=f"Area {area_id} not found")

    return AreaResponse.model_validate(area)
