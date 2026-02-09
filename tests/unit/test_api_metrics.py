"""Unit tests for src/api/metrics.py (MetricsCollector)."""

from src.api.metrics import MetricsCollector, get_metrics_collector


class TestMetricsCollector:
    def test_init(self):
        mc = MetricsCollector()
        metrics = mc.get_metrics()
        assert metrics["requests"]["total"] == 0
        assert metrics["errors"]["total"] == 0
        assert metrics["active_requests"] == 0

    def test_record_request(self):
        mc = MetricsCollector()
        mc.record_request("GET", "/api/v1/health", 200, 15.5)
        metrics = mc.get_metrics()
        assert metrics["requests"]["total"] == 1
        assert metrics["requests"]["by_status"]["200"] == 1

    def test_record_error_request(self):
        mc = MetricsCollector()
        mc.record_request("POST", "/api/v1/chat", 500, 100.0)
        metrics = mc.get_metrics()
        assert metrics["errors"]["total"] == 1

    def test_record_error_by_type(self):
        mc = MetricsCollector()
        mc.record_error("ValueError")
        mc.record_error("ValueError")
        mc.record_error("TimeoutError")
        metrics = mc.get_metrics()
        assert metrics["errors"]["total"] == 3
        assert metrics["errors"]["by_type"]["ValueError"] == 2

    def test_active_requests(self):
        mc = MetricsCollector()
        mc.increment_active_requests()
        mc.increment_active_requests()
        assert mc.get_metrics()["active_requests"] == 2
        mc.decrement_active_requests()
        assert mc.get_metrics()["active_requests"] == 1

    def test_decrement_below_zero(self):
        mc = MetricsCollector()
        mc.decrement_active_requests()
        assert mc.get_metrics()["active_requests"] == 0

    def test_agent_invocations(self):
        mc = MetricsCollector()
        mc.record_agent_invocation("architect")
        mc.record_agent_invocation("data_scientist")
        mc.record_agent_invocation("architect")
        metrics = mc.get_metrics()
        assert metrics["agents"]["invocations"]["architect"] == 2
        assert metrics["agents"]["invocations"]["data_scientist"] == 1

    def test_latency_percentiles(self):
        mc = MetricsCollector()
        for i in range(100):
            mc.record_request("GET", "/api/v1/test", 200, float(i))
        metrics = mc.get_metrics()
        assert metrics["latency"]["p50_ms"] == 50.0
        assert metrics["latency"]["min_ms"] == 0.0
        assert metrics["latency"]["max_ms"] == 99.0

    def test_empty_latency(self):
        mc = MetricsCollector()
        metrics = mc.get_metrics()
        assert metrics["latency"]["p50_ms"] == 0.0

    def test_reset(self):
        mc = MetricsCollector()
        mc.record_request("GET", "/", 200, 10.0)
        mc.record_error("Err")
        mc.increment_active_requests()
        mc.record_agent_invocation("test")
        mc.reset()
        metrics = mc.get_metrics()
        assert metrics["requests"]["total"] == 0
        assert metrics["errors"]["total"] == 0
        assert metrics["active_requests"] == 0

    def test_uptime(self):
        mc = MetricsCollector()
        metrics = mc.get_metrics()
        assert metrics["uptime_seconds"] >= 0


class TestGetMetricsCollector:
    def test_singleton(self):
        c1 = get_metrics_collector()
        c2 = get_metrics_collector()
        assert c1 is c2
