"""Service repository for HA service registry.

MCP Gap: No `list_services` tool available.
Workaround: Seed common services from constants, expand during discovery.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.constants import get_all_services
from src.storage.entities.ha_automation import Service


class ServiceRepository:
    """Repository for Service CRUD operations.

    Manages the service registry which is seeded with common services
    and expanded as services are discovered during agent operations.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, service_id: str) -> Service | None:
        """Get service by internal ID.

        Args:
            service_id: Internal UUID

        Returns:
            Service or None
        """
        result = await self.session.execute(
            select(Service).where(Service.id == service_id)
        )
        return result.scalar_one_or_none()

    async def get_by_full_name(self, domain: str, service: str) -> Service | None:
        """Get service by domain and service name.

        Args:
            domain: Service domain (e.g., 'light')
            service: Service name (e.g., 'turn_on')

        Returns:
            Service or None
        """
        result = await self.session.execute(
            select(Service).where(
                Service.domain == domain,
                Service.service == service,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        domain: str | None = None,
        is_seeded: bool | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Service]:
        """List services with optional filtering.

        Args:
            domain: Filter by domain
            is_seeded: Filter by seeded status
            limit: Max results
            offset: Skip results

        Returns:
            List of services
        """
        query = select(Service)

        if domain:
            query = query.where(Service.domain == domain)
        if is_seeded is not None:
            query = query.where(Service.is_seeded == is_seeded)

        query = query.order_by(Service.domain, Service.service).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_domain(self, domain: str) -> list[Service]:
        """List all services for a domain.

        Args:
            domain: Domain to filter by

        Returns:
            List of services
        """
        return await self.list_all(domain=domain)

    async def get_domains(self) -> list[str]:
        """Get all unique service domains.

        Returns:
            List of domain names
        """
        result = await self.session.execute(
            select(Service.domain).distinct().order_by(Service.domain)
        )
        return [row[0] for row in result.fetchall()]

    async def count(self, domain: str | None = None) -> int:
        """Count services.

        Args:
            domain: Optional domain filter

        Returns:
            Service count
        """
        from sqlalchemy import func

        query = select(func.count(Service.id))
        if domain:
            query = query.where(Service.domain == domain)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, data: dict[str, Any]) -> Service:
        """Create a new service record.

        Args:
            data: Service data

        Returns:
            Created service
        """
        service = Service(
            id=str(uuid4()),
            **data,
        )
        self.session.add(service)
        await self.session.flush()
        return service

    async def upsert(self, data: dict[str, Any]) -> tuple[Service, bool]:
        """Create or update a service.

        Args:
            data: Service data (must include domain and service)

        Returns:
            Tuple of (service, created)
        """
        domain = data.get("domain")
        service_name = data.get("service")

        if not domain or not service_name:
            raise ValueError("domain and service required for upsert")

        existing = await self.get_by_full_name(domain, service_name)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            await self.session.flush()
            return existing, False
        else:
            service = await self.create(data)
            return service, True

    async def seed_common_services(self) -> dict[str, int]:
        """Seed common services from constants.

        This should be called during initial setup or migration
        to populate the service registry with known common services.

        Returns:
            Dict with 'added' and 'skipped' counts
        """
        services_data = get_all_services()
        stats = {"added": 0, "skipped": 0}

        for svc_data in services_data:
            existing = await self.get_by_full_name(
                svc_data["domain"],
                svc_data["service"],
            )

            if existing:
                stats["skipped"] += 1
            else:
                await self.create(svc_data)
                stats["added"] += 1

        await self.session.flush()
        return stats

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Service]:
        """Search services by name or description.

        Args:
            query: Search term
            limit: Max results

        Returns:
            Matching services
        """
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(Service)
            .where(
                (Service.name.ilike(search_pattern))
                | (Service.description.ilike(search_pattern))
                | (Service.domain.ilike(search_pattern))
                | (Service.service.ilike(search_pattern))
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_service_info(self, full_name: str) -> Service | None:
        """Get service by full name (domain.service).

        Args:
            full_name: Full service name like 'light.turn_on'

        Returns:
            Service or None
        """
        if "." not in full_name:
            return None

        domain, service = full_name.split(".", 1)
        return await self.get_by_full_name(domain, service)


async def seed_services(session: AsyncSession) -> dict[str, int]:
    """Convenience function to seed common services.

    Args:
        session: Database session

    Returns:
        Seeding stats
    """
    repo = ServiceRepository(session)
    return await repo.seed_common_services()
