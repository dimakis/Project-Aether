"""Registry sync endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rate_limit import limiter
from src.dal.sync import run_registry_sync

from ._common import get_db

router = APIRouter(tags=["HA Registry"])


class RegistrySyncResponse(BaseModel):
    """Response from registry sync."""

    automations_synced: int = Field(description="Number of automations synced")
    scripts_synced: int = Field(description="Number of scripts synced")
    scenes_synced: int = Field(description="Number of scenes synced")
    duration_seconds: float = Field(description="Sync duration in seconds")


@router.post("/sync", response_model=RegistrySyncResponse)
@limiter.limit("5/minute")
async def sync_registry(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> RegistrySyncResponse:
    """Sync automations, scripts, and scenes from Home Assistant.

    Lightweight sync that only populates registry tables (skips
    areas, devices, and entities). Rate limited to 5/minute.
    """
    try:
        result = await run_registry_sync(session=session)
        return RegistrySyncResponse(**result)
    except Exception as e:
        from src.api.utils import sanitize_error

        raise HTTPException(
            status_code=500,
            detail=sanitize_error(e, context="Registry sync"),
        ) from e
