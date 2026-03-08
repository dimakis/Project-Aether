"""Integration tests for Insights API routes.

Tests FastAPI insight endpoints with TestClient.
Constitution: Reliability & Quality - API integration testing.

T113: Insights API integration tests.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_insight():
    """Create a mock Insight object."""
    insight = MagicMock()
    insight.id = "insight-123"
    insight.type = MagicMock()
    insight.type.value = "energy_optimization"
    insight.title = "Peak Usage Detected"
    insight.description = "High energy usage detected at 6 PM"
    insight.evidence = {"peak_hour": 18, "peak_value": 3.5}
    insight.confidence = 0.85
    insight.impact = "high"
    insight.entities = ["sensor.grid_power"]
    insight.script_path = None
    insight.script_output = None
    insight.status = MagicMock()
    insight.status.value = "pending"
    insight.mlflow_run_id = "run-abc123"
    insight.conversation_id = None
    insight.task_label = None
    insight.created_at = datetime(2026, 2, 4, 12, 0, 0)
    insight.reviewed_at = None
    insight.actioned_at = None
    return insight


@pytest.fixture
def mock_insight_repo(mock_insight):
    """Create mock InsightRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_insight])
    repo.list_by_type = AsyncMock(return_value=[mock_insight])
    repo.list_by_status = AsyncMock(return_value=[mock_insight])
    repo.list_pending = AsyncMock(return_value=[mock_insight])
    repo.list_by_impact = AsyncMock(return_value=[mock_insight])
    repo.get_by_id = AsyncMock(return_value=mock_insight)
    repo.count = AsyncMock(return_value=1)
    repo.count_by_type = AsyncMock(return_value={"energy_optimization": 1})
    repo.count_by_status = AsyncMock(return_value={"pending": 1})
    repo.create = AsyncMock(return_value=mock_insight)
    repo.mark_reviewed = AsyncMock(return_value=mock_insight)
    repo.mark_actioned = AsyncMock(return_value=mock_insight)
    repo.dismiss = AsyncMock(return_value=mock_insight)
    repo.delete = AsyncMock(return_value=True)
    repo.get_summary = AsyncMock(
        return_value={
            "total": 1,
            "by_type": {"energy_optimization": 1},
            "by_status": {"pending": 1},
            "pending_count": 1,
            "high_impact_count": 0,
        }
    )
    return repo


@pytest.mark.asyncio
class TestInsightListEndpoint:
    """Tests for GET /insights endpoint."""

    async def test_list_insights(self, async_client, mock_insight_repo):
        """Test listing all insights."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.get("/api/v1/insights")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert data["total"] == 1

    async def test_list_insights_with_type_filter(self, async_client, mock_insight_repo):
        """Test listing insights with type filter."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.get("/api/v1/insights?type=energy_optimization")

            assert response.status_code == 200
            mock_insight_repo.list_by_type.assert_called()

    async def test_list_insights_with_status_filter(self, async_client, mock_insight_repo):
        """Test listing insights with status filter."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.get("/api/v1/insights?status=pending")

            assert response.status_code == 200

    async def test_list_pending_insights(self, async_client, mock_insight_repo):
        """Test GET /insights/pending endpoint."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.get("/api/v1/insights/pending")

            assert response.status_code == 200
            mock_insight_repo.list_pending.assert_called()


@pytest.mark.asyncio
class TestInsightSummaryEndpoint:
    """Tests for GET /insights/summary endpoint."""

    async def test_get_summary(self, async_client, mock_insight_repo):
        """Test getting insights summary."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.get("/api/v1/insights/summary")

            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "by_type" in data
            assert "by_status" in data
            assert "pending_count" in data


@pytest.mark.asyncio
class TestInsightGetEndpoint:
    """Tests for GET /insights/{id} endpoint."""

    async def test_get_insight(self, async_client, mock_insight_repo, mock_insight):
        """Test getting a specific insight."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.get("/api/v1/insights/insight-123")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "insight-123"
            assert data["title"] == "Peak Usage Detected"

    async def test_get_insight_not_found(self, async_client, mock_insight_repo):
        """Test getting non-existent insight returns 404."""
        mock_insight_repo.get_by_id.return_value = None

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.get("/api/v1/insights/nonexistent")

            assert response.status_code == 404


@pytest.mark.asyncio
class TestInsightCreateEndpoint:
    """Tests for POST /insights endpoint."""

    async def test_create_insight(self, async_client, mock_insight_repo):
        """Test creating a new insight."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.post(
                "/api/v1/insights",
                json={
                    "type": "energy_optimization",
                    "title": "New Insight",
                    "description": "A new insight",
                    "evidence": {"source": "test"},
                    "confidence": 0.75,
                    "impact": "medium",
                    "entities": ["sensor.test"],
                },
            )

            assert response.status_code == 201
            mock_insight_repo.create.assert_called()


@pytest.mark.asyncio
class TestInsightActionsEndpoints:
    """Tests for insight action endpoints (review, action, dismiss)."""

    async def test_review_insight(self, async_client, mock_insight_repo):
        """Test marking insight as reviewed."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.post(
                "/api/v1/insights/insight-123/review",
                json={"reviewed_by": "test_user"},
            )

            assert response.status_code == 200
            mock_insight_repo.mark_reviewed.assert_called_with("insight-123")

    async def test_review_insight_not_found(self, async_client, mock_insight_repo):
        """Test reviewing non-existent insight returns 404."""
        mock_insight_repo.mark_reviewed.return_value = None

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.post(
                "/api/v1/insights/nonexistent/review",
                json={"reviewed_by": "test_user"},
            )

            assert response.status_code == 404

    async def test_action_insight(self, async_client, mock_insight_repo):
        """Test marking insight as actioned."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.post(
                "/api/v1/insights/insight-123/action",
                json={"action_taken": "implemented recommendation"},
            )

            assert response.status_code == 200
            mock_insight_repo.mark_actioned.assert_called_with("insight-123")

    async def test_dismiss_insight(self, async_client, mock_insight_repo):
        """Test dismissing an insight."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.post(
                "/api/v1/insights/insight-123/dismiss",
                json={"reason": "not relevant"},
            )

            assert response.status_code == 200
            mock_insight_repo.dismiss.assert_called_with("insight-123")


@pytest.mark.asyncio
class TestInsightDeleteEndpoint:
    """Tests for DELETE /insights/{id} endpoint."""

    async def test_delete_insight(self, async_client, mock_insight_repo):
        """Test deleting an insight."""
        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.delete("/api/v1/insights/insight-123")

            assert response.status_code == 204
            mock_insight_repo.delete.assert_called_with("insight-123")

    async def test_delete_insight_not_found(self, async_client, mock_insight_repo):
        """Test deleting non-existent insight returns 404."""
        mock_insight_repo.delete.return_value = False

        with patch("src.api.routes.insights.InsightRepository", return_value=mock_insight_repo):
            response = await async_client.delete("/api/v1/insights/nonexistent")

            assert response.status_code == 404


@pytest.mark.asyncio
class TestInsightAnalyzeEndpoint:
    """Tests for POST /insights/analyze endpoint."""

    async def test_start_analysis(self, async_client):
        """Test starting an analysis job."""
        # Patch the background task to prevent real DB connections
        with patch("src.api.routes.insights._run_analysis_job", new_callable=AsyncMock):
            response = await async_client.post(
                "/api/v1/insights/analyze",
                json={
                    "analysis_type": "energy_optimization",
                    "hours": 24,
                    "options": {},
                },
            )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["analysis_type"] == "energy_optimization"

    async def test_start_analysis_with_entities(self, async_client):
        """Test starting analysis with specific entities."""
        with patch("src.api.routes.insights._run_analysis_job", new_callable=AsyncMock):
            response = await async_client.post(
                "/api/v1/insights/analyze",
                json={
                    "analysis_type": "anomaly_detection",
                    "entity_ids": ["sensor.grid_power", "sensor.solar_power"],
                    "hours": 48,
                    "options": {},
                },
            )

        assert response.status_code == 202
        data = response.json()
        assert data["analysis_type"] == "anomaly_detection"
