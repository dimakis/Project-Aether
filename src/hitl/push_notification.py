"""Push notification HITL via Home Assistant actionable notifications.

Sends approval requests to the user's phone/watch via HA's
``notify.mobile_app_<device_name>`` service.  Actionable notifications
include Approve/Reject buttons that work on both iPhone and Apple Watch.

When the user taps a button, HA fires a ``mobile_app_notification_action``
event with the action identifier in ``event_data.action``.  This is caught
by the webhook handler and routed to ``handle_notification_action()``.

Configuration (via app settings or env):
    HITL_NOTIFY_SERVICE: HA notify service target
        (e.g. ``notify.mobile_app_dans_iphone``)
    HITL_CHANNEL: ``ui_only`` | ``push_only`` | ``both``
        (default: ``both``)
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_NOTIFY_SERVICE = "notify.mobile_app_iphone"
_DEFAULT_CHANNEL = "both"


async def _get_hitl_settings() -> tuple[str, str]:
    """Resolve HITL notify service and channel from DB settings or env.

    Returns:
        Tuple of (notify_service, channel).
    """
    try:
        from src.dal.app_settings import get_chat_setting

        service = await get_chat_setting("hitl_notify_service")
        channel = await get_chat_setting("hitl_channel")
        return (
            service or os.getenv("HITL_NOTIFY_SERVICE", _DEFAULT_NOTIFY_SERVICE),
            channel or os.getenv("HITL_CHANNEL", _DEFAULT_CHANNEL),
        )
    except Exception:
        return (
            os.getenv("HITL_NOTIFY_SERVICE", _DEFAULT_NOTIFY_SERVICE),
            os.getenv("HITL_CHANNEL", _DEFAULT_CHANNEL),
        )


async def send_approval_notification(
    proposal_id: str,
    title: str,
    description: str,
    notify_service: str | None = None,
) -> dict[str, Any]:
    """Send an actionable push notification for proposal approval.

    The notification includes Approve and Reject action buttons.
    Works on iPhone and Apple Watch via HA Companion App.

    Args:
        proposal_id: UUID of the proposal requiring approval.
        title: Short title for the notification.
        description: Description of the action being proposed.
        notify_service: Override the notify service target
            (e.g. ``notify.mobile_app_dans_iphone``).

    Returns:
        Dict with ``success``, ``service``, and ``error`` (if any).
    """
    configured_service, channel = await _get_hitl_settings()
    service = notify_service or configured_service

    if channel == "ui_only":
        return {"success": False, "service": service, "skipped": True, "reason": "ui_only channel"}

    try:
        from src.ha import get_ha_client

        ha = get_ha_client()
        parts = service.split(".", 1)
        if len(parts) != 2:
            return {
                "success": False,
                "service": service,
                "error": f"Invalid service format: {service}",
            }

        domain, svc_name = parts
        short_id = proposal_id[:8]

        # HA Companion App notification format:
        # https://companion.home-assistant.io/docs/notifications/actionable-notifications
        service_data: dict[str, Any] = {
            "message": description,
            "title": f"Aether: {title}",
            "data": {
                "actions": [
                    {
                        "action": f"APPROVE_{proposal_id}",
                        "title": "Approve",
                    },
                    {
                        "action": f"REJECT_{proposal_id}",
                        "title": "Reject",
                    },
                ],
                "push": {
                    "sound": "default",
                    "interruption-level": "time-sensitive",
                },
                "tag": f"aether-approval-{short_id}",
            },
        }

        result = await ha.call_service(domain, svc_name, service_data)

        # HA returns a list of changed states on success (typically []
        # for notifications).  A dict with "error" indicates failure.
        failed = isinstance(result, dict) and "error" in result
        if not failed:
            logger.info("Push notification sent for proposal %s via %s", short_id, service)
            return {"success": True, "service": service, "result": result}

        logger.warning("Push notification failed for proposal %s: %s", short_id, result)
        return {
            "success": False,
            "service": service,
            "error": result.get("error"),
            "result": result,
        }

    except Exception:
        logger.exception(
            "Failed to send push notification for proposal %s via %s", proposal_id[:8], service
        )
        return {
            "success": False,
            "service": service,
            "error": f"Failed to send approval notification via {service}; see server logs for details.",
        }


async def send_insight_notification(
    title: str,
    message: str,
    insight_id: str | None = None,
) -> dict[str, Any]:
    """Send a push notification for an actionable insight.

    Args:
        title: Notification title.
        message: Notification body text.
        insight_id: UUID of the specific insight (None for batch summary).

    Returns:
        Dict with ``success``, ``service``, and ``error`` (if any).
    """
    configured_service, channel = await _get_hitl_settings()

    if channel == "ui_only":
        return {
            "success": False,
            "service": configured_service,
            "skipped": True,
            "reason": "ui_only channel",
        }

    actions: list[dict[str, str]] = []
    if insight_id:
        actions.append({"action": f"INVESTIGATE_{insight_id}", "title": "Investigate"})
        actions.append({"action": f"DISMISS_{insight_id}", "title": "Dismiss"})
    else:
        actions.append({"action": "VIEW_INSIGHTS", "title": "Review All"})

    tag = f"aether-insight-{insight_id[:8]}" if insight_id else "aether-insights"

    try:
        from src.ha import get_ha_client

        ha = get_ha_client()
        parts = configured_service.split(".", 1)
        if len(parts) != 2:
            return {
                "success": False,
                "service": configured_service,
                "error": f"Invalid service format: {configured_service}",
            }

        domain, svc_name = parts
        service_data: dict[str, Any] = {
            "message": message,
            "title": f"Aether: {title}",
            "data": {
                "actions": actions,
                "push": {
                    "sound": "default",
                    "interruption-level": "active",
                },
                "tag": tag,
            },
        }

        result = await ha.call_service(domain, svc_name, service_data)

        failed = isinstance(result, dict) and "error" in result
        if not failed:
            logger.info(
                "Insight notification sent via %s (insight=%s)",
                configured_service,
                insight_id or "batch",
            )
            return {"success": True, "service": configured_service, "result": result}

        logger.warning("Insight notification failed: %s", result)
        return {
            "success": False,
            "service": configured_service,
            "error": result.get("error"),
            "result": result,
        }

    except Exception:
        logger.exception("Failed to send insight notification via %s", configured_service)
        return {
            "success": False,
            "service": configured_service,
            "error": f"Failed to send insight notification via {configured_service}; see server logs.",
        }


async def send_test_notification(
    notify_service: str,
    message: str = "This is a test notification from Aether.",
) -> dict[str, Any]:
    """Send a plain test notification (no actions) to verify the service works.

    Args:
        notify_service: HA notify service (e.g. ``notify.mobile_app_dans_iphone``).
        message: Message body.

    Returns:
        Dict with ``success``, ``service``, and ``error`` (if any).
    """
    try:
        from src.ha import get_ha_client

        ha = get_ha_client()
        parts = notify_service.split(".", 1)
        if len(parts) != 2:
            return {
                "success": False,
                "service": notify_service,
                "error": f"Invalid format: {notify_service}",
            }

        domain, svc_name = parts
        result = await ha.call_service(
            domain,
            svc_name,
            {"message": message, "title": "Aether Test"},
        )
        failed = isinstance(result, dict) and "error" in result
        if not failed:
            return {"success": True, "service": notify_service, "result": result}
        return {
            "success": False,
            "service": notify_service,
            "error": result.get("error"),
            "result": result,
        }

    except Exception:
        logger.exception("Failed to send test notification via %s", notify_service)
        return {
            "success": False,
            "service": notify_service,
            "error": f"Failed to send test notification via {notify_service}; see server logs for details.",
        }


async def discover_notify_services() -> list[str]:
    """Discover available notify.mobile_app_* services from HA.

    Returns:
        List of service IDs (e.g. ``["notify.mobile_app_dans_iphone"]``).
    """
    try:
        from src.ha import get_ha_client

        ha = get_ha_client()
        result = await ha._request("GET", "/api/services")
        services: list[str] = []
        if isinstance(result, list):
            for svc_domain in result:
                if svc_domain.get("domain") == "notify":
                    for svc in svc_domain.get("services", {}):
                        if svc.startswith("mobile_app_"):
                            services.append(f"notify.{svc}")
        return services
    except Exception:
        logger.warning("Failed to discover notify services", exc_info=True)
        return []


async def handle_notification_action(action_id: str) -> dict[str, Any]:
    """Handle an actionable notification callback from HA.

    Called when the user taps Approve or Reject on their phone/watch.
    HA fires ``mobile_app_notification_action`` with ``event_data.action``
    set to ``APPROVE_{proposal_id}`` or ``REJECT_{proposal_id}``.

    Args:
        action_id: The action identifier from the HA notification event.

    Returns:
        Dict with ``status``, ``proposal_id``, and ``action`` keys.
    """
    from src.dal import ProposalRepository
    from src.storage import get_session

    if action_id.startswith("APPROVE_"):
        proposal_id = action_id[len("APPROVE_") :]
        action = "approve"
    elif action_id.startswith("REJECT_"):
        proposal_id = action_id[len("REJECT_") :]
        action = "reject"
    else:
        logger.warning("Unknown notification action: %s", action_id)
        return {"status": "ignored", "action_id": action_id}

    try:
        async with get_session() as session:
            repo = ProposalRepository(session)

            if action == "approve":
                result = await repo.approve(proposal_id, approved_by="push_notification")
            else:
                result = await repo.reject(proposal_id, reason="Rejected via push notification")

            await session.commit()

            if result:
                logger.info("Proposal %s %sd via push notification", proposal_id[:8], action)
                return {"status": "success", "proposal_id": proposal_id, "action": action}

            logger.warning("Proposal %s not found for %s", proposal_id[:8], action)
            return {"status": "not_found", "proposal_id": proposal_id, "action": action}

    except Exception:
        logger.exception("Failed to %s proposal %s via push notification", action, proposal_id[:8])
        return {"status": "error", "proposal_id": proposal_id, "action": action}
