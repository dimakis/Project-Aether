"""Entity repository for HA entity CRUD operations."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dal.base import BaseRepository
from src.storage.entities import HAEntity


def _escape_ilike(value: str) -> str:
    """Escape special characters for ILIKE pattern matching.

    Prevents wildcard injection by escaping %, _, and \\ characters
    so they are treated as literals in SQL ILIKE expressions (T189).

    Args:
        value: Raw search term from user input

    Returns:
        Escaped string safe for use in ILIKE patterns
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class EntityRepository(BaseRepository[HAEntity]):
    """Repository for HAEntity CRUD operations.

    Provides efficient entity querying with optional caching.
    """
    
    model = HAEntity
    ha_id_field = "entity_id"
    order_by_field = "entity_id"

    async def get_by_entity_id(self, ha_entity_id: str) -> HAEntity | None:
        """Get entity by Home Assistant entity_id.

        Args:
            ha_entity_id: HA entity ID (e.g., "light.living_room")

        Returns:
            HAEntity or None
        """
        return await self.get_by_ha_id(ha_entity_id)

    async def list_all(
        self,
        domain: str | None = None,
        area_id: str | None = None,
        device_id: str | None = None,
        state: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[HAEntity]:
        """List entities with optional filtering.

        Args:
            domain: Filter by domain
            area_id: Filter by area
            device_id: Filter by device
            state: Filter by state
            limit: Max results
            offset: Skip results

        Returns:
            List of entities
        """
        return await super().list_all(
            limit=limit,
            offset=offset,
            domain=domain,
            area_id=area_id,
            device_id=device_id,
            state=state,
        )

    async def list_by_domain(self, domain: str) -> list[HAEntity]:
        """List all entities in a domain.

        Args:
            domain: Domain to filter by

        Returns:
            List of entities
        """
        return await self.list_all(domain=domain)

    async def list_by_domains(
        self,
        domains: list[str],
        limit_per_domain: int = 50,
    ) -> dict[str, list[HAEntity]]:
        """List entities for multiple domains in a single query (T190).

        Avoids N+1 queries when building context for multiple domains.

        Args:
            domains: List of domains to fetch
            limit_per_domain: Max entities per domain (applied in Python)

        Returns:
            Dictionary of domain -> list of entities
        """
        if not domains:
            return {}

        query = (
            select(HAEntity)
            .where(HAEntity.domain.in_(domains))
            .order_by(HAEntity.domain, HAEntity.entity_id)
        )

        result = await self.session.execute(query)
        all_entities = list(result.scalars().all())

        # Group by domain and apply per-domain limit
        grouped: dict[str, list[HAEntity]] = {d: [] for d in domains}
        for entity in all_entities:
            domain_list = grouped.get(entity.domain)
            if domain_list is not None and len(domain_list) < limit_per_domain:
                domain_list.append(entity)

        return grouped

    async def count(self, domain: str | None = None) -> int:
        """Count entities, optionally by domain.

        Args:
            domain: Optional domain filter

        Returns:
            Count of entities
        """
        return await super().count(domain=domain)

    async def get_domain_counts(self) -> dict[str, int]:
        """Get entity count per domain.

        Returns:
            Dictionary of domain -> count
        """
        from sqlalchemy import func

        query = (
            select(HAEntity.domain, func.count(HAEntity.id))
            .group_by(HAEntity.domain)
            .order_by(func.count(HAEntity.id).desc())
        )

        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.fetchall()}


    async def update(
        self,
        ha_entity_id: str,
        data: dict[str, Any],
    ) -> HAEntity | None:
        """Update an entity by HA entity_id.

        Args:
            ha_entity_id: HA entity ID
            data: Fields to update

        Returns:
            Updated entity or None
        """
        entity = await self.get_by_entity_id(ha_entity_id)
        if not entity:
            return None

        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        entity.last_synced_at = datetime.now(timezone.utc)
        await self.session.flush()
        return entity


    async def delete(self, ha_entity_id: str) -> bool:
        """Delete an entity by HA entity_id.

        Args:
            ha_entity_id: HA entity ID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_entity_id(ha_entity_id)
        if not entity:
            return False

        await self.session.delete(entity)
        await self.session.flush()
        return True

    async def get_all_entity_ids(self) -> set[str]:
        """Get all HA entity IDs in database.

        Returns:
            Set of entity IDs
        """
        return await self.get_all_ha_ids()

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[HAEntity]:
        """Search entities by name or entity_id.

        Args:
            query: Search term
            limit: Max results

        Returns:
            Matching entities
        """
        escaped = _escape_ilike(query)
        search_pattern = f"%{escaped}%"
        result = await self.session.execute(
            select(HAEntity)
            .where(
                (HAEntity.name.ilike(search_pattern, escape="\\"))
                | (HAEntity.entity_id.ilike(search_pattern, escape="\\"))
            )
            .limit(limit)
        )
        return list(result.scalars().all())
