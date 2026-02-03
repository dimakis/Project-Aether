"""Entity repository for HA entity CRUD operations."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities import HAEntity


class EntityRepository:
    """Repository for HAEntity CRUD operations.

    Provides efficient entity querying with optional caching.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, entity_id: str) -> HAEntity | None:
        """Get entity by our internal ID.

        Args:
            entity_id: Internal UUID

        Returns:
            HAEntity or None
        """
        result = await self.session.execute(
            select(HAEntity).where(HAEntity.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_entity_id(self, ha_entity_id: str) -> HAEntity | None:
        """Get entity by Home Assistant entity_id.

        Args:
            ha_entity_id: HA entity ID (e.g., "light.living_room")

        Returns:
            HAEntity or None
        """
        result = await self.session.execute(
            select(HAEntity).where(HAEntity.entity_id == ha_entity_id)
        )
        return result.scalar_one_or_none()

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
        query = select(HAEntity)

        if domain:
            query = query.where(HAEntity.domain == domain)
        if area_id:
            query = query.where(HAEntity.area_id == area_id)
        if device_id:
            query = query.where(HAEntity.device_id == device_id)
        if state:
            query = query.where(HAEntity.state == state)

        query = query.order_by(HAEntity.entity_id).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_domain(self, domain: str) -> list[HAEntity]:
        """List all entities in a domain.

        Args:
            domain: Domain to filter by

        Returns:
            List of entities
        """
        return await self.list_all(domain=domain)

    async def count(self, domain: str | None = None) -> int:
        """Count entities, optionally by domain.

        Args:
            domain: Optional domain filter

        Returns:
            Count of entities
        """
        from sqlalchemy import func

        query = select(func.count(HAEntity.id))
        if domain:
            query = query.where(HAEntity.domain == domain)

        result = await self.session.execute(query)
        return result.scalar() or 0

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

    async def create(self, data: dict[str, Any]) -> HAEntity:
        """Create a new entity.

        Args:
            data: Entity data

        Returns:
            Created entity
        """
        entity = HAEntity(
            id=str(uuid4()),
            **data,
            last_synced_at=datetime.utcnow(),
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

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

        entity.last_synced_at = datetime.utcnow()
        await self.session.flush()
        return entity

    async def upsert(self, data: dict[str, Any]) -> tuple[HAEntity, bool]:
        """Create or update an entity.

        Args:
            data: Entity data (must include entity_id)

        Returns:
            Tuple of (entity, created) where created is True if new
        """
        ha_entity_id = data.get("entity_id")
        if not ha_entity_id:
            raise ValueError("entity_id required for upsert")

        existing = await self.get_by_entity_id(ha_entity_id)
        if existing:
            # Update
            for key, value in data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            existing.last_synced_at = datetime.utcnow()
            await self.session.flush()
            return existing, False
        else:
            # Create
            entity = await self.create(data)
            return entity, True

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
        result = await self.session.execute(select(HAEntity.entity_id))
        return {row[0] for row in result.fetchall()}

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
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(HAEntity)
            .where(
                (HAEntity.name.ilike(search_pattern))
                | (HAEntity.entity_id.ilike(search_pattern))
            )
            .limit(limit)
        )
        return list(result.scalars().all())
