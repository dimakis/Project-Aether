"""Area repository for HA area CRUD operations."""

from sqlalchemy import select

from src.dal.base import BaseRepository
from src.storage.entities import Area


class AreaRepository(BaseRepository[Area]):
    """Repository for Area CRUD operations."""

    model = Area
    ha_id_field = "ha_area_id"
    order_by_field = "name"

    async def get_by_ha_area_id(self, ha_area_id: str) -> Area | None:
        """Get area by Home Assistant area_id.

        Args:
            ha_area_id: HA area ID

        Returns:
            Area or None
        """
        return await self.get_by_ha_id(ha_area_id)

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
        return await super().list_all(limit=limit, offset=offset, floor_id=floor_id)

    async def get_all_ha_area_ids(self) -> set[str]:
        """Get all HA area IDs in database.

        Returns:
            Set of area IDs
        """
        return await self.get_all_ha_ids()

    async def get_id_mapping(self) -> dict[str, str]:
        """Get mapping of HA area_id to internal ID.

        Returns:
            Dictionary mapping ha_area_id to id
        """
        result = await self.session.execute(select(Area.ha_area_id, Area.id))
        return {row[0]: row[1] for row in result.fetchall()}
