"""Unit tests for CLI analyze commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli.main import app


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_workflow():
    """Mock DataScientistWorkflow."""
    workflow = MagicMock()
    workflow.run_analysis = AsyncMock()
    return workflow


@pytest.fixture
def mock_insight_repo():
    """Mock insight repository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.list_by_type = AsyncMock(return_value=[])
    repo.list_by_status = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.count = AsyncMock(return_value=0)
    return repo


class TestAnalyze:
    """Test analyze command."""

    def test_analyze_energy_success(self, runner, mock_session, mock_workflow):
        """Test energy analysis success."""
        from src.graph.state import AnalysisState

        mock_state = AnalysisState(
            insights=[
                {
                    "title": "High Energy Usage",
                    "description": "Energy usage is high",
                    "impact": "high",
                    "confidence": 0.85,
                }
            ],
            recommendations=["Reduce usage"],
        )

        mock_workflow.run_analysis = AsyncMock(return_value=mock_state)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = runner.invoke(app, ["analyze", "energy", "--days", "7"])

            assert result.exit_code == 0
            assert "Analysis: Energy" in result.stdout
            assert "Insights found: 1" in result.stdout

    def test_analyze_anomaly_with_entity(self, runner, mock_session, mock_workflow):
        """Test anomaly analysis with specific entity."""
        from src.graph.state import AnalysisState

        mock_state = AnalysisState(insights=[], recommendations=[])

        mock_workflow.run_analysis = AsyncMock(return_value=mock_state)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = runner.invoke(
                app, ["analyze", "anomaly", "--entity", "sensor.temperature", "--days", "1"]
            )

            assert result.exit_code == 0
            mock_workflow.run_analysis.assert_called_once()
            call_kwargs = mock_workflow.run_analysis.call_args[1]
            assert call_kwargs["entity_ids"] == ["sensor.temperature"]
            assert call_kwargs["hours"] == 24

    def test_analyze_custom_with_query(self, runner, mock_session, mock_workflow):
        """Test custom analysis with query."""
        from src.graph.state import AnalysisState

        mock_state = AnalysisState(insights=[], recommendations=[])

        mock_workflow.run_analysis = AsyncMock(return_value=mock_state)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = runner.invoke(
                app, ["analyze", "custom", "--query", "Find peak usage", "--days", "1"]
            )

            assert result.exit_code == 0
            call_kwargs = mock_workflow.run_analysis.call_args[1]
            assert call_kwargs["custom_query"] == "Find peak usage"

    def test_analyze_error_handling(self, runner, mock_session, mock_workflow):
        """Test analyze error handling."""
        mock_workflow.run_analysis = AsyncMock(side_effect=Exception("Analysis failed"))

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch("src.agents.DataScientistWorkflow", return_value=mock_workflow),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = runner.invoke(app, ["analyze", "energy"])

            assert result.exit_code == 0  # CLI doesn't exit on error, just prints
            assert "Analysis failed" in result.stdout


class TestInsights:
    """Test insights list command."""

    def test_insights_list_no_results(self, runner, mock_session, mock_insight_repo):
        """Test listing insights when none exist."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.InsightRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_insight_repo

            result = runner.invoke(app, ["insights"])

            assert result.exit_code == 0
            assert "No insights found" in result.stdout

    def test_insights_list_with_results(self, runner, mock_session, mock_insight_repo):
        """Test listing insights with results."""
        from datetime import UTC, datetime

        from src.storage.entities.insight import Insight, InsightStatus, InsightType

        mock_insight = Insight(
            id="insight-123",
            type=InsightType.ENERGY_OPTIMIZATION,
            title="High Energy Usage",
            description="Energy usage is high",
            impact="high",
            confidence=0.85,
            status=InsightStatus.PENDING,
            created_at=datetime.now(UTC),
        )

        mock_insight_repo.list_all = AsyncMock(return_value=[mock_insight])
        mock_insight_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.InsightRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_insight_repo

            result = runner.invoke(app, ["insights"])

            assert result.exit_code == 0
            assert "Insights" in result.stdout
            # Title may be truncated in table, check for part of it or type
            assert "Energy" in result.stdout or "High" in result.stdout

    def test_insights_list_with_status_filter(self, runner, mock_session, mock_insight_repo):
        """Test listing insights with status filter."""
        from datetime import UTC, datetime

        from src.storage.entities.insight import Insight, InsightStatus, InsightType

        mock_insight = Insight(
            id="insight-123",
            type=InsightType.ENERGY_OPTIMIZATION,
            title="High Energy Usage",
            description="Energy usage is high",
            impact="high",
            confidence=0.85,
            status=InsightStatus.PENDING,
            created_at=datetime.now(UTC),
        )

        mock_insight_repo.list_by_status = AsyncMock(return_value=[mock_insight])
        mock_insight_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.InsightRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_insight_repo

            result = runner.invoke(app, ["insights", "--status", "pending"])

            assert result.exit_code == 0
            mock_insight_repo.list_by_status.assert_called_once()

    def test_insights_list_with_type_filter(self, runner, mock_session, mock_insight_repo):
        """Test listing insights with type filter."""
        from datetime import UTC, datetime

        from src.storage.entities.insight import Insight, InsightStatus, InsightType

        mock_insight = Insight(
            id="insight-123",
            type=InsightType.ENERGY_OPTIMIZATION,
            title="High Energy Usage",
            description="Energy usage is high",
            impact="high",
            confidence=0.85,
            status=InsightStatus.PENDING,
            created_at=datetime.now(UTC),
        )

        mock_insight_repo.list_by_type = AsyncMock(return_value=[mock_insight])
        mock_insight_repo.count = AsyncMock(return_value=1)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.InsightRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_insight_repo

            result = runner.invoke(app, ["insights", "--type", "energy_optimization"])

            assert result.exit_code == 0
            mock_insight_repo.list_by_type.assert_called_once()


class TestShowInsight:
    """Test show insight command."""

    def test_show_insight_not_found(self, runner, mock_session, mock_insight_repo):
        """Test showing insight that doesn't exist."""
        mock_insight_repo.get_by_id = AsyncMock(return_value=None)
        mock_insight_repo.list_all = AsyncMock(return_value=[])

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.InsightRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_insight_repo

            result = runner.invoke(app, ["insight", "nonexistent"])

            assert result.exit_code == 0
            assert "not found" in result.stdout

    def test_show_insight_success(self, runner, mock_session, mock_insight_repo):
        """Test showing insight successfully."""
        from datetime import UTC, datetime

        from src.storage.entities.insight import Insight, InsightStatus, InsightType

        mock_insight = Insight(
            id="insight-123",
            type=InsightType.ENERGY_OPTIMIZATION,
            title="High Energy Usage",
            description="Energy usage is high during peak hours",
            impact="high",
            confidence=0.85,
            status=InsightStatus.PENDING,
            created_at=datetime.now(UTC),
            entities=["sensor.power"],
            evidence={"peak_hours": [18, 19, 20]},
        )

        mock_insight_repo.get_by_id = AsyncMock(return_value=mock_insight)

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.dal.InsightRepository") as mock_repo_class,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_repo_class.return_value = mock_insight_repo

            result = runner.invoke(app, ["insight", "insight-123"])

            assert result.exit_code == 0
            assert "High Energy Usage" in result.stdout
            assert "Energy usage is high" in result.stdout


class TestOptimize:
    """Test optimize command."""

    def test_optimize_all_success(self, runner, mock_session):
        """Test optimization with 'all' type."""
        from src.graph.state import AnalysisState

        mock_state = AnalysisState(
            insights=[
                {
                    "title": "Optimization Opportunity",
                    "description": "Can optimize",
                    "impact": "medium",
                    "confidence": 0.75,
                    "type": "behavior_analysis",
                }
            ],
            recommendations=["Optimize behavior"],
        )

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch(
                "src.graph.workflows.run_optimization_workflow", new_callable=AsyncMock
            ) as mock_workflow,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_workflow.return_value = mock_state

            result = runner.invoke(app, ["optimize", "all", "--days", "7"])

            assert result.exit_code == 0
            assert "Optimization: All" in result.stdout
            assert "Insights found: 1" in result.stdout

    def test_optimize_gaps_success(self, runner, mock_session):
        """Test optimization with gaps type."""
        from src.graph.state import AnalysisState, AutomationSuggestion

        mock_state = AnalysisState(
            insights=[],
            recommendations=[],
            automation_suggestion=AutomationSuggestion(
                pattern="Pattern detected",
                proposed_trigger="Trigger",
                proposed_action="Action",
                confidence=0.8,
                entities=["sensor.temp"],
            ),
        )

        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch(
                "src.graph.workflows.run_optimization_workflow", new_callable=AsyncMock
            ) as mock_workflow,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_workflow.return_value = mock_state

            result = runner.invoke(app, ["optimize", "gaps", "--days", "14"])

            assert result.exit_code == 0
            assert "Automation suggestion: Yes" in result.stdout
            assert "Automation Suggestion" in result.stdout

    def test_optimize_error_handling(self, runner, mock_session):
        """Test optimize error handling."""
        with (
            patch("src.storage.get_session") as mock_get_session,
            patch("src.tracing.init_mlflow"),
            patch(
                "src.graph.workflows.run_optimization_workflow", new_callable=AsyncMock
            ) as mock_workflow,
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_workflow.side_effect = Exception("Optimization failed")

            result = runner.invoke(app, ["optimize", "behavior"])

            assert result.exit_code == 0
            assert "Optimization failed" in result.stdout
