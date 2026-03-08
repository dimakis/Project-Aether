"""HA helper CRUD endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from src.api.rate_limit import limiter
from src.api.schemas import (
    HelperCreateRequest,
    HelperCreateResponse,
    HelperDeleteResponse,
    HelperListResponse,
    HelperResponse,
)

router = APIRouter(tags=["HA Registry"])


@router.get("/helpers", response_model=HelperListResponse)
async def list_helpers() -> HelperListResponse:
    """List all helper entities from Home Assistant.

    Returns live helper state directly from HA (not cached).

    Returns:
        List of helpers with type breakdown
    """
    from src.ha import get_ha_client_async

    try:
        ha = await get_ha_client_async()
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
    from src.ha import get_ha_client_async

    ha = await get_ha_client_async()
    result: dict[str, Any]

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
    from src.ha import get_ha_client_async

    ha = await get_ha_client_async()
    result = await ha.delete_helper(domain, input_id)

    return HelperDeleteResponse(
        success=result.get("success", False),
        entity_id=result.get("entity_id", f"{domain}.{input_id}"),
        error=result.get("error"),
    )
