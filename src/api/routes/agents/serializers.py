"""Serialization helpers for Agent Configuration API."""

from __future__ import annotations

from typing import Any


def _serialize_config(cv: Any) -> dict[str, Any]:
    """Serialize a config version to response dict."""
    return {
        "id": cv.id,
        "agent_id": cv.agent_id,
        "version_number": cv.version_number,
        "version": getattr(cv, "version", None),
        "status": cv.status,
        "model_name": cv.model_name,
        "temperature": cv.temperature,
        "fallback_model": cv.fallback_model,
        "tools_enabled": cv.tools_enabled,
        "change_summary": cv.change_summary,
        "promoted_at": cv.promoted_at.isoformat() if cv.promoted_at else None,
        "created_at": cv.created_at.isoformat() if cv.created_at else "",
        "updated_at": cv.updated_at.isoformat() if cv.updated_at else "",
    }


def _serialize_prompt(pv: Any) -> dict[str, Any]:
    """Serialize a prompt version to response dict."""
    return {
        "id": pv.id,
        "agent_id": pv.agent_id,
        "version_number": pv.version_number,
        "version": getattr(pv, "version", None),
        "status": pv.status,
        "prompt_template": pv.prompt_template,
        "change_summary": pv.change_summary,
        "promoted_at": pv.promoted_at.isoformat() if pv.promoted_at else None,
        "created_at": pv.created_at.isoformat() if pv.created_at else "",
        "updated_at": pv.updated_at.isoformat() if pv.updated_at else "",
    }


def _serialize_agent(
    agent: Any, active_config: Any = None, active_prompt: Any = None
) -> dict[str, Any]:
    """Serialize an agent to response dict."""
    result: dict[str, Any] = {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "version": agent.version,
        "status": agent.status,
        "active_config_version_id": agent.active_config_version_id,
        "active_prompt_version_id": agent.active_prompt_version_id,
        "active_config": _serialize_config(active_config) if active_config else None,
        "active_prompt": _serialize_prompt(active_prompt) if active_prompt else None,
        "created_at": agent.created_at.isoformat() if agent.created_at else "",
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else "",
    }
    return result
