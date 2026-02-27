"""Model tier classification for dynamic model selection.

Classifies known LLM models into capability tiers so the Orchestrator
can auto-select an appropriate model based on task complexity.

Tiers:
    fast     -- cheap, low-latency; for classification, short answers
    standard -- balanced cost/capability; for most agent tasks
    frontier -- most capable; for complex reasoning, research synthesis
"""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

ModelTier = Literal["fast", "standard", "frontier"]

MODEL_TIER_MAP: dict[str, ModelTier] = {
    # Fast tier
    "gpt-4o-mini": "fast",
    "gpt-4.1-mini": "fast",
    "gpt-4.1-nano": "fast",
    "gpt-5-mini": "fast",
    "gpt-3.5-turbo": "fast",
    "o3-mini": "fast",
    "gemini-2.0-flash": "fast",
    "gemini-2.0-flash-lite": "fast",
    "gemini-1.5-flash": "fast",
    "anthropic/claude-3-haiku": "fast",
    # Standard tier
    "gpt-4o": "standard",
    "gpt-4.1": "standard",
    "gpt-4-turbo": "standard",
    "anthropic/claude-sonnet-4": "standard",
    "anthropic/claude-3.5-sonnet": "standard",
    "claude-sonnet-4": "standard",
    "claude-3-5-sonnet-20241022": "standard",
    "gemini-1.5-pro": "standard",
    "o1-mini": "standard",
    # Frontier tier
    "gpt-5": "frontier",
    "gpt-4.5-preview": "frontier",
    "gpt-4": "frontier",
    "o1": "frontier",
    "o1-preview": "frontier",
    "anthropic/claude-3-opus": "frontier",
}

_DEFAULT_TIER_MODEL: dict[ModelTier, str] = {
    "fast": "gpt-4o-mini",
    "standard": "gpt-4o",
    "frontier": "gpt-5",
}


def get_model_tier(model_name: str) -> ModelTier:
    """Classify a model into a capability tier.

    Unknown models are treated as ``standard`` (safe middle ground).
    """
    tier = MODEL_TIER_MAP.get(model_name)
    if tier:
        return tier

    name_lower = model_name.lower()
    if any(kw in name_lower for kw in ("mini", "nano", "flash", "haiku", "lite")):
        return "fast"
    if any(kw in name_lower for kw in ("opus", "o1", "gpt-5", "gpt-4.5")):
        return "frontier"
    return "standard"


def get_default_model_for_tier(tier: ModelTier) -> str:
    """Return the default model name for a given tier."""
    return _DEFAULT_TIER_MODEL[tier]


def resolve_model_for_tier(
    requested_tier: ModelTier,
    available_models: list[str] | None = None,
) -> str:
    """Find the best available model for a requested tier.

    If ``available_models`` is provided, picks the first match in that
    tier.  Falls back to the hardcoded default otherwise.
    """
    if available_models:
        for model in available_models:
            if MODEL_TIER_MAP.get(model) == requested_tier:
                return model

    return get_default_model_for_tier(requested_tier)
