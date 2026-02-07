"""Factory Boy factories for test data generation.

Provides factories for creating realistic test instances
of all domain models.

Constitution: Reliability & Quality - consistent test data.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import factory
from factory import LazyAttribute, LazyFunction, SubFactory

# Note: These factories use simple dict-based generation
# rather than SQLAlchemy integration to allow use in unit tests
# without database dependencies.


class BaseFactory(factory.Factory):
    """Base factory with common fields."""

    class Meta:
        abstract = True

    id = LazyFunction(lambda: str(uuid4()))
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


# =============================================================================
# HA ENTITY FACTORIES
# =============================================================================


class AreaFactory(BaseFactory):
    """Factory for Area entities."""

    class Meta:
        model = dict

    ha_area_id = LazyAttribute(lambda o: f"area_{o.id[:8]}")
    name = factory.Sequence(lambda n: f"Area {n}")
    floor_id = None


class DeviceFactory(BaseFactory):
    """Factory for Device entities."""

    class Meta:
        model = dict

    ha_device_id = LazyAttribute(lambda o: f"device_{o.id[:8]}")
    name = factory.Sequence(lambda n: f"Device {n}")
    manufacturer = factory.Faker("company")
    model = factory.Faker("word")
    sw_version = factory.Faker("numerify", text="#.#.#")
    area_id = None


class EntityFactory(BaseFactory):
    """Factory for HA Entity records."""

    class Meta:
        model = dict

    entity_id = factory.Sequence(lambda n: f"light.entity_{n}")
    domain = "light"
    name = factory.Sequence(lambda n: f"Light {n}")
    state = "off"
    attributes = LazyFunction(lambda: {"brightness": 0, "friendly_name": "Test Light"})
    device_id = None
    area_id = None
    platform = "mock"
    device_class = None
    supported_features = 0
    disabled = False
    hidden = False


class LightEntityFactory(EntityFactory):
    """Factory for light entities specifically."""

    entity_id = factory.Sequence(lambda n: f"light.light_{n}")
    domain = "light"
    attributes = LazyFunction(
        lambda: {
            "brightness": 128,
            "color_mode": "brightness",
            "supported_color_modes": ["brightness"],
        }
    )
    supported_features = 44  # SUPPORT_BRIGHTNESS | SUPPORT_TRANSITION


class SensorEntityFactory(EntityFactory):
    """Factory for sensor entities."""

    entity_id = factory.Sequence(lambda n: f"sensor.sensor_{n}")
    domain = "sensor"
    state = factory.Faker("pyfloat", min_value=0, max_value=100)
    attributes = LazyFunction(
        lambda: {
            "unit_of_measurement": "°C",
            "device_class": "temperature",
        }
    )


class SwitchEntityFactory(EntityFactory):
    """Factory for switch entities."""

    entity_id = factory.Sequence(lambda n: f"switch.switch_{n}")
    domain = "switch"
    state = factory.Faker("random_element", elements=["on", "off"])


# =============================================================================
# AGENT FACTORIES
# =============================================================================


class AgentFactory(BaseFactory):
    """Factory for Agent records."""

    class Meta:
        model = dict

    name = factory.Faker(
        "random_element",
        elements=["librarian", "categorizer", "architect", "developer", "data_scientist"],
    )
    description = factory.Faker("sentence")
    version = "1.0.0"
    prompt_template = factory.Faker("paragraph")


class ConversationFactory(BaseFactory):
    """Factory for Conversation records."""

    class Meta:
        model = dict

    status = "active"
    started_at = LazyFunction(lambda: datetime.now(timezone.utc))
    ended_at = None
    message_count = 0
    summary = None
    mlflow_run_id = LazyAttribute(lambda o: f"run_{o.id[:8]}")


class MessageFactory(BaseFactory):
    """Factory for Message records."""

    class Meta:
        model = dict

    conversation_id = LazyFunction(lambda: str(uuid4()))
    role = factory.Faker("random_element", elements=["user", "assistant", "system"])
    content = factory.Faker("paragraph")
    sequence_number = factory.Sequence(lambda n: n)
    tokens_used = factory.Faker("random_int", min=10, max=500)
    agent_name = None


# =============================================================================
# AUTOMATION FACTORIES
# =============================================================================


class AutomationFactory(BaseFactory):
    """Factory for Automation records."""

    class Meta:
        model = dict

    name = factory.Sequence(lambda n: f"Automation {n}")
    description = factory.Faker("sentence")
    status = "draft"
    yaml_content = LazyAttribute(
        lambda o: f"""
alias: {o.name}
description: {o.description}
trigger:
  - platform: state
    entity_id: light.living_room
action:
  - service: light.turn_on
    entity_id: light.kitchen
"""
    )
    conversation_id = None
    deployed_at = None
    approved = False
    approved_by = None


class HAAutomationFactory(BaseFactory):
    """Factory for HA Automation sync records."""

    class Meta:
        model = dict

    ha_automation_id = LazyAttribute(lambda o: f"automation.auto_{o.id[:8]}")
    alias = factory.Sequence(lambda n: f"HA Automation {n}")
    description = factory.Faker("sentence")
    state = "on"
    mode = "single"
    trigger_types = LazyFunction(lambda: ["state"])
    action_count = factory.Faker("random_int", min=1, max=5)


# =============================================================================
# DISCOVERY FACTORIES
# =============================================================================


class DiscoverySessionFactory(BaseFactory):
    """Factory for DiscoverySession records."""

    class Meta:
        model = dict

    started_at = LazyFunction(lambda: datetime.now(timezone.utc))
    completed_at = LazyAttribute(
        lambda o: o.started_at + timedelta(seconds=factory.Faker("random_int", min=5, max=60).generate())
    )
    status = "completed"
    entities_found = factory.Faker("random_int", min=10, max=100)
    entities_added = factory.Faker("random_int", min=0, max=10)
    entities_removed = 0
    entities_updated = factory.Faker("random_int", min=0, max=5)
    devices_found = factory.Faker("random_int", min=5, max=20)
    areas_found = factory.Faker("random_int", min=3, max=10)
    services_found = factory.Faker("random_int", min=50, max=200)
    error_message = None
    mlflow_run_id = LazyAttribute(lambda o: f"run_{o.id[:8]}")


# =============================================================================
# INSIGHT FACTORIES
# =============================================================================


class InsightFactory(BaseFactory):
    """Factory for Insight records."""

    class Meta:
        model = dict

    type = factory.Faker(
        "random_element",
        elements=["energy_optimization", "usage_pattern", "anomaly"],
    )
    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("paragraph")
    severity = factory.Faker("random_element", elements=["info", "warning", "critical"])
    data = LazyFunction(lambda: {"metric": 42, "comparison": "baseline"})
    entities = LazyFunction(lambda: ["sensor.energy_usage"])
    confidence_score = factory.Faker("pyfloat", min_value=0.7, max_value=1.0)
    acknowledged = False


# =============================================================================
# MCP RESPONSE FACTORIES
# =============================================================================


class MCPSystemOverviewFactory(factory.Factory):
    """Factory for MCP system_overview responses."""

    class Meta:
        model = dict

    total_entities = factory.Faker("random_int", min=20, max=200)
    domains = LazyFunction(
        lambda: {
            "light": {"count": 10, "states": {"on": 3, "off": 7}},
            "switch": {"count": 8, "states": {"on": 2, "off": 6}},
            "sensor": {"count": 50, "states": {}},
            "binary_sensor": {"count": 15, "states": {"on": 5, "off": 10}},
            "climate": {"count": 2, "states": {"heat": 1, "off": 1}},
        }
    )
    domain_samples = LazyFunction(
        lambda: {
            "light": [
                {"entity_id": "light.living_room", "state": "off"},
                {"entity_id": "light.bedroom", "state": "on"},
            ]
        }
    )


class MCPEntityListFactory(factory.Factory):
    """Factory for MCP list_entities responses."""

    class Meta:
        model = dict

    entities = LazyFunction(
        lambda: [
            {
                "entity_id": f"light.light_{i}",
                "state": "off" if i % 2 == 0 else "on",
                "name": f"Light {i}",
            }
            for i in range(10)
        ]
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_entity_batch(
    domain: str = "light",
    count: int = 5,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Create a batch of entity dictionaries.

    Args:
        domain: Entity domain
        count: Number of entities
        **kwargs: Additional fields for all entities

    Returns:
        List of entity dictionaries
    """
    factory_map = {
        "light": LightEntityFactory,
        "sensor": SensorEntityFactory,
        "switch": SwitchEntityFactory,
    }
    factory_class = factory_map.get(domain, EntityFactory)
    return [factory_class.build(domain=domain, **kwargs) for _ in range(count)]


def create_discovery_with_entities(
    entity_count: int = 20,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Create a discovery session with associated entities.

    Args:
        entity_count: Number of entities to create

    Returns:
        Tuple of (discovery_session, entities)
    """
    session = DiscoverySessionFactory.build(entities_found=entity_count)
    entities = create_entity_batch(count=entity_count)
    return session, entities
