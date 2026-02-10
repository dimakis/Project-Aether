"""YAML Schema Compiler/Validator.

General-purpose YAML schema validation framework using Pydantic models
that compile to JSON Schema. Ships with Home Assistant config schemas
as the primary use case.

Feature 26: YAML Schema Compiler/Validator (Structural).

Usage::

    from src.schema import validate_yaml, registry

    result = validate_yaml(yaml_string, "ha.automation")
    if not result.valid:
        for error in result.errors:
            print(f"{error.path}: {error.message}")
"""

from __future__ import annotations

# Auto-register HA schemas on import
import src.schema.ha  # noqa: F401
from src.schema.core import (
    SchemaRegistry,
    ValidationError,
    ValidationResult,
    registry,
    validate_yaml,
    validate_yaml_semantic,
)

__all__ = [
    "SchemaRegistry",
    "ValidationError",
    "ValidationResult",
    "registry",
    "validate_yaml",
    "validate_yaml_semantic",
]
