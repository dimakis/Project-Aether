"""Area API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AreaBase(BaseModel):
    """Base area schema."""

    ha_area_id: str = Field(..., description="HA area ID")
    name: str = Field(..., description="Area name")


class AreaResponse(AreaBase):
    """Area response with all fields."""

    id: str = Field(..., description="Internal UUID")
    floor_id: str | None = Field(None, description="Floor ID (if available)")
    icon: str | None = None
    entity_count: int = 0
    last_synced_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AreaListResponse(BaseModel):
    """Response for area list."""

    areas: list[AreaResponse]
    total: int
