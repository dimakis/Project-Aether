"""Unit tests for LLM pricing module."""

import pytest

from src.llm_pricing import calculate_cost, get_model_pricing, list_known_models


class TestGetModelPricing:
    """Test model pricing lookup."""

    def test_known_model_returns_pricing(self):
        """Known models return pricing data."""
        pricing = get_model_pricing("gpt-4o")
        assert pricing is not None
        assert pricing["input_per_1m"] > 0
        assert pricing["output_per_1m"] > 0

    def test_unknown_model_returns_none(self):
        """Unknown models return None."""
        assert get_model_pricing("nonexistent-model-xyz") is None

    def test_anthropic_model_with_prefix(self):
        """Anthropic models with OpenRouter prefix are found."""
        pricing = get_model_pricing("anthropic/claude-sonnet-4")
        assert pricing is not None

    def test_gemini_model(self):
        """Gemini models are in the pricing table."""
        pricing = get_model_pricing("gemini-2.0-flash")
        assert pricing is not None


class TestCalculateCost:
    """Test cost calculation."""

    def test_calculate_cost_known_model(self):
        """Cost is calculated correctly for known models."""
        # gpt-4o: $2.50/1M input, $10.00/1M output
        cost = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert cost is not None
        # 1000/1M * 2.50 + 500/1M * 10.00 = 0.0025 + 0.005 = 0.0075
        assert cost == pytest.approx(0.0075, abs=0.0001)

    def test_calculate_cost_unknown_model(self):
        """Unknown model returns None."""
        cost = calculate_cost("unknown-model", input_tokens=100, output_tokens=50)
        assert cost is None

    def test_calculate_cost_zero_tokens(self):
        """Zero tokens results in zero cost."""
        cost = calculate_cost("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_calculate_cost_large_usage(self):
        """Large token counts produce proportional costs."""
        cost = calculate_cost("gpt-4o", input_tokens=1_000_000, output_tokens=500_000)
        assert cost is not None
        # 1M * 2.50/1M + 0.5M * 10.00/1M = 2.50 + 5.00 = 7.50
        assert cost == pytest.approx(7.50, abs=0.01)

    def test_calculate_cost_cheap_model(self):
        """Cheap models (mini/flash) have lower costs."""
        cheap = calculate_cost("gpt-4o-mini", input_tokens=10000, output_tokens=5000)
        expensive = calculate_cost("gpt-4o", input_tokens=10000, output_tokens=5000)
        assert cheap is not None
        assert expensive is not None
        assert cheap < expensive


class TestListKnownModels:
    """Test listing known models."""

    def test_returns_sorted_list(self):
        """Returns a sorted list of model names."""
        models = list_known_models()
        assert len(models) > 10  # We have many models defined
        assert models == sorted(models)

    def test_common_models_present(self):
        """Common models are in the list."""
        models = list_known_models()
        assert "gpt-4o" in models
        assert "gemini-2.0-flash" in models
