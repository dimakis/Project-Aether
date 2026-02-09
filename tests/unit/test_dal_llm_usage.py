"""Unit tests for LLM Usage DAL operations.

Tests LLMUsageRepository CRUD operations with mocked database.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.dal.llm_usage import LLMUsageRepository


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def llm_usage_repo(mock_session):
    """Create LLMUsageRepository with mock session."""
    return LLMUsageRepository(mock_session)


class TestLLMUsageRepositoryRecord:
    """Tests for LLMUsageRepository.record method."""

    @pytest.mark.asyncio
    async def test_record_success(self, llm_usage_repo, mock_session):
        """Test recording LLM usage."""
        result = await llm_usage_repo.record(
            provider="anthropic",
            model="claude-sonnet-4",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.01,
            latency_ms=500,
            conversation_id=str(uuid4()),
            agent_role="architect",
        )

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestLLMUsageRepositoryGetSummary:
    """Tests for LLMUsageRepository.get_summary method."""

    @pytest.mark.asyncio
    async def test_get_summary(self, llm_usage_repo, mock_session):
        """Test getting usage summary."""
        # Mock total aggregates
        mock_row = MagicMock()
        mock_row.total_calls = 100
        mock_row.total_input_tokens = 10000
        mock_row.total_output_tokens = 5000
        mock_row.total_tokens = 15000
        mock_row.total_cost_usd = 1.5

        mock_result_total = MagicMock()
        mock_result_total.one.return_value = mock_row

        # Mock per-model breakdown
        mock_model_rows = [
            MagicMock(
                model="claude-sonnet-4",
                provider="anthropic",
                calls=50,
                tokens=7500,
                cost_usd=0.75,
            ),
            MagicMock(
                model="gpt-4",
                provider="openai",
                calls=50,
                tokens=7500,
                cost_usd=0.75,
            ),
        ]

        mock_result_models = MagicMock()
        mock_result_models.__iter__ = lambda self: iter(mock_model_rows)

        mock_session.execute.side_effect = [mock_result_total, mock_result_models]

        result = await llm_usage_repo.get_summary(days=30)

        assert result["period_days"] == 30
        assert result["total_calls"] == 100
        assert result["total_tokens"] == 15000
        assert result["total_cost_usd"] == 1.5
        assert len(result["by_model"]) == 2

    @pytest.mark.asyncio
    async def test_get_summary_empty(self, llm_usage_repo, mock_session):
        """Test getting summary when no usage exists."""
        mock_row = MagicMock()
        mock_row.total_calls = 0
        mock_row.total_input_tokens = 0
        mock_row.total_output_tokens = 0
        mock_row.total_tokens = 0
        mock_row.total_cost_usd = 0.0

        mock_result_total = MagicMock()
        mock_result_total.one.return_value = mock_row

        mock_result_models = MagicMock()
        mock_result_models.__iter__ = lambda self: iter([])

        mock_session.execute.side_effect = [mock_result_total, mock_result_models]

        result = await llm_usage_repo.get_summary(days=30)

        assert result["total_calls"] == 0
        assert result["by_model"] == []


class TestLLMUsageRepositoryGetDaily:
    """Tests for LLMUsageRepository.get_daily method."""

    @pytest.mark.asyncio
    async def test_get_daily(self, llm_usage_repo, mock_session):
        """Test getting daily usage breakdown."""
        mock_rows = [
            MagicMock(
                day=datetime.now(UTC).date(),
                calls=10,
                tokens=1500,
                cost_usd=0.15,
            ),
            MagicMock(
                day=(datetime.now(UTC) - timedelta(days=1)).date(),
                calls=5,
                tokens=750,
                cost_usd=0.075,
            ),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(mock_rows)

        mock_session.execute.return_value = mock_result

        result = await llm_usage_repo.get_daily(days=30)

        assert len(result) == 2
        assert result[0]["calls"] == 10
        assert result[1]["calls"] == 5


class TestLLMUsageRepositoryGetConversationCost:
    """Tests for LLMUsageRepository.get_conversation_cost method."""

    @pytest.mark.asyncio
    async def test_get_conversation_cost(self, llm_usage_repo, mock_session):
        """Test getting conversation cost."""
        conversation_id = str(uuid4())

        # Mock total aggregates
        mock_row = MagicMock()
        mock_row.total_calls = 5
        mock_row.total_input_tokens = 500
        mock_row.total_output_tokens = 250
        mock_row.total_tokens = 750
        mock_row.total_cost_usd = 0.075

        mock_result_total = MagicMock()
        mock_result_total.one.return_value = mock_row

        # Mock per-agent breakdown
        mock_agent_rows = [
            MagicMock(
                agent_role="architect",
                model="claude-sonnet-4",
                calls=3,
                tokens=450,
                cost_usd=0.045,
                avg_latency_ms=500.0,
            ),
            MagicMock(
                agent_role="developer",
                model="gpt-4",
                calls=2,
                tokens=300,
                cost_usd=0.03,
                avg_latency_ms=600.0,
            ),
        ]

        mock_result_agents = MagicMock()
        mock_result_agents.__iter__ = lambda self: iter(mock_agent_rows)

        mock_session.execute.side_effect = [mock_result_total, mock_result_agents]

        result = await llm_usage_repo.get_conversation_cost(conversation_id)

        assert result["conversation_id"] == conversation_id
        assert result["total_calls"] == 5
        assert result["total_tokens"] == 750
        assert result["total_cost_usd"] == 0.075
        assert len(result["by_agent"]) == 2

    @pytest.mark.asyncio
    async def test_get_conversation_cost_empty(self, llm_usage_repo, mock_session):
        """Test getting conversation cost when no usage exists."""
        conversation_id = str(uuid4())

        mock_row = MagicMock()
        mock_row.total_calls = 0
        mock_row.total_input_tokens = 0
        mock_row.total_output_tokens = 0
        mock_row.total_tokens = 0
        mock_row.total_cost_usd = 0.0

        mock_result_total = MagicMock()
        mock_result_total.one.return_value = mock_row

        mock_result_agents = MagicMock()
        mock_result_agents.__iter__ = lambda self: iter([])

        mock_session.execute.side_effect = [mock_result_total, mock_result_agents]

        result = await llm_usage_repo.get_conversation_cost(conversation_id)

        assert result["total_calls"] == 0
        assert result["by_agent"] == []


class TestLLMUsageRepositoryGetByModel:
    """Tests for LLMUsageRepository.get_by_model method."""

    @pytest.mark.asyncio
    async def test_get_by_model(self, llm_usage_repo, mock_session):
        """Test getting per-model usage breakdown."""
        mock_rows = [
            MagicMock(
                model="claude-sonnet-4",
                provider="anthropic",
                calls=50,
                input_tokens=5000,
                output_tokens=2500,
                tokens=7500,
                cost_usd=0.75,
                avg_latency_ms=500.0,
            ),
            MagicMock(
                model="gpt-4",
                provider="openai",
                calls=30,
                input_tokens=3000,
                output_tokens=1500,
                tokens=4500,
                cost_usd=0.45,
                avg_latency_ms=600.0,
            ),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(mock_rows)

        mock_session.execute.return_value = mock_result

        result = await llm_usage_repo.get_by_model(days=30)

        assert len(result) == 2
        assert result[0]["model"] == "claude-sonnet-4"
        assert result[0]["calls"] == 50
        assert result[0]["input_tokens"] == 5000
        assert result[0]["output_tokens"] == 2500
        assert result[0]["tokens"] == 7500
        assert result[0]["cost_usd"] == 0.75
        assert result[0]["avg_latency_ms"] == 500.0

    @pytest.mark.asyncio
    async def test_get_by_model_with_none_latency(self, llm_usage_repo, mock_session):
        """Test getting by model when latency is None."""
        mock_rows = [
            MagicMock(
                model="claude-sonnet-4",
                provider="anthropic",
                calls=10,
                input_tokens=1000,
                output_tokens=500,
                tokens=1500,
                cost_usd=0.15,
                avg_latency_ms=None,
            ),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(mock_rows)

        mock_session.execute.return_value = mock_result

        result = await llm_usage_repo.get_by_model(days=30)

        assert len(result) == 1
        assert result[0]["avg_latency_ms"] is None
