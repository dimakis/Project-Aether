"""Automation registry endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    AutomationListResponse,
    AutomationResponse,
)
from src.dal import AutomationRepository

from ._common import _is_valid_uuid, get_db

router = APIRouter(tags=["HA Registry"])


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
) -> dict[str, Any]:
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
