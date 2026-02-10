"""Home Assistant Lovelace dashboard YAML schema.

Defines Pydantic models for Lovelace dashboard configurations
including views and cards.

Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LovelaceCard(BaseModel):
    """A Lovelace dashboard card.

    Cards have a required ``type`` field and varying additional
    fields depending on card type. Extra fields are allowed for
    forward compatibility with all card types.
    """

    type: str = Field(..., description="Card type (entities, markdown, gauge, etc.)")
    title: str | None = None
    # Common card fields — not exhaustive, extras allowed
    entities: list[str | dict[str, Any]] | None = None
    entity: str | None = None
    content: str | None = None
    cards: list[dict[str, Any]] | None = None  # for stack/grid cards
    show_header_toggle: bool | None = None

    model_config = {"extra": "allow"}


class LovelaceView(BaseModel):
    """A Lovelace dashboard view (tab).

    Each view has a title and a list of cards.
    """

    title: str | None = Field(default=None, description="View tab title")
    path: str | None = Field(default=None, description="URL path segment")
    icon: str | None = Field(default=None, description="MDI icon for the tab")
    badges: list[str | dict[str, Any]] | None = None
    cards: list[dict[str, Any]] = Field(default_factory=list, description="Cards in this view")
    type: str | None = Field(default=None, description="View type (masonry, sidebar, panel)")
    theme: str | None = None
    visible: bool | list[dict[str, Any]] | None = None

    model_config = {"extra": "allow"}


class LovelaceDashboard(BaseModel):
    """Top-level Lovelace dashboard configuration.

    Requires at least a ``views`` list.
    """

    title: str | None = Field(default=None, description="Dashboard title")
    views: list[dict[str, Any]] = Field(..., description="Dashboard views (tabs)")
    button_card_templates: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


__all__ = [
    "LovelaceCard",
    "LovelaceDashboard",
    "LovelaceView",
]
