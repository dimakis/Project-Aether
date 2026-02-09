"""Common services seed data.

Provides a baseline set of common HA services that are seeded
into the database before discovery. This ensures agents know
about standard services even if discovery hasn't run.

HA Gap: No `list_services` tool available.
Workaround: Seed common services from this constant data.
"""

from typing import Any

# Common services organized by domain
COMMON_SERVICES: dict[str, list[dict[str, Any]]] = {
    "homeassistant": [
        {
            "service": "turn_on",
            "name": "Turn On",
            "description": "Turn on an entity",
            "fields": {"entity_id": {"description": "Entity to turn on"}},
        },
        {
            "service": "turn_off",
            "name": "Turn Off",
            "description": "Turn off an entity",
            "fields": {"entity_id": {"description": "Entity to turn off"}},
        },
        {
            "service": "toggle",
            "name": "Toggle",
            "description": "Toggle an entity on/off",
            "fields": {"entity_id": {"description": "Entity to toggle"}},
        },
        {
            "service": "reload_all",
            "name": "Reload All",
            "description": "Reload all configuration",
            "fields": {},
        },
    ],
    "light": [
        {
            "service": "turn_on",
            "name": "Turn On Light",
            "description": "Turn on a light with optional settings",
            "fields": {
                "entity_id": {"description": "Light entity"},
                "brightness": {"description": "Brightness (0-255)"},
                "brightness_pct": {"description": "Brightness percentage (0-100)"},
                "color_temp": {"description": "Color temperature in mireds"},
                "kelvin": {"description": "Color temperature in Kelvin"},
                "rgb_color": {"description": "RGB color [R, G, B]"},
                "transition": {"description": "Transition time in seconds"},
                "effect": {"description": "Light effect name"},
            },
        },
        {
            "service": "turn_off",
            "name": "Turn Off Light",
            "description": "Turn off a light",
            "fields": {
                "entity_id": {"description": "Light entity"},
                "transition": {"description": "Transition time in seconds"},
            },
        },
        {
            "service": "toggle",
            "name": "Toggle Light",
            "description": "Toggle a light on/off",
            "fields": {"entity_id": {"description": "Light entity"}},
        },
    ],
    "switch": [
        {
            "service": "turn_on",
            "name": "Turn On Switch",
            "description": "Turn on a switch",
            "fields": {"entity_id": {"description": "Switch entity"}},
        },
        {
            "service": "turn_off",
            "name": "Turn Off Switch",
            "description": "Turn off a switch",
            "fields": {"entity_id": {"description": "Switch entity"}},
        },
        {
            "service": "toggle",
            "name": "Toggle Switch",
            "description": "Toggle a switch",
            "fields": {"entity_id": {"description": "Switch entity"}},
        },
    ],
    "climate": [
        {
            "service": "set_temperature",
            "name": "Set Temperature",
            "description": "Set target temperature",
            "fields": {
                "entity_id": {"description": "Climate entity"},
                "temperature": {"description": "Target temperature"},
                "target_temp_high": {"description": "High target (for range)"},
                "target_temp_low": {"description": "Low target (for range)"},
            },
        },
        {
            "service": "set_hvac_mode",
            "name": "Set HVAC Mode",
            "description": "Set the HVAC mode",
            "fields": {
                "entity_id": {"description": "Climate entity"},
                "hvac_mode": {"description": "Mode (heat, cool, auto, off, etc.)"},
            },
        },
        {
            "service": "set_preset_mode",
            "name": "Set Preset Mode",
            "description": "Set a preset mode",
            "fields": {
                "entity_id": {"description": "Climate entity"},
                "preset_mode": {"description": "Preset name"},
            },
        },
        {
            "service": "turn_on",
            "name": "Turn On Climate",
            "description": "Turn on climate control",
            "fields": {"entity_id": {"description": "Climate entity"}},
        },
        {
            "service": "turn_off",
            "name": "Turn Off Climate",
            "description": "Turn off climate control",
            "fields": {"entity_id": {"description": "Climate entity"}},
        },
    ],
    "cover": [
        {
            "service": "open_cover",
            "name": "Open Cover",
            "description": "Open a cover",
            "fields": {"entity_id": {"description": "Cover entity"}},
        },
        {
            "service": "close_cover",
            "name": "Close Cover",
            "description": "Close a cover",
            "fields": {"entity_id": {"description": "Cover entity"}},
        },
        {
            "service": "stop_cover",
            "name": "Stop Cover",
            "description": "Stop cover movement",
            "fields": {"entity_id": {"description": "Cover entity"}},
        },
        {
            "service": "set_cover_position",
            "name": "Set Cover Position",
            "description": "Set cover position",
            "fields": {
                "entity_id": {"description": "Cover entity"},
                "position": {"description": "Position (0-100)"},
            },
        },
        {
            "service": "set_cover_tilt_position",
            "name": "Set Tilt Position",
            "description": "Set cover tilt position",
            "fields": {
                "entity_id": {"description": "Cover entity"},
                "tilt_position": {"description": "Tilt position (0-100)"},
            },
        },
    ],
    "fan": [
        {
            "service": "turn_on",
            "name": "Turn On Fan",
            "description": "Turn on a fan",
            "fields": {
                "entity_id": {"description": "Fan entity"},
                "percentage": {"description": "Speed percentage"},
            },
        },
        {
            "service": "turn_off",
            "name": "Turn Off Fan",
            "description": "Turn off a fan",
            "fields": {"entity_id": {"description": "Fan entity"}},
        },
        {
            "service": "set_percentage",
            "name": "Set Fan Speed",
            "description": "Set fan speed percentage",
            "fields": {
                "entity_id": {"description": "Fan entity"},
                "percentage": {"description": "Speed (0-100)"},
            },
        },
    ],
    "media_player": [
        {
            "service": "play_media",
            "name": "Play Media",
            "description": "Play media on a player",
            "fields": {
                "entity_id": {"description": "Media player entity"},
                "media_content_id": {"description": "Content to play"},
                "media_content_type": {"description": "Content type"},
            },
        },
        {
            "service": "volume_set",
            "name": "Set Volume",
            "description": "Set volume level",
            "fields": {
                "entity_id": {"description": "Media player entity"},
                "volume_level": {"description": "Volume (0.0-1.0)"},
            },
        },
        {
            "service": "media_play",
            "name": "Play",
            "description": "Start playback",
            "fields": {"entity_id": {"description": "Media player entity"}},
        },
        {
            "service": "media_pause",
            "name": "Pause",
            "description": "Pause playback",
            "fields": {"entity_id": {"description": "Media player entity"}},
        },
        {
            "service": "media_stop",
            "name": "Stop",
            "description": "Stop playback",
            "fields": {"entity_id": {"description": "Media player entity"}},
        },
    ],
    "automation": [
        {
            "service": "trigger",
            "name": "Trigger Automation",
            "description": "Trigger an automation to run",
            "fields": {"entity_id": {"description": "Automation entity"}},
        },
        {
            "service": "turn_on",
            "name": "Enable Automation",
            "description": "Enable an automation",
            "fields": {"entity_id": {"description": "Automation entity"}},
        },
        {
            "service": "turn_off",
            "name": "Disable Automation",
            "description": "Disable an automation",
            "fields": {"entity_id": {"description": "Automation entity"}},
        },
        {
            "service": "reload",
            "name": "Reload Automations",
            "description": "Reload all automations from config",
            "fields": {},
        },
    ],
    "script": [
        {
            "service": "turn_on",
            "name": "Run Script",
            "description": "Run a script",
            "fields": {"entity_id": {"description": "Script entity"}},
        },
        {
            "service": "turn_off",
            "name": "Stop Script",
            "description": "Stop a running script",
            "fields": {"entity_id": {"description": "Script entity"}},
        },
        {
            "service": "reload",
            "name": "Reload Scripts",
            "description": "Reload all scripts from config",
            "fields": {},
        },
    ],
    "scene": [
        {
            "service": "turn_on",
            "name": "Activate Scene",
            "description": "Activate a scene",
            "fields": {"entity_id": {"description": "Scene entity"}},
        },
        {
            "service": "apply",
            "name": "Apply Scene",
            "description": "Apply a scene with transitions",
            "fields": {
                "entity_id": {"description": "Scene entity"},
                "transition": {"description": "Transition time in seconds"},
            },
        },
        {
            "service": "reload",
            "name": "Reload Scenes",
            "description": "Reload all scenes from config",
            "fields": {},
        },
    ],
    "notify": [
        {
            "service": "persistent_notification",
            "name": "Create Notification",
            "description": "Create a persistent notification",
            "fields": {
                "message": {"description": "Notification message"},
                "title": {"description": "Notification title"},
            },
        },
    ],
    "input_boolean": [
        {
            "service": "turn_on",
            "name": "Turn On",
            "description": "Turn on an input boolean",
            "fields": {"entity_id": {"description": "Input boolean entity"}},
        },
        {
            "service": "turn_off",
            "name": "Turn Off",
            "description": "Turn off an input boolean",
            "fields": {"entity_id": {"description": "Input boolean entity"}},
        },
        {
            "service": "toggle",
            "name": "Toggle",
            "description": "Toggle an input boolean",
            "fields": {"entity_id": {"description": "Input boolean entity"}},
        },
    ],
    "input_number": [
        {
            "service": "set_value",
            "name": "Set Value",
            "description": "Set the value of an input number",
            "fields": {
                "entity_id": {"description": "Input number entity"},
                "value": {"description": "Value to set"},
            },
        },
        {
            "service": "increment",
            "name": "Increment",
            "description": "Increment the value by step",
            "fields": {"entity_id": {"description": "Input number entity"}},
        },
        {
            "service": "decrement",
            "name": "Decrement",
            "description": "Decrement the value by step",
            "fields": {"entity_id": {"description": "Input number entity"}},
        },
    ],
}


def get_all_services() -> list[dict[str, Any]]:
    """Get all common services as a flat list.

    Returns:
        List of service dictionaries with domain included
    """
    services = []
    for domain, domain_services in COMMON_SERVICES.items():
        for service in domain_services:
            services.append(
                {
                    "domain": domain,
                    **service,
                    "is_seeded": True,
                }
            )
    return services


def get_services_for_domain(domain: str) -> list[dict[str, Any]]:
    """Get common services for a specific domain.

    Args:
        domain: Domain name

    Returns:
        List of services for that domain
    """
    return COMMON_SERVICES.get(domain, [])


__all__ = [
    "COMMON_SERVICES",
    "get_all_services",
    "get_services_for_domain",
]
