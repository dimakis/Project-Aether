"""Workarounds for HA capability gaps.

These functions infer missing data from available entity attributes.
Each workaround is documented with the HA feature that would make it unnecessary.
"""

from typing import Any

from src.ha.parsers import ParsedEntity


def infer_devices_from_entities(
    entities: list[ParsedEntity],
) -> dict[str, dict[str, Any]]:
    """Infer device information from entity attributes.

    HA Gap: No `list_devices` tool available.
    Workaround: Extract device_id from entity attributes and group entities.

    Args:
        entities: List of parsed entities

    Returns:
        Dictionary mapping device_id to device info
    """
    devices: dict[str, dict[str, Any]] = {}

    for entity in entities:
        # Try to get device_id from various sources
        device_id = entity.device_id
        if not device_id and entity.attributes:
            device_id = entity.attributes.get("device_id")

        if not device_id:
            continue

        if device_id not in devices:
            devices[device_id] = {
                "ha_device_id": device_id,
                "name": _infer_device_name(entity),
                "entities": [],
                "area_id": entity.area_id,
                # These would come from list_devices - HA gap
                "manufacturer": None,
                "model": None,
                "sw_version": None,
            }

        devices[device_id]["entities"].append(entity.entity_id)

        # Update area if we find one
        if entity.area_id and not devices[device_id]["area_id"]:
            devices[device_id]["area_id"] = entity.area_id

    return devices


def _infer_device_name(entity: ParsedEntity) -> str:
    """Infer device name from entity.

    Args:
        entity: Entity to infer from

    Returns:
        Best guess at device name
    """
    # Try to extract from entity name
    name = entity.name

    # Remove common suffixes
    suffixes = [
        " Temperature",
        " Humidity",
        " Battery",
        " Power",
        " Energy",
        " Voltage",
        " Current",
        " Light",
        " Switch",
        " Motion",
        " Illuminance",
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[: -len(suffix)].strip()

    # If entity_id has a reasonable structure, use it
    if "." in entity.entity_id:
        entity_name = entity.entity_id.split(".", 1)[1]
        # Convert snake_case to Title Case
        return entity_name.replace("_", " ").title()

    return name


def infer_areas_from_entities(
    entities: list[ParsedEntity],
) -> dict[str, dict[str, Any]]:
    """Infer area information from entity attributes.

    HA Gap: Areas come from entity attributes, not a dedicated tool.
    The area registry details (floor, icon) are not available.

    Args:
        entities: List of parsed entities

    Returns:
        Dictionary mapping area_id to area info
    """
    areas: dict[str, dict[str, Any]] = {}

    for entity in entities:
        area_id = entity.area_id
        if not area_id and entity.attributes:
            area_id = entity.attributes.get("area_id")

        if not area_id:
            continue

        if area_id not in areas:
            areas[area_id] = {
                "ha_area_id": area_id,
                "name": _area_id_to_name(area_id),
                "entities": [],
                # HA gap - floor not available
                "floor_id": None,
                "icon": None,
            }

        areas[area_id]["entities"].append(entity.entity_id)

    return areas


def _area_id_to_name(area_id: str) -> str:
    """Convert area_id to a display name.

    Args:
        area_id: Area ID (e.g., "living_room")

    Returns:
        Display name (e.g., "Living Room")
    """
    # Convert snake_case to Title Case
    return area_id.replace("_", " ").title()


def extract_entity_metadata(entity: ParsedEntity) -> dict[str, Any]:
    """Extract additional metadata from entity attributes.

    Args:
        entity: Parsed entity

    Returns:
        Dictionary with extracted metadata
    """
    attrs = entity.attributes or {}

    metadata = {
        "device_class": entity.device_class or attrs.get("device_class"),
        "state_class": attrs.get("state_class"),
        "unit_of_measurement": entity.unit_of_measurement or attrs.get("unit_of_measurement"),
        "supported_features": entity.supported_features or attrs.get("supported_features", 0),
        "icon": attrs.get("icon"),
        "entity_category": attrs.get("entity_category"),
    }

    # Extract platform from entity_id if possible
    # e.g., sensor.hue_motion_sensor -> hue
    if "." in entity.entity_id:
        entity_name = entity.entity_id.split(".", 1)[1]
        parts = entity_name.split("_")
        if len(parts) > 1:
            # First part might be platform name
            potential_platform = parts[0]
            if potential_platform in ("hue", "zwave", "zigbee", "mqtt", "esphome"):
                metadata["platform"] = potential_platform

    return metadata


def identify_helper_entities(entities: list[ParsedEntity]) -> list[ParsedEntity]:
    """Identify helper entities (input_*, counter, timer, etc.).

    Args:
        entities: List of parsed entities

    Returns:
        List of entities that are helpers
    """
    helper_domains = {
        "input_boolean",
        "input_number",
        "input_text",
        "input_select",
        "input_datetime",
        "input_button",
        "counter",
        "timer",
        "schedule",
        "group",
    }

    return [e for e in entities if e.domain in helper_domains]


def identify_automation_entities(entities: list[ParsedEntity]) -> list[ParsedEntity]:
    """Identify automation-related entities.

    Args:
        entities: List of parsed entities

    Returns:
        List of automation, script, and scene entities
    """
    automation_domains = {"automation", "script", "scene"}
    return [e for e in entities if e.domain in automation_domains]


__all__ = [
    "extract_entity_metadata",
    "identify_automation_entities",
    "identify_helper_entities",
    "infer_areas_from_entities",
    "infer_devices_from_entities",
]
