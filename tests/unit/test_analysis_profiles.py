"""Unit tests for analysis profiles: depth, strategy, and policy factory.

Tests T3320-T3323: AnalysisDepth/ExecutionStrategy enums, depth+strategy
fields on AnalysisState, configurable timeout/memory settings, and
get_policy_for_depth() factory.
"""

import pytest

# =============================================================================
# T3320: AnalysisDepth and ExecutionStrategy enums
# =============================================================================


class TestAnalysisDepthEnum:
    """Test the AnalysisDepth enum."""

    def test_values(self):
        from src.graph.state import AnalysisDepth

        assert AnalysisDepth.QUICK == "quick"
        assert AnalysisDepth.STANDARD == "standard"
        assert AnalysisDepth.DEEP == "deep"

    def test_is_str_enum(self):
        from src.graph.state import AnalysisDepth

        assert isinstance(AnalysisDepth.QUICK, str)

    def test_all_values(self):
        from src.graph.state import AnalysisDepth

        assert len(AnalysisDepth) == 3


class TestExecutionStrategyEnum:
    """Test the ExecutionStrategy enum."""

    def test_values(self):
        from src.graph.state import ExecutionStrategy

        assert ExecutionStrategy.PARALLEL == "parallel"
        assert ExecutionStrategy.TEAMWORK == "teamwork"

    def test_is_str_enum(self):
        from src.graph.state import ExecutionStrategy

        assert isinstance(ExecutionStrategy.PARALLEL, str)

    def test_all_values(self):
        from src.graph.state import ExecutionStrategy

        assert len(ExecutionStrategy) == 2


# =============================================================================
# T3321: depth and strategy fields on AnalysisState
# =============================================================================


class TestAnalysisStateFields:
    """Test that AnalysisState includes depth and strategy fields."""

    def test_default_depth_is_standard(self):
        from src.graph.state import AnalysisDepth, AnalysisState

        state = AnalysisState()
        assert state.depth == AnalysisDepth.STANDARD

    def test_default_strategy_is_parallel(self):
        from src.graph.state import AnalysisState, ExecutionStrategy

        state = AnalysisState()
        assert state.strategy == ExecutionStrategy.PARALLEL

    def test_can_set_depth(self):
        from src.graph.state import AnalysisDepth, AnalysisState

        state = AnalysisState(depth=AnalysisDepth.DEEP)
        assert state.depth == AnalysisDepth.DEEP

    def test_can_set_strategy(self):
        from src.graph.state import AnalysisState, ExecutionStrategy

        state = AnalysisState(strategy=ExecutionStrategy.TEAMWORK)
        assert state.strategy == ExecutionStrategy.TEAMWORK

    def test_depth_from_string(self):
        from src.graph.state import AnalysisDepth, AnalysisState

        state = AnalysisState(depth="deep")
        assert state.depth == AnalysisDepth.DEEP

    def test_strategy_from_string(self):
        from src.graph.state import AnalysisState, ExecutionStrategy

        state = AnalysisState(strategy="teamwork")
        assert state.strategy == ExecutionStrategy.TEAMWORK


# =============================================================================
# T3322: Configurable timeout and memory settings
# =============================================================================


class TestDepthSettings:
    """Test per-depth timeout and memory settings."""

    def test_timeout_defaults(self):
        from src.settings import Settings

        s = Settings(environment="testing", ha_token="test")  # type: ignore[arg-type]
        assert s.sandbox_timeout_quick == 30
        assert s.sandbox_timeout_standard == 60
        assert s.sandbox_timeout_deep == 180

    def test_memory_defaults(self):
        from src.settings import Settings

        s = Settings(environment="testing", ha_token="test")  # type: ignore[arg-type]
        assert s.sandbox_memory_quick == 512
        assert s.sandbox_memory_standard == 1024
        assert s.sandbox_memory_deep == 2048

    def test_timeout_can_be_overridden(self):
        from src.settings import Settings

        s = Settings(
            environment="testing",
            ha_token="test",  # type: ignore[arg-type]
            sandbox_timeout_deep=300,
        )
        assert s.sandbox_timeout_deep == 300

    def test_memory_can_be_overridden(self):
        from src.settings import Settings

        s = Settings(
            environment="testing",
            ha_token="test",  # type: ignore[arg-type]
            sandbox_memory_deep=4096,
        )
        assert s.sandbox_memory_deep == 4096


# =============================================================================
# T3323: get_policy_for_depth()
# =============================================================================


class TestGetPolicyForDepth:
    """Test the depth-aware policy factory."""

    def test_quick_policy(self):
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_quick = 30
        settings.sandbox_memory_quick = 512
        settings.sandbox_artifacts_enabled = False
        settings.sandbox_timeout_deep = 180

        policy = get_policy_for_depth("quick", settings)
        assert policy.timeout_seconds == 30
        assert policy.resources.memory_mb == 512
        assert policy.artifacts_enabled is False
        assert policy.name == "depth:quick"

    def test_standard_policy(self):
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_standard = 60
        settings.sandbox_memory_standard = 1024
        settings.sandbox_artifacts_enabled = False
        settings.sandbox_timeout_deep = 180

        policy = get_policy_for_depth("standard", settings)
        assert policy.timeout_seconds == 60
        assert policy.resources.memory_mb == 1024

    def test_deep_policy(self):
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_deep = 180
        settings.sandbox_memory_deep = 2048
        settings.sandbox_artifacts_enabled = True

        policy = get_policy_for_depth("deep", settings)
        assert policy.timeout_seconds == 180
        assert policy.resources.memory_mb == 2048
        assert policy.artifacts_enabled is True

    def test_deep_enables_artifacts_when_global_true(self):
        """Deep analysis automatically enables per-policy artifacts when global is on."""
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_deep = 180
        settings.sandbox_memory_deep = 2048
        settings.sandbox_artifacts_enabled = True

        policy = get_policy_for_depth("deep", settings)
        assert policy.artifacts_enabled is True

    def test_deep_artifacts_false_when_global_false(self):
        """Deep analysis does NOT enable artifacts when global is off."""
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_deep = 180
        settings.sandbox_memory_deep = 2048
        settings.sandbox_artifacts_enabled = False

        policy = get_policy_for_depth("deep", settings)
        assert policy.artifacts_enabled is False

    def test_timeout_override(self):
        """timeout_override replaces the depth default."""
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_standard = 60
        settings.sandbox_memory_standard = 1024
        settings.sandbox_artifacts_enabled = False
        settings.sandbox_timeout_deep = 180

        policy = get_policy_for_depth("standard", settings, timeout_override=120)
        assert policy.timeout_seconds == 120

    def test_timeout_override_clamped_to_deep_ceiling(self):
        """timeout_override cannot exceed sandbox_timeout_deep."""
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_standard = 60
        settings.sandbox_memory_standard = 1024
        settings.sandbox_artifacts_enabled = False
        settings.sandbox_timeout_deep = 180

        policy = get_policy_for_depth("standard", settings, timeout_override=999)
        assert policy.timeout_seconds == 180  # Clamped to deep ceiling

    def test_timeout_override_clamped_minimum(self):
        """timeout_override cannot go below 5 seconds."""
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_quick = 30
        settings.sandbox_memory_quick = 512
        settings.sandbox_artifacts_enabled = False
        settings.sandbox_timeout_deep = 180

        policy = get_policy_for_depth("quick", settings, timeout_override=1)
        assert policy.timeout_seconds == 5  # Clamped to minimum

    def test_artifacts_override(self):
        """artifacts_enabled can be explicitly set."""
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_standard = 60
        settings.sandbox_memory_standard = 1024
        settings.sandbox_artifacts_enabled = True
        settings.sandbox_timeout_deep = 180

        policy = get_policy_for_depth("standard", settings, artifacts_enabled=True)
        assert policy.artifacts_enabled is True

    def test_invalid_depth_raises(self):
        """Unknown depth value raises ValueError."""
        from unittest.mock import MagicMock

        from src.sandbox.policies import get_policy_for_depth

        settings = MagicMock()
        settings.sandbox_timeout_deep = 180

        with pytest.raises(ValueError, match="Unknown depth"):
            get_policy_for_depth("ultra", settings)
