"""Home Assistant YAML schemas.

Auto-registers all HA schemas with the global registry on import.

Usage::

    # Import triggers registration
    import src.schema.ha  # noqa: F401

    # Then validate
    from src.schema import validate_yaml

    result = validate_yaml(yaml_str, "ha.automation")

Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.schema.core import registry
from src.schema.ha.automation import HAAutomation
from src.schema.ha.dashboard import LovelaceDashboard
from src.schema.ha.entity_command import EntityCommandPayload
from src.schema.ha.helper import HAHelper
from src.schema.ha.scene import HAScene
from src.schema.ha.script import HAScript

if TYPE_CHECKING:
    from pydantic import BaseModel


def _register_ha_schemas() -> None:
    """Register all HA schemas with the global registry.

    Called once on module import. Idempotent — skips already-registered names.
    """
    _schemas: dict[str, type[BaseModel]] = {
        "ha.automation": HAAutomation,
        "ha.dashboard": LovelaceDashboard,
        "ha.entity_command": EntityCommandPayload,
        "ha.helper": HAHelper,
        "ha.script": HAScript,
        "ha.scene": HAScene,
    }
    for name, model in _schemas.items():
        if name not in registry.list_schemas():
            registry.register(name, model)


_register_ha_schemas()

__all__ = [
    "EntityCommandPayload",
    "HAAutomation",
    "HAHelper",
    "HAScene",
    "HAScript",
    "LovelaceDashboard",
]
