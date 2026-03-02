"""Unit tests for Settings API routes.

Tests GET/PATCH/POST /api/v1/settings with mocked get_session and repository.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.dal.app_settings import SECTION_DEFAULTS


def _make_test_app():
    """Create a minimal FastAPI app with the settings router."""
    from fastapi import FastAPI

    from src.api.routes.settings import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def settings_app():
    """App with settings router."""
    return _make_test_app()


@pytest.fixture
async def settings_client(settings_app):
    """HTTP client for settings API."""
    async with AsyncClient(
        transport=ASGITransport(app=settings_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
class TestSettingsAPI:
    """Tests for settings endpoints."""

    async def test_get_settings_returns_merged(self, settings_client, mock_session):
        """GET /api/v1/settings returns merged settings with defaults."""
        merged = {s: dict(d) for s, d in SECTION_DEFAULTS.items()}
        mock_repo = MagicMock()
        mock_repo.get_merged = AsyncMock(return_value=merged)

        @asynccontextmanager
        async def _get_session():
            yield mock_session

        with (
            patch("src.api.routes.settings.get_session", _get_session),
            patch(
                "src.api.routes.settings.AppSettingsRepository",
                return_value=mock_repo,
            ),
        ):
            response = await settings_client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert "chat" in data
        assert "dashboard" in data
        assert "data_science" in data
        assert "notifications" in data
        mock_repo.get_merged.assert_called_once()

    async def test_patch_empty_body_returns_400(self, settings_client):
        """PATCH with no sections returns 400."""

        @asynccontextmanager
        async def _get_session():
            yield MagicMock()

        with patch("src.api.routes.settings.get_session", _get_session):
            response = await settings_client.patch(
                "/api/v1/settings",
                json={},
            )
        assert response.status_code == 400
        assert "No sections to update" in response.json().get("detail", "")

    async def test_patch_validation_error_returns_422(self, settings_client):
        """PATCH with invalid value (e.g. min_impact) returns 422."""

        @asynccontextmanager
        async def _get_session():
            yield MagicMock()

        with patch("src.api.routes.settings.get_session", _get_session):
            response = await settings_client.patch(
                "/api/v1/settings",
                json={"notifications": {"min_impact": "invalid_level"}},
            )
        assert response.status_code == 422
        assert "detail" in response.json()

    async def test_patch_valid_updates_and_returns_merged(self, settings_client, mock_session):
        """PATCH with valid section updates and returns merged settings."""
        merged = {s: dict(d) for s, d in SECTION_DEFAULTS.items()}
        merged["chat"] = {**merged["chat"], "stream_timeout_seconds": 600}
        mock_repo = MagicMock()
        mock_repo.update_section = AsyncMock(return_value=merged)
        mock_repo.get_merged = AsyncMock(return_value=merged)

        @asynccontextmanager
        async def _get_session():
            yield mock_session

        with (
            patch("src.api.routes.settings.get_session", _get_session),
            patch(
                "src.api.routes.settings.AppSettingsRepository",
                return_value=mock_repo,
            ),
        ):
            response = await settings_client.patch(
                "/api/v1/settings",
                json={"chat": {"stream_timeout_seconds": 600}},
            )
        assert response.status_code == 200
        assert response.json()["chat"]["stream_timeout_seconds"] == 600

    async def test_reset_unknown_section_returns_400(self, settings_client):
        """POST /reset with unknown section returns 400."""

        @asynccontextmanager
        async def _get_session():
            yield MagicMock()

        with patch("src.api.routes.settings.get_session", _get_session):
            response = await settings_client.post(
                "/api/v1/settings/reset",
                json={"section": "invalid_section"},
            )
        assert response.status_code == 400
        assert "Unknown section" in response.json().get("detail", "")

    async def test_reset_valid_section_returns_merged(self, settings_client, mock_session):
        """POST /reset with valid section resets and returns merged."""
        merged = {s: dict(d) for s, d in SECTION_DEFAULTS.items()}
        mock_repo = MagicMock()
        mock_repo.reset_section = AsyncMock(return_value=merged)

        @asynccontextmanager
        async def _get_session():
            yield mock_session

        with (
            patch("src.api.routes.settings.get_session", _get_session),
            patch(
                "src.api.routes.settings.AppSettingsRepository",
                return_value=mock_repo,
            ),
        ):
            response = await settings_client.post(
                "/api/v1/settings/reset",
                json={"section": "chat"},
            )
        assert response.status_code == 200
        mock_repo.reset_section.assert_called_once_with("chat")
