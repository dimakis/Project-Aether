"""Device repository for HA device CRUD operations."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities import Device


class DeviceRepository:
    """Repository for Device CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, device_id: str) -> Device | None:
        """Get device by internal ID.

        Args:
            device_id: Internal UUID

        Returns:
            Device or None
        """
        result = await self.session.execute(
            select(Device).where(Device.id == device_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ha_device_id(self, ha_device_id: str) -> Device | None:
        """Get device by Home Assistant device_id.

        Args:
            ha_device_id: HA device ID

        Returns:
            Device or None
        """
        result = await self.session.execute(
            select(Device).where(Device.ha_device_id == ha_device_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        area_id: str | None = None,
        manufacturer: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Device]:
        """List devices with optional filtering.

        Args:
            area_id: Filter by area
            manufacturer: Filter by manufacturer
            limit: Max results
            offset: Skip results

        Returns:
            List of devices
        """
        query = select(Device)

        if area_id:
            query = query.where(Device.area_id == area_id)
        if manufacturer:
            query = query.where(Device.manufacturer == manufacturer)

        query = query.order_by(Device.name).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count all devices.

        Returns:
            Device count
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count(Device.id)))
        return result.scalar() or 0

    async def create(self, data: dict[str, Any]) -> Device:
        """Create a new device.

        Args:
            data: Device data

        Returns:
            Created device
        """
        device = Device(
            id=str(uuid4()),
            **data,
            last_synced_at=datetime.utcnow(),
        )
        self.session.add(device)
        await self.session.flush()
        return device

    async def upsert(self, data: dict[str, Any]) -> tuple[Device, bool]:
        """Create or update a device.

        Args:
            data: Device data (must include ha_device_id)

        Returns:
            Tuple of (device, created)
        """
        ha_device_id = data.get("ha_device_id")
        if not ha_device_id:
            raise ValueError("ha_device_id required for upsert")

        existing = await self.get_by_ha_device_id(ha_device_id)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            existing.last_synced_at = datetime.utcnow()
            await self.session.flush()
            return existing, False
        else:
            device = await self.create(data)
            return device, True

    async def get_all_ha_device_ids(self) -> set[str]:
        """Get all HA device IDs in database.

        Returns:
            Set of device IDs
        """
        result = await self.session.execute(select(Device.ha_device_id))
        return {row[0] for row in result.fetchall()}
