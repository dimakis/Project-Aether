"""Unit tests for discovery workflow nodes (src/graph/nodes/discovery.py).

All HA client, DAL, and MLflow calls are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import AgentRole, DiscoveryState, DiscoveryStatus, EntitySummary


def _make_state(**overrides) -> MagicMock:
    """Create a mock DiscoveryState."""
    state = MagicMock(spec=DiscoveryState)
    state.run_id = "run-1"
    state.mlflow_run_id = None
    state.entities_found = []
    state.domains_scanned = []
    state.devices_found = 0
    state.areas_found = 0
    state.services_found = 0
    state.entities_added = 0
    state.entities_updated = 0
    state.entities_removed = 0
    state.status = DiscoveryStatus.RUNNING
    state.errors = []
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


class TestInitializeDiscoveryNode:
    async def test_sets_running_status(self):
        from src.graph.nodes.discovery import initialize_discovery_node

        state = _make_state()
        result = await initialize_discovery_node(state)
        assert result["current_agent"] == AgentRole.LIBRARIAN
        assert result["status"] == DiscoveryStatus.RUNNING


class TestFetchEntitiesNode:
    async def test_fetches_and_parses_entities(self):
        from src.graph.nodes.discovery import fetch_entities_node

        mock_entity = MagicMock()
        mock_entity.entity_id = "light.kitchen"
        mock_entity.domain = "light"
        mock_entity.name = "Kitchen Light"
        mock_entity.state = "on"
        mock_entity.area_id = "kitchen"
        mock_entity.device_id = "dev-1"

        mock_ha = MagicMock()
        mock_ha.list_entities = AsyncMock(return_value=[{"entity_id": "light.kitchen"}])

        with patch("src.ha.parse_entity_list", return_value=[mock_entity]):
            result = await fetch_entities_node(_make_state(), ha_client=mock_ha)

        assert len(result["entities_found"]) == 1
        assert result["entities_found"][0].entity_id == "light.kitchen"
        assert "light" in result["domains_scanned"]

    async def test_creates_ha_client_if_none(self):
        from src.graph.nodes.discovery import fetch_entities_node

        mock_ha = MagicMock()
        mock_ha.list_entities = AsyncMock(return_value=[])

        with (
            patch("src.ha.get_ha_client", return_value=mock_ha),
            patch("src.ha.parse_entity_list", return_value=[]),
        ):
            result = await fetch_entities_node(_make_state())
            assert result["entities_found"] == []


class TestInferDevicesNode:
    async def test_counts_unique_devices(self):
        from src.graph.nodes.discovery import infer_devices_node

        entities = [
            EntitySummary(
                entity_id="light.kitchen",
                domain="light",
                name="Kitchen Light",
                state="on",
                device_id="dev-1",
            ),
            EntitySummary(
                entity_id="switch.kitchen",
                domain="switch",
                name="Kitchen Switch",
                state="off",
                device_id="dev-1",
            ),
            EntitySummary(
                entity_id="light.bedroom",
                domain="light",
                name="Bedroom Light",
                state="on",
                device_id="dev-2",
            ),
        ]
        state = _make_state(entities_found=entities)
        result = await infer_devices_node(state)
        assert result["devices_found"] == 2

    async def test_no_devices(self):
        from src.graph.nodes.discovery import infer_devices_node

        entities = [
            EntitySummary(
                entity_id="light.test",
                domain="light",
                name="Test",
                state="on",
            ),
        ]
        state = _make_state(entities_found=entities)
        result = await infer_devices_node(state)
        assert result["devices_found"] == 0


class TestInferAreasNode:
    async def test_counts_unique_areas(self):
        from src.graph.nodes.discovery import infer_areas_node

        entities = [
            EntitySummary(
                entity_id="light.kitchen",
                domain="light",
                name="Kitchen Light",
                state="on",
                area_id="kitchen",
            ),
            EntitySummary(
                entity_id="light.bedroom",
                domain="light",
                name="Bedroom Light",
                state="on",
                area_id="bedroom",
            ),
        ]
        state = _make_state(entities_found=entities)
        result = await infer_areas_node(state)
        assert result["areas_found"] == 2


class TestSyncAutomationsNode:
    async def test_sync_success(self):
        from src.graph.nodes.discovery import sync_automations_node

        mock_ha = MagicMock()
        mock_ha.list_automations = AsyncMock(return_value=[{"id": "a1"}, {"id": "a2"}])

        scripts = [
            EntitySummary(entity_id="script.test", domain="script", name="Test", state="on"),
        ]
        state = _make_state(entities_found=scripts)

        result = await sync_automations_node(state, ha_client=mock_ha)
        assert result["services_found"] == 3  # 2 automations + 1 script

    async def test_sync_error_handled(self):
        from src.graph.nodes.discovery import sync_automations_node

        mock_ha = MagicMock()
        mock_ha.list_automations = AsyncMock(side_effect=Exception("HA unavailable"))

        state = _make_state(errors=[])
        result = await sync_automations_node(state, ha_client=mock_ha)
        assert "errors" in result
        assert any("Automation sync warning" in e for e in result["errors"])


class TestPersistEntitiesNode:
    async def test_persist_with_session(self):
        from src.graph.nodes.discovery import persist_entities_node

        mock_session = AsyncMock()
        mock_ha = MagicMock()

        mock_discovery = MagicMock()
        mock_discovery.entities_added = 5
        mock_discovery.entities_updated = 2
        mock_discovery.entities_removed = 1

        mock_sync = MagicMock()
        mock_sync.run_discovery = AsyncMock(return_value=mock_discovery)

        with patch("src.dal.DiscoverySyncService", return_value=mock_sync):
            result = await persist_entities_node(
                _make_state(), session=mock_session, ha_client=mock_ha
            )
            assert result["entities_added"] == 5
            assert result["status"] == DiscoveryStatus.COMPLETED

    async def test_persist_without_session(self):
        from src.graph.nodes.discovery import persist_entities_node

        mock_ha = MagicMock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_discovery = MagicMock()
        mock_discovery.entities_added = 3
        mock_discovery.entities_updated = 0
        mock_discovery.entities_removed = 0

        mock_sync = MagicMock()
        mock_sync.run_discovery = AsyncMock(return_value=mock_discovery)

        with (
            patch("src.storage.get_session", return_value=mock_session),
            patch("src.ha.get_ha_client", return_value=mock_ha),
            patch("src.dal.DiscoverySyncService", return_value=mock_sync),
        ):
            result = await persist_entities_node(_make_state())
            assert result["entities_added"] == 3


class TestFinalizeDiscoveryNode:
    async def test_finalize_completed(self):
        from src.graph.nodes.discovery import finalize_discovery_node

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        state = _make_state(
            entities_found=[MagicMock()],
            entities_added=1,
            entities_updated=0,
            entities_removed=0,
            devices_found=1,
            areas_found=1,
            domains_scanned=["light"],
            errors=[],
            status=DiscoveryStatus.RUNNING,
        )

        with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
            result = await finalize_discovery_node(state)
            assert result["status"] == DiscoveryStatus.COMPLETED

    async def test_finalize_with_errors(self):
        from src.graph.nodes.discovery import finalize_discovery_node

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = None

        state = _make_state(errors=["something failed"])

        with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
            result = await finalize_discovery_node(state)
            assert result["status"] == DiscoveryStatus.FAILED


class TestErrorHandlerNode:
    async def test_error_handler(self):
        from src.graph.nodes.discovery import error_handler_node

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        state = _make_state(errors=[])
        error = RuntimeError("Discovery failed")

        with patch.dict("sys.modules", {"mlflow": mock_mlflow}):
            result = await error_handler_node(state, error=error)
            assert result["status"] == DiscoveryStatus.FAILED
            assert "RuntimeError" in result["errors"][0]


class TestRunDiscoveryNode:
    async def test_delegates_to_workflow(self):
        from src.graph.nodes.discovery import run_discovery_node

        mock_result = MagicMock()
        mock_result.entities_found = [MagicMock()]
        mock_result.entities_added = 2
        mock_result.entities_updated = 1
        mock_result.entities_removed = 0
        mock_result.devices_found = 3
        mock_result.areas_found = 2
        mock_result.status = DiscoveryStatus.COMPLETED
        mock_result.errors = []

        with patch(
            "src.graph.workflows.run_discovery_workflow",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await run_discovery_node(_make_state())
            assert result["entities_added"] == 2
            assert result["status"] == DiscoveryStatus.COMPLETED
