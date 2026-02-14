"""Script registry endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ScriptListResponse, ScriptResponse
from src.dal import ScriptRepository

from ._common import _is_valid_uuid, get_db

router = APIRouter(tags=["HA Registry"])


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
