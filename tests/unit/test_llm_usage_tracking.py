"""Unit tests for LLM usage tracking in the ResilientLLM wrapper.

Tests that token usage is extracted from LLM responses and
logged via the usage tracking context variable system.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm_pricing import calculate_cost


class TestUsageContextVar:
    """Test the LLM usage context variable for passing metadata."""

    def test_context_var_import(self):
        """The LLM call context module is importable."""
        from src.llm_call_context import (
            get_llm_call_context,
            set_llm_call_context,
            LLMCallContext,
        )
        assert LLMCallContext is not None

    def test_set_and_get_context(self):
        """Can set and retrieve LLM call context."""
        from src.llm_call_context import (
            get_llm_call_context,
            set_llm_call_context,
            LLMCallContext,
        )
        ctx = LLMCallContext(
            conversation_id="test-conv-id",
            agent_role="architect",
            request_type="chat",
        )
        token = set_llm_call_context(ctx)
        retrieved = get_llm_call_context()
        assert retrieved is not None
        assert retrieved.conversation_id == "test-conv-id"
        assert retrieved.agent_role == "architect"

    def test_default_context_is_none(self):
        """Without setting, context returns None."""
        from src.llm_call_context import _llm_call_context
        # Reset the context var
        token = _llm_call_context.set(None)
        from src.llm_call_context import get_llm_call_context
        assert get_llm_call_context() is None
        _llm_call_context.reset(token)


class TestCostCalculationIntegration:
    """Test cost calculation with realistic token counts."""

    def test_typical_chat_turn(self):
        """Calculate cost for a typical chat interaction."""
        cost = calculate_cost("gpt-4o", input_tokens=500, output_tokens=300)
        assert cost is not None
        assert 0.001 < cost < 0.01  # Reasonable range for a chat turn

    def test_large_analysis_run(self):
        """Calculate cost for a large analysis/insight generation."""
        cost = calculate_cost("gpt-4o", input_tokens=10000, output_tokens=5000)
        assert cost is not None
        assert cost > 0.05  # Non-trivial cost

    def test_mini_model_much_cheaper(self):
        """Mini models are significantly cheaper."""
        full_cost = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        mini_cost = calculate_cost("gpt-4o-mini", input_tokens=1000, output_tokens=500)
        assert full_cost is not None and mini_cost is not None
        assert mini_cost < full_cost * 0.15  # Mini is at least 85% cheaper
