"""Unit tests for Traces API routes.

Tests GET /traces/{trace_id}/spans endpoint with mock MLflow client --
no real database or MLflow connection needed.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.routes.traces import router


def _make_test_app():
    """Create a minimal FastAPI app with the traces router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    return app


@pytest.fixture
def traces_app():
    """Lightweight FastAPI app with traces routes."""
    return _make_test_app()


@pytest.fixture
async def traces_client(traces_app):
    """Async HTTP client wired to the traces test app."""
    async with AsyncClient(
        transport=ASGITransport(app=traces_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_trace():
    """Create a mock MLflow trace object."""
    trace = MagicMock()
    trace.data = MagicMock()
    trace.data.spans = []
    trace.info = MagicMock()
    trace.info.status = "OK"
    trace.info.execution_time_ms = 1000.0
    return trace


@pytest.fixture
def mock_span():
    """Create a mock MLflow span object."""
    span = MagicMock()
    span.span_id = "span-1"
    span.name = "test_span"
    span.span_type = "chain"
    span.start_time_ns = 1000000000  # 1 second in ns
    span.end_time_ns = 2000000000  # 2 seconds in ns
    span.status = MagicMock()
    span.status.status_code = MagicMock()
    span.status.status_code.name = "OK"
    span.attributes = {}
    span.parent_id = None
    span.context = None
    return span


@pytest.mark.asyncio
class TestGetTraceSpans:
    """Tests for GET /api/v1/traces/{trace_id}/spans."""

    async def test_get_trace_spans_success(self, traces_client, mock_trace, mock_span):
        """Should return trace spans formatted for Agent Activity panel."""
        mock_trace.data.spans = [mock_span]

        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(return_value=mock_trace)

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 200
            data = response.json()
            assert data["trace_id"] == "test-trace-id"
            assert data["status"] == "OK"
            assert data["duration_ms"] == 1000.0
            assert data["span_count"] == 1
            assert data["root_span"] is not None
            assert data["root_span"]["span_id"] == "span-1"
            assert data["root_span"]["name"] == "test_span"
            assert data["root_span"]["agent"] == "system"
            assert data["root_span"]["type"] == "chain"
            assert data["root_span"]["status"] == "OK"
            assert "children" in data["root_span"]

    async def test_get_trace_spans_with_agent_role(self, traces_client, mock_trace, mock_span):
        """Should identify agent from agent_role attribute."""
        mock_span.attributes = {"agent_role": "architect"}
        mock_trace.data.spans = [mock_span]

        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(return_value=mock_trace)

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 200
            data = response.json()
            assert data["root_span"]["agent"] == "architect"
            assert "architect" in data["agents_involved"]

    async def test_get_trace_spans_with_nested_spans(self, traces_client, mock_trace):
        """Should build nested span tree correctly."""
        parent_span = MagicMock()
        parent_span.span_id = "parent-1"
        parent_span.name = "parent_span"
        parent_span.span_type = "chain"
        parent_span.start_time_ns = 1000000000
        parent_span.end_time_ns = 3000000000
        parent_span.status = MagicMock()
        parent_span.status.status_code = MagicMock()
        parent_span.status.status_code.name = "OK"
        parent_span.attributes = {}
        parent_span.parent_id = None
        parent_span.context = None

        child_span = MagicMock()
        child_span.span_id = "child-1"
        child_span.name = "child_span"
        child_span.span_type = "tool"
        child_span.start_time_ns = 1500000000
        child_span.end_time_ns = 2500000000
        child_span.status = MagicMock()
        child_span.status.status_code = MagicMock()
        child_span.status.status_code.name = "OK"
        child_span.attributes = {}
        child_span.parent_id = "parent-1"
        child_span.context = None

        mock_trace.data.spans = [parent_span, child_span]

        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(return_value=mock_trace)

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 200
            data = response.json()
            assert data["span_count"] == 2
            assert len(data["root_span"]["children"]) == 1
            assert data["root_span"]["children"][0]["span_id"] == "child-1"

    async def test_get_trace_spans_empty_spans(self, traces_client, mock_trace):
        """Should return empty trace response when no spans."""
        mock_trace.data.spans = []

        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(return_value=mock_trace)

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 200
            data = response.json()
            assert data["trace_id"] == "test-trace-id"
            assert data["root_span"] is None
            assert data["span_count"] == 0
            assert data["agents_involved"] == []

    async def test_get_trace_spans_no_data_attribute(self, traces_client, mock_trace):
        """Should handle trace without data.spans attribute."""
        delattr(mock_trace, "data")
        mock_trace.spans = []

        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(return_value=mock_trace)

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 200
            data = response.json()
            assert data["root_span"] is None
            assert data["span_count"] == 0

    async def test_get_trace_spans_trace_not_found(self, traces_client):
        """Should return 404 when trace not found."""
        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(side_effect=Exception("Trace not found"))

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/nonexistent/spans")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    async def test_get_trace_spans_none_trace(self, traces_client):
        """Should return 404 when trace is None."""
        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(return_value=None)

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    async def test_get_trace_spans_mlflow_connection_error(self, traces_client):
        """Should return 503 when MLflow connection fails."""
        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"
        mock_settings.debug = True  # For sanitize_error to return detailed message
        mock_settings.environment = "testing"

        # Simulate import error or connection error - patch both sites
        with (
            patch("src.settings.get_settings", side_effect=Exception("Connection failed")),
            patch("src.api.utils.get_settings", return_value=mock_settings),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 503
            assert "MLflow connection" in response.json()["detail"]

    async def test_get_trace_spans_with_started_at(self, traces_client, mock_trace, mock_span):
        """Should include started_at timestamp when available."""
        mock_span.start_time_ns = 1609459200000000000  # 2021-01-01 00:00:00 UTC in ns
        mock_trace.data.spans = [mock_span]

        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(return_value=mock_trace)

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 200
            data = response.json()
            assert data["started_at"] is not None
            assert "2021-01-01" in data["started_at"]

    async def test_get_trace_spans_agent_pattern_matching(self, traces_client, mock_trace):
        """Should identify agents from span name patterns."""
        span = MagicMock()
        span.span_id = "span-1"
        span.name = "EnergyAnalyst.analyze"
        span.span_type = "chain"
        span.start_time_ns = 1000000000
        span.end_time_ns = 2000000000
        span.status = MagicMock()
        span.status.status_code = MagicMock()
        span.status.status_code.name = "OK"
        span.attributes = {}
        span.parent_id = None
        span.context = None

        mock_trace.data.spans = [span]

        mock_settings = MagicMock()
        mock_settings.mlflow_tracking_uri = "http://localhost:5000"

        mock_client = MagicMock()
        mock_client.get_trace = MagicMock(return_value=mock_trace)

        with (
            patch("src.settings.get_settings", return_value=mock_settings),
            patch("mlflow.tracking.MlflowClient", return_value=mock_client),
        ):
            response = await traces_client.get("/api/v1/traces/test-trace-id/spans")

            assert response.status_code == 200
            data = response.json()
            assert data["root_span"]["agent"] == "energy_analyst"
            assert "energy_analyst" in data["agents_involved"]
