"""Cached Home Assistant registry for semantic validation.

Provides an in-memory cache over HA's entity, service, and area
registries. Used by the semantic validator to check entity existence,
service validity, and area/device existence without repeated API calls.

Feature 27: YAML Semantic Validation.
"""

from __future__ import annotations

import time
from typing import Any

_DEFAULT_TTL = 600  # 10 minutes


class HARegistryCache:
    """Cached view of Home Assistant registries.

    Fetches entity, service, and area data from the HA client
    and caches it in memory with a configurable TTL.

    Args:
        ha_client: An object with async methods ``list_entities()``,
            ``list_services()``, and ``get_area_registry()``.
        ttl_seconds: Cache time-to-live in seconds (default 600).
    """

    def __init__(self, ha_client: Any, ttl_seconds: int = _DEFAULT_TTL) -> None:
        self._ha = ha_client
        self._ttl_seconds = ttl_seconds

        # Entity cache
        self._entity_ids: set[str] | None = None
        self._entities_fetched_at: float = 0.0

        # Service cache
        self._services: dict[str, dict[str, dict[str, Any]]] | None = None
        self._services_fetched_at: float = 0.0

        # Area cache
        self._area_ids: set[str] | None = None
        self._areas_fetched_at: float = 0.0

    # ------------------------------------------------------------------
    # Entity methods
    # ------------------------------------------------------------------

    async def _ensure_entities(self) -> None:
        """Fetch entities if cache is empty or expired."""
        now = time.monotonic()
        if self._entity_ids is not None and (now - self._entities_fetched_at) < self._ttl_seconds:
            return

        entities = await self._ha.list_entities()
        self._entity_ids = {e.get("entity_id", "") for e in entities if e.get("entity_id")}
        self._entities_fetched_at = now

    async def entity_exists(self, entity_id: str) -> bool:
        """Check if an entity ID exists in the HA registry."""
        await self._ensure_entities()
        assert self._entity_ids is not None  # nosec B101 — guaranteed by _ensure_entities
        return entity_id in self._entity_ids

    async def get_entity_ids(self, *, domain: str | None = None) -> set[str]:
        """Get all known entity IDs, optionally filtered by domain."""
        await self._ensure_entities()
        assert self._entity_ids is not None  # nosec B101 — guaranteed by _ensure_entities
        if domain is None:
            return set(self._entity_ids)
        prefix = f"{domain}."
        return {eid for eid in self._entity_ids if eid.startswith(prefix)}

    # ------------------------------------------------------------------
    # Service methods
    # ------------------------------------------------------------------

    async def _ensure_services(self) -> None:
        """Fetch services if cache is empty or expired."""
        now = time.monotonic()
        if self._services is not None and (now - self._services_fetched_at) < self._ttl_seconds:
            return

        raw = await self._ha.list_services()
        self._services = {}
        for domain_entry in raw:
            domain = domain_entry.get("domain", "")
            services = domain_entry.get("services", {})
            if domain:
                self._services[domain] = services
        self._services_fetched_at = now

    async def service_exists(self, service_name: str) -> bool:
        """Check if a domain.service exists in HA.

        Args:
            service_name: Full service name, e.g. "light.turn_on".
        """
        await self._ensure_services()
        assert self._services is not None  # nosec B101 — guaranteed by _ensure_services

        parts = service_name.split(".", 1)
        if len(parts) != 2:
            return False

        domain, service = parts
        return domain in self._services and service in self._services[domain]

    async def get_service_fields(self, service_name: str) -> dict[str, Any] | None:
        """Get the field definitions for a service.

        Args:
            service_name: Full service name, e.g. "light.turn_on".

        Returns:
            Field definitions dict, or None if service not found.
        """
        await self._ensure_services()
        assert self._services is not None  # nosec B101 — guaranteed by _ensure_services

        parts = service_name.split(".", 1)
        if len(parts) != 2:
            return None

        domain, service = parts
        if domain not in self._services or service not in self._services[domain]:
            return None

        svc_info = self._services[domain][service]
        fields: dict[str, Any] | None = svc_info.get("fields")
        return fields if fields is not None else {}

    async def get_service_domains(self) -> set[str]:
        """Get all known service domains."""
        await self._ensure_services()
        assert self._services is not None  # nosec B101 — guaranteed by _ensure_services
        return set(self._services.keys())

    # ------------------------------------------------------------------
    # Area methods
    # ------------------------------------------------------------------

    async def _ensure_areas(self) -> None:
        """Fetch areas if cache is empty or expired."""
        now = time.monotonic()
        if self._area_ids is not None and (now - self._areas_fetched_at) < self._ttl_seconds:
            return

        areas = await self._ha.get_area_registry()
        self._area_ids = {a.get("area_id", "") for a in areas if a.get("area_id")}
        self._areas_fetched_at = now

    async def area_exists(self, area_id: str) -> bool:
        """Check if an area ID exists in the HA registry."""
        await self._ensure_areas()
        assert self._area_ids is not None  # nosec B101 — guaranteed by _ensure_areas
        return area_id in self._area_ids

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate(self) -> None:
        """Clear all cached data, forcing re-fetch on next access."""
        self._entity_ids = None
        self._entities_fetched_at = 0.0
        self._services = None
        self._services_fetched_at = 0.0
        self._area_ids = None
        self._areas_fetched_at = 0.0


__all__ = ["HARegistryCache"]
