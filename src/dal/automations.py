"""Automation, Script, and Scene repositories for CRUD operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dal.base import BaseRepository
from src.storage.entities.ha_automation import HAAutomation, Scene, Script


class AutomationRepository(BaseRepository[HAAutomation]):
    """Repository for HAAutomation CRUD operations."""
    
    model = HAAutomation
    ha_id_field = "ha_automation_id"
    order_by_field = "alias"

    async def get_by_ha_automation_id(self, ha_automation_id: str) -> HAAutomation | None:
        """Get automation by Home Assistant automation ID.

        Args:
            ha_automation_id: HA automation ID

        Returns:
            HAAutomation or None
        """
        return await self.get_by_ha_id(ha_automation_id)

    async def get_by_entity_id(self, entity_id: str) -> HAAutomation | None:
        """Get automation by entity ID.

        Args:
            entity_id: Entity ID (automation.xxx)

        Returns:
            HAAutomation or None
        """
        result = await self.session.execute(
            select(HAAutomation).where(HAAutomation.entity_id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        state: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[HAAutomation]:
        """List automations with optional filtering.

        Args:
            state: Filter by state (on/off)
            limit: Max results
            offset: Skip results

        Returns:
            List of automations
        """
        return await super().list_all(limit=limit, offset=offset, state=state)

    async def count(self, state: str | None = None) -> int:
        """Count automations.

        Args:
            state: Optional state filter

        Returns:
            Automation count
        """
        return await super().count(state=state)

    async def delete(self, ha_automation_id: str) -> bool:
        """Delete an automation.

        Args:
            ha_automation_id: HA automation ID

        Returns:
            True if deleted
        """
        automation = await self.get_by_ha_automation_id(ha_automation_id)
        if not automation:
            return False

        await self.session.delete(automation)
        await self.session.flush()
        return True

    async def get_all_ha_automation_ids(self) -> set[str]:
        """Get all HA automation IDs in database.

        Returns:
            Set of automation IDs
        """
        return await self.get_all_ha_ids()


class ScriptRepository(BaseRepository[Script]):
    """Repository for Script CRUD operations."""
    
    model = Script
    ha_id_field = "entity_id"
    order_by_field = "alias"

    async def get_by_entity_id(self, entity_id: str) -> Script | None:
        """Get script by entity ID.

        Args:
            entity_id: Entity ID (script.xxx)

        Returns:
            Script or None
        """
        result = await self.session.execute(
            select(Script).where(Script.entity_id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        state: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Script]:
        """List scripts with optional filtering.

        Args:
            state: Filter by state (on=running, off=idle)
            limit: Max results
            offset: Skip results

        Returns:
            List of scripts
        """
        return await super().list_all(limit=limit, offset=offset, state=state)

    async def delete(self, entity_id: str) -> bool:
        """Delete a script.

        Args:
            entity_id: Script entity ID

        Returns:
            True if deleted
        """
        script = await self.get_by_entity_id(entity_id)
        if not script:
            return False

        await self.session.delete(script)
        await self.session.flush()
        return True

    async def get_all_entity_ids(self) -> set[str]:
        """Get all script entity IDs in database.

        Returns:
            Set of entity IDs
        """
        return await self.get_all_ha_ids()


class SceneRepository(BaseRepository[Scene]):
    """Repository for Scene CRUD operations."""
    
    model = Scene
    ha_id_field = "entity_id"
    order_by_field = "name"

    async def get_by_entity_id(self, entity_id: str) -> Scene | None:
        """Get scene by entity ID.

        Args:
            entity_id: Entity ID (scene.xxx)

        Returns:
            Scene or None
        """
        result = await self.session.execute(
            select(Scene).where(Scene.entity_id == entity_id)
        )
        return result.scalar_one_or_none()


    async def delete(self, entity_id: str) -> bool:
        """Delete a scene.

        Args:
            entity_id: Scene entity ID

        Returns:
            True if deleted
        """
        scene = await self.get_by_entity_id(entity_id)
        if not scene:
            return False

        await self.session.delete(scene)
        await self.session.flush()
        return True

    async def get_all_entity_ids(self) -> set[str]:
        """Get all scene entity IDs in database.

        Returns:
            Set of entity IDs
        """
        return await self.get_all_ha_ids()
