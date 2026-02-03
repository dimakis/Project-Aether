"""Area repository for HA area CRUD operations."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities import Area


class AreaRepository:
    """Repository for Area CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, area_id: str) -> Area | None:
        """Get area by internal ID.

        Args:
            area_id: Internal UUID

        Returns:
            Area or None
        """
        result = await self.session.execute(
            select(Area).where(Area.id == area_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ha_area_id(self, ha_area_id: str) -> Area | None:
        """Get area by Home Assistant area_id.

        Args:
            ha_area_id: HA area ID

        Returns:
            Area or None
        """
        result = await self.session.execute(
            select(Area).where(Area.ha_area_id == ha_area_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        floor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Area]:
        """List areas with optional filtering.

        Args:
            floor_id: Filter by floor
            limit: Max results
            offset: Skip results

        Returns:
            List of areas
        """
        query = select(Area)

        if floor_id:
            query = query.where(Area.floor_id == floor_id)

        query = query.order_by(Area.name).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count all areas.

        Returns:
            Area count
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count(Area.id)))
        return result.scalar() or 0

    async def create(self, data: dict[str, Any]) -> Area:
        """Create a new area.

        Args:
            data: Area data

        Returns:
            Created area
        """
        area = Area(
            id=str(uuid4()),
            **data,
            last_synced_at=datetime.utcnow(),
        )
        self.session.add(area)
        await self.session.flush()
        return area

    async def upsert(self, data: dict[str, Any]) -> tuple[Area, bool]:
        """Create or update an area.

        Args:
            data: Area data (must include ha_area_id)

        Returns:
            Tuple of (area, created)
        """
        ha_area_id = data.get("ha_area_id")
        if not ha_area_id:
            raise ValueError("ha_area_id required for upsert")

        existing = await self.get_by_ha_area_id(ha_area_id)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            existing.last_synced_at = datetime.utcnow()
            await self.session.flush()
            return existing, False
        else:
            area = await self.create(data)
            return area, True

    async def get_all_ha_area_ids(self) -> set[str]:
        """Get all HA area IDs in database.

        Returns:
            Set of area IDs
        """
        result = await self.session.execute(select(Area.ha_area_id))
        return {row[0] for row in result.fetchall()}

    async def get_id_mapping(self) -> dict[str, str]:
        """Get mapping of HA area_id to internal ID.

        Returns:
            Dictionary mapping ha_area_id to id
        """
        result = await self.session.execute(
            select(Area.ha_area_id, Area.id)
        )
        return {row[0]: row[1] for row in result.fetchall()}
