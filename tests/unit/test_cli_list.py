"""Unit tests for CLI list commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli.main import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_entity_repo():
    """Mock entity repository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_area_repo():
    """Mock area repository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_device_repo():
    """Mock device repository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_service_repo():
    """Mock service repository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    return repo


class TestListEntities:
    """Test entities list command."""

    def test_list_entities_no_results(self, runner, mock_session, mock_entity_repo):
        """Test listing entities when none exist."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["entities"])

            assert result.exit_code == 0
            assert "No entities found" in result.stdout

    def test_list_entities_with_results(self, runner, mock_session, mock_entity_repo):
        """Test listing entities with results."""
        from src.storage.entities.ha_entity import HAEntity

        mock_entities = [
            HAEntity(
                id="1",
                entity_id="light.living_room",
                name="Living Room Light",
                domain="light",
                state="on",
            ),
            HAEntity(
                id="2",
                entity_id="switch.kitchen",
                name="Kitchen Switch",
                domain="switch",
                state="off",
            ),
        ]

        mock_entity_repo.list_all = AsyncMock(return_value=mock_entities)
        mock_entity_repo.count = AsyncMock(return_value=2)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["entities"])

            assert result.exit_code == 0
            assert "Entities (2/2)" in result.stdout
            assert "light.living_room" in result.stdout
            assert "switch.kitchen" in result.stdout

    def test_list_entities_with_domain_filter(self, runner, mock_session, mock_entity_repo):
        """Test listing entities with domain filter."""
        from src.storage.entities.ha_entity import HAEntity

        mock_entities = [
            HAEntity(
                id="1",
                entity_id="light.living_room",
                name="Living Room Light",
                domain="light",
                state="on",
            ),
        ]

        mock_entity_repo.list_all = AsyncMock(return_value=mock_entities)
        mock_entity_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["entities", "--domain", "light"])

            assert result.exit_code == 0
            mock_entity_repo.list_all.assert_called_once_with(domain="light", limit=50)

    def test_list_entities_with_limit(self, runner, mock_session, mock_entity_repo):
        """Test listing entities with limit."""
        mock_entity_repo.list_all = AsyncMock(return_value=[])
        mock_entity_repo.count = AsyncMock(return_value=0)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["entities", "--limit", "10"])

            assert result.exit_code == 0
            mock_entity_repo.list_all.assert_called_once_with(domain=None, limit=10)


class TestListAreas:
    """Test areas list command."""

    def test_list_areas_no_results(self, runner, mock_session, mock_area_repo):
        """Test listing areas when none exist."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.areas.AreaRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_area_repo

            result = runner.invoke(app, ["areas"])

            assert result.exit_code == 0
            assert "No areas found" in result.stdout

    def test_list_areas_with_results(self, runner, mock_session, mock_area_repo):
        """Test listing areas with results."""
        from src.storage.entities.area import Area

        mock_area = Area(id="1", ha_area_id="living_room", name="Living Room")
        mock_area.entities = []

        mock_area_repo.list_all = AsyncMock(return_value=[mock_area])

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.areas.AreaRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_area_repo

            result = runner.invoke(app, ["areas"])

            assert result.exit_code == 0
            assert "Areas" in result.stdout
            assert "living_room" in result.stdout


class TestListDevices:
    """Test devices list command."""

    def test_list_devices_no_results(self, runner, mock_session, mock_device_repo):
        """Test listing devices when none exist."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.devices.DeviceRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_device_repo

            result = runner.invoke(app, ["devices"])

            assert result.exit_code == 0
            assert "No devices found" in result.stdout

    def test_list_devices_with_results(self, runner, mock_session, mock_device_repo):
        """Test listing devices with results."""
        from src.storage.entities.area import Area
        from src.storage.entities.device import Device

        mock_area = Area(id="1", ha_area_id="living_room", name="Living Room")
        mock_device = Device(
            id="1",
            ha_device_id="abc123",
            name="Smart Light",
            manufacturer="Test Corp",
            model="TL-100",
        )
        mock_device.area = mock_area
        mock_device.entities = []

        mock_device_repo.list_all = AsyncMock(return_value=[mock_device])
        mock_device_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.devices.DeviceRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_device_repo

            result = runner.invoke(app, ["devices"])

            assert result.exit_code == 0
            assert "Devices (1/1)" in result.stdout
            assert "Smart Light" in result.stdout


class TestListAutomations:
    """Test automations list command."""

    def test_list_automations_no_results(self, runner, mock_session, mock_entity_repo):
        """Test listing automations when none exist."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["automations"])

            assert result.exit_code == 0
            assert "No automations found" in result.stdout

    def test_list_automations_with_results(self, runner, mock_session, mock_entity_repo):
        """Test listing automations with results."""
        from src.storage.entities.ha_entity import HAEntity

        mock_automation = HAEntity(
            id="1",
            entity_id="automation.morning_routine",
            name="Morning Routine",
            domain="automation",
            state="on",
            attributes={"mode": "single"},
        )

        mock_entity_repo.list_all = AsyncMock(return_value=[mock_automation])
        mock_entity_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["automations"])

            assert result.exit_code == 0
            assert "Automations" in result.stdout
            assert "automation.morning_routine" in result.stdout

    def test_list_automations_with_state_filter(self, runner, mock_session, mock_entity_repo):
        """Test listing automations with state filter."""
        from src.storage.entities.ha_entity import HAEntity

        mock_automation = HAEntity(
            id="1",
            entity_id="automation.morning_routine",
            name="Morning Routine",
            domain="automation",
            state="on",
            attributes={"mode": "single"},
        )

        mock_entity_repo.list_all = AsyncMock(return_value=[mock_automation])
        mock_entity_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["automations", "--state", "on"])

            assert result.exit_code == 0
            assert "automation.morning_routine" in result.stdout


class TestListScripts:
    """Test scripts list command."""

    def test_list_scripts_no_results(self, runner, mock_session, mock_entity_repo):
        """Test listing scripts when none exist."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["scripts"])

            assert result.exit_code == 0
            assert "No scripts found" in result.stdout

    def test_list_scripts_with_results(self, runner, mock_session, mock_entity_repo):
        """Test listing scripts with results."""
        from src.storage.entities.ha_entity import HAEntity

        mock_script = HAEntity(
            id="1",
            entity_id="script.turn_on_lights",
            name="Turn On Lights",
            domain="script",
            state="off",
            attributes={"mode": "single", "icon": "mdi:lightbulb"},
        )

        mock_entity_repo.list_all = AsyncMock(return_value=[mock_script])
        mock_entity_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["scripts"])

            assert result.exit_code == 0
            assert "Scripts" in result.stdout
            assert "script.turn_on_lights" in result.stdout


class TestListScenes:
    """Test scenes list command."""

    def test_list_scenes_no_results(self, runner, mock_session, mock_entity_repo):
        """Test listing scenes when none exist."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["scenes"])

            assert result.exit_code == 0
            assert "No scenes found" in result.stdout

    def test_list_scenes_with_results(self, runner, mock_session, mock_entity_repo):
        """Test listing scenes with results."""
        from src.storage.entities.ha_entity import HAEntity

        mock_scene = HAEntity(
            id="1",
            entity_id="scene.evening",
            name="Evening Scene",
            domain="scene",
            state="unknown",
            attributes={"icon": "mdi:weather-sunset"},
        )

        mock_entity_repo.list_all = AsyncMock(return_value=[mock_scene])
        mock_entity_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.entities.EntityRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_entity_repo

            result = runner.invoke(app, ["scenes"])

            assert result.exit_code == 0
            assert "Scenes" in result.stdout
            assert "scene.evening" in result.stdout


class TestListServices:
    """Test services list command."""

    def test_list_services_no_results(self, runner, mock_session, mock_service_repo):
        """Test listing services when none exist."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.services.ServiceRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_service_repo

            result = runner.invoke(app, ["services"])

            assert result.exit_code == 0
            assert "No services found" in result.stdout

    def test_list_services_with_results(self, runner, mock_session, mock_service_repo):
        """Test listing services with results."""
        from src.storage.entities.ha_automation import Service

        mock_service = Service(
            id="1",
            domain="light",
            service="turn_on",
            name="Turn On",
            is_seeded=True,
        )

        mock_service_repo.list_all = AsyncMock(return_value=[mock_service])
        mock_service_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.services.ServiceRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_service_repo

            result = runner.invoke(app, ["services"])

            assert result.exit_code == 0
            assert "Services" in result.stdout
            assert "light.turn_on" in result.stdout


class TestSeedServices:
    """Test seed-services command."""

    def test_seed_services_success(self, runner, mock_session):
        """Test seeding services successfully."""
        mock_stats = {"added": 10, "skipped": 5}

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.services.seed_services") as mock_seed,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_seed.return_value = mock_stats

            result = runner.invoke(app, ["seed-services"])

            assert result.exit_code == 0
            assert "Services seeded successfully" in result.stdout
            assert "Added: 10" in result.stdout
            assert "Skipped" in result.stdout


class TestMcpGaps:
    """Test ha-gaps command."""

    def test_mcp_gaps_success(self, runner):
        """Test showing MCP gaps."""
        mock_gaps = [
            {
                "tool": "test_tool",
                "priority": "P1",
                "impact": "High impact",
                "workaround": "Manual workaround",
            }
        ]
        mock_report = {
            "priority_counts": {"P1": 1, "P2": 0, "P3": 0},
        }

        with (
            patch("src.ha.gaps.get_all_gaps", return_value=mock_gaps),
            patch("src.ha.gaps.get_gaps_report", return_value=mock_report),
        ):
            result = runner.invoke(app, ["ha-gaps"])

            assert result.exit_code == 0
            assert "MCP Capability Gap Report" in result.stdout
            assert "Total gaps identified: 1" in result.stdout
