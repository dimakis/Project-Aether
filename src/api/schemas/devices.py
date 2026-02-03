"""Device API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class DeviceBase(BaseModel):
    """Base device schema."""

    ha_device_id: str = Field(..., description="HA device ID")
    name: str = Field(..., description="Device name")


class DeviceResponse(DeviceBase):
    """Device response with all fields."""

    id: str = Field(..., description="Internal UUID")
    area_id: str | None = Field(None, description="Area ID")
    manufacturer: str | None = None
    model: str | None = None
    sw_version: str | None = None
    entity_count: int = 0
    last_synced_at: datetime | None = None

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """Response for device list."""

    devices: list[DeviceResponse]
    total: int
