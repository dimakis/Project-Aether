"""Automation, Script, and Scene repositories for CRUD operations."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities.ha_automation import HAAutomation, Scene, Script


class AutomationRepository:
    """Repository for HAAutomation CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, automation_id: str) -> HAAutomation | None:
        """Get automation by internal ID.

        Args:
            automation_id: Internal UUID

        Returns:
            HAAutomation or None
        """
        result = await self.session.execute(
            select(HAAutomation).where(HAAutomation.id == automation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ha_automation_id(self, ha_automation_id: str) -> HAAutomation | None:
        """Get automation by Home Assistant automation ID.

        Args:
            ha_automation_id: HA automation ID

        Returns:
            HAAutomation or None
        """
        result = await self.session.execute(
            select(HAAutomation).where(HAAutomation.ha_automation_id == ha_automation_id)
        )
        return result.scalar_one_or_none()

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
        query = select(HAAutomation)

        if state:
            query = query.where(HAAutomation.state == state)

        query = query.order_by(HAAutomation.alias).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, state: str | None = None) -> int:
        """Count automations.

        Args:
            state: Optional state filter

        Returns:
            Automation count
        """
        from sqlalchemy import func

        query = select(func.count(HAAutomation.id))
        if state:
            query = query.where(HAAutomation.state == state)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, data: dict[str, Any]) -> HAAutomation:
        """Create a new automation record.

        Args:
            data: Automation data

        Returns:
            Created automation
        """
        automation = HAAutomation(
            id=str(uuid4()),
            **data,
            last_synced_at=datetime.utcnow(),
        )
        self.session.add(automation)
        await self.session.flush()
        return automation

    async def upsert(self, data: dict[str, Any]) -> tuple[HAAutomation, bool]:
        """Create or update an automation.

        Args:
            data: Automation data (must include ha_automation_id)

        Returns:
            Tuple of (automation, created)
        """
        ha_automation_id = data.get("ha_automation_id")
        if not ha_automation_id:
            raise ValueError("ha_automation_id required for upsert")

        existing = await self.get_by_ha_automation_id(ha_automation_id)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            existing.last_synced_at = datetime.utcnow()
            await self.session.flush()
            return existing, False
        else:
            automation = await self.create(data)
            return automation, True

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
        result = await self.session.execute(select(HAAutomation.ha_automation_id))
        return {row[0] for row in result.fetchall()}


class ScriptRepository:
    """Repository for Script CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, script_id: str) -> Script | None:
        """Get script by internal ID.

        Args:
            script_id: Internal UUID

        Returns:
            Script or None
        """
        result = await self.session.execute(
            select(Script).where(Script.id == script_id)
        )
        return result.scalar_one_or_none()

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
        query = select(Script)

        if state:
            query = query.where(Script.state == state)

        query = query.order_by(Script.alias).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count all scripts.

        Returns:
            Script count
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count(Script.id)))
        return result.scalar() or 0

    async def create(self, data: dict[str, Any]) -> Script:
        """Create a new script record.

        Args:
            data: Script data

        Returns:
            Created script
        """
        script = Script(
            id=str(uuid4()),
            **data,
            last_synced_at=datetime.utcnow(),
        )
        self.session.add(script)
        await self.session.flush()
        return script

    async def upsert(self, data: dict[str, Any]) -> tuple[Script, bool]:
        """Create or update a script.

        Args:
            data: Script data (must include entity_id)

        Returns:
            Tuple of (script, created)
        """
        entity_id = data.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required for upsert")

        existing = await self.get_by_entity_id(entity_id)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            existing.last_synced_at = datetime.utcnow()
            await self.session.flush()
            return existing, False
        else:
            script = await self.create(data)
            return script, True

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
        result = await self.session.execute(select(Script.entity_id))
        return {row[0] for row in result.fetchall()}


class SceneRepository:
    """Repository for Scene CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, scene_id: str) -> Scene | None:
        """Get scene by internal ID.

        Args:
            scene_id: Internal UUID

        Returns:
            Scene or None
        """
        result = await self.session.execute(
            select(Scene).where(Scene.id == scene_id)
        )
        return result.scalar_one_or_none()

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

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Scene]:
        """List scenes.

        Args:
            limit: Max results
            offset: Skip results

        Returns:
            List of scenes
        """
        query = select(Scene).order_by(Scene.name).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count all scenes.

        Returns:
            Scene count
        """
        from sqlalchemy import func

        result = await self.session.execute(select(func.count(Scene.id)))
        return result.scalar() or 0

    async def create(self, data: dict[str, Any]) -> Scene:
        """Create a new scene record.

        Args:
            data: Scene data

        Returns:
            Created scene
        """
        scene = Scene(
            id=str(uuid4()),
            **data,
            last_synced_at=datetime.utcnow(),
        )
        self.session.add(scene)
        await self.session.flush()
        return scene

    async def upsert(self, data: dict[str, Any]) -> tuple[Scene, bool]:
        """Create or update a scene.

        Args:
            data: Scene data (must include entity_id)

        Returns:
            Tuple of (scene, created)
        """
        entity_id = data.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id required for upsert")

        existing = await self.get_by_entity_id(entity_id)
        if existing:
            for key, value in data.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            existing.last_synced_at = datetime.utcnow()
            await self.session.flush()
            return existing, False
        else:
            scene = await self.create(data)
            return scene, True

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
        result = await self.session.execute(select(Scene.entity_id))
        return {row[0] for row in result.fetchall()}
