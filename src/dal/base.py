"""Base repository with common CRUD operations."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations.

    Subclasses must set:
    - model: The SQLAlchemy model class
    - ha_id_field: Name of the HA ID column (e.g., "ha_area_id", "entity_id")
    - order_by_field: Field to use for ordering in list_all() (default: "name")
    """

    model: type[T]  # Set by subclasses
    ha_id_field: str  # Name of the HA ID column (e.g., "ha_area_id")
    order_by_field: str = "name"  # Field for ordering

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, id: str) -> T | None:
        """Get entity by internal ID.

        Args:
            id: Internal UUID

        Returns:
            Entity or None
        """
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_ha_id(self, ha_id: str) -> T | None:
        """Get entity by Home Assistant ID.

        Args:
            ha_id: HA ID value

        Returns:
            Entity or None
        """
        ha_id_attr = getattr(self.model, self.ha_id_field)
        result = await self.session.execute(select(self.model).where(ha_id_attr == ha_id))
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0, **filters) -> list[T]:
        """List entities with optional filtering.

        Args:
            limit: Max results
            offset: Skip results
            **filters: Additional filters as keyword arguments

        Returns:
            List of entities
        """
        query = select(self.model)

        # Apply filters dynamically
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                attr = getattr(self.model, key)
                query = query.where(attr == value)

        # Order by configured field
        order_by_attr = getattr(self.model, self.order_by_field, None)
        if order_by_attr is not None:
            query = query.order_by(order_by_attr)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, **filters) -> int:
        """Count entities, optionally with filters.

        Args:
            **filters: Optional filters as keyword arguments

        Returns:
            Count of entities
        """
        query = select(func.count(self.model.id))

        # Apply filters dynamically
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                attr = getattr(self.model, key)
                query = query.where(attr == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, data: dict[str, Any]) -> T:
        """Create a new entity.

        Args:
            data: Entity data

        Returns:
            Created entity
        """
        # Check if model has last_synced_at field
        create_data = {
            "id": str(uuid4()),
            **data,
        }

        # Add last_synced_at if model has the field
        if hasattr(self.model, "last_synced_at"):
            create_data["last_synced_at"] = datetime.now(UTC)

        entity = self.model(**create_data)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def upsert(self, data: dict[str, Any]) -> tuple[T, bool]:
        """Create or update an entity.

        Args:
            data: Entity data (must include the HA ID field)

        Returns:
            Tuple of (entity, created) where created is True if new
        """
        ha_id_value = data.get(self.ha_id_field)
        if not ha_id_value:
            raise ValueError(f"{self.ha_id_field} required for upsert")

        existing = await self.get_by_ha_id(ha_id_value)
        if existing:
            # Update
            for key, value in data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)

            # Update last_synced_at if model has the field
            if hasattr(existing, "last_synced_at"):
                existing.last_synced_at = datetime.now(UTC)

            await self.session.flush()
            return existing, False
        else:
            # Create
            entity = await self.create(data)
            return entity, True

    async def get_all_ha_ids(self) -> set[str]:
        """Get all HA IDs in database.

        Returns:
            Set of HA IDs
        """
        ha_id_attr = getattr(self.model, self.ha_id_field)
        result = await self.session.execute(select(ha_id_attr))
        return {row[0] for row in result.fetchall() if row[0] is not None}
