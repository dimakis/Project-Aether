"""Unit tests for BaseRepository batch operations.

Tests upsert_many and delete_by_ha_ids for the sync N+1 optimization.
Uses the real Area model + AreaRepository with a mocked session.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.dal.areas import AreaRepository
from src.storage.entities.area import Area


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    return AreaRepository(mock_session)


def _make_area(**kwargs) -> MagicMock:
    """Create a fake Area-like object for testing without SA session binding."""
    defaults = {"id": str(uuid4()), "ha_area_id": "", "name": "", "floor_id": None, "icon": None}
    area = MagicMock(spec=Area)
    for k, v in {**defaults, **kwargs}.items():
        setattr(area, k, v)
    return area


class TestUpsertMany:
    """Tests for BaseRepository.upsert_many batch upsert."""

    @pytest.mark.asyncio
    async def test_upsert_many_creates_new_rows(self, repo, mock_session):
        """When no existing rows, all items are created via add_all."""
        # No existing rows
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        data_list = [
            {"ha_area_id": "kitchen", "name": "Kitchen"},
            {"ha_area_id": "bedroom", "name": "Bedroom"},
        ]

        _results, stats = await repo.upsert_many(data_list)

        assert stats["created"] == 2
        assert stats["updated"] == 0
        # add_all called with 2 new model instances
        mock_session.add_all.assert_called_once()
        added = mock_session.add_all.call_args[0][0]
        assert len(added) == 2
        # flush called once (not per-row)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_many_updates_existing_rows(self, repo, mock_session):
        """When all rows exist, they are updated in-place."""
        existing = _make_area(ha_area_id="kitchen", name="Old Kitchen")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing]
        mock_session.execute.return_value = mock_result

        data_list = [{"ha_area_id": "kitchen", "name": "New Kitchen"}]

        _results, stats = await repo.upsert_many(data_list)

        assert stats["created"] == 0
        assert stats["updated"] == 1
        assert existing.name == "New Kitchen"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_many_mixed(self, repo, mock_session):
        """Mix of creates and updates in single batch."""
        existing = _make_area(ha_area_id="kitchen", name="Kitchen")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing]
        mock_session.execute.return_value = mock_result

        data_list = [
            {"ha_area_id": "kitchen", "name": "Updated Kitchen"},
            {"ha_area_id": "bedroom", "name": "Bedroom"},
        ]

        _results, stats = await repo.upsert_many(data_list)

        assert stats["created"] == 1
        assert stats["updated"] == 1

    @pytest.mark.asyncio
    async def test_upsert_many_empty_list(self, repo, mock_session):
        """Empty list returns empty results without DB calls."""
        results, stats = await repo.upsert_many([])

        assert results == []
        assert stats == {"created": 0, "updated": 0}
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_many_single_select_query(self, repo, mock_session):
        """Verify only 1 SELECT query (not N) for N items."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        data_list = [{"ha_area_id": f"area_{i}", "name": f"Area {i}"} for i in range(10)]

        await repo.upsert_many(data_list)

        # Only 1 execute call (the SELECT for existing rows)
        assert mock_session.execute.call_count == 1


class TestDeleteByHaIds:
    """Tests for BaseRepository.delete_by_ha_ids batch delete."""

    @pytest.mark.asyncio
    async def test_delete_by_ha_ids_removes_matching(self, repo, mock_session):
        """Batch delete removes all matching HA IDs in one query."""
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        count = await repo.delete_by_ha_ids({"kitchen", "bedroom", "garage"})

        assert count == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_ha_ids_empty_set(self, repo, mock_session):
        """Empty set returns 0 without DB call."""
        count = await repo.delete_by_ha_ids(set())

        assert count == 0
        mock_session.execute.assert_not_called()
