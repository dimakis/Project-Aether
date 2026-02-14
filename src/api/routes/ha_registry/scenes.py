"""Scene registry endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import SceneListResponse, SceneResponse
from src.dal import SceneRepository

from ._common import _is_valid_uuid, get_db

router = APIRouter(tags=["HA Registry"])


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
