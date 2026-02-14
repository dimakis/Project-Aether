"""Review state for config review workflow."""

from typing import Any

from pydantic import Field

from .base import MessageState


class ReviewState(MessageState):
    """State for the config review workflow.

    Used when the Architect reviews existing HA automations/scripts/scenes
    and produces improvement suggestions via DS team analysis.
    """

    # Targets to review
    targets: list[str] = Field(
        default_factory=list,
        description="Entity IDs to review (e.g. automation.kitchen_lights)",
    )
    configs: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of entity_id -> original YAML config",
    )
    focus: str | None = Field(
        default=None,
        description="Optional focus area: energy, behavioral, efficiency, security",
    )

    # Context and analysis
    entity_context: dict[str, Any] = Field(
        default_factory=dict,
        description="All entities, areas, registry data for DS team context",
    )
    ds_findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Findings from DS team (energy, behavioral, diagnostic)",
    )
    suggestions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Architect suggestions per target (entity_id, suggested_yaml, review_notes)",
    )

    # Batch and split tracking
    review_session_id: str | None = Field(
        default=None,
        description="UUID grouping proposals from a batch review",
    )
    split_requested: bool = Field(
        default=False,
        description="Whether to create individual proposals per change",
    )

    # Error handling
    error: str | None = None
