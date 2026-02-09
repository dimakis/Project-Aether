"""Unit tests for src/tracing/scorers.py.

Tests the scorer functions and helpers. MLflow scorers are only testable
when mlflow.genai is available, so we test them conditionally.
"""

from unittest.mock import MagicMock

import pytest

from src.tracing.scorers import (
    _APPROVAL_SPANS,
    _LATENCY_THRESHOLD_MS,
    _MAX_DELEGATION_DEPTH,
    _MUTATION_TOOLS,
    _has_approval_ancestor,
    get_all_scorers,
)


class TestConstants:
    def test_latency_threshold(self):
        assert _LATENCY_THRESHOLD_MS == 30_000

    def test_mutation_tools(self):
        assert "entity_action" in _MUTATION_TOOLS
        assert "deploy_automation" in _MUTATION_TOOLS

    def test_approval_spans(self):
        assert "approve_proposal" in _APPROVAL_SPANS
        assert "deploy_proposal" in _APPROVAL_SPANS

    def test_max_delegation_depth(self):
        assert _MAX_DELEGATION_DEPTH == 6


class TestHasApprovalAncestor:
    def test_no_parent(self):
        span = MagicMock()
        span.parent_id = None
        assert _has_approval_ancestor(span, {}) is False

    def test_parent_is_approval(self):
        span = MagicMock()
        span.parent_id = "parent-1"

        parent = MagicMock()
        parent.name = "approve_proposal"
        parent.parent_id = None

        span_map = {"parent-1": parent}
        assert _has_approval_ancestor(span, span_map) is True

    def test_grandparent_is_approval(self):
        span = MagicMock()
        span.parent_id = "parent-1"

        parent = MagicMock()
        parent.name = "some_operation"
        parent.parent_id = "grandparent-1"

        grandparent = MagicMock()
        grandparent.name = "deploy_proposal"
        grandparent.parent_id = None

        span_map = {"parent-1": parent, "grandparent-1": grandparent}
        assert _has_approval_ancestor(span, span_map) is True

    def test_no_approval_in_chain(self):
        span = MagicMock()
        span.parent_id = "parent-1"

        parent = MagicMock()
        parent.name = "some_operation"
        parent.parent_id = None

        span_map = {"parent-1": parent}
        assert _has_approval_ancestor(span, span_map) is False

    def test_cycle_guard(self):
        span = MagicMock()
        span.parent_id = "parent-1"

        parent = MagicMock()
        parent.name = "loop_operation"
        parent.parent_id = "parent-1"  # cycle

        span_map = {"parent-1": parent}
        assert _has_approval_ancestor(span, span_map) is False


class TestGetAllScorers:
    def test_returns_list(self):
        scorers = get_all_scorers()
        assert isinstance(scorers, list)

    def test_scorers_when_available(self):
        """If mlflow.genai is available, should return scorers."""
        from src.tracing.scorers import _SCORERS_AVAILABLE

        scorers = get_all_scorers()
        if _SCORERS_AVAILABLE:
            assert len(scorers) > 0
        else:
            assert len(scorers) == 0


class TestResponseLatencyScorer:
    """Test response_latency scorer if available."""

    @pytest.fixture
    def scorer_fn(self):
        try:
            from src.tracing.scorers import response_latency

            return response_latency
        except (ImportError, NameError):
            pytest.skip("MLflow scorers not available")

    def test_within_threshold(self, scorer_fn):
        trace = MagicMock()
        trace.info.execution_duration = 5000  # 5 seconds
        result = scorer_fn(trace)
        assert result.value == "yes"

    def test_above_threshold(self, scorer_fn):
        trace = MagicMock()
        trace.info.execution_duration = 60000  # 60 seconds
        result = scorer_fn(trace)
        assert result.value == "no"

    def test_no_duration(self, scorer_fn):
        trace = MagicMock()
        trace.info.execution_duration = None
        result = scorer_fn(trace)
        assert result.value == "no"


class TestToolUsageSafetyScorer:
    @pytest.fixture
    def scorer_fn(self):
        try:
            from src.tracing.scorers import tool_usage_safety

            return tool_usage_safety
        except (ImportError, NameError):
            pytest.skip("MLflow scorers not available")

    def test_no_tool_spans(self, scorer_fn):
        trace = MagicMock()
        trace.search_spans.return_value = []
        result = scorer_fn(trace)
        assert result.value == "yes"

    def test_safe_mutation_with_approval(self, scorer_fn):
        tool_span = MagicMock()
        tool_span.name = "entity_action"
        tool_span.parent_id = "parent-1"

        parent = MagicMock()
        parent.name = "approve_proposal"
        parent.parent_id = None
        parent.span_id = "parent-1"

        trace = MagicMock()
        trace.search_spans.return_value = [tool_span]
        trace.data.spans = [tool_span, parent]

        result = scorer_fn(trace)
        assert result.value == "yes"


class TestAgentDelegationDepthScorer:
    @pytest.fixture
    def scorer_fn(self):
        try:
            from src.tracing.scorers import agent_delegation_depth

            return agent_delegation_depth
        except (ImportError, NameError):
            pytest.skip("MLflow scorers not available")

    def test_no_spans(self, scorer_fn):
        trace = MagicMock()
        trace.data.spans = []
        result = scorer_fn(trace)
        assert result.value == "yes"

    def test_within_depth(self, scorer_fn):
        span = MagicMock()
        span.span_id = "s1"
        span.parent_id = None
        span.span_type = "CHAIN"

        trace = MagicMock()
        trace.data.spans = [span]
        result = scorer_fn(trace)
        assert result.value == "yes"
        assert "depth: 1" in result.rationale


class TestToolCallCountScorer:
    @pytest.fixture
    def scorer_fn(self):
        try:
            from src.tracing.scorers import tool_call_count

            return tool_call_count
        except (ImportError, NameError):
            pytest.skip("MLflow scorers not available")

    def test_counts_tools(self, scorer_fn):
        trace = MagicMock()
        trace.search_spans.return_value = [MagicMock(), MagicMock(), MagicMock()]
        result = scorer_fn(trace)
        assert result.value == 3
        assert "3 tool" in result.rationale
