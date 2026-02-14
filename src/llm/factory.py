"""LLM provider factory.

Supports multiple LLM backends:
- OpenRouter (default): Access to many models via unified API
- OpenAI: Direct OpenAI API access
- Google: Google Gemini via langchain-google-genai
- Any OpenAI-compatible API: Set LLM_BASE_URL

Environment variables:
- LLM_PROVIDER: openrouter (default), openai, google
- LLM_MODEL: Model name (e.g., anthropic/claude-sonnet-4, gpt-4o, gemini-2.0-flash)
- LLM_API_KEY: API key for the provider
- LLM_BASE_URL: Custom base URL for OpenAI-compatible APIs
- LLM_TEMPERATURE: Generation temperature (0.0-2.0)
"""

from functools import lru_cache
from typing import Any

from langchain_core.language_models import BaseChatModel

from src.llm.resilient import ResilientLLM
from src.settings import get_settings

# Provider base URLs
PROVIDER_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "together": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",
}


def get_llm(
    temperature: float | None = None,
    model: str | None = None,
    provider: str | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Get LLM instance based on configured provider.

    Args:
        temperature: Override default temperature
        model: Override default model name (can include provider prefix like "ollama/llama3")
        provider: Override default provider
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured LLM instance

    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    settings = get_settings()
    model_name = model or settings.llm_model
    temp = temperature if temperature is not None else settings.llm_temperature

    # Auto-detect provider from model prefix (e.g., "ollama/llama3" -> provider="ollama", model="llama3")
    detected_provider = None
    if model_name and "/" in model_name:
        prefix, suffix = model_name.split("/", 1)
        # Known provider prefixes
        if (
            prefix
            in (
                "ollama",
                "openai",
                "anthropic",
                "google",
                "meta-llama",
                "mistralai",
                "deepseek",
            )
            and prefix == "ollama"
        ):
            detected_provider = "ollama"
            model_name = suffix  # Ollama uses just the model name
            # For OpenRouter models, keep the full path
            # (e.g., "anthropic/claude-sonnet-4" stays as-is)

    provider = provider or detected_provider or settings.llm_provider

    # Create primary LLM instance
    primary_llm = _create_llm_instance(
        provider=provider,
        model=model_name,
        temperature=temp,
        **kwargs,
    )

    # Check for fallback configuration
    fallback_provider = settings.llm_fallback_provider
    fallback_model = settings.llm_fallback_model

    if fallback_provider and fallback_model:
        # Create fallback LLM instance
        fallback_llm = _create_llm_instance(
            provider=fallback_provider,
            model=fallback_model,
            temperature=temp,
            **kwargs,
        )

        # Wrap with resilience
        return ResilientLLM(  # type: ignore[return-value]
            primary_llm=primary_llm,
            provider=provider,
            fallback_llm=fallback_llm,
            fallback_provider=fallback_provider,
        )

    # No fallback, wrap primary with resilience
    return ResilientLLM(  # type: ignore[return-value]
        primary_llm=primary_llm,
        provider=provider,
    )


def _create_llm_instance(
    provider: str,
    model: str,
    temperature: float,
    **kwargs: Any,
) -> BaseChatModel:
    """Create an LLM instance (internal helper for fallback creation).

    Args:
        provider: Provider name
        model: Model name
        temperature: Temperature setting
        **kwargs: Additional arguments

    Returns:
        LLM instance
    """
    settings = get_settings()

    # Google Gemini uses separate SDK
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = settings.google_api_key.get_secret_value()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required when using Google provider")

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
            **kwargs,
        )

    # OpenAI-compatible providers
    from langchain_openai import ChatOpenAI

    api_key = settings.llm_api_key.get_secret_value()
    if not api_key and provider != "ollama":
        raise ValueError(f"LLM_API_KEY is required when using {provider} provider")

    # Determine base URL
    base_url = settings.llm_base_url
    if base_url is None:
        base_url = PROVIDER_BASE_URLS.get(provider)
        if base_url is None and provider not in ["openai"]:
            raise ValueError(
                f"Unknown provider '{provider}'. Set LLM_BASE_URL for custom providers."
            )

    # Build kwargs
    llm_kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        **kwargs,
    }

    if api_key:
        llm_kwargs["api_key"] = api_key
    elif provider == "ollama":
        llm_kwargs["api_key"] = "ollama"

    if base_url:
        llm_kwargs["base_url"] = base_url

    # Add headers for OpenRouter
    if provider == "openrouter":
        llm_kwargs.setdefault("default_headers", {})
        llm_kwargs["default_headers"]["HTTP-Referer"] = "https://github.com/project-aether"
        llm_kwargs["default_headers"]["X-Title"] = "Project Aether"

    return ChatOpenAI(**llm_kwargs)


@lru_cache
def get_default_llm() -> BaseChatModel:
    """Get cached default LLM instance.

    Returns:
        Default LLM based on settings
    """
    return get_llm()


def list_supported_providers() -> dict[str, str]:
    """List supported LLM providers and their base URLs.

    Returns:
        Dict of provider name to base URL
    """
    return {
        **PROVIDER_BASE_URLS,
        "google": "(uses Google SDK)",
    }
