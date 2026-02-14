"""Circuit breaker pattern for LLM providers."""

import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Retry configuration for resilient LLM calls
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff delays in seconds


class CircuitBreaker:
    """Simple circuit breaker pattern for LLM providers.

    After N consecutive failures, stops trying the provider for a cooldown period.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: int = 60,
        time_func: Callable[[], float] | None = None,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            cooldown_seconds: Seconds to wait before allowing retry after circuit opens
            time_func: Callable returning current time in seconds (default: time.time).
                       Inject a mock clock for deterministic testing.
        """
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._time_func = time_func or time.time
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.circuit_open = False

    def record_success(self) -> None:
        """Record a successful call, resetting failure count."""
        self.failure_count = 0
        self.circuit_open = False
        self.last_failure_time = None

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = self._time_func()

        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry after {self.cooldown_seconds}s cooldown."
            )

    def can_attempt(self) -> bool:
        """Check if we can attempt a call (circuit not open or cooldown expired)."""
        if not self.circuit_open:
            return True

        if self.last_failure_time is None:
            return True

        elapsed = self._time_func() - self.last_failure_time
        if elapsed >= self.cooldown_seconds:
            logger.info("Circuit breaker cooldown expired, attempting call")
            self.circuit_open = False
            self.failure_count = 0
            return True

        return False


# Global circuit breakers per provider
_circuit_breakers: dict[str, CircuitBreaker] = {}


def _get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create circuit breaker for a provider."""
    if provider not in _circuit_breakers:
        _circuit_breakers[provider] = CircuitBreaker()
    return _circuit_breakers[provider]
