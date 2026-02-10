"""Unit tests for HA common schema types.

T203: Tests for Mode enum, EntityId, ServiceName, Duration, and shared types.
Feature 26: YAML Schema Compiler/Validator.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from src.schema.ha.common import EntityId, Mode, ServiceName  # noqa: TC001


class TestMode:
    """Test the Mode enum."""

    def test_valid_modes(self) -> None:
        """All four HA automation modes are valid."""
        from src.schema.ha.common import Mode

        assert Mode.SINGLE == "single"
        assert Mode.RESTART == "restart"
        assert Mode.QUEUED == "queued"
        assert Mode.PARALLEL == "parallel"

    def test_mode_values(self) -> None:
        """Mode enum contains exactly four values."""
        from src.schema.ha.common import Mode

        assert len(Mode) == 4

    def test_mode_in_model(self) -> None:
        """Mode works as a Pydantic field with default."""
        from src.schema.ha.common import Mode

        class TestModel(BaseModel):
            mode: Mode = Mode.SINGLE

        m = TestModel()
        assert m.mode == Mode.SINGLE

        m2 = TestModel(mode="restart")
        assert m2.mode == Mode.RESTART

    def test_mode_invalid_value(self) -> None:
        """Invalid mode value raises ValidationError."""

        class TestModel(BaseModel):
            mode: Mode

        with pytest.raises(ValidationError):
            TestModel(mode="invalid_mode")


class TestEntityId:
    """Test the EntityId annotated type."""

    def test_valid_entity_ids(self) -> None:
        """Valid HA entity IDs pass validation."""

        class TestModel(BaseModel):
            entity_id: EntityId

        valid_ids = [
            "light.living_room",
            "switch.bedroom_fan",
            "sensor.temperature_1",
            "binary_sensor.motion_front_door",
            "climate.main_floor",
            "automation.morning_routine",
            "input_boolean.guest_mode",
            "media_player.living_room_tv",
        ]
        for eid in valid_ids:
            m = TestModel(entity_id=eid)
            assert m.entity_id == eid

    def test_invalid_entity_ids(self) -> None:
        """Invalid entity IDs raise ValidationError."""

        class TestModel(BaseModel):
            entity_id: EntityId

        invalid_ids = [
            "no_domain",  # missing domain.name format
            ".no_domain_prefix",  # starts with dot
            "UPPER.case",  # uppercase domain
            "",  # empty
        ]
        for eid in invalid_ids:
            with pytest.raises(ValidationError, match="entity_id"):
                TestModel(entity_id=eid)


class TestServiceName:
    """Test the ServiceName annotated type."""

    def test_valid_service_names(self) -> None:
        """Valid HA service names pass validation."""

        class TestModel(BaseModel):
            service: ServiceName

        valid_services = [
            "light.turn_on",
            "light.turn_off",
            "switch.toggle",
            "climate.set_temperature",
            "media_player.play_media",
            "automation.trigger",
            "homeassistant.restart",
            "notify.mobile_app_phone",
        ]
        for svc in valid_services:
            m = TestModel(service=svc)
            assert m.service == svc

    def test_invalid_service_names(self) -> None:
        """Invalid service names raise ValidationError."""

        class TestModel(BaseModel):
            service: ServiceName

        invalid_services = [
            "no_service",  # missing domain.service format
            ".turn_on",  # missing domain
            "LIGHT.turn_on",  # uppercase
            "",  # empty
        ]
        for svc in invalid_services:
            with pytest.raises(ValidationError):
                TestModel(service=svc)


class TestServiceTarget:
    """Test the ServiceTarget model."""

    def test_entity_id_target(self) -> None:
        """ServiceTarget accepts entity_id."""
        from src.schema.ha.common import ServiceTarget

        target = ServiceTarget(entity_id="light.bedroom")
        assert target.entity_id == "light.bedroom"

    def test_entity_id_list_target(self) -> None:
        """ServiceTarget accepts a list of entity_ids."""
        from src.schema.ha.common import ServiceTarget

        target = ServiceTarget(entity_id=["light.bedroom", "light.kitchen"])
        assert target.entity_id == ["light.bedroom", "light.kitchen"]

    def test_device_id_target(self) -> None:
        """ServiceTarget accepts device_id."""
        from src.schema.ha.common import ServiceTarget

        target = ServiceTarget(device_id="abc123")
        assert target.device_id == "abc123"

    def test_area_id_target(self) -> None:
        """ServiceTarget accepts area_id."""
        from src.schema.ha.common import ServiceTarget

        target = ServiceTarget(area_id="living_room")
        assert target.area_id == "living_room"

    def test_combined_targets(self) -> None:
        """ServiceTarget accepts combinations."""
        from src.schema.ha.common import ServiceTarget

        target = ServiceTarget(
            entity_id="light.bedroom",
            area_id="bedroom",
        )
        assert target.entity_id == "light.bedroom"
        assert target.area_id == "bedroom"

    def test_empty_target(self) -> None:
        """ServiceTarget can be empty (all optional)."""
        from src.schema.ha.common import ServiceTarget

        target = ServiceTarget()
        assert target.entity_id is None
        assert target.device_id is None
        assert target.area_id is None
