"""Unit tests for Agent Configuration API routes.

Feature 23: Agent Configuration Page.
Constitution: Reliability & Quality - API route testing.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.storage.entities.agent import Agent, AgentStatus
from src.storage.entities.agent_config_version import AgentConfigVersion, VersionStatus
from src.storage.entities.agent_prompt_version import AgentPromptVersion


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
    sample_agent.active_prompt_version_id = pv.id
    sample_agent.active_prompt_version = pv
    return pv


class TestListAgents:
    """Tests for GET /agents."""

    @pytest.mark.asyncio
    async def test_list_agents_returns_all(self, sample_agent, sample_config, sample_prompt):
        """Test listing agents includes active config/prompt."""
        from src.api.routes.agents import list_agents

        with (
            patch("src.api.routes.agents.get_session") as mock_get_session,
            patch("src.api.routes.agents.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.AgentConfigVersionRepository") as MockConfigRepo,
            patch("src.api.routes.agents.AgentPromptVersionRepository") as MockPromptRepo,
        ):
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            MockAgentRepo.return_value.list_all = AsyncMock(return_value=[sample_agent])
            MockConfigRepo.return_value.get_active = AsyncMock(return_value=sample_config)
            MockPromptRepo.return_value.get_active = AsyncMock(return_value=sample_prompt)

            result = await list_agents()

            assert result.total == 1
            assert result.agents[0].name == "architect"
            assert result.agents[0].active_config is not None
            assert result.agents[0].active_config.model_name == "gpt-4o"


class TestGetAgent:
    """Tests for GET /agents/{agent_name}."""

    @pytest.mark.asyncio
    async def test_get_agent_found(self, sample_agent, sample_config, sample_prompt):
        """Test getting an existing agent."""
        from src.api.routes.agents import get_agent

        with (
            patch("src.api.routes.agents.get_session") as mock_get_session,
            patch("src.api.routes.agents.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.AgentConfigVersionRepository") as MockConfigRepo,
            patch("src.api.routes.agents.AgentPromptVersionRepository") as MockPromptRepo,
        ):
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockConfigRepo.return_value.get_active = AsyncMock(return_value=sample_config)
            MockPromptRepo.return_value.get_active = AsyncMock(return_value=sample_prompt)

            result = await get_agent("architect")

            assert result.name == "architect"
            assert result.status == "enabled"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self):
        """Test getting nonexistent agent raises 404."""
        from fastapi import HTTPException

        from src.api.routes.agents import get_agent

        with (
            patch("src.api.routes.agents.get_session") as mock_get_session,
            patch("src.api.routes.agents.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.AgentConfigVersionRepository"),
            patch("src.api.routes.agents.AgentPromptVersionRepository"),
        ):
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_agent("nonexistent")

            assert exc_info.value.status_code == 404


class TestUpdateAgentStatus:
    """Tests for PATCH /agents/{agent_name}."""

    @pytest.mark.asyncio
    async def test_update_status_success(self, sample_agent):
        """Test successful status update."""
        from src.api.routes.agents import AgentStatusUpdate, update_agent_status

        sample_agent.status = AgentStatus.DISABLED.value

        with (
            patch("src.api.routes.agents.get_session") as mock_get_session,
            patch("src.api.routes.agents.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.AgentConfigVersionRepository") as MockConfigRepo,
            patch("src.api.routes.agents.AgentPromptVersionRepository") as MockPromptRepo,
        ):
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            MockAgentRepo.return_value.update_status = AsyncMock(return_value=sample_agent)
            MockConfigRepo.return_value.get_active = AsyncMock(return_value=None)
            MockPromptRepo.return_value.get_active = AsyncMock(return_value=None)

            result = await update_agent_status(
                "architect",
                AgentStatusUpdate(status="disabled"),
            )

            assert result.status == "disabled"

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition(self):
        """Test invalid status transition returns 409."""
        from fastapi import HTTPException

        from src.api.routes.agents import AgentStatusUpdate, update_agent_status

        with (
            patch("src.api.routes.agents.get_session") as mock_get_session,
            patch("src.api.routes.agents.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.AgentConfigVersionRepository"),
            patch("src.api.routes.agents.AgentPromptVersionRepository"),
        ):
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            MockAgentRepo.return_value.update_status = AsyncMock(
                side_effect=ValueError("Invalid status transition")
            )

            with pytest.raises(HTTPException) as exc_info:
                await update_agent_status(
                    "architect",
                    AgentStatusUpdate(status="disabled"),
                )

            assert exc_info.value.status_code == 409


class TestConfigVersionPromote:
    """Tests for POST /agents/{agent_name}/config/versions/{id}/promote."""

    @pytest.mark.asyncio
    async def test_promote_config_success(self, sample_config):
        """Test promoting a config version."""
        from starlette.requests import Request

        from src.api.routes.agents import promote_config_version

        sample_config.status = VersionStatus.ACTIVE.value
        sample_config.promoted_at = datetime.now(UTC)

        with (
            patch("src.api.routes.agents.get_session") as mock_get_session,
            patch("src.api.routes.agents.AgentConfigVersionRepository") as MockConfigRepo,
        ):
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            MockConfigRepo.return_value.promote = AsyncMock(return_value=sample_config)

            request = Request(
                scope={
                    "type": "http",
                    "method": "POST",
                    "path": "/",
                    "headers": [],
                }
            )
            result = await promote_config_version(request, "architect", sample_config.id)

            assert result.status == "active"
            assert result.promoted_at is not None


class TestPromptVersionCreate:
    """Tests for POST /agents/{agent_name}/prompt/versions."""

    @pytest.mark.asyncio
    async def test_create_prompt_version(self, sample_agent, sample_prompt):
        """Test creating a new prompt version draft."""
        from src.api.routes.agents import AgentPromptVersionCreate, create_prompt_version

        sample_prompt.status = VersionStatus.DRAFT.value
        sample_prompt.version_number = 2

        with (
            patch("src.api.routes.agents.get_session") as mock_get_session,
            patch("src.api.routes.agents.AgentRepository") as MockAgentRepo,
            patch("src.api.routes.agents.AgentPromptVersionRepository") as MockPromptRepo,
        ):
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            MockAgentRepo.return_value.get_by_name = AsyncMock(return_value=sample_agent)
            MockPromptRepo.return_value.create_draft = AsyncMock(return_value=sample_prompt)

            result = await create_prompt_version(
                "architect",
                AgentPromptVersionCreate(
                    prompt_template="Updated prompt",
                    change_summary="Testing",
                ),
            )

            assert result.version_number == 2
            assert result.status == "draft"
