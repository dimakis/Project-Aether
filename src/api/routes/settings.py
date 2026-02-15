"""App settings API routes.

GET  /api/v1/settings         — read all settings (merged with defaults)
PATCH /api/v1/settings        — update one or more sections
POST /api/v1/settings/reset   — reset a section to defaults
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.dal.app_settings import (
    SECTION_DEFAULTS,
    AppSettingsRepository,
    invalidate_settings_cache,
    validate_section,
)
from src.storage import get_session

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsResponse(BaseModel):
    """Full settings response with all sections."""

    chat: dict[str, Any]
    dashboard: dict[str, Any]
    data_science: dict[str, Any]


class SettingsPatchRequest(BaseModel):
    """Partial update — include only the sections you want to change."""

    chat: dict[str, Any] | None = None
    dashboard: dict[str, Any] | None = None
    data_science: dict[str, Any] | None = None


class ResetRequest(BaseModel):
    """Reset a section to defaults."""

    section: str


@router.get("", response_model=SettingsResponse)
async def get_settings_endpoint() -> SettingsResponse:
    """Get all application settings merged with defaults."""
    async with get_session() as session:
        repo = AppSettingsRepository(session)
        merged = await repo.get_merged()
        return SettingsResponse(**merged)


@router.patch("", response_model=SettingsResponse)
async def patch_settings(body: SettingsPatchRequest) -> SettingsResponse:
    """Update settings for one or more sections.

    Only include sections you want to change. Within each section,
    only include the keys you want to change — existing keys are
    preserved (merge, not replace).

    Values are validated and clamped to allowed bounds.
    """
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No sections to update")

    # Validate all sections before writing
    for section, data in updates.items():
        if section not in SECTION_DEFAULTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown section: {section}",
            )
        try:
            validate_section(section, data)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    async with get_session() as session:
        repo = AppSettingsRepository(session)
        result = None
        for section, data in updates.items():
            result = await repo.update_section(section, data)
        await session.commit()
        invalidate_settings_cache()

        # Return the final merged state
        if result is None:
            result = await repo.get_merged()
        return SettingsResponse(**result)


@router.post("/reset", response_model=SettingsResponse)
async def reset_section(body: ResetRequest) -> SettingsResponse:
    """Reset a section to its default values (clears all DB overrides)."""
    if body.section not in SECTION_DEFAULTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown section: {body.section}. Valid: {list(SECTION_DEFAULTS.keys())}",
        )

    async with get_session() as session:
        repo = AppSettingsRepository(session)
        result = await repo.reset_section(body.section)
        await session.commit()
        invalidate_settings_cache()
        return SettingsResponse(**result)
