"""Unit tests for Librarian agent and workflow.

Tests LibrarianWorkflow and run_librarian_discovery with mocked HA client and DB.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.librarian import LibrarianWorkflow, run_librarian_discovery
from src.graph.state import AgentRole, DiscoveryState, DiscoveryStatus, EntitySummary


@pytest.fixture
def mock_ha_client():
    """Create a mock HA client."""
    client = MagicMock()
    client.list_entities = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


class TestLibrarianWorkflow:
    """Tests for LibrarianWorkflow class."""

    def test_init_with_ha_client(self, mock_ha_client):
        """Test initializing workflow with HA client."""
        workflow = LibrarianWorkflow(ha_client=mock_ha_client)

        assert workflow._ha_client == mock_ha_client

    def test_init_without_ha_client(self):
        """Test initializing workflow without HA client."""
        workflow = LibrarianWorkflow()

        assert workflow._ha_client is None

    @pytest.mark.asyncio
    async def test_ha_property_creates_client(self):
        """Test that ha property creates client if not provided."""
        workflow = LibrarianWorkflow()

        with patch("src.ha.get_ha_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            client = workflow.ha

            assert client == mock_client
            assert workflow._ha_client == mock_client

    async def test_ha_property_reuses_client(self, mock_ha_client):
        """Test that ha property reuses existing client."""
        workflow = LibrarianWorkflow(ha_client=mock_ha_client)

        client1 = workflow.ha
        client2 = workflow.ha

        assert client1 == client2 == mock_ha_client

    async def test_run_discovery_success(self, mock_ha_client):
        """Test successful discovery run."""
        workflow = LibrarianWorkflow(ha_client=mock_ha_client)

        # Mock entity data
        mock_entities = [
            {
                "entity_id": "light.living_room",
                "domain": "light",
                "name": "Living Room Light",
                "state": "on",
                "area_id": "area-living-room",
                "device_id": "device-light-1",
            }
        ]

        mock_ha_client.list_entities = AsyncMock(return_value=mock_entities)

        # Mock parse_entity_list
        mock_parsed = MagicMock()
        mock_parsed.entity_id = "light.living_room"
        mock_parsed.domain = "light"
        mock_parsed.name = "Living Room Light"
        mock_parsed.state = "on"
        mock_parsed.area_id = "area-living-room"
        mock_parsed.device_id = "device-light-1"

        # Mock sync service
        mock_discovery = MagicMock()
        mock_discovery.id = "discovery-uuid-1"
        mock_discovery.status = "completed"
        mock_discovery.entities_added = 1
        mock_discovery.entities_updated = 0
        mock_discovery.entities_removed = 0
        mock_discovery.devices_found = 1
        mock_discovery.areas_found = 1

        with (
            patch("src.ha.parse_entity_list", return_value=[mock_parsed]),
            patch("src.agents.librarian.start_experiment_run") as mock_start_run,
            patch("src.agents.librarian.log_param"),
            patch("src.agents.librarian.log_metric"),
            patch("src.agents.librarian.log_dict"),
            patch("src.storage.get_session") as mock_get_session,
            patch("src.agents.librarian.DiscoverySyncService") as MockSyncService,
        ):
            # Setup mock context manager
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_start_run.return_value = mock_context

            # Setup mock run
            mock_run = MagicMock()
            mock_run.info.run_id = "run-uuid-1"
            mock_context.__enter__.return_value = mock_run

            # Setup mock session
            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            # Setup mock sync service
            mock_sync_service = MagicMock()
            mock_sync_service.run_discovery = AsyncMock(return_value=mock_discovery)
            MockSyncService.return_value = mock_sync_service

            state = await workflow.run_discovery(triggered_by="test")

            assert state.status == DiscoveryStatus.COMPLETED
            assert state.entities_added == 1
            assert state.devices_found == 1
            assert state.areas_found == 1
            assert len(state.entities_found) == 1
            assert state.entities_found[0].entity_id == "light.living_room"

    async def test_run_discovery_with_domain_filter(self, mock_ha_client):
        """Test discovery run with domain filter."""
        workflow = LibrarianWorkflow(ha_client=mock_ha_client)

        mock_ha_client.list_entities = AsyncMock(return_value=[])

        with (
            patch("src.ha.parse_entity_list", return_value=[]),
            patch("src.agents.librarian.start_experiment_run") as mock_start_run,
            patch("src.agents.librarian.log_param"),
            patch("src.agents.librarian.log_metric"),
            patch("src.agents.librarian.log_dict"),
            patch("src.storage.get_session") as mock_get_session,
            patch("src.agents.librarian.DiscoverySyncService") as MockSyncService,
        ):
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_start_run.return_value = mock_context

            mock_run = MagicMock()
            mock_run.info.run_id = "run-uuid-1"
            mock_context.__enter__.return_value = mock_run

            mock_session = MagicMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_discovery = MagicMock()
            mock_discovery.id = "discovery-uuid-1"
            mock_discovery.status = "completed"
            mock_discovery.entities_added = 0
            mock_discovery.entities_updated = 0
            mock_discovery.entities_removed = 0
            mock_discovery.devices_found = 0
            mock_discovery.areas_found = 0

            mock_sync_service = MagicMock()
            mock_sync_service.run_discovery = AsyncMock(return_value=mock_discovery)
            MockSyncService.return_value = mock_sync_service

            await workflow.run_discovery(triggered_by="test", domain_filter="light")

            # Verify domain filter was passed to list_entities
            mock_ha_client.list_entities.assert_called_once_with(domain="light", detailed=True)
            # Verify domain filter was used
            assert True

    async def test_run_discovery_handles_error(self, mock_ha_client):
        """Test discovery run handles errors."""
        workflow = LibrarianWorkflow(ha_client=mock_ha_client)

        mock_ha_client.list_entities = AsyncMock(side_effect=Exception("HA error"))

        with (
            patch("src.agents.librarian.start_experiment_run") as mock_start_run,
            patch("src.agents.librarian.log_param"),
            patch("src.agents.librarian.log_metric"),
            patch("src.agents.librarian.log_dict"),
        ):
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_start_run.return_value = mock_context

            mock_run = MagicMock()
            mock_run.info.run_id = "run-uuid-1"
            mock_context.__enter__.return_value = mock_run

            with pytest.raises(Exception, match="HA error"):
                await workflow.run_discovery(triggered_by="test")

            # Verify error was raised
            assert True

    async def test_log_discovery_session(self, mock_ha_client):
        """Test that discovery session is logged as artifact."""
        workflow = LibrarianWorkflow(ha_client=mock_ha_client)

        state = DiscoveryState(
            current_agent=AgentRole.LIBRARIAN,
            status=DiscoveryStatus.COMPLETED,
        )
        state.entities_found = [
            EntitySummary(
                entity_id="light.living_room",
                domain="light",
                name="Living Room Light",
                state="on",
                area_id="area-living-room",
                device_id="device-light-1",
            )
        ]
        state.entities_added = 1
        state.entities_updated = 0
        state.entities_removed = 0
        state.devices_found = 1
        state.areas_found = 1
        state.domains_scanned = ["light"]

        with (
            patch("src.agents.librarian.log_dict") as mock_log_dict,
            patch("time.time", return_value=1234567890),
        ):
            workflow._log_discovery_session(state, "test", None)

            mock_log_dict.assert_called_once()
            call_args = mock_log_dict.call_args[0]
            artifact_data = call_args[0]
            assert artifact_data["agent"] == "Librarian"
            assert artifact_data["triggered_by"] == "test"
            assert artifact_data["status"] == "completed"
            assert "summary" in artifact_data
            assert artifact_data["summary"]["entities_found"] == 1
            assert artifact_data["summary"]["entities_added"] == 1


@pytest.mark.asyncio
class TestRunLibrarianDiscovery:
    """Tests for run_librarian_discovery convenience function."""

    async def test_run_librarian_discovery_creates_workflow(self, mock_ha_client):
        """Test that run_librarian_discovery creates workflow and runs discovery."""
        with (
            patch("src.agents.librarian.LibrarianWorkflow") as MockWorkflow,
            patch("src.agents.librarian.start_experiment_run"),
            patch("src.agents.librarian.log_param"),
            patch("src.agents.librarian.log_metric"),
            patch("src.agents.librarian.log_dict"),
            patch("src.storage.get_session"),
            patch("src.agents.librarian.DiscoverySyncService"),
        ):
            mock_workflow = MagicMock()
            mock_state = DiscoveryState(
                current_agent=AgentRole.LIBRARIAN, status=DiscoveryStatus.COMPLETED
            )
            mock_workflow.run_discovery = AsyncMock(return_value=mock_state)
            MockWorkflow.return_value = mock_workflow

            result = await run_librarian_discovery(triggered_by="test", ha_client=mock_ha_client)

            assert result == mock_state
            MockWorkflow.assert_called_once_with(ha_client=mock_ha_client)
            mock_workflow.run_discovery.assert_called_once_with(
                triggered_by="test", domain_filter=None
            )

    async def test_run_librarian_discovery_with_domain_filter(self):
        """Test run_librarian_discovery with domain filter."""
        with (
            patch("src.agents.librarian.LibrarianWorkflow") as MockWorkflow,
            patch("src.agents.librarian.start_experiment_run"),
            patch("src.agents.librarian.log_param"),
            patch("src.agents.librarian.log_metric"),
            patch("src.agents.librarian.log_dict"),
            patch("src.storage.get_session"),
            patch("src.agents.librarian.DiscoverySyncService"),
        ):
            mock_workflow = MagicMock()
            mock_state = DiscoveryState(
                current_agent=AgentRole.LIBRARIAN, status=DiscoveryStatus.COMPLETED
            )
            mock_workflow.run_discovery = AsyncMock(return_value=mock_state)
            MockWorkflow.return_value = mock_workflow

            await run_librarian_discovery(triggered_by="test", domain_filter="light")

            mock_workflow.run_discovery.assert_called_once_with(
                triggered_by="test", domain_filter="light"
            )
