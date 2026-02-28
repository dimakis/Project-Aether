"""Unit tests for HA Registry API routes.

Tests GET/POST endpoints for automations, scripts, scenes, and services
with mock repositories -- no real database or app lifespan needed.

The get_db dependency is overridden with a mock AsyncSession so
the test never attempts a real Postgres connection (which would
hang indefinitely in a unit-test environment).
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Deterministic UUIDs for test fixtures
_AUTO_UUID = str(uuid.UUID("00000000-0000-0000-0000-000000000001"))
_SCRIPT_UUID = str(uuid.UUID("00000000-0000-0000-0000-000000000002"))
_SCENE_UUID = str(uuid.UUID("00000000-0000-0000-0000-000000000003"))
_SERVICE_UUID = str(uuid.UUID("00000000-0000-0000-0000-000000000004"))

from src.api.routes.ha_registry import get_db


def _make_test_app():
    """Create a minimal FastAPI app with the registry router and mock DB."""
    from fastapi import FastAPI
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    from src.api.rate_limit import limiter
    from src.api.routes.ha_registry import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/registry")

    # Attach the SAME limiter instance and error handler used in production
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Override get_db so no real Postgres connection is attempted
    async def _mock_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _mock_get_db
    return app


@pytest.fixture
def registry_app():
    """Lightweight FastAPI app with registry routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def registry_client(registry_app):
    """Async HTTP client wired to the registry test app."""
    async with AsyncClient(
        transport=ASGITransport(app=registry_app),
        base_url="http://test",
    ) as client:
        yield client


# =============================================================================
# FIXTURES: Mock Models
# =============================================================================


@pytest.fixture
def mock_automation():
    """Create a mock Automation object."""
    automation = MagicMock()
    automation.id = _AUTO_UUID
    automation.ha_automation_id = "auto_123"
    automation.entity_id = "automation.test_automation"
    automation.alias = "Test Automation"
    automation.state = "on"
    automation.description = "Test description"
    automation.mode = "single"
    automation.trigger_types = ["state"]
    automation.trigger_count = 1
    automation.action_count = 2
    automation.condition_count = 0
    automation.last_triggered = None
    automation.last_synced_at = datetime(2026, 2, 4, 12, 0, 0)
    automation.config = {"trigger": [], "action": []}
    return automation


@pytest.fixture
def mock_script():
    """Create a mock Script object."""
    script = MagicMock()
    script.id = _SCRIPT_UUID
    script.entity_id = "script.test_script"
    script.alias = "Test Script"
    script.state = "off"
    script.description = "Test script description"
    script.mode = "single"
    script.icon = "mdi:script"
    script.last_triggered = None
    script.last_synced_at = datetime(2026, 2, 4, 12, 0, 0)
    script.fields = None  # Real dict or None, not MagicMock
    return script


@pytest.fixture
def mock_scene():
    """Create a mock Scene object."""
    scene = MagicMock()
    scene.id = _SCENE_UUID
    scene.entity_id = "scene.test_scene"
    scene.name = "Test Scene"
    scene.icon = "mdi:palette"
    scene.last_synced_at = datetime(2026, 2, 4, 12, 0, 0)
    scene.entity_states = None
    return scene


@pytest.fixture
def mock_service():
    """Create a mock Service object."""
    service = MagicMock()
    service.id = _SERVICE_UUID
    service.domain = "light"
    service.service = "turn_on"
    service.name = "Turn On"
    service.description = "Turn on a light"
    service.fields = {"entity_id": {"required": True}}
    service.target = None
    service.is_seeded = False
    return service


# =============================================================================
# FIXTURES: Mock Repositories
# =============================================================================


@pytest.fixture
def mock_automation_repo(mock_automation):
    """Create mock AutomationRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_automation])
    repo.count = AsyncMock(return_value=1)
    repo.get_by_id = AsyncMock(return_value=mock_automation)
    repo.get_by_ha_automation_id = AsyncMock(return_value=mock_automation)
    repo.get_by_entity_id = AsyncMock(return_value=mock_automation)
    return repo


@pytest.fixture
def mock_script_repo(mock_script):
    """Create mock ScriptRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_script])
    repo.count = AsyncMock(return_value=1)
    repo.get_by_id = AsyncMock(return_value=mock_script)
    repo.get_by_entity_id = AsyncMock(return_value=mock_script)
    return repo


@pytest.fixture
def mock_scene_repo(mock_scene):
    """Create mock SceneRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_scene])
    repo.count = AsyncMock(return_value=1)
    repo.get_by_id = AsyncMock(return_value=mock_scene)
    repo.get_by_entity_id = AsyncMock(return_value=mock_scene)
    return repo


@pytest.fixture
def mock_service_repo(mock_service):
    """Create mock ServiceRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[mock_service])
    repo.count = AsyncMock(return_value=1)
    repo.get_by_id = AsyncMock(return_value=mock_service)
    repo.get_service_info = AsyncMock(return_value=mock_service)
    repo.get_domains = AsyncMock(return_value=["light", "switch"])
    return repo


# =============================================================================
# TESTS: Automations
# =============================================================================


@pytest.mark.asyncio
class TestListAutomations:
    """Tests for GET /api/v1/registry/automations."""

    async def test_list_automations_returns_paginated_results(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should return automations with total and enabled/disabled counts."""
        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository",
            return_value=mock_automation_repo,
        ):
            response = await registry_client.get("/api/v1/registry/automations")

            assert response.status_code == 200
            data = response.json()
            assert "automations" in data
            assert data["total"] == 1
            assert len(data["automations"]) == 1
            assert data["automations"][0]["entity_id"] == "automation.test_automation"
            assert data["automations"][0]["alias"] == "Test Automation"
            assert "enabled_count" in data
            assert "disabled_count" in data

    async def test_list_automations_with_state_filter(self, registry_client, mock_automation_repo):
        """Should pass state filter to repository."""
        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository",
            return_value=mock_automation_repo,
        ):
            response = await registry_client.get("/api/v1/registry/automations?state=on")

            assert response.status_code == 200
            mock_automation_repo.list_all.assert_called_once()
            call_kwargs = mock_automation_repo.list_all.call_args[1]
            assert call_kwargs["state"] == "on"

    async def test_list_automations_with_pagination(self, registry_client, mock_automation_repo):
        """Should pass limit and offset to repository."""
        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository",
            return_value=mock_automation_repo,
        ):
            response = await registry_client.get("/api/v1/registry/automations?limit=10&offset=5")

            assert response.status_code == 200
            call_kwargs = mock_automation_repo.list_all.call_args[1]
            assert call_kwargs["limit"] == 10
            assert call_kwargs["offset"] == 5

    async def test_list_automations_empty(self, registry_client):
        """Should return empty list when no automations exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository", return_value=repo
        ):
            response = await registry_client.get("/api/v1/registry/automations")

            assert response.status_code == 200
            data = response.json()
            assert data["automations"] == []
            assert data["total"] == 0
            assert data["enabled_count"] == 0
            assert data["disabled_count"] == 0


@pytest.mark.asyncio
class TestGetAutomation:
    """Tests for GET /api/v1/registry/automations/{automation_id}."""

    async def test_get_automation_by_internal_id(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should find automation by internal UUID."""
        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository",
            return_value=mock_automation_repo,
        ):
            response = await registry_client.get(f"/api/v1/registry/automations/{_AUTO_UUID}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == _AUTO_UUID
            assert data["entity_id"] == "automation.test_automation"
            mock_automation_repo.get_by_id.assert_called_once_with(_AUTO_UUID)

    async def test_get_automation_by_ha_id(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should fall back to HA automation ID when internal ID not found."""
        mock_automation_repo.get_by_id = AsyncMock(return_value=None)
        mock_automation_repo.get_by_ha_automation_id = AsyncMock(return_value=mock_automation)

        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository",
            return_value=mock_automation_repo,
        ):
            response = await registry_client.get("/api/v1/registry/automations/auto_123")

            assert response.status_code == 200
            mock_automation_repo.get_by_ha_automation_id.assert_called_once_with("auto_123")

    async def test_get_automation_by_entity_id(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should fall back to entity ID when other methods fail."""
        mock_automation_repo.get_by_id = AsyncMock(return_value=None)
        mock_automation_repo.get_by_ha_automation_id = AsyncMock(return_value=None)
        mock_automation_repo.get_by_entity_id = AsyncMock(return_value=mock_automation)

        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository",
            return_value=mock_automation_repo,
        ):
            response = await registry_client.get("/api/v1/registry/automations/test_automation")

            assert response.status_code == 200
            mock_automation_repo.get_by_entity_id.assert_called_once_with(
                "automation.test_automation"
            )

    async def test_get_automation_not_found(self, registry_client):
        """Should return 404 when automation not found."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        repo.get_by_ha_automation_id = AsyncMock(return_value=None)
        repo.get_by_entity_id = AsyncMock(return_value=None)

        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository", return_value=repo
        ):
            response = await registry_client.get("/api/v1/registry/automations/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestGetAutomationConfig:
    """Tests for GET /api/v1/registry/automations/{automation_id}/config."""

    async def test_get_automation_config_success(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should return automation config from HA."""
        mock_config = {"trigger": [{"platform": "state"}], "action": [{"service": "test"}]}
        mock_ha_client = MagicMock()
        mock_ha_client.get_automation_config = AsyncMock(return_value=mock_config)

        with (
            patch(
                "src.api.routes.ha_registry.automations.AutomationRepository",
                return_value=mock_automation_repo,
            ),
            patch(
                "src.ha.get_ha_client_async",
                new_callable=AsyncMock,
                return_value=mock_ha_client,
            ),
        ):
            response = await registry_client.get(
                f"/api/v1/registry/automations/{_AUTO_UUID}/config"
            )

            assert response.status_code == 200
            data = response.json()
            assert "config" in data
            assert "yaml" in data
            assert data["automation_id"] == _AUTO_UUID
            assert data["ha_automation_id"] == "auto_123"
            assert data["entity_id"] == "automation.test_automation"

    async def test_get_automation_config_fallback_to_db(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should fall back to DB config when HA returns None."""
        mock_config = {"trigger": [], "action": []}
        mock_automation.config = mock_config
        mock_ha_client = MagicMock()
        mock_ha_client.get_automation_config = AsyncMock(return_value=None)

        with (
            patch(
                "src.api.routes.ha_registry.automations.AutomationRepository",
                return_value=mock_automation_repo,
            ),
            patch(
                "src.ha.get_ha_client_async",
                new_callable=AsyncMock,
                return_value=mock_ha_client,
            ),
        ):
            response = await registry_client.get(
                f"/api/v1/registry/automations/{_AUTO_UUID}/config"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["config"] == mock_config

    async def test_get_automation_config_not_found(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should return 404 when automation not found."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        repo.get_by_ha_automation_id = AsyncMock(return_value=None)
        repo.get_by_entity_id = AsyncMock(return_value=None)

        with patch(
            "src.api.routes.ha_registry.automations.AutomationRepository", return_value=repo
        ):
            response = await registry_client.get("/api/v1/registry/automations/nonexistent/config")

            assert response.status_code == 404

    async def test_get_automation_config_ha_error(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should return 502 when HA client fails."""
        mock_ha_client = MagicMock()
        mock_ha_client.get_automation_config = AsyncMock(
            side_effect=Exception("HA connection failed")
        )

        with (
            patch(
                "src.api.routes.ha_registry.automations.AutomationRepository",
                return_value=mock_automation_repo,
            ),
            patch(
                "src.ha.get_ha_client_async",
                new_callable=AsyncMock,
                return_value=mock_ha_client,
            ),
        ):
            response = await registry_client.get(
                f"/api/v1/registry/automations/{_AUTO_UUID}/config"
            )

            assert response.status_code == 502
            assert "HA connection failed" in response.json()["detail"]

    async def test_get_automation_config_no_config_available(
        self, registry_client, mock_automation_repo, mock_automation
    ):
        """Should return 404 when no config available from HA or DB."""
        mock_automation.config = None
        mock_ha_client = MagicMock()
        mock_ha_client.get_automation_config = AsyncMock(return_value=None)

        with (
            patch(
                "src.api.routes.ha_registry.automations.AutomationRepository",
                return_value=mock_automation_repo,
            ),
            patch(
                "src.ha.get_ha_client_async",
                new_callable=AsyncMock,
                return_value=mock_ha_client,
            ),
        ):
            response = await registry_client.get(
                f"/api/v1/registry/automations/{_AUTO_UUID}/config"
            )

            assert response.status_code == 404
            assert "not available" in response.json()["detail"].lower()


# =============================================================================
# TESTS: Scripts
# =============================================================================


@pytest.mark.asyncio
class TestListScripts:
    """Tests for GET /api/v1/registry/scripts."""

    async def test_list_scripts_returns_paginated_results(
        self, registry_client, mock_script_repo, mock_script
    ):
        """Should return scripts with total and running count."""
        with patch(
            "src.api.routes.ha_registry.scripts.ScriptRepository", return_value=mock_script_repo
        ):
            response = await registry_client.get("/api/v1/registry/scripts")

            assert response.status_code == 200
            data = response.json()
            assert "scripts" in data
            assert data["total"] == 1
            assert len(data["scripts"]) == 1
            assert data["scripts"][0]["entity_id"] == "script.test_script"
            assert data["scripts"][0]["alias"] == "Test Script"
            assert "running_count" in data

    async def test_list_scripts_with_state_filter(self, registry_client, mock_script_repo):
        """Should pass state filter to repository."""
        with patch(
            "src.api.routes.ha_registry.scripts.ScriptRepository", return_value=mock_script_repo
        ):
            response = await registry_client.get("/api/v1/registry/scripts?state=on")

            assert response.status_code == 200
            # list_all is called twice: once with state filter, once with state="on" for running_count
            assert mock_script_repo.list_all.call_count == 2
            # Check the first call (with the state filter)
            call_kwargs = mock_script_repo.list_all.call_args_list[0][1]
            assert call_kwargs["state"] == "on"

    async def test_list_scripts_empty(self, registry_client):
        """Should return empty list when no scripts exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with patch("src.api.routes.ha_registry.scripts.ScriptRepository", return_value=repo):
            response = await registry_client.get("/api/v1/registry/scripts")

            assert response.status_code == 200
            data = response.json()
            assert data["scripts"] == []
            assert data["total"] == 0
            assert data["running_count"] == 0


@pytest.mark.asyncio
class TestGetScript:
    """Tests for GET /api/v1/registry/scripts/{script_id}."""

    async def test_get_script_by_internal_id(self, registry_client, mock_script_repo, mock_script):
        """Should find script by internal UUID."""
        with patch(
            "src.api.routes.ha_registry.scripts.ScriptRepository", return_value=mock_script_repo
        ):
            response = await registry_client.get(f"/api/v1/registry/scripts/{_SCRIPT_UUID}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == _SCRIPT_UUID
            assert data["entity_id"] == "script.test_script"
            mock_script_repo.get_by_id.assert_called_once_with(_SCRIPT_UUID)

    async def test_get_script_by_entity_id(self, registry_client, mock_script_repo, mock_script):
        """Should fall back to entity ID when internal ID not found."""
        mock_script_repo.get_by_id = AsyncMock(return_value=None)
        mock_script_repo.get_by_entity_id = AsyncMock(return_value=mock_script)

        with patch(
            "src.api.routes.ha_registry.scripts.ScriptRepository", return_value=mock_script_repo
        ):
            response = await registry_client.get("/api/v1/registry/scripts/test_script")

            assert response.status_code == 200
            mock_script_repo.get_by_entity_id.assert_called_once_with("script.test_script")

    async def test_get_script_with_script_prefix(
        self, registry_client, mock_script_repo, mock_script
    ):
        """Should handle entity ID with script. prefix."""
        mock_script_repo.get_by_id = AsyncMock(return_value=None)
        mock_script_repo.get_by_entity_id = AsyncMock(return_value=mock_script)

        with patch(
            "src.api.routes.ha_registry.scripts.ScriptRepository", return_value=mock_script_repo
        ):
            response = await registry_client.get("/api/v1/registry/scripts/script.test_script")

            assert response.status_code == 200
            mock_script_repo.get_by_entity_id.assert_called_once_with("script.test_script")

    async def test_get_script_not_found(self, registry_client):
        """Should return 404 when script not found."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        repo.get_by_entity_id = AsyncMock(return_value=None)

        with patch("src.api.routes.ha_registry.scripts.ScriptRepository", return_value=repo):
            response = await registry_client.get("/api/v1/registry/scripts/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


# =============================================================================
# TESTS: Scenes
# =============================================================================


@pytest.mark.asyncio
class TestListScenes:
    """Tests for GET /api/v1/registry/scenes."""

    async def test_list_scenes_returns_paginated_results(
        self, registry_client, mock_scene_repo, mock_scene
    ):
        """Should return scenes with total count."""
        with patch(
            "src.api.routes.ha_registry.scenes.SceneRepository", return_value=mock_scene_repo
        ):
            response = await registry_client.get("/api/v1/registry/scenes")

            assert response.status_code == 200
            data = response.json()
            assert "scenes" in data
            assert data["total"] == 1
            assert len(data["scenes"]) == 1
            assert data["scenes"][0]["entity_id"] == "scene.test_scene"
            assert data["scenes"][0]["name"] == "Test Scene"

    async def test_list_scenes_with_pagination(self, registry_client, mock_scene_repo):
        """Should pass limit and offset to repository."""
        with patch(
            "src.api.routes.ha_registry.scenes.SceneRepository", return_value=mock_scene_repo
        ):
            response = await registry_client.get("/api/v1/registry/scenes?limit=10&offset=5")

            assert response.status_code == 200
            call_kwargs = mock_scene_repo.list_all.call_args[1]
            assert call_kwargs["limit"] == 10
            assert call_kwargs["offset"] == 5

    async def test_list_scenes_empty(self, registry_client):
        """Should return empty list when no scenes exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)

        with patch("src.api.routes.ha_registry.scenes.SceneRepository", return_value=repo):
            response = await registry_client.get("/api/v1/registry/scenes")

            assert response.status_code == 200
            data = response.json()
            assert data["scenes"] == []
            assert data["total"] == 0


@pytest.mark.asyncio
class TestGetScene:
    """Tests for GET /api/v1/registry/scenes/{scene_id}."""

    async def test_get_scene_by_internal_id(self, registry_client, mock_scene_repo, mock_scene):
        """Should find scene by internal UUID."""
        with patch(
            "src.api.routes.ha_registry.scenes.SceneRepository", return_value=mock_scene_repo
        ):
            response = await registry_client.get(f"/api/v1/registry/scenes/{_SCENE_UUID}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == _SCENE_UUID
            assert data["entity_id"] == "scene.test_scene"
            mock_scene_repo.get_by_id.assert_called_once_with(_SCENE_UUID)

    async def test_get_scene_by_entity_id(self, registry_client, mock_scene_repo, mock_scene):
        """Should fall back to entity ID when internal ID not found."""
        mock_scene_repo.get_by_id = AsyncMock(return_value=None)
        mock_scene_repo.get_by_entity_id = AsyncMock(return_value=mock_scene)

        with patch(
            "src.api.routes.ha_registry.scenes.SceneRepository", return_value=mock_scene_repo
        ):
            response = await registry_client.get("/api/v1/registry/scenes/test_scene")

            assert response.status_code == 200
            mock_scene_repo.get_by_entity_id.assert_called_once_with("scene.test_scene")

    async def test_get_scene_with_scene_prefix(self, registry_client, mock_scene_repo, mock_scene):
        """Should handle entity ID with scene. prefix."""
        mock_scene_repo.get_by_id = AsyncMock(return_value=None)
        mock_scene_repo.get_by_entity_id = AsyncMock(return_value=mock_scene)

        with patch(
            "src.api.routes.ha_registry.scenes.SceneRepository", return_value=mock_scene_repo
        ):
            response = await registry_client.get("/api/v1/registry/scenes/scene.test_scene")

            assert response.status_code == 200
            mock_scene_repo.get_by_entity_id.assert_called_once_with("scene.test_scene")

    async def test_get_scene_not_found(self, registry_client):
        """Should return 404 when scene not found."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        repo.get_by_entity_id = AsyncMock(return_value=None)

        with patch("src.api.routes.ha_registry.scenes.SceneRepository", return_value=repo):
            response = await registry_client.get("/api/v1/registry/scenes/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


# =============================================================================
# TESTS: Services
# =============================================================================


@pytest.mark.asyncio
class TestListServices:
    """Tests for GET /api/v1/registry/services."""

    async def test_list_services_returns_paginated_results(
        self, registry_client, mock_service_repo, mock_service
    ):
        """Should return services with total, domains, and seeded/discovered counts."""
        with patch(
            "src.api.routes.ha_registry.services.ServiceRepository", return_value=mock_service_repo
        ):
            response = await registry_client.get("/api/v1/registry/services")

            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert data["total"] == 1
            assert len(data["services"]) == 1
            assert data["services"][0]["domain"] == "light"
            assert data["services"][0]["service"] == "turn_on"
            assert "domains" in data
            assert "seeded_count" in data
            assert "discovered_count" in data

    async def test_list_services_with_domain_filter(self, registry_client, mock_service_repo):
        """Should pass domain filter to repository."""
        with patch(
            "src.api.routes.ha_registry.services.ServiceRepository", return_value=mock_service_repo
        ):
            response = await registry_client.get("/api/v1/registry/services?domain=light")

            assert response.status_code == 200
            mock_service_repo.list_all.assert_called_once()
            call_kwargs = mock_service_repo.list_all.call_args[1]
            assert call_kwargs["domain"] == "light"

    async def test_list_services_with_pagination(self, registry_client, mock_service_repo):
        """Should pass limit and offset to repository."""
        with patch(
            "src.api.routes.ha_registry.services.ServiceRepository", return_value=mock_service_repo
        ):
            response = await registry_client.get("/api/v1/registry/services?limit=50&offset=10")

            assert response.status_code == 200
            call_kwargs = mock_service_repo.list_all.call_args[1]
            assert call_kwargs["limit"] == 50
            assert call_kwargs["offset"] == 10

    async def test_list_services_empty(self, registry_client):
        """Should return empty list when no services exist."""
        repo = MagicMock()
        repo.list_all = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)
        repo.get_domains = AsyncMock(return_value=[])

        with patch("src.api.routes.ha_registry.services.ServiceRepository", return_value=repo):
            response = await registry_client.get("/api/v1/registry/services")

            assert response.status_code == 200
            data = response.json()
            assert data["services"] == []
            assert data["total"] == 0
            assert data["domains"] == []
            assert data["seeded_count"] == 0
            assert data["discovered_count"] == 0


@pytest.mark.asyncio
class TestGetService:
    """Tests for GET /api/v1/registry/services/{service_id}."""

    async def test_get_service_by_internal_id(
        self, registry_client, mock_service_repo, mock_service
    ):
        """Should find service by internal UUID."""
        with patch(
            "src.api.routes.ha_registry.services.ServiceRepository", return_value=mock_service_repo
        ):
            response = await registry_client.get(f"/api/v1/registry/services/{_SERVICE_UUID}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == _SERVICE_UUID
            assert data["domain"] == "light"
            assert data["service"] == "turn_on"
            mock_service_repo.get_by_id.assert_called_once_with(_SERVICE_UUID)

    async def test_get_service_by_full_name(self, registry_client, mock_service_repo, mock_service):
        """Should fall back to full service name when internal ID not found."""
        mock_service_repo.get_by_id = AsyncMock(return_value=None)
        mock_service_repo.get_service_info = AsyncMock(return_value=mock_service)

        with patch(
            "src.api.routes.ha_registry.services.ServiceRepository", return_value=mock_service_repo
        ):
            response = await registry_client.get("/api/v1/registry/services/light.turn_on")

            assert response.status_code == 200
            mock_service_repo.get_service_info.assert_called_once_with("light.turn_on")

    async def test_get_service_not_found(self, registry_client):
        """Should return 404 when service not found."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        repo.get_service_info = AsyncMock(return_value=None)

        with patch("src.api.routes.ha_registry.services.ServiceRepository", return_value=repo):
            response = await registry_client.get("/api/v1/registry/services/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestCallService:
    """Tests for POST /api/v1/registry/services/call."""

    async def test_call_service_success(self, registry_client, mock_service_repo, mock_service):
        """Should successfully call a service via HA client."""
        mock_ha_client = MagicMock()
        mock_ha_client.call_service = AsyncMock()

        with (
            patch(
                "src.api.routes.ha_registry.services.ServiceRepository",
                return_value=mock_service_repo,
            ),
            patch(
                "src.ha.get_ha_client_async",
                new_callable=AsyncMock,
                return_value=mock_ha_client,
            ),
        ):
            response = await registry_client.post(
                "/api/v1/registry/services/call",
                json={
                    "domain": "light",
                    "service": "turn_on",
                    "data": {"entity_id": "light.living_room"},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["domain"] == "light"
            assert data["service"] == "turn_on"
            mock_ha_client.call_service.assert_called_once_with(
                domain="light",
                service="turn_on",
                data={"entity_id": "light.living_room"},
            )

    async def test_call_service_without_data(
        self, registry_client, mock_service_repo, mock_service
    ):
        """Should call service with empty data dict when data not provided."""
        mock_ha_client = MagicMock()
        mock_ha_client.call_service = AsyncMock()

        with (
            patch(
                "src.api.routes.ha_registry.services.ServiceRepository",
                return_value=mock_service_repo,
            ),
            patch(
                "src.ha.get_ha_client_async",
                new_callable=AsyncMock,
                return_value=mock_ha_client,
            ),
        ):
            response = await registry_client.post(
                "/api/v1/registry/services/call",
                json={"domain": "light", "service": "turn_on"},
            )

            assert response.status_code == 200
            mock_ha_client.call_service.assert_called_once_with(
                domain="light", service="turn_on", data={}
            )

    async def test_call_service_blocked_domain(
        self, registry_client, mock_service_repo, mock_service
    ):
        """Should block calls to dangerous domains."""
        with patch(
            "src.api.routes.ha_registry.services.ServiceRepository", return_value=mock_service_repo
        ):
            response = await registry_client.post(
                "/api/v1/registry/services/call",
                json={"domain": "homeassistant", "service": "restart"},
            )

            assert response.status_code == 403
            data = response.json()
            assert "restricted" in data["detail"].lower()

    async def test_call_service_ha_error(self, registry_client, mock_service_repo, mock_service):
        """Should return error response when HA client fails."""
        mock_ha_client = MagicMock()
        mock_ha_client.call_service = AsyncMock(side_effect=Exception("HA error"))

        with (
            patch(
                "src.api.routes.ha_registry.services.ServiceRepository",
                return_value=mock_service_repo,
            ),
            patch(
                "src.ha.get_ha_client_async",
                new_callable=AsyncMock,
                return_value=mock_ha_client,
            ),
        ):
            response = await registry_client.post(
                "/api/v1/registry/services/call",
                json={"domain": "light", "service": "turn_on"},
            )

            assert response.status_code == 502
            data = response.json()
            assert "HA error" in data["detail"]


@pytest.mark.asyncio
class TestSeedServices:
    """Tests for POST /api/v1/registry/services/seed."""

    async def test_seed_services_success(self, registry_client):
        """Should seed services and return statistics."""
        mock_stats = {"added": 10, "skipped": 5}
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        async def _mock_get_db():
            yield mock_session

        from src.api.routes.ha_registry import get_db

        registry_app = _make_test_app()
        registry_app.dependency_overrides[get_db] = _mock_get_db

        async with AsyncClient(
            transport=ASGITransport(app=registry_app),
            base_url="http://test",
        ) as client:
            # seed_services is imported inline from src.dal, so patch at source
            mock_seed = AsyncMock(return_value=mock_stats)
            with patch("src.dal.seed_services", mock_seed):
                response = await client.post("/api/v1/registry/services/seed")

                assert response.status_code == 200
                data = response.json()
                assert data["added"] == 10
                assert data["skipped"] == 5
                mock_seed.assert_called_once_with(mock_session)
                mock_session.commit.assert_called_once()


# =============================================================================
# TESTS: Registry Summary
# =============================================================================


@pytest.mark.asyncio
class TestGetRegistrySummary:
    """Tests for GET /api/v1/registry/summary."""

    async def test_get_registry_summary_success(
        self,
        registry_client,
        mock_automation_repo,
        mock_script_repo,
        mock_scene_repo,
        mock_service_repo,
    ):
        """Should return summary with counts for all registry types."""

        # Setup mocks with proper side effects for count
        def automation_count_side_effect(state=None):
            if state == "on":
                return 3
            return 5

        mock_automation_repo.count = AsyncMock(side_effect=automation_count_side_effect)
        mock_script_repo.count = AsyncMock(return_value=2)
        mock_scene_repo.count = AsyncMock(return_value=3)
        mock_service_repo.count = AsyncMock(return_value=10)

        # Create seeded and discovered services
        seeded_service = MagicMock()
        seeded_service.domain = "light"
        seeded_service.service = "turn_on"
        seeded_service.is_seeded = True
        seeded_service.fields = None  # Real dict or None, not MagicMock
        discovered_service = MagicMock()
        discovered_service.domain = "switch"
        discovered_service.service = "toggle"
        discovered_service.is_seeded = False
        discovered_service.fields = None  # Real dict or None, not MagicMock
        mock_service_repo.list_all = AsyncMock(return_value=[seeded_service, discovered_service])

        # Mock DiscoverySession query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=datetime(2026, 2, 4, 12, 0, 0))
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _mock_get_db():
            yield mock_session

        from src.api.routes.ha_registry import get_db

        registry_app = _make_test_app()
        registry_app.dependency_overrides[get_db] = _mock_get_db

        async with AsyncClient(
            transport=ASGITransport(app=registry_app),
            base_url="http://test",
        ) as client:
            with (
                patch(
                    "src.api.routes.ha_registry.summary.AutomationRepository",
                    return_value=mock_automation_repo,
                ),
                patch(
                    "src.api.routes.ha_registry.summary.ScriptRepository",
                    return_value=mock_script_repo,
                ),
                patch(
                    "src.api.routes.ha_registry.summary.SceneRepository",
                    return_value=mock_scene_repo,
                ),
                patch(
                    "src.api.routes.ha_registry.summary.ServiceRepository",
                    return_value=mock_service_repo,
                ),
            ):
                response = await client.get("/api/v1/registry/summary")

                assert response.status_code == 200
                data = response.json()
                assert data["automations_count"] == 5
                assert data["automations_enabled"] == 3
                assert data["scripts_count"] == 2
                assert data["scenes_count"] == 3
                assert data["services_count"] == 10
                assert data["services_seeded"] == 1
                assert data["last_synced_at"] is not None
                assert "mcp_gaps" in data
                assert isinstance(data["mcp_gaps"], list)

    async def test_get_registry_summary_no_last_sync(
        self,
        registry_client,
        mock_automation_repo,
        mock_script_repo,
        mock_scene_repo,
        mock_service_repo,
    ):
        """Should return summary with None for last_synced_at when no sync exists."""
        mock_automation_repo.count = AsyncMock(return_value=0)
        mock_script_repo.count = AsyncMock(return_value=0)
        mock_scene_repo.count = AsyncMock(return_value=0)
        mock_service_repo.count = AsyncMock(return_value=0)
        mock_service_repo.list_all = AsyncMock(return_value=[])

        # Mock DiscoverySession query returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _mock_get_db():
            yield mock_session

        from src.api.routes.ha_registry import get_db

        registry_app = _make_test_app()
        registry_app.dependency_overrides[get_db] = _mock_get_db

        async with AsyncClient(
            transport=ASGITransport(app=registry_app),
            base_url="http://test",
        ) as client:
            with (
                patch(
                    "src.api.routes.ha_registry.summary.AutomationRepository",
                    return_value=mock_automation_repo,
                ),
                patch(
                    "src.api.routes.ha_registry.summary.ScriptRepository",
                    return_value=mock_script_repo,
                ),
                patch(
                    "src.api.routes.ha_registry.summary.SceneRepository",
                    return_value=mock_scene_repo,
                ),
                patch(
                    "src.api.routes.ha_registry.summary.ServiceRepository",
                    return_value=mock_service_repo,
                ),
            ):
                response = await client.get("/api/v1/registry/summary")

                assert response.status_code == 200
                data = response.json()
                assert data["last_synced_at"] is None
                assert data["automations_count"] == 0
                assert data["scripts_count"] == 0
