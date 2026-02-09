"""Workflow presets API.

Provides endpoints for listing available workflow presets
that define agent compositions for different task types.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from src.graph.state import DEFAULT_WORKFLOW_PRESETS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


# ─── Response Schemas ──────────────────────────────────────────────────────────


class WorkflowPresetResponse(BaseModel):
    """Response schema for a single workflow preset."""

    id: str
    name: str
    description: str
    agents: list[str]
    workflow_key: str
    icon: str | None = None


class WorkflowPresetsListResponse(BaseModel):
    """Response schema for listing workflow presets."""

    presets: list[WorkflowPresetResponse]
    total: int


# ─── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/presets", response_model=WorkflowPresetsListResponse)
async def list_workflow_presets() -> WorkflowPresetsListResponse:
    """List available workflow presets.

    Returns all preset workflow configurations that define which agents
    participate in different task types. Used by the chat interface to
    offer quick-start workflow templates and agent customization.
    """
    presets = [
        WorkflowPresetResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            agents=p.agents,
            workflow_key=p.workflow_key,
            icon=p.icon,
        )
        for p in DEFAULT_WORKFLOW_PRESETS
    ]
    return WorkflowPresetsListResponse(presets=presets, total=len(presets))
