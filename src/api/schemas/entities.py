"""Entity API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EntityBase(BaseModel):
    """Base entity schema."""

    entity_id: str = Field(..., description="HA entity ID (e.g., light.living_room)")
    domain: str = Field(..., description="Entity domain")
    name: str = Field(..., description="Display name")
    state: str | None = Field(None, description="Current state")


class EntityResponse(EntityBase):
    """Entity response with all fields."""

    id: str = Field(..., description="Internal UUID")
    attributes: dict[str, Any] | None = Field(None, description="Entity attributes")
    area_id: str | None = Field(None, description="Area ID")
    device_id: str | None = Field(None, description="Device ID")
    device_class: str | None = None
    unit_of_measurement: str | None = None
    supported_features: int = 0
    icon: str | None = None
    last_synced_at: datetime | None = None

    class Config:
        from_attributes = True


class EntityListResponse(BaseModel):
    """Response for entity list."""

    entities: list[EntityResponse]
    total: int
    domain: str | None = None


class EntityQueryRequest(BaseModel):
    """Request for natural language entity query."""

    query: str = Field(..., max_length=2000, description="Natural language query")
    limit: int = Field(20, ge=1, le=100)


class EntityQueryResult(BaseModel):
    """Result from entity query."""

    entities: list[EntityResponse]
    query: str
    interpreted_as: str | None = None


class EntitySyncRequest(BaseModel):
    """Request to trigger entity sync."""

    force: bool = Field(False, description="Force full re-sync")


class EntitySyncResponse(BaseModel):
    """Response from entity sync."""

    session_id: str
    status: str
    entities_found: int
    entities_added: int
    entities_updated: int
    entities_removed: int
    duration_seconds: float | None = None
