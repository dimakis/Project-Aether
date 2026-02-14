"""Core YAML schema validation framework.

Provides the SchemaRegistry, ValidationResult, ValidationError models,
and the top-level validate_yaml() convenience function.

Pydantic models are compiled to JSON Schema via .model_json_schema()
and validated using the jsonschema library.

Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

from typing import Any

import jsonschema  # type: ignore[import-untyped,unused-ignore]
import yaml
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

# =============================================================================
# MODELS
# =============================================================================


class ValidationError(BaseModel):
    """A single validation error with location context.

    Attributes:
        path: JSONPath-style location of the error (e.g., "trigger[0].platform").
        message: Human-readable error description.
        schema_path: JSON Schema path that triggered the error.
    """

    path: str
    message: str
    schema_path: str = ""

    def __str__(self) -> str:
        """Human-readable representation."""
        if self.path:
            return f"{self.path}: {self.message}"
        return self.message


class ValidationResult(BaseModel):
    """Result of validating YAML against a schema.

    Attributes:
        valid: Whether the data conforms to the schema.
        errors: List of validation errors (empty when valid).
        warnings: List of non-fatal warnings.
        schema_name: Name of the schema that was validated against.
    """

    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)
    schema_name: str


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================


class SchemaRegistry:
    """Registry mapping schema names to Pydantic models and compiled JSON Schemas.

    Schemas are registered by name and compiled to JSON Schema on first access.
    Validation delegates to the jsonschema library.
    """

    def __init__(self) -> None:
        self._models: dict[str, type[BaseModel]] = {}
        self._compiled: dict[str, dict[str, Any]] = {}

    def register(self, name: str, model: type[BaseModel]) -> None:
        """Register a Pydantic model under a schema name.

        Args:
            name: Unique schema name (e.g., "ha.automation").
            model: Pydantic BaseModel class.

        Raises:
            ValueError: If name is already registered.
        """
        if name in self._models:
            raise ValueError(f"Schema '{name}' is already registered")
        self._models[name] = model
        # Invalidate cached compilation
        self._compiled.pop(name, None)

    def list_schemas(self) -> list[str]:
        """Return list of registered schema names."""
        return list(self._models.keys())

    def get_json_schema(self, name: str) -> dict[str, Any]:
        """Get the compiled JSON Schema for a registered schema.

        Args:
            name: Schema name.

        Returns:
            JSON Schema dict.

        Raises:
            KeyError: If schema name is not registered.
        """
        if name not in self._models:
            raise KeyError(f"Schema '{name}' is not registered")

        if name not in self._compiled:
            model = self._models[name]
            schema = model.model_json_schema()
            # Ensure additionalProperties is not restricted so that
            # HA configs with extra keys beyond our schema still pass.
            # Only set at top level; nested $defs keep their own rules.
            schema.setdefault("additionalProperties", True)
            self._compiled[name] = schema

        return self._compiled[name]

    def validate(self, name: str, data: dict[str, Any]) -> ValidationResult:
        """Validate a data dict against a registered schema.

        Args:
            name: Schema name.
            data: Parsed data to validate.

        Returns:
            ValidationResult with errors if any.

        Raises:
            KeyError: If schema name is not registered.
        """
        json_schema = self.get_json_schema(name)

        validator_cls = jsonschema.validators.validator_for(json_schema)
        # Configure validator to NOT fail on additional properties
        validator = validator_cls(json_schema)

        errors: list[ValidationError] = []
        for error in validator.iter_errors(data):
            path = _format_json_path(error.absolute_path)
            schema_path = _format_json_path(error.absolute_schema_path)
            errors.append(
                ValidationError(
                    path=path,
                    message=error.message,
                    schema_path=schema_path,
                )
            )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            schema_name=name,
        )


# =============================================================================
# TOP-LEVEL API
# =============================================================================


# Module-level default registry
registry = SchemaRegistry()


def validate_yaml(
    content: str,
    schema_name: str,
    *,
    registry: SchemaRegistry | None = None,
) -> ValidationResult:
    """Parse a YAML string and validate against a named schema.

    Args:
        content: YAML string to validate.
        schema_name: Registered schema name.
        registry: Optional SchemaRegistry instance (defaults to module-level registry).

    Returns:
        ValidationResult with structured errors.

    Raises:
        KeyError: If schema_name is not registered in the registry.
    """
    reg = registry or _get_default_registry()

    # Step 1: Parse YAML
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return ValidationResult(
            valid=False,
            errors=[
                ValidationError(
                    path="",
                    message=f"Invalid YAML syntax: {exc}",
                    schema_path="",
                )
            ],
            schema_name=schema_name,
        )

    # Step 2: Must be a dict (mapping)
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False,
            errors=[
                ValidationError(
                    path="",
                    message=(f"Expected a YAML mapping (object), got {type(data).__name__}"),
                    schema_path="",
                )
            ],
            schema_name=schema_name,
        )

    # Step 3: Normalize HA 2024.1+ syntax to old-style keys
    if schema_name == "ha.automation":
        data = _normalize_ha_automation(data)

    # Step 4: Validate against JSON Schema
    result = reg.validate(schema_name, data)

    # Step 5: Validate trigger/action/condition contents (HA automations)
    if result.valid and schema_name == "ha.automation":
        content_errors = _validate_ha_automation_contents(data)
        if content_errors:
            result = ValidationResult(
                valid=False,
                errors=result.errors + content_errors,
                warnings=result.warnings,
                schema_name=schema_name,
            )

    return result


async def validate_yaml_semantic(
    content: str,
    schema_name: str,
    *,
    ha_client: Any = None,
    registry: SchemaRegistry | None = None,
    cache: Any | None = None,
) -> ValidationResult:
    """Parse YAML, validate structurally, then validate semantically.

    Runs structural validation first (Feature 26). If structural
    validation passes, runs semantic validation against live HA
    registry state (Feature 27).

    Args:
        content: YAML string to validate.
        schema_name: Registered schema name.
        ha_client: HAClient instance for registry lookups (required if cache not provided).
        registry: Optional SchemaRegistry instance.
        cache: Optional pre-built HARegistryCache (if not provided, creates one from ha_client).

    Returns:
        ValidationResult combining structural and semantic errors/warnings.

    Raises:
        KeyError: If schema_name is not registered.
        ValueError: If neither ha_client nor cache is provided.
    """
    # Step 1: Structural validation (includes normalization)
    structural_result = validate_yaml(content, schema_name, registry=registry)
    if not structural_result.valid:
        return structural_result

    # Step 2: Parse and normalize for semantic validation
    data = yaml.safe_load(content)
    if schema_name == "ha.automation":
        data = _normalize_ha_automation(data)

    # Step 3: Semantic validation
    if cache is None:
        if ha_client is None:
            raise ValueError("Either ha_client or cache must be provided for semantic validation")
        from src.schema.ha.registry_cache import HARegistryCache

        cache = HARegistryCache(ha_client=ha_client)

    from src.schema.semantic import SemanticValidator

    semantic_validator = SemanticValidator(cache=cache)
    semantic_result = await semantic_validator.validate(data, schema_name=schema_name)

    # Merge: structural was valid, so errors come from semantic only
    return ValidationResult(
        valid=semantic_result.valid,
        errors=semantic_result.errors,
        warnings=semantic_result.warnings,
        schema_name=schema_name,
    )


def parse_ha_yaml(content: str) -> tuple[dict[str, Any], list[ValidationError]]:
    """Parse a YAML string and normalize HA automation syntax.

    Returns the parsed+normalized dict and any parse errors.
    Does NOT run schema validation -- use validate_yaml() for that.

    Args:
        content: YAML string to parse.

    Returns:
        Tuple of (normalized data dict, list of errors).
        On success, errors is empty. On failure, data is {}.
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return {}, [ValidationError(path="", message=f"Invalid YAML: {exc}")]

    if not isinstance(data, dict):
        return {}, [
            ValidationError(
                path="",
                message=f"Expected mapping, got {type(data).__name__}",
            )
        ]

    return _normalize_ha_automation(data), []


def detect_proposal_type(data: dict[str, Any]) -> str:
    """Detect proposal type from a normalized HA YAML dict.

    Args:
        data: Parsed and normalized YAML dict.

    Returns:
        One of "automation", "script", or "scene".
    """
    if data.get("entities") and not data.get("trigger"):
        return "scene"
    if data.get("sequence") and not data.get("trigger"):
        return "script"
    return "automation"


def _get_default_registry() -> SchemaRegistry:
    """Return the module-level default registry."""
    return registry


# =============================================================================
# HELPERS
# =============================================================================


def _format_json_path(path: Any) -> str:
    """Format a jsonschema deque path as a JSONPath-style string.

    Examples:
        deque([]) -> ""
        deque(["trigger", 0, "platform"]) -> "trigger[0].platform"
    """
    parts: list[str] = []
    for segment in path:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        elif parts:
            parts.append(f".{segment}")
        else:
            parts.append(str(segment))
    return "".join(parts)


# =============================================================================
# HA 2024.1+ NORMALIZATION
# =============================================================================


def _normalize_ha_automation(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize HA 2024.1+ automation syntax to old-style keys.

    Handles:
    - triggers → trigger, conditions → condition, actions → action (top-level)
    - trigger → platform (inside trigger definitions)
    - action → service (inside action definitions, when value is a service name)

    Returns a shallow copy of the top-level dict with normalized keys.
    Nested dicts (triggers, actions) are modified in-place since they
    come from a fresh yaml.safe_load() call.
    """
    result = dict(data)

    # Top-level plural → singular
    if "triggers" in result and "trigger" not in result:
        result["trigger"] = result.pop("triggers")
    if "conditions" in result and "condition" not in result:
        result["condition"] = result.pop("conditions")
    if "actions" in result and "action" not in result:
        result["action"] = result.pop("actions")

    # Normalize trigger dicts: trigger → platform
    triggers = result.get("trigger")
    if isinstance(triggers, dict):
        triggers = [triggers]
    if isinstance(triggers, list):
        for t in triggers:
            if isinstance(t, dict) and "trigger" in t and "platform" not in t:
                t["platform"] = t.pop("trigger")

    # Normalize action dicts: action → service (for service calls only)
    _normalize_ha_actions(result.get("action"))

    return result


def _normalize_ha_actions(actions: Any) -> None:
    """Normalize action dicts: rename 'action' key to 'service' for service calls.

    Modifies action dicts in-place. Only renames 'action' to 'service'
    when the value is a string containing a dot (service name pattern like
    'light.turn_on'), to avoid confusion with other action types.
    """
    if isinstance(actions, dict):
        actions = [actions]
    if not isinstance(actions, list):
        return

    for a in actions:
        if not isinstance(a, dict):
            continue
        if "action" in a and "service" not in a:
            action_val = a["action"]
            # Only rename if value is a service name (domain.service pattern)
            if isinstance(action_val, str) and "." in action_val:
                a["service"] = a.pop("action")


# =============================================================================
# CONTENT VALIDATION (typed model validation for HA automations)
# =============================================================================


def _validate_ha_automation_contents(data: dict[str, Any]) -> list[ValidationError]:
    """Validate individual trigger/action/condition contents using typed models.

    JSON Schema only validates the top-level structure of HAAutomation.
    This function provides deeper validation by checking each trigger, action,
    and condition dict against its specific Pydantic model, catching issues
    like missing required fields on specific trigger types.

    Args:
        data: Normalized automation dict (after _normalize_ha_automation).

    Returns:
        List of content validation errors (empty if all valid).
    """
    from src.schema.ha.automation import (
        ACTION_KEY_MAP,
        CONDITION_MODEL_MAP,
        TRIGGER_MODEL_MAP,
        GenericCondition,
        GenericTrigger,
    )

    errors: list[ValidationError] = []

    # --- Validate triggers ---
    triggers = data.get("trigger", [])
    if isinstance(triggers, dict):
        triggers = [triggers]
    if isinstance(triggers, list):
        for i, trigger in enumerate(triggers):
            if not isinstance(trigger, dict):
                continue

            platform = trigger.get("platform")
            if platform is None:
                errors.append(
                    ValidationError(
                        path=f"trigger[{i}]",
                        message=(
                            "Missing required 'platform' key (or 'trigger' in HA 2024.1+ syntax)"
                        ),
                    )
                )
                continue

            model = TRIGGER_MODEL_MAP.get(platform, GenericTrigger)
            try:
                model.model_validate(trigger)
            except PydanticValidationError as exc:
                for e in exc.errors():
                    loc = ".".join(str(part) for part in e["loc"])
                    errors.append(
                        ValidationError(
                            path=f"trigger[{i}].{loc}" if loc else f"trigger[{i}]",
                            message=e["msg"],
                        )
                    )

    # --- Validate actions ---
    actions = data.get("action", [])
    if isinstance(actions, dict):
        actions = [actions]
    if isinstance(actions, list):
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                continue

            # Determine action type by checking which unique key is present
            action_model: type[BaseModel] | None = None
            for key, model_cls in ACTION_KEY_MAP.items():
                if key in action:
                    action_model = model_cls
                    break

            if action_model is not None:
                try:
                    action_model.model_validate(action)
                except PydanticValidationError as exc:
                    for e in exc.errors():
                        loc = ".".join(str(part) for part in e["loc"])
                        errors.append(
                            ValidationError(
                                path=f"action[{i}].{loc}" if loc else f"action[{i}]",
                                message=e["msg"],
                            )
                        )

    # --- Validate conditions ---
    conditions = data.get("condition", [])
    if isinstance(conditions, dict):
        conditions = [conditions]
    if isinstance(conditions, list):
        for i, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                continue

            cond_type = condition.get("condition")
            if cond_type is None:
                errors.append(
                    ValidationError(
                        path=f"condition[{i}]",
                        message="Missing required 'condition' key",
                    )
                )
                continue

            cond_model = CONDITION_MODEL_MAP.get(cond_type, GenericCondition)
            try:
                cond_model.model_validate(condition)
            except PydanticValidationError as exc:
                for e in exc.errors():
                    loc = ".".join(str(part) for part in e["loc"])
                    errors.append(
                        ValidationError(
                            path=f"condition[{i}].{loc}" if loc else f"condition[{i}]",
                            message=e["msg"],
                        )
                    )

    return errors
