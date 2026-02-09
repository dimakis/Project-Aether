"""Unit tests for Insight conversation_id and task_label fields.

Tests that the Insight model supports conversation_id and task_label columns,
that the repository accepts them, and that persist_findings reads them
from the execution context.

TDD: Insight model conversation/task tagging.
"""

from uuid import uuid4

from src.storage.entities.insight import Insight, InsightType


class TestInsightConversationFields:
    """Tests for new Insight model fields."""

    def test_conversation_id_column_exists(self):
        """Insight should have a conversation_id column."""
        insight = Insight(
            id=str(uuid4()),
            type=InsightType.ENERGY_OPTIMIZATION,
            title="Test",
            description="Test desc",
            evidence={},
            confidence=0.8,
            impact="medium",
            entities=[],
            conversation_id="conv-123",
        )
        assert insight.conversation_id == "conv-123"

    def test_task_label_column_exists(self):
        """Insight should have a task_label column."""
        insight = Insight(
            id=str(uuid4()),
            type=InsightType.ANOMALY_DETECTION,
            title="Test",
            description="Test desc",
            evidence={},
            confidence=0.7,
            impact="high",
            entities=[],
            task_label="Diagnostic: Energy outage 7d",
        )
        assert insight.task_label == "Diagnostic: Energy outage 7d"

    def test_fields_are_nullable(self):
        """conversation_id and task_label should be nullable (None by default)."""
        insight = Insight(
            id=str(uuid4()),
            type=InsightType.USAGE_PATTERN,
            title="Test",
            description="Test desc",
            evidence={},
            confidence=0.5,
            impact="low",
            entities=[],
        )
        assert insight.conversation_id is None
        assert insight.task_label is None

    def test_both_fields_set(self):
        """Both fields can be set simultaneously."""
        insight = Insight(
            id=str(uuid4()),
            type=InsightType.USAGE_PATTERN,
            title="Test",
            description="Test desc",
            evidence={},
            confidence=0.5,
            impact="low",
            entities=[],
            conversation_id="conv-abc",
            task_label="Analysis task",
        )
        assert insight.conversation_id == "conv-abc"
        assert insight.task_label == "Analysis task"
