"""Unit tests for LLM resilience features.

Tests retry logic, circuit breaker, and provider failover.
"""

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from src.llm import CircuitBreaker, ResilientLLM, _circuit_breakers, _get_circuit_breaker


def _chat_result(content: str) -> ChatResult:
    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


class StubChatModel(BaseChatModel):
    """Minimal BaseChatModel for tests. Pass agenerate_sequence: list of ChatResult or Exception."""

    model_config = {"extra": "allow"}
    agenerate_sequence: list[Any] = Field(default_factory=list)
    astream_sequence: list[Any] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "stub"

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        raise NotImplementedError("Use async tests")

    async def _agenerate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        if not self.agenerate_sequence:
            raise Exception("StubChatModel: no more responses in sequence")
        item = self.agenerate_sequence.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    async def _astream(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        if not self.astream_sequence:
            raise Exception("StubChatModel: no more streams in sequence")
        item = self.astream_sequence.pop(0)
        if isinstance(item, BaseException):
            raise item
        async for chunk in item:
            yield chunk


@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Reset global circuit breakers between tests to prevent state leakage."""
    _circuit_breakers.clear()
    yield
    _circuit_breakers.clear()


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state(self):
        """Test circuit breaker starts closed."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        assert not cb.circuit_open
        assert cb.failure_count == 0
        assert cb.can_attempt()

    def test_success_resets_failures(self):
        """Test successful call resets failure count."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0
        assert not cb.circuit_open

    def test_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)

        cb.record_failure()
        cb.record_failure()
        assert not cb.circuit_open
        assert cb.can_attempt()

        cb.record_failure()
        assert cb.circuit_open
        assert not cb.can_attempt()

    def test_cooldown_expires(self):
        """Test circuit breaker resets after cooldown period (deterministic, no sleep)."""
        current_time = 1000.0

        def mock_clock() -> float:
            return current_time

        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=60, time_func=mock_clock)

        # Open circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.circuit_open
        assert not cb.can_attempt()

        # Advance clock past cooldown
        current_time = 1061.0
        assert cb.can_attempt()
        assert not cb.circuit_open
        assert cb.failure_count == 0

    def test_global_circuit_breakers(self):
        """Test circuit breakers are shared per provider."""
        cb1 = _get_circuit_breaker("openai")
        cb2 = _get_circuit_breaker("openai")
        cb3 = _get_circuit_breaker("openrouter")

        assert cb1 is cb2  # Same provider = same breaker
        assert cb1 is not cb3  # Different provider = different breaker


class TestResilientLLM:
    """Tests for ResilientLLM wrapper."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test successful call doesn't retry."""
        primary = StubChatModel(agenerate_sequence=[_chat_result("Success")])
        resilient = ResilientLLM(primary_llm=primary, provider="test")
        result = await resilient.ainvoke("test input")
        assert primary.agenerate_sequence == []
        assert result.content == "Success"

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retries on transient failure."""
        primary = StubChatModel(
            agenerate_sequence=[
                Exception("Transient error 1"),
                Exception("Transient error 2"),
                _chat_result("Success after retry"),
            ]
        )
        resilient = ResilientLLM(primary_llm=primary, provider="test")
        result = await resilient.ainvoke("test input")
        assert primary.agenerate_sequence == []
        assert result.content == "Success after retry"

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """Test fallback provider used when primary fails."""
        primary = StubChatModel(agenerate_sequence=[Exception("Primary failed")] * 3)
        fallback = StubChatModel(agenerate_sequence=[_chat_result("Fallback success")])
        resilient = ResilientLLM(
            primary_llm=primary,
            provider="primary",
            fallback_llm=fallback,
            fallback_provider="fallback",
        )
        result = await resilient.ainvoke("test input")
        assert primary.agenerate_sequence == []
        assert fallback.agenerate_sequence == []
        assert result.content == "Fallback success"

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_attempts(self):
        """Test circuit breaker prevents attempts when open."""
        cb = _get_circuit_breaker("test_provider")
        for _ in range(5):
            cb.record_failure()
        primary = StubChatModel(agenerate_sequence=[Exception("Should not be called")])
        resilient = ResilientLLM(primary_llm=primary, provider="test_provider")
        with pytest.raises(Exception, match="LLM provider test_provider failed"):
            await resilient.ainvoke("test input")
        assert len(primary.agenerate_sequence) == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_raises_error(self):
        """Test raises error when all retries exhausted."""
        primary = StubChatModel(
            agenerate_sequence=[Exception("Persistent error")] * 3,
        )
        resilient = ResilientLLM(primary_llm=primary, provider="test")
        with pytest.raises(Exception, match="Persistent error"):
            await resilient.ainvoke("test input")
        assert primary.agenerate_sequence == []

    @pytest.mark.asyncio
    async def test_fallback_also_fails(self):
        """Test raises error when both primary and fallback fail."""
        primary = StubChatModel(agenerate_sequence=[Exception("Primary failed")] * 3)
        fallback = StubChatModel(agenerate_sequence=[Exception("Fallback also failed")])
        resilient = ResilientLLM(
            primary_llm=primary,
            provider="primary",
            fallback_llm=fallback,
            fallback_provider="fallback",
        )
        with pytest.raises(Exception, match="Primary failed"):
            await resilient.ainvoke("test input")
        assert primary.agenerate_sequence == []
        assert fallback.agenerate_sequence == []

    def test_delegates_other_attributes(self):
        """Test other attributes are delegated to primary LLM."""
        primary = StubChatModel(agenerate_sequence=[])
        primary.some_attribute = "test_value"  # type: ignore[attr-defined]
        primary.some_method = MagicMock(return_value="result")  # type: ignore[attr-defined]
        resilient = ResilientLLM(primary_llm=primary, provider="test")
        assert resilient.some_attribute == "test_value"
        assert resilient.some_method() == "result"

    @pytest.mark.asyncio
    async def test_astream_retries_on_initial_failure(self):
        """astream should retry on initial connection failure then stream."""

        async def _fake_stream():
            yield ChatGenerationChunk(message=AIMessageChunk(content="chunk1"))
            yield ChatGenerationChunk(message=AIMessageChunk(content="chunk2"))

        primary = StubChatModel(
            astream_sequence=[
                Exception("Connection refused"),
                _fake_stream(),
            ]
        )
        resilient = ResilientLLM(primary_llm=primary, provider="test")
        chunks = []
        async for chunk in resilient.astream("test input"):
            chunks.append(chunk)
        assert len(chunks) >= 2
        assert primary.astream_sequence == []

    @pytest.mark.asyncio
    async def test_astream_fallback_on_primary_exhausted(self):
        """astream should fall back to secondary provider when primary retries exhausted."""

        async def _fake_stream():
            yield ChatGenerationChunk(message=AIMessageChunk(content="fallback_chunk"))

        primary = StubChatModel(astream_sequence=[Exception("Primary dead")] * 3)
        fallback = StubChatModel(astream_sequence=[_fake_stream()])
        resilient = ResilientLLM(
            primary_llm=primary,
            provider="primary",
            fallback_llm=fallback,
            fallback_provider="fallback",
        )
        chunks = []
        async for chunk in resilient.astream("test input"):
            chunks.append(chunk)
        assert len(chunks) >= 1
        assert fallback.astream_sequence == []

    @pytest.mark.asyncio
    async def test_astream_raises_when_all_fail(self):
        """astream should raise when all retries exhausted and no fallback."""
        primary = StubChatModel(astream_sequence=[Exception("Dead")] * 3)
        resilient = ResilientLLM(primary_llm=primary, provider="test")
        with pytest.raises(Exception, match="Dead"):
            async for _ in resilient.astream("test input"):
                pass


class TestGetLLMWithResilience:
    """Tests for get_llm with resilience features."""

    @pytest.fixture
    def mock_settings_with_fallback(self):
        """Mock settings with fallback configured."""
        settings = MagicMock()
        settings.llm_provider = "openrouter"
        settings.llm_model = "anthropic/claude-sonnet-4"
        settings.llm_temperature = 0.7
        settings.llm_api_key.get_secret_value.return_value = "sk-test"
        settings.llm_base_url = None
        settings.llm_fallback_provider = "openai"
        settings.llm_fallback_model = "gpt-4o"
        return settings

    def test_returns_resilient_llm_with_fallback(self, mock_settings_with_fallback):
        """Test get_llm returns ResilientLLM when fallback configured."""
        import src.llm.factory as factory_mod

        factory_mod._llm_cache.clear()

        with patch("src.llm.factory.get_settings", return_value=mock_settings_with_fallback):
            with patch("src.llm.factory._create_llm_instance") as mock_create:
                from src.llm import get_llm

                primary_llm = StubChatModel(agenerate_sequence=[])
                fallback_llm = StubChatModel(agenerate_sequence=[])
                mock_create.side_effect = [primary_llm, fallback_llm]

                llm = get_llm()

                assert isinstance(llm, ResilientLLM)
                assert llm.primary_llm is primary_llm
                assert llm.fallback_llm is fallback_llm
                assert llm.provider == "openrouter"
                assert llm.fallback_provider == "openai"

    def test_returns_resilient_llm_without_fallback(self):
        """Test get_llm returns ResilientLLM even without fallback."""
        settings = MagicMock()
        settings.llm_provider = "openrouter"
        settings.llm_model = "test"
        settings.llm_temperature = 0.7
        settings.llm_api_key.get_secret_value.return_value = "sk-test"
        settings.llm_base_url = None
        settings.llm_fallback_provider = None
        settings.llm_fallback_model = None

        with patch("src.llm.factory.get_settings", return_value=settings):
            with patch("src.llm.factory._create_llm_instance") as mock_create:
                from src.llm import get_llm

                primary_llm = StubChatModel(agenerate_sequence=[])
                mock_create.return_value = primary_llm

                llm = get_llm()

                assert isinstance(llm, ResilientLLM)
                assert llm.primary_llm is primary_llm
                assert llm.fallback_llm is None
