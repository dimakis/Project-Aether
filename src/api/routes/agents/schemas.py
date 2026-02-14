"""Pydantic request/response schemas for Agent Configuration API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentConfigVersionCreate(BaseModel):
    """Request body for creating a config version draft."""

    model_name: str | None = Field(default=None, max_length=100)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    fallback_model: str | None = Field(default=None, max_length=100)
    tools_enabled: list[str] | None = None
    change_summary: str | None = Field(default=None, max_length=2000)
    bump_type: str = Field(default="patch", pattern="^(major|minor|patch)$")


class AgentConfigVersionUpdate(BaseModel):
    """Request body for updating a config version draft."""

    model_name: str | None = Field(default=None, max_length=100)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    fallback_model: str | None = Field(default=None, max_length=100)
    tools_enabled: list[str] | None = None
    change_summary: str | None = Field(default=None, max_length=2000)


class AgentPromptVersionCreate(BaseModel):
    """Request body for creating a prompt version draft."""

    prompt_template: str = Field(..., min_length=1, max_length=50_000)
    change_summary: str | None = Field(default=None, max_length=2000)
    bump_type: str = Field(default="patch", pattern="^(major|minor|patch)$")


class AgentPromptVersionUpdate(BaseModel):
    """Request body for updating a prompt version draft."""

    prompt_template: str | None = Field(default=None, max_length=50_000)
    change_summary: str | None = Field(default=None, max_length=2000)


class AgentStatusUpdate(BaseModel):
    """Request body for updating agent status."""

    status: str = Field(..., max_length=20, pattern="^(disabled|enabled|primary)$")


class QuickModelSwitch(BaseModel):
    """Request body for quick model switch (create + promote in one step)."""

    model_name: str = Field(..., min_length=1, max_length=100)


class ConfigVersionResponse(BaseModel):
    """Response schema for a config version."""

    id: str
    agent_id: str
    version_number: int
    version: str | None = None
    status: str
    model_name: str | None
    temperature: float | None
    fallback_model: str | None
    tools_enabled: list[str] | None
    change_summary: str | None
    promoted_at: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PromptVersionResponse(BaseModel):
    """Response schema for a prompt version."""

    id: str
    agent_id: str
    version_number: int
    version: str | None = None
    status: str
    prompt_template: str
    change_summary: str | None
    promoted_at: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    """Response schema for an agent."""

    id: str
    name: str
    description: str
    version: str
    status: str
    active_config_version_id: str | None
    active_prompt_version_id: str | None
    active_config: ConfigVersionResponse | None = None
    active_prompt: PromptVersionResponse | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Response schema for agent list."""

    agents: list[AgentResponse]
    total: int


class PromoteBothResponse(BaseModel):
    """Response schema for promoting both config and prompt drafts."""

    config: ConfigVersionResponse | None = None
    prompt: PromptVersionResponse | None = None
    message: str


class PromptGenerateRequest(BaseModel):
    """Request body for AI-assisted prompt generation."""

    user_input: str | None = Field(
        default=None,
        max_length=5000,
        description="Custom instructions for prompt generation",
    )


class PromptGenerateResponse(BaseModel):
    """Response from prompt generation."""

    generated_prompt: str
    agent_name: str
    agent_role: str
