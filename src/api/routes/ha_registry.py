"""HA Registry routes for automations, scripts, scenes, and services.

Provides endpoints for accessing Home Assistant registry data
including automations, scripts, scenes, and the service registry.
"""

import logging
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession


def _is_valid_uuid(value: str) -> bool:
    """Return True if *value* is a valid UUID string."""
    try:
        _uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


from src.api.rate_limit import limiter
from src.api.schemas import (
    AutomationListResponse,
    AutomationResponse,
    HARegistrySummary,
    HelperCreateRequest,
    HelperCreateResponse,
    HelperDeleteResponse,
    HelperListResponse,
    HelperResponse,
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
from src.dal.sync import run_registry_sync
from src.storage import get_session

router = APIRouter(tags=["HA Registry"])


class RegistrySyncResponse(BaseModel):
    """Response from registry sync."""

    automations_synced: int = Field(description="Number of automations synced")
    scripts_synced: int = Field(description="Number of scripts synced")
    scenes_synced: int = Field(description="Number of scenes synced")
    duration_seconds: float = Field(description="Sync duration in seconds")


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with get_session() as session:
        yield session


# =============================================================================
# REGISTRY SYNC
# =============================================================================


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

    # Try internal UUID first (only if value looks like a UUID)
    automation = await repo.get_by_id(automation_id) if _is_valid_uuid(automation_id) else None

    # Try HA automation ID
    if not automation:
        automation = await repo.get_by_ha_automation_id(automation_id)

    # Try entity ID
    if not automation:
        automation = await repo.get_by_entity_id(f"automation.{automation_id}")

    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    return AutomationResponse.model_validate(automation)


@router.get("/automations/{automation_id}/config")
async def get_automation_config(
    automation_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get an automation's raw YAML configuration from Home Assistant.

    Args:
        automation_id: Internal UUID, HA automation ID, or entity ID slug
        session: Database session

    Returns:
        Automation config dict from HA
    """
    import yaml as pyyaml

    from src.ha import get_ha_client

    # Resolve to HA automation ID
    repo = AutomationRepository(session)
    automation = await repo.get_by_id(automation_id) if _is_valid_uuid(automation_id) else None
    if not automation:
        automation = await repo.get_by_ha_automation_id(automation_id)
    if not automation:
        automation = await repo.get_by_entity_id(f"automation.{automation_id}")

    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    import logging

    logger = logging.getLogger(__name__)

    ha_id = automation.ha_automation_id or automation_id
    logger.debug(
        "Fetching automation config: db_id=%s, ha_automation_id=%s, entity_id=%s, resolved_ha_id=%s",
        automation.id,
        automation.ha_automation_id,
        automation.entity_id,
        ha_id,
    )

    try:
        ha = get_ha_client()
        config = await ha.get_automation_config(ha_id)

        if not config:
            # Fallback: check if config is stored in the DB entity
            if automation.config:
                logger.info("HA config API returned None; using cached DB config for %s", ha_id)
                config = automation.config
            else:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Automation config not available from Home Assistant "
                        f"(ha_id={ha_id}, entity_id={automation.entity_id}). "
                        f"Try re-syncing the registry."
                    ),
                )

        return {
            "automation_id": str(automation.id),
            "ha_automation_id": ha_id,
            "entity_id": automation.entity_id,
            "config": config,
            "yaml": pyyaml.dump(config, default_flow_style=False, sort_keys=False),
        }
    except HTTPException:
        raise
    except Exception as e:
        from src.api.utils import sanitize_error

        logger.warning(
            "Failed to fetch automation config for ha_id=%s: %s",
            ha_id,
            e,
        )
        raise HTTPException(
            status_code=502,
            detail=sanitize_error(e, context="Fetch automation config from HA"),
        ) from e


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

    # Try internal UUID first (only if value looks like a UUID)
    script = await repo.get_by_id(script_id) if _is_valid_uuid(script_id) else None

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

    # Try internal UUID first (only if value looks like a UUID)
    scene = await repo.get_by_id(scene_id) if _is_valid_uuid(scene_id) else None

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
    from src.ha import get_ha_client

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
        ha = get_ha_client()
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


# =============================================================================
# HELPERS
# =============================================================================


@router.get("/helpers", response_model=HelperListResponse)
async def list_helpers() -> HelperListResponse:
    """List all helper entities from Home Assistant.

    Returns live helper state directly from HA (not cached).

    Returns:
        List of helpers with type breakdown
    """
    from src.ha import get_ha_client

    try:
        ha = get_ha_client()
        helpers = await ha.list_helpers()

        # Build type counts
        by_type: dict[str, int] = {}
        for h in helpers:
            domain = h.get("domain", "")
            by_type[domain] = by_type.get(domain, 0) + 1

        return HelperListResponse(
            helpers=[HelperResponse(**h) for h in helpers],
            total=len(helpers),
            by_type=by_type,
        )
    except Exception as e:
        from src.api.utils import sanitize_error

        raise HTTPException(
            status_code=502,
            detail=sanitize_error(e, context="List helpers from HA"),
        ) from e


@router.post("/helpers", response_model=HelperCreateResponse)
@limiter.limit("10/minute")
async def create_helper(
    request: Request,
    body: HelperCreateRequest,
) -> HelperCreateResponse:
    """Create a helper entity in Home Assistant.

    Dispatches to the appropriate HA client method based on helper_type.
    Rate limited to 10/minute.

    Args:
        request: FastAPI/Starlette request (for rate limiter)
        body: Helper creation request

    Returns:
        Creation result
    """
    from src.ha import get_ha_client

    ha = get_ha_client()
    result: dict

    try:
        if body.helper_type == "input_boolean":
            result = await ha.create_input_boolean(
                input_id=body.input_id,
                name=body.name,
                initial=body.config.get("initial", False),
                icon=body.icon,
            )
        elif body.helper_type == "input_number":
            result = await ha.create_input_number(
                input_id=body.input_id,
                name=body.name,
                min_value=body.config.get("min", 0),
                max_value=body.config.get("max", 100),
                initial=body.config.get("initial"),
                step=body.config.get("step", 1),
                unit_of_measurement=body.config.get("unit_of_measurement"),
                mode=body.config.get("mode", "slider"),
                icon=body.icon,
            )
        elif body.helper_type == "input_text":
            result = await ha.create_input_text(
                input_id=body.input_id,
                name=body.name,
                min_length=body.config.get("min", 0),
                max_length=body.config.get("max", 100),
                pattern=body.config.get("pattern"),
                mode=body.config.get("mode", "text"),
                initial=body.config.get("initial"),
                icon=body.icon,
            )
        elif body.helper_type == "input_select":
            result = await ha.create_input_select(
                input_id=body.input_id,
                name=body.name,
                options=body.config.get("options", []),
                initial=body.config.get("initial"),
                icon=body.icon,
            )
        elif body.helper_type == "input_datetime":
            result = await ha.create_input_datetime(
                input_id=body.input_id,
                name=body.name,
                has_date=body.config.get("has_date", True),
                has_time=body.config.get("has_time", True),
                initial=body.config.get("initial"),
                icon=body.icon,
            )
        elif body.helper_type == "input_button":
            result = await ha.create_input_button(
                input_id=body.input_id,
                name=body.name,
                icon=body.icon,
            )
        elif body.helper_type == "counter":
            result = await ha.create_counter(
                input_id=body.input_id,
                name=body.name,
                initial=body.config.get("initial", 0),
                minimum=body.config.get("minimum"),
                maximum=body.config.get("maximum"),
                step=body.config.get("step", 1),
                restore=body.config.get("restore", True),
                icon=body.icon,
            )
        elif body.helper_type == "timer":
            result = await ha.create_timer(
                input_id=body.input_id,
                name=body.name,
                duration=body.config.get("duration"),
                restore=body.config.get("restore", True),
                icon=body.icon,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported helper type: {body.helper_type}",
            )

        return HelperCreateResponse(
            success=result.get("success", False),
            entity_id=result.get("entity_id"),
            input_id=body.input_id,
            helper_type=body.helper_type,
            error=result.get("error"),
        )

    except Exception as e:
        from src.api.utils import sanitize_error

        raise HTTPException(
            status_code=502,
            detail=sanitize_error(e, context="Create helper"),
        ) from e


@router.delete("/helpers/{domain}/{input_id}", response_model=HelperDeleteResponse)
@limiter.limit("10/minute")
async def delete_helper(
    request: Request,
    domain: str,
    input_id: str,
) -> HelperDeleteResponse:
    """Delete a helper entity from Home Assistant.

    Rate limited to 10/minute.

    Args:
        request: FastAPI/Starlette request (for rate limiter)
        domain: Helper domain (e.g., input_boolean, counter)
        input_id: Helper ID to delete

    Returns:
        Deletion result
    """
    from src.ha import get_ha_client

    ha = get_ha_client()
    result = await ha.delete_helper(domain, input_id)

    return HelperDeleteResponse(
        success=result.get("success", False),
        entity_id=result.get("entity_id", f"{domain}.{input_id}"),
        error=result.get("error"),
    )


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
    from sqlalchemy import select

    from src.storage.entities import DiscoverySession, DiscoveryStatus

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
        from src.ha import get_ha_client

        ha = get_ha_client()
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
