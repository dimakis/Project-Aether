"""SQLAlchemy base model and common mixins.

Provides reusable model infrastructure for all database entities.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Naming convention for constraints (helps with migrations)
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    Features:
    - Automatic table naming from class name (snake_case)
    - Metadata with naming convention for consistent constraint names
    - Type annotation support for mapped columns
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Make __tablename__ automatic from class name
    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Generate table name from class name in snake_case."""
        name = cls.__name__
        # Convert CamelCase to snake_case
        result: list[str] = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary.

        Returns:
            Dictionary with column names as keys and their values.
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class UUIDMixin:
    """Mixin that adds UUID primary key.

    Provides:
    - id: UUID primary key with auto-generation
    """

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        doc="Unique identifier (UUID v4)",
    )


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps.

    Provides:
    - created_at: Set automatically on insert
    - updated_at: Updated automatically on every update
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Last update timestamp",
    )


class SoftDeleteMixin:
    """Mixin that adds soft delete capability.

    Provides:
    - deleted_at: When set, record is considered deleted
    - is_deleted property for convenience

    Usage:
        query.filter(Model.deleted_at.is_(None))  # Active records only
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Soft delete timestamp (null = active)",
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None


class HAEntityMixin:
    """Mixin for Home Assistant entity tracking.

    Provides:
    - last_synced_at: When entity was last synced from HA
    - ha_last_changed: HA's last_changed timestamp
    - ha_last_updated: HA's last_updated timestamp
    """

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When this record was last synced from Home Assistant",
    )
    ha_last_changed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Home Assistant last_changed timestamp",
    )
    ha_last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Home Assistant last_updated timestamp",
    )


# Export all public classes
__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "HAEntityMixin",
    "NAMING_CONVENTION",
]
