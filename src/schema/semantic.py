"""Semantic YAML validator.

Validates parsed YAML data against live Home Assistant state:
entity existence, service validity, domain consistency, and
area existence.

Sits on top of the structural validator (Feature 26). The
structural validator checks schema conformance; this module
checks that referenced HA objects actually exist.

Feature 27: YAML Semantic Validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.schema.core import ValidationError, ValidationResult

if TYPE_CHECKING:
    from src.schema.ha.registry_cache import HARegistryCache

# Services in these domains are domain-agnostic and can target any entity type.
# e.g., homeassistant.turn_on can target light.*, switch.*, etc.
_DOMAIN_AGNOSTIC_SERVICES = frozenset({"homeassistant"})


class SemanticValidator:
    """Validates HA YAML data against live registry state.

    Args:
        cache: HARegistryCache providing entity/service/area lookups.
    """

    def __init__(self, cache: HARegistryCache) -> None:
        self._cache = cache

    async def validate(
        self,
        data: dict[str, Any],
        *,
        schema_name: str = "ha.automation",
    ) -> ValidationResult:
        """Run all semantic rules against parsed YAML data.

        Expects data that has already been normalized (plural keys → singular,
        trigger → platform, action → service) by core._normalize_ha_automation().

        Args:
            data: Parsed YAML dict (already structurally validated and normalized).
            schema_name: Schema context for error reporting.

        Returns:
            ValidationResult with semantic errors/warnings.
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        # Extract and check entities, services, and areas from triggers
        await self._check_triggers(data.get("trigger", []), errors)

        # Check actions
        await self._check_actions(data.get("action", []), errors, warnings)

        # Check conditions
        await self._check_conditions(data.get("condition", []), errors)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            schema_name=schema_name,
        )

    # ------------------------------------------------------------------
    # Trigger checks
    # ------------------------------------------------------------------

    async def _check_triggers(
        self,
        triggers: list[dict[str, Any]] | dict[str, Any],
        errors: list[ValidationError],
    ) -> None:
        """Check entity references in triggers."""
        if isinstance(triggers, dict):
            triggers = [triggers]
        if not isinstance(triggers, list):
            return

        for i, trigger in enumerate(triggers):
            if not isinstance(trigger, dict):
                continue

            # Check entity_id in trigger
            entity_ids = trigger.get("entity_id")
            if entity_ids:
                await self._check_entity_ids(
                    entity_ids,
                    f"trigger[{i}].entity_id",
                    errors,
                )

    # ------------------------------------------------------------------
    # Action checks
    # ------------------------------------------------------------------

    async def _check_actions(
        self,
        actions: list[dict[str, Any]] | dict[str, Any],
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        """Check service and entity references in actions."""
        if isinstance(actions, dict):
            actions = [actions]
        if not isinstance(actions, list):
            return

        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                continue

            # Check service exists
            service = action.get("service")
            if service and isinstance(service, str):
                if not await self._cache.service_exists(service):
                    errors.append(
                        ValidationError(
                            path=f"action[{i}].service",
                            message=f"Service '{service}' not found in HA registry",
                        )
                    )

                # Check target entity domain consistency
                target = action.get("target", {})
                if isinstance(target, dict):
                    await self._check_action_target(
                        target,
                        service,
                        i,
                        errors,
                        warnings,
                    )

    async def _check_action_target(
        self,
        target: dict[str, Any],
        service: str,
        action_idx: int,
        errors: list[ValidationError],
        warnings: list[ValidationError],
    ) -> None:
        """Check entity/area references in an action's target."""
        # Check entity_id in target
        entity_ids = target.get("entity_id")
        if entity_ids:
            await self._check_entity_ids(
                entity_ids,
                f"action[{action_idx}].target.entity_id",
                errors,
            )

            # Domain consistency: warn if entity domain != service domain.
            # Skip domain-agnostic services (e.g., homeassistant.turn_on)
            # which intentionally target entities of any domain.
            service_domain = service.split(".", 1)[0] if "." in service else ""
            if service_domain and service_domain not in _DOMAIN_AGNOSTIC_SERVICES:
                eids = entity_ids if isinstance(entity_ids, list) else [entity_ids]
                for eid in eids:
                    if isinstance(eid, str) and "." in eid:
                        entity_domain = eid.split(".", 1)[0]
                        if entity_domain != service_domain:
                            warnings.append(
                                ValidationError(
                                    path=f"action[{action_idx}].target.entity_id",
                                    message=(
                                        f"Entity '{eid}' has domain '{entity_domain}' "
                                        f"but service is '{service}' (domain '{service_domain}')"
                                    ),
                                )
                            )

        # Check area_id in target
        area_ids = target.get("area_id")
        if area_ids:
            await self._check_area_ids(
                area_ids,
                f"action[{action_idx}].target.area_id",
                errors,
            )

    # ------------------------------------------------------------------
    # Condition checks
    # ------------------------------------------------------------------

    async def _check_conditions(
        self,
        conditions: list[dict[str, Any]] | dict[str, Any] | None,
        errors: list[ValidationError],
    ) -> None:
        """Check entity references in conditions."""
        if conditions is None:
            return
        if isinstance(conditions, dict):
            conditions = [conditions]
        if not isinstance(conditions, list):
            return

        for i, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                continue

            # Check entity_id in condition
            entity_ids = condition.get("entity_id")
            if entity_ids:
                await self._check_entity_ids(
                    entity_ids,
                    f"condition[{i}].entity_id",
                    errors,
                )

            # Recurse into nested conditions (and/or/not)
            nested = condition.get("conditions")
            if nested and isinstance(nested, list):
                await self._check_conditions(nested, errors)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _check_entity_ids(
        self,
        entity_ids: str | list[str],
        path: str,
        errors: list[ValidationError],
    ) -> None:
        """Check one or more entity IDs exist."""
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        for eid in entity_ids:
            if not isinstance(eid, str):
                continue
            if not await self._cache.entity_exists(eid):
                errors.append(
                    ValidationError(
                        path=path,
                        message=f"Entity '{eid}' not found in HA registry",
                    )
                )

    async def _check_area_ids(
        self,
        area_ids: str | list[str],
        path: str,
        errors: list[ValidationError],
    ) -> None:
        """Check one or more area IDs exist."""
        if isinstance(area_ids, str):
            area_ids = [area_ids]

        for aid in area_ids:
            if not isinstance(aid, str):
                continue
            if not await self._cache.area_exists(aid):
                errors.append(
                    ValidationError(
                        path=path,
                        message=f"Area '{aid}' not found in HA registry",
                    )
                )


__all__ = ["SemanticValidator"]
