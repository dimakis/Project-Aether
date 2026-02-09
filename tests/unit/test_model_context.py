"""Unit tests for model context propagation.

Tests the ModelContext, context manager, and resolution chain.

TDD: T-MR01, T-MR02 - Model context infrastructure.
"""

import pytest

from src.agents.model_context import (
    ModelContext,
    clear_model_context,
    get_model_context,
    model_context,
    resolve_model,
    set_model_context,
)


class TestModelContext:
    """Tests for the ModelContext dataclass."""

    def test_default_values(self):
        """ModelContext should have None defaults."""
        ctx = ModelContext()
        assert ctx.model_name is None
        assert ctx.temperature is None
        assert ctx.parent_span_id is None

    def test_with_values(self):
        """ModelContext should store provided values."""
        ctx = ModelContext(
            model_name="anthropic/claude-sonnet-4",
            temperature=0.5,
            parent_span_id="span-123",
        )
        assert ctx.model_name == "anthropic/claude-sonnet-4"
        assert ctx.temperature == 0.5
        assert ctx.parent_span_id == "span-123"

    def test_immutable(self):
        """ModelContext should be frozen (immutable)."""
        ctx = ModelContext(model_name="gpt-4o")
        with pytest.raises(AttributeError):
            ctx.model_name = "other-model"  # type: ignore[misc]


class TestModelContextManager:
    """Tests for the model_context() context manager."""

    def test_sets_and_clears_context(self):
        """Context manager should set and restore previous context."""
        assert get_model_context() is None

        with model_context(model_name="gpt-4o", temperature=0.7):
            ctx = get_model_context()
            assert ctx is not None
            assert ctx.model_name == "gpt-4o"
            assert ctx.temperature == 0.7

        # Restored to None
        assert get_model_context() is None

    def test_nested_contexts(self):
        """Nested context managers should save/restore correctly."""
        with model_context(model_name="outer-model", temperature=0.5):
            assert get_model_context().model_name == "outer-model"

            with model_context(model_name="inner-model", temperature=0.9):
                assert get_model_context().model_name == "inner-model"
                assert get_model_context().temperature == 0.9

            # Outer restored
            assert get_model_context().model_name == "outer-model"
            assert get_model_context().temperature == 0.5

        assert get_model_context() is None

    def test_yields_context(self):
        """Context manager should yield the created ModelContext."""
        with model_context(model_name="test-model") as ctx:
            assert isinstance(ctx, ModelContext)
            assert ctx.model_name == "test-model"

    def test_context_with_parent_span_id(self):
        """Context manager should propagate parent_span_id."""
        with model_context(
            model_name="test-model",
            parent_span_id="span-abc",
        ):
            ctx = get_model_context()
            assert ctx.parent_span_id == "span-abc"


class TestSetAndClearContext:
    """Tests for set_model_context and clear_model_context."""

    def test_set_model_context(self):
        """set_model_context should update the active context."""
        try:
            ctx = ModelContext(model_name="set-test")
            set_model_context(ctx)
            assert get_model_context() == ctx
        finally:
            clear_model_context()

    def test_clear_model_context(self):
        """clear_model_context should reset to None."""
        with model_context(model_name="to-clear"):
            clear_model_context()
            assert get_model_context() is None


class TestResolveModel:
    """Tests for resolve_model() resolution chain."""

    def test_no_context_no_agent_settings(self):
        """When nothing is set, returns (None, None)."""
        # Ensure no context is active
        clear_model_context()
        model, temp = resolve_model()
        assert model is None
        assert temp is None

    def test_agent_settings_without_context(self):
        """Per-agent settings should be used when no context is active."""
        clear_model_context()
        model, temp = resolve_model(
            agent_model="gpt-4o-mini",
            agent_temperature=0.3,
        )
        assert model == "gpt-4o-mini"
        assert temp == 0.3

    def test_context_overrides_agent_settings(self):
        """Active model context should override per-agent settings."""
        with model_context(model_name="anthropic/claude-sonnet-4", temperature=0.8):
            model, temp = resolve_model(
                agent_model="gpt-4o-mini",
                agent_temperature=0.3,
            )
        assert model == "anthropic/claude-sonnet-4"
        assert temp == 0.8

    def test_context_with_none_model_falls_through(self):
        """Context with model_name=None should fall through to agent settings."""
        with model_context(model_name=None, temperature=None):
            model, temp = resolve_model(
                agent_model="gpt-4o-mini",
                agent_temperature=0.5,
            )
        assert model == "gpt-4o-mini"
        assert temp == 0.5

    def test_context_with_model_but_no_temperature(self):
        """Context with only model_name should return None temperature."""
        with model_context(model_name="test-model"):
            model, temp = resolve_model()
        assert model == "test-model"
        assert temp is None

    def test_agent_model_only_no_temperature(self):
        """Agent model without temperature returns None for temperature."""
        clear_model_context()
        model, temp = resolve_model(agent_model="gpt-4o-mini")
        assert model == "gpt-4o-mini"
        assert temp is None
