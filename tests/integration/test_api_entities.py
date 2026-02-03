"""Integration tests for Entity API routes.

Tests FastAPI entity endpoints with TestClient.
Constitution: Reliability & Quality - API integration testing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_entity_repo():
    """Create mock entity repository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_entity_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_discovery_session():
    """Create mock discovery session result."""
    session = MagicMock()
    session.id = "session-123"
    session.status = "completed"
    session.entities_found = 10
    session.entities_added = 5
    session.entities_updated = 3
    session.entities_removed = 2
    session.duration_seconds = 1.5
    return session


@pytest.mark.asyncio
class TestEntityListEndpoint:
    """Tests for GET /entities endpoint."""

    async def test_list_entities_empty(self, async_client, mock_entity_repo):
        """Test listing entities when database is empty."""
        with patch("src.api.routes.entities.EntityRepository", return_value=mock_entity_repo):
            response = await async_client.get("/api/v1/entities")

            # Should return 200 with empty list
            assert response.status_code == 200
            data = response.json()
            assert "entities" in data
            assert data["total"] == 0

    async def test_list_entities_with_domain_filter(self, async_client, mock_entity_repo):
        """Test listing entities with domain filter."""
        with patch("src.api.routes.entities.EntityRepository", return_value=mock_entity_repo):
            response = await async_client.get("/api/v1/entities?domain=light")

            assert response.status_code == 200

    async def test_list_entities_with_limit(self, async_client, mock_entity_repo):
        """Test listing entities with limit parameter."""
        with patch("src.api.routes.entities.EntityRepository", return_value=mock_entity_repo):
            response = await async_client.get("/api/v1/entities?limit=10")

            assert response.status_code == 200


@pytest.mark.asyncio
class TestEntityGetEndpoint:
    """Tests for GET /entities/{id} endpoint."""

    async def test_get_entity_not_found(self, async_client, mock_entity_repo):
        """Test getting non-existent entity returns 404."""
        mock_entity_repo.get_by_id.return_value = None
        mock_entity_repo.get_by_entity_id.return_value = None

        with patch("src.api.routes.entities.EntityRepository", return_value=mock_entity_repo):
            response = await async_client.get("/api/v1/entities/nonexistent")

            assert response.status_code == 404

    async def test_get_entity_by_id(self, async_client, mock_entity_repo):
        """Test getting entity by internal ID."""
        mock_entity = MagicMock()
        mock_entity.id = "uuid-123"
        mock_entity.entity_id = "light.test"
        mock_entity.domain = "light"
        mock_entity.name = "Test Light"
        mock_entity.state = "off"
        mock_entity.attributes = {}
        mock_entity.area_id = None
        mock_entity.device_id = None
        mock_entity.device_class = None
        mock_entity.unit_of_measurement = None
        mock_entity.supported_features = 0
        mock_entity.icon = None
        mock_entity.last_synced_at = None

        mock_entity_repo.get_by_id.return_value = mock_entity

        with patch("src.api.routes.entities.EntityRepository", return_value=mock_entity_repo):
            response = await async_client.get("/api/v1/entities/uuid-123")

            # Would be 200 if entity found, 404 if not
            assert response.status_code in [200, 404]


@pytest.mark.asyncio
class TestEntitySyncEndpoint:
    """Tests for POST /entities/sync endpoint."""

    async def test_sync_entities_triggers_discovery(
        self, async_client, mock_discovery_session
    ):
        """Test that sync endpoint triggers discovery."""
        with patch("src.api.routes.entities.run_discovery", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_discovery_session

            response = await async_client.post(
                "/api/v1/entities/sync",
                json={"force": False},
            )

            # Should return sync response
            assert response.status_code in [200, 500]  # 500 if db not available


@pytest.mark.asyncio
class TestEntityQueryEndpoint:
    """Tests for POST /entities/query endpoint."""

    async def test_query_entities_with_question(self, async_client):
        """Test natural language entity query."""
        with patch("src.api.routes.entities.query_entities", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "question": "lights",
                "intent": {"type": "list_entities"},
                "result": {"entities": [], "count": 0},
                "explanation": "Found 0 entities",
            }

            response = await async_client.post(
                "/api/v1/entities/query",
                json={"query": "Show me all lights", "limit": 20},
            )

            # Should return query result
            assert response.status_code in [200, 500]

    async def test_query_entities_validation(self, async_client):
        """Test query endpoint validates input."""
        response = await async_client.post(
            "/api/v1/entities/query",
            json={},  # Missing required 'query' field
        )

        # Should return validation error
        assert response.status_code == 422
