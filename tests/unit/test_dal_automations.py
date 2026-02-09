"""Unit tests for AutomationRepository, ScriptRepository, and SceneRepository.

Tests DAL repository methods with mocked database sessions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.sql import Select

from src.dal.automations import (
    AutomationRepository,
    SceneRepository,
    ScriptRepository,
)
from src.storage.entities.ha_automation import HAAutomation, Scene, Script


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_automation():
    """Create a mock HAAutomation object."""
    automation = MagicMock(spec=HAAutomation)
    automation.id = "uuid-auto-1"
    automation.ha_automation_id = "auto_123"
    automation.entity_id = "automation.test_automation"
    automation.alias = "Test Automation"
    automation.state = "on"
    return automation


@pytest.fixture
def mock_script():
    """Create a mock Script object."""
    script = MagicMock(spec=Script)
    script.id = "uuid-script-1"
    script.entity_id = "script.test_script"
    script.alias = "Test Script"
    script.state = "off"
    return script


@pytest.fixture
def mock_scene():
    """Create a mock Scene object."""
    scene = MagicMock(spec=Scene)
    scene.id = "uuid-scene-1"
    scene.entity_id = "scene.test_scene"
    scene.name = "Test Scene"
    return scene


@pytest.mark.asyncio
class TestAutomationRepository:
    """Tests for AutomationRepository."""

    async def test_get_by_ha_automation_id(self, mock_session, mock_automation):
        """Test getting automation by HA automation ID."""
        repo = AutomationRepository(mock_session)

        with patch.object(repo, "get_by_ha_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_automation

            result = await repo.get_by_ha_automation_id("auto_123")

            assert result == mock_automation
            mock_get.assert_called_once_with("auto_123")

    async def test_get_by_entity_id(self, mock_session, mock_automation):
        """Test getting automation by entity ID."""
        repo = AutomationRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_automation)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_entity_id("automation.test_automation")

        assert result == mock_automation
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, Select)

    async def test_list_all_with_filters(self, mock_session):
        """Test listing automations with filters."""
        repo = AutomationRepository(mock_session)

        with patch.object(repo, "list_all", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            await repo.list_all(state="on", limit=10, offset=0)

            mock_list.assert_called_once_with(state="on", limit=10, offset=0)

    async def test_count_with_state_filter(self, mock_session):
        """Test counting automations with state filter."""
        repo = AutomationRepository(mock_session)

        with patch.object(repo, "count", new_callable=AsyncMock) as mock_count:
            mock_count.return_value = 5

            result = await repo.count(state="on")

            assert result == 5
            mock_count.assert_called_once_with(state="on")

    async def test_delete_success(self, mock_session, mock_automation):
        """Test deleting an automation."""
        repo = AutomationRepository(mock_session)

        with patch.object(
            repo, "get_by_ha_automation_id", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_automation

            result = await repo.delete("auto_123")

            assert result is True
            mock_session.delete.assert_called_once_with(mock_automation)
            mock_session.flush.assert_called_once()

    async def test_delete_not_found(self, mock_session):
        """Test deleting non-existent automation."""
        repo = AutomationRepository(mock_session)

        with patch.object(
            repo, "get_by_ha_automation_id", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await repo.delete("nonexistent")

            assert result is False
            mock_session.delete.assert_not_called()

    async def test_get_all_ha_automation_ids(self, mock_session):
        """Test getting all HA automation IDs."""
        repo = AutomationRepository(mock_session)

        with patch.object(repo, "get_all_ha_ids", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"auto_1", "auto_2"}

            result = await repo.get_all_ha_automation_ids()

            assert result == {"auto_1", "auto_2"}
            mock_get.assert_called_once()


@pytest.mark.asyncio
class TestScriptRepository:
    """Tests for ScriptRepository."""

    async def test_get_by_entity_id(self, mock_session, mock_script):
        """Test getting script by entity ID."""
        repo = ScriptRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_script)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_entity_id("script.test_script")

        assert result == mock_script
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, Select)

    async def test_list_all_with_filters(self, mock_session):
        """Test listing scripts with filters."""
        repo = ScriptRepository(mock_session)

        with patch.object(repo, "list_all", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            await repo.list_all(state="on", limit=10, offset=0)

            mock_list.assert_called_once_with(state="on", limit=10, offset=0)

    async def test_delete_success(self, mock_session, mock_script):
        """Test deleting a script."""
        repo = ScriptRepository(mock_session)

        with patch.object(repo, "get_by_entity_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_script

            result = await repo.delete("script.test_script")

            assert result is True
            mock_session.delete.assert_called_once_with(mock_script)
            mock_session.flush.assert_called_once()

    async def test_delete_not_found(self, mock_session):
        """Test deleting non-existent script."""
        repo = ScriptRepository(mock_session)

        with patch.object(repo, "get_by_entity_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await repo.delete("nonexistent")

            assert result is False
            mock_session.delete.assert_not_called()

    async def test_get_all_entity_ids(self, mock_session):
        """Test getting all script entity IDs."""
        repo = ScriptRepository(mock_session)

        with patch.object(repo, "get_all_ha_ids", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"script.1", "script.2"}

            result = await repo.get_all_entity_ids()

            assert result == {"script.1", "script.2"}
            mock_get.assert_called_once()


@pytest.mark.asyncio
class TestSceneRepository:
    """Tests for SceneRepository."""

    async def test_get_by_entity_id(self, mock_session, mock_scene):
        """Test getting scene by entity ID."""
        repo = SceneRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_scene)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_entity_id("scene.test_scene")

        assert result == mock_scene
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, Select)

    async def test_delete_success(self, mock_session, mock_scene):
        """Test deleting a scene."""
        repo = SceneRepository(mock_session)

        with patch.object(repo, "get_by_entity_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_scene

            result = await repo.delete("scene.test_scene")

            assert result is True
            mock_session.delete.assert_called_once_with(mock_scene)
            mock_session.flush.assert_called_once()

    async def test_delete_not_found(self, mock_session):
        """Test deleting non-existent scene."""
        repo = SceneRepository(mock_session)

        with patch.object(repo, "get_by_entity_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await repo.delete("nonexistent")

            assert result is False
            mock_session.delete.assert_not_called()

    async def test_get_all_entity_ids(self, mock_session):
        """Test getting all scene entity IDs."""
        repo = SceneRepository(mock_session)

        with patch.object(repo, "get_all_ha_ids", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"scene.1", "scene.2"}

            result = await repo.get_all_entity_ids()

            assert result == {"scene.1", "scene.2"}
            mock_get.assert_called_once()
