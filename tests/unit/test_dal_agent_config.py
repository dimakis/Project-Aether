"""Unit tests for Agent Configuration DAL operations.

Tests AgentRepository, AgentConfigVersionRepository, and
AgentPromptVersionRepository with mocked database.

Feature 23: Agent Configuration.
Constitution: Reliability & Quality - comprehensive DAL testing.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dal.agents import (
    AgentConfigVersionRepository,
    AgentPromptVersionRepository,
    AgentRepository,
)
from src.storage.entities.agent import Agent, AgentStatus
from src.storage.entities.agent_config_version import AgentConfigVersion, VersionStatus
from src.storage.entities.agent_prompt_version import AgentPromptVersion


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def agent_repo(mock_session):
    """Create AgentRepository with mock session."""
    return AgentRepository(mock_session)


@pytest.fixture
def config_repo(mock_session):
    """Create AgentConfigVersionRepository with mock session."""
    return AgentConfigVersionRepository(mock_session)


@pytest.fixture
def prompt_repo(mock_session):
    """Create AgentPromptVersionRepository with mock session."""
    return AgentPromptVersionRepository(mock_session)


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    return Agent(
        id=str(uuid4()),
        name="architect",
        description="Automation design and user interaction",
        version="0.1.0",
        status=AgentStatus.ENABLED.value,
    )


@pytest.fixture
def sample_config_version(sample_agent):
    """Create a sample config version for testing."""
    return AgentConfigVersion(
        id=str(uuid4()),
        agent_id=sample_agent.id,
        version_number=1,
        status=VersionStatus.ACTIVE.value,
        model_name="gpt-4o",
        temperature=0.7,
        fallback_model=None,
        tools_enabled=["get_entity_state", "control_entity"],
        change_summary="Initial config",
    )


@pytest.fixture
def sample_prompt_version(sample_agent):
    """Create a sample prompt version for testing."""
    return AgentPromptVersion(
        id=str(uuid4()),
        agent_id=sample_agent.id,
        version_number=1,
        status=VersionStatus.ACTIVE.value,
        prompt_template="You are the Architect agent.",
        change_summary="Initial prompt",
    )


# ─── AgentRepository ─────────────────────────────────────────────────────────


class TestAgentRepositoryGetByName:
    """Tests for get_by_name method."""

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, agent_repo, mock_session, sample_agent):
        """Test getting agent by name when it exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_agent
        mock_session.execute.return_value = mock_result

        result = await agent_repo.get_by_name("architect")

        assert result == sample_agent
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, agent_repo, mock_session):
        """Test getting agent by name when it doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await agent_repo.get_by_name("nonexistent")

        assert result is None


class TestAgentRepositoryListAll:
    """Tests for list_all method."""

    @pytest.mark.asyncio
    async def test_list_all(self, agent_repo, mock_session, sample_agent):
        """Test listing all agents."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_agent]
        mock_session.execute.return_value = mock_result

        results = await agent_repo.list_all()

        assert len(results) == 1
        assert results[0] == sample_agent


class TestAgentRepositoryUpdateStatus:
    """Tests for update_status method."""

    @pytest.mark.asyncio
    async def test_update_status_valid_transition(
        self, agent_repo, mock_session, sample_agent
    ):
        """Test valid status transition (enabled -> disabled)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_agent
        mock_session.execute.return_value = mock_result

        result = await agent_repo.update_status("architect", AgentStatus.DISABLED)

        assert result is not None
        assert result.status == AgentStatus.DISABLED.value

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition(
        self, agent_repo, mock_session
    ):
        """Test invalid status transition raises ValueError."""
        agent = Agent(
            id=str(uuid4()),
            name="architect",
            description="test",
            version="0.1.0",
            status=AgentStatus.DISABLED.value,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = agent
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Invalid status transition"):
            await agent_repo.update_status("architect", AgentStatus.PRIMARY)

    @pytest.mark.asyncio
    async def test_update_status_agent_not_found(self, agent_repo, mock_session):
        """Test updating status of nonexistent agent returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await agent_repo.update_status("nonexistent", AgentStatus.DISABLED)

        assert result is None


# ─── AgentConfigVersionRepository ─────────────────────────────────────────────


class TestConfigVersionCreate:
    """Tests for create_draft method."""

    @pytest.mark.asyncio
    async def test_create_draft(self, config_repo, mock_session, sample_agent):
        """Test creating a new draft config version."""
        # Mock: no existing draft
        mock_draft_result = MagicMock()
        mock_draft_result.scalar_one_or_none.return_value = None
        # Mock: max version number
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 1
        # Mock: latest semver
        mock_semver_result = MagicMock()
        mock_semver_result.scalar_one_or_none.return_value = "0.1.0"
        mock_session.execute.side_effect = [mock_draft_result, mock_max_result, mock_semver_result]

        result = await config_repo.create_draft(
            agent_id=sample_agent.id,
            model_name="anthropic/claude-sonnet-4",
            temperature=0.5,
            tools_enabled=["get_entity_state"],
            change_summary="Switch to Claude",
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.version_number == 2
        assert added.status == VersionStatus.DRAFT.value
        assert added.model_name == "anthropic/claude-sonnet-4"

    @pytest.mark.asyncio
    async def test_create_draft_replaces_existing(
        self, config_repo, mock_session, sample_agent
    ):
        """Test creating a draft when one already exists raises error."""
        existing_draft = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=2,
            status=VersionStatus.DRAFT.value,
        )
        mock_draft_result = MagicMock()
        mock_draft_result.scalar_one_or_none.return_value = existing_draft
        mock_session.execute.return_value = mock_draft_result

        with pytest.raises(ValueError, match="already exists"):
            await config_repo.create_draft(
                agent_id=sample_agent.id,
                model_name="gpt-4o",
            )

    @pytest.mark.asyncio
    async def test_create_draft_first_version(
        self, config_repo, mock_session, sample_agent
    ):
        """Test creating the very first config version."""
        mock_draft_result = MagicMock()
        mock_draft_result.scalar_one_or_none.return_value = None
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = None  # No versions exist
        # Mock: no existing semver
        mock_semver_result = MagicMock()
        mock_semver_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [mock_draft_result, mock_max_result, mock_semver_result]

        await config_repo.create_draft(
            agent_id=sample_agent.id,
            model_name="gpt-4o",
        )

        added = mock_session.add.call_args[0][0]
        assert added.version_number == 1


class TestConfigVersionPromote:
    """Tests for promote method."""

    @pytest.mark.asyncio
    async def test_promote_draft_to_active(
        self, config_repo, mock_session, sample_agent
    ):
        """Test promoting a draft config to active."""
        draft = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=2,
            status=VersionStatus.DRAFT.value,
            model_name="gpt-4o",
        )
        # Mock: get draft by ID
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = draft
        # Mock: get current active (to archive it)
        current_active = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=1,
            status=VersionStatus.ACTIVE.value,
        )
        mock_active_result = MagicMock()
        mock_active_result.scalar_one_or_none.return_value = current_active
        # Mock: get parent agent
        mock_agent_result = MagicMock()
        mock_agent_result.scalar_one_or_none.return_value = sample_agent
        mock_session.execute.side_effect = [
            mock_get_result,
            mock_active_result,
            mock_agent_result,
        ]

        result = await config_repo.promote(draft.id)

        assert result.status == VersionStatus.ACTIVE.value
        assert result.promoted_at is not None
        assert current_active.status == VersionStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_promote_non_draft_raises(self, config_repo, mock_session):
        """Test promoting non-draft version raises error."""
        active_version = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=str(uuid4()),
            version_number=1,
            status=VersionStatus.ACTIVE.value,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = active_version
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Only draft versions"):
            await config_repo.promote(active_version.id)


class TestConfigVersionRollback:
    """Tests for rollback method."""

    @pytest.mark.asyncio
    async def test_rollback_creates_draft_from_archived(
        self, config_repo, mock_session, sample_agent
    ):
        """Test rollback creates a new draft from the latest archived version."""
        archived = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=1,
            status=VersionStatus.ARCHIVED.value,
            model_name="gpt-4o",
            temperature=0.7,
            tools_enabled=["get_entity_state"],
        )
        # Mock: no existing draft
        mock_draft_result = MagicMock()
        mock_draft_result.scalar_one_or_none.return_value = None
        # Mock: latest archived version
        mock_archived_result = MagicMock()
        mock_archived_result.scalar_one_or_none.return_value = archived
        # Mock: max version number
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 2
        mock_session.execute.side_effect = [
            mock_draft_result,
            mock_archived_result,
            mock_max_result,
        ]

        result = await config_repo.rollback(sample_agent.id)

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.version_number == 3
        assert added.model_name == "gpt-4o"
        assert added.status == VersionStatus.DRAFT.value
        assert added.change_summary is not None
        assert "Rollback" in added.change_summary

    @pytest.mark.asyncio
    async def test_rollback_no_archived_raises(
        self, config_repo, mock_session, sample_agent
    ):
        """Test rollback with no archived versions raises error."""
        mock_draft_result = MagicMock()
        mock_draft_result.scalar_one_or_none.return_value = None
        mock_archived_result = MagicMock()
        mock_archived_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [mock_draft_result, mock_archived_result]

        with pytest.raises(ValueError, match="No archived version"):
            await config_repo.rollback(sample_agent.id)


class TestConfigVersionList:
    """Tests for list_versions method."""

    @pytest.mark.asyncio
    async def test_list_versions(
        self, config_repo, mock_session, sample_config_version
    ):
        """Test listing config versions for an agent."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_config_version]
        mock_session.execute.return_value = mock_result

        results = await config_repo.list_versions(sample_config_version.agent_id)

        assert len(results) == 1
        assert results[0] == sample_config_version


class TestConfigVersionGetActive:
    """Tests for get_active method."""

    @pytest.mark.asyncio
    async def test_get_active_found(
        self, config_repo, mock_session, sample_config_version
    ):
        """Test getting active config version."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_config_version
        mock_session.execute.return_value = mock_result

        result = await config_repo.get_active(sample_config_version.agent_id)

        assert result == sample_config_version
        assert result.status == VersionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_get_active_none(self, config_repo, mock_session):
        """Test getting active when none exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await config_repo.get_active(str(uuid4()))

        assert result is None


# ─── AgentPromptVersionRepository ─────────────────────────────────────────────


class TestPromptVersionCreate:
    """Tests for create_draft method."""

    @pytest.mark.asyncio
    async def test_create_draft(self, prompt_repo, mock_session, sample_agent):
        """Test creating a new draft prompt version."""
        mock_draft_result = MagicMock()
        mock_draft_result.scalar_one_or_none.return_value = None
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 1
        # Mock: latest semver
        mock_semver_result = MagicMock()
        mock_semver_result.scalar_one_or_none.return_value = "0.1.0"
        mock_session.execute.side_effect = [mock_draft_result, mock_max_result, mock_semver_result]

        result = await prompt_repo.create_draft(
            agent_id=sample_agent.id,
            prompt_template="You are a revised Architect agent.",
            change_summary="Updated system prompt",
        )

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert added.version_number == 2
        assert added.status == VersionStatus.DRAFT.value
        assert "revised" in added.prompt_template


class TestPromptVersionPromote:
    """Tests for promote method."""

    @pytest.mark.asyncio
    async def test_promote_draft_to_active(
        self, prompt_repo, mock_session, sample_agent
    ):
        """Test promoting a draft prompt to active."""
        draft = AgentPromptVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=2,
            status=VersionStatus.DRAFT.value,
            prompt_template="New prompt",
        )
        current_active = AgentPromptVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=1,
            status=VersionStatus.ACTIVE.value,
            prompt_template="Old prompt",
        )
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = draft
        mock_active_result = MagicMock()
        mock_active_result.scalar_one_or_none.return_value = current_active
        mock_agent_result = MagicMock()
        mock_agent_result.scalar_one_or_none.return_value = sample_agent
        mock_session.execute.side_effect = [
            mock_get_result,
            mock_active_result,
            mock_agent_result,
        ]

        result = await prompt_repo.promote(draft.id)

        assert result.status == VersionStatus.ACTIVE.value
        assert current_active.status == VersionStatus.ARCHIVED.value


class TestPromptVersionRollback:
    """Tests for rollback method."""

    @pytest.mark.asyncio
    async def test_rollback_creates_draft_from_archived(
        self, prompt_repo, mock_session, sample_agent
    ):
        """Test rollback creates a new draft from latest archived prompt."""
        archived = AgentPromptVersion(
            id=str(uuid4()),
            agent_id=sample_agent.id,
            version_number=1,
            status=VersionStatus.ARCHIVED.value,
            prompt_template="Original prompt text",
        )
        mock_draft_result = MagicMock()
        mock_draft_result.scalar_one_or_none.return_value = None
        mock_archived_result = MagicMock()
        mock_archived_result.scalar_one_or_none.return_value = archived
        mock_max_result = MagicMock()
        mock_max_result.scalar.return_value = 2
        mock_session.execute.side_effect = [
            mock_draft_result,
            mock_archived_result,
            mock_max_result,
        ]

        result = await prompt_repo.rollback(sample_agent.id)

        added = mock_session.add.call_args[0][0]
        assert added.prompt_template == "Original prompt text"
        assert added.version_number == 3
        assert "Rollback" in added.change_summary
