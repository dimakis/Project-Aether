"""Unit tests for depth/strategy prompt fragment loading.

Tests T3328-T3333: Prompt fragment loading, content checks, and wiring.
"""


# =============================================================================
# T3328: load_depth_fragment
# =============================================================================


class TestLoadDepthFragment:
    """Test depth prompt fragment loading."""

    def test_quick_loads(self):
        from src.agents.prompts import load_depth_fragment

        fragment = load_depth_fragment("quick")
        assert len(fragment) > 0
        assert "Quick" in fragment

    def test_standard_loads(self):
        from src.agents.prompts import load_depth_fragment

        fragment = load_depth_fragment("standard")
        assert len(fragment) > 0
        assert "Standard" in fragment

    def test_deep_loads(self):
        from src.agents.prompts import load_depth_fragment

        fragment = load_depth_fragment("deep")
        assert len(fragment) > 0
        assert "Deep" in fragment

    def test_deep_mentions_charts(self):
        from src.agents.prompts import load_depth_fragment

        fragment = load_depth_fragment("deep")
        assert "/workspace/output/" in fragment

    def test_quick_no_charts(self):
        from src.agents.prompts import load_depth_fragment

        fragment = load_depth_fragment("quick")
        assert "No charts" in fragment

    def test_unknown_depth_returns_empty(self):
        from src.agents.prompts import load_depth_fragment

        fragment = load_depth_fragment("ultra")
        assert fragment == ""


# =============================================================================
# T3329: load_strategy_fragment
# =============================================================================


class TestLoadStrategyFragment:
    """Test strategy prompt fragment loading."""

    def test_parallel_returns_empty(self):
        from src.agents.prompts import load_strategy_fragment

        fragment = load_strategy_fragment("parallel")
        assert fragment == ""

    def test_teamwork_loads(self):
        from src.agents.prompts import load_strategy_fragment

        fragment = load_strategy_fragment("teamwork", prior_findings="None yet")
        assert len(fragment) > 0
        assert "Teamwork" in fragment

    def test_teamwork_formats_prior_findings(self):
        from src.agents.prompts import load_strategy_fragment

        fragment = load_strategy_fragment(
            "teamwork", prior_findings="Energy: high consumption overnight"
        )
        assert "Energy: high consumption overnight" in fragment

    def test_teamwork_mentions_cross_references(self):
        from src.agents.prompts import load_strategy_fragment

        fragment = load_strategy_fragment("teamwork", prior_findings="n/a")
        assert "cross_references" in fragment

    def test_unknown_strategy_returns_empty(self):
        from src.agents.prompts import load_strategy_fragment

        fragment = load_strategy_fragment("unknown_strategy")
        assert fragment == ""
