"""Unit tests for ToolGroupRepository.

Tests DAL repository methods with mocked database sessions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql import Select

from src.dal.tool_groups import ToolGroupRepository
from src.storage.entities.tool_group import ToolGroup


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_tool_group():
    """Create a mock ToolGroup."""
    group = MagicMock(spec=ToolGroup)
    group.id = "group-uuid-1"
    group.name = "ha_entity_query"
    group.display_name = "HA Entity Queries"
    group.tool_names = ["get_entities", "get_states"]
    group.is_read_only = True
    return group


@pytest.mark.asyncio
class TestToolGroupRepository:
    """Tests for ToolGroupRepository."""

    async def test_get_by_name_found(self, mock_session, mock_tool_group):
        """get_by_name returns group when found."""
        repo = ToolGroupRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_tool_group)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_name("ha_entity_query")
        assert result == mock_tool_group
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Select)

    async def test_get_by_name_not_found(self, mock_session):
        """get_by_name returns None when not found."""
        repo = ToolGroupRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_name("nonexistent")
        assert result is None

    async def test_get_by_names_empty(self, mock_session):
        """get_by_names returns empty list when names is empty."""
        repo = ToolGroupRepository(mock_session)
        result = await repo.get_by_names([])
        assert result == []
        mock_session.execute.assert_not_called()

    async def test_get_by_names(self, mock_session, mock_tool_group):
        """get_by_names returns list of groups."""
        repo = ToolGroupRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_tool_group]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_names(["ha_entity_query"])
        assert result == [mock_tool_group]
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Select)

    async def test_list_all(self, mock_session, mock_tool_group):
        """list_all returns all groups ordered by name."""
        repo = ToolGroupRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_tool_group]
        mock_session.execute.return_value = mock_result

        result = await repo.list_all()
        assert result == [mock_tool_group]
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Select)

    async def test_create(self, mock_session):
        """create adds group and flushes."""
        repo = ToolGroupRepository(mock_session)
        data = {
            "name": "new_group",
            "display_name": "New Group",
            "tool_names": ["tool_a"],
            "is_read_only": False,
        }
        result = await repo.create(data)
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    async def test_update_found(self, mock_session, mock_tool_group):
        """update modifies group when found and flushes."""
        repo = ToolGroupRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_tool_group)
        mock_session.execute.return_value = mock_result

        result = await repo.update("ha_entity_query", {"display_name": "Updated"})
        assert result == mock_tool_group
        mock_session.flush.assert_called_once()

    async def test_update_not_found(self, mock_session):
        """update returns None when group not found."""
        repo = ToolGroupRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repo.update("nonexistent", {"display_name": "Updated"})
        assert result is None
        mock_session.flush.assert_not_called()
