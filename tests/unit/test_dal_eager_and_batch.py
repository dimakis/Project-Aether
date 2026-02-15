"""Unit tests for eager-loading options and batch entity lookup.

Part 1a: list_by_domains and DeviceRepository.list_all include selectinload(area)
Part 1b: EntityRepository.get_by_entity_ids returns entities via single IN query
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.dal.devices import DeviceRepository
from src.dal.entities import EntityRepository

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def entity_repo(mock_session):
    return EntityRepository(mock_session)


@pytest.fixture
def device_repo(mock_session):
    return DeviceRepository(mock_session)


# ── Part 1a: Eager loading ───────────────────────────────────────────────────


class TestListByDomainsEagerLoading:
    """list_by_domains must include selectinload(HAEntity.area)."""

    @pytest.mark.asyncio
    async def test_list_by_domains_includes_selectinload(self, entity_repo, mock_session):
        """The query passed to session.execute should contain selectinload for area."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await entity_repo.list_by_domains(["light"], limit_per_domain=50)

        # Verify the query was compiled with eager-load options
        call_args = mock_session.execute.call_args
        query = call_args[0][0]
        assert query._with_options, "list_by_domains query must include eager-load options"

    @pytest.mark.asyncio
    async def test_list_by_domains_empty_input(self, entity_repo):
        """Empty domain list returns empty dict without querying."""
        result = await entity_repo.list_by_domains([])
        assert result == {}


class TestDeviceListAllEagerLoading:
    """DeviceRepository.list_all must include selectinload(Device.area)."""

    @pytest.mark.asyncio
    async def test_list_all_includes_selectinload(self, device_repo, mock_session):
        """The query passed to session.execute should contain selectinload for area."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await device_repo.list_all(limit=20)

        call_args = mock_session.execute.call_args
        query = call_args[0][0]
        assert query._with_options, "Device.list_all query must include eager-load options"


# ── Part 1b: Batch entity lookup ─────────────────────────────────────────────


class TestGetByEntityIds:
    """EntityRepository.get_by_entity_ids returns entities via IN query."""

    @pytest.mark.asyncio
    async def test_get_by_entity_ids_returns_matching(self, entity_repo, mock_session):
        """Batch lookup returns matching entities."""
        mock_e1 = MagicMock(entity_id="light.a")
        mock_e2 = MagicMock(entity_id="light.b")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_e1, mock_e2]
        mock_session.execute.return_value = mock_result

        result = await entity_repo.get_by_entity_ids(["light.a", "light.b"])

        assert len(result) == 2
        assert result[0].entity_id == "light.a"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_entity_ids_empty_list(self, entity_repo, mock_session):
        """Empty input returns empty list without querying."""
        result = await entity_repo.get_by_entity_ids([])

        assert result == []
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_entity_ids_no_matches(self, entity_repo, mock_session):
        """Returns empty list when no entities match."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await entity_repo.get_by_entity_ids(["light.nonexistent"])

        assert result == []
