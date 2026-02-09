"""Unit tests for CLI evaluate command (src/cli/commands/evaluate.py).

All external deps (MLflow, scorers, console) are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_init_mlflow():
    with patch("src.tracing.init_mlflow") as m:
        yield m


@pytest.fixture
def mock_get_settings():
    with patch("src.settings.get_settings") as m:
        s = MagicMock()
        s.mlflow_experiment_name = "test_exp"
        m.return_value = s
        yield m


@pytest.fixture
def mock_console():
    with patch("src.cli.commands.evaluate.console") as m:
        yield m


class TestEvaluateCommand:
    """Tests for the evaluate CLI command."""

    def _make_app(self):
        import typer

        from src.cli.commands.evaluate import evaluate

        app = typer.Typer()
        app.command()(evaluate)
        return app

    def test_evaluate_mlflow_unavailable(self, mock_init_mlflow, mock_console):
        mock_init_mlflow.return_value = None
        app = self._make_app()
        result = runner.invoke(app, [])
        assert result.exit_code == 1

    def test_evaluate_no_traces(self, mock_init_mlflow, mock_get_settings, mock_console):
        import pandas as pd

        mock_mlflow = MagicMock()
        mock_mlflow.search_traces.return_value = pd.DataFrame()
        mock_init_mlflow.return_value = MagicMock()

        with patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.genai": MagicMock()}):
            app = self._make_app()
            result = runner.invoke(app, ["--traces", "10"])
            assert result.exit_code == 0

    def test_evaluate_no_scorers(self, mock_init_mlflow, mock_get_settings, mock_console):
        import pandas as pd

        mock_mlflow = MagicMock()
        trace_df = pd.DataFrame({"trace_id": ["t1", "t2"]})
        mock_mlflow.search_traces.return_value = trace_df
        mock_init_mlflow.return_value = MagicMock()

        with (
            patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.genai": MagicMock()}),
            patch("src.tracing.scorers.get_all_scorers", return_value=[]),
        ):
            app = self._make_app()
            result = runner.invoke(app, [])
            assert result.exit_code == 1

    def test_evaluate_success(self, mock_init_mlflow, mock_get_settings, mock_console):
        import pandas as pd

        mock_mlflow = MagicMock()
        trace_df = pd.DataFrame({"trace_id": ["t1", "t2"]})
        mock_mlflow.search_traces.return_value = trace_df

        mock_eval_result = MagicMock()
        mock_eval_result.metrics = {"accuracy/pass_rate": 0.9}
        mock_eval_result.run_id = "eval-run-1"
        mock_mlflow.genai.evaluate.return_value = mock_eval_result

        mock_scorer = MagicMock()
        mock_scorer.__name__ = "accuracy"
        mock_init_mlflow.return_value = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {"mlflow": mock_mlflow, "mlflow.genai": mock_mlflow.genai},
            ),
            patch("src.tracing.scorers.get_all_scorers", return_value=[mock_scorer]),
        ):
            app = self._make_app()
            result = runner.invoke(app, ["--traces", "50", "--hours", "24"])
            assert result.exit_code == 0

    def test_evaluate_with_experiment_flag(
        self, mock_init_mlflow, mock_get_settings, mock_console
    ):
        import pandas as pd

        mock_mlflow = MagicMock()
        trace_df = pd.DataFrame({"trace_id": ["t1"]})
        mock_mlflow.search_traces.return_value = trace_df

        mock_eval_result = MagicMock()
        mock_eval_result.metrics = {}
        mock_eval_result.run_id = None
        mock_eval_result.aggregate_results = None
        mock_mlflow.genai.evaluate.return_value = mock_eval_result

        mock_scorer = MagicMock()
        mock_scorer.__name__ = "test_scorer"
        mock_init_mlflow.return_value = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {"mlflow": mock_mlflow, "mlflow.genai": mock_mlflow.genai},
            ),
            patch("src.tracing.scorers.get_all_scorers", return_value=[mock_scorer]),
        ):
            app = self._make_app()
            result = runner.invoke(app, ["--experiment", "custom_exp"])
            assert result.exit_code == 0

    def test_evaluate_search_traces_error(
        self, mock_init_mlflow, mock_get_settings, mock_console
    ):
        mock_mlflow = MagicMock()
        mock_mlflow.search_traces.side_effect = Exception("Connection failed")
        mock_init_mlflow.return_value = MagicMock()

        with patch.dict("sys.modules", {"mlflow": mock_mlflow, "mlflow.genai": MagicMock()}):
            app = self._make_app()
            result = runner.invoke(app, [])
            assert result.exit_code == 1

    def test_evaluate_evaluation_error(
        self, mock_init_mlflow, mock_get_settings, mock_console
    ):
        import pandas as pd

        mock_mlflow = MagicMock()
        trace_df = pd.DataFrame({"trace_id": ["t1"]})
        mock_mlflow.search_traces.return_value = trace_df
        mock_mlflow.genai.evaluate.side_effect = Exception("Eval failed")

        mock_scorer = MagicMock()
        mock_scorer.__name__ = "scorer1"
        mock_init_mlflow.return_value = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {"mlflow": mock_mlflow, "mlflow.genai": mock_mlflow.genai},
            ),
            patch("src.tracing.scorers.get_all_scorers", return_value=[mock_scorer]),
        ):
            app = self._make_app()
            result = runner.invoke(app, [])
            assert result.exit_code == 1


class TestDisplayResults:
    """Tests for _display_results helper."""

    def test_display_with_metrics(self, mock_console):
        from src.cli.commands.evaluate import _display_results

        eval_result = MagicMock()
        eval_result.metrics = {"accuracy/pass_rate": 0.85, "latency/mean": 0.42}
        eval_result.aggregate_results = None
        eval_result.run_id = "run-123"
        _display_results(eval_result, 10)

    def test_display_with_aggregate_results(self, mock_console):
        from src.cli.commands.evaluate import _display_results

        eval_result = MagicMock()
        eval_result.metrics = None
        eval_result.aggregate_results = {"accuracy": {"pass_rate": 0.9}}
        eval_result.run_id = None
        _display_results(eval_result, 5)

    def test_display_fallback(self, mock_console):
        from src.cli.commands.evaluate import _display_results

        eval_result = MagicMock()
        eval_result.metrics = None
        eval_result.aggregate_results = None
        eval_result.run_id = None
        _display_results(eval_result, 5)


class TestFormatMetric:
    def test_float_percentage(self):
        from src.cli.commands.evaluate import _format_metric

        assert _format_metric(0.85) == "85.0%"

    def test_float_large(self):
        from src.cli.commands.evaluate import _format_metric

        assert _format_metric(42.567) == "42.57"

    def test_bool_pass(self):
        from src.cli.commands.evaluate import _format_metric

        result = _format_metric(True)
        assert "PASS" in result

    def test_bool_fail(self):
        from src.cli.commands.evaluate import _format_metric

        result = _format_metric(False)
        assert "FAIL" in result

    def test_string(self):
        from src.cli.commands.evaluate import _format_metric

        assert _format_metric("hello") == "hello"
