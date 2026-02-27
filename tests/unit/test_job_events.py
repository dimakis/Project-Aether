"""Unit tests for job event helpers.

Verifies that emit_job_start/status/agent/complete/failed publish
correctly structured events to the activity stream.
"""

from __future__ import annotations

from unittest.mock import patch

PATCH_TARGET = "src.api.routes.activity_stream.publish_activity"


class TestEmitJobStart:
    def test_publishes_start_event(self):
        from src.jobs.events import emit_job_start

        with patch(PATCH_TARGET) as mock_pub:
            emit_job_start("job-1", "optimization", "Energy analysis (1 week)")

        mock_pub.assert_called_once()
        event = mock_pub.call_args[0][0]
        assert event["type"] == "job"
        assert event["event"] == "start"
        assert event["job_id"] == "job-1"
        assert event["job_type"] == "optimization"
        assert event["title"] == "Energy analysis (1 week)"

    def test_includes_timestamp(self):
        from src.jobs.events import emit_job_start

        with patch(PATCH_TARGET) as mock_pub:
            emit_job_start("j-1", "chat", "Test")

        event = mock_pub.call_args[0][0]
        assert "ts" in event


class TestEmitJobAgent:
    def test_publishes_agent_start(self):
        from src.jobs.events import emit_job_agent

        with patch(PATCH_TARGET) as mock_pub:
            emit_job_agent("job-1", "energy_analyst", "start")

        event = mock_pub.call_args[0][0]
        assert event["type"] == "job"
        assert event["event"] == "agent_start"
        assert event["job_id"] == "job-1"
        assert event["agent"] == "energy_analyst"

    def test_publishes_agent_end(self):
        from src.jobs.events import emit_job_agent

        with patch(PATCH_TARGET) as mock_pub:
            emit_job_agent("job-1", "architect", "end")

        event = mock_pub.call_args[0][0]
        assert event["event"] == "agent_end"


class TestEmitJobStatus:
    def test_publishes_status_message(self):
        from src.jobs.events import emit_job_status

        with patch(PATCH_TARGET) as mock_pub:
            emit_job_status("job-1", "Running behavioral analysis...")

        event = mock_pub.call_args[0][0]
        assert event["type"] == "job"
        assert event["event"] == "status"
        assert event["message"] == "Running behavioral analysis..."


class TestEmitJobComplete:
    def test_publishes_complete_event(self):
        from src.jobs.events import emit_job_complete

        with patch(PATCH_TARGET) as mock_pub:
            emit_job_complete("job-1")

        event = mock_pub.call_args[0][0]
        assert event["type"] == "job"
        assert event["event"] == "complete"
        assert event["job_id"] == "job-1"


class TestEmitJobFailed:
    def test_publishes_failed_event_with_error(self):
        from src.jobs.events import emit_job_failed

        with patch(PATCH_TARGET) as mock_pub:
            emit_job_failed("job-1", "Timeout exceeded")

        event = mock_pub.call_args[0][0]
        assert event["type"] == "job"
        assert event["event"] == "failed"
        assert event["job_id"] == "job-1"
        assert event["error"] == "Timeout exceeded"
