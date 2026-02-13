"""Unit tests for DiscoverySyncService (src/dal/sync.py).

Covers discovery session creation, entity upsert flow, area/device sync,
error handling and status transitions, and the registry sync helper.
All external dependencies (HA client, repositories, DB session) are mocked.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dal.sync import DiscoverySyncService, run_discovery, run_registry_sync
from src.storage.entities import DiscoveryStatus


def _make_entity(
    entity_id: str,
    domain: str,
    name: str = "Test",
    state: str = "on",
    area_id: str | None = None,
    device_id: str | None = None,
    attributes: dict | None = None,
) -> SimpleNamespace:
    """Create a minimal entity stub matching parse_entity_list output."""
    return SimpleNamespace(
        entity_id=entity_id,
        domain=domain,
        name=name,
        state=state,
        area_id=area_id,
        device_id=device_id,
        attributes=attributes or {},
    )


def _make_service(
    ha_client: MagicMock | None = None,
    session: MagicMock | None = None,
) -> tuple[DiscoverySyncService, MagicMock, MagicMock]:
    """Build a DiscoverySyncService with all repos mocked."""
    sess = session or MagicMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    sess.commit = AsyncMock()

    ha = ha_client or MagicMock()

    with (
        patch("src.dal.sync.EntityRepository") as MockEntityRepo,
        patch("src.dal.sync.DeviceRepository") as MockDeviceRepo,
        patch("src.dal.sync.AreaRepository") as MockAreaRepo,
        patch("src.dal.sync.AutomationRepository") as MockAutoRepo,
        patch("src.dal.sync.ScriptRepository") as MockScriptRepo,
        patch("src.dal.sync.SceneRepository") as MockSceneRepo,
    ):
        # Defaults: all repos return empty structures
        for MockRepo in [
            MockEntityRepo,
            MockDeviceRepo,
            MockAreaRepo,
            MockAutoRepo,
            MockScriptRepo,
            MockSceneRepo,
        ]:
            instance = MockRepo.return_value
            instance.upsert = AsyncMock(return_value=(MagicMock(id="id-1"), True))
            instance.upsert_many = AsyncMock(return_value=([], {"created": 0, "updated": 0}))
            instance.get_all_entity_ids = AsyncMock(return_value=set())
            instance.get_all_ha_ids = AsyncMock(return_value=set())
            instance.get_domain_counts = AsyncMock(return_value={"light": 1})
            instance.delete = AsyncMock()
            instance.delete_by_ha_ids = AsyncMock(return_value=0)

        service = DiscoverySyncService(sess, ha)

    return service, sess, ha


class TestDiscoverySessionCreation:
    """Tests for run_discovery session lifecycle."""

    @pytest.mark.asyncio
    async def test_discovery_creates_session_record(self):
        """run_discovery should add a DiscoverySession to the DB session."""
        service, sess, ha = _make_service()

        ha.list_entities = AsyncMock(return_value=[])
        ha.get_area_registry = AsyncMock(return_value=[])

        with (
            patch("src.dal.sync.parse_entity_list", return_value=[]),
            patch("src.dal.sync.infer_areas_from_entities", return_value={}),
            patch("src.dal.sync.infer_devices_from_entities", return_value={}),
        ):
            result = await service.run_discovery(triggered_by="test")

        sess.add.assert_called_once()
        added = sess.add.call_args[0][0]
        assert added.triggered_by == "test"
        assert result.status == DiscoveryStatus.COMPLETED
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_discovery_sets_failed_on_error(self):
        """If HA client raises, session should be marked FAILED."""
        service, sess, ha = _make_service()

        ha.list_entities = AsyncMock(side_effect=RuntimeError("HA unavailable"))

        with pytest.raises(RuntimeError, match="HA unavailable"):
            await service.run_discovery()

        # The session was added and should be marked failed
        added = sess.add.call_args[0][0]
        assert added.status == DiscoveryStatus.FAILED
        assert "HA unavailable" in added.error_message


class TestEntitySync:
    """Tests for _sync_entities tracking adds/updates/removals."""

    @pytest.mark.asyncio
    async def test_new_entities_counted_as_added(self):
        """New entities should increment 'added' count."""
        service, _, _ = _make_service()

        entities = [
            _make_entity("light.living_room", "light"),
            _make_entity("sensor.temp", "sensor"),
        ]

        service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
        service.entity_repo.upsert_many = AsyncMock(return_value=([], {"created": 2, "updated": 0}))
        service.entity_repo.delete_by_ha_ids = AsyncMock(return_value=0)

        with patch("src.dal.sync.extract_entity_metadata", return_value={}):
            stats = await service._sync_entities(entities, {}, {})

        assert stats["added"] == 2
        assert stats["updated"] == 0
        assert stats["removed"] == 0

    @pytest.mark.asyncio
    async def test_existing_entities_counted_as_updated(self):
        """Existing entities should increment 'updated' count."""
        service, _, _ = _make_service()

        entities = [_make_entity("light.living_room", "light")]

        service.entity_repo.get_all_entity_ids = AsyncMock(return_value={"light.living_room"})
        service.entity_repo.upsert_many = AsyncMock(return_value=([], {"created": 0, "updated": 1}))
        service.entity_repo.delete_by_ha_ids = AsyncMock(return_value=0)

        with patch("src.dal.sync.extract_entity_metadata", return_value={}):
            stats = await service._sync_entities(entities, {}, {})

        assert stats["updated"] == 1
        assert stats["added"] == 0

    @pytest.mark.asyncio
    async def test_stale_entities_removed(self):
        """Entities in DB but not in HA should be batch-deleted."""
        service, _, _ = _make_service()

        entities = [_make_entity("light.living_room", "light")]

        service.entity_repo.get_all_entity_ids = AsyncMock(
            return_value={"light.living_room", "switch.old_device"}
        )
        service.entity_repo.upsert_many = AsyncMock(return_value=([], {"created": 0, "updated": 1}))
        service.entity_repo.delete_by_ha_ids = AsyncMock(return_value=1)

        with patch("src.dal.sync.extract_entity_metadata", return_value={}):
            stats = await service._sync_entities(entities, {}, {})

        assert stats["removed"] == 1
        service.entity_repo.delete_by_ha_ids.assert_called_once_with({"switch.old_device"})

    @pytest.mark.asyncio
    async def test_area_and_device_ids_mapped(self):
        """Entity sync should map HA area/device IDs to internal IDs."""
        service, _, _ = _make_service()

        entities = [
            _make_entity(
                "light.living_room",
                "light",
                area_id="living_room",
                device_id="dev-1",
            ),
        ]

        service.entity_repo.get_all_entity_ids = AsyncMock(return_value=set())
        service.entity_repo.upsert_many = AsyncMock(return_value=([], {"created": 1, "updated": 0}))
        service.entity_repo.delete_by_ha_ids = AsyncMock(return_value=0)

        area_mapping = {"living_room": "internal-area-uuid"}
        device_mapping = {"dev-1": "internal-device-uuid"}

        with patch("src.dal.sync.extract_entity_metadata", return_value={}):
            await service._sync_entities(entities, area_mapping, device_mapping)

        # Check that the data passed to upsert_many has correct mapped IDs
        call_data_list = service.entity_repo.upsert_many.call_args[0][0]
        assert call_data_list[0]["area_id"] == "internal-area-uuid"
        assert call_data_list[0]["device_id"] == "internal-device-uuid"


class TestAreaSync:
    """Tests for _sync_areas and _fetch_areas."""

    @pytest.mark.asyncio
    async def test_sync_areas_upserts_and_returns_mapping(self):
        """_sync_areas should batch upsert areas and return id mapping."""
        service, _, _ = _make_service()

        mock_area = MagicMock(id="internal-uuid", ha_area_id="living_room")
        service.area_repo.upsert_many = AsyncMock(
            return_value=([mock_area], {"created": 1, "updated": 0})
        )

        areas = {
            "living_room": {"name": "Living Room", "floor_id": "ground"},
        }

        mapping = await service._sync_areas(areas)

        assert mapping == {"living_room": "internal-uuid"}
        service.area_repo.upsert_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_areas_prefers_ha_api(self):
        """_fetch_areas should use HA area registry when available."""
        service, _, ha = _make_service()

        ha.get_area_registry = AsyncMock(
            return_value=[
                {"area_id": "living_room", "name": "Living Room", "floor_id": "ground"},
            ]
        )

        result = await service._fetch_areas(entities=[])

        assert "living_room" in result
        assert result["living_room"]["name"] == "Living Room"

    @pytest.mark.asyncio
    async def test_fetch_areas_falls_back_to_inference(self):
        """_fetch_areas should infer from entities when HA API returns empty."""
        service, _, ha = _make_service()

        ha.get_area_registry = AsyncMock(return_value=[])

        inferred = {"bedroom": {"ha_area_id": "bedroom", "name": "Bedroom"}}
        with patch("src.dal.sync.infer_areas_from_entities", return_value=inferred):
            result = await service._fetch_areas(entities=[])

        assert "bedroom" in result


class TestAutomationRegistrySync:
    """Tests for _sync_automation_entities."""

    @pytest.mark.asyncio
    async def test_syncs_automations_scripts_scenes(self):
        """Should upsert each entity type and remove stale records."""
        service, _, _ = _make_service()

        entities = [
            _make_entity(
                "automation.morning",
                "automation",
                attributes={"id": "morning", "friendly_name": "Morning Routine"},
            ),
            _make_entity(
                "script.reboot",
                "script",
                attributes={"friendly_name": "Reboot All"},
            ),
            _make_entity(
                "scene.movie",
                "scene",
                attributes={"friendly_name": "Movie Night"},
            ),
        ]

        # No stale records
        service.automation_repo.get_all_ha_ids = AsyncMock(return_value=set())
        service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        stats = await service._sync_automation_entities(entities)

        assert stats["automations_synced"] == 1
        assert stats["scripts_synced"] == 1
        assert stats["scenes_synced"] == 1

    @pytest.mark.asyncio
    async def test_removes_stale_automations(self):
        """Stale automation IDs should be deleted."""
        service, _, _ = _make_service()

        entities = [
            _make_entity("automation.current", "automation", attributes={"id": "current"}),
        ]

        service.automation_repo.get_all_ha_ids = AsyncMock(return_value={"current", "old_deleted"})
        service.script_repo.get_all_ha_ids = AsyncMock(return_value=set())
        service.scene_repo.get_all_ha_ids = AsyncMock(return_value=set())

        await service._sync_automation_entities(entities)

        service.automation_repo.delete.assert_called_once_with("old_deleted")


class TestConvenienceFunctions:
    """Tests for run_discovery() and run_registry_sync() module functions."""

    @pytest.mark.asyncio
    async def test_run_discovery_creates_client_if_none(self):
        """run_discovery() should create an HA client if not provided."""
        mock_session = MagicMock()
        mock_ha = MagicMock()

        with (
            patch("src.dal.sync.DiscoverySyncService") as MockService,
            patch("src.ha.get_ha_client", return_value=mock_ha) as get_ha,
        ):
            mock_instance = MockService.return_value
            mock_instance.run_discovery = AsyncMock()

            await run_discovery(mock_session, ha_client=None, triggered_by="test")

            get_ha.assert_called_once()
            MockService.assert_called_once_with(mock_session, mock_ha)

    @pytest.mark.asyncio
    async def test_run_registry_sync_returns_stats_with_duration(self):
        """run_registry_sync() should return stats including duration."""
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_ha = MagicMock()
        mock_ha.list_entities = AsyncMock(return_value=[])

        with (
            patch("src.dal.sync.DiscoverySyncService") as MockService,
            patch("src.dal.sync.parse_entity_list", return_value=[]),
        ):
            mock_instance = MockService.return_value
            mock_instance._sync_automation_entities = AsyncMock(
                return_value={"automations_synced": 0, "scripts_synced": 0, "scenes_synced": 0}
            )

            result = await run_registry_sync(mock_session, ha_client=mock_ha)

        assert "duration_seconds" in result
        assert isinstance(result["duration_seconds"], float)
        mock_session.commit.assert_called_once()
