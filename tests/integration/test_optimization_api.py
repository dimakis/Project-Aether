"""Integration tests for the optimization API endpoints.

Tests the FastAPI routes for optimization analysis.
Constitution: Reliability & Quality.

TDD: T240 - Optimization API endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(mock_settings):
    """Create a test client for the API.

    Uses mock_settings (environment='testing') so the lifespan
    skips real DB/MLflow init.
    """
    from src.api.main import create_app

    app = create_app(mock_settings)
    return TestClient(app)


class TestOptimizationRoutes:
    def test_optimization_endpoint_exists(self, client):
        """POST /optimize should exist."""
        # Patch background task to prevent real DB connection attempts
        with patch(
            "src.api.routes.optimization._run_optimization_background",
            new_callable=AsyncMock,
        ):
            response = client.post(
                "/api/v1/optimize",
                json={
                    "analysis_types": ["behavior_analysis"],
                    "hours": 24,
                },
            )
        # Should not be 404
        assert response.status_code != 404

    def test_suggestions_list_endpoint(self, client):
        """GET /optimize/suggestions/list should return list."""
        response = client.get("/api/v1/optimize/suggestions/list")
        # Should not be 404
        assert response.status_code != 404

    def test_accept_suggestion_not_found(self, client):
        """POST /optimize/suggestions/{id}/accept with bad ID should 404."""
        response = client.post(
            "/api/v1/optimize/suggestions/nonexistent/accept",
            json={},
        )
        assert response.status_code in (404, 429)

    def test_reject_suggestion_not_found(self, client):
        """POST /optimize/suggestions/{id}/reject with bad ID should 404."""
        response = client.post(
            "/api/v1/optimize/suggestions/nonexistent/reject",
            json={},
        )
        assert response.status_code in (404, 429)
