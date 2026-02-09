"""Unit tests for Insight DAL operations.

Tests InsightRepository CRUD operations with mocked database.
Constitution: Reliability & Quality - comprehensive DAL testing.

TDD: T181 - InsightRepository unit tests.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.dal.insights import InsightRepository
from src.storage.entities.insight import Insight, InsightStatus, InsightType


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
def insight_repo(mock_session):
    """Create InsightRepository with mock session."""
    return InsightRepository(mock_session)


@pytest.fixture
def sample_insight():
    """Create a sample insight for testing."""
    return Insight(
        id=str(uuid4()),
        type=InsightType.ENERGY_OPTIMIZATION,
        title="High energy usage detected",
        description="Your HVAC is using 30% more energy than average",
        evidence={"avg_usage": 150, "your_usage": 195},
        confidence=0.85,
        impact="high",
        entities=["climate.living_room", "sensor.hvac_power"],
        status=InsightStatus.PENDING,
    )


class TestInsightRepositoryCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_insight(self, insight_repo, mock_session):
        """Test creating a new insight."""
        await insight_repo.create(
            type=InsightType.ENERGY_OPTIMIZATION,
            title="Test Insight",
            description="Test description",
            evidence={"test": "data"},
            confidence=0.9,
            impact="medium",
            entities=["sensor.test"],
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Check the insight was created with correct values
        added_insight = mock_session.add.call_args[0][0]
        assert added_insight.type == InsightType.ENERGY_OPTIMIZATION
        assert added_insight.title == "Test Insight"
        assert added_insight.confidence == 0.9
        assert added_insight.status == InsightStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_insight_with_script(self, insight_repo, mock_session):
        """Test creating insight with script information."""
        await insight_repo.create(
            type=InsightType.ENERGY_OPTIMIZATION,
            title="Script Analysis",
            description="Analysis from script",
            evidence={},
            confidence=0.8,
            impact="high",
            script_path="/mlflow/artifacts/analysis.py",
            script_output={"chart": "base64..."},
            mlflow_run_id="run-123",
        )

        added_insight = mock_session.add.call_args[0][0]
        assert added_insight.script_path == "/mlflow/artifacts/analysis.py"
        assert added_insight.mlflow_run_id == "run-123"


class TestInsightRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, insight_repo, mock_session, sample_insight):
        """Test getting insight by ID when it exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_insight
        mock_session.execute.return_value = mock_result

        result = await insight_repo.get_by_id(sample_insight.id)

        assert result == sample_insight
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, insight_repo, mock_session):
        """Test getting insight by ID when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await insight_repo.get_by_id("nonexistent-id")

        assert result is None


class TestInsightRepositoryListMethods:
    """Tests for list methods."""

    @pytest.mark.asyncio
    async def test_list_by_type(self, insight_repo, mock_session, sample_insight):
        """Test listing insights by type."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_insight]
        mock_session.execute.return_value = mock_result

        results = await insight_repo.list_by_type(InsightType.ENERGY_OPTIMIZATION)

        assert len(results) == 1
        assert results[0] == sample_insight

    @pytest.mark.asyncio
    async def test_list_by_status(self, insight_repo, mock_session, sample_insight):
        """Test listing insights by status."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_insight]
        mock_session.execute.return_value = mock_result

        results = await insight_repo.list_by_status(InsightStatus.PENDING)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_pending(self, insight_repo, mock_session, sample_insight):
        """Test listing pending insights."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_insight]
        mock_session.execute.return_value = mock_result

        results = await insight_repo.list_pending()

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_high_confidence(self, insight_repo, mock_session, sample_insight):
        """Test listing high confidence insights."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_insight]
        mock_session.execute.return_value = mock_result

        results = await insight_repo.list_high_confidence(min_confidence=0.8)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_by_impact(self, insight_repo, mock_session, sample_insight):
        """Test listing insights by impact."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_insight]
        mock_session.execute.return_value = mock_result

        results = await insight_repo.list_by_impact("high")

        assert len(results) == 1


class TestInsightRepositoryStatusTransitions:
    """Tests for status transition methods."""

    @pytest.mark.asyncio
    async def test_mark_reviewed(self, insight_repo, mock_session, sample_insight):
        """Test marking insight as reviewed."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_insight
        mock_session.execute.return_value = mock_result

        result = await insight_repo.mark_reviewed(sample_insight.id)

        assert result.status == InsightStatus.REVIEWED
        assert result.reviewed_at is not None
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_actioned(self, insight_repo, mock_session, sample_insight):
        """Test marking insight as actioned."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_insight
        mock_session.execute.return_value = mock_result

        result = await insight_repo.mark_actioned(sample_insight.id)

        assert result.status == InsightStatus.ACTIONED
        assert result.actioned_at is not None

    @pytest.mark.asyncio
    async def test_dismiss(self, insight_repo, mock_session, sample_insight):
        """Test dismissing insight."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_insight
        mock_session.execute.return_value = mock_result

        result = await insight_repo.dismiss(sample_insight.id)

        assert result.status == InsightStatus.DISMISSED


class TestInsightRepositoryCount:
    """Tests for count methods."""

    @pytest.mark.asyncio
    async def test_count_all(self, insight_repo, mock_session):
        """Test counting all insights."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        count = await insight_repo.count()

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_by_type(self, insight_repo, mock_session):
        """Test counting by type filter."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        count = await insight_repo.count(type=InsightType.ENERGY_OPTIMIZATION)

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_by_status(self, insight_repo, mock_session):
        """Test counting by status filter."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        mock_session.execute.return_value = mock_result

        count = await insight_repo.count(status=InsightStatus.PENDING)

        assert count == 2


class TestInsightRepositoryDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_existing(self, insight_repo, mock_session, sample_insight):
        """Test deleting an existing insight."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_insight
        mock_session.execute.return_value = mock_result

        result = await insight_repo.delete(sample_insight.id)

        assert result is True
        mock_session.delete.assert_called_once_with(sample_insight)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, insight_repo, mock_session):
        """Test deleting a nonexistent insight."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await insight_repo.delete("nonexistent-id")

        assert result is False
        mock_session.delete.assert_not_called()


class TestInsightRepositoryMlflowIntegration:
    """Tests for MLflow-related methods."""

    @pytest.mark.asyncio
    async def test_get_by_mlflow_run(self, insight_repo, mock_session, sample_insight):
        """Test getting insights by MLflow run ID."""
        sample_insight.mlflow_run_id = "run-123"
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_insight]
        mock_session.execute.return_value = mock_result

        results = await insight_repo.get_by_mlflow_run("run-123")

        assert len(results) == 1
        assert results[0].mlflow_run_id == "run-123"
