"""Unit tests for model context propagation through the Data Scientist.

Tests that the Data Scientist resolves its LLM model correctly based on
the active model context vs per-agent settings vs global defaults.

TDD: T-MR05 - DS model selection with/without context.
"""

from unittest.mock import MagicMock, patch

from src.agents.model_context import clear_model_context, model_context


class TestDataScientistModelResolution:
    """Tests for DataScientistAgent.llm model resolution."""

    def _make_agent(self, ha_client=None):
        """Create a DataScientistAgent with mock HA."""
        from src.agents.data_scientist import DataScientistAgent

        return DataScientistAgent(ha_client=ha_client or MagicMock())

    @patch("src.agents.data_scientist.agent.get_llm")
    @patch("src.agents.data_scientist.agent.get_settings")
    def test_no_context_no_agent_setting_uses_default(
        self,
        mock_settings,
        mock_get_llm,
    ):
        """With no context and no per-agent setting, uses global default."""
        clear_model_context()

        settings = MagicMock()
        settings.data_scientist_model = None
        settings.data_scientist_temperature = None
        mock_settings.return_value = settings

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        agent = self._make_agent()
        llm = agent.llm

        # Should call get_llm with None (falls to global default)
        mock_get_llm.assert_called_once_with(model=None, temperature=None)
        assert llm == mock_llm

    @patch("src.agents.data_scientist.agent.get_llm")
    @patch("src.agents.data_scientist.agent.get_settings")
    def test_agent_setting_used_without_context(
        self,
        mock_settings,
        mock_get_llm,
    ):
        """Per-agent setting should be used when no model context is active."""
        clear_model_context()

        settings = MagicMock()
        settings.data_scientist_model = "gpt-4o-mini"
        settings.data_scientist_temperature = 0.3
        mock_settings.return_value = settings

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        agent = self._make_agent()
        _ = agent.llm  # trigger lazy LLM init

        mock_get_llm.assert_called_once_with(model="gpt-4o-mini", temperature=0.3)

    @patch("src.agents.data_scientist.agent.get_llm")
    @patch("src.agents.data_scientist.agent.get_settings")
    def test_context_overrides_agent_setting(
        self,
        mock_settings,
        mock_get_llm,
    ):
        """Active model context should override per-agent settings."""
        settings = MagicMock()
        settings.data_scientist_model = "gpt-4o-mini"
        settings.data_scientist_temperature = 0.3
        mock_settings.return_value = settings

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        agent = self._make_agent()

        with model_context(
            model_name="anthropic/claude-sonnet-4",
            temperature=0.8,
        ):
            _ = agent.llm  # trigger LLM init inside context

        # Should use the context model, not the agent setting
        mock_get_llm.assert_called_with(
            model="anthropic/claude-sonnet-4",
            temperature=0.8,
        )

    @patch("src.agents.data_scientist.agent.get_llm")
    @patch("src.agents.data_scientist.agent.get_settings")
    def test_cached_llm_without_context(
        self,
        mock_settings,
        mock_get_llm,
    ):
        """LLM should be cached when no model context is active."""
        clear_model_context()

        settings = MagicMock()
        settings.data_scientist_model = None
        settings.data_scientist_temperature = None
        mock_settings.return_value = settings

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        agent = self._make_agent()

        # Access llm twice
        llm1 = agent.llm
        llm2 = agent.llm

        # get_llm should only be called once (cached)
        assert mock_get_llm.call_count == 1
        assert llm1 is llm2

    @patch("src.agents.data_scientist.agent.get_llm")
    @patch("src.agents.data_scientist.agent.get_settings")
    def test_not_cached_with_context(
        self,
        mock_settings,
        mock_get_llm,
    ):
        """LLM should NOT be cached when model context is active."""
        settings = MagicMock()
        settings.data_scientist_model = None
        settings.data_scientist_temperature = None
        mock_settings.return_value = settings

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        agent = self._make_agent()

        with model_context(model_name="model-a"):
            _ = agent.llm
        with model_context(model_name="model-b"):
            _ = agent.llm

        # get_llm should be called twice (not cached)
        assert mock_get_llm.call_count == 2

    @patch("src.agents.data_scientist.agent.get_llm")
    @patch("src.agents.data_scientist.agent.get_settings")
    def test_different_contexts_get_different_models(
        self,
        mock_settings,
        mock_get_llm,
    ):
        """Different model contexts should produce different get_llm calls."""
        settings = MagicMock()
        settings.data_scientist_model = None
        settings.data_scientist_temperature = None
        mock_settings.return_value = settings

        agent = self._make_agent()

        with model_context(model_name="model-a", temperature=0.5):
            _ = agent.llm
        with model_context(model_name="model-b", temperature=0.9):
            _ = agent.llm

        calls = mock_get_llm.call_args_list
        assert calls[0].kwargs == {"model": "model-a", "temperature": 0.5}
        assert calls[1].kwargs == {"model": "model-b", "temperature": 0.9}
