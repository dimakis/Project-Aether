"""Resilient LLM wrapper with retry and failover logic."""

import asyncio
import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

from src.llm.circuit_breaker import MAX_RETRIES, RETRY_DELAYS, _get_circuit_breaker
from src.llm.usage import _log_usage_async, _publish_llm_activity

logger = logging.getLogger(__name__)


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
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Any:
        """Invoke LLM with retry and failover logic.

        After a successful call, logs token usage to the LLM usage tracker
        (fire-and-forget, non-blocking).

        Args:
            input: Input messages or string
            config: Optional configuration
            **kwargs: Additional arguments

        Returns:
            LLM response

        Raises:
            Exception: If all retries and fallback attempts fail
        """
        import time as _time

        start_ms = _time.perf_counter()
        _publish_llm_activity("start", self._get_model_name())

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
                latency_ms = int((_time.perf_counter() - start_ms) * 1000)
                _log_usage_async(result, self.provider, self._get_model_name(), latency_ms)
                _publish_llm_activity("end", self._get_model_name(), latency_ms=latency_ms)
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
                logger.warning("Fallback circuit breaker also open")
                if last_error:
                    raise last_error
                raise Exception(f"Both primary ({self.provider}) and fallback providers failed")

            try:
                result = await self.fallback_llm.ainvoke(input, config=config, **kwargs)
                fallback_cb.record_success()
                logger.info("Fallback provider succeeded")
                return result
            except Exception as e:
                fallback_cb.record_failure()
                logger.error(f"Fallback provider also failed: {e}")
                if last_error:
                    raise last_error from e
                raise

        # No fallback or fallback failed
        if last_error:
            raise last_error
        raise Exception(f"LLM provider {self.provider} failed after retries")

    def invoke(
        self,
        input: list[BaseMessage] | str,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Any:
        """Synchronous invoke (delegates to async)."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.ainvoke(input, config=config, **kwargs))

    async def astream(
        self,
        input: list[BaseMessage] | str,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Any:
        """Stream LLM output with retry on initial connection failure.

        Retries apply to the initial stream acquisition (connection
        errors, auth failures, etc.).  Once streaming has started,
        mid-stream errors propagate to the caller.

        Falls back to the secondary provider when primary retries are
        exhausted, mirroring the ainvoke failover logic.
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            if not self._circuit_breaker.can_attempt():
                logger.info("Circuit breaker open for %s, skipping stream attempt", self.provider)
                break

            try:
                stream = self.primary_llm.astream(input, config=config, **kwargs)
                # Yield from the stream — mid-stream errors propagate
                async for chunk in stream:
                    yield chunk
                self._circuit_breaker.record_success()
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

        # Try fallback if available
        if self.fallback_llm:
            logger.info("Attempting stream fallback: %s", self.fallback_provider)
            fallback_cb = _get_circuit_breaker(self.fallback_provider or "fallback")

            if fallback_cb.can_attempt():
                try:
                    stream = self.fallback_llm.astream(input, config=config, **kwargs)
                    async for chunk in stream:
                        yield chunk
                    fallback_cb.record_success()
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

    def _get_model_name(self) -> str:
        """Get the model name from the primary LLM."""
        return getattr(
            self.primary_llm, "model_name", getattr(self.primary_llm, "model", "unknown")
        )

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to primary LLM."""
        return getattr(self.primary_llm, name)
