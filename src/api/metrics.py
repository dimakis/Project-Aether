"""Operational metrics collection for FastAPI.

Provides in-memory metrics collection for request rates, latency,
error rates, and agent invocations. Metrics are ephemeral (reset on restart).
"""

import time
from collections import Counter, defaultdict, deque
from collections.abc import Callable
from threading import Lock
from typing import Any

# Track application start time for uptime calculation
_start_time: float = time.time()


class MetricsCollector:
    """Thread-safe in-memory metrics collector.
    
    Tracks:
    - Request counts (by method, path, status)
    - Request latency (histogram/percentiles by path)
    - Error counts (by error type)
    - Active requests (gauge)
    - Agent invocation count (by agent role)
    
    Uses a sliding window (last 1000 requests) for percentile calculation.
    """

    def __init__(self, window_size: int = 1000):
        """Initialize metrics collector.
        
        Args:
            window_size: Number of recent requests to keep for percentile calculation
        """
        self._lock = Lock()
        self._window_size = window_size
        
        # Request tracking
        self._request_count = 0
        self._requests_by_status: Counter[str] = Counter()
        self._requests_by_path: Counter[str] = Counter()
        self._requests_by_method_path: Counter[str] = Counter()
        
        # Latency tracking (sliding window)
        self._latency_window: deque[float] = deque(maxlen=window_size)
        
        # Error tracking
        self._error_count = 0
        self._errors_by_type: Counter[str] = Counter()
        
        # Active requests gauge
        self._active_requests = 0
        
        # Agent invocation tracking
        self._agent_invocations: Counter[str] = Counter()

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Record a completed request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
        """
        with self._lock:
            self._request_count += 1
            self._requests_by_status[str(status_code)] += 1
            self._requests_by_path[path] += 1
            self._requests_by_method_path[f"{method} {path}"] += 1
            
            # Add to latency window
            self._latency_window.append(duration_ms)
            
            # Track errors (4xx and 5xx)
            if status_code >= 400:
                self._error_count += 1

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence.
        
        Args:
            error_type: Type of error (exception class name)
        """
        with self._lock:
            self._error_count += 1
            self._errors_by_type[error_type] += 1

    def increment_active_requests(self) -> None:
        """Increment the active requests counter."""
        with self._lock:
            self._active_requests += 1

    def decrement_active_requests(self) -> None:
        """Decrement the active requests counter."""
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

    def record_agent_invocation(self, agent_role: str) -> None:
        """Record an agent invocation.
        
        Args:
            agent_role: Role of the agent (e.g., "data_scientist", "architect")
        """
        with self._lock:
            self._agent_invocations[agent_role] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics as a dictionary.
        
        Returns:
            Dictionary with all current metrics
        """
        with self._lock:
            # Calculate latency percentiles
            latencies = sorted(self._latency_window)
            latency_metrics = {}
            
            if latencies:
                n = len(latencies)
                latency_metrics = {
                    "p50_ms": round(latencies[n // 2], 2),
                    "p95_ms": round(latencies[int(n * 0.95)], 2) if n > 0 else 0.0,
                    "p99_ms": round(latencies[int(n * 0.99)], 2) if n > 0 else 0.0,
                    "min_ms": round(latencies[0], 2) if latencies else 0.0,
                    "max_ms": round(latencies[-1], 2) if latencies else 0.0,
                    "avg_ms": round(sum(latencies) / n, 2) if n > 0 else 0.0,
                }
            else:
                latency_metrics = {
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                    "min_ms": 0.0,
                    "max_ms": 0.0,
                    "avg_ms": 0.0,
                }
            
            return {
                "requests": {
                    "total": self._request_count,
                    "by_status": dict(self._requests_by_status),
                    "by_path": dict(self._requests_by_path.most_common(20)),  # Top 20 paths
                    "by_method_path": dict(self._requests_by_method_path.most_common(20)),  # Top 20 method+path
                },
                "latency": latency_metrics,
                "errors": {
                    "total": self._error_count,
                    "by_type": dict(self._errors_by_type),
                },
                "active_requests": self._active_requests,
                "agents": {
                    "invocations": dict(self._agent_invocations),
                },
                "uptime_seconds": round(time.time() - _start_time, 2),
            }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._request_count = 0
            self._requests_by_status.clear()
            self._requests_by_path.clear()
            self._requests_by_method_path.clear()
            self._latency_window.clear()
            self._error_count = 0
            self._errors_by_type.clear()
            self._active_requests = 0
            self._agent_invocations.clear()


# Singleton instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the singleton metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
