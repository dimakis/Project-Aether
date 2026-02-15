"""Utility tools for Home Assistant: events, notifications, templates, diagnostics."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.ha import get_ha_client
from src.tracing import trace_with_uri


@tool("fire_event")
@trace_with_uri(name="ha.fire_event", span_type="TOOL")
async def fire_event(
    event_type: str,
    event_data: dict[str, Any] | None = None,
) -> str:
    """Fire a custom event in Home Assistant.

    Events can trigger automations. Useful for signaling state changes
    or coordinating between automations.

    Args:
        event_type: Event name (e.g., "aether_analysis_complete")
        event_data: Optional data to include with the event

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.fire_event(event_type, event_data)

        if result.get("success"):
            return f"✅ Event '{event_type}' fired."
        else:
            return f"❌ Failed to fire event: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to fire event: {exc}"


@tool("send_ha_notification")
@trace_with_uri(name="ha.send_notification", span_type="TOOL")
async def send_ha_notification(
    title: str,
    message: str,
    target: str = "notify.notify",
    data: dict[str, Any] | None = None,
) -> str:
    """Send a notification via Home Assistant's notify service.

    Uses HA service calls to send push notifications, emails, or other
    notification targets configured in Home Assistant.

    Args:
        title: Notification title
        message: Notification body text
        target: Notify service target (default: 'notify.notify').
            Examples: 'notify.mobile_app_phone', 'notify.email'
        data: Optional extra data for the notification platform
            (e.g., {"push": {"sound": "default"}})

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        # Split target into domain.service
        parts = target.split(".", 1)
        if len(parts) != 2:
            return f"❌ Invalid target format: '{target}'. Use 'notify.service_name'."

        domain, service = parts
        service_data: dict[str, Any] = {
            "title": title,
            "message": message,
        }
        if data:
            service_data["data"] = data

        result = await ha.call_service(domain, service, service_data)

        if result.get("success"):
            return f"✅ Notification sent via '{target}'."
        else:
            return f"❌ Failed to send notification: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to send notification: {exc}"


@tool("render_template")
@trace_with_uri(name="ha.render_template", span_type="TOOL")
async def render_template(template: str) -> str:
    """Render a Jinja2 template via HA's template engine.

    Args:
        template: Jinja2 template string
    """
    ha = get_ha_client()
    try:
        result = await ha.render_template(template)
        if result is not None:
            return f"Result: {result}"
        else:
            return "❌ Failed to render template"
    except Exception as exc:
        return f"❌ Failed to render template: {exc}"


@tool("get_ha_logs")
@trace_with_uri(name="ha.get_ha_logs", span_type="TOOL")
async def get_ha_logs() -> str:
    """Get recent HA error/warning log entries."""
    ha = get_ha_client()
    try:
        log_text = await ha.get_error_log()
        if not log_text:
            return "No errors found in the Home Assistant log."

        # Truncate for LLM context window
        if len(log_text) > 4000:
            log_text = log_text[-4000:]
            return f"**HA Error Log** (last ~4000 chars):\n\n{log_text}"

        return f"**HA Error Log**:\n\n{log_text}"
    except Exception as exc:
        return f"Failed to retrieve HA logs: {exc}"


@tool("check_ha_config")
@trace_with_uri(name="ha.check_ha_config", span_type="TOOL")
async def check_ha_config() -> str:
    """Check HA configuration validity."""
    ha = get_ha_client()
    try:
        result = await ha.check_config()
        status = result.get("result", "unknown")

        if status == "valid":
            return "HA configuration is valid. No errors found."

        errors = result.get("errors", "")
        return f"HA configuration check result: {status}\n\nDetails:\n{errors}"
    except Exception as exc:
        return f"Failed to check HA config: {exc}"
