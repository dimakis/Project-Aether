"""Agent configuration cache for runtime model/prompt resolution.

Feature 23: Agent Configuration.

Provides a lightweight async cache for active agent configurations
so that DB-backed per-agent settings can be resolved without
querying the database on every LLM call.

Cache is invalidated on config/prompt promotion or rollback
via invalidate_agent_config().
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Cache TTL in seconds (configs are rarely changed; 60s is reasonable)
_CACHE_TTL = 60

# In-memory cache: agent_name -> CachedAgentConfig
_cache: dict[str, _CacheEntry] = {}


@dataclass
class AgentRuntimeConfig:
    """Resolved runtime configuration for an agent.

    Contains the active model settings and prompt template
    loaded from the database.
    """

    agent_id: str
    agent_name: str
    status: str
    model_name: str | None = None
    temperature: float | None = None
    fallback_model: str | None = None
    tools_enabled: list[str] | None = None
    prompt_template: str | None = None


@dataclass
class _CacheEntry:
    """Internal cache entry with TTL tracking."""

    config: AgentRuntimeConfig
    fetched_at: float = field(default_factory=time.monotonic)

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.fetched_at) > _CACHE_TTL


async def get_agent_runtime_config(agent_name: str) -> AgentRuntimeConfig | None:
    """Get the runtime config for an agent (cached).

    Checks the in-memory cache first. On miss or expiry, queries the
    database for the agent's active config and prompt versions.

    Args:
        agent_name: Agent identifier (e.g. 'architect', 'data_scientist')

    Returns:
        AgentRuntimeConfig or None if agent not found in DB
    """
    # Check cache
    entry = _cache.get(agent_name)
    if entry and not entry.is_expired:
        return entry.config

    # Cache miss or expired — fetch from DB
    try:
        from src.dal.agents import (
            AgentConfigVersionRepository,
            AgentPromptVersionRepository,
            AgentRepository,
        )
        from src.storage import get_session

        async with get_session() as session:
            agent_repo = AgentRepository(session)
            agent = await agent_repo.get_by_name(agent_name)
            if agent is None:
                return None

            config_repo = AgentConfigVersionRepository(session)
            prompt_repo = AgentPromptVersionRepository(session)

            active_config = await config_repo.get_active(agent.id)
            active_prompt = await prompt_repo.get_active(agent.id)

            runtime_config = AgentRuntimeConfig(
                agent_id=agent.id,
                agent_name=agent.name,
                status=agent.status,
                model_name=active_config.model_name if active_config else None,
                temperature=active_config.temperature if active_config else None,
                fallback_model=active_config.fallback_model if active_config else None,
                tools_enabled=active_config.tools_enabled if active_config else None,
                prompt_template=active_prompt.prompt_template if active_prompt else None,
            )

            _cache[agent_name] = _CacheEntry(config=runtime_config)
            return runtime_config

    except Exception:
        logger.exception("Failed to load agent config for %s", agent_name)
        # Return stale cache entry if available
        if entry:
            return entry.config
        return None


def invalidate_agent_config(agent_name: str | None = None) -> None:
    """Invalidate cached agent configuration.

    Called after config/prompt promotion or rollback to ensure
    agents pick up the new settings.

    Args:
        agent_name: Specific agent to invalidate, or None for all
    """
    if agent_name:
        _cache.pop(agent_name, None)
        logger.debug("Invalidated config cache for agent: %s", agent_name)
    else:
        _cache.clear()
        logger.debug("Invalidated all agent config caches")


def clear_config_cache() -> None:
    """Clear the entire config cache. Used in tests."""
    _cache.clear()
