"""Unit tests for Device DAL operations.

Tests DeviceRepository CRUD operations and device inference.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.dal.devices import DeviceRepository


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
def device_repo(mock_session):
    """Create DeviceRepository with mock session."""
    return DeviceRepository(mock_session)


@pytest.fixture
def sample_device():
    """Create a sample device dict."""
    return {
        "ha_device_id": "device_abc123",
        "name": "Living Room Lights",
        "manufacturer": "Philips",
        "model": "Hue Bridge",
        "sw_version": "1.50.0",
        "area_id": None,
    }


class TestDeviceRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, device_repo, mock_session):
        """Test getting device by ID when it exists."""
        mock_device = MagicMock()
        mock_device.id = str(uuid4())
        mock_device.name = "Test Device"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        mock_session.execute.return_value = mock_result

        result = await device_repo.get_by_id(mock_device.id)

        assert result == mock_device
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, device_repo, mock_session):
        """Test getting device by ID when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await device_repo.get_by_id("nonexistent-id")

        assert result is None


class TestDeviceRepositoryGetByHaDeviceId:
    """Tests for get_by_ha_device_id method."""

    @pytest.mark.asyncio
    async def test_get_by_ha_device_id_found(self, device_repo, mock_session):
        """Test getting device by HA device_id when it exists."""
        mock_device = MagicMock()
        mock_device.ha_device_id = "device_abc123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        mock_session.execute.return_value = mock_result

        result = await device_repo.get_by_ha_device_id("device_abc123")

        assert result == mock_device
        assert result.ha_device_id == "device_abc123"

    @pytest.mark.asyncio
    async def test_get_by_ha_device_id_not_found(self, device_repo, mock_session):
        """Test getting device by HA device_id when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await device_repo.get_by_ha_device_id("nonexistent")

        assert result is None


class TestDeviceRepositoryListAll:
    """Tests for list_all method."""

    @pytest.mark.asyncio
    async def test_list_all_no_filters(self, device_repo, mock_session):
        """Test listing all devices without filters."""
        mock_devices = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_devices
        mock_session.execute.return_value = mock_result

        result = await device_repo.list_all()

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_all_with_area_filter(self, device_repo, mock_session):
        """Test listing devices filtered by area."""
        mock_devices = [MagicMock(area_id="area123") for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_devices
        mock_session.execute.return_value = mock_result

        result = await device_repo.list_all(area_id="area123")

        assert len(result) == 3


class TestDeviceRepositoryCount:
    """Tests for count method."""

    @pytest.mark.asyncio
    async def test_count_all(self, device_repo, mock_session):
        """Test counting all devices."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 15
        mock_session.execute.return_value = mock_result

        result = await device_repo.count()

        assert result == 15


class TestDeviceRepositoryUpsert:
    """Tests for upsert method."""

    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, device_repo, mock_session, sample_device):
        """Test upsert creates new device when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Bypass the actual create
        async def mock_create(data):
            device = MagicMock(**data)
            device.id = str(uuid4())
            return device

        device_repo.create = mock_create

        result, created = await device_repo.upsert(sample_device)

        assert created is True

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, device_repo, mock_session, sample_device):
        """Test upsert updates device when found."""
        mock_existing = MagicMock()
        mock_existing.ha_device_id = sample_device["ha_device_id"]
        mock_existing.name = "Old Name"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        result, created = await device_repo.upsert(sample_device)

        assert created is False
        assert result == mock_existing

    @pytest.mark.asyncio
    async def test_upsert_requires_ha_device_id(self, device_repo):
        """Test upsert raises error without ha_device_id."""
        with pytest.raises(ValueError, match="ha_device_id required"):
            await device_repo.upsert({"name": "Test Device"})


class TestDeviceRepositoryGetIdMapping:
    """Tests for get_id_mapping method."""

    @pytest.mark.asyncio
    async def test_get_id_mapping(self, device_repo, mock_session):
        """Test getting mapping of HA device_id to internal ID."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("device_abc123", "uuid-1"),
            ("device_def456", "uuid-2"),
        ]
        mock_session.execute.return_value = mock_result

        result = await device_repo.get_id_mapping()

        assert result == {
            "device_abc123": "uuid-1",
            "device_def456": "uuid-2",
        }
