"""API routes for HA Zone management (multi-server connections).

Provides CRUD endpoints for creating, listing, updating, deleting,
and testing connectivity to Home Assistant zones.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.api.auth import _get_jwt_secret
from src.api.ha_verify import verify_ha_connection
from src.dal.ha_zones import HAZoneRepository
from src.storage import get_session
import src.settings as _settings_mod

router = APIRouter(prefix="/zones", tags=["HA Zones"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class ZoneCreate(BaseModel):
    """Request body for creating a new zone."""

    name: str = Field(max_length=200, description="Human-readable zone name")
    ha_url: str = Field(max_length=500, description="Primary/local HA URL")
    ha_url_remote: str | None = Field(
        None, max_length=500, description="Public/remote HA URL"
    )
    ha_token: str = Field(description="HA long-lived access token")
    is_default: bool = False
    latitude: float | None = None
    longitude: float | None = None
    icon: str | None = Field(None, max_length=100, description="MDI icon name")


class ZoneUpdate(BaseModel):
    """Request body for updating a zone. Only provided fields are changed."""

    name: str | None = Field(None, max_length=200)
    ha_url: str | None = Field(None, max_length=500)
    ha_url_remote: str | None = Field(None, max_length=500)
    ha_token: str | None = Field(None, description="New token (re-encrypted)")
    latitude: float | None = None
    longitude: float | None = None
    icon: str | None = Field(None, max_length=100)


class ZoneResponse(BaseModel):
    """Zone response (no token exposed)."""

    id: str
    name: str
    slug: str
    ha_url: str
    ha_url_remote: str | None
    is_default: bool
    latitude: float | None
    longitude: float | None
    icon: str | None
    created_at: str
    updated_at: str


class ZoneTestResult(BaseModel):
    """Result of testing connectivity to a zone."""

    local_ok: bool
    remote_ok: bool | None = None
    local_version: str | None = None
    remote_version: str | None = None
    local_error: str | None = None
    remote_error: str | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _serialize_zone(zone) -> dict:
    """Serialize a zone entity to a response dict."""
    return {
        "id": zone.id,
        "name": zone.name,
        "slug": zone.slug,
        "ha_url": zone.ha_url,
        "ha_url_remote": zone.ha_url_remote,
        "is_default": zone.is_default,
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "icon": zone.icon,
        "created_at": zone.created_at.isoformat() if zone.created_at else None,
        "updated_at": zone.updated_at.isoformat() if zone.updated_at else None,
    }


def _get_secret() -> str:
    """Get the JWT secret for encryption/decryption."""
    settings = _settings_mod.get_settings()
    return _get_jwt_secret(settings)


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ZoneResponse])
async def list_zones():
    """List all configured HA zones."""
    async with get_session() as session:
        repo = HAZoneRepository(session)
        zones = await repo.list_all()
        return [_serialize_zone(z) for z in zones]


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(body: ZoneCreate):
    """Create a new HA zone. Validates connectivity before saving."""
    # Validate HA connection (SSRF-protected)
    await verify_ha_connection(body.ha_url, body.ha_token)

    # If remote URL provided, try it too (but don't fail on it)
    if body.ha_url_remote:
        try:
            await verify_ha_connection(body.ha_url_remote, body.ha_token)
        except HTTPException:
            pass  # Remote is optional; it may not be reachable from server

    secret = _get_secret()

    async with get_session() as session:
        repo = HAZoneRepository(session)
        zone = await repo.create(
            name=body.name,
            ha_url=body.ha_url,
            ha_url_remote=body.ha_url_remote,
            ha_token=body.ha_token,
            secret=secret,
            is_default=body.is_default,
            latitude=body.latitude,
            longitude=body.longitude,
            icon=body.icon,
        )
        await session.commit()
        return _serialize_zone(zone)


@router.patch("/{zone_id}", response_model=ZoneResponse)
async def update_zone(zone_id: str, body: ZoneUpdate):
    """Update a zone's configuration."""
    secret = _get_secret()

    # If changing URL or token, validate connectivity
    if body.ha_url or body.ha_token:
        async with get_session() as session:
            repo = HAZoneRepository(session)
            existing = await repo.get_by_id(zone_id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Zone not found.",
                )
            test_url = body.ha_url or existing.ha_url
            if body.ha_token:
                test_token = body.ha_token
            else:
                from src.dal.system_config import decrypt_token

                test_token = decrypt_token(existing.ha_token_encrypted, secret)
            await verify_ha_connection(test_url, test_token)

    async with get_session() as session:
        repo = HAZoneRepository(session)

        # Build kwargs — use Ellipsis sentinel for fields not provided
        kwargs: dict = {"secret": secret}
        if body.name is not None:
            kwargs["name"] = body.name
        if body.ha_url is not None:
            kwargs["ha_url"] = body.ha_url
        if body.ha_url_remote is not None:
            kwargs["ha_url_remote"] = body.ha_url_remote
        if body.ha_token is not None:
            kwargs["ha_token"] = body.ha_token
        if body.latitude is not None:
            kwargs["latitude"] = body.latitude
        if body.longitude is not None:
            kwargs["longitude"] = body.longitude
        if body.icon is not None:
            kwargs["icon"] = body.icon

        zone = await repo.update(zone_id, **kwargs)
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Zone not found.",
            )
        await session.commit()
        return _serialize_zone(zone)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(zone_id: str):
    """Delete a zone. Cannot delete the default or last zone."""
    async with get_session() as session:
        repo = HAZoneRepository(session)
        deleted = await repo.delete(zone_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete this zone. It may be the default zone, "
                "the last remaining zone, or not found.",
            )
        await session.commit()


@router.post("/{zone_id}/set-default", response_model=ZoneResponse)
async def set_default_zone(zone_id: str):
    """Set a zone as the default."""
    async with get_session() as session:
        repo = HAZoneRepository(session)
        zone = await repo.set_default(zone_id)
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Zone not found.",
            )
        await session.commit()
        return _serialize_zone(zone)


@router.post("/{zone_id}/test", response_model=ZoneTestResult)
async def test_zone(zone_id: str):
    """Test connectivity to a zone's local and remote URLs."""
    secret = _get_secret()

    async with get_session() as session:
        repo = HAZoneRepository(session)
        conn = await repo.get_connection(zone_id, secret)
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Zone not found.",
            )

    ha_url, ha_url_remote, ha_token = conn

    # Test local URL
    local_ok = False
    local_version = None
    local_error = None
    try:
        result = await verify_ha_connection(ha_url, ha_token)
        local_ok = True
        local_version = result.get("version")
    except HTTPException as e:
        local_error = e.detail

    # Test remote URL (if configured)
    remote_ok = None
    remote_version = None
    remote_error = None
    if ha_url_remote:
        try:
            result = await verify_ha_connection(ha_url_remote, ha_token)
            remote_ok = True
            remote_version = result.get("version")
        except HTTPException as e:
            remote_ok = False
            remote_error = e.detail

    return ZoneTestResult(
        local_ok=local_ok,
        remote_ok=remote_ok,
        local_version=local_version,
        remote_version=remote_version,
        local_error=local_error,
        remote_error=remote_error,
    )
