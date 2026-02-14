"""Agent configuration CRUD API.

Feature 23: Agent Configuration Page.

Provides endpoints for managing agents and their versioned LLM
configurations (model settings and prompt templates) with
draft -> active -> archived promotion lifecycle.
"""

from __future__ import annotations

from fastapi import APIRouter

from .config_versions import router as config_versions_router
from .core import router as core_router
from .prompt_versions import router as prompt_versions_router
from .schemas import (
    AgentConfigVersionCreate,
    AgentConfigVersionUpdate,
    AgentListResponse,
    AgentPromptVersionCreate,
    AgentResponse,
    AgentStatusUpdate,
    ConfigVersionResponse,
    PromoteBothResponse,
    PromptGenerateRequest,
    PromptGenerateResponse,
    PromptVersionResponse,
    QuickModelSwitch,
)
from .seed import router as seed_router

# Combined router - include each sub-router with prefix to avoid "prefix and path both empty" error
router = APIRouter(tags=["Agents"])
router.include_router(core_router, prefix="/agents")
router.include_router(config_versions_router, prefix="/agents")
router.include_router(prompt_versions_router, prefix="/agents")
router.include_router(seed_router, prefix="/agents")

# Re-exports for backward compatibility (tests import from src.api.routes.agents)
from .config_versions import promote_config_version
from .core import (
    clone_agent,
    get_agent,
    list_agents,
    quick_model_switch,
    update_agent_status,
)
from .prompt_versions import create_prompt_version, generate_prompt, promote_both
from .seed import seed_agents

__all__ = [
    "AgentConfigVersionCreate",
    "AgentConfigVersionUpdate",
    "AgentListResponse",
    "AgentPromptVersionCreate",
    "AgentResponse",
    "AgentStatusUpdate",
    "ConfigVersionResponse",
    "PromoteBothResponse",
    "PromptGenerateRequest",
    "PromptGenerateResponse",
    "PromptVersionResponse",
    "QuickModelSwitch",
    "clone_agent",
    "create_prompt_version",
    "generate_prompt",
    "get_agent",
    "list_agents",
    "promote_both",
    "promote_config_version",
    "quick_model_switch",
    "router",
    "seed_agents",
    "update_agent_status",
]
