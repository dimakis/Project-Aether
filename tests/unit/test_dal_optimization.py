"""Unit tests for OptimizationJobRepository and AutomationSuggestionRepository.

Tests DAL repository methods with mocked database sessions.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql import Select, Update

from src.dal.optimization import (
    AutomationSuggestionRepository,
    OptimizationJobRepository,
)
from src.storage.entities.automation_suggestion import AutomationSuggestionEntity
from src.storage.entities.optimization_job import OptimizationJob


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_job():
    """Create a mock OptimizationJob."""
    job = MagicMock(spec=OptimizationJob)
    job.id = "job-uuid-1"
    job.status = "pending"
    job.analysis_types = ["energy"]
    job.insight_count = 0
    job.suggestion_count = 0
    return job


@pytest.fixture
def mock_suggestion():
    """Create a mock AutomationSuggestionEntity."""
    suggestion = MagicMock(spec=AutomationSuggestionEntity)
    suggestion.id = "suggestion-uuid-1"
    suggestion.job_id = "job-uuid-1"
    suggestion.pattern = "test pattern"
    suggestion.status = "pending"
    return suggestion


@pytest.mark.asyncio
class TestOptimizationJobRepository:
    """Tests for OptimizationJobRepository."""

    async def test_create(self, mock_session):
        """Create adds job and flushes."""
        repo = OptimizationJobRepository(mock_session)
        data = {
            "status": "pending",
            "analysis_types": ["energy"],
            "insight_count": 0,
            "suggestion_count": 0,
        }
        result = await repo.create(data)
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    async def test_get_by_id_found(self, mock_session, mock_job):
        """get_by_id returns job when found."""
        repo = OptimizationJobRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_job)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id("job-uuid-1")
        assert result == mock_job
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Select)

    async def test_get_by_id_not_found(self, mock_session):
        """get_by_id returns None when not found."""
        repo = OptimizationJobRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id("nonexistent")
        assert result is None

    async def test_list_all(self, mock_session, mock_job):
        """list_all returns list of jobs."""
        repo = OptimizationJobRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_job]
        mock_session.execute.return_value = mock_result

        result = await repo.list_all()
        assert result == [mock_job]
        mock_session.execute.assert_called_once()

    async def test_list_all_with_status(self, mock_session):
        """list_all with status filter passes status to query."""
        repo = OptimizationJobRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.list_all(status="completed", limit=10)
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Select)

    async def test_update_status(self, mock_session):
        """update_status executes update with status and kwargs."""
        repo = OptimizationJobRepository(mock_session)
        mock_session.execute.return_value = None

        await repo.update_status("job-1", "completed", completed_at=datetime.now(UTC))
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Update)

    async def test_reconcile_stale_jobs(self, mock_session):
        """reconcile_stale_jobs updates running jobs to failed and returns count."""
        repo = OptimizationJobRepository(mock_session)
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result

        count = await repo.reconcile_stale_jobs()
        assert count == 2
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Update)


@pytest.mark.asyncio
class TestAutomationSuggestionRepository:
    """Tests for AutomationSuggestionRepository."""

    async def test_create(self, mock_session):
        """Create adds suggestion and flushes."""
        repo = AutomationSuggestionRepository(mock_session)
        data = {
            "job_id": "job-1",
            "pattern": "pattern",
            "status": "pending",
        }
        result = await repo.create(data)
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    async def test_get_by_id_found(self, mock_session, mock_suggestion):
        """get_by_id returns suggestion when found."""
        repo = AutomationSuggestionRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_suggestion)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id("suggestion-uuid-1")
        assert result == mock_suggestion
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Select)

    async def test_get_by_id_not_found(self, mock_session):
        """get_by_id returns None when not found."""
        repo = AutomationSuggestionRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id("nonexistent")
        assert result is None

    async def test_list_all(self, mock_session, mock_suggestion):
        """list_all returns list of suggestions."""
        repo = AutomationSuggestionRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_suggestion]
        mock_session.execute.return_value = mock_result

        result = await repo.list_all()
        assert result == [mock_suggestion]
        mock_session.execute.assert_called_once()

    async def test_list_all_with_filters(self, mock_session):
        """list_all with status and job_id passes filters to query."""
        repo = AutomationSuggestionRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.list_all(status="accepted", job_id="job-1")
        mock_session.execute.assert_called_once()
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Select)

    async def test_update_status_true(self, mock_session):
        """update_status returns True when row updated."""
        repo = AutomationSuggestionRepository(mock_session)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repo.update_status("suggestion-1", "accepted")
        assert result is True
        call_arg = mock_session.execute.call_args[0][0]
        assert isinstance(call_arg, Update)

    async def test_update_status_false(self, mock_session):
        """update_status returns False when no row updated."""
        repo = AutomationSuggestionRepository(mock_session)
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repo.update_status("nonexistent", "accepted")
        assert result is False
