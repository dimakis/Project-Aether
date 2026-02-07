"""Entity operations for Home Assistant.

Provides methods for listing, getting, searching, and managing entities.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.ha.base import BaseHAClient, HAClientError, _trace_ha_call
from src.tracing import log_param

logger = logging.getLogger(__name__)


class EntityMixin:
    """Mixin providing entity-related operations."""

    async def _fetch_entity_registry(self) -> dict[str, dict[str, Any]]:
        """Fetch the HA entity registry to get area_id, device_id, etc.

        The entity registry contains metadata not available in /api/states,
        including area_id, device_id, disabled_by, hidden_by, etc.

        Returns:
            Mapping of entity_id to registry entry
        """
        try:
            # HA REST API for entity registry
            registry = await self._request("GET", "/api/config/entity_registry")
            if not registry or not isinstance(registry, list):
                logger.debug("Entity registry returned empty or unexpected format")
                return {}

            return {
                entry.get("entity_id", ""): entry
                for entry in registry
                if entry.get("entity_id")
            }
        except Exception as e:
            logger.warning("Failed to fetch entity registry (area_id will be blank): %s", e)
            return {}

    async def get_area_registry(self) -> list[dict[str, Any]]:
        """Fetch areas directly from the HA area registry REST API.

        Bypasses the HA tool limitation that can only infer areas from
        entity attributes. Returns the full area registry including
        floor_id, icon, picture, and aliases.

        Returns:
            List of area dicts, or empty list on error
        """
        try:
            result = await self._request("GET", "/api/config/area_registry/list")
            if not result or not isinstance(result, list):
                return []
            return result
        except Exception as e:
            logger.warning("Failed to fetch area registry from HA: %s", e)
            return []

    @_trace_ha_call("ha.list_entities")
    async def list_entities(
        self,
        domain: str | None = None,
        search_query: str | None = None,
        limit: int = 1000,
        detailed: bool = False,
    ) -> list[dict[str, Any]]:
        """List entities with optional filtering.

        Merges state data from /api/states with registry data from
        /api/config/entity_registry to include area_id, device_id, etc.

        Args:
            domain: Filter by domain (e.g., "light")
            search_query: Search term for filtering
            limit: Maximum entities to return
            detailed: Include full attributes

        Returns:
            List of entity dictionaries
        """
        # Log query parameters
        if domain:
            log_param("ha.list_entities.domain", domain)
        if search_query:
            log_param("ha.list_entities.search_query", search_query)

        states = await self._request("GET", "/api/states")
        if not states:
            raise HAClientError("Failed to list entities", "list_entities")

        # Fetch entity registry for area_id and other metadata
        registry = await self._fetch_entity_registry()

        entities = []

        for state in states:
            entity_id = state.get("entity_id", "")
            entity_domain = entity_id.split(".")[0] if "." in entity_id else ""

            # Filter by domain
            if domain and entity_domain != domain:
                continue

            # Filter by search query
            if search_query:
                name = state.get("attributes", {}).get("friendly_name", entity_id)
                if (
                    search_query.lower() not in name.lower()
                    and search_query.lower() not in entity_id.lower()
                ):
                    continue

            entity = {
                "entity_id": entity_id,
                "state": state.get("state"),
                "name": state.get("attributes", {}).get("friendly_name", entity_id),
                "domain": entity_domain,
            }

            if detailed:
                entity["attributes"] = state.get("attributes", {})
                entity["last_changed"] = state.get("last_changed")
                entity["last_updated"] = state.get("last_updated")

            # Merge registry metadata (area_id, device_id, etc.)
            reg_entry = registry.get(entity_id, {})
            if reg_entry.get("area_id"):
                entity["area_id"] = reg_entry["area_id"]
            if reg_entry.get("device_id"):
                entity["device_id"] = reg_entry["device_id"]
            if reg_entry.get("icon"):
                entity["icon"] = reg_entry["icon"]

            # Fallback: try extracting area_id from state attributes
            if "area_id" not in entity:
                attrs = state.get("attributes", {})
                if "area_id" in attrs:
                    entity["area_id"] = attrs["area_id"]

            entities.append(entity)

            if len(entities) >= limit:
                break

        return entities

    @_trace_ha_call("ha.get_entity")
    async def get_entity(
        self,
        entity_id: str,
        detailed: bool = True,
    ) -> dict[str, Any] | None:
        """Get a specific entity by ID.

        Args:
            entity_id: Entity ID (e.g., "light.living_room")
            detailed: Include full attributes

        Returns:
            Entity dictionary or None if not found
        """
        log_param("ha.get_entity.entity_id", entity_id)

        state = await self._request("GET", f"/api/states/{entity_id}")
        if not state:
            return None

        domain = entity_id.split(".")[0] if "." in entity_id else ""

        entity = {
            "entity_id": entity_id,
            "state": state.get("state"),
            "name": state.get("attributes", {}).get("friendly_name", entity_id),
            "domain": domain,
        }

        if detailed:
            entity["attributes"] = state.get("attributes", {})
            entity["last_changed"] = state.get("last_changed")
            entity["last_updated"] = state.get("last_updated")

        return entity

    @_trace_ha_call("ha.domain_summary")
    async def domain_summary(
        self,
        domain: str,
        example_limit: int = 3,
    ) -> dict[str, Any]:
        """Get summary of entities in a domain.

        Args:
            domain: Domain to summarize (e.g., "light")
            example_limit: Max examples per state

        Returns:
            Dictionary with count, state distribution, examples
        """
        log_param("ha.domain_summary.domain", domain)

        entities = await self.list_entities(domain=domain, detailed=True)

        state_distribution: dict[str, int] = {}
        examples: dict[str, list[dict[str, Any]]] = {}
        common_attributes: set[str] = set()

        for entity in entities:
            state = entity.get("state", "unknown")
            state_distribution[state] = state_distribution.get(state, 0) + 1

            if state not in examples:
                examples[state] = []
            if len(examples[state]) < example_limit:
                examples[state].append(
                    {
                        "entity_id": entity["entity_id"],
                        "name": entity["name"],
                    }
                )

            if entity.get("attributes"):
                common_attributes.update(entity["attributes"].keys())

        return {
            "total_count": len(entities),
            "state_distribution": state_distribution,
            "examples": examples,
            "common_attributes": list(common_attributes)[:20],
        }

    @_trace_ha_call("ha.entity_action")
    async def entity_action(
        self,
        entity_id: str,
        action: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform action on an entity.

        Args:
            entity_id: Entity to act on
            action: Action (on, off, toggle)
            params: Additional parameters

        Returns:
            Response from HA
        """
        log_param("ha.entity_action.entity_id", entity_id)
        log_param("ha.entity_action.action", action)

        domain = entity_id.split(".")[0] if "." in entity_id else ""
        service = f"turn_{action}" if action in ("on", "off") else action

        data = {"entity_id": entity_id}
        if params:
            data.update(params)

        await self._request("POST", f"/api/services/{domain}/{service}", json=data)
        return {"success": True}

    @_trace_ha_call("ha.call_service")
    async def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call any Home Assistant service.

        Args:
            domain: Service domain
            service: Service name
            data: Service data

        Returns:
            Response from HA
        """
        log_param("ha.call_service.domain", domain)
        log_param("ha.call_service.service", service)

        result = await self._request(
            "POST", f"/api/services/{domain}/{service}", json=data or {}
        )
        return result or {}

    @_trace_ha_call("ha.get_history")
    async def get_history(
        self,
        entity_id: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get entity history.

        Args:
            entity_id: Entity to get history for
            hours: Hours of history

        Returns:
            History data
        """
        log_param("ha.get_history.entity_id", entity_id)
        log_param("ha.get_history.hours", hours)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        history = await self._request(
            "GET",
            f"/api/history/period/{start_time.isoformat()}",
            params={
                "filter_entity_id": entity_id,
                "end_time": end_time.isoformat(),
            },
        )

        if not history or not history[0]:
            return {"entity_id": entity_id, "states": [], "count": 0}

        states = history[0]
        return {
            "entity_id": entity_id,
            "states": [
                {"state": s.get("state"), "last_changed": s.get("last_changed")}
                for s in states
            ],
            "count": len(states),
            "first_changed": states[0].get("last_changed") if states else None,
            "last_changed": states[-1].get("last_changed") if states else None,
        }

    @_trace_ha_call("ha.get_logbook")
    async def get_logbook(
        self,
        hours: int = 24,
        entity_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get logbook entries from Home Assistant.

        Fetches logbook data for behavioral analysis, including
        user actions, automation triggers, and state changes.

        Args:
            hours: Hours of history to fetch
            entity_id: Optional entity to filter by

        Returns:
            List of logbook entry dicts
        """
        log_param("ha.get_logbook.hours", hours)
        if entity_id:
            log_param("ha.get_logbook.entity_id", entity_id)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        params: dict[str, Any] = {
            "end_time": end_time.isoformat(),
        }
        if entity_id:
            params["entity"] = entity_id

        result = await self._request(
            "GET",
            f"/api/logbook/{start_time.isoformat()}",
            params=params,
        )

        if not result:
            return []

        # HA logbook returns a flat list of entries
        if isinstance(result, list):
            return result

        return []

    @_trace_ha_call("ha.search_entities")
    async def search_entities(
        self,
        query: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search for entities matching a query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Search results with count and domain breakdown
        """
        log_param("ha.search_entities.query", query)

        entities = await self.list_entities(search_query=query, limit=limit)

        # Build domain counts
        domains: dict[str, int] = {}
        for entity in entities:
            domain = entity.get("domain", "unknown")
            domains[domain] = domains.get(domain, 0) + 1

        return {
            "count": len(entities),
            "results": entities,
            "domains": domains,
        }
