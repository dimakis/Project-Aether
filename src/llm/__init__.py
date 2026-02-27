"""LLM provider factory and resilient wrapper.

Re-exports public API and internal symbols used by tests.
"""

from src.llm.circuit_breaker import (
    MAX_RETRIES,
    RETRY_DELAYS,
    CircuitBreaker,
    _circuit_breakers,
    _get_circuit_breaker,
)
from src.llm.factory import (
    PROVIDER_BASE_URLS,
    get_default_llm,
    get_llm,
    list_supported_providers,
)
from src.llm.model_tiers import (
    ModelTier,
    get_default_model_for_tier,
    get_model_tier,
    resolve_model_for_tier,
)
from src.llm.resilient import ResilientLLM

__all__ = [
    "MAX_RETRIES",
    "PROVIDER_BASE_URLS",
    "RETRY_DELAYS",
    "CircuitBreaker",
    "ModelTier",
    "ResilientLLM",
    "_circuit_breakers",
    "_get_circuit_breaker",
    "get_default_llm",
    "get_default_model_for_tier",
    "get_llm",
    "get_model_tier",
    "list_supported_providers",
    "resolve_model_for_tier",
]
