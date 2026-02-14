"""Input helper creation tools for Home Assistant."""

from __future__ import annotations

from langchain_core.tools import tool

from src.ha import get_ha_client
from src.tracing import trace_with_uri


@tool("create_input_boolean")
@trace_with_uri(name="ha.create_input_boolean", span_type="TOOL")
async def create_input_boolean(
    input_id: str,
    name: str,
    initial: bool = False,
) -> str:
    """Create a virtual on/off switch (input_boolean).

    Useful for creating mode toggles like "guest_mode", "vacation_mode".
    The agent can then use these in automations.

    Args:
        input_id: Unique ID (e.g., "vacation_mode")
        name: Display name
        initial: Initial state (on/off)

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_input_boolean(
            input_id=input_id,
            name=name,
            initial=initial,
        )

        if result.get("success"):
            return f"✅ Input boolean '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create input_boolean: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create input_boolean: {exc}"


@tool("create_input_number")
@trace_with_uri(name="ha.create_input_number", span_type="TOOL")
async def create_input_number(
    input_id: str,
    name: str,
    min_value: float,
    max_value: float,
    initial: float | None = None,
    step: float = 1.0,
    unit_of_measurement: str | None = None,
) -> str:
    """Create a configurable number input (input_number).

    Useful for thresholds like "motion_timeout_minutes", "brightness_level".
    The agent can create and adjust these values.

    Args:
        input_id: Unique ID (e.g., "motion_timeout")
        name: Display name
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        initial: Starting value
        step: Increment step
        unit_of_measurement: Unit label (e.g., "minutes", "%")

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_input_number(
            input_id=input_id,
            name=name,
            min_value=min_value,
            max_value=max_value,
            initial=initial,
            step=step,
            unit_of_measurement=unit_of_measurement,
        )

        if result.get("success"):
            return f"✅ Input number '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create input_number: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create input_number: {exc}"


@tool("create_input_text")
@trace_with_uri(name="ha.create_input_text", span_type="TOOL")
async def create_input_text(
    input_id: str,
    name: str,
    min_length: int = 0,
    max_length: int = 100,
    pattern: str | None = None,
    mode: str = "text",
    initial: str | None = None,
) -> str:
    """Create a text input helper (input_text).

    Useful for storing user-editable text values like names, notes,
    or configuration strings.

    Args:
        input_id: Unique ID (e.g., "welcome_message")
        name: Display name
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regex pattern for validation
        mode: "text" or "password"
        initial: Starting value

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_input_text(
            input_id=input_id,
            name=name,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            mode=mode,
            initial=initial,
        )

        if result.get("success"):
            return f"✅ Input text '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create input_text: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create input_text: {exc}"


@tool("create_input_select")
@trace_with_uri(name="ha.create_input_select", span_type="TOOL")
async def create_input_select(
    input_id: str,
    name: str,
    options: list[str],
    initial: str | None = None,
) -> str:
    """Create a dropdown selection helper (input_select).

    Useful for mode selectors like "home_mode" with options
    ["home", "away", "vacation", "guest"].

    Args:
        input_id: Unique ID (e.g., "home_mode")
        name: Display name
        options: List of selectable options
        initial: Initially selected option

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_input_select(
            input_id=input_id,
            name=name,
            options=options,
            initial=initial,
        )

        if result.get("success"):
            return f"✅ Input select '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create input_select: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create input_select: {exc}"


@tool("create_input_datetime")
@trace_with_uri(name="ha.create_input_datetime", span_type="TOOL")
async def create_input_datetime(
    input_id: str,
    name: str,
    has_date: bool = True,
    has_time: bool = True,
    initial: str | None = None,
) -> str:
    """Create a date/time input helper (input_datetime).

    Useful for scheduling values like wake-up times or event dates.

    Args:
        input_id: Unique ID (e.g., "wakeup_time")
        name: Display name
        has_date: Include date component
        has_time: Include time component
        initial: Initial datetime string

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_input_datetime(
            input_id=input_id,
            name=name,
            has_date=has_date,
            has_time=has_time,
            initial=initial,
        )

        if result.get("success"):
            return f"✅ Input datetime '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create input_datetime: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create input_datetime: {exc}"


@tool("create_input_button")
@trace_with_uri(name="ha.create_input_button", span_type="TOOL")
async def create_input_button(
    input_id: str,
    name: str,
) -> str:
    """Create a button helper (input_button).

    Useful for triggering automations via a virtual button press.
    The button has no state—it fires a "pressed" event.

    Args:
        input_id: Unique ID (e.g., "reset_counters")
        name: Display name

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_input_button(
            input_id=input_id,
            name=name,
        )

        if result.get("success"):
            return f"✅ Input button '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create input_button: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create input_button: {exc}"


@tool("create_counter")
@trace_with_uri(name="ha.create_counter", span_type="TOOL")
async def create_counter(
    input_id: str,
    name: str,
    initial: int = 0,
    minimum: int | None = None,
    maximum: int | None = None,
    step: int = 1,
) -> str:
    """Create a counter helper.

    Useful for tracking counts like visitors, events, or retries.
    Supports increment, decrement, and reset.

    Args:
        input_id: Unique ID (e.g., "visitor_count")
        name: Display name
        initial: Starting count
        minimum: Minimum allowed value
        maximum: Maximum allowed value
        step: Increment/decrement step

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_counter(
            input_id=input_id,
            name=name,
            initial=initial,
            minimum=minimum,
            maximum=maximum,
            step=step,
        )

        if result.get("success"):
            return f"✅ Counter '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create counter: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create counter: {exc}"


@tool("create_timer")
@trace_with_uri(name="ha.create_timer", span_type="TOOL")
async def create_timer(
    input_id: str,
    name: str,
    duration: str | None = None,
) -> str:
    """Create a timer helper.

    Useful for countdown timers like "washing_machine" or "cooking".
    Fires events on start, pause, cancel, and finish.

    Args:
        input_id: Unique ID (e.g., "cooking_timer")
        name: Display name
        duration: Default duration in HH:MM:SS format (e.g., "00:30:00")

    Returns:
        Success or error message
    """
    ha = get_ha_client()
    try:
        result = await ha.create_timer(
            input_id=input_id,
            name=name,
            duration=duration,
        )

        if result.get("success"):
            return f"✅ Timer '{name}' created. Entity: {result.get('entity_id')}"
        else:
            return f"❌ Failed to create timer: {result.get('error')}"
    except Exception as exc:
        return f"❌ Failed to create timer: {exc}"
