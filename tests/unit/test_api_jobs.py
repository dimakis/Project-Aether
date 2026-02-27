"""Unit tests for the GET /jobs endpoint.

Tests the MLflow trace -> job mapping logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.api.routes.jobs import _map_trace_to_job


class TestMapTraceToJob:
    """_map_trace_to_job converts MLflow trace info to job format."""

    def test_maps_completed_conversation(self):
        trace = MagicMock()
        trace.info.request_id = "trace-123"
        trace.info.status = MagicMock(value="OK")
        trace.info.timestamp_ms = 1709000000000
        trace.info.execution_time_ms = 3500
        trace.info.tags = {
            "mlflow.runName": "conversation_workflow",
            "mlflow.trace.session": "conv-abc",
        }

        job = _map_trace_to_job(trace)

        assert job["job_id"] == "trace-123"
        assert job["job_type"] == "chat"
        assert job["status"] == "completed"
        assert job["started_at"] == 1709000000000
        assert job["duration_ms"] == 3500
        assert job["conversation_id"] == "conv-abc"

    def test_maps_running_analysis(self):
        trace = MagicMock()
        trace.info.request_id = "trace-456"
        trace.info.status = MagicMock(value="IN_PROGRESS")
        trace.info.timestamp_ms = 1709000000000
        trace.info.execution_time_ms = None
        trace.info.tags = {
            "mlflow.runName": "analysis_workflow",
        }

        job = _map_trace_to_job(trace)

        assert job["job_type"] == "analysis"
        assert job["status"] == "running"
        assert job["duration_ms"] is None

    def test_maps_failed_optimization(self):
        trace = MagicMock()
        trace.info.request_id = "trace-789"
        trace.info.status = MagicMock(value="ERROR")
        trace.info.timestamp_ms = 1709000000000
        trace.info.execution_time_ms = 1000
        trace.info.tags = {
            "mlflow.runName": "optimization_workflow",
        }

        job = _map_trace_to_job(trace)

        assert job["job_type"] == "optimization"
        assert job["status"] == "failed"

    def test_unknown_workflow_defaults_to_other(self):
        trace = MagicMock()
        trace.info.request_id = "trace-xxx"
        trace.info.status = MagicMock(value="OK")
        trace.info.timestamp_ms = 1709000000000
        trace.info.execution_time_ms = 500
        trace.info.tags = {
            "mlflow.runName": "some_unknown_thing",
        }

        job = _map_trace_to_job(trace)

        assert job["job_type"] == "other"

    def test_handles_missing_tags_gracefully(self):
        trace = MagicMock()
        trace.info.request_id = "trace-no-tags"
        trace.info.status = MagicMock(value="OK")
        trace.info.timestamp_ms = 1709000000000
        trace.info.execution_time_ms = 200
        trace.info.tags = {}

        job = _map_trace_to_job(trace)

        assert job["job_id"] == "trace-no-tags"
        assert job["job_type"] == "other"
        assert job["conversation_id"] is None
