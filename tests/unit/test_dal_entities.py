"""Unit tests for Entity DAL operations.

Tests EntityRepository CRUD operations with mocked database.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dal.entities import EntityRepository


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def entity_repo(mock_session):
    """Create EntityRepository with mock session."""
    return EntityRepository(mock_session)


@pytest.fixture
def sample_entity():
    """Create a sample entity dict."""
    return {
        "entity_id": "light.living_room",
        "domain": "light",
        "name": "Living Room",
        "state": "off",
        "attributes": {"brightness": 0, "friendly_name": "Living Room"},
        "area_id": None,
        "device_id": None,
    }


class TestEntityRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, entity_repo, mock_session):
        """Test getting entity by ID when it exists."""
        mock_entity = MagicMock()
        mock_entity.id = str(uuid4())
        mock_entity.entity_id = "light.test"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_entity
        mock_session.execute.return_value = mock_result

        result = await entity_repo.get_by_id(mock_entity.id)

        assert result == mock_entity
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, entity_repo, mock_session):
        """Test getting entity by ID when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await entity_repo.get_by_id("nonexistent-id")

        assert result is None


class TestEntityRepositoryGetByEntityId:
    """Tests for get_by_entity_id method."""

    @pytest.mark.asyncio
    async def test_get_by_entity_id_found(self, entity_repo, mock_session):
        """Test getting entity by HA entity_id when it exists."""
        mock_entity = MagicMock()
        mock_entity.entity_id = "light.living_room"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_entity
        mock_session.execute.return_value = mock_result

        result = await entity_repo.get_by_entity_id("light.living_room")

        assert result == mock_entity
        assert result.entity_id == "light.living_room"

    @pytest.mark.asyncio
    async def test_get_by_entity_id_not_found(self, entity_repo, mock_session):
        """Test getting entity by HA entity_id when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await entity_repo.get_by_entity_id("light.nonexistent")

        assert result is None


class TestEntityRepositoryListAll:
    """Tests for list_all method."""

    @pytest.mark.asyncio
    async def test_list_all_no_filters(self, entity_repo, mock_session):
        """Test listing all entities without filters."""
        mock_entities = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_entities
        mock_session.execute.return_value = mock_result

        result = await entity_repo.list_all()

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_all_with_domain_filter(self, entity_repo, mock_session):
        """Test listing entities filtered by domain."""
        mock_lights = [MagicMock(domain="light") for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_lights
        mock_session.execute.return_value = mock_result

        result = await entity_repo.list_all(domain="light")

        assert len(result) == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_all_with_limit(self, entity_repo, mock_session):
        """Test listing entities with limit."""
        mock_entities = [MagicMock() for _ in range(10)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_entities
        mock_session.execute.return_value = mock_result

        result = await entity_repo.list_all(limit=10)

        assert len(result) == 10


class TestEntityRepositoryCount:
    """Tests for count method."""

    @pytest.mark.asyncio
    async def test_count_all(self, entity_repo, mock_session):
        """Test counting all entities."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result

        result = await entity_repo.count()

        assert result == 42

    @pytest.mark.asyncio
    async def test_count_by_domain(self, entity_repo, mock_session):
        """Test counting entities by domain."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await entity_repo.count(domain="light")

        assert result == 10


class TestEntityRepositoryUpsert:
    """Tests for upsert method."""

    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, entity_repo, mock_session, sample_entity):
        """Test upsert creates new entity when not found."""
        # Mock not finding existing
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch.object(entity_repo, "create", new_callable=AsyncMock) as mock_create:
            mock_new_entity = MagicMock()
            mock_create.return_value = mock_new_entity

            result, created = await entity_repo.upsert(sample_entity)

            assert created is True
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, entity_repo, mock_session, sample_entity):
        """Test upsert updates entity when found."""
        mock_existing = MagicMock()
        mock_existing.entity_id = sample_entity["entity_id"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        result, created = await entity_repo.upsert(sample_entity)

        assert created is False
        assert result == mock_existing

    @pytest.mark.asyncio
    async def test_upsert_requires_entity_id(self, entity_repo):
        """Test upsert raises error without entity_id."""
        with pytest.raises(ValueError, match="entity_id required"):
            await entity_repo.upsert({"name": "Test", "domain": "light"})


class TestEntityRepositoryDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_found(self, entity_repo, mock_session):
        """Test deleting existing entity."""
        mock_entity = MagicMock()
        mock_entity.entity_id = "light.test"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_entity
        mock_session.execute.return_value = mock_result

        result = await entity_repo.delete("light.test")

        assert result is True
        mock_session.delete.assert_called_once_with(mock_entity)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, entity_repo, mock_session):
        """Test deleting non-existent entity."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await entity_repo.delete("light.nonexistent")

        assert result is False


class TestEntityRepositorySearch:
    """Tests for search method."""

    @pytest.mark.asyncio
    async def test_search_by_name(self, entity_repo, mock_session):
        """Test searching entities by name."""
        mock_entities = [
            MagicMock(name="Living Room Light"),
            MagicMock(name="Living Room Switch"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_entities
        mock_session.execute.return_value = mock_result

        result = await entity_repo.search("living")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_empty_results(self, entity_repo, mock_session):
        """Test search with no matching results."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await entity_repo.search("nonexistent")

        assert result == []


class TestEntityRepositoryGetDomainCounts:
    """Tests for get_domain_counts method."""

    @pytest.mark.asyncio
    async def test_get_domain_counts(self, entity_repo, mock_session):
        """Test getting entity count per domain."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("light", 10),
            ("switch", 5),
            ("sensor", 20),
        ]
        mock_session.execute.return_value = mock_result

        result = await entity_repo.get_domain_counts()

        assert result == {"light": 10, "switch": 5, "sensor": 20}
