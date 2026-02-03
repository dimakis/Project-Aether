"""HA Registry routes for automations, scripts, scenes, and services.

Provides endpoints for accessing Home Assistant registry data
including automations, scripts, scenes, and the service registry.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    AutomationListResponse,
    AutomationResponse,
    HARegistrySummary,
    SceneListResponse,
    SceneResponse,
    ScriptListResponse,
    ScriptResponse,
    ServiceCallRequest,
    ServiceCallResponse,
    ServiceListResponse,
    ServiceResponse,
)
from src.dal import (
    AutomationRepository,
    SceneRepository,
    ScriptRepository,
    ServiceRepository,
)
from src.storage import get_session

router = APIRouter(tags=["HA Registry"])


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with get_session() as session:
        yield session


# =============================================================================
# AUTOMATIONS
# =============================================================================


@router.get("/automations", response_model=AutomationListResponse)
async def list_automations(
    state: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
) -> AutomationListResponse:
    """List all automations.

    Args:
        state: Optional filter by state (on/off)
        limit: Maximum number of results
        offset: Number of results to skip
        session: Database session

    Returns:
        List of automations with counts
    """
    repo = AutomationRepository(session)

    automations = await repo.list_all(state=state, limit=limit, offset=offset)
    total = await repo.count()
    enabled = await repo.count(state="on")
    disabled = await repo.count(state="off")

    return AutomationListResponse(
        automations=[AutomationResponse.model_validate(a) for a in automations],
        total=total,
        enabled_count=enabled,
        disabled_count=disabled,
    )


@router.get("/automations/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: str,
    session: AsyncSession = Depends(get_db),
) -> AutomationResponse:
    """Get a specific automation.

    Args:
        automation_id: Internal UUID or HA automation ID
        session: Database session

    Returns:
        Automation details

    Raises:
        HTTPException: If automation not found
    """
    repo = AutomationRepository(session)

    # Try internal ID first
    automation = await repo.get_by_id(automation_id)

    # Try HA automation ID
    if not automation:
        automation = await repo.get_by_ha_automation_id(automation_id)

    # Try entity ID
    if not automation:
        automation = await repo.get_by_entity_id(f"automation.{automation_id}")

    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    return AutomationResponse.model_validate(automation)


# =============================================================================
# SCRIPTS
# =============================================================================


@router.get("/scripts", response_model=ScriptListResponse)
async def list_scripts(
    state: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
) -> ScriptListResponse:
    """List all scripts.

    Args:
        state: Optional filter by state
        limit: Maximum number of results
        offset: Number of results to skip
        session: Database session

    Returns:
        List of scripts with counts
    """
    repo = ScriptRepository(session)

    scripts = await repo.list_all(state=state, limit=limit, offset=offset)
    total = await repo.count()

    # Count running scripts
    running_scripts = await repo.list_all(state="on")
    running_count = len(running_scripts)

    return ScriptListResponse(
        scripts=[ScriptResponse.model_validate(s) for s in scripts],
        total=total,
        running_count=running_count,
    )


@router.get("/scripts/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: str,
    session: AsyncSession = Depends(get_db),
) -> ScriptResponse:
    """Get a specific script.

    Args:
        script_id: Internal UUID or entity ID
        session: Database session

    Returns:
        Script details

    Raises:
        HTTPException: If script not found
    """
    repo = ScriptRepository(session)

    # Try internal ID first
    script = await repo.get_by_id(script_id)

    # Try entity ID
    if not script:
        entity_id = script_id if script_id.startswith("script.") else f"script.{script_id}"
        script = await repo.get_by_entity_id(entity_id)

    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return ScriptResponse.model_validate(script)


# =============================================================================
# SCENES
# =============================================================================


@router.get("/scenes", response_model=SceneListResponse)
async def list_scenes(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
) -> SceneListResponse:
    """List all scenes.

    Args:
        limit: Maximum number of results
        offset: Number of results to skip
        session: Database session

    Returns:
        List of scenes
    """
    repo = SceneRepository(session)

    scenes = await repo.list_all(limit=limit, offset=offset)
    total = await repo.count()

    return SceneListResponse(
        scenes=[SceneResponse.model_validate(s) for s in scenes],
        total=total,
    )


@router.get("/scenes/{scene_id}", response_model=SceneResponse)
async def get_scene(
    scene_id: str,
    session: AsyncSession = Depends(get_db),
) -> SceneResponse:
    """Get a specific scene.

    Args:
        scene_id: Internal UUID or entity ID
        session: Database session

    Returns:
        Scene details

    Raises:
        HTTPException: If scene not found
    """
    repo = SceneRepository(session)

    # Try internal ID first
    scene = await repo.get_by_id(scene_id)

    # Try entity ID
    if not scene:
        entity_id = scene_id if scene_id.startswith("scene.") else f"scene.{scene_id}"
        scene = await repo.get_by_entity_id(entity_id)

    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    return SceneResponse.model_validate(scene)


# =============================================================================
# SERVICES
# =============================================================================


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

    # Try internal ID first
    service = await repo.get_by_id(service_id)

    # Try full service name
    if not service:
        service = await repo.get_service_info(service_id)

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return ServiceResponse.model_validate(service)


@router.post("/services/call", response_model=ServiceCallResponse)
async def call_service(
    request: ServiceCallRequest,
    session: AsyncSession = Depends(get_db),
) -> ServiceCallResponse:
    """Call a Home Assistant service via MCP.

    Args:
        request: Service call request
        session: Database session

    Returns:
        Service call result
    """
    from src.mcp import get_mcp_client

    try:
        mcp = get_mcp_client()
        await mcp.call_service(
            domain=request.domain,
            service=request.service,
            data=request.data or {},
        )

        return ServiceCallResponse(
            success=True,
            domain=request.domain,
            service=request.service,
            message=f"Successfully called {request.domain}.{request.service}",
        )

    except Exception as e:
        return ServiceCallResponse(
            success=False,
            domain=request.domain,
            service=request.service,
            message=f"Service call failed: {e}",
        )


@router.post("/services/seed")
async def seed_services(
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


# =============================================================================
# REGISTRY SUMMARY
# =============================================================================


@router.get("/summary", response_model=HARegistrySummary)
async def get_registry_summary(
    session: AsyncSession = Depends(get_db),
) -> HARegistrySummary:
    """Get a summary of the HA registry.

    Provides counts and status of automations, scripts, scenes, and services.

    Args:
        session: Database session

    Returns:
        Registry summary with MCP gaps
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

    # Known MCP gaps
    mcp_gaps = [
        "list_devices: No device registry access",
        "list_areas: No area registry access",
        "list_services: Service list limited to seeded+discovered",
        "get_script_config: Script sequences unavailable",
        "get_scene_config: Scene entity states unavailable",
        "list_floors: Floor hierarchy unavailable",
    ]

    return HARegistrySummary(
        automations_count=automations_count,
        automations_enabled=automations_enabled,
        scripts_count=scripts_count,
        scenes_count=scenes_count,
        services_count=services_count,
        services_seeded=seeded_count,
        last_synced_at=datetime.utcnow(),  # TODO: Get from last discovery session
        mcp_gaps=mcp_gaps,
    )
