"""Discovery sync service for orchestrating HA synchronization."""

import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession

from src.dal.areas import AreaRepository
from src.dal.automations import AutomationRepository, SceneRepository, ScriptRepository
from src.dal.devices import DeviceRepository
from src.dal.entities import EntityRepository
from src.ha import HAClient, parse_entity_list
from src.ha.workarounds import (
    extract_entity_metadata,
    infer_areas_from_entities,
    infer_devices_from_entities,
)
from src.storage.entities import DiscoverySession, DiscoveryStatus


class DiscoverySyncService:
    """Service for synchronizing HA entities to local database.

    Orchestrates the discovery process:
    1. Fetch entities from HA via MCP
    2. Infer areas and devices from entity attributes
    3. Create/update/remove entities in database
    4. Track discovery session statistics
    """

    def __init__(
        self,
        session: AsyncSession,
        ha_client: HAClient,
    ):
        """Initialize sync service.

        Args:
            session: Database session
            ha_client: HA client for HA communication
        """
        self.session = session
        self.ha = ha_client
        self.entity_repo = EntityRepository(session)
        self.device_repo = DeviceRepository(session)
        self.area_repo = AreaRepository(session)
        self.automation_repo = AutomationRepository(session)
        self.script_repo = ScriptRepository(session)
        self.scene_repo = SceneRepository(session)

    async def run_discovery(
        self,
        triggered_by: str = "manual",
        mlflow_run_id: str | None = None,
    ) -> DiscoverySession:
        """Run a full discovery sync.

        Args:
            triggered_by: What triggered this discovery
            mlflow_run_id: MLflow run ID for tracing

        Returns:
            Completed DiscoverySession
        """
        # Create session record
        discovery = DiscoverySession(
            id=str(uuid4()),
            started_at=datetime.now(timezone.utc),
            status=DiscoveryStatus.RUNNING,
            triggered_by=triggered_by,
            mlflow_run_id=mlflow_run_id,
        )
        self.session.add(discovery)
        await self.session.flush()

        try:
            # 1. Fetch all entities from HA
            raw_entities = await self.ha.list_entities(detailed=True)
            entities = parse_entity_list(raw_entities)
            discovery.entities_found = len(entities)

            # 2. Fetch areas (direct HA API with inference fallback)
            inferred_areas = await self._fetch_areas(entities)
            discovery.areas_found = len(inferred_areas)

            # Sync areas
            area_id_mapping = await self._sync_areas(inferred_areas)
            discovery.areas_added = sum(1 for _ in area_id_mapping.values())

            # 3. Infer devices from entities
            inferred_devices = infer_devices_from_entities(entities)
            discovery.devices_found = len(inferred_devices)

            # Sync devices
            device_id_mapping = await self._sync_devices(inferred_devices, area_id_mapping)
            discovery.devices_added = sum(1 for _ in device_id_mapping.values())

            # 4. Sync entities
            stats = await self._sync_entities(entities, area_id_mapping, device_id_mapping)
            discovery.entities_added = stats["added"]
            discovery.entities_updated = stats["updated"]
            discovery.entities_removed = stats["removed"]

            # 5. Get domain breakdown
            discovery.domain_counts = await self.entity_repo.get_domain_counts()

            # 6. Sync automations, scripts, scenes to registry tables
            await self._sync_automation_entities(entities)
            discovery.automations_found = len([e for e in entities if e.domain == "automation"])
            discovery.scripts_found = len([e for e in entities if e.domain == "script"])
            discovery.scenes_found = len([e for e in entities if e.domain == "scene"])

            # Mark complete
            discovery.status = DiscoveryStatus.COMPLETED
            discovery.completed_at = datetime.now(timezone.utc)

            # Record HA gaps encountered
            # areas_via_inference is True only if the HA API returned nothing
            areas_via_api = bool(await self.ha.get_area_registry())
            discovery.mcp_gaps_encountered = {
                "areas_via_inference": not areas_via_api,
                "floors_not_available": True,
                "labels_not_available": True,
                "device_details_not_available": True,
                "script_config_not_available": True,
                "scene_config_not_available": True,
                "services_not_available": True,
            }

        except Exception as e:
            discovery.status = DiscoveryStatus.FAILED
            discovery.error_message = str(e)
            discovery.completed_at = datetime.now(timezone.utc)
            raise

        await self.session.commit()
        return discovery

    async def _fetch_areas(
        self,
        entities: list,
    ) -> dict[str, dict[str, Any]]:
        """Fetch areas from HA REST API, falling back to entity inference.

        Tries the direct HA area registry API first (which provides
        floor_id, icon, picture). Falls back to inferring areas from
        entity attributes if the API returns nothing.

        Args:
            entities: Parsed entities (used as fallback for inference)

        Returns:
            Dictionary mapping area_id to area info
        """
        import logging

        logger = logging.getLogger(__name__)

        # Try direct HA REST API first
        ha_areas = await self.ha.get_area_registry()
        if ha_areas:
            logger.info("Fetched %d areas from HA area registry API", len(ha_areas))
            areas = {}
            for area in ha_areas:
                area_id = area.get("area_id")
                if area_id:
                    areas[area_id] = {
                        "ha_area_id": area_id,
                        "name": area.get("name", area_id),
                        "floor_id": area.get("floor_id"),
                        "icon": area.get("icon"),
                        "picture": area.get("picture"),
                    }
            return areas

        # Fallback: infer from entity attributes
        logger.info("HA area registry API returned empty; falling back to entity inference")
        return infer_areas_from_entities(entities)

    async def _sync_areas(
        self,
        inferred_areas: dict[str, dict[str, Any]],
    ) -> dict[str, str]:
        """Sync areas to database.

        Args:
            inferred_areas: Areas inferred from entities

        Returns:
            Mapping of ha_area_id to internal id
        """
        mapping = {}

        for ha_area_id, area_data in inferred_areas.items():
            area, created = await self.area_repo.upsert({
                "ha_area_id": ha_area_id,
                "name": area_data["name"],
                "floor_id": area_data.get("floor_id"),
                "icon": area_data.get("icon"),
            })
            mapping[ha_area_id] = area.id

        return mapping

    async def _sync_devices(
        self,
        inferred_devices: dict[str, dict[str, Any]],
        area_id_mapping: dict[str, str],
    ) -> dict[str, str]:
        """Sync devices to database.

        Args:
            inferred_devices: Devices inferred from entities
            area_id_mapping: Mapping of ha_area_id to internal id

        Returns:
            Mapping of ha_device_id to internal id
        """
        mapping = {}

        for ha_device_id, device_data in inferred_devices.items():
            # Map area_id
            internal_area_id = None
            if device_data.get("area_id"):
                internal_area_id = area_id_mapping.get(device_data["area_id"])

            device, created = await self.device_repo.upsert({
                "ha_device_id": ha_device_id,
                "name": device_data["name"],
                "area_id": internal_area_id,
                "manufacturer": device_data.get("manufacturer"),
                "model": device_data.get("model"),
                "sw_version": device_data.get("sw_version"),
            })
            mapping[ha_device_id] = device.id

        return mapping

    async def _sync_entities(
        self,
        entities: list[Any],
        area_id_mapping: dict[str, str],
        device_id_mapping: dict[str, str],
    ) -> dict[str, int]:
        """Sync entities to database.

        Args:
            entities: Parsed entities from MCP
            area_id_mapping: Mapping of ha_area_id to internal id
            device_id_mapping: Mapping of ha_device_id to internal id

        Returns:
            Stats dict with added, updated, removed counts
        """
        stats = {"added": 0, "updated": 0, "removed": 0}

        # Get existing entity IDs
        existing_ids = await self.entity_repo.get_all_entity_ids()
        seen_ids: set[str] = set()

        for entity in entities:
            seen_ids.add(entity.entity_id)

            # Extract metadata
            metadata = extract_entity_metadata(entity)

            # Map foreign keys
            internal_area_id = None
            internal_device_id = None

            if entity.area_id:
                internal_area_id = area_id_mapping.get(entity.area_id)
            if entity.device_id:
                internal_device_id = device_id_mapping.get(entity.device_id)

            entity_data = {
                "entity_id": entity.entity_id,
                "domain": entity.domain,
                "name": entity.name,
                "state": entity.state,
                "attributes": entity.attributes,
                "area_id": internal_area_id,
                "device_id": internal_device_id,
                "device_class": metadata.get("device_class"),
                "unit_of_measurement": metadata.get("unit_of_measurement"),
                "supported_features": metadata.get("supported_features", 0),
                "state_class": metadata.get("state_class"),
                "icon": metadata.get("icon"),
                "entity_category": metadata.get("entity_category"),
                "platform": metadata.get("platform"),
            }

            _, created = await self.entity_repo.upsert(entity_data)
            if created:
                stats["added"] += 1
            else:
                stats["updated"] += 1

        # Remove entities no longer in HA
        removed_ids = existing_ids - seen_ids
        for entity_id in removed_ids:
            await self.entity_repo.delete(entity_id)
            stats["removed"] += 1

        return stats

    async def _sync_automation_entities(self, entities: list[Any]) -> dict[str, int]:
        """Sync automation, script, and scene entities to registry tables.

        Populates ha_automations, scripts, and scenes tables from parsed
        entity data. Removes stale records no longer present in HA.

        Args:
            entities: All parsed entities (filters to automation/script/scene)

        Returns:
            Stats dict with automations_synced, scripts_synced, scenes_synced
        """
        stats = {"automations_synced": 0, "scripts_synced": 0, "scenes_synced": 0}

        # Partition entities by domain
        automations = [e for e in entities if e.domain == "automation"]
        scripts = [e for e in entities if e.domain == "script"]
        scenes = [e for e in entities if e.domain == "scene"]

        # --- Automations ---
        seen_automation_ids: set[str] = set()
        for entity in automations:
            attrs = entity.attributes or {}
            ha_automation_id = attrs.get("id", entity.entity_id.split(".", 1)[-1])
            seen_automation_ids.add(ha_automation_id)

            # Fetch full config from HA (trigger/condition/action)
            config: dict[str, Any] | None = None
            try:
                config = await self.ha.get_automation_config(ha_automation_id)
            except Exception as exc:
                logger.warning(
                    "Failed to fetch config for automation %s: %s",
                    ha_automation_id,
                    exc,
                )

            await self.automation_repo.upsert({
                "ha_automation_id": ha_automation_id,
                "entity_id": entity.entity_id,
                "alias": attrs.get("friendly_name", entity.name),
                "state": entity.state or "off",
                "mode": attrs.get("mode", "single"),
                "last_triggered": attrs.get("last_triggered"),
                "config": config,
            })
            stats["automations_synced"] += 1

        # Remove stale automations
        existing_automation_ids = await self.automation_repo.get_all_ha_ids()
        for stale_id in existing_automation_ids - seen_automation_ids:
            await self.automation_repo.delete(stale_id)

        # --- Scripts ---
        seen_script_ids: set[str] = set()
        for entity in scripts:
            attrs = entity.attributes or {}
            seen_script_ids.add(entity.entity_id)

            # Fetch full config from HA (sequence/fields)
            script_id = entity.entity_id.split(".", 1)[-1]
            sequence: list[Any] | None = None
            fields: dict[str, Any] | None = None
            try:
                script_config = await self.ha.get_script_config(script_id)
                if script_config:
                    sequence = script_config.get("sequence")
                    fields = script_config.get("fields")
            except Exception as exc:
                logger.warning(
                    "Failed to fetch config for script %s: %s",
                    script_id,
                    exc,
                )

            await self.script_repo.upsert({
                "entity_id": entity.entity_id,
                "alias": attrs.get("friendly_name", entity.name),
                "state": entity.state or "off",
                "mode": attrs.get("mode", "single"),
                "icon": attrs.get("icon"),
                "last_triggered": attrs.get("last_triggered"),
                "sequence": sequence,
                "fields": fields,
            })
            stats["scripts_synced"] += 1

        # Remove stale scripts
        existing_script_ids = await self.script_repo.get_all_ha_ids()
        for stale_id in existing_script_ids - seen_script_ids:
            await self.script_repo.delete(stale_id)

        # --- Scenes ---
        seen_scene_ids: set[str] = set()
        for entity in scenes:
            attrs = entity.attributes or {}
            seen_scene_ids.add(entity.entity_id)

            await self.scene_repo.upsert({
                "entity_id": entity.entity_id,
                "name": attrs.get("friendly_name", entity.name),
                "icon": attrs.get("icon"),
            })
            stats["scenes_synced"] += 1

        # Remove stale scenes
        existing_scene_ids = await self.scene_repo.get_all_ha_ids()
        for stale_id in existing_scene_ids - seen_scene_ids:
            await self.scene_repo.delete(stale_id)

        return stats

    async def _sync_entities_delta(
        self,
        entities: list[Any],
        area_id_mapping: dict[str, str],
        device_id_mapping: dict[str, str],
    ) -> dict[str, int]:
        """Sync entities using delta logic — skip unchanged ones.

        Compares each entity's ``last_updated`` timestamp from HA against
        the ``last_synced_at`` on the DB record.  Only upserts when the
        entity is new or has been updated since the last sync.

        Args:
            entities: Parsed entities from MCP
            area_id_mapping: Mapping of ha_area_id to internal id
            device_id_mapping: Mapping of ha_device_id to internal id

        Returns:
            Stats dict with added, updated, skipped, removed counts
        """
        stats = {"added": 0, "updated": 0, "skipped": 0, "removed": 0}

        existing_ids = await self.entity_repo.get_all_entity_ids()
        seen_ids: set[str] = set()

        for entity in entities:
            seen_ids.add(entity.entity_id)

            # Check if we can skip this entity
            db_record = await self.entity_repo.get_by_entity_id(entity.entity_id)
            if db_record is not None:
                ha_updated = getattr(entity, "last_updated", None)
                db_synced = db_record.last_synced_at
                if (
                    ha_updated is not None
                    and db_synced is not None
                    and ha_updated <= db_synced
                ):
                    stats["skipped"] += 1
                    continue

            # Entity is new or changed — upsert
            metadata = extract_entity_metadata(entity)

            internal_area_id = None
            internal_device_id = None
            if getattr(entity, "area_id", None):
                internal_area_id = area_id_mapping.get(entity.area_id)
            if getattr(entity, "device_id", None):
                internal_device_id = device_id_mapping.get(entity.device_id)

            entity_data = {
                "entity_id": entity.entity_id,
                "domain": entity.domain,
                "name": entity.name,
                "state": entity.state,
                "attributes": getattr(entity, "attributes", None),
                "area_id": internal_area_id,
                "device_id": internal_device_id,
                "device_class": metadata.get("device_class"),
                "unit_of_measurement": metadata.get("unit_of_measurement"),
                "supported_features": metadata.get("supported_features", 0),
                "state_class": metadata.get("state_class"),
                "icon": metadata.get("icon"),
                "entity_category": metadata.get("entity_category"),
                "platform": metadata.get("platform"),
            }

            _, created = await self.entity_repo.upsert(entity_data)
            if created:
                stats["added"] += 1
            else:
                stats["updated"] += 1

        # Remove entities no longer in HA
        removed_ids = existing_ids - seen_ids
        for entity_id in removed_ids:
            await self.entity_repo.delete(entity_id)
            stats["removed"] += 1

        return stats

    async def run_delta_sync(self) -> dict[str, Any]:
        """Run a lightweight delta sync.

        Fetches all entities from HA, but only writes those that have
        changed since the last sync.  Automation/script configs are
        re-fetched for any registry items that were updated or whose
        config is currently NULL.

        Returns:
            Stats dict with entity and registry sync counts.
        """
        start = time.monotonic()

        raw_entities = await self.ha.list_entities(detailed=True)
        entities = parse_entity_list(raw_entities)

        # Delta entity sync (skips unchanged)
        entity_stats = await self._sync_entities_delta(entities, {}, {})

        # Registry sync (automations/scripts/scenes — always full)
        registry_stats = await self._sync_automation_entities(entities)

        duration = time.monotonic() - start

        await self.session.commit()

        return {
            **entity_stats,
            **registry_stats,
            "duration_seconds": round(duration, 2),
        }


async def run_discovery(
    session: AsyncSession,
    ha_client: HAClient | None = None,
    triggered_by: str = "manual",
) -> DiscoverySession:
    """Convenience function to run discovery.

    Args:
        session: Database session
        ha_client: Optional HA client (creates one if not provided)
        triggered_by: What triggered discovery

    Returns:
        DiscoverySession with results
    """
    if ha_client is None:
        from src.ha import get_ha_client
        ha_client = get_ha_client()

    service = DiscoverySyncService(session, ha_client)
    return await service.run_discovery(triggered_by=triggered_by)


async def run_registry_sync(
    session: AsyncSession,
    ha_client: HAClient | None = None,
) -> dict[str, Any]:
    """Sync only registry items (automations, scripts, scenes).

    Lighter-weight alternative to run_discovery() that skips
    area/device/entity sync and only populates registry tables.

    Args:
        session: Database session
        ha_client: Optional HA client (creates one if not provided)

    Returns:
        Dict with automations_synced, scripts_synced, scenes_synced,
        and duration_seconds.
    """
    if ha_client is None:
        from src.ha import get_ha_client
        ha_client = get_ha_client()

    start = time.monotonic()

    service = DiscoverySyncService(session, ha_client)

    # Fetch entities from HA and parse
    raw_entities = await ha_client.list_entities(detailed=True)
    entities = parse_entity_list(raw_entities)

    # Sync only registry tables
    stats = await service._sync_automation_entities(entities)

    duration = time.monotonic() - start
    stats["duration_seconds"] = round(duration, 2)

    await session.commit()
    return stats
