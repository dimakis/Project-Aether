"""Unit tests for model tier classification.

Tests the tier map, heuristic fallbacks, and model resolution logic.
"""

from __future__ import annotations

import pytest

from src.llm.model_tiers import (
    ModelTier,
    get_default_model_for_tier,
    get_model_tier,
    resolve_model_for_tier,
)


class TestGetModelTier:
    """Tests for get_model_tier()."""

    @pytest.mark.parametrize(
        ("model", "expected_tier"),
        [
            ("gpt-4o-mini", "fast"),
            ("gpt-4o", "standard"),
            ("gpt-5", "frontier"),
            ("anthropic/claude-sonnet-4", "standard"),
            ("anthropic/claude-3-opus", "frontier"),
        ],
    )
    def test_returns_correct_tier_for_known_models(self, model: str, expected_tier: str) -> None:
        assert get_model_tier(model) == expected_tier

    def test_returns_standard_for_unknown_models(self) -> None:
        assert get_model_tier("some-unknown-model-v7") == "standard"

    @pytest.mark.parametrize(
        "model",
        ["custom-mini-v2", "acme-flash-3", "vendor/haiku-xl", "tiny-nano-1b"],
    )
    def test_heuristic_mini_flash_haiku_maps_to_fast(self, model: str) -> None:
        assert get_model_tier(model) == "fast"

    @pytest.mark.parametrize(
        "model",
        ["custom-opus-3", "vendor/o1-custom"],
    )
    def test_heuristic_opus_o1_maps_to_frontier(self, model: str) -> None:
        assert get_model_tier(model) == "frontier"


class TestGetDefaultModelForTier:
    """Tests for get_default_model_for_tier()."""

    @pytest.mark.parametrize(
        ("tier", "expected"),
        [
            ("fast", "gpt-4o-mini"),
            ("standard", "gpt-4o"),
            ("frontier", "gpt-5"),
        ],
    )
    def test_returns_expected_defaults(self, tier: ModelTier, expected: str) -> None:
        assert get_default_model_for_tier(tier) == expected


class TestResolveModelForTier:
    """Tests for resolve_model_for_tier()."""

    def test_picks_from_available_models(self) -> None:
        available = ["gpt-4o-mini", "gpt-4o", "gpt-5"]
        assert resolve_model_for_tier("fast", available) == "gpt-4o-mini"
        assert resolve_model_for_tier("standard", available) == "gpt-4o"
        assert resolve_model_for_tier("frontier", available) == "gpt-5"

    def test_falls_back_to_default_without_available(self) -> None:
        assert resolve_model_for_tier("fast") == "gpt-4o-mini"
        assert resolve_model_for_tier("standard") == "gpt-4o"

    def test_falls_back_to_default_when_tier_not_in_available(self) -> None:
        available = ["gpt-4o-mini"]
        assert resolve_model_for_tier("frontier", available) == "gpt-5"
