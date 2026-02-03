"""Natural language query interface using LLM.

Provides a way to query entities using natural language,
translating user questions into database queries.
"""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.dal.areas import AreaRepository
from src.dal.automations import AutomationRepository, SceneRepository, ScriptRepository
from src.dal.devices import DeviceRepository
from src.dal.entities import EntityRepository


class NaturalLanguageQueryEngine:
    """Engine for processing natural language queries about home entities.

    Uses LLM to understand user intent and translate to database queries.
    """

    def __init__(self, session: AsyncSession):
        """Initialize query engine.

        Args:
            session: Database session
        """
        self.session = session
        self.entity_repo = EntityRepository(session)
        self.device_repo = DeviceRepository(session)
        self.area_repo = AreaRepository(session)
        self.automation_repo = AutomationRepository(session)
        self.script_repo = ScriptRepository(session)
        self.scene_repo = SceneRepository(session)

    async def query(
        self,
        question: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a natural language query.

        Args:
            question: User's natural language question
            context: Optional context from conversation

        Returns:
            Query result with entities and explanation
        """
        # Parse the query intent
        intent = await self._parse_intent(question)

        # Execute appropriate query based on intent
        result = await self._execute_query(intent)

        return {
            "question": question,
            "intent": intent,
            "result": result,
            "explanation": self._generate_explanation(intent, result),
        }

    async def _parse_intent(self, question: str) -> dict[str, Any]:
        """Parse user question into structured intent.

        This is a simplified version that uses pattern matching.
        A full implementation would use an LLM for intent parsing.

        Args:
            question: User question

        Returns:
            Structured intent
        """
        question_lower = question.lower()

        # Default intent
        intent: dict[str, Any] = {
            "type": "list_entities",
            "filters": {},
            "limit": 20,
        }

        # Domain detection
        domains = [
            "light", "switch", "sensor", "binary_sensor", "climate",
            "cover", "fan", "media_player", "automation", "script", "scene",
        ]
        for domain in domains:
            if domain in question_lower or f"{domain}s" in question_lower:
                intent["filters"]["domain"] = domain
                break

        # State detection
        if any(word in question_lower for word in ["on", "active", "running"]):
            intent["filters"]["state"] = "on"
        elif any(word in question_lower for word in ["off", "inactive", "idle"]):
            intent["filters"]["state"] = "off"
        elif "unavailable" in question_lower:
            intent["filters"]["state"] = "unavailable"

        # Area detection (basic)
        area_keywords = ["living room", "bedroom", "kitchen", "bathroom", "office", "garage"]
        for area in area_keywords:
            if area in question_lower:
                intent["filters"]["area_name"] = area
                break

        # Count queries
        if any(word in question_lower for word in ["how many", "count", "total"]):
            intent["type"] = "count"

        # Specific entity query
        if "entity_id:" in question_lower:
            # Extract entity ID
            parts = question_lower.split("entity_id:")
            if len(parts) > 1:
                entity_id = parts[1].strip().split()[0]
                intent["type"] = "get_entity"
                intent["entity_id"] = entity_id

        # Device queries
        if "device" in question_lower:
            intent["type"] = "list_devices"

        # Area queries
        if "area" in question_lower and "which" in question_lower:
            intent["type"] = "list_areas"

        # Automation queries
        if "automation" in question_lower:
            intent["type"] = "list_automations"

        return intent

    async def _execute_query(self, intent: dict[str, Any]) -> dict[str, Any]:
        """Execute query based on parsed intent.

        Args:
            intent: Structured intent

        Returns:
            Query results
        """
        query_type = intent.get("type", "list_entities")
        filters = intent.get("filters", {})
        limit = intent.get("limit", 20)

        if query_type == "count":
            domain = filters.get("domain")
            count = await self.entity_repo.count(domain=domain)
            return {"count": count, "domain": domain}

        if query_type == "get_entity":
            entity_id = intent.get("entity_id")
            entity = await self.entity_repo.get_by_entity_id(entity_id)
            if entity:
                return {"entity": self._entity_to_dict(entity)}
            return {"entity": None, "message": f"Entity {entity_id} not found"}

        if query_type == "list_devices":
            devices = await self.device_repo.list_all(limit=limit)
            return {
                "devices": [self._device_to_dict(d) for d in devices],
                "count": len(devices),
            }

        if query_type == "list_areas":
            areas = await self.area_repo.list_all(limit=limit)
            return {
                "areas": [self._area_to_dict(a) for a in areas],
                "count": len(areas),
            }

        if query_type == "list_automations":
            state = filters.get("state")
            automations = await self.automation_repo.list_all(state=state, limit=limit)
            return {
                "automations": [self._automation_to_dict(a) for a in automations],
                "count": len(automations),
            }

        # Default: list entities
        entities = await self.entity_repo.list_all(
            domain=filters.get("domain"),
            state=filters.get("state"),
            limit=limit,
        )

        # Filter by area name if specified (post-query filter)
        area_name = filters.get("area_name")
        if area_name:
            entities = [
                e for e in entities
                if e.area and area_name.lower() in e.area.name.lower()
            ]

        return {
            "entities": [self._entity_to_dict(e) for e in entities],
            "count": len(entities),
            "filters_applied": filters,
        }

    def _generate_explanation(
        self,
        intent: dict[str, Any],
        result: dict[str, Any],
    ) -> str:
        """Generate human-readable explanation of query result.

        Args:
            intent: Query intent
            result: Query result

        Returns:
            Explanation string
        """
        query_type = intent.get("type", "list_entities")
        filters = intent.get("filters", {})

        if query_type == "count":
            domain = filters.get("domain", "all")
            count = result.get("count", 0)
            return f"Found {count} {domain} entities."

        if query_type == "get_entity":
            entity = result.get("entity")
            if entity:
                return f"Found entity {entity['entity_id']} with state '{entity['state']}'."
            return "Entity not found."

        if query_type == "list_devices":
            count = result.get("count", 0)
            return f"Found {count} devices."

        if query_type == "list_areas":
            count = result.get("count", 0)
            return f"Found {count} areas."

        if query_type == "list_automations":
            count = result.get("count", 0)
            state = filters.get("state", "any")
            return f"Found {count} automations with state '{state}'."

        # Entity list
        count = result.get("count", 0)
        domain = filters.get("domain", "")
        state = filters.get("state", "")
        area = filters.get("area_name", "")

        parts = [f"Found {count}"]
        if state:
            parts.append(f"'{state}'")
        if domain:
            parts.append(f"{domain}")
        parts.append("entities")
        if area:
            parts.append(f"in {area}")

        return " ".join(parts) + "."

    def _entity_to_dict(self, entity: Any) -> dict[str, Any]:
        """Convert entity to dictionary.

        Args:
            entity: HAEntity instance

        Returns:
            Entity as dictionary
        """
        return {
            "id": entity.id,
            "entity_id": entity.entity_id,
            "name": entity.name,
            "domain": entity.domain,
            "state": entity.state,
            "device_class": entity.device_class,
            "unit_of_measurement": entity.unit_of_measurement,
            "area": entity.area.name if entity.area else None,
            "device": entity.device.name if entity.device else None,
        }

    def _device_to_dict(self, device: Any) -> dict[str, Any]:
        """Convert device to dictionary.

        Args:
            device: Device instance

        Returns:
            Device as dictionary
        """
        return {
            "id": device.id,
            "ha_device_id": device.ha_device_id,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "area": device.area.name if device.area else None,
        }

    def _area_to_dict(self, area: Any) -> dict[str, Any]:
        """Convert area to dictionary.

        Args:
            area: Area instance

        Returns:
            Area as dictionary
        """
        return {
            "id": area.id,
            "ha_area_id": area.ha_area_id,
            "name": area.name,
            "entity_count": len(area.entities) if area.entities else 0,
        }

    def _automation_to_dict(self, automation: Any) -> dict[str, Any]:
        """Convert automation to dictionary.

        Args:
            automation: HAAutomation instance

        Returns:
            Automation as dictionary
        """
        return {
            "id": automation.id,
            "entity_id": automation.entity_id,
            "alias": automation.alias,
            "state": automation.state,
            "mode": automation.mode,
            "trigger_count": automation.trigger_count,
            "action_count": automation.action_count,
        }


async def query_entities(
    session: AsyncSession,
    question: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience function to run a natural language query.

    Args:
        session: Database session
        question: Natural language question
        context: Optional conversation context

    Returns:
        Query result
    """
    engine = NaturalLanguageQueryEngine(session)
    return await engine.query(question, context)
