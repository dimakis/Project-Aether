"""Device repository for HA device CRUD operations."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.dal.base import BaseRepository
from src.storage.entities import Device


class DeviceRepository(BaseRepository[Device]):
    """Repository for Device CRUD operations."""

    model = Device
    ha_id_field = "ha_device_id"
    order_by_field = "name"

    async def get_by_ha_device_id(self, ha_device_id: str) -> Device | None:
        """Get device by Home Assistant device_id.

        Args:
            ha_device_id: HA device ID

        Returns:
            Device or None
        """
        return await self.get_by_ha_id(ha_device_id)

    async def list_all(
        self,
        area_id: str | None = None,
        manufacturer: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Device]:
        """List devices with optional filtering.

        Eagerly loads the ``area`` relationship so results remain usable
        after the session is closed (required for session-per-task
        concurrency in entity_context).

        Args:
            area_id: Filter by area
            manufacturer: Filter by manufacturer
            limit: Max results
            offset: Skip results

        Returns:
            List of devices
        """
        query = select(Device).options(selectinload(Device.area))

        # Apply filters
        if area_id is not None:
            query = query.where(Device.area_id == area_id)
        if manufacturer is not None:
            query = query.where(Device.manufacturer == manufacturer)

        query = query.order_by(Device.name).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_ha_device_ids(self) -> set[str]:
        """Get all HA device IDs in database.

        Returns:
            Set of device IDs
        """
        return await self.get_all_ha_ids()
