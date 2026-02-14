"""Unit tests for Agent Configuration API routes.

Feature 23: Agent Configuration Page.
Comprehensive tests for all agent endpoints with mock repositories.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.rate_limit import limiter
from src.storage.entities.agent import Agent, AgentStatus
from src.storage.entities.agent_config_version import AgentConfigVersion, VersionStatus
from src.storage.entities.agent_prompt_version import AgentPromptVersion


def _make_test_app():
    """Create a minimal FastAPI app with the agents router and mock DB."""
    from fastapi import FastAPI

    from src.api.routes.agents import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Configure rate limiter for tests
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    return app


@pytest.fixture
def agents_app():
    """Lightweight FastAPI app with agent routes and mocked DB."""
    return _make_test_app()


@pytest.fixture
async def agents_client(agents_app):
    """Async HTTP client wired to the agents test app."""
    async with AsyncClient(
        transport=ASGITransport(app=agents_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_agent():
    """Create a sample agent."""
    agent = Agent(
        id=str(uuid4()),
        name="architect",
        description="Automation design",
        version="0.1.0",
        status=AgentStatus.ENABLED.value,
    )
    agent.created_at = datetime.now(UTC)
    agent.updated_at = datetime.now(UTC)
    agent.active_config_version_id = None
    agent.active_prompt_version_id = None
    agent.active_config_version = None
    agent.active_prompt_version = None
    return agent


@pytest.fixture
def sample_config(sample_agent):
    """Create a sample config version."""
    cv = AgentConfigVersion(
        id=str(uuid4()),
        agent_id=sample_agent.id,
        version_number=1,
        status=VersionStatus.ACTIVE.value,
        model_name="gpt-4o",
        temperature=0.7,
        fallback_model=None,
        tools_enabled=["get_entity_state"],
        change_summary="Initial",
    )
    cv.created_at = datetime.now(UTC)
    cv.updated_at = datetime.now(UTC)
    cv.promoted_at = datetime.now(UTC)
    cv.version = "0.1.0"
    sample_agent.active_config_version_id = cv.id
    sample_agent.active_config_version = cv
    return cv


@pytest.fixture
def sample_prompt(sample_agent):
    """Create a sample prompt version."""
    pv = AgentPromptVersion(
        id=str(uuid4()),
        agent_id=sample_agent.id,
        version_number=1,
        status=VersionStatus.ACTIVE.value,
        prompt_template="You are the Architect.",
        change_summary="Initial",
    )
    pv.created_at = datetime.now(UTC)
    pv.updated_at = datetime.now(UTC)
    pv.promoted_at = datetime.now(UTC)
    pv.version = "0.1.0"
    sample_agent.active_prompt_version_id = pv.id
    sample_agent.active_prompt_version = pv
    return pv


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
class TestListAgents:
    """Tests for GET /api/v1/agents."""

    async def test_list_agents_success(
        self, agents_client, sample_agent, sample_config, sample_prompt, mock_session
    ):
        """Should return all agents with active config/prompt."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.list_all = AsyncMock(return_value=[sample_agent])

            response = await agents_client.get("/api/v1/agents")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["agents"]) == 1
            assert data["agents"][0]["name"] == "architect"
            assert data["agents"][0]["status"] == "enabled"

    async def test_list_agents_empty(self, agents_client, mock_session):
        """Should return empty list when no agents exist."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.list_all = AsyncMock(return_value=[])

            response = await agents_client.get("/api/v1/agents")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["agents"] == []


@pytest.mark.asyncio
class TestGetAgent:
    """Tests for GET /api/v1/agents/{agent_name}."""

    async def test_get_agent_success(
        self, agents_client, sample_agent, sample_config, sample_prompt, mock_session
    ):
        """Should return agent by name."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)

            response = await agents_client.get("/api/v1/agents/architect")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "architect"
            assert data["status"] == "enabled"

    async def test_get_agent_not_found(self, agents_client, mock_session):
        """Should return 404 when agent not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=None)

            response = await agents_client.get("/api/v1/agents/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestUpdateAgentStatus:
    """Tests for PATCH /api/v1/agents/{agent_name}."""

    async def test_update_status_success(self, agents_client, sample_agent, mock_session):
        """Should update agent status successfully."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        sample_agent.status = AgentStatus.DISABLED.value

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.update_status = AsyncMock(return_value=sample_agent)

            response = await agents_client.patch(
                "/api/v1/agents/architect",
                json={"status": "disabled"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "disabled"
            mock_session.commit.assert_called_once()

    async def test_update_status_invalid(self, agents_client, mock_session):
        """Should return 400 for invalid status."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository"),
        ):
            response = await agents_client.patch(
                "/api/v1/agents/architect",
                json={"status": "invalid_status"},
            )

            assert response.status_code == 422  # Validation error

    async def test_update_status_conflict(self, agents_client, mock_session):
        """Should return 409 for invalid transition."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.update_status = AsyncMock(
                side_effect=ValueError("Invalid transition")
            )

            response = await agents_client.patch(
                "/api/v1/agents/architect",
                json={"status": "disabled"},
            )

            assert response.status_code == 409

    async def test_update_status_not_found(self, agents_client, mock_session):
        """Should return 404 when agent not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.update_status = AsyncMock(return_value=None)

            response = await agents_client.patch(
                "/api/v1/agents/nonexistent",
                json={"status": "disabled"},
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestCloneAgent:
    """Tests for POST /api/v1/agents/{agent_name}/clone."""

    async def test_clone_agent_success(
        self, agents_client, sample_agent, sample_config, sample_prompt, mock_session
    ):
        """Should clone agent with config and prompt."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        cloned_agent = Agent(
            id=str(uuid4()),
            name="architect_copy",
            description="Clone of Automation design",
            version="0.1.0",
            status=AgentStatus.ENABLED.value,
        )
        cloned_agent.created_at = datetime.now(UTC)
        cloned_agent.updated_at = datetime.now(UTC)
        cloned_agent.active_config_version = sample_config
        cloned_agent.active_prompt_version = sample_prompt

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.core.AgentConfigVersionRepository") as MockConfigRepo,
            patch("src.api.routes.agents.core.AgentPromptVersionRepository") as MockPromptRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(
                side_effect=[sample_agent, None, cloned_agent]
            )
            MockAgentRepo.return_value.create_or_update = AsyncMock(return_value=cloned_agent)

            new_config = AgentConfigVersion(
                id=str(uuid4()),
                agent_id=cloned_agent.id,
                version_number=1,
                status=VersionStatus.ACTIVE.value,
                model_name=sample_config.model_name,
                temperature=sample_config.temperature,
            )
            new_config.created_at = datetime.now(UTC)
            new_config.updated_at = datetime.now(UTC)
            new_config.promoted_at = datetime.now(UTC)

            new_prompt = AgentPromptVersion(
                id=str(uuid4()),
                agent_id=cloned_agent.id,
                version_number=1,
                status=VersionStatus.ACTIVE.value,
                prompt_template=sample_prompt.prompt_template,
            )
            new_prompt.created_at = datetime.now(UTC)
            new_prompt.updated_at = datetime.now(UTC)
            new_prompt.promoted_at = datetime.now(UTC)

            MockConfigRepo.return_value.create_draft = AsyncMock(return_value=new_config)
            MockConfigRepo.return_value.promote = AsyncMock(return_value=new_config)
            MockPromptRepo.return_value.create_draft = AsyncMock(return_value=new_prompt)
            MockPromptRepo.return_value.promote = AsyncMock(return_value=new_prompt)

            response = await agents_client.post("/api/v1/agents/architect/clone")

            assert response.status_code == 201
            data = response.json()
            assert "copy" in data["name"].lower()

    async def test_clone_agent_not_found(self, agents_client, mock_session):
        """Should return 404 when source agent not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=None)

            response = await agents_client.post("/api/v1/agents/nonexistent/clone")

            assert response.status_code == 404


@pytest.mark.asyncio
class TestQuickModelSwitch:
    """Tests for PATCH /api/v1/agents/{agent_name}/model."""

    async def test_quick_model_switch_success(
        self, agents_client, sample_agent, sample_config, mock_session
    ):
        """Should create and promote new config version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        new_config = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=2,
            status=VersionStatus.ACTIVE.value,
            model_name="gpt-4o-mini",
            temperature=sample_config.temperature,
        )
        new_config.created_at = datetime.now(UTC)
        new_config.updated_at = datetime.now(UTC)
        new_config.promoted_at = datetime.now(UTC)

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.core.AgentConfigVersionRepository") as MockConfigRepo,
            patch("src.agents.config_cache.invalidate_agent_config") as mock_invalidate,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockConfigRepo.return_value.create_draft = AsyncMock(return_value=new_config)
            MockConfigRepo.return_value.promote = AsyncMock(return_value=new_config)

            response = await agents_client.patch(
                "/api/v1/agents/architect/model",
                json={"model_name": "gpt-4o-mini"},
            )

            assert response.status_code == 200
            mock_invalidate.assert_called_once_with("architect")

    async def test_quick_model_switch_not_found(self, agents_client, mock_session):
        """Should return 404 when agent not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch("src.api.routes.agents.core.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.core.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=None)

            response = await agents_client.patch(
                "/api/v1/agents/nonexistent/model",
                json={"model_name": "gpt-4o-mini"},
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestConfigVersions:
    """Tests for config version endpoints."""

    async def test_list_config_versions(
        self, agents_client, sample_agent, sample_config, mock_session
    ):
        """Should list all config versions for an agent."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch(
                "src.api.routes.agents.config_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.config_versions.AgentRepository") as MockAgentRepo,
            patch(
                "src.api.routes.agents.config_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockConfigRepo.return_value.list_versions = AsyncMock(return_value=[sample_config])

            response = await agents_client.get("/api/v1/agents/architect/config/versions")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["model_name"] == "gpt-4o"

    async def test_create_config_version(
        self, agents_client, sample_agent, sample_config, mock_session
    ):
        """Should create a new draft config version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        draft_config = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=2,
            status=VersionStatus.DRAFT.value,
            model_name="gpt-4o-mini",
            temperature=0.8,
        )
        draft_config.created_at = datetime.now(UTC)
        draft_config.updated_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.config_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.config_versions.AgentRepository") as MockAgentRepo,
            patch(
                "src.api.routes.agents.config_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockConfigRepo.return_value.create_draft = AsyncMock(return_value=draft_config)

            response = await agents_client.post(
                "/api/v1/agents/architect/config/versions",
                json={
                    "model_name": "gpt-4o-mini",
                    "temperature": 0.8,
                    "bump_type": "patch",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "draft"
            assert data["model_name"] == "gpt-4o-mini"

    async def test_update_config_version(self, agents_client, sample_config, mock_session):
        """Should update a draft config version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        updated_config = AgentConfigVersion(
            id=sample_config.id,
            agent_id=sample_config.agent_id,
            version_number=sample_config.version_number,
            status=VersionStatus.DRAFT.value,
            model_name="gpt-4o-mini",
            temperature=0.9,
        )
        updated_config.created_at = datetime.now(UTC)
        updated_config.updated_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.config_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch(
                "src.api.routes.agents.config_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
        ):
            MockConfigRepo.return_value.update_draft = AsyncMock(return_value=updated_config)

            response = await agents_client.patch(
                f"/api/v1/agents/architect/config/versions/{sample_config.id}",
                json={"temperature": 0.9},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["temperature"] == 0.9

    async def test_promote_config_version(self, agents_client, sample_config, mock_session):
        """Should promote a draft config version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        promoted_config = AgentConfigVersion(
            id=sample_config.id,
            agent_id=sample_config.agent_id,
            version_number=sample_config.version_number,
            status=VersionStatus.ACTIVE.value,
            model_name=sample_config.model_name,
        )
        promoted_config.created_at = datetime.now(UTC)
        promoted_config.updated_at = datetime.now(UTC)
        promoted_config.promoted_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.config_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch(
                "src.api.routes.agents.config_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
            patch("src.agents.config_cache.invalidate_agent_config") as mock_invalidate,
        ):
            MockConfigRepo.return_value.promote = AsyncMock(return_value=promoted_config)

            response = await agents_client.post(
                f"/api/v1/agents/architect/config/versions/{sample_config.id}/promote?bump_type=patch"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "active"
            mock_invalidate.assert_called_once_with("architect")

    async def test_rollback_config_version(
        self, agents_client, sample_agent, sample_config, mock_session
    ):
        """Should rollback to previous config version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        rollback_config = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=1,
            status=VersionStatus.DRAFT.value,
            model_name="gpt-4o",
        )
        rollback_config.created_at = datetime.now(UTC)
        rollback_config.updated_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.config_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.config_versions.AgentRepository") as MockAgentRepo,
            patch(
                "src.api.routes.agents.config_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockConfigRepo.return_value.rollback = AsyncMock(return_value=rollback_config)

            response = await agents_client.post("/api/v1/agents/architect/config/rollback")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "draft"

    async def test_delete_config_version(self, agents_client, sample_config, mock_session):
        """Should delete a draft config version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch(
                "src.api.routes.agents.config_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch(
                "src.api.routes.agents.config_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
        ):
            MockConfigRepo.return_value.delete_draft = AsyncMock(return_value=True)

            response = await agents_client.delete(
                f"/api/v1/agents/architect/config/versions/{sample_config.id}"
            )

            assert response.status_code == 204

    async def test_delete_config_version_not_found(self, agents_client, mock_session):
        """Should return 404 when config version not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch(
                "src.api.routes.agents.config_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch(
                "src.api.routes.agents.config_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
        ):
            MockConfigRepo.return_value.delete_draft = AsyncMock(return_value=False)

            response = await agents_client.delete(
                "/api/v1/agents/architect/config/versions/nonexistent"
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestPromptVersions:
    """Tests for prompt version endpoints."""

    async def test_list_prompt_versions(
        self, agents_client, sample_agent, sample_prompt, mock_session
    ):
        """Should list all prompt versions for an agent."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.prompt_versions.AgentRepository") as MockAgentRepo,
            patch(
                "src.api.routes.agents.prompt_versions.AgentPromptVersionRepository"
            ) as MockPromptRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockPromptRepo.return_value.list_versions = AsyncMock(return_value=[sample_prompt])

            response = await agents_client.get("/api/v1/agents/architect/prompt/versions")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["prompt_template"] == "You are the Architect."

    async def test_create_prompt_version(
        self, agents_client, sample_agent, sample_prompt, mock_session
    ):
        """Should create a new draft prompt version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        draft_prompt = AgentPromptVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=2,
            status=VersionStatus.DRAFT.value,
            prompt_template="Updated prompt",
        )
        draft_prompt.created_at = datetime.now(UTC)
        draft_prompt.updated_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.prompt_versions.AgentRepository") as MockAgentRepo,
            patch(
                "src.api.routes.agents.prompt_versions.AgentPromptVersionRepository"
            ) as MockPromptRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockPromptRepo.return_value.create_draft = AsyncMock(return_value=draft_prompt)

            response = await agents_client.post(
                "/api/v1/agents/architect/prompt/versions",
                json={
                    "prompt_template": "Updated prompt",
                    "bump_type": "patch",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "draft"
            assert data["prompt_template"] == "Updated prompt"

    async def test_update_prompt_version(self, agents_client, sample_prompt, mock_session):
        """Should update a draft prompt version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        updated_prompt = AgentPromptVersion(
            id=sample_prompt.id,
            agent_id=sample_prompt.agent_id,
            version_number=sample_prompt.version_number,
            status=VersionStatus.DRAFT.value,
            prompt_template="Updated prompt text",
        )
        updated_prompt.created_at = datetime.now(UTC)
        updated_prompt.updated_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch(
                "src.api.routes.agents.prompt_versions.AgentPromptVersionRepository"
            ) as MockPromptRepo,
        ):
            MockPromptRepo.return_value.update_draft = AsyncMock(return_value=updated_prompt)

            response = await agents_client.patch(
                f"/api/v1/agents/architect/prompt/versions/{sample_prompt.id}",
                json={"prompt_template": "Updated prompt text"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["prompt_template"] == "Updated prompt text"

    async def test_promote_prompt_version(self, agents_client, sample_prompt, mock_session):
        """Should promote a draft prompt version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        promoted_prompt = AgentPromptVersion(
            id=sample_prompt.id,
            agent_id=sample_prompt.agent_id,
            version_number=sample_prompt.version_number,
            status=VersionStatus.ACTIVE.value,
            prompt_template=sample_prompt.prompt_template,
        )
        promoted_prompt.created_at = datetime.now(UTC)
        promoted_prompt.updated_at = datetime.now(UTC)
        promoted_prompt.promoted_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch(
                "src.api.routes.agents.prompt_versions.AgentPromptVersionRepository"
            ) as MockPromptRepo,
            patch("src.agents.config_cache.invalidate_agent_config") as mock_invalidate,
        ):
            MockPromptRepo.return_value.promote = AsyncMock(return_value=promoted_prompt)

            response = await agents_client.post(
                f"/api/v1/agents/architect/prompt/versions/{sample_prompt.id}/promote?bump_type=patch"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "active"
            mock_invalidate.assert_called_once_with("architect")

    async def test_rollback_prompt_version(
        self, agents_client, sample_agent, sample_prompt, mock_session
    ):
        """Should rollback to previous prompt version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        rollback_prompt = AgentPromptVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=1,
            status=VersionStatus.DRAFT.value,
            prompt_template="Previous prompt",
        )
        rollback_prompt.created_at = datetime.now(UTC)
        rollback_prompt.updated_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.prompt_versions.AgentRepository") as MockAgentRepo,
            patch(
                "src.api.routes.agents.prompt_versions.AgentPromptVersionRepository"
            ) as MockPromptRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockPromptRepo.return_value.rollback = AsyncMock(return_value=rollback_prompt)

            response = await agents_client.post("/api/v1/agents/architect/prompt/rollback")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "draft"

    async def test_delete_prompt_version(self, agents_client, sample_prompt, mock_session):
        """Should delete a draft prompt version."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch(
                "src.api.routes.agents.prompt_versions.AgentPromptVersionRepository"
            ) as MockPromptRepo,
        ):
            MockPromptRepo.return_value.delete_draft = AsyncMock(return_value=True)

            response = await agents_client.delete(
                f"/api/v1/agents/architect/prompt/versions/{sample_prompt.id}"
            )

            assert response.status_code == 204


@pytest.mark.asyncio
class TestPromoteBoth:
    """Tests for POST /api/v1/agents/{agent_name}/promote-all."""

    async def test_promote_both_success(
        self, agents_client, sample_agent, sample_config, sample_prompt, mock_session
    ):
        """Should promote both config and prompt drafts."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        promoted_config = AgentConfigVersion(
            id=sample_config.id,
            agent_id=sample_agent.id,
            version_number=2,
            status=VersionStatus.ACTIVE.value,
            model_name=sample_config.model_name,
            version="0.2.0",
        )
        promoted_config.created_at = datetime.now(UTC)
        promoted_config.updated_at = datetime.now(UTC)
        promoted_config.promoted_at = datetime.now(UTC)

        promoted_prompt = AgentPromptVersion(
            id=sample_prompt.id,
            agent_id=sample_agent.id,
            version_number=2,
            status=VersionStatus.ACTIVE.value,
            prompt_template=sample_prompt.prompt_template,
            version="0.2.0",
        )
        promoted_prompt.created_at = datetime.now(UTC)
        promoted_prompt.updated_at = datetime.now(UTC)
        promoted_prompt.promoted_at = datetime.now(UTC)

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.prompt_versions.AgentRepository") as MockAgentRepo,
            patch(
                "src.api.routes.agents.prompt_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
            patch(
                "src.api.routes.agents.prompt_versions.AgentPromptVersionRepository"
            ) as MockPromptRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockConfigRepo.return_value.get_draft = AsyncMock(return_value=sample_config)
            MockConfigRepo.return_value.promote = AsyncMock(return_value=promoted_config)
            MockPromptRepo.return_value.get_draft = AsyncMock(return_value=sample_prompt)
            MockPromptRepo.return_value.promote = AsyncMock(return_value=promoted_prompt)

            response = await agents_client.post(
                "/api/v1/agents/architect/promote-all?bump_type=minor"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["config"] is not None
            assert data["prompt"] is not None
            assert "promoted" in data["message"].lower()

    async def test_promote_both_no_drafts(self, agents_client, sample_agent, mock_session):
        """Should return 409 when no drafts exist."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.prompt_versions.AgentRepository") as MockAgentRepo,
            patch(
                "src.api.routes.agents.prompt_versions.AgentConfigVersionRepository"
            ) as MockConfigRepo,
            patch(
                "src.api.routes.agents.prompt_versions.AgentPromptVersionRepository"
            ) as MockPromptRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockConfigRepo.return_value.get_draft = AsyncMock(return_value=None)
            MockPromptRepo.return_value.get_draft = AsyncMock(return_value=None)

            response = await agents_client.post("/api/v1/agents/architect/promote-all")

            assert response.status_code == 409


@pytest.mark.asyncio
class TestGeneratePrompt:
    """Tests for POST /api/v1/agents/{agent_name}/prompt/generate."""

    async def test_generate_prompt_success(
        self, agents_client, sample_agent, sample_prompt, mock_session
    ):
        """Should generate a prompt using LLM."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        mock_llm_response = MagicMock()
        mock_llm_response.content = "Generated system prompt"

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.prompt_versions.AgentRepository") as MockAgentRepo,
            patch("src.llm.get_llm") as mock_get_llm,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_get_llm.return_value = mock_llm

            response = await agents_client.post(
                "/api/v1/agents/architect/prompt/generate",
                json={"user_input": "Make it more concise"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "generated_prompt" in data
            assert data["agent_name"] == "architect"

    async def test_generate_prompt_not_found(self, agents_client, mock_session):
        """Should return 404 when agent not found."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        with (
            patch(
                "src.api.routes.agents.prompt_versions.get_session",
                side_effect=_get_session_factory,
            ),
            patch("src.api.routes.agents.prompt_versions.AgentRepository") as MockAgentRepo,
        ):
            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=None)

            response = await agents_client.post(
                "/api/v1/agents/nonexistent/prompt/generate",
                json={},
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestSeedAgents:
    """Tests for POST /api/v1/agents/seed."""

    async def test_seed_agents_success(self, agents_client, mock_session):
        """Should seed default agents."""

        @asynccontextmanager
        async def _mock_get_session():
            yield mock_session

        def _get_session_factory():
            return _mock_get_session()

        mock_agent = Agent(
            id=str(uuid4()),
            name="architect",
            description="Test",
            version="0.1.0",
            status=AgentStatus.PRIMARY.value,
        )
        mock_agent.created_at = datetime.now(UTC)
        mock_agent.updated_at = datetime.now(UTC)

        with (
            patch("src.api.routes.agents.seed.get_session", side_effect=_get_session_factory),
            patch("src.api.routes.agents.seed.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.seed.AgentConfigVersionRepository") as MockConfigRepo,
            patch("src.api.routes.agents.seed.AgentPromptVersionRepository") as MockPromptRepo,
            patch("src.settings.get_settings") as mock_get_settings,
            patch("src.agents.prompts.load_prompt") as mock_load_prompt,
        ):
            mock_settings = MagicMock()
            mock_settings.llm_model = "gpt-4o"
            mock_settings.llm_temperature = 0.7
            mock_settings.data_scientist_model = None
            mock_settings.data_scientist_temperature = None
            mock_get_settings.return_value = mock_settings

            mock_load_prompt.return_value = "Test prompt"

            mock_config = AgentConfigVersion(
                id=str(uuid4()),
                agent_id=mock_agent.id,
                version_number=1,
                status=VersionStatus.ACTIVE.value,
                model_name="gpt-4o",
            )
            mock_config.created_at = datetime.now(UTC)
            mock_config.updated_at = datetime.now(UTC)
            mock_config.promoted_at = datetime.now(UTC)

            mock_prompt = AgentPromptVersion(
                id=str(uuid4()),
                agent_id=mock_agent.id,
                version_number=1,
                status=VersionStatus.ACTIVE.value,
                prompt_template="Test prompt",
            )
            mock_prompt.created_at = datetime.now(UTC)
            mock_prompt.updated_at = datetime.now(UTC)
            mock_prompt.promoted_at = datetime.now(UTC)

            MockAgentRepo.return_value.create_or_update = AsyncMock(return_value=mock_agent)
            MockConfigRepo.return_value.get_active = AsyncMock(return_value=None)
            MockConfigRepo.return_value.create_draft = AsyncMock(return_value=mock_config)
            MockConfigRepo.return_value.promote = AsyncMock(return_value=mock_config)
            MockPromptRepo.return_value.get_active = AsyncMock(return_value=None)
            MockPromptRepo.return_value.create_draft = AsyncMock(return_value=mock_prompt)
            MockPromptRepo.return_value.promote = AsyncMock(return_value=mock_prompt)

            response = await agents_client.post("/api/v1/agents/seed")

            assert response.status_code == 201
            data = response.json()
            assert "agents_seeded" in data
            assert "configs_created" in data
            assert "prompts_created" in data
