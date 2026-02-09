"""Unit tests for HA Zone DAL operations.

Tests HAZoneRepository CRUD operations with mocked database.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dal.ha_zones import HAZoneRepository


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
def zone_repo(mock_session):
    """Create HAZoneRepository with mock session."""
    return HAZoneRepository(mock_session)


@pytest.fixture
def sample_zone_data():
    """Create sample zone data."""
    return {
        "name": "Beach House",
        "ha_url": "http://localhost:8123",
        "ha_token": "test_token",
        "secret": "test_secret",
    }


class TestHAZoneRepositoryListAll:
    """Tests for HAZoneRepository.list_all method."""

    @pytest.mark.asyncio
    async def test_list_all(self, zone_repo, mock_session):
        """Test listing all zones."""
        mock_zones = [MagicMock() for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_zones
        mock_session.execute.return_value = mock_result

        result = await zone_repo.list_all()

        assert len(result) == 3


class TestHAZoneRepositoryGetById:
    """Tests for HAZoneRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, zone_repo, mock_session):
        """Test getting zone by ID when it exists."""
        zone_id = str(uuid4())
        mock_zone = MagicMock()
        mock_zone.id = zone_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_zone
        mock_session.execute.return_value = mock_result

        result = await zone_repo.get_by_id(zone_id)

        assert result == mock_zone

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, zone_repo, mock_session):
        """Test getting zone by ID when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await zone_repo.get_by_id(str(uuid4()))

        assert result is None


class TestHAZoneRepositoryGetBySlug:
    """Tests for HAZoneRepository.get_by_slug method."""

    @pytest.mark.asyncio
    async def test_get_by_slug_found(self, zone_repo, mock_session):
        """Test getting zone by slug when it exists."""
        mock_zone = MagicMock()
        mock_zone.slug = "beach-house"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_zone
        mock_session.execute.return_value = mock_result

        result = await zone_repo.get_by_slug("beach-house")

        assert result == mock_zone

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(self, zone_repo, mock_session):
        """Test getting zone by slug when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await zone_repo.get_by_slug("nonexistent")

        assert result is None


class TestHAZoneRepositoryGetDefault:
    """Tests for HAZoneRepository.get_default method."""

    @pytest.mark.asyncio
    async def test_get_default_found(self, zone_repo, mock_session):
        """Test getting default zone."""
        mock_zone = MagicMock()
        mock_zone.is_default = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_zone
        mock_session.execute.return_value = mock_result

        result = await zone_repo.get_default()

        assert result == mock_zone

    @pytest.mark.asyncio
    async def test_get_default_not_found(self, zone_repo, mock_session):
        """Test getting default zone when none exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await zone_repo.get_default()

        assert result is None


class TestHAZoneRepositoryCount:
    """Tests for HAZoneRepository.count method."""

    @pytest.mark.asyncio
    async def test_count(self, zone_repo, mock_session):
        """Test counting zones."""
        mock_zones = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_zones
        mock_session.execute.return_value = mock_result

        result = await zone_repo.count()

        assert result == 5


class TestHAZoneRepositoryCreate:
    """Tests for HAZoneRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_success(self, zone_repo, mock_session, sample_zone_data):
        """Test creating a new zone."""
        # Mock no existing zone with same slug
        mock_result_no_slug = MagicMock()
        mock_result_no_slug.scalar_one_or_none.return_value = None

        # Mock count (first zone)
        mock_result_count = MagicMock()
        mock_result_count.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_result_no_slug,  # get_by_slug
            mock_result_count,  # count
        ]

        with patch("src.dal.ha_zones.encrypt_token", return_value="encrypted_token"):
            result = await zone_repo.create(**sample_zone_data)

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_existing_slug_appends_counter(
        self, zone_repo, mock_session, sample_zone_data
    ):
        """Test creating zone with existing slug appends counter."""
        # Mock existing zone with slug
        mock_existing = MagicMock()
        mock_existing.slug = "beach-house"

        # Mock get_by_slug calls: first returns existing, second returns None
        mock_result_existing = MagicMock()
        mock_result_existing.scalar_one_or_none.return_value = mock_existing

        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        # Mock count
        mock_result_count = MagicMock()
        mock_result_count.scalars.return_value.all.return_value = [MagicMock()]

        mock_session.execute.side_effect = [
            mock_result_existing,  # get_by_slug("beach-house") - exists
            mock_result_none,  # get_by_slug("beach-house-2") - doesn't exist
            mock_result_count,  # count
        ]

        with patch("src.dal.ha_zones.encrypt_token", return_value="encrypted_token"):
            result = await zone_repo.create(**sample_zone_data)

        assert result is not None
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sets_default_when_first_zone(
        self, zone_repo, mock_session, sample_zone_data
    ):
        """Test creating first zone sets it as default."""
        # Mock no existing zone
        mock_result_no_slug = MagicMock()
        mock_result_no_slug.scalar_one_or_none.return_value = None

        # Mock count (empty)
        mock_result_count = MagicMock()
        mock_result_count.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_result_no_slug,  # get_by_slug
            mock_result_count,  # count
        ]

        with patch("src.dal.ha_zones.encrypt_token", return_value="encrypted_token"):
            result = await zone_repo.create(**sample_zone_data, is_default=False)

        assert result is not None
        # Should be set to default even though we passed False
        mock_session.add.assert_called_once()


class TestHAZoneRepositoryUpdate:
    """Tests for HAZoneRepository.update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, zone_repo, mock_session):
        """Test updating zone."""
        zone_id = str(uuid4())
        mock_zone = MagicMock()
        mock_zone.id = zone_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_zone
        mock_session.execute.return_value = mock_result

        with patch("src.dal.ha_zones.encrypt_token", return_value="new_encrypted_token"):
            result = await zone_repo.update(
                zone_id,
                secret="test_secret",
                name="New Name",
                ha_url="http://new.url",
            )

        assert result == mock_zone
        assert mock_zone.name == "New Name"
        assert mock_zone.ha_url == "http://new.url"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, zone_repo, mock_session):
        """Test updating non-existent zone."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await zone_repo.update(
            str(uuid4()),
            secret="test_secret",
            name="New Name",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_token_encrypts(self, zone_repo, mock_session):
        """Test updating token encrypts it."""
        zone_id = str(uuid4())
        mock_zone = MagicMock()
        mock_zone.id = zone_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_zone
        mock_session.execute.return_value = mock_result

        with patch("src.dal.ha_zones.encrypt_token", return_value="encrypted") as mock_encrypt:
            await zone_repo.update(
                zone_id,
                secret="test_secret",
                ha_token="new_token",
            )

        mock_encrypt.assert_called_once_with("new_token", "test_secret")
        assert mock_zone.ha_token_encrypted == "encrypted"


class TestHAZoneRepositoryDelete:
    """Tests for HAZoneRepository.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, zone_repo, mock_session):
        """Test deleting zone."""
        zone_id = str(uuid4())
        mock_zone = MagicMock()
        mock_zone.id = zone_id
        mock_zone.is_default = False

        # Mock get_by_id
        mock_result_get = MagicMock()
        mock_result_get.scalar_one_or_none.return_value = mock_zone

        # Mock count
        mock_result_count = MagicMock()
        mock_result_count.scalars.return_value.all.return_value = [
            MagicMock(),
            MagicMock(),
        ]  # 2 zones

        mock_session.execute.side_effect = [
            mock_result_get,  # get_by_id
            mock_result_count,  # count
        ]

        result = await zone_repo.delete(zone_id)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_zone)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, zone_repo, mock_session):
        """Test deleting non-existent zone."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await zone_repo.delete(str(uuid4()))

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_default_zone_fails(self, zone_repo, mock_session):
        """Test deleting default zone fails."""
        zone_id = str(uuid4())
        mock_zone = MagicMock()
        mock_zone.id = zone_id
        mock_zone.is_default = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_zone
        mock_session.execute.return_value = mock_result

        result = await zone_repo.delete(zone_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_last_zone_fails(self, zone_repo, mock_session):
        """Test deleting last remaining zone fails."""
        zone_id = str(uuid4())
        mock_zone = MagicMock()
        mock_zone.id = zone_id
        mock_zone.is_default = False

        # Mock get_by_id
        mock_result_get = MagicMock()
        mock_result_get.scalar_one_or_none.return_value = mock_zone

        # Mock count (only 1 zone)
        mock_result_count = MagicMock()
        mock_result_count.scalars.return_value.all.return_value = [mock_zone]

        mock_session.execute.side_effect = [
            mock_result_get,  # get_by_id
            mock_result_count,  # count
        ]

        result = await zone_repo.delete(zone_id)

        assert result is False


class TestHAZoneRepositorySetDefault:
    """Tests for HAZoneRepository.set_default method."""

    @pytest.mark.asyncio
    async def test_set_default_success(self, zone_repo, mock_session):
        """Test setting zone as default."""
        zone_id = str(uuid4())
        mock_zone = MagicMock()
        mock_zone.id = zone_id
        mock_zone.is_default = False

        # Mock get_by_id
        mock_result_get = MagicMock()
        mock_result_get.scalar_one_or_none.return_value = mock_zone

        # Mock _clear_defaults (update statement)
        mock_result_update = MagicMock()

        mock_session.execute.side_effect = [
            mock_result_get,  # get_by_id
            mock_result_update,  # _clear_defaults
        ]

        result = await zone_repo.set_default(zone_id)

        assert result == mock_zone
        assert mock_zone.is_default is True
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_default_not_found(self, zone_repo, mock_session):
        """Test setting default when zone doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await zone_repo.set_default(str(uuid4()))

        assert result is None


class TestHAZoneRepositoryGetConnection:
    """Tests for HAZoneRepository.get_connection method."""

    @pytest.mark.asyncio
    async def test_get_connection_success(self, zone_repo, mock_session):
        """Test getting decrypted connection details."""
        zone_id = str(uuid4())
        mock_zone = MagicMock()
        mock_zone.id = zone_id
        mock_zone.ha_url = "http://localhost:8123"
        mock_zone.ha_url_remote = "http://remote:8123"
        mock_zone.ha_token_encrypted = "encrypted_token"
        mock_zone.url_preference = "auto"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_zone
        mock_session.execute.return_value = mock_result

        with patch("src.dal.ha_zones.decrypt_token", return_value="decrypted_token"):
            result = await zone_repo.get_connection(zone_id, secret="test_secret")

        assert result is not None
        assert result[0] == "http://localhost:8123"
        assert result[1] == "http://remote:8123"
        assert result[2] == "decrypted_token"
        assert result[3] == "auto"

    @pytest.mark.asyncio
    async def test_get_connection_not_found(self, zone_repo, mock_session):
        """Test getting connection when zone doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await zone_repo.get_connection(str(uuid4()), secret="test_secret")

        assert result is None
