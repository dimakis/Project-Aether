"""Unit tests for Evaluation API routes.

Tests MLflow evaluation endpoints with mocked MLflow client.
All imports in the route are INLINE, so we patch at source modules.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _make_test_app():
    from fastapi import FastAPI

    from src.api.routes.evaluations import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def evaluations_app():
    return _make_test_app()


@pytest.fixture
async def evaluations_client(evaluations_app):
    async with AsyncClient(
        transport=ASGITransport(app=evaluations_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_mlflow_run():
    run = MagicMock()
    run.info.run_id = "run-123"
    run.info.start_time = int(datetime.now(UTC).timestamp() * 1000)
    run.data.metrics = {
        "trace_count": 10,
        "scorer1/pass_rate": 0.8,
        "scorer1/mean": 0.85,
        "scorer2/pass_rate": 0.9,
    }
    return run


def _mlflow_mock():
    """Create a mock mlflow module with sub-modules."""
    mock = MagicMock()
    mock.tracking.MlflowClient = MagicMock()
    return mock


@pytest.mark.asyncio
class TestGetEvaluationSummary:
    """Tests for GET /api/v1/evaluations/summary."""

    async def test_get_summary_success(self, evaluations_client, mock_mlflow_run):
        mock_mlflow = _mlflow_mock()
        mock_experiment = MagicMock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        mock_client = MagicMock()
        mock_client.search_runs.return_value = [mock_mlflow_run]
        mock_mlflow.tracking.MlflowClient.return_value = mock_client

        with (
            patch.dict(
                "sys.modules",
                {"mlflow": mock_mlflow, "mlflow.tracking": mock_mlflow.tracking},
            ),
            patch("src.settings.get_settings") as mock_get_settings,
        ):
            mock_settings = MagicMock()
            mock_settings.mlflow_tracking_uri = "http://localhost:5000"
            mock_settings.mlflow_experiment_name = "test_exp"
            mock_get_settings.return_value = mock_settings

            response = await evaluations_client.get("/api/v1/evaluations/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["run_id"] == "run-123"
            assert data["trace_count"] == 10

    async def test_get_summary_no_experiment(self, evaluations_client):
        mock_mlflow = _mlflow_mock()
        mock_mlflow.get_experiment_by_name.return_value = None

        with (
            patch.dict(
                "sys.modules",
                {"mlflow": mock_mlflow, "mlflow.tracking": mock_mlflow.tracking},
            ),
            patch("src.settings.get_settings") as mock_get_settings,
        ):
            mock_settings = MagicMock()
            mock_settings.mlflow_tracking_uri = "http://localhost:5000"
            mock_settings.mlflow_experiment_name = "test_exp"
            mock_get_settings.return_value = mock_settings

            response = await evaluations_client.get("/api/v1/evaluations/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["trace_count"] == 0

    async def test_get_summary_no_runs(self, evaluations_client):
        mock_mlflow = _mlflow_mock()
        mock_experiment = MagicMock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment
        mock_client = MagicMock()
        mock_client.search_runs.return_value = []
        mock_mlflow.tracking.MlflowClient.return_value = mock_client

        with (
            patch.dict(
                "sys.modules",
                {"mlflow": mock_mlflow, "mlflow.tracking": mock_mlflow.tracking},
            ),
            patch("src.settings.get_settings") as mock_get_settings,
        ):
            mock_settings = MagicMock()
            mock_settings.mlflow_tracking_uri = "http://localhost:5000"
            mock_settings.mlflow_experiment_name = "test_exp"
            mock_get_settings.return_value = mock_settings

            response = await evaluations_client.get("/api/v1/evaluations/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["trace_count"] == 0

    async def test_get_summary_exception_handled(self, evaluations_client):
        mock_mlflow = _mlflow_mock()
        mock_mlflow.get_experiment_by_name.side_effect = Exception("Connection error")

        with (
            patch.dict(
                "sys.modules",
                {"mlflow": mock_mlflow, "mlflow.tracking": mock_mlflow.tracking},
            ),
            patch("src.settings.get_settings") as mock_get_settings,
        ):
            mock_settings = MagicMock()
            mock_settings.mlflow_tracking_uri = "http://localhost:5000"
            mock_get_settings.return_value = mock_settings

            response = await evaluations_client.get("/api/v1/evaluations/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["trace_count"] == 0


@pytest.mark.asyncio
class TestTriggerEvaluation:
    """Tests for POST /api/v1/evaluations/run."""

    async def test_trigger_evaluation_no_mlflow(self, evaluations_client):
        with patch("src.tracing.init_mlflow", return_value=None):
            response = await evaluations_client.post("/api/v1/evaluations/run")

            assert response.status_code == 503
            data = response.json()
            assert "MLflow not available" in data["detail"]

    async def test_trigger_evaluation_no_scorers(self, evaluations_client):
        with (
            patch("src.tracing.init_mlflow", return_value=MagicMock()),
            patch("src.tracing.scorers.get_all_scorers", return_value=[]),
        ):
            response = await evaluations_client.post("/api/v1/evaluations/run")

            assert response.status_code == 503
            data = response.json()
            assert "No scorers available" in data["detail"]

    async def test_trigger_evaluation_exception(self, evaluations_client):
        with patch("src.tracing.init_mlflow", side_effect=Exception("Connection failed")):
            response = await evaluations_client.post("/api/v1/evaluations/run")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


@pytest.mark.asyncio
class TestListScorers:
    """Tests for GET /api/v1/evaluations/scorers."""

    async def test_list_scorers_success(self, evaluations_client):
        mock_scorer1 = MagicMock()
        mock_scorer1.__name__ = "accuracy_scorer"
        mock_scorer1.__doc__ = "Calculates accuracy"

        mock_scorer2 = MagicMock()
        mock_scorer2.__name__ = "latency_scorer"
        mock_scorer2.__doc__ = "Measures latency"

        with patch(
            "src.tracing.scorers.get_all_scorers",
            return_value=[mock_scorer1, mock_scorer2],
        ):
            response = await evaluations_client.get("/api/v1/evaluations/scorers")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2

    async def test_list_scorers_empty(self, evaluations_client):
        with patch("src.tracing.scorers.get_all_scorers", return_value=[]):
            response = await evaluations_client.get("/api/v1/evaluations/scorers")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
