"""LLM provider factory and resilient wrapper.

Re-exports public API and internal symbols used by tests.

Uses lazy imports to defer LLM client initialization.
"""

from typing import TYPE_CHECKING, Any

_EXPORTS = {
    # circuit_breaker
    "MAX_RETRIES": "src.llm.circuit_breaker",
    "RETRY_DELAYS": "src.llm.circuit_breaker",
    "CircuitBreaker": "src.llm.circuit_breaker",
    "_circuit_breakers": "src.llm.circuit_breaker",
    "_get_circuit_breaker": "src.llm.circuit_breaker",
    # factory
    "PROVIDER_BASE_URLS": "src.llm.factory",
    "get_default_llm": "src.llm.factory",
    "get_llm": "src.llm.factory",
    "list_supported_providers": "src.llm.factory",
    # model_tiers
    "ModelTier": "src.llm.model_tiers",
    "get_default_model_for_tier": "src.llm.model_tiers",
    "get_model_tier": "src.llm.model_tiers",
    "resolve_model_for_tier": "src.llm.model_tiers",
    # resilient
    "ResilientLLM": "src.llm.resilient",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import attributes on first access."""
    if name in _cache:
        return _cache[name]

    if name in _EXPORTS:
        from importlib import import_module

        module = import_module(_EXPORTS[name])
        attr = getattr(module, name)
        _cache[name] = attr
        return attr

    raise AttributeError(f"module 'src.llm' has no attribute {name!r}")


def __dir__() -> list[str]:
    """List all available attributes."""
    return list(_EXPORTS.keys())


if TYPE_CHECKING:
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
