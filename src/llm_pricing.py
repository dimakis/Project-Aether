"""LLM model pricing for cost estimation.

Maps model names to per-token costs (USD per 1M tokens).
Prices are approximate and should be periodically updated.

Configurable via LLM_PRICING_FILE env var pointing to a JSON override file.
"""

import json
import logging
import os
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class ModelPricing(TypedDict):
    """Pricing for a single model."""

    input_per_1m: float  # USD per 1M input tokens
    output_per_1m: float  # USD per 1M output tokens


# Default pricing table (USD per 1M tokens, as of early 2026)
# Sources: provider pricing pages
DEFAULT_PRICING: dict[str, ModelPricing] = {
    # OpenAI — GPT-5
    "gpt-5": {"input_per_1m": 2.50, "output_per_1m": 10.00},
    "gpt-5-mini": {"input_per_1m": 0.30, "output_per_1m": 1.25},
    # OpenAI — GPT-4.x / GPT-4o
    "gpt-4o": {"input_per_1m": 2.50, "output_per_1m": 10.00},
    "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "gpt-4-turbo": {"input_per_1m": 10.00, "output_per_1m": 30.00},
    "gpt-4": {"input_per_1m": 30.00, "output_per_1m": 60.00},
    "gpt-4.5-preview": {"input_per_1m": 75.00, "output_per_1m": 150.00},
    "gpt-4.1": {"input_per_1m": 2.00, "output_per_1m": 8.00},
    "gpt-4.1-mini": {"input_per_1m": 0.40, "output_per_1m": 1.60},
    "gpt-4.1-nano": {"input_per_1m": 0.10, "output_per_1m": 0.40},
    # OpenAI — o-series reasoning
    "o1": {"input_per_1m": 15.00, "output_per_1m": 60.00},
    "o1-mini": {"input_per_1m": 3.00, "output_per_1m": 12.00},
    "o1-preview": {"input_per_1m": 15.00, "output_per_1m": 60.00},
    "o3-mini": {"input_per_1m": 1.10, "output_per_1m": 4.40},
    # OpenAI — Legacy
    "gpt-3.5-turbo": {"input_per_1m": 0.50, "output_per_1m": 1.50},
    # Anthropic (via OpenRouter or direct)
    "anthropic/claude-sonnet-4": {"input_per_1m": 3.00, "output_per_1m": 15.00},
    "anthropic/claude-3.5-sonnet": {"input_per_1m": 3.00, "output_per_1m": 15.00},
    "anthropic/claude-3-haiku": {"input_per_1m": 0.25, "output_per_1m": 1.25},
    "anthropic/claude-3-opus": {"input_per_1m": 15.00, "output_per_1m": 75.00},
    "claude-sonnet-4": {"input_per_1m": 3.00, "output_per_1m": 15.00},
    "claude-3-5-sonnet-20241022": {"input_per_1m": 3.00, "output_per_1m": 15.00},
    # Google Gemini
    "gemini-2.0-flash": {"input_per_1m": 0.10, "output_per_1m": 0.40},
    "gemini-2.0-flash-lite": {"input_per_1m": 0.02, "output_per_1m": 0.10},
    "gemini-1.5-flash": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    "gemini-1.5-pro": {"input_per_1m": 1.25, "output_per_1m": 5.00},
    # Meta (via OpenRouter/Together)
    "meta-llama/llama-3-70b-instruct": {"input_per_1m": 0.59, "output_per_1m": 0.79},
    "meta-llama/llama-3-8b-instruct": {"input_per_1m": 0.06, "output_per_1m": 0.06},
    # DeepSeek
    "deepseek/deepseek-chat": {"input_per_1m": 0.14, "output_per_1m": 0.28},
    "deepseek/deepseek-r1": {"input_per_1m": 0.55, "output_per_1m": 2.19},
    # Mistral
    "mistralai/mistral-large": {"input_per_1m": 2.00, "output_per_1m": 6.00},
    "mistralai/mistral-small": {"input_per_1m": 0.10, "output_per_1m": 0.30},
}

# Cached pricing table (loaded once)
_pricing_cache: dict[str, ModelPricing] | None = None


def _load_pricing() -> dict[str, ModelPricing]:
    """Load pricing table, merging defaults with optional JSON override."""
    global _pricing_cache
    if _pricing_cache is not None:
        return _pricing_cache

    pricing = dict(DEFAULT_PRICING)

    # Check for override file
    override_path = os.environ.get("LLM_PRICING_FILE")
    if override_path:
        path = Path(override_path)
        if path.is_file():
            try:
                with path.open() as f:
                    overrides = json.load(f)
                pricing.update(overrides)
                logger.info(f"Loaded {len(overrides)} pricing overrides from {override_path}")
            except Exception as e:
                logger.warning(f"Failed to load pricing overrides: {e}")

    _pricing_cache = pricing
    return pricing


def get_model_pricing(model: str) -> ModelPricing | None:
    """Get pricing for a specific model.

    Args:
        model: Model name (e.g. "gpt-4o", "anthropic/claude-sonnet-4")

    Returns:
        ModelPricing dict with input_per_1m and output_per_1m, or None if unknown
    """
    pricing = _load_pricing()
    return pricing.get(model)


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    """Calculate estimated cost for an LLM call.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD, or None if model pricing is unknown
    """
    pricing = get_model_pricing(model)
    if pricing is None:
        return None

    input_cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
    return round(input_cost + output_cost, 6)


def list_known_models() -> list[str]:
    """List all models with known pricing."""
    return sorted(_load_pricing().keys())
