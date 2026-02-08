"""Data access layer for HA Zones (multi-server connections).

Provides CRUD operations for ha_zone records, using the same
Fernet encryption pattern as system_config for token storage.
"""

import re
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.dal.system_config import decrypt_token, encrypt_token
from src.storage.entities.ha_zone import HAZone


def _slugify(name: str) -> str:
    """Convert a name to a URL-safe slug.

    Examples:
        "Beach House" -> "beach-house"
        "My Home" -> "my-home"
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class HAZoneRepository:
    """Repository for HA zone CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[HAZone]:
        """List all configured zones, default first."""
        result = await self.session.execute(
            select(HAZone).order_by(HAZone.is_default.desc(), HAZone.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, zone_id: str) -> HAZone | None:
        """Get a zone by its UUID."""
        result = await self.session.execute(
            select(HAZone).where(HAZone.id == zone_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> HAZone | None:
        """Get a zone by its slug."""
        result = await self.session.execute(
            select(HAZone).where(HAZone.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_default(self) -> HAZone | None:
        """Get the default zone."""
        result = await self.session.execute(
            select(HAZone).where(HAZone.is_default.is_(True)).limit(1)
        )
        return result.scalar_one_or_none()

    async def count(self) -> int:
        """Count the total number of zones."""
        result = await self.session.execute(select(HAZone))
        return len(list(result.scalars().all()))

    async def create(
        self,
        *,
        name: str,
        ha_url: str,
        ha_token: str,
        secret: str,
        ha_url_remote: str | None = None,
        is_default: bool = False,
        latitude: float | None = None,
        longitude: float | None = None,
        icon: str | None = None,
    ) -> HAZone:
        """Create a new zone with encrypted token.

        Args:
            name: Human-readable name (e.g. "Beach House").
            ha_url: Primary/local HA URL.
            ha_token: Plaintext HA long-lived access token (will be encrypted).
            secret: Encryption secret (JWT_SECRET).
            ha_url_remote: Optional remote/public HA URL.
            is_default: Whether to make this the default zone.
            latitude: Optional geo latitude.
            longitude: Optional geo longitude.
            icon: Optional MDI icon.

        Returns:
            The created HAZone instance.
        """
        slug = _slugify(name)

        # Ensure slug uniqueness by appending a counter
        existing = await self.get_by_slug(slug)
        if existing:
            counter = 2
            while True:
                candidate = f"{slug}-{counter}"
                if not await self.get_by_slug(candidate):
                    slug = candidate
                    break
                counter += 1

        # If making this the new default, unset existing defaults
        if is_default:
            await self._clear_defaults()

        # If this is the first zone, make it default regardless
        total = await self.count()
        if total == 0:
            is_default = True

        ha_token_encrypted = encrypt_token(ha_token, secret)

        zone = HAZone(
            id=str(uuid4()),
            name=name,
            slug=slug,
            ha_url=ha_url,
            ha_url_remote=ha_url_remote,
            ha_token_encrypted=ha_token_encrypted,
            is_default=is_default,
            latitude=latitude,
            longitude=longitude,
            icon=icon,
        )
        self.session.add(zone)
        await self.session.flush()
        return zone

    async def update(
        self,
        zone_id: str,
        *,
        secret: str,
        name: str | None = None,
        ha_url: str | None = None,
        ha_url_remote: str | None = ...,  # type: ignore[assignment]
        ha_token: str | None = None,
        latitude: float | None = ...,  # type: ignore[assignment]
        longitude: float | None = ...,  # type: ignore[assignment]
        icon: str | None = ...,  # type: ignore[assignment]
    ) -> HAZone | None:
        """Update a zone. Only provided fields are changed.

        Use sentinel `...` (Ellipsis) to skip nullable fields vs explicit None.

        Args:
            zone_id: Zone UUID.
            secret: Encryption secret for re-encrypting token if changed.
            name: New name (also regenerates slug).
            ha_url: New primary URL.
            ha_url_remote: New remote URL (None to clear, ... to skip).
            ha_token: New plaintext token (None to skip).
            latitude: New latitude (None to clear, ... to skip).
            longitude: New longitude (None to clear, ... to skip).
            icon: New icon (None to clear, ... to skip).

        Returns:
            Updated HAZone or None if not found.
        """
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None

        if name is not None:
            zone.name = name
            zone.slug = _slugify(name)
        if ha_url is not None:
            zone.ha_url = ha_url
        if ha_url_remote is not ...:
            zone.ha_url_remote = ha_url_remote
        if ha_token is not None:
            zone.ha_token_encrypted = encrypt_token(ha_token, secret)
        if latitude is not ...:
            zone.latitude = latitude
        if longitude is not ...:
            zone.longitude = longitude
        if icon is not ...:
            zone.icon = icon

        await self.session.flush()
        return zone

    async def delete(self, zone_id: str) -> bool:
        """Delete a zone.

        Cannot delete the default zone or the last remaining zone.

        Args:
            zone_id: Zone UUID.

        Returns:
            True if deleted, False if not found or cannot delete.
        """
        zone = await self.get_by_id(zone_id)
        if not zone:
            return False
        if zone.is_default:
            return False

        total = await self.count()
        if total <= 1:
            return False

        await self.session.delete(zone)
        await self.session.flush()
        return True

    async def set_default(self, zone_id: str) -> HAZone | None:
        """Set a zone as the default.

        Args:
            zone_id: Zone UUID to make default.

        Returns:
            The updated zone or None if not found.
        """
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None

        await self._clear_defaults()
        zone.is_default = True
        await self.session.flush()
        return zone

    async def get_connection(
        self, zone_id: str, secret: str
    ) -> tuple[str, str | None, str] | None:
        """Get decrypted connection details for a zone.

        Args:
            zone_id: Zone UUID.
            secret: Decryption secret.

        Returns:
            Tuple of (ha_url, ha_url_remote, ha_token) or None.
        """
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        token = decrypt_token(zone.ha_token_encrypted, secret)
        return zone.ha_url, zone.ha_url_remote, token

    async def _clear_defaults(self) -> None:
        """Unset is_default on all zones."""
        await self.session.execute(
            update(HAZone).where(HAZone.is_default.is_(True)).values(is_default=False)
        )
