"""HITL push notification test and configuration endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.api.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hitl", tags=["HITL"])


class TestNotificationRequest(BaseModel):
    """Request body for sending a test notification."""

    notify_service: str = Field(
        ...,
        description="HA notify service (e.g. 'notify.mobile_app_dans_iphone')",
        examples=["notify.mobile_app_dans_iphone"],
    )
    message: str = Field(
        default="This is a test notification from Aether.",
        description="Test message body",
    )


class TestApprovalRequest(BaseModel):
    """Request body for sending a test approval notification."""

    notify_service: str = Field(
        ...,
        description="HA notify service (e.g. 'notify.mobile_app_dans_iphone')",
    )
    title: str = Field(default="Test Action", description="Proposal title")
    description: str = Field(
        default="Preheat oven to 200C for pizza",
        description="Action description shown in the notification",
    )


@router.get("/notify-services")
@limiter.limit("10/minute")
async def list_notify_services(request: Request) -> dict[str, Any]:
    """Discover available notify.mobile_app_* services from HA."""
    from src.hitl.push_notification import discover_notify_services

    services = await discover_notify_services()
    return {"services": services, "count": len(services)}


@router.post("/test-notification")
@limiter.limit("5/minute")
async def test_notification(
    request: Request,
    body: TestNotificationRequest,
) -> dict[str, Any]:
    """Send a plain test notification to verify the service works."""
    from src.hitl.push_notification import send_test_notification

    return await send_test_notification(
        notify_service=body.notify_service,
        message=body.message,
    )


@router.post("/test-approval")
@limiter.limit("5/minute")
async def test_approval(
    request: Request,
    body: TestApprovalRequest,
) -> dict[str, Any]:
    """Send a test actionable approval notification with Approve/Reject buttons."""
    from uuid import uuid4

    from src.hitl.push_notification import send_approval_notification

    test_proposal_id = str(uuid4())
    result = await send_approval_notification(
        proposal_id=test_proposal_id,
        title=body.title,
        description=body.description,
        notify_service=body.notify_service,
    )
    result["test_proposal_id"] = test_proposal_id
    return result


@router.get("/action-status/{proposal_id}")
@limiter.limit("60/minute")
async def get_action_status(request: Request, proposal_id: str) -> dict[str, Any]:
    """Check if a notification action (Approve/Reject) has been received.

    The test page polls this after sending an approval notification.
    Returns the action taken if the webhook has been received, or
    ``{"received": false}`` if still waiting.
    """
    from src.hitl.action_log import get_action_for_proposal

    entry = get_action_for_proposal(proposal_id)
    if entry:
        return {
            "received": True,
            "action": entry.action,
            "status": entry.status,
            "timestamp": entry.timestamp,
        }
    return {"received": False}


@router.get("/recent-actions")
@limiter.limit("30/minute")
async def list_recent_actions(request: Request) -> dict[str, Any]:
    """List recent notification actions received via webhook."""
    from src.hitl.action_log import get_recent_actions

    actions = get_recent_actions(limit=20)
    return {"actions": actions, "count": len(actions)}
