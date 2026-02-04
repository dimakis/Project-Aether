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
from typing import Any

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
        # OpenAI
        ("openai/gpt-4o", "GPT-4o - Latest flagship model"),
        ("openai/gpt-4o-mini", "GPT-4o Mini - Fast and efficient"),
        ("openai/gpt-4-turbo", "GPT-4 Turbo - High capability"),
        # Anthropic
        ("anthropic/claude-sonnet-4", "Claude Sonnet 4 - Latest balanced model"),
        ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet - Previous best"),
        ("anthropic/claude-3-haiku", "Claude 3 Haiku - Fast and cheap"),
        ("anthropic/claude-3-opus", "Claude 3 Opus - Most capable"),
        # Meta
        ("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B - Open source champion"),
        ("meta-llama/llama-3.1-8b-instruct", "Llama 3.1 8B - Fast open source"),
        # Google
        ("google/gemini-2.0-flash-001", "Gemini 2.0 Flash - Fast multimodal"),
        ("google/gemini-pro-1.5", "Gemini Pro 1.5 - Long context"),
        # Mistral
        ("mistralai/mistral-large", "Mistral Large - High capability"),
        ("mistralai/mixtral-8x7b-instruct", "Mixtral 8x7B - MoE model"),
        # DeepSeek
        ("deepseek/deepseek-chat", "DeepSeek Chat - Reasoning specialist"),
    ]

    OPENAI_MODELS = [
        ("gpt-4o", "GPT-4o - Latest flagship model"),
        ("gpt-4o-mini", "GPT-4o Mini - Fast and efficient"),
        ("gpt-4-turbo", "GPT-4 Turbo - High capability"),
        ("gpt-4", "GPT-4 - Original"),
        ("gpt-3.5-turbo", "GPT-3.5 Turbo - Fast legacy model"),
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
