"""Unit tests for InsightSchedule DAL operations.

Tests InsightScheduleRepository CRUD operations with mocked database.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.dal.insight_schedules import InsightScheduleRepository
from src.storage.entities.insight_schedule import InsightSchedule


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def schedule_repo(mock_session):
    """Create InsightScheduleRepository with mock session."""
    return InsightScheduleRepository(mock_session)


@pytest.fixture
def sample_schedule_data():
    """Create sample schedule data."""
    return {
        "name": "Daily Energy Report",
        "analysis_type": "energy_consumption",
        "trigger_type": "cron",
        "hours": 24,
        "cron_expression": "0 9 * * *",
    }


class TestInsightScheduleRepositoryCreate:
    """Tests for InsightScheduleRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_success(self, schedule_repo, mock_session, sample_schedule_data):
        """Test creating a new schedule."""
        result = await schedule_repo.create(**sample_schedule_data)

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_webhook(self, schedule_repo, mock_session):
        """Test creating schedule with webhook trigger."""
        result = await schedule_repo.create(
            name="Event Triggered",
            analysis_type="usage_pattern",
            trigger_type="webhook",
            webhook_event="state_changed",
            webhook_filter={"entity_id": "sensor.temperature"},
        )

        assert result is not None
        mock_session.add.assert_called_once()


class TestInsightScheduleRepositoryGet:
    """Tests for InsightScheduleRepository.get method."""

    @pytest.mark.asyncio
    async def test_get_found(self, schedule_repo, mock_session):
        """Test getting schedule by ID when it exists."""
        schedule_id = str(uuid4())
        mock_schedule = MagicMock()
        mock_schedule.id = schedule_id

        mock_session.get.return_value = mock_schedule

        result = await schedule_repo.get(schedule_id)

        assert result == mock_schedule
        mock_session.get.assert_called_once_with(InsightSchedule, schedule_id)

    @pytest.mark.asyncio
    async def test_get_not_found(self, schedule_repo, mock_session):
        """Test getting schedule by ID when it doesn't exist."""
        mock_session.get.return_value = None

        result = await schedule_repo.get(str(uuid4()))

        assert result is None


class TestInsightScheduleRepositoryListAll:
    """Tests for InsightScheduleRepository.list_all method."""

    @pytest.mark.asyncio
    async def test_list_all(self, schedule_repo, mock_session):
        """Test listing all schedules."""
        mock_schedules = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_schedules
        mock_session.execute.return_value = mock_result

        result = await schedule_repo.list_all()

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_all_enabled_only(self, schedule_repo, mock_session):
        """Test listing only enabled schedules."""
        mock_schedules = [MagicMock(enabled=True) for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_schedules
        mock_session.execute.return_value = mock_result

        result = await schedule_repo.list_all(enabled_only=True)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_all_with_trigger_type(self, schedule_repo, mock_session):
        """Test listing schedules filtered by trigger type."""
        mock_schedules = [MagicMock(trigger_type="cron") for _ in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_schedules
        mock_session.execute.return_value = mock_result

        result = await schedule_repo.list_all(trigger_type="cron")

        assert len(result) == 2


class TestInsightScheduleRepositoryListWebhookTriggers:
    """Tests for InsightScheduleRepository.list_webhook_triggers method."""

    @pytest.mark.asyncio
    async def test_list_webhook_triggers(self, schedule_repo, mock_session):
        """Test listing webhook triggers."""
        mock_schedules = [MagicMock(trigger_type="webhook") for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_schedules
        mock_session.execute.return_value = mock_result

        result = await schedule_repo.list_webhook_triggers()

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_webhook_triggers_with_event(self, schedule_repo, mock_session):
        """Test listing webhook triggers filtered by event."""
        mock_schedules = [MagicMock(webhook_event="state_changed") for _ in range(2)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_schedules
        mock_session.execute.return_value = mock_result

        result = await schedule_repo.list_webhook_triggers(webhook_event="state_changed")

        assert len(result) == 2


class TestInsightScheduleRepositoryListCronSchedules:
    """Tests for InsightScheduleRepository.list_cron_schedules method."""

    @pytest.mark.asyncio
    async def test_list_cron_schedules(self, schedule_repo, mock_session):
        """Test listing cron schedules."""
        mock_schedules = [MagicMock(trigger_type="cron") for _ in range(4)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_schedules
        mock_session.execute.return_value = mock_result

        result = await schedule_repo.list_cron_schedules()

        assert len(result) == 4


class TestInsightScheduleRepositoryUpdate:
    """Tests for InsightScheduleRepository.update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, schedule_repo, mock_session):
        """Test updating schedule."""
        schedule_id = str(uuid4())
        mock_schedule = MagicMock()
        mock_schedule.id = schedule_id
        mock_schedule.name = "Old Name"

        mock_session.get.return_value = mock_schedule

        result = await schedule_repo.update(schedule_id, name="New Name", enabled=False)

        assert result == mock_schedule
        assert mock_schedule.name == "New Name"
        assert mock_schedule.enabled is False
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, schedule_repo, mock_session):
        """Test updating schedule when it doesn't exist."""
        mock_session.get.return_value = None

        result = await schedule_repo.update(str(uuid4()), name="New Name")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, schedule_repo, mock_session):
        """Test updating multiple fields at once."""
        schedule_id = str(uuid4())
        mock_schedule = MagicMock()
        mock_schedule.id = schedule_id

        mock_session.get.return_value = mock_schedule

        result = await schedule_repo.update(
            schedule_id,
            name="Updated",
            hours=48,
            cron_expression="0 10 * * *",
        )

        assert result == mock_schedule
        assert mock_schedule.name == "Updated"
        assert mock_schedule.hours == 48
        assert mock_schedule.cron_expression == "0 10 * * *"


class TestInsightScheduleRepositoryDelete:
    """Tests for InsightScheduleRepository.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, schedule_repo, mock_session):
        """Test deleting schedule."""
        schedule_id = str(uuid4())
        mock_schedule = MagicMock()
        mock_schedule.id = schedule_id

        mock_session.get.return_value = mock_schedule

        result = await schedule_repo.delete(schedule_id)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_schedule)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, schedule_repo, mock_session):
        """Test deleting schedule when it doesn't exist."""
        mock_session.get.return_value = None

        result = await schedule_repo.delete(str(uuid4()))

        assert result is False


class TestInsightScheduleRepositoryRecordRun:
    """Tests for InsightScheduleRepository.record_run method."""

    @pytest.mark.asyncio
    async def test_record_run_success(self, schedule_repo, mock_session):
        """Test recording successful run."""
        schedule_id = str(uuid4())
        mock_schedule = MagicMock()
        mock_schedule.id = schedule_id
        mock_schedule.record_run = MagicMock()

        mock_session.get.return_value = mock_schedule

        result = await schedule_repo.record_run(schedule_id, success=True)

        assert result == mock_schedule
        mock_schedule.record_run.assert_called_once_with(success=True, error=None)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_run_with_error(self, schedule_repo, mock_session):
        """Test recording failed run with error."""
        schedule_id = str(uuid4())
        mock_schedule = MagicMock()
        mock_schedule.id = schedule_id
        mock_schedule.record_run = MagicMock()

        mock_session.get.return_value = mock_schedule

        result = await schedule_repo.record_run(schedule_id, success=False, error="Test error")

        assert result == mock_schedule
        mock_schedule.record_run.assert_called_once_with(success=False, error="Test error")

    @pytest.mark.asyncio
    async def test_record_run_not_found(self, schedule_repo, mock_session):
        """Test recording run when schedule doesn't exist."""
        mock_session.get.return_value = None

        result = await schedule_repo.record_run(str(uuid4()), success=True)

        assert result is None
