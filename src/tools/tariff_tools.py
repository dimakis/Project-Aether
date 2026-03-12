"""Electricity tariff management tools.

Allows the Architect to update electricity tariff rates via HITL approval
and to perform one-time setup of the required HA helpers and automation.

Feature 40: Electricity Tariff Management.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from src.tools.approval_tools import seek_approval
from src.tracing import trace_with_uri

logger = logging.getLogger(__name__)

TARIFF_ENTITY_IDS = {
    "day": "input_number.electricity_rate_day",
    "night": "input_number.electricity_rate_night",
    "peak": "input_number.electricity_rate_peak",
    "current": "input_number.electricity_rate_current",
    "plan_name": "input_text.electricity_plan_name",
    "period": "input_select.electricity_tariff_period",
}

TARIFF_SCHEDULE = {
    "day": {"start": "08:00", "end": "23:00"},
    "night": {"start": "23:00", "end": "08:00"},
    "peak": {"start": "17:00", "end": "19:00"},
}


@tool("update_electricity_tariffs")
@trace_with_uri(name="tariff.update", span_type="TOOL")
async def update_electricity_tariffs(
    day_rate: float,
    night_rate: float,
    peak_rate: float,
    plan_name: str = "Electricity Plan",
) -> str:
    """Update electricity tariff rates via HITL approval.

    The user pastes tariff information in chat, the Architect extracts
    rates and calls this tool. A proposal is created for user review
    before the HA helpers are updated.

    Args:
        day_rate: Day rate in c/kWh (e.g. 25.84)
        night_rate: Night rate in c/kWh (e.g. 13.54)
        peak_rate: Peak rate in c/kWh (e.g. 29.18)
        plan_name: Tariff plan name (e.g. "Yuno ETV06")

    Returns:
        Proposal submission result.
    """
    for label, value in [("day", day_rate), ("night", night_rate), ("peak", peak_rate)]:
        if value <= 0:
            return f"Invalid rate: {label}_rate must be positive (got {value})"

    description = (
        f"Update electricity tariffs to: "
        f"Day {day_rate} c/kWh, Night {night_rate} c/kWh, Peak {peak_rate} c/kWh. "
        f"Plan: {plan_name}"
    )

    service_data = {
        "rates": {
            "day": day_rate,
            "night": night_rate,
            "peak": peak_rate,
        },
        "plan_name": plan_name,
        "entity_updates": [
            {"entity_id": TARIFF_ENTITY_IDS["day"], "value": day_rate},
            {"entity_id": TARIFF_ENTITY_IDS["night"], "value": night_rate},
            {"entity_id": TARIFF_ENTITY_IDS["peak"], "value": peak_rate},
            {"entity_id": TARIFF_ENTITY_IDS["plan_name"], "value": plan_name},
        ],
    }

    result = await seek_approval.ainvoke(
        {
            "action_type": "entity_command",
            "name": "Update Electricity Tariffs",
            "description": description,
            "entity_id": TARIFF_ENTITY_IDS["day"],
            "service_domain": "input_number",
            "service_action": "set_value",
            "service_data": service_data,
        }
    )
    return str(result)


@tool("setup_electricity_tariffs")
@trace_with_uri(name="tariff.setup", span_type="TOOL")
async def setup_electricity_tariffs(
    day_rate: float = 25.84,
    night_rate: float = 13.54,
    peak_rate: float = 29.18,
    plan_name: str = "Electricity Plan",
) -> str:
    """One-time setup of electricity tariff HA helpers and automation.

    Creates input_number helpers for day/night/peak/current rates,
    an input_text for the plan name, an input_select for the current
    period, and a time-based automation to switch rates automatically.

    All proposals require HITL approval before execution.

    Args:
        day_rate: Initial day rate in c/kWh
        night_rate: Initial night rate in c/kWh
        peak_rate: Initial peak rate in c/kWh
        plan_name: Tariff plan name

    Returns:
        Summary of proposals submitted.
    """
    results: list[str] = []

    helper_configs: list[dict[str, Any]] = [
        {
            "helper_type": "input_number",
            "input_id": "electricity_rate_day",
            "name": "Electricity Rate Day",
            "min": 0,
            "max": 100,
            "step": 0.01,
            "initial": day_rate,
            "unit_of_measurement": "c/kWh",
            "icon": "mdi:weather-sunny",
        },
        {
            "helper_type": "input_number",
            "input_id": "electricity_rate_night",
            "name": "Electricity Rate Night",
            "min": 0,
            "max": 100,
            "step": 0.01,
            "initial": night_rate,
            "unit_of_measurement": "c/kWh",
            "icon": "mdi:weather-night",
        },
        {
            "helper_type": "input_number",
            "input_id": "electricity_rate_peak",
            "name": "Electricity Rate Peak",
            "min": 0,
            "max": 100,
            "step": 0.01,
            "initial": peak_rate,
            "unit_of_measurement": "c/kWh",
            "icon": "mdi:flash-alert",
        },
        {
            "helper_type": "input_number",
            "input_id": "electricity_rate_current",
            "name": "Electricity Rate Current",
            "min": 0,
            "max": 100,
            "step": 0.01,
            "initial": day_rate,
            "unit_of_measurement": "c/kWh",
            "icon": "mdi:flash",
        },
        {
            "helper_type": "input_text",
            "input_id": "electricity_plan_name",
            "name": "Electricity Plan Name",
            "initial": plan_name,
            "min": 0,
            "max": 255,
            "icon": "mdi:file-document-outline",
        },
        {
            "helper_type": "input_select",
            "input_id": "electricity_tariff_period",
            "name": "Electricity Tariff Period",
            "options": ["day", "night", "peak"],
            "initial": "day",
            "icon": "mdi:clock-outline",
        },
    ]

    for config in helper_configs:
        r = await seek_approval.ainvoke(
            {
                "action_type": "helper",
                "name": f"Create {config['name']}",
                "description": f"Create {config['helper_type']} helper for electricity tariff tracking.",
                "helper_config": config,
            }
        )
        results.append(r)

    automation_result = await seek_approval.ainvoke(
        {
            "action_type": "automation",
            "name": "Electricity Tariff Period Switcher",
            "description": (
                "Automatically switches the current electricity rate and tariff "
                "period based on time of day: Day 08:00-17:00 & 19:00-23:00, "
                "Peak 17:00-19:00, Night 23:00-08:00."
            ),
            "trigger": [
                {"platform": "time", "at": "08:00:00"},
                {"platform": "time", "at": "17:00:00"},
                {"platform": "time", "at": "19:00:00"},
                {"platform": "time", "at": "23:00:00"},
            ],
            "actions": [
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "time",
                                    "after": "08:00:00",
                                    "before": "17:00:00",
                                }
                            ],
                            "sequence": [
                                _set_rate_action("day"),
                                _set_period_action("day"),
                            ],
                        },
                        {
                            "conditions": [
                                {
                                    "condition": "time",
                                    "after": "17:00:00",
                                    "before": "19:00:00",
                                }
                            ],
                            "sequence": [
                                _set_rate_action("peak"),
                                _set_period_action("peak"),
                            ],
                        },
                        {
                            "conditions": [
                                {
                                    "condition": "time",
                                    "after": "19:00:00",
                                    "before": "23:00:00",
                                }
                            ],
                            "sequence": [
                                _set_rate_action("day"),
                                _set_period_action("day"),
                            ],
                        },
                    ],
                    "default": [
                        _set_rate_action("night"),
                        _set_period_action("night"),
                    ],
                }
            ],
        }
    )
    results.append(automation_result)

    helper_count = len(helper_configs)
    return (
        f"Submitted {helper_count} helper proposals and 1 automation proposal "
        f"for electricity tariff setup. Please review them on the Proposals page."
    )


def _resolve_current_period() -> str:
    """Determine the current tariff period from TARIFF_SCHEDULE and local time."""
    from datetime import datetime as _dt

    now = _dt.now()
    t = now.hour * 60 + now.minute

    peak_start = 17 * 60  # 17:00
    peak_end = 19 * 60  # 19:00
    day_start = 8 * 60  # 08:00
    night_start = 23 * 60  # 23:00

    if peak_start <= t < peak_end:
        return "peak"
    if day_start <= t < night_start:
        return "day"
    return "night"


async def get_tariff_rates(ha_client: Any) -> dict[str, Any]:
    """Read current tariff rates from HA entities.

    Used by the Energy Analyst and the API endpoint to retrieve
    the current tariff configuration.

    Args:
        ha_client: HAClient instance.

    Returns:
        Tariff data dict with configured flag, rates, and schedule.
    """
    day_entity = await ha_client.get_entity(TARIFF_ENTITY_IDS["day"], detailed=False)
    if day_entity is None:
        return {"configured": False}

    night_entity = await ha_client.get_entity(TARIFF_ENTITY_IDS["night"], detailed=False)
    peak_entity = await ha_client.get_entity(TARIFF_ENTITY_IDS["peak"], detailed=False)
    current_entity = await ha_client.get_entity(TARIFF_ENTITY_IDS["current"], detailed=False)
    plan_entity = await ha_client.get_entity(TARIFF_ENTITY_IDS["plan_name"], detailed=False)
    period_entity = await ha_client.get_entity(TARIFF_ENTITY_IDS["period"], detailed=False)

    def _float_state(entity: dict[str, Any] | None) -> float:
        if entity is None:
            return 0.0
        try:
            return float(entity.get("state", 0))
        except (ValueError, TypeError):
            return 0.0

    def _str_state(entity: dict[str, Any] | None, default: str = "") -> str:
        if entity is None:
            return default
        return str(entity.get("state", default))

    day_rate = _float_state(day_entity)
    night_rate = _float_state(night_entity)
    peak_rate = _float_state(peak_entity)

    ha_period = _str_state(period_entity, "")
    current_period = (
        ha_period if ha_period in ("day", "night", "peak") else _resolve_current_period()
    )

    period_rates = {"day": day_rate, "night": night_rate, "peak": peak_rate}
    current_rate = _float_state(current_entity)
    if current_rate == 0.0 and current_period in period_rates:
        current_rate = period_rates[current_period]

    return {
        "configured": True,
        "plan_name": _str_state(plan_entity, "Unknown Plan"),
        "current_period": current_period,
        "current_rate": current_rate,
        "rates": {
            "day": {"rate": day_rate, **TARIFF_SCHEDULE["day"]},
            "night": {"rate": night_rate, **TARIFF_SCHEDULE["night"]},
            "peak": {"rate": peak_rate, **TARIFF_SCHEDULE["peak"]},
        },
        "currency": "EUR",
        "unit": "c/kWh",
        "vat_rate": 9,
    }


def _set_rate_action(period: str) -> dict[str, Any]:
    """Build a service action to set the current rate from a period's entity."""
    source = TARIFF_ENTITY_IDS[period]
    return {
        "service": "input_number.set_value",
        "target": {"entity_id": TARIFF_ENTITY_IDS["current"]},
        "data": {"value": f"{{{{ states('{source}') | float }}}}"},
    }


def _set_period_action(period: str) -> dict[str, Any]:
    """Build a service action to set the current tariff period."""
    return {
        "service": "input_select.select_option",
        "target": {"entity_id": TARIFF_ENTITY_IDS["period"]},
        "data": {"option": period},
    }
