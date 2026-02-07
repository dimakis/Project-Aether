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

import asyncio
import logging
import time
from functools import lru_cache
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from src.settings import get_settings

logger = logging.getLogger(__name__)

# Retry configuration for resilient LLM calls
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff delays in seconds

# Provider base URLs
PROVIDER_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "together": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",
}


class CircuitBreaker:
    """Simple circuit breaker pattern for LLM providers.
    
    After N consecutive failures, stops trying the provider for a cooldown period.
    """
    
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            cooldown_seconds: Seconds to wait before allowing retry after circuit opens
        """
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.circuit_open = False
    
    def record_success(self) -> None:
        """Record a successful call, resetting failure count."""
        self.failure_count = 0
        self.circuit_open = False
        self.last_failure_time = None
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry after {self.cooldown_seconds}s cooldown."
            )
    
    def can_attempt(self) -> bool:
        """Check if we can attempt a call (circuit not open or cooldown expired)."""
        if not self.circuit_open:
            return True
        
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.cooldown_seconds:
            logger.info(f"Circuit breaker cooldown expired, attempting call")
            self.circuit_open = False
            self.failure_count = 0
            return True
        
        return False


# Global circuit breakers per provider
_circuit_breakers: dict[str, CircuitBreaker] = {}


def _get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create circuit breaker for a provider."""
    if provider not in _circuit_breakers:
        _circuit_breakers[provider] = CircuitBreaker()
    return _circuit_breakers[provider]


class ResilientLLM:
    """Wrapper around BaseChatModel that adds retry and failover logic."""
    
    def __init__(
        self,
        primary_llm: BaseChatModel,
        provider: str,
        fallback_llm: BaseChatModel | None = None,
        fallback_provider: str | None = None,
    ):
        """Initialize resilient LLM wrapper.
        
        Args:
            primary_llm: Primary LLM instance
            provider: Provider name for circuit breaker tracking
            fallback_llm: Optional fallback LLM instance
            fallback_provider: Optional fallback provider name
        """
        self.primary_llm = primary_llm
        self.provider = provider
        self.fallback_llm = fallback_llm
        self.fallback_provider = fallback_provider
        self._circuit_breaker = _get_circuit_breaker(provider)
    
    async def ainvoke(
        self,
        input: list[BaseMessage] | str,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Invoke LLM with retry and failover logic.
        
        Args:
            input: Input messages or string
            config: Optional configuration
            **kwargs: Additional arguments
            
        Returns:
            LLM response
            
        Raises:
            Exception: If all retries and fallback attempts fail
        """
        # Try primary provider with retries
        last_error: Exception | None = None
        
        for attempt in range(MAX_RETRIES):
            # Check circuit breaker
            if not self._circuit_breaker.can_attempt():
                logger.info(f"Circuit breaker open for {self.provider}, skipping attempt")
                break
            
            try:
                result = await self.primary_llm.ainvoke(input, config=config, **kwargs)
                self._circuit_breaker.record_success()
                return result
            except Exception as e:
                last_error = e
                self._circuit_breaker.record_failure()
                
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retries exhausted for {self.provider}: {e}")
        
        # Try fallback if available
        if self.fallback_llm:
            logger.info(f"Attempting fallback provider: {self.fallback_provider}")
            fallback_cb = _get_circuit_breaker(self.fallback_provider or "fallback")
            
            if not fallback_cb.can_attempt():
                logger.warning(f"Fallback circuit breaker also open")
                if last_error:
                    raise last_error
                raise Exception(f"Both primary ({self.provider}) and fallback providers failed")
            
            try:
                result = await self.fallback_llm.ainvoke(input, config=config, **kwargs)
                fallback_cb.record_success()
                logger.info(f"Fallback provider succeeded")
                return result
            except Exception as e:
                fallback_cb.record_failure()
                logger.error(f"Fallback provider also failed: {e}")
                if last_error:
                    raise last_error
                raise
        
        # No fallback or fallback failed
        if last_error:
            raise last_error
        raise Exception(f"LLM provider {self.provider} failed after retries")
    
    def invoke(
        self,
        input: list[BaseMessage] | str,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Synchronous invoke (delegates to async)."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.ainvoke(input, config=config, **kwargs)
        )
    
    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to primary LLM."""
        return getattr(self.primary_llm, name)


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
        if prefix in ("ollama", "openai", "anthropic", "google", "meta-llama", "mistralai", "deepseek"):
            if prefix == "ollama":
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
        return ResilientLLM(
            primary_llm=primary_llm,
            provider=provider,
            fallback_llm=fallback_llm,
            fallback_provider=fallback_provider,
        )
    
    # No fallback, wrap primary with resilience
    return ResilientLLM(
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
