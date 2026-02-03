"""Unit tests for Insight model.

TDD: T091 - Test Insight model before implementation.
"""

import pytest
from datetime import datetime
from uuid import uuid4


class TestInsightModel:
    """Tests for Insight SQLAlchemy model."""

    def test_insight_creation(self):
        """Test creating an Insight instance."""
        from src.storage.entities import Insight, InsightType, InsightStatus

        insight = Insight(
            id=str(uuid4()),
            type=InsightType.ENERGY_OPTIMIZATION,
            title="High energy usage detected",
            description="Your HVAC system is using 30% more energy than average",
            evidence={"avg_usage": 150, "your_usage": 195, "period": "7d"},
            confidence=0.85,
            impact="medium",
            entities=["climate.living_room", "sensor.hvac_power"],
        )

        assert insight.type == InsightType.ENERGY_OPTIMIZATION
        assert insight.title == "High energy usage detected"
        assert insight.confidence == 0.85
        assert "climate.living_room" in insight.entities

    def test_insight_with_script(self):
        """Test Insight with analysis script."""
        from src.storage.entities import Insight, InsightType, InsightStatus

        insight = Insight(
            id=str(uuid4()),
            type=InsightType.ENERGY_OPTIMIZATION,
            title="Analysis Result",
            description="Based on analysis",
            evidence={},
            confidence=0.9,
            impact="high",
            entities=[],
            script_path="/tmp/analysis_123.py",
            script_output={"chart": "base64...", "summary": "Usage peaked at 3PM"},
        )

        assert insight.script_path == "/tmp/analysis_123.py"
        assert "summary" in insight.script_output

    def test_insight_status_transitions(self):
        """Test Insight status can transition."""
        from src.storage.entities import Insight, InsightType, InsightStatus

        insight = Insight(
            id=str(uuid4()),
            type=InsightType.ENERGY_OPTIMIZATION,
            title="Test",
            description="Test insight",
            evidence={},
            confidence=0.5,
            impact="low",
            entities=[],
            status=InsightStatus.PENDING,
        )

        assert insight.status == InsightStatus.PENDING

        # Transition to reviewed
        insight.status = InsightStatus.REVIEWED
        assert insight.status == InsightStatus.REVIEWED

        # Transition to actioned
        insight.status = InsightStatus.ACTIONED
        assert insight.status == InsightStatus.ACTIONED

    def test_insight_with_mlflow_run(self):
        """Test Insight tracks MLflow run ID."""
        from src.storage.entities import Insight, InsightType, InsightStatus

        run_id = str(uuid4())
        insight = Insight(
            id=str(uuid4()),
            type=InsightType.ANOMALY_DETECTION,
            title="Anomaly Found",
            description="Unusual pattern",
            evidence={},
            confidence=0.7,
            impact="medium",
            entities=[],
            mlflow_run_id=run_id,
        )

        assert insight.mlflow_run_id == run_id


class TestInsightType:
    """Tests for InsightType enum."""

    def test_insight_types_exist(self):
        """Test all expected insight types exist."""
        from src.storage.entities import InsightType

        assert hasattr(InsightType, "ENERGY_OPTIMIZATION")
        assert hasattr(InsightType, "ANOMALY_DETECTION")
        assert hasattr(InsightType, "USAGE_PATTERN")
        assert hasattr(InsightType, "COST_SAVING")


class TestInsightStatus:
    """Tests for InsightStatus enum."""

    def test_insight_statuses_exist(self):
        """Test all expected statuses exist."""
        from src.storage.entities import InsightStatus

        assert hasattr(InsightStatus, "PENDING")
        assert hasattr(InsightStatus, "REVIEWED")
        assert hasattr(InsightStatus, "ACTIONED")
        assert hasattr(InsightStatus, "DISMISSED")
