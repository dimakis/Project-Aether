"""Unit tests for src/tracing/mlflow.py.

Tests the MLflow wrapper functions with mocked MLflow imports.
"""

from contextlib import suppress
from unittest.mock import MagicMock, patch

import pytest

# We need to import the module, but MLflow globals are module-level state.
# We'll patch them as needed in each test.


class TestSafeImportMlflow:
    def test_returns_mlflow_when_available(self):
        from src.tracing import mlflow as mod

        result = mod._safe_import_mlflow()
        # Could be mlflow or None depending on env
        assert result is None or hasattr(result, "set_tracking_uri")


class TestDisableTraces:
    def test_disable_traces(self):
        import os

        from src.tracing import mlflow as mod

        orig = mod._traces_available
        mod._traces_available = True
        try:
            mod._disable_traces("test reason")
            assert mod._traces_available is False
            assert os.environ.get("MLFLOW_TRACE_SAMPLING_RATIO") == "0"
        finally:
            mod._traces_available = orig

    def test_disable_idempotent(self):
        from src.tracing import mlflow as mod

        orig = mod._traces_available
        mod._traces_available = False
        try:
            mod._disable_traces("already disabled")
            assert mod._traces_available is False
        finally:
            mod._traces_available = orig


class TestLogParam:
    def test_log_param_no_mlflow(self):
        from src.tracing.mlflow import log_param

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=None):
            log_param("key", "value")  # should not raise

    def test_log_param_no_active_run(self):
        from src.tracing.mlflow import log_param

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = None

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            log_param("key", "value")
            mock_mlflow.log_param.assert_not_called()

    def test_log_param_success(self):
        from src.tracing.mlflow import log_param

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            log_param("key", "value")
            mock_mlflow.log_param.assert_called_once_with("key", "value")


class TestLogParams:
    def test_log_params_no_mlflow(self):
        from src.tracing.mlflow import log_params

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=None):
            log_params({"a": "1"})

    def test_log_params_success(self):
        from src.tracing.mlflow import log_params

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            log_params({"a": "1"})
            mock_mlflow.log_params.assert_called_once()


class TestLogMetric:
    def test_log_metric_no_mlflow(self):
        from src.tracing.mlflow import log_metric

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=None):
            log_metric("key", 1.0)

    def test_log_metric_success(self):
        from src.tracing.mlflow import log_metric

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            log_metric("latency", 0.5, step=1)
            mock_mlflow.log_metric.assert_called_once_with("latency", 0.5, step=1)


class TestLogMetrics:
    def test_log_metrics_success(self):
        from src.tracing.mlflow import log_metrics

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            log_metrics({"a": 1.0, "b": 2.0})
            mock_mlflow.log_metrics.assert_called_once()


class TestLogDict:
    def test_log_dict_success(self):
        from src.tracing.mlflow import log_dict

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            log_dict({"data": "test"}, "output.json")
            mock_mlflow.log_dict.assert_called_once()


class TestEndRun:
    def test_end_run_no_mlflow(self):
        from src.tracing.mlflow import end_run

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=None):
            end_run()

    def test_end_run_success(self):
        from src.tracing.mlflow import end_run

        mock_mlflow = MagicMock()
        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            end_run(status="FINISHED")
            mock_mlflow.end_run.assert_called_once_with(status="FINISHED")


class TestGetActiveRun:
    def test_no_mlflow(self):
        from src.tracing.mlflow import get_active_run

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=None):
            assert get_active_run() is None

    def test_with_active_run(self):
        from src.tracing.mlflow import get_active_run

        mock_mlflow = MagicMock()
        mock_run = MagicMock()
        mock_mlflow.active_run.return_value = mock_run

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            assert get_active_run() is mock_run


class TestGetActiveSpan:
    def test_no_mlflow(self):
        from src.tracing.mlflow import get_active_span

        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=None):
            assert get_active_span() is None


class TestAddSpanEvent:
    def test_no_span(self):
        from src.tracing.mlflow import add_span_event

        add_span_event(None, "test")  # should not raise

    def test_span_without_add_event(self):
        from src.tracing.mlflow import add_span_event

        span = MagicMock(spec=[])  # no add_event
        add_span_event(span, "test")  # should not raise

    def test_success(self):
        from src.tracing.mlflow import add_span_event

        span = MagicMock()
        with patch.dict("sys.modules", {"mlflow.entities": MagicMock()}):
            add_span_event(span, "event_name", {"key": "val"})


class TestStartExperimentRun:
    def test_context_manager(self):
        from src.tracing.mlflow import start_experiment_run

        with (
            patch("src.tracing.mlflow.start_run", return_value=MagicMock()) as mock_start,
            patch("src.tracing.mlflow.end_run") as mock_end,
        ):
            with start_experiment_run(run_name="test"):
                pass
            mock_end.assert_called_once_with(status="FINISHED")

    def test_context_manager_on_error(self):
        from src.tracing.mlflow import start_experiment_run

        with (
            patch("src.tracing.mlflow.start_run", return_value=MagicMock()),
            patch("src.tracing.mlflow.end_run") as mock_end,
        ):
            with suppress(ValueError), start_experiment_run():
                raise ValueError("test")
            mock_end.assert_called_once_with(status="FAILED")


class TestGetOrCreateExperiment:
    def test_returns_none_when_not_initialized(self):
        from src.tracing.mlflow import get_or_create_experiment

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            assert get_or_create_experiment() is None

    def test_creates_new_experiment(self):
        from src.tracing.mlflow import get_or_create_experiment

        mock_mlflow = MagicMock()
        mock_mlflow.get_experiment_by_name.return_value = None
        mock_mlflow.create_experiment.return_value = "exp-123"
        mock_settings = MagicMock()
        mock_settings.mlflow_experiment_name = "test"

        with (
            patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=True),
            patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow),
            patch("src.tracing.mlflow.get_settings", return_value=mock_settings),
        ):
            result = get_or_create_experiment()
            assert result == "exp-123"

    def test_gets_existing_experiment(self):
        from src.tracing.mlflow import get_or_create_experiment

        mock_exp = MagicMock()
        mock_exp.experiment_id = "existing-123"
        mock_mlflow = MagicMock()
        mock_mlflow.get_experiment_by_name.return_value = mock_exp
        mock_settings = MagicMock()
        mock_settings.mlflow_experiment_name = "test"

        with (
            patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=True),
            patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow),
            patch("src.tracing.mlflow.get_settings", return_value=mock_settings),
        ):
            result = get_or_create_experiment()
            assert result == "existing-123"


class TestStartRun:
    def test_returns_none_when_not_initialized(self):
        from src.tracing.mlflow import start_run

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            assert start_run() is None


class TestSearchTraces:
    def test_returns_none_when_not_initialized(self):
        from src.tracing.mlflow import search_traces

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            assert search_traces() is None


class TestLogHumanFeedback:
    def test_skips_when_not_initialized(self):
        from src.tracing.mlflow import log_human_feedback

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            log_human_feedback("trace-1", "sentiment", "positive")  # no error


class TestLogCodeFeedback:
    def test_skips_when_not_initialized(self):
        from src.tracing.mlflow import log_code_feedback

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            log_code_feedback("trace-1", "safety", True)


class TestLogExpectation:
    def test_skips_when_not_initialized(self):
        from src.tracing.mlflow import log_expectation

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            log_expectation("trace-1", "expected_action", "turn_on")


class TestIsAsync:
    def test_sync_function(self):
        from src.tracing.mlflow import _is_async

        def sync_fn():
            pass

        assert _is_async(sync_fn) is False

    def test_async_function(self):
        from src.tracing.mlflow import _is_async

        async def async_fn():
            pass

        assert _is_async(async_fn) is True


class TestAetherTracer:
    def test_init(self):
        from src.tracing.mlflow import AetherTracer

        tracer = AetherTracer(name="test", tags={"a": "b"}, session_id="sess-1")
        assert tracer.name == "test"
        assert tracer.session_id == "sess-1"

    def test_sync_context_manager(self):
        from src.tracing.mlflow import AetherTracer

        with (
            patch("src.tracing.mlflow.start_run", return_value=MagicMock()),
            patch("src.tracing.mlflow.end_run"),
            patch("src.tracing.mlflow.log_metric"),
            patch("src.tracing.mlflow._safe_import_mlflow", return_value=MagicMock()),
        ):
            tracer = AetherTracer(name="test", session_id="sess-1")
            with tracer:
                pass

    def test_run_id_property(self):
        from src.tracing.mlflow import AetherTracer

        tracer = AetherTracer(name="test")
        assert tracer.run_id is None

        mock_run = MagicMock()
        mock_run.info.run_id = "run-123"
        tracer.run = mock_run
        assert tracer.run_id == "run-123"

    def test_log_methods(self):
        from src.tracing.mlflow import AetherTracer

        tracer = AetherTracer(name="test")
        with (
            patch("src.tracing.mlflow.log_param") as mock_lp,
            patch("src.tracing.mlflow.log_params") as mock_lps,
            patch("src.tracing.mlflow.log_metric") as mock_lm,
            patch("src.tracing.mlflow.log_metrics") as mock_lms,
        ):
            tracer.log_param("k", "v")
            tracer.log_params({"k": "v"})
            tracer.log_metric("m", 1.0)
            tracer.log_metrics({"m": 1.0})
            mock_lp.assert_called_once()
            mock_lps.assert_called_once()
            mock_lm.assert_called_once()
            mock_lms.assert_called_once()

    def test_set_tag(self):
        from src.tracing.mlflow import AetherTracer

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        tracer = AetherTracer(name="test")
        with patch("src.tracing.mlflow._safe_import_mlflow", return_value=mock_mlflow):
            tracer.set_tag("key", "val")
            mock_mlflow.set_tag.assert_called_once_with("key", "val")


class TestGetTracer:
    def test_returns_none_by_default(self):
        from src.tracing.mlflow import get_tracer

        result = get_tracer()
        assert result is None


class TestGetTracingStatus:
    def test_returns_dict(self):
        from src.tracing.mlflow import get_tracing_status

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            status = get_tracing_status()
            assert "mlflow_initialized" in status
            assert "traces_enabled" in status


class TestTraceWithUri:
    def test_sync_decorator_no_mlflow(self):
        from src.tracing.mlflow import trace_with_uri

        @trace_with_uri(name="test_fn")
        def my_func():
            return 42

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            assert my_func() == 42

    async def test_async_decorator_no_mlflow(self):
        from src.tracing.mlflow import trace_with_uri

        @trace_with_uri(name="test_async_fn")
        async def my_async_func():
            return 99

        with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
            result = await my_async_func()
            assert result == 99


class TestEnableAutolog:
    def test_skips_when_not_initialized(self):
        from src.tracing import mlflow as mod

        orig = mod._autolog_enabled
        mod._autolog_enabled = False
        try:
            with patch("src.tracing.mlflow._ensure_mlflow_initialized", return_value=False):
                mod.enable_autolog()
                assert mod._autolog_enabled is False
        finally:
            mod._autolog_enabled = orig

    def test_idempotent(self):
        from src.tracing import mlflow as mod

        orig = mod._autolog_enabled
        mod._autolog_enabled = True
        try:
            mod.enable_autolog()  # should return early
        finally:
            mod._autolog_enabled = orig


class TestCheckTraceBackend:
    def test_already_checked(self):
        from src.tracing import mlflow as mod

        orig_checked = mod._traces_checked
        orig_available = mod._traces_available
        mod._traces_checked = True
        try:
            mod._check_trace_backend("http://localhost:5002")
        finally:
            mod._traces_checked = orig_checked
            mod._traces_available = orig_available

    def test_local_backend(self):
        from src.tracing import mlflow as mod

        orig_checked = mod._traces_checked
        orig_available = mod._traces_available
        mod._traces_checked = False
        try:
            mod._check_trace_backend("/local/path")
            assert mod._traces_available is True
        finally:
            mod._traces_checked = orig_checked
            mod._traces_available = orig_available
