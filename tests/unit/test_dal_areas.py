"""Unit tests for Area DAL operations.

Tests AreaRepository CRUD operations and area extraction.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.dal.areas import AreaRepository


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def area_repo(mock_session):
    """Create AreaRepository with mock session."""
    return AreaRepository(mock_session)


@pytest.fixture
def sample_area():
    """Create a sample area dict."""
    return {
        "ha_area_id": "living_room",
        "name": "Living Room",
        "floor_id": None,
        "icon": "mdi:sofa",
    }


class TestAreaRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, area_repo, mock_session):
        """Test getting area by ID when it exists."""
        mock_area = MagicMock()
        mock_area.id = str(uuid4())
        mock_area.name = "Test Area"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_area
        mock_session.execute.return_value = mock_result

        result = await area_repo.get_by_id(mock_area.id)

        assert result == mock_area
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, area_repo, mock_session):
        """Test getting area by ID when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await area_repo.get_by_id("nonexistent-id")

        assert result is None


class TestAreaRepositoryGetByHaAreaId:
    """Tests for get_by_ha_area_id method."""

    @pytest.mark.asyncio
    async def test_get_by_ha_area_id_found(self, area_repo, mock_session):
        """Test getting area by HA area_id when it exists."""
        mock_area = MagicMock()
        mock_area.ha_area_id = "living_room"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_area
        mock_session.execute.return_value = mock_result

        result = await area_repo.get_by_ha_area_id("living_room")

        assert result == mock_area
        assert result.ha_area_id == "living_room"

    @pytest.mark.asyncio
    async def test_get_by_ha_area_id_not_found(self, area_repo, mock_session):
        """Test getting area by HA area_id when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await area_repo.get_by_ha_area_id("nonexistent")

        assert result is None


class TestAreaRepositoryListAll:
    """Tests for list_all method."""

    @pytest.mark.asyncio
    async def test_list_all_no_filters(self, area_repo, mock_session):
        """Test listing all areas without filters."""
        mock_areas = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_areas
        mock_session.execute.return_value = mock_result

        result = await area_repo.list_all()

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_all_with_floor_filter(self, area_repo, mock_session):
        """Test listing areas filtered by floor."""
        mock_areas = [MagicMock(floor_id="floor1") for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_areas
        mock_session.execute.return_value = mock_result

        result = await area_repo.list_all(floor_id="floor1")

        assert len(result) == 3


class TestAreaRepositoryCount:
    """Tests for count method."""

    @pytest.mark.asyncio
    async def test_count_all(self, area_repo, mock_session):
        """Test counting all areas."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 8
        mock_session.execute.return_value = mock_result

        result = await area_repo.count()

        assert result == 8


class TestAreaRepositoryUpsert:
    """Tests for upsert method."""

    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, area_repo, mock_session, sample_area):
        """Test upsert creates new area when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Bypass the actual create
        async def mock_create(data):
            area = MagicMock(**data)
            area.id = str(uuid4())
            return area

        area_repo.create = mock_create

        result, created = await area_repo.upsert(sample_area)

        assert created is True

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, area_repo, mock_session, sample_area):
        """Test upsert updates area when found."""
        mock_existing = MagicMock()
        mock_existing.ha_area_id = sample_area["ha_area_id"]
        mock_existing.name = "Old Name"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        result, created = await area_repo.upsert(sample_area)

        assert created is False
        assert result == mock_existing

    @pytest.mark.asyncio
    async def test_upsert_requires_ha_area_id(self, area_repo):
        """Test upsert raises error without ha_area_id."""
        with pytest.raises(ValueError, match="ha_area_id required"):
            await area_repo.upsert({"name": "Test Area"})


class TestAreaRepositoryGetIdMapping:
    """Tests for get_id_mapping method."""

    @pytest.mark.asyncio
    async def test_get_id_mapping(self, area_repo, mock_session):
        """Test getting mapping of HA area_id to internal ID."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("living_room", "uuid-1"),
            ("bedroom", "uuid-2"),
        ]
        mock_session.execute.return_value = mock_result

        result = await area_repo.get_id_mapping()

        assert result == {
            "living_room": "uuid-1",
            "bedroom": "uuid-2",
        }


class TestAreaRepositoryGetAllHaAreaIds:
    """Tests for get_all_ha_area_ids method."""

    @pytest.mark.asyncio
    async def test_get_all_ha_area_ids(self, area_repo, mock_session):
        """Test getting all HA area IDs."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("living_room",),
            ("bedroom",),
            ("kitchen",),
        ]
        mock_session.execute.return_value = mock_result

        result = await area_repo.get_all_ha_area_ids()

        assert result == {"living_room", "bedroom", "kitchen"}
