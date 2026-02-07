"""HA client response mocks and HA state fixtures.

Provides pre-built mock responses for testing without
actual Home Assistant connections.

Constitution: Reliability & Quality - deterministic test data.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

# =============================================================================
# HOME ASSISTANT STATE FIXTURES
# =============================================================================

# Sample HA system overview
HA_SYSTEM_OVERVIEW: dict[str, Any] = {
    "total_entities": 87,
    "domains": {
        "light": {"count": 15, "states": {"on": 4, "off": 11}},
        "switch": {"count": 12, "states": {"on": 3, "off": 9}},
        "sensor": {"count": 35, "states": {}},
        "binary_sensor": {"count": 10, "states": {"on": 3, "off": 7}},
        "climate": {"count": 3, "states": {"heat": 2, "off": 1}},
        "cover": {"count": 4, "states": {"open": 1, "closed": 3}},
        "media_player": {"count": 5, "states": {"playing": 1, "idle": 2, "off": 2}},
        "automation": {"count": 3, "states": {"on": 3}},
    },
    "domain_samples": {
        "light": [
            {"entity_id": "light.living_room", "state": "off", "name": "Living Room"},
            {"entity_id": "light.kitchen", "state": "on", "name": "Kitchen"},
        ],
        "sensor": [
            {"entity_id": "sensor.temperature", "state": "21.5", "name": "Temperature"},
        ],
    },
}

# Sample entity list
HA_LIGHT_ENTITIES: list[dict[str, Any]] = [
    {
        "entity_id": "light.living_room",
        "state": "off",
        "name": "Living Room",
        "area_id": "living_room",
        "attributes": {
            "friendly_name": "Living Room Light",
            "supported_features": 44,
            "color_mode": "brightness",
        },
    },
    {
        "entity_id": "light.kitchen",
        "state": "on",
        "name": "Kitchen",
        "area_id": "kitchen",
        "attributes": {
            "friendly_name": "Kitchen Light",
            "brightness": 255,
            "supported_features": 44,
        },
    },
    {
        "entity_id": "light.bedroom",
        "state": "off",
        "name": "Bedroom",
        "area_id": "bedroom",
        "attributes": {
            "friendly_name": "Bedroom Light",
            "supported_features": 44,
        },
    },
]

HA_SENSOR_ENTITIES: list[dict[str, Any]] = [
    {
        "entity_id": "sensor.living_room_temperature",
        "state": "21.5",
        "name": "Living Room Temperature",
        "area_id": "living_room",
        "attributes": {
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
        },
    },
    {
        "entity_id": "sensor.outdoor_temperature",
        "state": "15.2",
        "name": "Outdoor Temperature",
        "area_id": None,
        "attributes": {
            "unit_of_measurement": "°C",
            "device_class": "temperature",
        },
    },
    {
        "entity_id": "sensor.energy_usage",
        "state": "1523",
        "name": "Energy Usage",
        "area_id": None,
        "attributes": {
            "unit_of_measurement": "W",
            "device_class": "power",
            "state_class": "measurement",
        },
    },
]

HA_AUTOMATION_LIST: list[dict[str, Any]] = [
    {
        "id": "auto_1",
        "entity_id": "automation.morning_lights",
        "state": "on",
        "alias": "Morning Lights",
    },
    {
        "id": "auto_2",
        "entity_id": "automation.away_mode",
        "state": "on",
        "alias": "Away Mode",
    },
    {
        "id": "auto_3",
        "entity_id": "automation.night_mode",
        "state": "off",
        "alias": "Night Mode",
    },
]

# Sample areas
HA_AREAS: list[dict[str, Any]] = [
    {"area_id": "living_room", "name": "Living Room", "floor_id": "ground_floor"},
    {"area_id": "kitchen", "name": "Kitchen", "floor_id": "ground_floor"},
    {"area_id": "bedroom", "name": "Bedroom", "floor_id": "first_floor"},
    {"area_id": "bathroom", "name": "Bathroom", "floor_id": "first_floor"},
]

# Sample domain summary
HA_DOMAIN_SUMMARY: dict[str, Any] = {
    "total_count": 15,
    "state_distribution": {"on": 4, "off": 11},
    "examples": {
        "on": [
            {"entity_id": "light.kitchen", "name": "Kitchen"},
            {"entity_id": "light.hallway", "name": "Hallway"},
        ],
        "off": [
            {"entity_id": "light.living_room", "name": "Living Room"},
            {"entity_id": "light.bedroom", "name": "Bedroom"},
        ],
    },
    "common_attributes": ["brightness", "color_mode", "supported_features"],
}

# Sample entity history
HA_ENTITY_HISTORY: dict[str, Any] = {
    "entity_id": "sensor.temperature",
    "states": [
        {"state": "21.0", "last_changed": "2024-01-15T08:00:00Z"},
        {"state": "21.5", "last_changed": "2024-01-15T09:00:00Z"},
        {"state": "22.0", "last_changed": "2024-01-15T10:00:00Z"},
        {"state": "21.8", "last_changed": "2024-01-15T11:00:00Z"},
    ],
    "count": 4,
    "first_changed": "2024-01-15T08:00:00Z",
    "last_changed": "2024-01-15T11:00:00Z",
}


# =============================================================================
# mock HA CLIENT FACTORY
# =============================================================================


def create_mock_ha_client(
    system_overview: dict[str, Any] | None = None,
    light_entities: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Create a mock HA client with configurable responses.

    Args:
        system_overview: Custom system overview response
        light_entities: Custom light entity list

    Returns:
        Configured MagicMock HA client
    """
    client = MagicMock()

    # System overview
    client.system_overview = AsyncMock(
        return_value=system_overview or HA_SYSTEM_OVERVIEW
    )

    # List entities by domain
    async def mock_list_entities(domain: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        if domain == "light":
            return light_entities or HA_LIGHT_ENTITIES
        elif domain == "sensor":
            return HA_SENSOR_ENTITIES
        elif domain == "automation":
            return HA_AUTOMATION_LIST
        else:
            return HA_LIGHT_ENTITIES + HA_SENSOR_ENTITIES

    client.list_entities = AsyncMock(side_effect=mock_list_entities)

    # Get entity
    async def mock_get_entity(entity_id: str, **kwargs: Any) -> dict[str, Any] | None:
        all_entities = HA_LIGHT_ENTITIES + HA_SENSOR_ENTITIES
        for entity in all_entities:
            if entity["entity_id"] == entity_id:
                return entity
        return None

    client.get_entity = AsyncMock(side_effect=mock_get_entity)

    # Domain summary
    client.domain_summary_tool = AsyncMock(return_value=HA_DOMAIN_SUMMARY)

    # List automations
    client.list_automations = AsyncMock(return_value=HA_AUTOMATION_LIST)

    # Entity action
    client.entity_action = AsyncMock(return_value={"success": True})

    # Call service
    client.call_service_tool = AsyncMock(return_value={})

    # Get history
    client.get_history = AsyncMock(return_value=HA_ENTITY_HISTORY)

    # Get version
    client.get_version = AsyncMock(return_value="2024.1.0")

    # Search entities
    client.search_entities_tool = AsyncMock(
        return_value={
            "count": 3,
            "results": HA_LIGHT_ENTITIES[:3],
            "domains": {"light": 3},
        }
    )

    return client


# =============================================================================
# MOCK LLM RESPONSES
# =============================================================================


def create_mock_llm_response(content: str) -> MagicMock:
    """Create a mock LLM response.

    Args:
        content: Response content

    Returns:
        Mock AIMessage-like object
    """
    from langchain_core.messages import AIMessage

    return AIMessage(
        content=content,
        usage_metadata={
            "input_tokens": len(content.split()) * 2,
            "output_tokens": len(content.split()),
            "total_tokens": len(content.split()) * 3,
        },
    )


# Preset LLM responses
LLM_CATEGORIZER_RESPONSE = """Based on your request, I've identified the following:
- Intent: Create a new automation
- Entities involved: light.living_room, light.kitchen
- Trigger type: Time-based
- Suggested name: Morning Wake Up Lights"""

LLM_ARCHITECT_RESPONSE = """Here's the automation design:

**Name**: Morning Wake Up Lights
**Description**: Gradually turn on lights in the morning

**Trigger**: Time trigger at 7:00 AM on weekdays

**Actions**:
1. Turn on living room light at 30% brightness
2. Wait 5 minutes
3. Increase brightness to 70%
4. Turn on kitchen light

Would you like me to proceed with this design?"""

LLM_DATA_SCIENTIST_RESPONSE = """Based on my analysis of your energy data:

**Key Findings**:
1. Peak usage occurs between 6-8 PM
2. Standby power is consuming 150W constantly
3. HVAC is the largest consumer at 45% of total

**Recommendations**:
1. Install smart power strips to eliminate standby drain
2. Adjust thermostat schedule to reduce HVAC during peak hours
3. Consider LED replacements for high-usage lights

Estimated savings: 15-20% on monthly energy bill."""


# Exports
__all__ = [
    # Fixtures
    "HA_SYSTEM_OVERVIEW",
    "HA_LIGHT_ENTITIES",
    "HA_SENSOR_ENTITIES",
    "HA_AUTOMATION_LIST",
    "HA_AREAS",
    "HA_DOMAIN_SUMMARY",
    "HA_ENTITY_HISTORY",
    # Factories
    "create_mock_ha_client",
    "create_mock_llm_response",
    # LLM responses
    "LLM_CATEGORIZER_RESPONSE",
    "LLM_ARCHITECT_RESPONSE",
    "LLM_DATA_SCIENTIST_RESPONSE",
]
