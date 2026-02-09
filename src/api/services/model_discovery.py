"""Dynamic model discovery for LLM providers.

Discovers available models from:
- Ollama (local models)
- OpenRouter (when configured)
- OpenAI (when configured)
- Google (hardcoded list - no discovery API)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from src.settings import get_settings

logger = logging.getLogger(__name__)

# Cache duration in seconds
CACHE_TTL = 300  # 5 minutes


@dataclass
class DiscoveredModel:
    """A discovered model from a provider."""

    id: str
    provider: str
    name: str | None = None
    description: str | None = None
    context_length: int | None = None


@dataclass
class ModelCache:
    """Cache for discovered models."""

    models: list[DiscoveredModel] = field(default_factory=list)
    last_updated: float = 0

    def is_valid(self) -> bool:
        """Check if cache is still valid."""
        return time.time() - self.last_updated < CACHE_TTL


class ModelDiscovery:
    """Discovers available models from configured providers."""

    # Curated model lists for providers without discovery APIs
    OPENROUTER_MODELS = [
        # OpenAI (via OpenRouter)
        ("openai/gpt-5", "GPT-5 - Next generation flagship"),
        ("openai/gpt-4.5-preview", "GPT-4.5 Preview - Latest preview"),
        ("openai/gpt-4o", "GPT-4o - Flagship multimodal"),
        ("openai/gpt-4o-mini", "GPT-4o Mini - Fast and efficient"),
        ("openai/o1", "o1 - Advanced reasoning"),
        ("openai/o1-mini", "o1 Mini - Fast reasoning"),
        ("openai/o3-mini", "o3 Mini - Latest reasoning"),
        # Anthropic
        ("anthropic/claude-sonnet-4", "Claude Sonnet 4 - Latest balanced"),
        ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet - Excellent balance"),
        ("anthropic/claude-3-haiku", "Claude 3 Haiku - Fast and cheap"),
        ("anthropic/claude-3-opus", "Claude 3 Opus - Most capable"),
        # Meta Llama
        ("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B - OSS champion"),
        ("meta-llama/llama-3.2-90b-vision", "Llama 3.2 90B Vision - Multimodal"),
        ("meta-llama/llama-3.1-8b-instruct", "Llama 3.1 8B - Fast OSS"),
        # Google
        ("google/gemini-2.0-flash", "Gemini 2.0 Flash - Fast multimodal"),
        ("google/gemini-1.5-pro", "Gemini 1.5 Pro - Long context"),
        # Mistral
        ("mistralai/mistral-large", "Mistral Large - High capability"),
        ("mistralai/mistral-small", "Mistral Small - Efficient"),
        # DeepSeek
        ("deepseek/deepseek-r1", "DeepSeek R1 - Advanced reasoning"),
        ("deepseek/deepseek-chat", "DeepSeek Chat - General"),
        # Qwen
        ("qwen/qwen-2.5-72b-instruct", "Qwen 2.5 72B - Alibaba flagship"),
    ]

    OPENAI_MODELS = [
        # GPT-5 family
        ("gpt-5", "GPT-5 - Next generation flagship"),
        ("gpt-5-mini", "GPT-5 Mini - Efficient next-gen"),
        # GPT-4.5 family
        ("gpt-4.5-preview", "GPT-4.5 Preview - Latest preview"),
        # GPT-4.1 family
        ("gpt-4.1", "GPT-4.1 - Latest balanced"),
        ("gpt-4.1-mini", "GPT-4.1 Mini - Fast and efficient"),
        ("gpt-4.1-nano", "GPT-4.1 Nano - Ultra-efficient"),
        # GPT-4o family
        ("gpt-4o", "GPT-4o - Flagship multimodal"),
        ("gpt-4o-mini", "GPT-4o Mini - Fast and efficient"),
        # o-series reasoning
        ("o1", "o1 - Advanced reasoning"),
        ("o1-mini", "o1 Mini - Fast reasoning"),
        ("o1-preview", "o1 Preview - Reasoning preview"),
        ("o3-mini", "o3 Mini - Latest reasoning"),
        # GPT-4 family
        ("gpt-4-turbo", "GPT-4 Turbo - High capability"),
        ("gpt-4", "GPT-4 - Original"),
        # Legacy
        ("gpt-3.5-turbo", "GPT-3.5 Turbo - Fast legacy"),
    ]

    GOOGLE_MODELS = [
        ("gemini-2.0-flash", "Gemini 2.0 Flash - Fast multimodal"),
        ("gemini-1.5-pro", "Gemini 1.5 Pro - Long context"),
        ("gemini-1.5-flash", "Gemini 1.5 Flash - Fast"),
    ]

    def __init__(self) -> None:
        """Initialize model discovery."""
        self._cache = ModelCache()
        self._lock = asyncio.Lock()

    async def discover_all(self, force_refresh: bool = False) -> list[DiscoveredModel]:
        """Discover all available models from all providers.

        Args:
            force_refresh: Force refresh even if cache is valid

        Returns:
            List of discovered models
        """
        async with self._lock:
            if not force_refresh and self._cache.is_valid():
                return self._cache.models

            models: list[DiscoveredModel] = []
            settings = get_settings()
            provider = settings.llm_provider

            # Always try Ollama (it's local, fast to check)
            ollama_models = await self._discover_ollama()
            models.extend(ollama_models)

            # Add models based on configured provider
            if provider == "openrouter":
                models.extend(self._get_openrouter_models())
            elif provider == "google":
                models.extend(self._get_google_models())
            elif provider == "openai":
                models.extend(self._get_openai_models())
            else:
                # Unknown provider - add OpenAI as fallback
                models.extend(self._get_openai_models())

            # Update cache
            self._cache.models = models
            self._cache.last_updated = time.time()

            logger.info(
                f"Discovered {len(models)} models: "
                f"{len(ollama_models)} local, "
                f"{len(models) - len(ollama_models)} from {provider}"
            )

            return models

    async def _discover_ollama(self) -> list[DiscoveredModel]:
        """Discover local Ollama models.

        Returns:
            List of Ollama models, or empty list if Ollama is not running
        """
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for model in data.get("models", []):
                    model_name = model.get("name", "")
                    # Extract base name (without tag)
                    base_name = model_name.split(":")[0] if ":" in model_name else model_name

                    models.append(
                        DiscoveredModel(
                            id=f"ollama/{model_name}",
                            provider="ollama",
                            name=base_name,
                            description=f"Local Ollama model - {model.get('size', 'unknown size')}",
                        )
                    )

                logger.debug(f"Discovered {len(models)} Ollama models")
                return models

        except httpx.ConnectError:
            logger.debug("Ollama not running or not reachable")
            return []
        except Exception as e:
            logger.warning(f"Failed to discover Ollama models: {e}")
            return []

    def _get_openrouter_models(self) -> list[DiscoveredModel]:
        """Get curated OpenRouter model list."""
        return [
            DiscoveredModel(
                id=model_id,
                provider="openrouter",
                description=description,
            )
            for model_id, description in self.OPENROUTER_MODELS
        ]

    def _get_openai_models(self) -> list[DiscoveredModel]:
        """Get curated OpenAI model list."""
        return [
            DiscoveredModel(
                id=model_id,
                provider="openai",
                description=description,
            )
            for model_id, description in self.OPENAI_MODELS
        ]

    def _get_google_models(self) -> list[DiscoveredModel]:
        """Get curated Google model list."""
        return [
            DiscoveredModel(
                id=model_id,
                provider="google",
                description=description,
            )
            for model_id, description in self.GOOGLE_MODELS
        ]


# Global instance for caching
_discovery_instance: ModelDiscovery | None = None


def get_model_discovery() -> ModelDiscovery:
    """Get the model discovery singleton."""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = ModelDiscovery()
    return _discovery_instance
