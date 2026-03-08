"""Validation and detection tools for the automation builder.

Feature 36: Natural Language Automation Builder.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool("check_entity_exists")
async def check_entity_exists(entity_id: str) -> str:
    """Check if an entity exists in the HA registry and suggest corrections for typos.

    Args:
        entity_id: The entity ID to check (e.g., "light.living_room")

    Returns:
        JSON string with exists flag and suggestions if not found.
    """
    from src.dal.entities import EntityRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = EntityRepository(session)
        entity = await repo.get_by_entity_id(entity_id)

        if entity:
            return json.dumps(
                {
                    "exists": True,
                    "entity_id": entity_id,
                    "name": entity.name,
                    "domain": entity.domain,
                    "state": entity.state,
                }
            )

        # Fuzzy search for suggestions
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        suggestions: list[dict[str, str]] = []
        if domain:
            entities = await repo.list_all(limit=200, domain=domain)
            search_term = entity_id.split(".")[-1] if "." in entity_id else entity_id
            for e in entities:
                eid = e.entity_id or ""
                ename = e.name or ""
                if search_term.lower() in eid.lower() or search_term.lower() in ename.lower():
                    suggestions.append(
                        {
                            "entity_id": eid,
                            "name": ename,
                        }
                    )

        return json.dumps(
            {
                "exists": False,
                "entity_id": entity_id,
                "suggestions": suggestions[:5],
            }
        )


@tool("find_similar_automations")
async def find_similar_automations(
    entity_ids: list[str],
    trigger_type: str = "",
) -> str:
    """Find existing automations that target similar entities or triggers.

    Args:
        entity_ids: Entity IDs involved in the proposed automation
        trigger_type: Type of trigger (e.g., "time", "state", "event")

    Returns:
        JSON string with list of similar automations.
    """
    from src.dal.automations import AutomationRepository
    from src.storage import get_session

    async with get_session() as session:
        repo = AutomationRepository(session)
        all_automations = await repo.list_all(limit=500)

        similar: list[dict[str, Any]] = []

        for auto in all_automations:
            config = auto.config or {}
            config_str = json.dumps(config).lower()
            overlap = [eid for eid in entity_ids if eid.lower() in config_str]

            if overlap:
                similar.append(
                    {
                        "automation_id": auto.entity_id or "",
                        "alias": auto.alias or "",
                        "description": getattr(auto, "description", "") or "",
                        "overlapping_entities": overlap,
                        "state": auto.state or "",
                    }
                )

        return json.dumps(
            {
                "count": len(similar),
                "similar": similar[:10],
            }
        )


@tool("validate_automation_draft")
async def validate_automation_draft(yaml_content: str) -> str:
    """Validate automation YAML structurally and semantically.

    Args:
        yaml_content: The automation YAML string to validate

    Returns:
        JSON string with validation results.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Structural validation (Feature 26)
    try:
        from src.schema import validate_yaml

        result = validate_yaml(yaml_content, "ha.automation")
        if not result.valid:
            errors.extend(f"{e.path}: {e.message}" for e in result.errors)
    except KeyError:
        logger.debug("ha.automation schema not registered, skipping structural validation")
    except Exception:
        logger.exception("Schema validation error")
        errors.append("Schema validation failed unexpectedly")

    # Semantic validation (Feature 27) — best-effort
    try:
        from src.ha import get_ha_client
        from src.schema import validate_yaml_semantic

        ha_client = get_ha_client()
        sem_result = await validate_yaml_semantic(
            yaml_content, "ha.automation", ha_client=ha_client
        )
        if not sem_result.valid:
            errors.extend(f"{e.path}: {e.message}" for e in sem_result.errors)
            warnings.extend(f"{w.path}: {w.message}" for w in sem_result.warnings)
    except ImportError:
        pass
    except Exception:
        logger.debug("Semantic validation unavailable", exc_info=True)
        warnings.append("Semantic validation unavailable")

    return json.dumps(
        {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    )


def get_automation_builder_tools() -> list[Any]:
    return [
        check_entity_exists,
        find_similar_automations,
        validate_automation_draft,
    ]
