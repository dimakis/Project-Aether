"""Unit tests for Insight API schemas.

Tests Pydantic schema validation for insight endpoints.
Constitution: Reliability & Quality - comprehensive schema testing.

TDD: T102 - Insight schema tests.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.api.schemas.insights import (
    ActionRequest,
    AnalysisJob,
    AnalysisRequest,
    DismissRequest,
    EnergyOverviewResponse,
    EnergyStatsResponse,
    InsightCreate,
    InsightListResponse,
    InsightResponse,
    InsightStatus,
    InsightSummary,
    InsightType,
    ReviewRequest,
)


class TestInsightEnums:
    """Tests for insight enums."""

    def test_insight_type_values(self):
        """Test all insight types exist."""
        assert InsightType.ENERGY_OPTIMIZATION == "energy_optimization"
        assert InsightType.ANOMALY_DETECTION == "anomaly_detection"
        assert InsightType.USAGE_PATTERN == "usage_pattern"
        assert InsightType.COST_SAVING == "cost_saving"
        assert InsightType.MAINTENANCE_PREDICTION == "maintenance_prediction"

    def test_insight_status_values(self):
        """Test all insight statuses exist."""
        assert InsightStatus.PENDING == "pending"
        assert InsightStatus.REVIEWED == "reviewed"
        assert InsightStatus.ACTIONED == "actioned"
        assert InsightStatus.DISMISSED == "dismissed"


class TestInsightCreate:
    """Tests for InsightCreate schema."""

    def test_valid_create(self):
        """Test creating valid insight."""
        insight = InsightCreate(
            type=InsightType.ENERGY_OPTIMIZATION,
            title="High energy usage",
            description="Your HVAC is using 30% more energy",
            evidence={"avg": 100, "current": 130},
            confidence=0.85,
            impact="high",
            entities=["climate.living_room"],
        )

        assert insight.type == InsightType.ENERGY_OPTIMIZATION
        assert insight.confidence == 0.85
        assert len(insight.entities) == 1

    def test_confidence_bounds(self):
        """Test confidence must be 0.0-1.0."""
        with pytest.raises(ValidationError):
            InsightCreate(
                type=InsightType.ENERGY_OPTIMIZATION,
                title="Test",
                description="Test",
                evidence={},
                confidence=1.5,  # Invalid: > 1.0
                impact="low",
            )

        with pytest.raises(ValidationError):
            InsightCreate(
                type=InsightType.ENERGY_OPTIMIZATION,
                title="Test",
                description="Test",
                evidence={},
                confidence=-0.1,  # Invalid: < 0.0
                impact="low",
            )

    def test_optional_fields(self):
        """Test optional fields have defaults."""
        insight = InsightCreate(
            type=InsightType.ANOMALY_DETECTION,
            title="Anomaly",
            description="Unusual pattern",
            evidence={},
            confidence=0.7,
            impact="medium",
        )

        assert insight.entities == []
        assert insight.script_path is None
        assert insight.script_output is None
        assert insight.mlflow_run_id is None

    def test_with_script_info(self):
        """Test insight with script information."""
        insight = InsightCreate(
            type=InsightType.ENERGY_OPTIMIZATION,
            title="Analysis Result",
            description="From analysis",
            evidence={"chart": "base64..."},
            confidence=0.9,
            impact="high",
            script_path="/mlflow/artifacts/script.py",
            script_output={"figures": ["fig1.png"]},
            mlflow_run_id="run-123",
        )

        assert insight.script_path == "/mlflow/artifacts/script.py"
        assert insight.mlflow_run_id == "run-123"


class TestInsightResponse:
    """Tests for InsightResponse schema."""

    def test_response_from_attributes(self):
        """Test response can be created from ORM attributes."""
        # InsightResponse has model_config = {"from_attributes": True}
        response = InsightResponse(
            id="insight-123",
            type=InsightType.ENERGY_OPTIMIZATION,
            title="Test",
            description="Test description",
            evidence={},
            confidence=0.8,
            impact="medium",
            entities=[],
            script_path=None,
            script_output=None,
            status=InsightStatus.PENDING,
            mlflow_run_id=None,
            created_at=datetime.utcnow(),
            reviewed_at=None,
            actioned_at=None,
        )

        assert response.id == "insight-123"
        assert response.status == InsightStatus.PENDING

    def test_response_with_timestamps(self):
        """Test response with all timestamps."""
        now = datetime.utcnow()
        response = InsightResponse(
            id="insight-123",
            type=InsightType.USAGE_PATTERN,
            title="Pattern Found",
            description="Usage pattern detected",
            evidence={},
            confidence=0.75,
            impact="low",
            entities=["sensor.test"],
            script_path=None,
            script_output=None,
            status=InsightStatus.ACTIONED,
            mlflow_run_id=None,
            created_at=now,
            reviewed_at=now,
            actioned_at=now,
        )

        assert response.reviewed_at is not None
        assert response.actioned_at is not None


class TestInsightListResponse:
    """Tests for InsightListResponse schema."""

    def test_list_response(self):
        """Test list response structure."""
        response = InsightListResponse(
            items=[],
            total=0,
            limit=50,
            offset=0,
        )

        assert response.items == []
        assert response.total == 0

    def test_list_with_items(self):
        """Test list response with items."""
        item = InsightResponse(
            id="insight-1",
            type=InsightType.ENERGY_OPTIMIZATION,
            title="Test",
            description="Test",
            evidence={},
            confidence=0.8,
            impact="medium",
            entities=[],
            script_path=None,
            script_output=None,
            status=InsightStatus.PENDING,
            mlflow_run_id=None,
            created_at=datetime.utcnow(),
            reviewed_at=None,
            actioned_at=None,
        )

        response = InsightListResponse(
            items=[item],
            total=1,
            limit=50,
            offset=0,
        )

        assert len(response.items) == 1
        assert response.total == 1


class TestInsightSummary:
    """Tests for InsightSummary schema."""

    def test_summary_structure(self):
        """Test summary has all fields."""
        summary = InsightSummary(
            total=10,
            by_type={"energy_optimization": 5, "anomaly_detection": 3},
            by_status={"pending": 4, "reviewed": 6},
            pending_count=4,
            high_impact_count=2,
        )

        assert summary.total == 10
        assert summary.by_type["energy_optimization"] == 5
        assert summary.pending_count == 4


class TestAnalysisRequest:
    """Tests for AnalysisRequest schema."""

    def test_default_values(self):
        """Test default analysis request values."""
        request = AnalysisRequest()

        assert request.analysis_type == "energy"
        assert request.entity_ids is None
        assert request.hours == 24
        assert request.options == {}

    def test_custom_request(self):
        """Test custom analysis request."""
        request = AnalysisRequest(
            analysis_type="anomaly",
            entity_ids=["sensor.power1", "sensor.power2"],
            hours=168,
            options={"sensitivity": "high"},
        )

        assert request.analysis_type == "anomaly"
        assert len(request.entity_ids) == 2
        assert request.hours == 168

    def test_hours_bounds(self):
        """Test hours must be within bounds."""
        # Valid: 1 to 672 (4 weeks)
        AnalysisRequest(hours=1)
        AnalysisRequest(hours=672)

        with pytest.raises(ValidationError):
            AnalysisRequest(hours=0)

        with pytest.raises(ValidationError):
            AnalysisRequest(hours=1000)


class TestAnalysisJob:
    """Tests for AnalysisJob schema."""

    def test_job_structure(self):
        """Test analysis job structure."""
        job = AnalysisJob(
            job_id="job-123",
            status="running",
            analysis_type="energy",
            progress=0.5,
            started_at=datetime.utcnow(),
            completed_at=None,
            mlflow_run_id="run-456",
        )

        assert job.job_id == "job-123"
        assert job.status == "running"
        assert job.progress == 0.5

    def test_completed_job(self):
        """Test completed job with insights."""
        job = AnalysisJob(
            job_id="job-123",
            status="completed",
            analysis_type="energy",
            progress=1.0,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            insight_ids=["insight-1", "insight-2"],
        )

        assert job.status == "completed"
        assert len(job.insight_ids) == 2

    def test_failed_job(self):
        """Test failed job with error."""
        job = AnalysisJob(
            job_id="job-123",
            status="failed",
            analysis_type="energy",
            progress=0.3,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error="Connection timeout",
        )

        assert job.status == "failed"
        assert job.error == "Connection timeout"


class TestActionSchemas:
    """Tests for action request schemas."""

    def test_review_request(self):
        """Test review request schema."""
        request = ReviewRequest(
            reviewed_by="admin",
            comment="Looks good",
        )

        assert request.reviewed_by == "admin"
        assert request.comment == "Looks good"

    def test_review_request_defaults(self):
        """Test review request defaults."""
        request = ReviewRequest()

        assert request.reviewed_by == "user"
        assert request.comment is None

    def test_action_request(self):
        """Test action request schema."""
        request = ActionRequest(
            actioned_by="admin",
            action_taken="Created automation",
            create_automation=True,
        )

        assert request.actioned_by == "admin"
        assert request.create_automation is True

    def test_dismiss_request(self):
        """Test dismiss request schema."""
        request = DismissRequest(reason="Not applicable")

        assert request.reason == "Not applicable"


class TestEnergySchemas:
    """Tests for energy-related schemas."""

    def test_energy_stats_response(self):
        """Test energy stats response."""
        stats = EnergyStatsResponse(
            entity_id="sensor.grid_power",
            friendly_name="Grid Power",
            total_kwh=150.5,
            average_kwh=6.25,
            peak_value=15.0,
            peak_timestamp=datetime.utcnow(),
            daily_totals={"2024-01-01": 50.0},
            hourly_averages={"12": 7.5},
            hours_analyzed=24,
        )

        assert stats.entity_id == "sensor.grid_power"
        assert stats.total_kwh == 150.5
        assert "2024-01-01" in stats.daily_totals

    def test_energy_overview_response(self):
        """Test energy overview response."""
        sensor_stats = EnergyStatsResponse(
            entity_id="sensor.power",
            friendly_name="Power",
            total_kwh=100.0,
            average_kwh=4.0,
            peak_value=10.0,
            peak_timestamp=None,
            daily_totals={},
            hourly_averages={},
            hours_analyzed=24,
        )

        overview = EnergyOverviewResponse(
            sensors=[sensor_stats],
            total_kwh=100.0,
            sensor_count=1,
            hours_analyzed=24,
            analysis_timestamp=datetime.utcnow(),
        )

        assert len(overview.sensors) == 1
        assert overview.total_kwh == 100.0
        assert overview.sensor_count == 1
