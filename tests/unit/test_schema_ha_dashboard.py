"""Unit tests for HA dashboard (Lovelace) schema.

T205: Tests for LovelaceDashboard, View, Card.
Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError


class TestLovelaceCard:
    """Test card schema."""

    def test_entities_card(self) -> None:
        from src.schema.ha.dashboard import LovelaceCard

        card = LovelaceCard(
            type="entities",
            title="Living Room",
            entities=["light.living_room", "switch.fan"],
        )
        assert card.type == "entities"
        assert card.title == "Living Room"

    def test_markdown_card(self) -> None:
        from src.schema.ha.dashboard import LovelaceCard

        card = LovelaceCard(type="markdown", content="# Hello")
        assert card.type == "markdown"

    def test_card_requires_type(self) -> None:
        from src.schema.ha.dashboard import LovelaceCard

        with pytest.raises(ValidationError, match="type"):
            LovelaceCard()


class TestLovelaceView:
    """Test view schema."""

    def test_minimal_view(self) -> None:
        from src.schema.ha.dashboard import LovelaceView

        view = LovelaceView(
            title="Overview",
            cards=[{"type": "markdown", "content": "Hello"}],
        )
        assert view.title == "Overview"
        assert len(view.cards) == 1

    def test_view_with_path_and_icon(self) -> None:
        from src.schema.ha.dashboard import LovelaceView

        view = LovelaceView(
            title="Lights",
            path="lights",
            icon="mdi:lightbulb",
            cards=[],
        )
        assert view.path == "lights"
        assert view.icon == "mdi:lightbulb"

    def test_view_empty_cards(self) -> None:
        from src.schema.ha.dashboard import LovelaceView

        view = LovelaceView(title="Empty", cards=[])
        assert view.cards == []


class TestLovelaceDashboard:
    """Test full dashboard schema."""

    def test_minimal_dashboard(self) -> None:
        from src.schema.ha.dashboard import LovelaceDashboard

        dash = LovelaceDashboard(
            views=[
                {
                    "title": "Overview",
                    "cards": [{"type": "markdown", "content": "Hello"}],
                }
            ],
        )
        assert len(dash.views) == 1

    def test_dashboard_with_title(self) -> None:
        from src.schema.ha.dashboard import LovelaceDashboard

        dash = LovelaceDashboard(
            title="My Dashboard",
            views=[{"title": "Tab 1", "cards": []}],
        )
        assert dash.title == "My Dashboard"

    def test_dashboard_missing_views(self) -> None:
        from src.schema.ha.dashboard import LovelaceDashboard

        with pytest.raises(ValidationError, match="views"):
            LovelaceDashboard()

    def test_dashboard_yaml_roundtrip(self) -> None:
        """Validate a dashboard YAML string via registry."""
        from src.schema.core import SchemaRegistry
        from src.schema.ha.dashboard import LovelaceDashboard

        registry = SchemaRegistry()
        registry.register("ha.dashboard", LovelaceDashboard)

        yaml_str = """\
title: Home Overview
views:
  - title: Main
    cards:
      - type: entities
        title: Lights
        entities:
          - light.living_room
          - light.bedroom
  - title: Energy
    cards:
      - type: markdown
        content: "# Energy Dashboard"
"""
        data = yaml.safe_load(yaml_str)
        result = registry.validate("ha.dashboard", data)
        assert result.valid is True, f"Errors: {result.errors}"

    def test_dashboard_invalid_missing_views(self) -> None:
        """YAML without views key fails schema validation."""
        from src.schema.core import SchemaRegistry
        from src.schema.ha.dashboard import LovelaceDashboard

        registry = SchemaRegistry()
        registry.register("ha.dashboard", LovelaceDashboard)

        data = {"title": "No Views"}
        result = registry.validate("ha.dashboard", data)
        assert result.valid is False
        assert any("views" in e.message for e in result.errors)
