"""Unit tests for FlowGrade DAL operations.

Tests FlowGradeRepository CRUD operations with mocked database.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dal.flow_grades import FlowGradeRepository


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
def flow_grade_repo(mock_session):
    """Create FlowGradeRepository with mock session."""
    return FlowGradeRepository(mock_session)


class TestFlowGradeRepositoryUpsert:
    """Tests for FlowGradeRepository.upsert method."""

    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, flow_grade_repo, mock_session):
        """Test upsert creates new grade when none exists."""
        conversation_id = str(uuid4())

        # Mock no existing grade
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await flow_grade_repo.upsert(
            conversation_id=conversation_id,
            grade=1,
            comment="Great!",
        )

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, flow_grade_repo, mock_session):
        """Test upsert updates existing grade."""
        conversation_id = str(uuid4())
        span_id = str(uuid4())

        mock_existing = MagicMock()
        mock_existing.conversation_id = conversation_id
        mock_existing.span_id = span_id
        mock_existing.grade = -1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        result = await flow_grade_repo.upsert(
            conversation_id=conversation_id,
            span_id=span_id,
            grade=1,
            comment="Updated",
        )

        assert result == mock_existing
        assert mock_existing.grade == 1
        assert mock_existing.comment == "Updated"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_with_agent_role(self, flow_grade_repo, mock_session):
        """Test upsert with agent role."""
        conversation_id = str(uuid4())

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await flow_grade_repo.upsert(
            conversation_id=conversation_id,
            grade=1,
            agent_role="architect",
        )

        assert result is not None


class TestFlowGradeRepositoryListForConversation:
    """Tests for FlowGradeRepository.list_for_conversation method."""

    @pytest.mark.asyncio
    async def test_list_for_conversation(self, flow_grade_repo, mock_session):
        """Test listing grades for a conversation."""
        conversation_id = str(uuid4())
        mock_grades = [MagicMock() for _ in range(5)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_grades
        mock_session.execute.return_value = mock_result

        result = await flow_grade_repo.list_for_conversation(conversation_id)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_for_conversation_empty(self, flow_grade_repo, mock_session):
        """Test listing grades when none exist."""
        conversation_id = str(uuid4())

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await flow_grade_repo.list_for_conversation(conversation_id)

        assert result == []


class TestFlowGradeRepositoryGetSummary:
    """Tests for FlowGradeRepository.get_summary method."""

    @pytest.mark.asyncio
    async def test_get_summary_with_overall_and_steps(self, flow_grade_repo, mock_session):
        """Test getting summary with overall and step grades."""
        conversation_id = str(uuid4())

        # Create mock grades
        mock_overall = MagicMock()
        mock_overall.id = str(uuid4())
        mock_overall.span_id = None
        mock_overall.grade = 1
        mock_overall.comment = "Great conversation"
        mock_overall.agent_role = None
        mock_overall.created_at = None

        mock_step1 = MagicMock()
        mock_step1.id = str(uuid4())
        mock_step1.span_id = "span1"
        mock_step1.grade = 1
        mock_step1.comment = "Good step"
        mock_step1.agent_role = "architect"
        mock_step1.created_at = None

        mock_step2 = MagicMock()
        mock_step2.id = str(uuid4())
        mock_step2.span_id = "span2"
        mock_step2.grade = -1
        mock_step2.comment = "Bad step"
        mock_step2.agent_role = "developer"
        mock_step2.created_at = None

        mock_grades = [mock_overall, mock_step1, mock_step2]

        # Mock list_for_conversation
        with patch.object(
            flow_grade_repo, "list_for_conversation", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = mock_grades

            result = await flow_grade_repo.get_summary(conversation_id)

            assert result["conversation_id"] == conversation_id
            assert result["overall"] is not None
            assert len(result["steps"]) == 2
            assert result["total_grades"] == 3
            assert result["thumbs_up"] == 2
            assert result["thumbs_down"] == 1

    @pytest.mark.asyncio
    async def test_get_summary_no_grades(self, flow_grade_repo, mock_session):
        """Test getting summary when no grades exist."""
        conversation_id = str(uuid4())

        with patch.object(
            flow_grade_repo, "list_for_conversation", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []

            result = await flow_grade_repo.get_summary(conversation_id)

            assert result["conversation_id"] == conversation_id
            assert result["overall"] is None
            assert result["steps"] == []
            assert result["total_grades"] == 0
            assert result["thumbs_up"] == 0
            assert result["thumbs_down"] == 0


class TestFlowGradeRepositoryDelete:
    """Tests for FlowGradeRepository.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, flow_grade_repo, mock_session):
        """Test deleting grade."""
        grade_id = str(uuid4())
        mock_grade = MagicMock()
        mock_grade.id = grade_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_grade
        mock_session.execute.return_value = mock_result

        result = await flow_grade_repo.delete(grade_id)

        assert result is True
        mock_session.delete.assert_called_once_with(mock_grade)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, flow_grade_repo, mock_session):
        """Test deleting non-existent grade."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await flow_grade_repo.delete(str(uuid4()))

        assert result is False
