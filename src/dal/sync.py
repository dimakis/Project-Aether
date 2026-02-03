"""Discovery sync service for orchestrating HA synchronization."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.dal.areas import AreaRepository
from src.dal.devices import DeviceRepository
from src.dal.entities import EntityRepository
from src.mcp import MCPClient, parse_entity_list
from src.mcp.workarounds import (
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
        mcp_client: MCPClient,
    ):
        """Initialize sync service.

        Args:
            session: Database session
            mcp_client: MCP client for HA communication
        """
        self.session = session
        self.mcp = mcp_client
        self.entity_repo = EntityRepository(session)
        self.device_repo = DeviceRepository(session)
        self.area_repo = AreaRepository(session)

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
            started_at=datetime.utcnow(),
            status=DiscoveryStatus.RUNNING,
            triggered_by=triggered_by,
            mlflow_run_id=mlflow_run_id,
        )
        self.session.add(discovery)
        await self.session.flush()

        try:
            # 1. Fetch all entities from HA
            raw_entities = await self.mcp.list_entities(detailed=True)
            entities = parse_entity_list(raw_entities)
            discovery.entities_found = len(entities)

            # 2. Infer areas from entities
            inferred_areas = infer_areas_from_entities(entities)
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

            # 6. Sync automations, scripts, scenes
            await self._sync_automation_entities(entities)
            discovery.automations_found = len([e for e in entities if e.domain == "automation"])
            discovery.scripts_found = len([e for e in entities if e.domain == "script"])
            discovery.scenes_found = len([e for e in entities if e.domain == "scene"])

            # Mark complete
            discovery.status = DiscoveryStatus.COMPLETED
            discovery.completed_at = datetime.utcnow()

            # Record MCP gaps encountered
            discovery.mcp_gaps_encountered = {
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
            discovery.completed_at = datetime.utcnow()
            raise

        await self.session.commit()
        return discovery

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

    async def _sync_automation_entities(self, entities: list[Any]) -> None:
        """Sync automation, script, and scene entities.

        Args:
            entities: All parsed entities
        """
        # For now, just rely on the main entity sync
        # Detailed automation/script/scene records would need additional MCP tools
        pass


async def run_discovery(
    session: AsyncSession,
    mcp_client: MCPClient | None = None,
    triggered_by: str = "manual",
) -> DiscoverySession:
    """Convenience function to run discovery.

    Args:
        session: Database session
        mcp_client: Optional MCP client (creates one if not provided)
        triggered_by: What triggered discovery

    Returns:
        DiscoverySession with results
    """
    if mcp_client is None:
        from src.mcp import get_mcp_client
        mcp_client = get_mcp_client()

    service = DiscoverySyncService(session, mcp_client)
    return await service.run_discovery(triggered_by=triggered_by)
