"""Tests for Workflow Definition CRUD API (Feature 29).

POST/GET/PUT/DELETE /api/v1/workflows/definitions
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter


def _make_test_app():
    from fastapi import FastAPI

    from src.api.routes.workflow_definitions import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    return app


@pytest.fixture()
def app():
    return _make_test_app()


@pytest.fixture()
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _mock_session_ctx():
    @asynccontextmanager
    async def _ctx():
        yield AsyncMock()

    return _ctx()


def _make_entity(**overrides):
    from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

    defaults = {
        "id": str(uuid4()),
        "name": "test-workflow",
        "description": "A test workflow",
        "state_type": "ConversationState",
        "version": 1,
        "status": "draft",
        "config": {"nodes": [{"id": "a", "function": "node_a"}], "edges": []},
        "intent_patterns": [],
        "created_by": None,
    }
    defaults.update(overrides)
    entity = WorkflowDefinitionEntity(**defaults)
    entity.created_at = datetime.now(UTC)
    entity.updated_at = datetime.now(UTC)
    return entity


class TestCreateWorkflowDefinition:
    """POST /api/v1/workflows/definitions creates a workflow."""

    @pytest.mark.asyncio()
    async def test_create_returns_201(self, client):
        entity = _make_entity()
        mock_create = AsyncMock(return_value=entity)
        mock_compiler = MagicMock()
        mock_compiler.validate = MagicMock(return_value=[])

        with (
            patch("src.api.routes.workflow_definitions.get_session") as mock_s,
            patch("src.api.routes.workflow_definitions._create_definition", mock_create),
            patch("src.graph.workflows.compiler.WorkflowCompiler") as mock_compiler_cls,
            patch("src.graph.workflows.manifest.get_default_manifest"),
        ):
            mock_compiler_cls.return_value.validate.return_value = []
            mock_s.return_value = _mock_session_ctx()
            resp = await client.post(
                "/api/v1/workflows/definitions",
                json={
                    "name": "test-workflow",
                    "description": "A test",
                    "state_type": "ConversationState",
                    "nodes": [{"id": "a", "function": "node_a"}],
                    "edges": [{"source": "__start__", "target": "a"}],
                },
            )

        assert resp.status_code == 201
        assert resp.json()["name"] == "test-workflow"


class TestListWorkflowDefinitions:
    """GET /api/v1/workflows/definitions lists all definitions."""

    @pytest.mark.asyncio()
    async def test_list_returns_200(self, client):
        entities = [_make_entity(name="wf-1"), _make_entity(name="wf-2")]
        mock_list = AsyncMock(return_value=entities)

        with patch("src.api.routes.workflow_definitions.get_session") as mock_s:
            mock_s.return_value = _mock_session_ctx()
            with patch("src.api.routes.workflow_definitions._list_definitions", mock_list):
                resp = await client.get("/api/v1/workflows/definitions")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["definitions"]) == 2


class TestGetWorkflowDefinition:
    """GET /api/v1/workflows/definitions/{id} returns one definition."""

    @pytest.mark.asyncio()
    async def test_get_returns_200(self, client):
        entity = _make_entity()
        mock_get = AsyncMock(return_value=entity)

        with patch("src.api.routes.workflow_definitions.get_session") as mock_s:
            mock_s.return_value = _mock_session_ctx()
            with patch("src.api.routes.workflow_definitions._get_definition", mock_get):
                resp = await client.get(f"/api/v1/workflows/definitions/{entity.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == entity.id

    @pytest.mark.asyncio()
    async def test_get_returns_404_when_not_found(self, client):
        mock_get = AsyncMock(return_value=None)

        with patch("src.api.routes.workflow_definitions.get_session") as mock_s:
            mock_s.return_value = _mock_session_ctx()
            with patch("src.api.routes.workflow_definitions._get_definition", mock_get):
                resp = await client.get(f"/api/v1/workflows/definitions/{uuid4()}")

        assert resp.status_code == 404


class TestDeleteWorkflowDefinition:
    """DELETE /api/v1/workflows/definitions/{id} soft-deletes."""

    @pytest.mark.asyncio()
    async def test_delete_returns_200(self, client):
        entity = _make_entity()
        mock_get = AsyncMock(return_value=entity)
        mock_delete = AsyncMock(return_value=True)

        with patch("src.api.routes.workflow_definitions.get_session") as mock_s:
            mock_s.return_value = _mock_session_ctx()
            with (
                patch("src.api.routes.workflow_definitions._get_definition", mock_get),
                patch("src.api.routes.workflow_definitions._delete_definition", mock_delete),
            ):
                resp = await client.delete(f"/api/v1/workflows/definitions/{entity.id}")

        assert resp.status_code == 200
