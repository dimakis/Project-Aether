"""Unit tests for Service DAL operations.

Tests ServiceRepository CRUD operations with mocked database.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dal.services import ServiceRepository


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def service_repo(mock_session):
    """Create ServiceRepository with mock session."""
    return ServiceRepository(mock_session)


class TestServiceRepositoryGetByFullName:
    """Tests for ServiceRepository.get_by_full_name method."""

    @pytest.mark.asyncio
    async def test_get_by_full_name_found(self, service_repo, mock_session):
        """Test getting service by domain and service name when it exists."""
        mock_service = MagicMock()
        mock_service.domain = "light"
        mock_service.service = "turn_on"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_service
        mock_session.execute.return_value = mock_result

        result = await service_repo.get_by_full_name("light", "turn_on")

        assert result == mock_service

    @pytest.mark.asyncio
    async def test_get_by_full_name_not_found(self, service_repo, mock_session):
        """Test getting service by domain and service name when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service_repo.get_by_full_name("light", "nonexistent")

        assert result is None


class TestServiceRepositoryListAll:
    """Tests for ServiceRepository.list_all method."""

    @pytest.mark.asyncio
    async def test_list_all(self, service_repo, mock_session):
        """Test listing all services."""
        mock_services = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.return_value = mock_result

        result = await service_repo.list_all()

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_all_with_domain_filter(self, service_repo, mock_session):
        """Test listing services filtered by domain."""
        mock_services = [MagicMock(domain="light") for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.return_value = mock_result

        result = await service_repo.list_all(domain="light")

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_all_with_is_seeded_filter(self, service_repo, mock_session):
        """Test listing services filtered by seeded status."""
        mock_services = [MagicMock(is_seeded=True) for _ in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.return_value = mock_result

        result = await service_repo.list_all(is_seeded=True)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_all_with_limit_offset(self, service_repo, mock_session):
        """Test listing services with limit and offset."""
        mock_services = [MagicMock() for _ in range(10)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.return_value = mock_result

        result = await service_repo.list_all(limit=10, offset=0)

        assert len(result) == 10


class TestServiceRepositoryListByDomain:
    """Tests for ServiceRepository.list_by_domain method."""

    @pytest.mark.asyncio
    async def test_list_by_domain(self, service_repo, mock_session):
        """Test listing services by domain."""
        mock_services = [MagicMock(domain="light") for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.return_value = mock_result

        result = await service_repo.list_by_domain("light")

        assert len(result) == 3


class TestServiceRepositoryGetDomains:
    """Tests for ServiceRepository.get_domains method."""

    @pytest.mark.asyncio
    async def test_get_domains(self, service_repo, mock_session):
        """Test getting all unique domains."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("light",),
            ("switch",),
            ("sensor",),
        ]
        mock_session.execute.return_value = mock_result

        result = await service_repo.get_domains()

        assert result == ["light", "switch", "sensor"]


class TestServiceRepositoryCount:
    """Tests for ServiceRepository.count method."""

    @pytest.mark.asyncio
    async def test_count_all(self, service_repo, mock_session):
        """Test counting all services."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 50
        mock_session.execute.return_value = mock_result

        result = await service_repo.count()

        assert result == 50

    @pytest.mark.asyncio
    async def test_count_by_domain(self, service_repo, mock_session):
        """Test counting services by domain."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await service_repo.count(domain="light")

        assert result == 10


class TestServiceRepositoryUpsert:
    """Tests for ServiceRepository.upsert method."""

    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, service_repo, mock_session):
        """Test upsert creates new service when not found."""
        service_data = {
            "domain": "light",
            "service": "turn_on",
            "name": "Turn On",
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch.object(service_repo, "create", new_callable=AsyncMock) as mock_create:
            mock_service = MagicMock()
            mock_create.return_value = mock_service

            result, created = await service_repo.upsert(service_data)

            assert created is True
            assert result == mock_service
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, service_repo, mock_session):
        """Test upsert updates existing service."""
        service_data = {
            "domain": "light",
            "service": "turn_on",
            "name": "Updated Name",
        }

        mock_existing = MagicMock()
        mock_existing.domain = "light"
        mock_existing.service = "turn_on"
        mock_existing.name = "Old Name"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        result, created = await service_repo.upsert(service_data)

        assert created is False
        assert result == mock_existing
        assert mock_existing.name == "Updated Name"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_requires_domain_and_service(self, service_repo):
        """Test upsert raises error without domain and service."""
        with pytest.raises(ValueError, match="domain and service required"):
            await service_repo.upsert({"name": "Test"})


class TestServiceRepositorySeedCommonServices:
    """Tests for ServiceRepository.seed_common_services method."""

    @pytest.mark.asyncio
    async def test_seed_common_services(self, service_repo, mock_session):
        """Test seeding common services."""
        # Mock get_all_services to return test data
        test_services = [
            {"domain": "light", "service": "turn_on", "name": "Turn On"},
            {"domain": "light", "service": "turn_off", "name": "Turn Off"},
        ]

        with patch("src.dal.services.get_all_services", return_value=test_services):
            # Mock get_by_full_name to return None (services don't exist)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            # Mock create
            with patch.object(service_repo, "create", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = MagicMock()

                result = await service_repo.seed_common_services()

                assert result["added"] == 2
                assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_seed_common_services_skips_existing(self, service_repo, mock_session):
        """Test seeding skips existing services."""
        test_services = [
            {"domain": "light", "service": "turn_on", "name": "Turn On"},
        ]

        with patch("src.dal.services.get_all_services", return_value=test_services):
            # Mock get_by_full_name to return existing service
            mock_existing = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_existing
            mock_session.execute.return_value = mock_result

            result = await service_repo.seed_common_services()

            assert result["added"] == 0
            assert result["skipped"] == 1


class TestServiceRepositorySearch:
    """Tests for ServiceRepository.search method."""

    @pytest.mark.asyncio
    async def test_search_by_name(self, service_repo, mock_session):
        """Test searching services by name."""
        mock_services = [
            MagicMock(name="Turn On Light"),
            MagicMock(name="Turn Off Light"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.return_value = mock_result

        result = await service_repo.search("light")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_by_domain(self, service_repo, mock_session):
        """Test searching services by domain."""
        mock_services = [MagicMock(domain="light")]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_services
        mock_session.execute.return_value = mock_result

        result = await service_repo.search("light")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_empty_results(self, service_repo, mock_session):
        """Test search with no matching results."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await service_repo.search("nonexistent")

        assert result == []


class TestServiceRepositoryGetServiceInfo:
    """Tests for ServiceRepository.get_service_info method."""

    @pytest.mark.asyncio
    async def test_get_service_info_success(self, service_repo, mock_session):
        """Test getting service by full name."""
        mock_service = MagicMock()
        mock_service.domain = "light"
        mock_service.service = "turn_on"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_service
        mock_session.execute.return_value = mock_result

        result = await service_repo.get_service_info("light.turn_on")

        assert result == mock_service

    @pytest.mark.asyncio
    async def test_get_service_info_invalid_format(self, service_repo):
        """Test getting service info with invalid format returns None."""
        result = await service_repo.get_service_info("invalid")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_service_info_not_found(self, service_repo, mock_session):
        """Test getting service info when service doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service_repo.get_service_info("light.nonexistent")

        assert result is None
