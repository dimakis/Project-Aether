"""Unit tests for LLM provider factory.

Tests the flexible LLM configuration supporting multiple backends.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetLLM:
    """Tests for get_llm factory function."""

    @pytest.fixture
    def mock_settings_openrouter(self):
        """Mock settings for OpenRouter."""
        settings = MagicMock()
        settings.llm_provider = "openrouter"
        settings.llm_model = "anthropic/claude-sonnet-4"
        settings.llm_temperature = 0.7
        settings.llm_api_key.get_secret_value.return_value = "sk-or-test-key"
        settings.llm_base_url = None
        return settings

    @pytest.fixture
    def mock_settings_openai(self):
        """Mock settings for OpenAI."""
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_model = "gpt-4o"
        settings.llm_temperature = 0.5
        settings.llm_api_key.get_secret_value.return_value = "sk-openai-test"
        settings.llm_base_url = None
        return settings

    @pytest.fixture
    def mock_settings_google(self):
        """Mock settings for Google."""
        settings = MagicMock()
        settings.llm_provider = "google"
        settings.llm_model = "gemini-2.0-flash"
        settings.llm_temperature = 0.7
        settings.google_api_key.get_secret_value.return_value = "google-test-key"
        return settings

    @pytest.fixture
    def mock_settings_custom(self):
        """Mock settings for custom OpenAI-compatible API."""
        settings = MagicMock()
        settings.llm_provider = "custom"
        settings.llm_model = "llama3"
        settings.llm_temperature = 0.8
        settings.llm_api_key.get_secret_value.return_value = "custom-key"
        settings.llm_base_url = "https://custom-api.example.com/v1"
        return settings

    def test_openrouter_provider(self, mock_settings_openrouter):
        """Test OpenRouter provider configuration."""
        with patch("src.llm.get_settings", return_value=mock_settings_openrouter):
            with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
                from src.llm import get_llm

                llm = get_llm()

                MockChatOpenAI.assert_called_once()
                call_kwargs = MockChatOpenAI.call_args[1]
                assert call_kwargs["model"] == "anthropic/claude-sonnet-4"
                assert call_kwargs["temperature"] == 0.7
                assert call_kwargs["api_key"] == "sk-or-test-key"
                assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
                assert "HTTP-Referer" in call_kwargs["default_headers"]

    def test_openai_provider(self, mock_settings_openai):
        """Test OpenAI provider configuration."""
        with patch("src.llm.get_settings", return_value=mock_settings_openai):
            with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
                from src.llm import get_llm

                llm = get_llm()

                MockChatOpenAI.assert_called_once()
                call_kwargs = MockChatOpenAI.call_args[1]
                assert call_kwargs["model"] == "gpt-4o"
                assert call_kwargs["temperature"] == 0.5
                assert call_kwargs["api_key"] == "sk-openai-test"

    def test_google_provider(self, mock_settings_google):
        """Test Google Gemini provider configuration."""
        with patch("src.llm.get_settings", return_value=mock_settings_google):
            with patch("langchain_google_genai.ChatGoogleGenerativeAI") as MockGemini:
                from src.llm import get_llm

                llm = get_llm()

                MockGemini.assert_called_once()
                call_kwargs = MockGemini.call_args[1]
                assert call_kwargs["model"] == "gemini-2.0-flash"
                assert call_kwargs["temperature"] == 0.7
                assert call_kwargs["google_api_key"] == "google-test-key"

    def test_custom_base_url(self, mock_settings_custom):
        """Test custom base URL for OpenAI-compatible APIs."""
        with patch("src.llm.get_settings", return_value=mock_settings_custom):
            with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
                from src.llm import get_llm

                llm = get_llm()

                MockChatOpenAI.assert_called_once()
                call_kwargs = MockChatOpenAI.call_args[1]
                assert call_kwargs["base_url"] == "https://custom-api.example.com/v1"

    def test_temperature_override(self, mock_settings_openrouter):
        """Test temperature can be overridden."""
        with patch("src.llm.get_settings", return_value=mock_settings_openrouter):
            with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
                from src.llm import get_llm

                llm = get_llm(temperature=0.2)

                call_kwargs = MockChatOpenAI.call_args[1]
                assert call_kwargs["temperature"] == 0.2

    def test_model_override(self, mock_settings_openrouter):
        """Test model can be overridden."""
        with patch("src.llm.get_settings", return_value=mock_settings_openrouter):
            with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
                from src.llm import get_llm

                llm = get_llm(model="openai/gpt-4-turbo")

                call_kwargs = MockChatOpenAI.call_args[1]
                assert call_kwargs["model"] == "openai/gpt-4-turbo"

    def test_missing_api_key_raises_error(self):
        """Test missing API key raises ValueError."""
        settings = MagicMock()
        settings.llm_provider = "openrouter"
        settings.llm_model = "test"
        settings.llm_temperature = 0.7
        settings.llm_api_key.get_secret_value.return_value = ""
        settings.llm_base_url = None

        with patch("src.llm.get_settings", return_value=settings):
            from src.llm import get_llm

            with pytest.raises(ValueError, match="LLM_API_KEY is required"):
                get_llm()

    def test_ollama_no_api_key_required(self):
        """Test Ollama doesn't require API key."""
        settings = MagicMock()
        settings.llm_provider = "ollama"
        settings.llm_model = "llama3"
        settings.llm_temperature = 0.7
        settings.llm_api_key.get_secret_value.return_value = ""
        settings.llm_base_url = None

        with patch("src.llm.get_settings", return_value=settings):
            with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
                from src.llm import get_llm

                llm = get_llm()

                MockChatOpenAI.assert_called_once()
                call_kwargs = MockChatOpenAI.call_args[1]
                assert call_kwargs["base_url"] == "http://localhost:11434/v1"


class TestListSupportedProviders:
    """Tests for list_supported_providers function."""

    def test_returns_all_providers(self):
        """Test that all providers are listed."""
        from src.llm import list_supported_providers

        providers = list_supported_providers()

        assert "openrouter" in providers
        assert "openai" in providers
        assert "google" in providers
        assert "together" in providers
        assert "groq" in providers
        assert "ollama" in providers
