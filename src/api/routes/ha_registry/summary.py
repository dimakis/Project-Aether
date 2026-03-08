"""Registry summary endpoint."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import HARegistrySummary
from src.dal import (
    AutomationRepository,
    SceneRepository,
    ScriptRepository,
    ServiceRepository,
)
from src.storage.entities import DiscoverySession, DiscoveryStatus

from ._common import get_db

router = APIRouter(tags=["HA Registry"])


@router.get("/summary", response_model=HARegistrySummary)
async def get_registry_summary(
    session: AsyncSession = Depends(get_db),
) -> HARegistrySummary:
    """Get a summary of the HA registry.

    Provides counts and status of automations, scripts, scenes, and services.

    Args:
        session: Database session

    Returns:
        Registry summary with HA gaps
    """
    automation_repo = AutomationRepository(session)
    script_repo = ScriptRepository(session)
    scene_repo = SceneRepository(session)
    service_repo = ServiceRepository(session)

    automations_count = await automation_repo.count()
    automations_enabled = await automation_repo.count(state="on")
    scripts_count = await script_repo.count()
    scenes_count = await scene_repo.count()
    services_count = await service_repo.count()

    # Count seeded services
    services = await service_repo.list_all()
    seeded_count = sum(1 for s in services if s.is_seeded)

    # Known HA gaps
    mcp_gaps = [
        "list_devices: No device registry access",
        "list_areas: No area registry access",
        "list_services: Service list limited to seeded+discovered",
        "get_script_config: Script sequences unavailable",
        "get_scene_config: Scene entity states unavailable",
        "list_floors: Floor hierarchy unavailable",
    ]

    # Get last sync time from most recent completed discovery session
    result = await session.execute(
        select(DiscoverySession.completed_at)
        .where(DiscoverySession.status == DiscoveryStatus.COMPLETED)
        .order_by(DiscoverySession.completed_at.desc())
        .limit(1)
    )
    last_synced_at = result.scalar_one_or_none()

    # Count helpers from HA (live)
    helpers_count = 0
    try:
        from src.ha import get_ha_client_async

        ha = await get_ha_client_async()
        helpers_list = await ha.list_helpers()
        helpers_count = len(helpers_list)
    except Exception:
        logging.getLogger(__name__).warning("Failed to fetch helpers count", exc_info=True)

    return HARegistrySummary(
        automations_count=automations_count,
        automations_enabled=automations_enabled,
        scripts_count=scripts_count,
        scenes_count=scenes_count,
        services_count=services_count,
        services_seeded=seeded_count,
        helpers_count=helpers_count,
        last_synced_at=last_synced_at,
        mcp_gaps=mcp_gaps,
    )
