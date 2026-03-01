"""Resilient LLM wrapper with retry and failover logic."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from pydantic import PrivateAttr

from src.llm.circuit_breaker import MAX_RETRIES, RETRY_DELAYS, _get_circuit_breaker
from src.llm.usage import _log_usage_async, _publish_llm_activity

logger = logging.getLogger(__name__)


class ResilientLLM(BaseChatModel):
    """BaseChatModel wrapper that adds retry and failover logic."""

    primary_llm: BaseChatModel
    provider: str
    fallback_llm: BaseChatModel | None = None
    fallback_provider: str | None = None
    _circuit_breaker: Any = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        """Initialize non-model runtime state after Pydantic validation."""
        self._circuit_breaker = _get_circuit_breaker(self.provider)

    @property
    def _llm_type(self) -> str:
        return "resilient"

    def _get_model_name(self) -> str:
        return getattr(
            self.primary_llm, "model_name", getattr(self.primary_llm, "model", "unknown")
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Sync generate with retry and failover. Use ainvoke() from async context."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "ResilientLLM.invoke() cannot be called from within an async context; "
                "use await llm.ainvoke() instead."
            )
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            if not self._circuit_breaker.can_attempt():
                logger.info("Circuit breaker open for %s, skipping attempt", self.provider)
                break
            try:
                result = self.primary_llm._generate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                self._circuit_breaker.record_success()
                return result
            except Exception as e:
                last_error = e
                self._circuit_breaker.record_failure()
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt + 1,
                        MAX_RETRIES,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error("All retries exhausted for %s: %s", self.provider, e)
        if self.fallback_llm:
            logger.info("Attempting fallback provider: %s", self.fallback_provider)
            fallback_cb = _get_circuit_breaker(self.fallback_provider or "fallback")
            if fallback_cb.can_attempt():
                try:
                    result = self.fallback_llm._generate(
                        messages, stop=stop, run_manager=run_manager, **kwargs
                    )
                    fallback_cb.record_success()
                    return result
                except Exception as e:
                    fallback_cb.record_failure()
                    logger.error("Fallback provider also failed: %s", e)
                    if last_error:
                        raise last_error from e
                    raise
            if last_error:
                raise last_error
            raise Exception(f"Both primary ({self.provider}) and fallback providers failed")
        if last_error:
            raise last_error
        raise Exception(f"LLM provider {self.provider} failed after retries")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate with retry, failover, and usage logging."""
        start_ms = time.perf_counter()
        _publish_llm_activity("start", self._get_model_name())
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            if not self._circuit_breaker.can_attempt():
                logger.info("Circuit breaker open for %s, skipping attempt", self.provider)
                break
            try:
                result = await self.primary_llm._agenerate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                self._circuit_breaker.record_success()
                latency_ms = int((time.perf_counter() - start_ms) * 1000)
                if result.generations:
                    _log_usage_async(
                        result.generations[0].message,
                        self.provider,
                        self._get_model_name(),
                        latency_ms,
                    )
                _publish_llm_activity("end", self._get_model_name(), latency_ms=latency_ms)
                return result
            except Exception as e:
                last_error = e
                self._circuit_breaker.record_failure()
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt + 1,
                        MAX_RETRIES,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("All retries exhausted for %s: %s", self.provider, e)
        if self.fallback_llm:
            logger.info("Attempting fallback provider: %s", self.fallback_provider)
            fallback_cb = _get_circuit_breaker(self.fallback_provider or "fallback")
            if not fallback_cb.can_attempt():
                if last_error:
                    raise last_error
                raise Exception(f"Both primary ({self.provider}) and fallback providers failed")
            try:
                result = await self.fallback_llm._agenerate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
                fallback_cb.record_success()
                latency_ms = int((time.perf_counter() - start_ms) * 1000)
                if result.generations:
                    _log_usage_async(
                        result.generations[0].message,
                        self.fallback_provider or "fallback",
                        self._get_model_name(),
                        latency_ms,
                    )
                _publish_llm_activity("end", self._get_model_name(), latency_ms=latency_ms)
                return result
            except Exception as e:
                fallback_cb.record_failure()
                logger.error("Fallback provider also failed: %s", e)
                if last_error:
                    raise last_error from e
                raise
        if last_error:
            raise last_error
        raise Exception(f"LLM provider {self.provider} failed after retries")

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """Stream with retry on initial connection failure. Mid-stream errors propagate."""
        model_name = self._get_model_name()
        start_ms = time.perf_counter()
        _publish_llm_activity("start", model_name)
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            if not self._circuit_breaker.can_attempt():
                logger.info("Circuit breaker open for %s, skipping stream attempt", self.provider)
                break
            try:
                last_chunk = None
                async for chunk in self.primary_llm._astream(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                ):
                    last_chunk = chunk
                    yield chunk
                self._circuit_breaker.record_success()
                latency_ms = int((time.perf_counter() - start_ms) * 1000)
                if last_chunk is not None:
                    msg = getattr(last_chunk, "message", last_chunk)
                    _log_usage_async(msg, self.provider, model_name, latency_ms)
                _publish_llm_activity("end", model_name, latency_ms=latency_ms)
                return
            except Exception as e:
                last_error = e
                self._circuit_breaker.record_failure()
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        "LLM stream failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt + 1,
                        MAX_RETRIES,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("All stream retries exhausted for %s: %s", self.provider, e)
        if self.fallback_llm:
            logger.info("Attempting stream fallback: %s", self.fallback_provider)
            fallback_cb = _get_circuit_breaker(self.fallback_provider or "fallback")
            if fallback_cb.can_attempt():
                try:
                    last_chunk = None
                    async for chunk in self.fallback_llm._astream(
                        messages, stop=stop, run_manager=run_manager, **kwargs
                    ):
                        last_chunk = chunk
                        yield chunk
                    fallback_cb.record_success()
                    latency_ms = int((time.perf_counter() - start_ms) * 1000)
                    if last_chunk is not None:
                        msg = getattr(last_chunk, "message", last_chunk)
                        _log_usage_async(
                            msg,
                            self.fallback_provider or "fallback",
                            model_name,
                            latency_ms,
                        )
                    _publish_llm_activity("end", model_name, latency_ms=latency_ms)
                    return
                except Exception as e:
                    fallback_cb.record_failure()
                    logger.error("Fallback stream also failed: %s", e)
                    if last_error:
                        raise last_error from e
                    raise
        if last_error:
            raise last_error
        raise Exception(f"LLM stream provider {self.provider} failed after retries")

    def __getattr__(self, name: str) -> Any:
        """Delegate attributes not on this wrapper to primary LLM (e.g. model_name, bind_tools)."""
        private = self.__pydantic_private__
        if private and name in private:
            return private[name]
        return getattr(self.primary_llm, name)
