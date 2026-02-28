"""Home Assistant tools registry.

Provides get_ha_tools() returning the combined tool list from domain-focused
modules. Entity/automation/script/input/utility tools live in separate modules.
"""

from __future__ import annotations

from typing import Any

from src.tools.ha_automation_tools import (
    delete_automation,
    deploy_automation,
    get_automation_config,
    list_automations,
)
from src.tools.ha_entity_tools import (
    control_entity,
    get_domain_summary,
    get_entity_state,
    list_entities_by_domain,
    search_entities,
)
from src.tools.ha_input_tools import (
    create_counter,
    create_input_boolean,
    create_input_button,
    create_input_datetime,
    create_input_number,
    create_input_select,
    create_input_text,
    create_timer,
)
from src.tools.ha_script_scene_tools import create_scene, create_script, get_script_config
from src.tools.ha_utility_tools import (
    check_ha_config,
    fire_event,
    get_ha_logs,
    render_template,
    send_ha_notification,
)


def get_ha_tools() -> list[Any]:
    return [
        # Entity queries (DB-backed)
        get_entity_state,
        list_entities_by_domain,
        search_entities,
        get_domain_summary,
        # Entity control
        control_entity,
        # Automations
        deploy_automation,
        delete_automation,
        list_automations,
        get_automation_config,
        get_script_config,
        # Scripts & Scenes
        create_script,
        create_scene,
        # Input helpers
        create_input_boolean,
        create_input_number,
        create_input_text,
        create_input_select,
        create_input_datetime,
        create_input_button,
        create_counter,
        create_timer,
        # Events & Templates
        fire_event,
        send_ha_notification,
        render_template,
        # Diagnostics
        get_ha_logs,
        check_ha_config,
    ]
