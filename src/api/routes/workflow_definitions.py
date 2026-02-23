"""Workflow Definition CRUD API (Feature 29).

POST   /api/v1/workflows/definitions     — create
GET    /api/v1/workflows/definitions     — list all
GET    /api/v1/workflows/definitions/{id} — get one
DELETE /api/v1/workflows/definitions/{id} — soft-delete (status -> archived)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.storage import get_session
from src.storage.entities.workflow_definition import WorkflowDefinitionEntity

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Workflows"])


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a workflow definition."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    state_type: str = Field(..., max_length=100)
    nodes: list[dict[str, Any]] = Field(..., min_length=1, max_length=100)
    edges: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    conditional_edges: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    intent_patterns: list[str] = Field(default_factory=list, max_length=30)


class WorkflowResponse(BaseModel):
    """Response for a workflow definition."""

    id: str
    name: str
    description: str
    state_type: str
    version: int
    status: str
    config: dict[str, Any]
    intent_patterns: list[str]
    created_by: str | None
    created_at: str
    updated_at: str


class WorkflowListResponse(BaseModel):
    """Response for listing workflow definitions."""

    definitions: list[WorkflowResponse]
    total: int


def _serialize(entity: WorkflowDefinitionEntity) -> WorkflowResponse:
    return WorkflowResponse(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        state_type=entity.state_type,
        version=entity.version,
        status=entity.status,
        config=entity.config or {},
        intent_patterns=entity.intent_patterns or [],
        created_by=entity.created_by,
        created_at=str(entity.created_at),
        updated_at=str(entity.updated_at),
    )


@router.post("/workflows/definitions", response_model=WorkflowResponse, status_code=201)
async def create_workflow_definition(body: WorkflowCreateRequest) -> WorkflowResponse:
    """Create a new workflow definition.

    Validates the workflow topology (node functions, edges, cycles)
    against the default manifest before persisting.
    """
    from src.graph.workflows.compiler import WorkflowCompiler
    from src.graph.workflows.definition import (
        ConditionalEdge,
        EdgeDefinition,
        NodeDefinition,
        WorkflowDefinition,
    )
    from src.graph.workflows.manifest import get_default_manifest

    try:
        defn = WorkflowDefinition(
            name=body.name,
            description=body.description,
            state_type=body.state_type,
            nodes=[NodeDefinition(**n) for n in body.nodes],
            edges=[EdgeDefinition(**e) for e in body.edges],
            conditional_edges=[ConditionalEdge(**ce) for ce in body.conditional_edges],
            intent_patterns=body.intent_patterns,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid workflow schema: {e}") from e

    compiler = WorkflowCompiler(get_default_manifest())
    errors = compiler.validate(defn)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    async with get_session() as session:
        entity = await _create_definition(session, body)
        await session.commit()
        return _serialize(entity)


@router.get("/workflows/definitions", response_model=WorkflowListResponse)
async def list_workflow_definitions() -> WorkflowListResponse:
    """List all workflow definitions (excluding archived)."""
    async with get_session() as session:
        entities = await _list_definitions(session)
        items = [_serialize(e) for e in entities]
        return WorkflowListResponse(definitions=items, total=len(items))


@router.get("/workflows/definitions/{definition_id}", response_model=WorkflowResponse)
async def get_workflow_definition(definition_id: str) -> WorkflowResponse:
    """Get a single workflow definition by ID."""
    async with get_session() as session:
        entity = await _get_definition(session, definition_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
        return _serialize(entity)


@router.delete("/workflows/definitions/{definition_id}")
async def delete_workflow_definition(definition_id: str) -> dict[str, str]:
    """Soft-delete a workflow definition (set status to archived)."""
    async with get_session() as session:
        entity = await _get_definition(session, definition_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
        await _delete_definition(session, entity)
        await session.commit()
        return {"status": "archived", "id": definition_id}


async def _create_definition(
    session: Any,
    body: WorkflowCreateRequest,
) -> WorkflowDefinitionEntity:
    """Create a WorkflowDefinitionEntity from the request body."""
    entity = WorkflowDefinitionEntity(
        id=str(uuid4()),
        name=body.name,
        description=body.description,
        state_type=body.state_type,
        config={
            "nodes": body.nodes,
            "edges": body.edges,
            "conditional_edges": body.conditional_edges,
        },
        intent_patterns=body.intent_patterns,
    )
    entity.created_at = datetime.now(UTC)
    entity.updated_at = datetime.now(UTC)
    session.add(entity)
    return entity


async def _list_definitions(session: Any) -> list[WorkflowDefinitionEntity]:
    """List non-archived workflow definitions."""
    result = await session.execute(
        select(WorkflowDefinitionEntity)
        .where(WorkflowDefinitionEntity.status != "archived")
        .order_by(WorkflowDefinitionEntity.name)
    )
    return list(result.scalars().all())


async def _get_definition(
    session: Any,
    definition_id: str,
) -> WorkflowDefinitionEntity | None:
    """Get a single workflow definition by ID."""
    result = await session.execute(
        select(WorkflowDefinitionEntity).where(WorkflowDefinitionEntity.id == definition_id)
    )
    row: WorkflowDefinitionEntity | None = result.scalar_one_or_none()
    return row


async def _delete_definition(
    session: Any,
    entity: WorkflowDefinitionEntity,
) -> bool:
    """Soft-delete by setting status to archived."""
    entity.status = "archived"
    entity.updated_at = datetime.now(UTC)
    return True
