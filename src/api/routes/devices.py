"""Device API routes."""

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.devices import DeviceListResponse, DeviceResponse
from src.dal.devices import DeviceRepository
from src.storage import get_session

router = APIRouter(prefix="/devices", tags=["Devices"])


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with get_session() as session:
        yield session


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    area_id: str | None = Query(None, description="Filter by area"),
    manufacturer: str | None = Query(None, description="Filter by manufacturer"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> DeviceListResponse:
    """List all devices."""
    repo = DeviceRepository(session)
    devices = await repo.list_all(
        area_id=area_id,
        manufacturer=manufacturer,
        limit=limit,
        offset=offset,
    )
    total = await repo.count()

    return DeviceListResponse(
        devices=[DeviceResponse.model_validate(d) for d in devices],
        total=total,
    )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    session: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """Get a specific device."""
    repo = DeviceRepository(session)
    device = await repo.get_by_ha_device_id(device_id)

    if not device:
        device = await repo.get_by_id(device_id)

    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    return DeviceResponse.model_validate(device)
