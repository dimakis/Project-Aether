"""Unit tests for LLM resilience features.

Tests retry logic, circuit breaker, and provider failover.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm import CircuitBreaker, ResilientLLM, _circuit_breakers, _get_circuit_breaker


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

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM instance."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def mock_fallback_llm(self):
        """Create a mock fallback LLM instance."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self, mock_llm):
        """Test successful call doesn't retry."""
        mock_llm.ainvoke.return_value = MagicMock(content="Success")

        resilient = ResilientLLM(mock_llm, provider="test")
        result = await resilient.ainvoke("test input")

        assert mock_llm.ainvoke.call_count == 1
        assert result.content == "Success"

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, mock_llm):
        """Test retries on transient failure."""
        # First two calls fail, third succeeds
        mock_llm.ainvoke.side_effect = [
            Exception("Transient error 1"),
            Exception("Transient error 2"),
            MagicMock(content="Success after retry"),
        ]

        resilient = ResilientLLM(mock_llm, provider="test")
        result = await resilient.ainvoke("test input")

        assert mock_llm.ainvoke.call_count == 3
        assert result.content == "Success after retry"

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, mock_llm, mock_fallback_llm):
        """Test fallback provider used when primary fails."""
        mock_llm.ainvoke.side_effect = Exception("Primary failed")
        mock_fallback_llm.ainvoke.return_value = MagicMock(content="Fallback success")

        resilient = ResilientLLM(
            primary_llm=mock_llm,
            provider="primary",
            fallback_llm=mock_fallback_llm,
            fallback_provider="fallback",
        )

        result = await resilient.ainvoke("test input")

        # Should retry primary 3 times, then use fallback
        assert mock_llm.ainvoke.call_count == 3
        assert mock_fallback_llm.ainvoke.call_count == 1
        assert result.content == "Fallback success"

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_attempts(self, mock_llm):
        """Test circuit breaker prevents attempts when open."""
        cb = _get_circuit_breaker("test_provider")
        # Open circuit breaker
        for _ in range(5):
            cb.record_failure()

        mock_llm.ainvoke.side_effect = Exception("Should not be called")

        resilient = ResilientLLM(mock_llm, provider="test_provider")

        # Should skip attempts due to circuit breaker
        with pytest.raises(Exception, match="LLM provider test_provider failed"):
            await resilient.ainvoke("test input")

        # Should not have called the LLM
        assert mock_llm.ainvoke.call_count == 0

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_raises_error(self, mock_llm):
        """Test raises error when all retries exhausted."""
        mock_llm.ainvoke.side_effect = Exception("Persistent error")

        resilient = ResilientLLM(mock_llm, provider="test")

        with pytest.raises(Exception, match="Persistent error"):
            await resilient.ainvoke("test input")

        assert mock_llm.ainvoke.call_count == 3  # MAX_RETRIES

    @pytest.mark.asyncio
    async def test_fallback_also_fails(self, mock_llm, mock_fallback_llm):
        """Test raises error when both primary and fallback fail."""
        mock_llm.ainvoke.side_effect = Exception("Primary failed")
        mock_fallback_llm.ainvoke.side_effect = Exception("Fallback also failed")

        resilient = ResilientLLM(
            primary_llm=mock_llm,
            provider="primary",
            fallback_llm=mock_fallback_llm,
            fallback_provider="fallback",
        )

        with pytest.raises(Exception, match="Primary failed"):
            await resilient.ainvoke("test input")

        assert mock_llm.ainvoke.call_count == 3
        assert mock_fallback_llm.ainvoke.call_count == 1

    def test_delegates_other_attributes(self, mock_llm):
        """Test other attributes are delegated to primary LLM."""
        mock_llm.some_attribute = "test_value"
        mock_llm.some_method = MagicMock(return_value="result")

        resilient = ResilientLLM(mock_llm, provider="test")

        assert resilient.some_attribute == "test_value"
        assert resilient.some_method() == "result"

    @pytest.mark.asyncio
    async def test_astream_retries_on_initial_failure(self, mock_llm):
        """astream should retry on initial connection failure then stream."""

        async def _fake_stream(*args, **kwargs):
            yield MagicMock(content="chunk1")
            yield MagicMock(content="chunk2")

        # First call fails, second succeeds
        mock_llm.astream = MagicMock(
            side_effect=[
                Exception("Connection refused"),
                _fake_stream(),
            ]
        )

        resilient = ResilientLLM(mock_llm, provider="test")
        chunks = []
        async for chunk in resilient.astream("test input"):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert mock_llm.astream.call_count == 2

    @pytest.mark.asyncio
    async def test_astream_fallback_on_primary_exhausted(self, mock_llm, mock_fallback_llm):
        """astream should fall back to secondary provider when primary retries exhausted."""

        async def _fake_stream(*args, **kwargs):
            yield MagicMock(content="fallback_chunk")

        mock_llm.astream = MagicMock(side_effect=Exception("Primary dead"))
        mock_fallback_llm.astream = MagicMock(return_value=_fake_stream())

        resilient = ResilientLLM(
            primary_llm=mock_llm,
            provider="primary",
            fallback_llm=mock_fallback_llm,
            fallback_provider="fallback",
        )

        chunks = []
        async for chunk in resilient.astream("test input"):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert mock_fallback_llm.astream.call_count == 1

    @pytest.mark.asyncio
    async def test_astream_raises_when_all_fail(self, mock_llm):
        """astream should raise when all retries exhausted and no fallback."""
        mock_llm.astream = MagicMock(side_effect=Exception("Dead"))

        resilient = ResilientLLM(mock_llm, provider="test")

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
        with patch("src.llm.factory.get_settings", return_value=mock_settings_with_fallback):
            with patch("src.llm.factory._create_llm_instance") as mock_create:
                from src.llm import get_llm

                primary_llm = MagicMock()
                fallback_llm = MagicMock()
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

                primary_llm = MagicMock()
                mock_create.return_value = primary_llm

                llm = get_llm()

                assert isinstance(llm, ResilientLLM)
                assert llm.primary_llm is primary_llm
                assert llm.fallback_llm is None
