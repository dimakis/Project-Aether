"""Agent configuration repositories.

Feature 23: Agent Configuration Page.

Provides CRUD operations for managing agents and their versioned
configurations (LLM settings and prompt templates).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities.agent import Agent, AgentStatus, VALID_AGENT_STATUS_TRANSITIONS
from src.storage.entities.agent_config_version import AgentConfigVersion, VersionStatus
from src.storage.entities.agent_prompt_version import AgentPromptVersion

# ─── Semver helpers ───────────────────────────────────────────────────────────

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def bump_semver(current: str | None, bump_type: str = "patch") -> str:
    """Bump a semver string by the specified type.

    Args:
        current: Current version (e.g. '1.2.3') or None for initial
        bump_type: 'major', 'minor', or 'patch'

    Returns:
        Bumped version string
    """
    if current is None:
        return "0.1.0"

    m = _SEMVER_RE.match(current)
    if not m:
        return "0.1.0"

    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


class AgentRepository:
    """Repository for Agent CRUD and lifecycle operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, agent_id: str) -> Agent | None:
        """Get agent by ID."""
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Agent | None:
        """Get agent by name.

        Args:
            name: Agent identifier (e.g. 'architect', 'data_scientist')

        Returns:
            Agent or None
        """
        result = await self.session.execute(
            select(Agent).where(Agent.name == name)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Agent]:
        """List all agents ordered by name.

        Returns:
            List of agents
        """
        result = await self.session.execute(
            select(Agent).order_by(Agent.name)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        name: str,
        new_status: AgentStatus,
    ) -> Agent | None:
        """Update agent lifecycle status with transition validation.

        Args:
            name: Agent name
            new_status: Target status

        Returns:
            Updated agent, or None if not found

        Raises:
            ValueError: If the transition is invalid
        """
        agent = await self.get_by_name(name)
        if agent is None:
            return None

        if not agent.can_transition_to(new_status):
            current = AgentStatus(agent.status)
            raise ValueError(
                f"Invalid status transition: {current.value} -> {new_status.value}. "
                f"Allowed: {', '.join(s.value for s in VALID_AGENT_STATUS_TRANSITIONS.get(current, set()))}"
            )

        agent.status = new_status.value
        await self.session.flush()
        return agent

    async def create_or_update(
        self,
        name: str,
        description: str,
        version: str = "0.1.0",
        status: str = AgentStatus.ENABLED.value,
    ) -> Agent:
        """Create or update an agent by name.

        Args:
            name: Agent identifier
            description: Human-readable description
            version: Semantic version
            status: Initial status

        Returns:
            Created or updated Agent
        """
        agent = await self.get_by_name(name)
        if agent:
            agent.description = description
            agent.version = version
        else:
            agent = Agent(
                id=str(uuid4()),
                name=name,
                description=description,
                version=version,
                status=status,
            )
            self.session.add(agent)
        await self.session.flush()
        return agent


class AgentConfigVersionRepository:
    """Repository for versioned agent LLM configuration."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, version_id: str) -> AgentConfigVersion | None:
        """Get config version by ID."""
        result = await self.session.execute(
            select(AgentConfigVersion).where(AgentConfigVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self, agent_id: str) -> AgentConfigVersion | None:
        """Get the active config version for an agent.

        Args:
            agent_id: Parent agent ID

        Returns:
            Active config version or None
        """
        result = await self.session.execute(
            select(AgentConfigVersion).where(
                AgentConfigVersion.agent_id == agent_id,
                AgentConfigVersion.status == VersionStatus.ACTIVE.value,
            )
        )
        return result.scalar_one_or_none()

    async def get_draft(self, agent_id: str) -> AgentConfigVersion | None:
        """Get the current draft config version for an agent."""
        result = await self.session.execute(
            select(AgentConfigVersion).where(
                AgentConfigVersion.agent_id == agent_id,
                AgentConfigVersion.status == VersionStatus.DRAFT.value,
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[AgentConfigVersion]:
        """List all config versions for an agent (newest first).

        Args:
            agent_id: Parent agent ID
            limit: Max results

        Returns:
            List of config versions
        """
        result = await self.session.execute(
            select(AgentConfigVersion)
            .where(AgentConfigVersion.agent_id == agent_id)
            .order_by(AgentConfigVersion.version_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _next_version_number(self, agent_id: str) -> int:
        """Get the next version number for an agent."""
        result = await self.session.execute(
            select(func.max(AgentConfigVersion.version_number)).where(
                AgentConfigVersion.agent_id == agent_id
            )
        )
        max_version = result.scalar()
        return (max_version or 0) + 1

    async def _latest_semver(self, agent_id: str) -> str | None:
        """Get the latest semver string for an agent's config versions."""
        result = await self.session.execute(
            select(AgentConfigVersion.version)
            .where(
                AgentConfigVersion.agent_id == agent_id,
                AgentConfigVersion.version.isnot(None),
            )
            .order_by(AgentConfigVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_draft(
        self,
        agent_id: str,
        model_name: str | None = None,
        temperature: float | None = None,
        fallback_model: str | None = None,
        tools_enabled: list[str] | None = None,
        change_summary: str | None = None,
        bump_type: str = "patch",
    ) -> AgentConfigVersion:
        """Create a new draft config version.

        Enforces single-draft policy: only one draft per agent at a time.

        Args:
            agent_id: Parent agent ID
            model_name: LLM model identifier
            temperature: Generation temperature
            fallback_model: Fallback model name
            tools_enabled: List of tool names
            change_summary: Description of changes
            bump_type: Semver bump type: 'major', 'minor', or 'patch'

        Returns:
            New draft config version

        Raises:
            ValueError: If a draft already exists for this agent
        """
        existing_draft = await self.get_draft(agent_id)
        if existing_draft:
            raise ValueError(
                f"A draft config version (v{existing_draft.version_number}) "
                f"already exists for this agent. Edit or delete it first."
            )

        version_number = await self._next_version_number(agent_id)
        latest_sv = await self._latest_semver(agent_id)
        semver = bump_semver(latest_sv, bump_type)

        version = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=agent_id,
            version_number=version_number,
            version=semver,
            status=VersionStatus.DRAFT.value,
            model_name=model_name,
            temperature=temperature,
            fallback_model=fallback_model,
            tools_enabled=tools_enabled,
            change_summary=change_summary,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def update_draft(
        self,
        version_id: str,
        **kwargs: object,
    ) -> AgentConfigVersion | None:
        """Update a draft config version.

        Only draft versions can be edited.

        Args:
            version_id: Config version ID
            **kwargs: Fields to update

        Returns:
            Updated version or None

        Raises:
            ValueError: If the version is not a draft
        """
        version = await self.get_by_id(version_id)
        if version is None:
            return None

        if version.status != VersionStatus.DRAFT.value:
            raise ValueError("Only draft versions can be edited")

        allowed_fields = {
            "model_name", "temperature", "fallback_model",
            "tools_enabled", "change_summary",
        }
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(version, key, value)

        await self.session.flush()
        return version

    async def promote(
        self, version_id: str, bump_type: str = "patch",
    ) -> AgentConfigVersion:
        """Promote a draft config version to active.

        Atomically:
        1. Archives the current active version
        2. Recalculates the semver based on bump_type
        3. Sets the draft to active
        4. Updates the agent's active_config_version_id

        Args:
            version_id: Draft version ID to promote
            bump_type: Semver bump type: 'major', 'minor', or 'patch'

        Returns:
            The newly active version

        Raises:
            ValueError: If the version is not a draft or not found
        """
        version = await self.get_by_id(version_id)
        if version is None:
            raise ValueError(f"Config version {version_id} not found")

        if version.status != VersionStatus.DRAFT.value:
            raise ValueError("Only draft versions can be promoted")

        # Archive current active and recalculate semver from it
        current_active = await self.get_active(version.agent_id)
        base_semver = current_active.version if current_active else None
        if current_active:
            current_active.status = VersionStatus.ARCHIVED.value

        # Recalculate version at promotion time
        version.version = bump_semver(base_semver, bump_type)

        # Promote draft
        version.status = VersionStatus.ACTIVE.value
        version.promoted_at = datetime.now(timezone.utc)

        # Update agent FK pointer
        agent_result = await self.session.execute(
            select(Agent).where(Agent.id == version.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent:
            agent.active_config_version_id = version.id

        await self.session.flush()
        return version

    async def rollback(self, agent_id: str) -> AgentConfigVersion:
        """Create a new draft from the latest archived config version.

        Does not auto-promote -- the user must explicitly promote after reviewing.

        Args:
            agent_id: Agent ID to rollback

        Returns:
            New draft version with content from the latest archived version

        Raises:
            ValueError: If a draft already exists or no archived version found
        """
        existing_draft = await self.get_draft(agent_id)
        if existing_draft:
            raise ValueError(
                f"Cannot rollback: a draft (v{existing_draft.version_number}) already exists. "
                "Delete or promote it first."
            )

        # Find the latest archived version
        result = await self.session.execute(
            select(AgentConfigVersion)
            .where(
                AgentConfigVersion.agent_id == agent_id,
                AgentConfigVersion.status == VersionStatus.ARCHIVED.value,
            )
            .order_by(AgentConfigVersion.version_number.desc())
        )
        archived = result.scalar_one_or_none()
        if archived is None:
            raise ValueError("No archived version available for rollback")

        version_number = await self._next_version_number(agent_id)

        rollback_version = AgentConfigVersion(
            id=str(uuid4()),
            agent_id=agent_id,
            version_number=version_number,
            status=VersionStatus.DRAFT.value,
            model_name=archived.model_name,
            temperature=archived.temperature,
            fallback_model=archived.fallback_model,
            tools_enabled=archived.tools_enabled,
            change_summary=f"Rollback from v{archived.version_number}",
        )
        self.session.add(rollback_version)
        await self.session.flush()
        return rollback_version

    async def delete_draft(self, version_id: str) -> bool:
        """Delete a draft config version.

        Only drafts can be deleted.

        Args:
            version_id: Version ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If the version is not a draft
        """
        version = await self.get_by_id(version_id)
        if version is None:
            return False

        if version.status != VersionStatus.DRAFT.value:
            raise ValueError("Only draft versions can be deleted")

        await self.session.delete(version)
        await self.session.flush()
        return True


class AgentPromptVersionRepository:
    """Repository for versioned agent prompt templates."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, version_id: str) -> AgentPromptVersion | None:
        """Get prompt version by ID."""
        result = await self.session.execute(
            select(AgentPromptVersion).where(AgentPromptVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self, agent_id: str) -> AgentPromptVersion | None:
        """Get the active prompt version for an agent."""
        result = await self.session.execute(
            select(AgentPromptVersion).where(
                AgentPromptVersion.agent_id == agent_id,
                AgentPromptVersion.status == VersionStatus.ACTIVE.value,
            )
        )
        return result.scalar_one_or_none()

    async def get_draft(self, agent_id: str) -> AgentPromptVersion | None:
        """Get the current draft prompt version for an agent."""
        result = await self.session.execute(
            select(AgentPromptVersion).where(
                AgentPromptVersion.agent_id == agent_id,
                AgentPromptVersion.status == VersionStatus.DRAFT.value,
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[AgentPromptVersion]:
        """List all prompt versions for an agent (newest first)."""
        result = await self.session.execute(
            select(AgentPromptVersion)
            .where(AgentPromptVersion.agent_id == agent_id)
            .order_by(AgentPromptVersion.version_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _next_version_number(self, agent_id: str) -> int:
        """Get the next version number for an agent."""
        result = await self.session.execute(
            select(func.max(AgentPromptVersion.version_number)).where(
                AgentPromptVersion.agent_id == agent_id
            )
        )
        max_version = result.scalar()
        return (max_version or 0) + 1

    async def _latest_semver(self, agent_id: str) -> str | None:
        """Get the latest semver string for an agent's prompt versions."""
        result = await self.session.execute(
            select(AgentPromptVersion.version)
            .where(
                AgentPromptVersion.agent_id == agent_id,
                AgentPromptVersion.version.isnot(None),
            )
            .order_by(AgentPromptVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_draft(
        self,
        agent_id: str,
        prompt_template: str,
        change_summary: str | None = None,
        bump_type: str = "patch",
    ) -> AgentPromptVersion:
        """Create a new draft prompt version.

        Args:
            agent_id: Parent agent ID
            prompt_template: System prompt text
            change_summary: Description of changes
            bump_type: Semver bump type: 'major', 'minor', or 'patch'

        Returns:
            New draft prompt version

        Raises:
            ValueError: If a draft already exists
        """
        existing_draft = await self.get_draft(agent_id)
        if existing_draft:
            raise ValueError(
                f"A draft prompt version (v{existing_draft.version_number}) "
                f"already exists for this agent. Edit or delete it first."
            )

        version_number = await self._next_version_number(agent_id)
        latest_sv = await self._latest_semver(agent_id)
        semver = bump_semver(latest_sv, bump_type)

        version = AgentPromptVersion(
            id=str(uuid4()),
            agent_id=agent_id,
            version_number=version_number,
            version=semver,
            status=VersionStatus.DRAFT.value,
            prompt_template=prompt_template,
            change_summary=change_summary,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def update_draft(
        self,
        version_id: str,
        prompt_template: str | None = None,
        change_summary: str | None = None,
    ) -> AgentPromptVersion | None:
        """Update a draft prompt version.

        Args:
            version_id: Prompt version ID
            prompt_template: Updated prompt text
            change_summary: Updated description

        Returns:
            Updated version or None

        Raises:
            ValueError: If the version is not a draft
        """
        version = await self.get_by_id(version_id)
        if version is None:
            return None

        if version.status != VersionStatus.DRAFT.value:
            raise ValueError("Only draft versions can be edited")

        if prompt_template is not None:
            version.prompt_template = prompt_template
        if change_summary is not None:
            version.change_summary = change_summary

        await self.session.flush()
        return version

    async def promote(
        self, version_id: str, bump_type: str = "patch",
    ) -> AgentPromptVersion:
        """Promote a draft prompt version to active.

        Args:
            version_id: Draft version ID
            bump_type: Semver bump type: 'major', 'minor', or 'patch'

        Returns:
            The newly active version

        Raises:
            ValueError: If the version is not a draft or not found
        """
        version = await self.get_by_id(version_id)
        if version is None:
            raise ValueError(f"Prompt version {version_id} not found")

        if version.status != VersionStatus.DRAFT.value:
            raise ValueError("Only draft versions can be promoted")

        # Archive current active and recalculate semver from it
        current_active = await self.get_active(version.agent_id)
        base_semver = current_active.version if current_active else None
        if current_active:
            current_active.status = VersionStatus.ARCHIVED.value

        # Recalculate version at promotion time
        version.version = bump_semver(base_semver, bump_type)

        # Promote draft
        version.status = VersionStatus.ACTIVE.value
        version.promoted_at = datetime.now(timezone.utc)

        # Update agent FK pointer
        agent_result = await self.session.execute(
            select(Agent).where(Agent.id == version.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent:
            agent.active_prompt_version_id = version.id

        await self.session.flush()
        return version

    async def rollback(self, agent_id: str) -> AgentPromptVersion:
        """Create a new draft from the latest archived prompt version.

        Args:
            agent_id: Agent ID to rollback

        Returns:
            New draft version

        Raises:
            ValueError: If a draft exists or no archived version found
        """
        existing_draft = await self.get_draft(agent_id)
        if existing_draft:
            raise ValueError(
                f"Cannot rollback: a draft (v{existing_draft.version_number}) already exists."
            )

        result = await self.session.execute(
            select(AgentPromptVersion)
            .where(
                AgentPromptVersion.agent_id == agent_id,
                AgentPromptVersion.status == VersionStatus.ARCHIVED.value,
            )
            .order_by(AgentPromptVersion.version_number.desc())
        )
        archived = result.scalar_one_or_none()
        if archived is None:
            raise ValueError("No archived version available for rollback")

        version_number = await self._next_version_number(agent_id)

        rollback_version = AgentPromptVersion(
            id=str(uuid4()),
            agent_id=agent_id,
            version_number=version_number,
            status=VersionStatus.DRAFT.value,
            prompt_template=archived.prompt_template,
            change_summary=f"Rollback from v{archived.version_number}",
        )
        self.session.add(rollback_version)
        await self.session.flush()
        return rollback_version

    async def delete_draft(self, version_id: str) -> bool:
        """Delete a draft prompt version.

        Args:
            version_id: Version ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If the version is not a draft
        """
        version = await self.get_by_id(version_id)
        if version is None:
            return False

        if version.status != VersionStatus.DRAFT.value:
            raise ValueError("Only draft versions can be deleted")

        await self.session.delete(version)
        await self.session.flush()
        return True
