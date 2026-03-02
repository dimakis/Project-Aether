"""Unit tests for Tool Groups API routes.

Tests GET/POST/PUT /api/v1/tool-groups with mocked get_session and repository.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.storage.entities.tool_group import ToolGroup


def _make_test_app():
    """Create a minimal FastAPI app with the tool_groups router."""
    from fastapi import FastAPI

    from src.api.routes.tool_groups import router

    app = FastAPI()
    # Router already has prefix /api/v1/tool-groups
    app.include_router(router)
    return app


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_tool_group():
    """Mock ToolGroup entity for response serialization."""
    group = MagicMock(spec=ToolGroup)
    group.id = "group-uuid-1"
    group.name = "ha_entity_query"
    group.display_name = "HA Entity Queries"
    group.description = "Query HA entities"
    group.tool_names = ["get_entities", "get_states"]
    group.is_read_only = True
    group.created_at = datetime.now(UTC)
    group.updated_at = datetime.now(UTC)
    return group


@pytest.fixture
def tool_groups_app():
    """App with tool_groups router."""
    return _make_test_app()


@pytest.fixture
async def tool_groups_client(tool_groups_app):
    """HTTP client for tool groups API."""
    async with AsyncClient(
        transport=ASGITransport(app=tool_groups_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
class TestToolGroupsAPI:
    """Tests for tool groups endpoints."""

    async def test_list_tool_groups_returns_items(
        self, tool_groups_client, mock_session, mock_tool_group
    ):
        """GET /api/v1/tool-groups returns list and total."""
        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[mock_tool_group])

        @asynccontextmanager
        async def _get_session():
            yield mock_session

        with (
            patch("src.api.routes.tool_groups.get_session", _get_session),
            patch(
                "src.api.routes.tool_groups.ToolGroupRepository",
                return_value=mock_repo,
            ),
        ):
            response = await tool_groups_client.get("/api/v1/tool-groups")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] == 1
        mock_repo.list_all.assert_called_once()

    async def test_list_tool_groups_empty(self, tool_groups_client, mock_session):
        """GET /api/v1/tool-groups returns empty list when no groups."""
        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[])

        @asynccontextmanager
        async def _get_session():
            yield mock_session

        with (
            patch("src.api.routes.tool_groups.get_session", _get_session),
            patch(
                "src.api.routes.tool_groups.ToolGroupRepository",
                return_value=mock_repo,
            ),
        ):
            response = await tool_groups_client.get("/api/v1/tool-groups")
        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    async def test_get_tool_group_found(self, tool_groups_client, mock_session, mock_tool_group):
        """GET /api/v1/tool-groups/{name} returns group when found."""
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_tool_group)

        @asynccontextmanager
        async def _get_session():
            yield mock_session

        with (
            patch("src.api.routes.tool_groups.get_session", _get_session),
            patch(
                "src.api.routes.tool_groups.ToolGroupRepository",
                return_value=mock_repo,
            ),
        ):
            response = await tool_groups_client.get("/api/v1/tool-groups/ha_entity_query")
        assert response.status_code == 200
        assert response.json()["name"] == "ha_entity_query"
        mock_repo.get_by_name.assert_called_once_with("ha_entity_query")

    async def test_get_tool_group_not_found(self, tool_groups_client, mock_session):
        """GET /api/v1/tool-groups/{name} returns 404 when not found."""
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=None)

        @asynccontextmanager
        async def _get_session():
            yield mock_session

        with (
            patch("src.api.routes.tool_groups.get_session", _get_session),
            patch(
                "src.api.routes.tool_groups.ToolGroupRepository",
                return_value=mock_repo,
            ),
        ):
            response = await tool_groups_client.get("/api/v1/tool-groups/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    async def test_create_tool_group_unknown_tool_returns_422(
        self, tool_groups_client, mock_session
    ):
        """POST with unknown tool name returns 422."""
        mock_tool = MagicMock()
        mock_tool.name = "known_tool"
        with patch(
            "src.api.routes.tool_groups._get_known_tool_names",
            return_value={"known_tool"},
        ):

            @asynccontextmanager
            async def _get_session():
                yield mock_session

            with patch("src.api.routes.tool_groups.get_session", _get_session):
                response = await tool_groups_client.post(
                    "/api/v1/tool-groups",
                    json={
                        "name": "my_group",
                        "display_name": "My Group",
                        "tool_names": ["unknown_tool"],
                        "is_read_only": True,
                    },
                )
        assert response.status_code == 422
        assert (
            "Unknown tool" in response.json().get("detail", "")
            or "unknown" in response.json().get("detail", "").lower()
        )

    async def test_create_tool_group_success(
        self, tool_groups_client, mock_session, mock_tool_group
    ):
        """POST with valid payload creates group and returns 201."""
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=mock_tool_group)
        with patch(
            "src.api.routes.tool_groups._get_known_tool_names",
            return_value={"get_entities", "get_states"},
        ):

            @asynccontextmanager
            async def _get_session():
                yield mock_session

            with (
                patch("src.api.routes.tool_groups.get_session", _get_session),
                patch(
                    "src.api.routes.tool_groups.ToolGroupRepository",
                    return_value=mock_repo,
                ),
            ):
                response = await tool_groups_client.post(
                    "/api/v1/tool-groups",
                    json={
                        "name": "my_group",
                        "display_name": "My Group",
                        "tool_names": ["get_entities", "get_states"],
                        "is_read_only": True,
                    },
                )
        assert response.status_code == 201
        mock_repo.create.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_update_tool_group_not_found(self, tool_groups_client, mock_session):
        """PUT when group not found returns 404."""
        mock_repo = MagicMock()
        mock_repo.update = AsyncMock(return_value=None)
        with patch(
            "src.api.routes.tool_groups._get_known_tool_names",
            return_value=set(),
        ):

            @asynccontextmanager
            async def _get_session():
                yield mock_session

            with (
                patch("src.api.routes.tool_groups.get_session", _get_session),
                patch(
                    "src.api.routes.tool_groups.ToolGroupRepository",
                    return_value=mock_repo,
                ),
            ):
                response = await tool_groups_client.put(
                    "/api/v1/tool-groups/nonexistent",
                    json={"display_name": "Updated"},
                )
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()
        mock_repo.update.assert_called_once()
