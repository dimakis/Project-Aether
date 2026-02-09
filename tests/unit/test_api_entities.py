"""Unit tests for Entity API routes.

Tests entity endpoints with mock repositories -- no real database
or app lifespan needed.

The get_db dependency is overridden with a mock AsyncSession so
the test never attempts a real Postgres connection.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter
from src.api.routes.entities import get_db


def _make_test_app():
    """Create a minimal FastAPI app with the entities router and mock DB."""
    from fastapi import FastAPI

    from src.api.routes.entities import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Configure rate limiter for tests (required by @limiter.limit decorators)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Override get_db so no real Postgres connection is attempted
    async def _mock_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _mock_get_db
    return app


@pytest.fixture
def entities_app():
    """Lightweight FastAPI app with entity routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def entities_client(entities_app):
    """Async HTTP client wired to the entities test app."""
    async with AsyncClient(
        transport=ASGITransport(app=entities_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_entity():
    """Create a mock HAEntity object."""
    entity = MagicMock()
    entity.id = "uuid-entity-1"
    entity.entity_id = "light.living_room"
    entity.domain = "light"
    entity.name = "Living Room Light"
    entity.state = "on"
    entity.area_id = "area-living-room"
    entity.device_id = "device-light-1"
    entity.attributes = {"brightness": 255}
    entity.device_class = "light"
    entity.unit_of_measurement = None
    entity.icon = "mdi:lightbulb"
    entity.last_changed = datetime.now(UTC)
    entity.last_updated = datetime.now(UTC)
    return entity


@pytest.fixture
def mock_entity_repo(mock_entity):
    """Create mock EntityRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_entity])
    repo.count = AsyncMock(return_value=1)
    repo.get_by_entity_id = AsyncMock(return_value=mock_entity)
    repo.search = AsyncMock(return_value=[mock_entity])
    repo.get_domain_counts = AsyncMock(return_value={"light": 5, "switch": 3})
    return repo


@pytest.mark.asyncio
class TestListEntities:
    """Tests for GET /api/v1/entities."""

    async def test_list_entities_returns_paginated_results(
        self, entities_client, mock_entity_repo, mock_entity
    ):
        """Should return entities with total count."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.get("/api/v1/entities")

            assert response.status_code == 200
            data = response.json()
            assert "entities" in data
            assert data["total"] == 1
            assert len(data["entities"]) == 1
            assert data["entities"][0]["entity_id"] == "light.living_room"
            assert data["entities"][0]["domain"] == "light"

    async def test_list_entities_with_domain_filter(
        self, entities_client, mock_entity_repo
    ):
        """Should pass domain filter to repository."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.get("/api/v1/entities?domain=light")

            assert response.status_code == 200
            mock_entity_repo.list_all.assert_called_once()
            call_kwargs = mock_entity_repo.list_all.call_args[1]
            assert call_kwargs["domain"] == "light"

    async def test_list_entities_with_area_filter(
        self, entities_client, mock_entity_repo
    ):
        """Should pass area_id filter to repository."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.get(
                "/api/v1/entities?area_id=area-living-room"
            )

            assert response.status_code == 200
            call_kwargs = mock_entity_repo.list_all.call_args[1]
            assert call_kwargs["area_id"] == "area-living-room"

    async def test_list_entities_with_state_filter(
        self, entities_client, mock_entity_repo
    ):
        """Should pass state filter to repository."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.get("/api/v1/entities?state=on")

            assert response.status_code == 200
            call_kwargs = mock_entity_repo.list_all.call_args[1]
            assert call_kwargs["state"] == "on"

    async def test_list_entities_with_pagination(
        self, entities_client, mock_entity_repo
    ):
        """Should pass limit and offset to repository."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.get(
                "/api/v1/entities?limit=10&offset=5"
            )

            assert response.status_code == 200
            call_kwargs = mock_entity_repo.list_all.call_args[1]
            assert call_kwargs["limit"] == 10
            assert call_kwargs["offset"] == 5

    async def test_list_entities_empty(self, entities_client):
        """Should return empty list when no entities exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with patch("src.api.routes.entities.EntityRepository", return_value=repo):
            response = await entities_client.get("/api/v1/entities")

            assert response.status_code == 200
            data = response.json()
            assert data["entities"] == []
            assert data["total"] == 0


@pytest.mark.asyncio
class TestGetEntity:
    """Tests for GET /api/v1/entities/{entity_id}."""

    async def test_get_entity_found(
        self, entities_client, mock_entity_repo, mock_entity
    ):
        """Should return entity when found."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.get("/api/v1/entities/light.living_room")

            assert response.status_code == 200
            data = response.json()
            assert data["entity_id"] == "light.living_room"
            assert data["domain"] == "light"
            mock_entity_repo.get_by_entity_id.assert_called_once_with(
                "light.living_room"
            )

    async def test_get_entity_not_found(self, entities_client):
        """Should return 404 when entity not found."""
        repo = MagicMock()
        repo.get_by_entity_id = AsyncMock(return_value=None)

        with patch("src.api.routes.entities.EntityRepository", return_value=repo):
            response = await entities_client.get("/api/v1/entities/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestQueryEntities:
    """Tests for POST /api/v1/entities/query."""

    async def test_query_entities_success(
        self, entities_client, mock_entity_repo, mock_entity
    ):
        """Should return query results."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.post(
                "/api/v1/entities/query",
                json={"query": "lights in living room", "limit": 10},
            )

            assert response.status_code == 200
            data = response.json()
            assert "entities" in data
            assert data["query"] == "lights in living room"
            assert "interpreted_as" in data
            mock_entity_repo.search.assert_called_once_with(
                "lights in living room", limit=10
            )

    async def test_query_entities_default_limit(
        self, entities_client, mock_entity_repo
    ):
        """Should use default limit when not provided."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.post(
                "/api/v1/entities/query",
                json={"query": "temperature sensors"},
            )

            assert response.status_code == 200
            # Default limit should be used
            mock_entity_repo.search.assert_called_once()


@pytest.mark.asyncio
class TestSyncEntities:
    """Tests for POST /api/v1/entities/sync."""

    async def test_sync_entities_success(self, entities_client):
        """Should trigger discovery sync and return results."""
        mock_discovery = MagicMock()
        mock_discovery.id = "discovery-uuid-1"
        mock_discovery.status = "completed"
        mock_discovery.entities_found = 10
        mock_discovery.entities_added = 5
        mock_discovery.entities_updated = 3
        mock_discovery.entities_removed = 2
        mock_discovery.duration_seconds = 1.5

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        async def _mock_get_db():
            yield mock_session

        from src.api.routes.entities import get_db

        entities_app = _make_test_app()
        entities_app.dependency_overrides[get_db] = _mock_get_db

        async with AsyncClient(
            transport=ASGITransport(app=entities_app),
            base_url="http://test",
        ) as client:
            with patch("src.api.routes.entities.run_discovery") as mock_run_discovery:
                mock_run_discovery.return_value = mock_discovery

                response = await client.post(
                    "/api/v1/entities/sync",
                    json={},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] == "discovery-uuid-1"
                assert data["status"] == "completed"
                assert data["entities_found"] == 10
                assert data["entities_added"] == 5
                assert data["entities_updated"] == 3
                assert data["entities_removed"] == 2
                assert data["duration_seconds"] == 1.5
                mock_run_discovery.assert_called_once_with(
                    session=mock_session, triggered_by="api"
                )

    async def test_sync_entities_error(self, entities_client):
        """Should return 500 when discovery fails."""
        mock_session = MagicMock()

        async def _mock_get_db():
            yield mock_session

        from src.api.routes.entities import get_db

        entities_app = _make_test_app()
        entities_app.dependency_overrides[get_db] = _mock_get_db

        async with AsyncClient(
            transport=ASGITransport(app=entities_app),
            base_url="http://test",
        ) as client:
            with patch("src.api.routes.entities.run_discovery") as mock_run_discovery:
                mock_run_discovery.side_effect = Exception("Discovery failed")

                response = await client.post(
                    "/api/v1/entities/sync",
                    json={},
                )

                assert response.status_code == 500
                assert "Discovery failed" in response.json()["detail"]


@pytest.mark.asyncio
class TestGetDomainSummary:
    """Tests for GET /api/v1/entities/domains/summary."""

    async def test_get_domain_summary_success(
        self, entities_client, mock_entity_repo
    ):
        """Should return domain counts."""
        with patch(
            "src.api.routes.entities.EntityRepository", return_value=mock_entity_repo
        ):
            response = await entities_client.get("/api/v1/entities/domains/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["light"] == 5
            assert data["switch"] == 3
            mock_entity_repo.get_domain_counts.assert_called_once()
